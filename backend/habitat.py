"""C1 Sol16/17 opt-in rehearsal habitat actions. No medical decisions; simulation only."""
import json
import logging
import threading
import time
from contextlib import closing
from backend.db import connect
from backend.model import pipeline
from backend.mission import mission_sol, mission_status
from backend.today import today
from backend.seed import SOURCE, C1_SOL16_SLEEP, HYPOTHETICAL_EVA_ASSIGNMENT

LOW_Z = -2.0
CREW = "c1"
FIXED = {
    "lighting": ({"amber": None, "off": "23:00"}, {"amber": "21:00", "off": "22:00"}),
    "schedule": ({"activity": HYPOTHETICAL_EVA_ASSIGNMENT["activity"], "start": "09:00"},
                 {"activity": HYPOTHETICAL_EVA_ASSIGNMENT["activity"], "start": "13:00"}),
}

def _metrics(connection, sol):
    res = today(connection, CREW, sol)
    items = res.get("metrics", []) if isinstance(res, dict) else res
    return {m["metric"]: m for m in items or []}

def _low(m, key):
    z = (m.get(key) or {}).get("z")
    return z is not None and z <= LOW_Z

def is_rehearsal(connection):
    return connection.execute(
        "SELECT 1 FROM sample WHERE crew_id=? AND source=? AND source_key=? AND value=?",
        (CREW, SOURCE, "c1:sleep:16", float(C1_SOL16_SLEEP))).fetchone() is not None

def _auto(now):
    s = mission_status(now)
    s = s.get("comms_state") if isinstance(s, dict) else s
    return str(s).lower() in ("delayed", "blackout")

def sync(connection, now, cite_ids):
    sol = mission_sol(now)
    if sol < 16 or not is_rehearsal(connection):
        return
    if sol == 16:
        m = _metrics(connection, 16)
        sleep, hrv = _low(m, "sleep"), _low(m, "hrv")
        trig = {k: {"value": m[k]["value"], "z": m[k]["z"]} for k in ("sleep", "hrv") if k in m}
        eva = (HYPOTHETICAL_EVA_ASSIGNMENT["crew_id"] == CREW
               and HYPOTHETICAL_EVA_ASSIGNMENT["mission_day"] == 16)
        rules = []
        if sleep or hrv:
            rules.append(("lighting", "low_sleep_or_low_hrv", "Dim warm lighting to support rest."))
        if hrv and eva and sleep:
            rules.append(("schedule", "low_hrv_eva_low_sleep",
                          "Shift EVA later; EVA itself unchanged. Owner approval required."))
        for target, rule, reason in rules:
            auto = target == "lighting" and _auto(now)
            before, after = FIXED[target]
            cites = list(cite_ids.get(target, [])) if sleep else []
            data = {"rule": rule, "reason": reason, "before": before, "after": after,
                    "trigger": trig, "cite_ids": cites, "outcome": None}
            connection.execute(
                "INSERT INTO habitat_action(crew_id,sol,target,status,auto,applied_at,data)"
                " VALUES(?,?,?,?,?,?,?) ON CONFLICT(crew_id,sol,target) DO UPDATE SET"
                " status='applied', auto=1, applied_at=excluded.applied_at, data=excluded.data"
                " WHERE excluded.auto=1 AND habitat_action.status='proposed'",
                (CREW, 16, target, "applied" if auto else "proposed", int(auto),
                 now.isoformat() if auto else None, json.dumps(data)))
        return
    m = _metrics(connection, 17)
    for row in connection.execute(
            "SELECT * FROM habitat_action WHERE crew_id=? AND sol=16 AND status='applied'"
            " AND released_at IS NULL", (CREW,)).fetchall():
        data = json.loads(row["data"])
        if data.get("outcome") is not None:
            continue
        sz, hz = (m.get("sleep") or {}).get("z"), (m.get("hrv") or {}).get("z")
        if hz is None or sz is None:
            continue
        snap = {k: {"value": v["value"], "z": v["z"]} for k, v in m.items() if k in ("sleep", "hrv")}
        ok = hz > -1 and sz >= -1
        data["outcome"] = {"sol": 17, "metrics": snap, "rule_satisfied": ok}
        connection.execute(
            "UPDATE habitat_action SET data=?, released_at=?, status=? WHERE id=? AND status='applied'"
            " AND released_at IS NULL",
            (json.dumps(data), now.isoformat() if ok else None, "released" if ok else "applied", row["id"]))

