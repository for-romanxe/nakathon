from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.db import connect, initialize
from backend.main import create_app


class MedicationIntakeTest(TestCase):
    def test_records_survive_upgrade_and_retry_and_respect_crew_permissions(self):
        path = Path(self.enterContext(TemporaryDirectory())) / "crew.sqlite3"
        initialize(path)
        with closing(connect(path)) as db, db:
            db.execute("DROP TABLE medication_intake")
            db.execute("PRAGMA user_version = 6")

        url = "/crew/c1/medication-intakes"
        cmo = {"X-Demo-Viewer": "c2"}
        other = {"X-Demo-Viewer": "c3"}
        entry = {"request_id": str(uuid4()), "name": " Test item ", "amount": " 1 test unit "}
        with TestClient(create_app(path)) as api:
            self.assertEqual(api.get(url).json(), {"entries": []})
            self.assertEqual(api.post(url, json={**entry, "amount": "  "}).status_code, 422)
            self.assertEqual(api.post(url, json={**entry, "request_id": "bad-id"}).status_code, 422)
            self.assertEqual(api.post(url, headers=cmo, json=entry).status_code, 403)
            self.assertEqual(api.get(url, headers=other).status_code, 403)
            saved = api.post(url, json=entry).raise_for_status().json()
            self.assertEqual((saved["name"], saved["amount"], saved["mission_day"]),
                             ("Test item", "1 test unit", 16))
            api.post("/demo/clock", json={"advance": "24h"}).raise_for_status()
            self.assertEqual(api.post(url, json=entry).raise_for_status().json(), saved)
            self.assertEqual(api.post(url, json={**entry, "amount": "2 test units"}).status_code, 409)
            self.assertEqual(api.get(url, headers=cmo).json(), {"entries": [saved]})
            self.assertEqual(api.get("/crew/c2/medication-intakes", headers=cmo).json(), {"entries": []})
            api.put("/settings", json={"cmo_access": False}).raise_for_status()

        with TestClient(create_app(path)) as api:
            self.assertEqual(api.get(url).json(), {"entries": [saved]})
            self.assertEqual(api.get(url, headers=cmo).status_code, 403)
