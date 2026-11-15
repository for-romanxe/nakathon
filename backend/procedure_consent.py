import json
import sqlite3

from backend.mission import mission_sol, in_blackout
from backend.habitat import is_rehearsal

APPROVERS = ("c1", "c3")
STEP_ID = "save_report"
_TEXT = {
    "en": "Save a crew report of the logged readings for later transmission.",
    "ko": "기록된 측정값으로 승무원 보고서를 저장하여 나중에 전송합니다.",
}


class MissingPacketError(LookupError):
    """Raised when no tx_packet exists; caller must roll back."""


def eligible(conn: sqlite3.Connection, event, now) -> bool:
    if event is None:
        return False
    sol = mission_sol(now)
    codes = json.loads(event["codes"] or "[]")
    return bool(
        is_rehearsal(conn) and event["crew_id"] == "c4" and event["mission_day"] == 46
        and sol >= 46 and in_blackout(sol) and event["level"] == "warning"
        and event["urgent"] and "chest_pain" in codes and event["closed_at"] is None
    )


def _approvals(conn, event_id):
    rows = conn.execute(
        "SELECT crew_id, at FROM procedure_approval WHERE event_id=? AND step_id=? "
        "ORDER BY at, crew_id", (event_id, STEP_ID)).fetchall()
    return [{"crew_id": r["crew_id"], "at": r["at"]} for r in rows]


def read(conn, event_id, lang, available) -> dict:
    apps = _approvals(conn, event_id) if available else []
    done = len(apps) >= 2
    steps = [{"step_id": STEP_ID, "text": _TEXT.get(lang, _TEXT["en"]), "cite_id": None,
              "approvals": apps, "done": done}] if available else []
    return {"available": bool(available), "medical_available": False, "required": 2,
            "current_step": STEP_ID if available and not done else None,
            "hold_reason": "medical_steps_unreviewed", "steps": steps, "simulation": True}


def approve(conn, event, crew_id, now) -> dict:
    if crew_id not in APPROVERS or not eligible(conn, event, now):
        raise PermissionError("approval not allowed")
    conn.execute("INSERT OR IGNORE INTO procedure_approval(event_id, step_id, crew_id, at) "
                 "VALUES (?,?,?,?)", (event["id"], STEP_ID, crew_id, now.isoformat()))
    apps = _approvals(conn, event["id"])
    if len(apps) >= 2:
        pkt = conn.execute("SELECT seq, payload FROM tx_packet WHERE event_id=? ORDER BY seq "
                           "LIMIT 1", (event["id"],)).fetchone()
        if pkt is None:
            raise MissingPacketError(f"no tx_packet for event {event['id']}")
        payload = json.loads(pkt["payload"])
        snap = {"level": event["level"], "metrics": payload.get("readings", {}),
                "approvals": apps, "actions": [], "cite_ids": []}
        conn.execute("INSERT OR IGNORE INTO earth_report(event_id, packet_seq, created_at, "
                     "snapshot) VALUES (?,?,?,?)",
                     (event["id"], pkt["seq"], now.isoformat(), json.dumps(snap, sort_keys=True)))
    return read(conn, event["id"], event["lang"], True)


def list_reports(conn, crew_id, now) -> list:
    sql = ("SELECT r.id, r.event_id, r.created_at, r.snapshot, p.seq, p.status "
           "FROM earth_report r JOIN event e ON e.id = r.event_id "
           "JOIN crew c ON c.id = e.crew_id "
           "LEFT JOIN tx_packet p ON p.seq = r.packet_seq")
    if crew_id is None:
        rows = conn.execute(sql + " WHERE c.cmo_access = 1 ORDER BY r.id").fetchall()
    else:
        rows = conn.execute(sql + " WHERE e.crew_id = ? ORDER BY r.id", (crew_id,)).fetchall()
    blackout = in_blackout(mission_sol(now))
    out = []
    for r in rows:
        status = r["status"] if r["seq"] is not None else "missing"
        held = blackout and status in ("queued", "missing")
        snap = json.loads(r["snapshot"])
        out.append({"report_id": r["id"], "event_id": r["event_id"],
                    "created_at": r["created_at"], **snap,
                    "packet": {"seq": r["seq"], "status": "held" if held else status,
                               "held_reason": "blackout" if held else None}})
    return out