def list_actions(connection, crew_id, sol):
    return connection.execute("SELECT * FROM habitat_action WHERE crew_id=? AND sol BETWEEN ? AND ? ORDER BY id",
                              (crew_id, sol - 1, sol)).fetchall()

def action(connection, action_id):
    return connection.execute("SELECT * FROM habitat_action WHERE id=?", (int(action_id),)).fetchone()

def change(connection, row, command, actor_id, now, reason=None):
    if row is None or mission_sol(now) != row["sol"]:
        return None
    t = now.isoformat()
    if command == "approve":
        sql = ("UPDATE habitat_action SET status='applied', approved_by=?, applied_at=?"
               " WHERE id=? AND status='proposed'", (actor_id, t, int(row["id"])))
    elif command == "undo":
        if json.loads(row["data"]).get("outcome") is not None:
            return None
        sql = ("UPDATE habitat_action SET status='undone', undone_by=?, undone_at=?, undo_reason=?"
               " WHERE id=? AND status IN ('proposed','applied') AND released_at IS NULL"
               " AND json_extract(data,'$.outcome') IS NULL", (actor_id, t, reason, int(row["id"])))
    else:
        return None
    if connection.execute(*sql).rowcount != 1:
        return None
    return action(connection, row["id"])

REASON_WAIT = 10.0      # seconds after a reason job starts during which GETs wait for it
_LEVELS = ("normal", "advisory", "caution", "warning")
_reason_jobs = {}       # (db path, action id, lang) -> (thread, start time) of a job still running
_reason_failed = set()  # keys whose attempt ended without a verified sentence; not retried in this process
_reason_lock = threading.Lock()

def _stored_reason(data, lang):
    texts = data.get("reason_text")
    text = texts.get(lang) if isinstance(texts, dict) else None
    return text if isinstance(text, str) and text.strip() else None

