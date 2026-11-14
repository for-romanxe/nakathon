from contextlib import closing
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

    def test_next_window_after_sol_rollover(self):
        self.client.post("/demo/clock", json={"sol": 16, "time": "23:59"}).raise_for_status()
        self.assertEqual(self.client.get("/mission").json()["next_window"], "08:00")
        mission = self.client.post("/demo/clock", json={"advance": "481m"}).raise_for_status().json()
        self.assertEqual(mission["clock"], {"sol": 17, "time": "08:00"})
        self.assertEqual(mission["next_window"], "20:00")

    def test_event_day_is_excluded_only_while_inside_baseline(self):
        self.client.post("/demo/clock", json={"sol": 2, "time": "10:00"}).raise_for_status()
        self.client.post("/crew/c2/symptom", headers={"X-Demo-Viewer": "c2"}, json={"text": "Dizzy", "lang": "en"}).raise_for_status()

        self.client.post("/demo/clock", json={"sol": 16, "time": "10:00"}).raise_for_status()
        metric = self.client.get("/crew/c2/today", headers={"X-Demo-Viewer": "c2"}).json()["metrics"][0]
        self.assertEqual(metric["hold_reason"], "insufficient_baseline")
        self.assertIsNotNone(metric["value"])

        self.client.post("/demo/clock", json={"sol": 17, "time": "10:00"}).raise_for_status()
        metric = self.client.get("/crew/c2/today", headers={"X-Demo-Viewer": "c2"}).json()["metrics"][0]
        self.assertIsNotNone(metric["baseline"])
        self.assertEqual(metric["hold_reason"], "missing_reading")

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
