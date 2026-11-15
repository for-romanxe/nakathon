import json
import sqlite3
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.tests.test_mission_demo_seed import seed_demo

URL = "/events/{}/procedure"


def h(c):
    return {"X-Demo-Viewer": c}


class ProcedureConsentTest(TestCase):
    def setUp(self):
        d = Path(self.enterContext(TemporaryDirectory()))
        self.path = d / "demo.sqlite3"
        r = seed_demo(self.path)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.client = self.enterContext(TestClient(create_app(self.path)))
        self.client.post("/demo/clock", json={"sol": 46, "time": "08:00"}, headers=h("c2")).raise_for_status()
        self.event = self.client.post("/crew/c4/symptom", headers=h("c4"),
                                      json={"text": "I have chest pain", "lang": "en"}).raise_for_status().json()
        self.eid = self.event["event_id"]

    def approve(self, who, step="save_report", lang=None):
        return self.client.post(f"{URL.format(self.eid)}/steps/{step}/approve", headers=h(who),
                                params={"lang": lang} if lang else None)

    def check(self, body, lang="en"):
        self.assertEqual((body["event_id"], body["patient"], body["consenters"]), (self.eid, "c4", ["c1", "c3"]))
        s = body["steps"][0]
        self.assertEqual((s["kind"], s["needs_consent"]), ("report", True))
        self.assertIn("보고서" if lang == "ko" else "crew report", s["text"])
        self.assertTrue(all(a["crew"] == a["crew_id"] for a in s["approvals"]))
        self.assertEqual(body["current_step"], None if s["done"] else "save_report")

    def read(self, who="c4", lang="en"):
        return self.client.get(URL.format(self.eid), params={"lang": lang}, headers=h(who))

    def count(self, sql):
        with closing(sqlite3.connect(self.path)) as c:
            return c.execute(sql).fetchone()[0]

    def test_flow(self):
        body = self.read().json()
        self.check(body)
        self.assertTrue(body["available"])
        self.assertFalse(body["medical_available"])
        self.assertEqual(body["steps"][0]["approvals"], [])
        self.assertEqual(self.count("SELECT COUNT(*) FROM procedure_approval"), 0)
        self.check(self.read("c1", "ko").json(), "ko")
        self.assertEqual(self.read(lang="fr").status_code, 422)
        self.assertEqual(self.approve("c2").status_code, 403)
        self.assertEqual(self.approve("c1", "other").status_code, 404)
        self.check(self.approve("c1", lang="ko").raise_for_status().json(), "ko")
        self.check(self.approve("c1").raise_for_status().json())
        self.assertEqual(self.approve("c1", lang="fr").status_code, 422)
        self.assertEqual(self.count("SELECT COUNT(*) FROM earth_report"), 0)
        half = self.read().json()
        self.assertEqual(len(half["steps"][0]["approvals"]), 1)
        self.assertEqual(half["required"], 2)
        self.assertFalse(half["steps"][0]["done"])
        self.assertEqual(half["current_step"], "save_report")
        self.approve("c3").raise_for_status()
        self.approve("c3").raise_for_status()
        self.assertEqual(self.count("SELECT COUNT(*) FROM procedure_approval"), 2)
        self.assertEqual(self.count("SELECT COUNT(*) FROM earth_report"), 1)
        done = self.read().json()
        self.check(done)
        self.assertEqual(len(done["steps"][0]["approvals"]), 2)
        self.assertTrue(done["steps"][0]["done"])
        self.assertFalse(done["medical_available"])
        reports = self.client.get("/earth-reports", headers=h("c4")).json()["reports"]
        self.assertEqual(len(reports), 1)
        self.assertEqual([sorted(a) for a in reports[0]["approvals"]], [["at", "crew_id"]] * 2)
        seq = reports[0]["packet"]["seq"]
        self.assertEqual(reports[0]["packet"]["status"], "held")
        text = json.dumps(reports)
        self.assertNotIn("symptom_text", text)
        self.assertNotIn("chest pain", text)
        tx = self.client.get("/tx", headers=h("c2")).json()
        matches = [p for p in tx if p["seq"] == seq]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "queued")
        self.client.post("/demo/clock", json={"sol": 57, "time": "08:00"}, headers=h("c2")).raise_for_status()
        self.client.post("/tx/send", headers=h("c2")).raise_for_status()
        tx = self.client.get("/tx", headers=h("c2")).json()
        self.assertEqual([p["status"] for p in tx if p["seq"] == seq], ["sent"])
        rep = self.client.get("/earth-reports", headers=h("c4")).json()["reports"]
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0]["packet"]["seq"], seq)
        self.assertEqual(rep[0]["packet"]["status"], "sent")
        self.assertIsNone(rep[0]["packet"]["held_reason"])
        cmo = self.client.get("/earth-reports", headers=h("c2")).json()["reports"]
        self.assertEqual([x["packet"]["seq"] for x in cmo], [seq])
        self.assertEqual(self.client.get("/earth-reports", headers=h("c3")).json()["reports"], [])
        with TestClient(create_app(self.path)) as again:
            r = again.get("/earth-reports", headers=h("c4")).json()["reports"]
            self.assertEqual(r[0]["packet"]["seq"], seq)

    def reqs(self, who, crew=None):
        r = self.client.get(f"/crew/{crew or who}/today", headers=h(who)).raise_for_status()
        return r.json()["consent_requests"]

    def test_today_requests_and_report_metrics(self):
        want = [{"event_id": self.eid, "patient": "c4", "step_id": "save_report",
                 "approvals": 0, "required": 2}]
        self.assertEqual(self.reqs("c1"), want)
        self.assertEqual(self.reqs("c3"), want)
        self.assertEqual((self.reqs("c2"), self.reqs("c4"), self.reqs("c2", "c1")), ([], [], []))
        self.approve("c1").raise_for_status()
        self.assertEqual(self.reqs("c1"), [])
        self.assertEqual(self.reqs("c3"), [{**want[0], "approvals": 1}])
        self.approve("c3").raise_for_status()
        self.assertEqual((self.reqs("c1"), self.reqs("c3")), ([], []))
        rep = self.client.get("/earth-reports", headers=h("c4")).json()["reports"][0]
        got = {m["metric"]: m["value"] for m in rep["metrics"]}
        self.assertEqual(len(got), 6)
        self.assertTrue(all(isinstance(v, (int, float)) and not isinstance(v, bool)
                            for v in got.values()))
        ev = self.client.get(f"/events/{self.eid}", headers=h("c4")).raise_for_status().json()
        found = {f["metric"]: f for f in ev["findings"]}
        self.assertEqual(got, {k: found[k]["value"] for k in got})
        for m in ("hr", "hrv"):
            self.assertEqual(found[m]["level"], "caution")
        self.assertNotIn("chest", json.dumps(rep))

    def test_ordinary_clock_no_requests(self):
        self.client.post("/demo/clock", json={"sol": 57, "time": "08:00"}, headers=h("c2")).raise_for_status()
        self.assertEqual((self.reqs("c1"), self.reqs("c3")), ([], []))

    def test_concurrent_approvals(self):
        with ThreadPoolExecutor(4) as pool:
            codes = list(pool.map(lambda w: self.approve(w).status_code, ["c1", "c3", "c1", "c3"]))
        self.assertTrue(all(c == 200 for c in codes))
        self.assertEqual(self.count("SELECT COUNT(*) FROM earth_report"), 1)
        self.assertEqual(self.count("SELECT COUNT(*) FROM procedure_approval"), 2)
