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

    def test_history_keeps_latest_fifty_at_same_mission_time_after_backup(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        path = root / "crew.sqlite3"
        restored = root / "restored.sqlite3"
        url = "/crew/c1/medication-intakes"
        with TestClient(create_app(path)) as api:
            entries = [
                api.post(url, json={
                    "request_id": str(uuid4()), "name": f"Test item {index}", "amount": "1 test unit",
                }).raise_for_status().json()
                for index in range(51)
            ]
            self.assertEqual(len({entry["ts"] for entry in entries}), 1)
        with closing(connect(path)) as source, closing(connect(restored)) as target:
            source.backup(target)
        with TestClient(create_app(restored)) as api:
            history = api.get(url).raise_for_status().json()["entries"]
        self.assertEqual(history, entries[:0:-1])

    def test_history_ends_read_transaction_with_rollback(self):
        path = Path(self.enterContext(TemporaryDirectory())) / "crew.sqlite3"
        statements = []

        def traced_connect(db_path):
            connection = connect(db_path)
            connection.set_trace_callback(statements.append)
            return connection

        with TestClient(create_app(path)) as api, patch("backend.main.connect", side_effect=traced_connect):
            for crew, viewer, status in (("c1", "c1", 200), ("c1", "c3", 403), ("unknown", "c1", 404)):
                with self.subTest(status=status):
                    statements.clear()
                    response = api.get(f"/crew/{crew}/medication-intakes", headers={"X-Demo-Viewer": viewer})
                    self.assertEqual(response.status_code, status)
                    transactions = [sql for sql in statements if sql in ("BEGIN", "COMMIT", "ROLLBACK")]
                    self.assertEqual(transactions, ["BEGIN", "ROLLBACK"])

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
            self.assertEqual(api.get("/crew/unknown/medication-intakes").status_code, 404)
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
