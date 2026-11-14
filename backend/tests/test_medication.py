import json
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.db import connect, initialize
from backend.main import create_app


class MedicationIntakeTest(TestCase):
    def test_label_reference_requires_a_local_catalog(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        path = root / "crew.sqlite3"
        url = "/medication-references"
        with patch.dict("os.environ", {"CREW_HEALTH_MEDICATION_REFERENCES": ""}):
            with TestClient(create_app(path)) as api:
                self.assertEqual(api.get(url).json(), {"references": []})
        reference = {
            "id": "synthetic-product", "product": "Synthetic product", "strength": "Test strength",
            "directions": "Synthetic reference text.", "warnings": "Synthetic warning.",
            "label_revision": "Test revision", "label_url": "https://example.org/label",
        }
        catalog = root / "catalog.json"
        with patch.dict("os.environ", {"CREW_HEALTH_MEDICATION_REFERENCES": str(catalog)}):
            catalog.write_text(json.dumps([reference]), encoding="utf-8")
            with TestClient(create_app(path)) as api:
                self.assertEqual(api.get(url).raise_for_status().json(), {"references": [reference]})
            catalog.write_text(json.dumps([reference, reference]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate medication"):
                with TestClient(create_app(path)):
                    pass

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
