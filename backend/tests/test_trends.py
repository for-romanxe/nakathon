from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.db import connect
from backend.main import create_app


class TrendsTest(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / "demo.sqlite3"
        self.api = self.enterContext(TestClient(create_app(self.path)))
        self.url = "/crew/c1/trends"

    def read(self, days):
        return self.api.get(self.url, params={"metric": "hr", "days": days}).raise_for_status().json()

    def test_window_averages_samples_and_omits_missing_and_future_days(self):
        with closing(connect(self.path)) as db, db:
            db.execute("UPDATE sample SET value = NULL WHERE crew_id = 'c1' AND metric = 'hr' AND mission_day = 15")
            current = db.execute(
                "SELECT value FROM sample WHERE crew_id = 'c1' AND metric = 'hr' AND mission_day = 16"
            ).fetchone()["value"]
            db.executemany(
                """INSERT INTO sample (crew_id, metric, ts, mission_day, value, source)
                   VALUES ('c1', 'hr', ?, ?, ?, 'test')""",
                [("2026-11-14T05:00:00+00:00", 16, current + 2),
                 ("2026-11-15T05:00:00+00:00", 17, 999)],
            )
        self.assertEqual(self.read(2)["points"], [{"ts": "2026-11-14T05:00:00+00:00", "value": current + 1}])

    def test_baseline_matches_today_independent_of_window_and_excludes_event_days(self):
        def check():
            current = self.api.get("/crew/c1/today").raise_for_status().json()["metrics"]
            hr = next(row for row in current if row["metric"] == "hr")
            expected = {"mean": hr["baseline"], "sd": hr["sd"]}
            self.assertEqual(self.read(7)["baseline"], expected)
            self.assertEqual(self.read(90)["baseline"], expected)
            return expected

        self.assertIsNotNone(check()["mean"])
        self.api.post("/demo/clock", json={"sol": 13, "time": "08:00"}).raise_for_status()
        event = self.api.post("/crew/c1/symptom", json={"text": "Chest pain", "lang": "en"}).raise_for_status().json()
        self.api.post("/demo/clock", json={"sol": 16, "time": "08:00"}).raise_for_status()
        self.assertEqual(check(), {"mean": 68, "sd": 2})
        self.assertEqual([row["id"] for row in self.read(7)["events"]], [event["event_id"]])
        self.assertEqual(self.read(2)["events"], [])

    def test_baseline_backfills_both_missing_reading_and_event_day(self):
        self.api.post("/demo/clock", json={"sol": 16, "time": "08:00"}).raise_for_status()
        self.api.post("/crew/c1/symptom", json={"text": "Chest pain", "lang": "en"}).raise_for_status()
        with closing(connect(self.path)) as db, db:
            db.execute(
                "UPDATE sample SET value = NULL WHERE crew_id = 'c1' AND metric = 'hr' AND mission_day = 15"
            )
            db.execute(
                """INSERT INTO sample (crew_id, metric, ts, mission_day, value, source)
                   VALUES ('c1', 'hr', '2026-11-15T06:00:00+00:00', 17, 68, 'test')"""
            )
        self.api.post("/demo/clock", json={"sol": 17, "time": "08:00"}).raise_for_status()

        today = self.api.get("/crew/c1/today").raise_for_status().json()
        hr = next(metric for metric in today["metrics"] if metric["metric"] == "hr")
        self.assertIsNone(hr["hold_reason"])
        self.assertEqual({"mean": hr["baseline"], "sd": hr["sd"]}, {"mean": 68, "sd": 2})
        self.assertEqual(self.read(7)["baseline"], {"mean": 68, "sd": 2})

    def test_validation_and_visibility_match_today(self):
        cmo = {"X-Demo-Viewer": "c2"}
        self.assertEqual(self.api.get(self.url, params={"metric": "hr"}, headers=cmo).status_code, 200)
        self.api.put("/settings", json={"cmo_access": False}).raise_for_status()
        self.assertEqual(self.api.get(self.url, params={"metric": "hr"}, headers=cmo).status_code, 403)
        self.assertEqual(self.api.get("/crew/unknown/trends?metric=hr").status_code, 404)
        for query in ("", "?metric=unknown", "?metric=hr&days=0", "?metric=hr&days=91"):
            self.assertEqual(self.api.get(self.url + query).status_code, 422)