def _write_reason(db_path, action_id, lang, evidence):
    """Background job: ask the model for the reason of one action and store it. Never raises."""
    key, done = (str(db_path), action_id, lang), False
    try:
        with closing(connect(db_path)) as connection:
            row = action(connection, action_id)
            metrics = _metrics(connection, row["sol"]) if row is not None else {}
        if row is None:
            return
        findings = [metrics[k] for k in ("sleep", "hrv") if (metrics.get(k) or {}).get("z") is not None]
        level = max((f.get("level") for f in findings if f.get("level") in _LEVELS),
                    key=_LEVELS.index, default="caution")
        out = pipeline.adjustment_reason(row["target"], level, findings, evidence, lang)
        if not out.get("reason"):
            return
        with closing(connect(db_path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = action(connection, action_id)  # re-read inside the write transaction: data may have changed meanwhile
            if row is None:
                return
            data = json.loads(row["data"])
            texts = data.get("reason_text") if isinstance(data.get("reason_text"), dict) else {}
            data["reason_text"] = {**texts, lang: out["reason"]}
            connection.execute("UPDATE habitat_action SET data=? WHERE id=?", (json.dumps(data), action_id))
        done = True
    except Exception:
        logging.getLogger(__name__).warning("Habitat reason could not be written.", exc_info=True)
    finally:
        with _reason_lock:
            _reason_jobs.pop(key, None)
            if not done:
                _reason_failed.add(key)

def rows_with_reasons(connection, db_path, evidence, crew_id, sol, lang, wait=None):
    """list_actions(), after making sure a reason sentence is being written for every listed action that lacks one.
    Each job is waited for only until `wait` seconds (default REASON_WAIT) after it started, then the rows are returned as they are now."""
    rows = list_actions(connection, crew_id, sol)
    threads = []
    with _reason_lock:
        for row in rows:
            key = (str(db_path), row["id"], lang)
            if _stored_reason(json.loads(row["data"]), lang) or key in _reason_failed:
                continue
            job = _reason_jobs.get(key)
            if job is None:
                thread = threading.Thread(target=_write_reason, args=(db_path, row["id"], lang, evidence), daemon=True)
                job = _reason_jobs[key] = (thread, time.monotonic())
                thread.start()
            threads.append(job)
    limit = REASON_WAIT if wait is None else wait
    for thread, started in threads:
        thread.join(max(0.0, started + limit - time.monotonic()))
    return list_actions(connection, crew_id, sol) if threads else rows

def _text(target, values, lang):
    v = values if isinstance(values, dict) else {}
    ko = lang == "ko"
    if target == "lighting":
        parts = []
        if v.get("amber"):
            parts.append(f"{v['amber']} 앰버 조명" if ko else f"Amber light {v['amber']}")
        if v.get("off"):
            parts.append(f"{v['off']} 소등" if ko else f"Lights off {v['off']}")
        return " · ".join(parts)
    if target == "schedule":
        a, s = v.get("activity"), v.get("start")
        a = str(a).upper() if a else a
        return f"{a} {s} 시작" if ko else f"{a} starts {s}"
    return ""

def _valid(trig, key):
    t = trig.get(key)
    return isinstance(t, dict) and t.get("z") is not None

def _reason(target, trig):
    if target == "schedule":
        order = ("hrv", "sleep")
    elif _valid(trig, "sleep") and trig["sleep"]["z"] <= LOW_Z:
        order = ("sleep", "hrv")
    else:
        order = ("hrv", "sleep")
    for key in order:
        if _valid(trig, key):
            return {"metric": key, "value": trig[key].get("value"), "z": trig[key]["z"]}
    return None

def _outcome(row, trig, out):
    if not isinstance(out, dict):
        return None
    ms = out.get("metrics")
    if isinstance(ms, list):
        metrics = ms
    else:
        ms = ms if isinstance(ms, dict) else {}
        metrics = [{"metric": k,
                    "before": (trig.get(k) or {}).get("value"), "before_z": (trig.get(k) or {}).get("z"),
                    "after": (ms.get(k) or {}).get("value"), "after_z": (ms.get(k) or {}).get("z")}
                   for k in ("sleep", "hrv") if k in ms]
    return {"sol": out.get("sol"), "released": row["released_at"] is not None,
            "rule_satisfied": out.get("rule_satisfied"), "metrics": metrics}

def payload(row, lang="en"):
    d = json.loads(row["data"])
    trig = d.get("trigger") if isinstance(d.get("trigger"), dict) else {}
    target = row["target"]
    return {"id": row["id"], "crew": row["crew_id"], "crew_id": row["crew_id"], "sol": row["sol"],
            "target": target, "status": row["status"],
            "tier": "auto" if row["auto"] else "approve", "auto": bool(row["auto"]),
            "approved_by": row["approved_by"],
            "applied_at": row["applied_at"], "undone_by": row["undone_by"], "undone_at": row["undone_at"],
            "undo_reason": row["undo_reason"], "released_at": row["released_at"],
            "rule": d.get("rule"), "reason": _reason(target, trig), "reason_text": _stored_reason(d, lang),
            "before": _text(target, d.get("before"), lang), "after": _text(target, d.get("after"), lang),
            "before_values": d.get("before"), "after_values": d.get("after"),
            "trigger": d.get("trigger"), "cite_ids": d.get("cite_ids", []),
            "outcome": _outcome(row, trig, d.get("outcome")), "simulation": True}
