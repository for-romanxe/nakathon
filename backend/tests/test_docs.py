import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.docs import build_docs
from backend.main import create_app


class DocsTest(TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.app = create_app(self.directory / "demo.sqlite3")

    def test_empty_corpus_and_swagger(self):
        with patch.dict("os.environ", {"CREW_HEALTH_EVIDENCE": ""}), TestClient(self.app) as api:
            self.assertEqual(api.get("/docs").raise_for_status().json(), [])
            self.assertIn("text/html", api.get("/api/docs").raise_for_status().headers["content-type"])

    def test_citation_resolves_to_sorted_source_paragraphs(self):
        path = self.directory / "evidence.json"
        base = {"codes": ["dizziness"], "condition_id": "orthostatic_intolerance"}
        rows = [
            {**base, "id": "test:example#p10", "text": "Synthetic tenth paragraph.", "title": "Test source", "lang": "en"},
            {**base, "id": "test:example#p2", "text": "Synthetic second paragraph.", "org": "Test organization", "lang": "en"},
            {**base, "id": "test:legacy#p1", "text": "Synthetic legacy paragraph."},
        ]
        path.write_text(json.dumps(rows), encoding="utf-8")
        with patch.dict("os.environ", {"CREW_HEALTH_EVIDENCE": str(path)}), TestClient(self.app) as api:
            expected = {
                "id": "test:example", "title": "Test source", "org": "Test organization", "kind": "", "lang": "en",
                "paragraphs": [{"n": 2, "text": rows[1]["text"], "lang": "en"},
                               {"n": 10, "text": rows[0]["text"], "lang": "en"}],
            }
            self.assertEqual(api.get("/docs").raise_for_status().json()[0], expected)
            self.assertEqual(api.get("/docs/test%3Aexample").raise_for_status().json(), expected)
            legacy = api.get("/docs/test%3Alegacy").raise_for_status().json()
            self.assertEqual(legacy["title"], "test:legacy")
            self.assertNotIn("lang", legacy)
            self.assertEqual(legacy["paragraphs"], [{"n": 1, "text": rows[2]["text"]}])
            missing = api.get("/docs/test%3Amissing")
            self.assertEqual((missing.status_code, missing.json()["error"]["code"]), (404, "doc_not_found"))
        with self.assertRaisesRegex(ValueError, "Conflicting title"):
            build_docs([*rows, {**base, "id": "test:example#p3", "text": "Other", "title": "Different"}])
