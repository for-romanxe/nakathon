import json
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.db import MEDICATION_SCHEMA, connect, initialize
from backend.main import create_app
from backend.seed import seed


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

    def test_product_intake_preserves_identity_and_replays_without_catalog(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        path = root / "crew.sqlite3"
        initialize(path)
        legacy_id = str(uuid4())
        with closing(connect(path)) as db:
            seed(db)
            db.execute("DROP TABLE medication_intake")
            db.executescript(MEDICATION_SCHEMA.read_text(encoding="utf-8"))
            with db:
                db.execute(
                    """INSERT INTO medication_intake (crew_id, request_id, name, amount, ts, mission_day)
                       VALUES ('c1', ?, 'Legacy test item', 'Reported amount', '2026-11-13T06:12:00+00:00', 15)""",
                    (legacy_id,),
                )
        catalog = root / "catalog.json"
        reference = {
            "id": "synthetic-product", "product": "Synthetic product", "strength": "Test strength",
            "directions": "Synthetic reference text.", "warnings": "Synthetic warning.",
            "label_revision": "Test revision", "label_url": "https://example.org/label",
        }
        catalog.write_text(json.dumps([
            dict(reference, count_unit="test unit"), dict(reference, id="text-only"),
        ]), encoding="utf-8")
        url = "/crew/c1/medication-intakes"
        data = {"request_id": str(uuid4()), "product_id": "synthetic-product", "unit_count": 2}
        with patch.dict("os.environ", {"CREW_HEALTH_MEDICATION_REFERENCES": str(catalog)}):
            with TestClient(create_app(path)) as api:
                for invalid in (0, 1.5, True, "2"):
                    self.assertEqual(api.post(url, json={**data, "unit_count": invalid}).status_code, 422)
                self.assertEqual(api.post(url, json={**data, "product_id": "text-only"}).status_code, 422)
                saved = api.post(url, json=data).raise_for_status().json()
                self.assertEqual((saved["product_id"], saved["unit_count"]), ("synthetic-product", 2))
                self.assertEqual((saved["name"], saved["amount"]), ("Synthetic product · Test strength", "2 × test unit"))
                self.assertEqual(api.post(url, json={**data, "unit_count": 1}).status_code, 409)
                self.assertEqual(api.post(url, json={
                    "request_id": data["request_id"], "name": saved["name"], "amount": saved["amount"],
                }).status_code, 409)
        with patch.dict("os.environ", {"CREW_HEALTH_MEDICATION_REFERENCES": ""}):
            with TestClient(create_app(path)) as api:
                self.assertEqual(api.post(url, json=data).raise_for_status().json(), saved)
                self.assertEqual(api.post(url, json={**data, "request_id": str(uuid4())}).status_code, 422)
                structured, legacy = api.get(url).raise_for_status().json()["entries"]
                self.assertEqual(structured, saved)
                self.assertEqual((legacy["name"], legacy["amount"], legacy["product_id"], legacy["unit_count"]),
                                 ("Legacy test item", "Reported amount", None, None))

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

    def test_product_summary_uses_mission_clock_and_structured_records_only(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        url = "/crew/c1/medication-intakes"
        summary_url = "/crew/c1/medication-intake-summary?product_id=synthetic-product"
        reference = {
            "id": "synthetic-product", "product": "Synthetic product", "strength": "Test strength",
            "directions": "Synthetic text.", "warnings": "Synthetic warning.", "count_unit": "test unit",
            "label_revision": "Test revision", "label_url": "https://example.org/label",
        }
        catalog = root / "catalog.json"
        catalog.write_text(json.dumps([
            dict(reference, intake_limits={"minimum_interval_minutes": 120, "maximum_units_24h": 5}),
            dict(reference, id="other-product"),
        ]), encoding="utf-8")
        with patch.dict("os.environ", {"CREW_HEALTH_MEDICATION_REFERENCES": str(catalog)}):
            with TestClient(create_app(root / "db.sqlite3")) as api:
                initial = api.get(summary_url).raise_for_status().json()
                self.assertIsNone(initial["minutes_since_last"])
                self.assertIsNone(initial["limit_comparison"]["minutes_below_minimum_interval"])
                for time, sol, count in (("10:00", 15, 4), ("11:00", 15, 2), ("09:00", 16, 3), ("11:00", 16, 8)):
                    api.post("/demo/clock", json={"time": time, "sol": sol}).raise_for_status()
                    api.post(url, json={
                        "request_id": str(uuid4()), "product_id": "synthetic-product", "unit_count": count,
                    }).raise_for_status()
                api.post("/demo/clock", json={"time": "10:00", "sol": 16}).raise_for_status()
                comparison = api.get(summary_url).raise_for_status().json()["limit_comparison"]
                self.assertEqual(comparison, {
                    "status": "compared", "minutes_below_minimum_interval": 60,
                    "units_below_24h_limit": 0, "exceeds_24h_limit": False,
                })
                other = api.get(summary_url.replace("synthetic-product", "other-product")).raise_for_status().json()
                self.assertEqual(other["limit_comparison"], {"status": "hold", "reason": "no_limits"})
                api.post("/demo/clock", json={"time": "11:00", "sol": 16}).raise_for_status()
                over = api.get(summary_url).raise_for_status().json()["limit_comparison"]
                self.assertTrue(over["exceeds_24h_limit"])
                api.post("/demo/clock", json={"time": "13:00", "sol": 16}).raise_for_status()
                exact = api.get(summary_url).raise_for_status().json()["limit_comparison"]
                self.assertEqual(exact["minutes_below_minimum_interval"], 0)
                api.post("/demo/clock", json={"time": "10:00", "sol": 16}).raise_for_status()
                api.post(url, json={"request_id": str(uuid4()), "name": "Synthetic product",
                                    "amount": "Unverified text"}).raise_for_status()
                api.post(url, json={"request_id": str(uuid4()), "product_id": "other-product",
                                    "unit_count": 7}).raise_for_status()
                summary = api.get(summary_url).raise_for_status().json()
                self.assertEqual(summary, {
                    "product_id": "synthetic-product", "last_intake_at": "2026-11-14T09:00:00+00:00",
                    "minutes_since_last": 60, "recorded_units_24h": 5, "text_entries_24h": 1,
                    "limit_comparison": {"status": "hold", "reason": "unmatched_entries"},
                    "product_review": {
                        "shared_ingredients": [], "cautions": [], "unknown_product_history": True,
                        "shared_ingredient_in_limit_window": False,
                    },
                })
                self.assertEqual(api.get(summary_url, headers={"X-Demo-Viewer": "c3"}).status_code, 403)
                self.assertEqual(api.get(summary_url.replace("synthetic-product", "unknown")).status_code, 404)

    def test_product_review_reports_overlap_and_reverse_pair_caution(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        catalog = root / "catalog.json"
        base = {
            "product": "Synthetic product", "strength": "Test strength", "count_unit": "unit",
            "directions": "Synthetic text.", "warnings": "Synthetic warning.",
            "label_revision": "Test revision", "label_url": "https://example.org/label",
        }
        selected = dict(base, id="selected", active_ingredients=["test-ingredient"],
                        intake_limits={"minimum_interval_minutes": 60, "maximum_units_24h": 5},
                        pair_cautions=[{"product_id": "recorded", "lookback_minutes": 30,
                                        "text": "Synthetic forward caution."}])
        recorded = dict(base, id="recorded", active_ingredients=["test-ingredient"], pair_cautions=[
            {"product_id": "selected", "lookback_minutes": 60, "text": "Synthetic pair caution."},
        ])
        catalog.write_text(json.dumps([selected, recorded]), encoding="utf-8")
        url = "/crew/c1/medication-intake-summary?product_id=selected"
        with patch.dict("os.environ", {"CREW_HEALTH_MEDICATION_REFERENCES": str(catalog)}):
            with TestClient(create_app(root / "db.sqlite3")) as api:
                api.post("/crew/c1/medication-intakes", json={
                    "request_id": str(uuid4()), "product_id": "recorded", "unit_count": 1,
                }).raise_for_status()
                summary = api.get(url).raise_for_status().json()
                review = summary["product_review"]
                self.assertEqual(review["shared_ingredients"][0]["ingredients"], ["test-ingredient"])
                self.assertEqual({row["source_product_id"]: row["text"] for row in review["cautions"]}, {
                    "recorded": "Synthetic pair caution.", "selected": "Synthetic forward caution.",
                })
                self.assertEqual(summary["limit_comparison"], {"status": "hold", "reason": "other_products"})
                api.post("/demo/clock", json={"advance": "30m"}).raise_for_status()
                review = api.get(url).raise_for_status().json()["product_review"]
                self.assertEqual([row["source_product_id"] for row in review["cautions"]], ["recorded"])
                api.post("/demo/clock", json={"advance": "30m"}).raise_for_status()
                self.assertEqual(api.get(url).raise_for_status().json()["product_review"]["cautions"], [])
                api.post("/demo/clock", json={"advance": "23h"}).raise_for_status()
                result = api.get(url).raise_for_status().json()
                self.assertEqual(result["product_review"]["shared_ingredients"], [])
                self.assertEqual(result["limit_comparison"]["status"], "compared")

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
