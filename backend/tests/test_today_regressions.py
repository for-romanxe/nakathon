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

    def test_event_day_is_excluded_only_while_inside_baseline(self):
        self.client.post("/demo/clock", json={"sol": 2, "time": "10:00"}).raise_for_status()
        self.client.post("/crew/c2/symptom", json={"text": "Dizzy", "lang": "en"}).raise_for_status()

        self.client.post("/demo/clock", json={"sol": 16, "time": "10:00"}).raise_for_status()
        metric = self.client.get("/crew/c2/today").json()["metrics"][0]
        self.assertEqual(metric["hold_reason"], "insufficient_baseline")
        self.assertIsNotNone(metric["value"])

        self.client.post("/demo/clock", json={"sol": 17, "time": "10:00"}).raise_for_status()
        metric = self.client.get("/crew/c2/today").json()["metrics"][0]
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
