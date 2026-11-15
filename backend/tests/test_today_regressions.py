from contextlib import closing
from statistics import mean, pstdev
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.db import connect
from backend.main import create_app


class TodayRegressions(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.db_path = Path(directory) / "demo.sqlite3"
        self.client = self.enterContext(TestClient(create_app(self.db_path)))

    def test_invalid_language_returns_string_error(self):
        response = self.client.get("/crew/c1/today?lang=invalid")
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "invalid_request")
        self.assertIsInstance(error["message"], str)

    def test_yesterdays_outlier_does_not_raise_todays_status(self):
        with closing(connect(self.db_path)) as db, db:
            db.execute("UPDATE sample SET value = 75 WHERE crew_id = 'c2' AND metric = 'hr' AND mission_day = 15")
        self.client.post("/demo/clock", json={"sol": 15, "time": "08:00"}).raise_for_status()
        self.assertEqual(self.client.get("/crew/c2/today", headers={"X-Demo-Viewer": "c2"}).json()["status"]["level"], "advisory")
        self.client.post("/demo/clock", json={"sol": 16, "time": "08:00"}).raise_for_status()
        self.assertEqual(self.client.get("/crew/c2/today", headers={"X-Demo-Viewer": "c2"}).json()["status"]["level"], "normal")

    def test_next_window_reports_next_opening(self):
        for time, next_window in (
            ("07:59", "08:00"), ("08:00", "20:00"), ("08:29", "20:00"),
            ("08:30", "20:00"), ("19:59", "20:00"), ("20:00", "08:00"),
        ):
            with self.subTest(time=time):
                self.client.post("/demo/clock", json={"sol": 16, "time": time}).raise_for_status()
                self.assertEqual(self.client.get("/mission").json()["next_window"], next_window)

    def test_checkin_rejects_non_string_symptoms(self):
        for value in ([], {}, None, True, 1):
            with self.subTest(value=value):
                body = {"kind": "morning", "answers": {
                    "sleep_quality": 3, "mood": 3, "fatigue": 3, "symptoms": value,
                }}
                response = self.client.post("/crew/c1/checkin", json=body)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["code"], "invalid_request")

    def test_evening_checkin_validates_answers(self):
        url = "/crew/c1/checkin"
        answers = {"day_rating": 4, "stress": 2, "hydration_ok": False, "symptoms": "none"}
        for key, value in (("day_rating", True), ("day_rating", "4"), ("day_rating", 4.0),
                           ("day_rating", 0), ("day_rating", 6), ("hydration_ok", "false"),
                           ("hydration_ok", 1), ("hydration_ok", None)):
            with self.subTest(key=key, value=value):
                response = self.client.post(url, json={"kind": "evening", "answers": dict(answers, **{key: value})})
                self.assertEqual(response.status_code, 422)
        saved = self.client.post(url, json={"kind": "evening", "answers": answers}).raise_for_status().json()
        self.assertTrue(saved["checkin"]["evening_done"])
        self.assertFalse(saved["checkin"]["morning_done"])
        self.assertEqual(saved["guide"], [])

    def test_today_prefill_and_baseline_progress(self):
        viewer = {"X-Demo-Viewer": "c3"}
        url = "/crew/c3/today"
        initial = self.client.get(url, headers=viewer).raise_for_status().json()
        self.assertEqual(initial["baseline_progress"], {"collected_days": 9, "target_days": 14})
        self.assertEqual(initial["checkin"]["morning_prefill"]["answers"], {})
        self.client.post("/demo/clock", json={"sol": 15, "time": "08:00"}).raise_for_status()
        answers = {"sleep_quality": 4, "mood": 2, "fatigue": 5}
        self.client.post("/crew/c3/checkin", headers=viewer, json={
            "kind": "morning", "answers": dict(answers, symptoms="yes"),
        }).raise_for_status()
        self.client.post("/crew/c3/symptom", headers=viewer, json={
            "text": "Headache", "lang": "en",
        }).raise_for_status()
        self.client.post("/demo/clock", json={"sol": 16, "time": "08:00"}).raise_for_status()
        current = self.client.get(url, headers=viewer).raise_for_status().json()
        sleep = next(metric for metric in current["metrics"] if metric["metric"] == "sleep")
        self.assertEqual(current["baseline_progress"], {"collected_days": 8, "target_days": 14})
        self.assertEqual(sleep["baseline_days"], 8)
        self.assertEqual(current["checkin"]["morning_prefill"], {"answers": answers, "sleep_hours": sleep["value"]})

    def test_next_window_after_sol_rollover(self):
        self.client.post("/demo/clock", json={"sol": 16, "time": "23:59"}).raise_for_status()
        self.assertEqual(self.client.get("/mission").json()["next_window"], "08:00")
        mission = self.client.post("/demo/clock", json={"advance": "481m"}).raise_for_status().json()
        self.assertEqual(mission["clock"], {"sol": 17, "time": "08:00"})
        self.assertEqual(mission["next_window"], "20:00")

    def test_baseline_backfills_event_days_and_keeps_current_readings(self):
        viewer = {"X-Demo-Viewer": "c2"}
        for sol in (15, 16):
            self.client.post("/demo/clock", json={"sol": sol, "time": "10:00"}).raise_for_status()
            self.client.post("/crew/c2/symptom", headers=viewer, json={"text": "Headache", "lang": "en"}).raise_for_status()

        with closing(connect(self.db_path)) as db, db:
            db.execute(
                """INSERT INTO sample (crew_id, metric, ts, mission_day, value, source)
                   SELECT crew_id, metric, '2026-11-15T06:00:00+00:00', 17, value, 'test'
                   FROM sample WHERE crew_id = 'c2' AND mission_day = 16"""
            )
            history = [
                row["value"] for row in db.execute(
                    "SELECT value FROM sample WHERE crew_id = 'c2' AND metric = 'hr' AND mission_day BETWEEN 1 AND 14"
                )
            ]
        self.client.post("/demo/clock", json={"sol": 17, "time": "10:00"}).raise_for_status()
        today = self.client.get("/crew/c2/today", headers=viewer).raise_for_status().json()
        self.assertEqual(today["status"]["level"], "normal")
        self.assertTrue(all(metric["hold_reason"] is None for metric in today["metrics"]))
        hr = next(metric for metric in today["metrics"] if metric["metric"] == "hr")
        self.assertEqual(hr["baseline"], mean(history))
        self.assertEqual(hr["sd"], pstdev(history))
        self.assertEqual(today["events"], [])

    def test_baseline_stays_on_hold_without_fourteen_eligible_sols(self):
        viewer = {"X-Demo-Viewer": "c2"}
        self.client.post("/demo/clock", json={"sol": 14, "time": "10:00"}).raise_for_status()
        self.client.post("/crew/c2/symptom", headers=viewer, json={"text": "Headache", "lang": "en"}).raise_for_status()
        self.client.post("/demo/clock", json={"sol": 15, "time": "10:00"}).raise_for_status()
        today = self.client.get("/crew/c2/today", headers=viewer).raise_for_status().json()
        self.assertEqual(today["status"]["level"], "hold")
        self.assertTrue(all(metric["hold_reason"] == "insufficient_baseline" for metric in today["metrics"]))

    def test_missing_metric_does_not_hide_caution_or_warning(self):
        with closing(connect(self.db_path)) as db, db:
            db.execute("UPDATE sample SET value = NULL WHERE crew_id = 'c1' AND metric = 'eda' AND mission_day = 16")
        self.assert_status_with_missing_eda("caution")

        with closing(connect(self.db_path)) as db, db:
            db.execute("UPDATE sample SET value = 80 WHERE crew_id = 'c1' AND metric = 'hr' AND mission_day = 16")
        self.assert_status_with_missing_eda("warning")

    def assert_status_with_missing_eda(self, level):
        today = self.client.get("/crew/c1/today").json()
        self.assertEqual(today["status"]["level"], level)
        eda = next(metric for metric in today["metrics"] if metric["metric"] == "eda")
        self.assertEqual(eda["level"], "hold")
        self.assertEqual(eda["hold_reason"], "missing_reading")
