import json
import os
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.db import EVENT_SCHEMA, INITIAL_SCHEMA, TRANSMISSION_SCHEMA, connect
from backend.main import create_app
from backend.model import client as model
from backend.seed import seed


def stages(response):
    return [json.loads(line[6:])["stage"] for line in response.raise_for_status().text.splitlines() if line]


class EventFlowTest(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.db = self.root / "demo.sqlite3"
        self.enterContext(patch.dict(os.environ, {"MODEL": "mock", "MOCK_DELAY": "0", "CREW_HEALTH_EVIDENCE": ""}))

    def test_warning_bypasses_model_and_does_not_leak_to_next_report(self):
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api:
            with patch.object(model, "extract_symptoms", side_effect=AssertionError("unexpected inference")):
                report = api.post("/crew/c2/symptom", json={"text": "동료가 의식이 없어요", "lang": "ko"}).json()
                url = f"/events/{report['event_id']}"
                self.assertTrue(report["urgent"])
                self.assertFalse(report["needs_question"])
                self.assertEqual(stages(api.get(f"{url}/stream")), ["collect", "rules", "done"])
                warning = api.get(url).json()
                self.assertEqual((warning["level"], warning["codes"], warning["runs"]), ("warning", [], []))
                self.assertEqual(len(api.get("/tx").json()), 1)
            report = api.post("/crew/c2/symptom", json={"text": "I have a headache", "lang": "en"}).json()
            later = api.get(f"/events/{report['event_id']}").json()
            self.assertEqual((later["level"], later["urgent"], later["codes"]), ("normal", False, ["headache"]))
            self.assertEqual(api.get("/crew/c2/today").json()["status"]["level"], "warning")

    def test_urgent_phrase_variants_bypass_model(self):
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api:
            with patch.object(model, "extract_symptoms", side_effect=AssertionError("unexpected inference")):
                for text, lang, code in (
                    ("죽고 싶어요", "ko", "crisis"),
                    ("죽고싶어", "ko", "crisis"),
                    ("다 끝내고 싶어요", "ko", "crisis"),
                    ("I want to end it all", "en", "crisis"),
                    ("가슴통증", "ko", "chest_pain"),
                    ("가슴이아파요", "ko", "chest_pain"),
                    ("숨을못쉬어요", "ko", "shortness_of_breath"),
                    ("숨이 안 쉬어져요", "ko", "shortness_of_breath"),
                ):
                    with self.subTest(text=text):
                        payload = {"text": text, "lang": lang}
                        report = api.post("/crew/c2/symptom", json=payload).raise_for_status().json()
                        event = api.get(f"/events/{report['event_id']}").raise_for_status().json()
                        self.assertTrue(report["urgent"])
                        self.assertFalse(report["needs_question"])
                        self.assertEqual((event["level"], event["codes"]), ("warning", [code]))
                self.assertEqual(len(api.get("/tx").raise_for_status().json()), 8)

    def test_question_survives_restart_and_missing_evidence_blocks_generation(self):
        with TestClient(create_app(self.db)) as api:
            report = api.post("/crew/c1/symptom", json={"text": "I feel dizzy", "lang": "en"}).json()
            url = f"/events/{report['event_id']}"
            self.assertTrue(report["needs_question"])
            self.assertIn("stand", report["question"])
            self.assertEqual(api.get(f"{url}/stream").status_code, 409)
        with TestClient(create_app(self.db)) as api, patch.object(model, "explain") as explain:
            self.assertEqual(api.post(f"{url}/answer", json={"answer": "yes"}).status_code, 202)
            self.assertEqual(api.post(f"{url}/answer", json={"answer": "yes"}).status_code, 202)
            self.assertEqual(api.post(f"{url}/answer", json={"answer": "no"}).status_code, 409)
            self.assertEqual(stages(api.get(f"{url}/stream")), ["collect", "rules", "symptom", "question", "retrieve", "hold"])
            explain.assert_not_called()
            event = api.get(url).json()
            self.assertEqual((event["answer"], event["hold_reason"], event["level"]), ("yes", "no_matching_evidence", "caution"))
            self.assertIsNone(event["explanation"])
            self.assertIsNone(event["risk"])

    def test_reading_warning_bypasses_model_but_is_not_urgent_symptom(self):
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api, closing(connect(self.db)) as db:
            with db:
                db.execute("UPDATE sample SET value = 95 WHERE crew_id = 'c2' AND metric = 'hr' AND mission_day = 16")
            with patch.object(model, "extract_symptoms", side_effect=AssertionError("unexpected inference")):
                report = api.post("/crew/c2/symptom", json={"text": "Headache", "lang": "en"}).raise_for_status().json()
            event = api.get(f"/events/{report['event_id']}").raise_for_status().json()
            self.assertEqual((event["urgent"], event["level"], event["title"]), (False, "warning", "Symptom report"))
            api.post(f"/events/{event['id']}/override", json={"reason": "wear_fault"}).raise_for_status()
            self.assertEqual(api.get("/crew/c2/today").raise_for_status().json()["status"]["level"], "warning")

    def test_warning_override_preserves_history_and_queued_packet(self):
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api:
            report = api.post("/crew/c2/symptom", json={"text": "Chest pain", "lang": "en"}).raise_for_status().json()
            url = f"/events/{report['event_id']}"
            self.assertEqual(api.post(f"{url}/close").status_code, 409)
            self.assertEqual(api.post(f"{url}/override", json={"reason": "invalid"}).status_code, 422)
            before = api.get("/tx").raise_for_status().json()
            self.assertTrue(api.post(f"{url}/share").raise_for_status().json()["shared"])
            body = {"reason": "action_done", "note": "Synthetic scenario completed."}
            closed = api.post(f"{url}/override", json=body).raise_for_status().json()
            self.assertEqual(api.post(f"{url}/override", json=body).json(), closed)
            self.assertEqual(api.post(f"{url}/override", json={"reason": "other"}).status_code, 409)
            self.assertEqual(api.get("/tx").json(), before)
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api:
            self.assertEqual(api.get(url).raise_for_status().json(), closed)
            self.assertEqual((closed["status"], closed["level"], closed["closed_reason"]), ("closed", "warning", "action_done"))
            self.assertEqual(closed["override"]["note"], body["note"])
            current = api.get("/crew/c2/today").raise_for_status().json()
            self.assertEqual(current["status"]["level"], "normal")
            self.assertEqual(current["events"], [closed])

    def test_non_warning_can_close_without_an_override(self):
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api:
            report = api.post("/crew/c2/symptom", json={"text": "I feel nauseous", "lang": "en"}).raise_for_status().json()
            url = f"/events/{report['event_id']}"
            event = api.post(f"{url}/close").raise_for_status().json()
            self.assertEqual((event["status"], event["closed_reason"], event["override"]), ("closed", "resolved", None))
            self.assertEqual(api.post(f"{url}/close").json(), event)
            self.assertEqual(api.post("/events/999/share").status_code, 404)

    def test_upgrade_keeps_warning_event_and_packet(self):
        with closing(connect(self.db)) as db:
            for schema in (INITIAL_SCHEMA, EVENT_SCHEMA, TRANSMISSION_SCHEMA):
                db.executescript(schema.read_text(encoding="utf-8"))
            seed(db)
            with db:
                db.execute("INSERT INTO event VALUES (1, 'c2', 16, '2026-11-14T06:12:00', 'en', "
                           "'I have chest pain', '[\"chest_pain\"]', 'warning', '[]')")
                db.execute("INSERT INTO tx_packet (event_id, kind, mission_day, priority, payload, hash) "
                           "VALUES (1, 'event', 16, 'warning', '{}', ?)", ("0" * 64,))
        with TestClient(create_app(self.db), headers={"X-Demo-Viewer": "c2"}) as api:
            self.assertTrue(api.get("/events/1").raise_for_status().json()["urgent"])
            self.assertEqual(stages(api.get("/events/1/stream")), ["collect", "rules", "done"])
            self.assertEqual(api.get("/tx").raise_for_status().json()[0]["event_id"], 1)

    def test_verified_retry_history_is_persisted_and_stream_replays(self):
        evidence = self.root / "evidence.json"
        cited = {
            "id": "test:standing#p1", "text": "Synthetic paragraph for verification tests.",
            "codes": ["dizziness"], "condition_id": "orthostatic_intolerance",
            "action_text": "Complete the synthetic exercise.",
        }
        uncited = dict(cited, id="test:standing#p2", action_text="Do not display this test action.")
        evidence.write_text(json.dumps([cited, uncited]), encoding="utf-8")
        os.environ["CREW_HEALTH_EVIDENCE"] = str(evidence)
        verified = {"category": "cardiovascular", "condition_id": "orthostatic_intolerance",
                    "lines": ["The report describes dizziness after standing."], "cites": ["test:standing#p1"]}
        bad_cite = dict(verified, cites=["test:missing#p1"])
        with TestClient(create_app(self.db)) as api, patch.object(model, "explain", side_effect=[bad_cite, verified]) as explain:
            report = api.post("/crew/c1/symptom", json={"text": "I feel dizzy", "lang": "en"}).json()
            url = f"/events/{report['event_id']}"
            api.post(f"{url}/answer", json={"answer": "yes"}).raise_for_status()
            expected = ["collect", "rules", "symptom", "question", "retrieve", "generate", "verify", "done"]
            self.assertEqual(stages(api.get(f"{url}/stream")), expected)
            self.assertEqual(stages(api.get(f"{url}/stream")), expected)
            self.assertEqual(explain.call_count, 2)
        with TestClient(create_app(self.db)) as api:
            event = api.get(url).json()
            self.assertEqual(event["explanation"], verified)
            self.assertEqual(event["verified"], 5)
            self.assertEqual([run["fails"] for run in event["runs"]], [["cites"], []])
            actions = [{"text": cited["action_text"], "doc": cited["id"], "done": False}]
            self.assertEqual(event["risk"]["actions"], actions)
            self.assertEqual(api.post(f"{url}/action/1/done").status_code, 404)
            self.assertEqual(api.post(f"{url}/action/0/done", headers={"X-Demo-Viewer": "c2"}).status_code, 403)
            completed = api.post(f"{url}/action/0/done").raise_for_status().json()
            self.assertEqual(completed["risk"]["actions"], [dict(actions[0], done=True)])
            self.assertEqual(api.post(f"{url}/action/0/done").json(), completed)
        with TestClient(create_app(self.db)) as api:
            self.assertEqual(api.get(url).raise_for_status().json(), completed)
