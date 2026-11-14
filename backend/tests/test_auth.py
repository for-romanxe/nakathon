import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import create_app


class AuthTest(TestCase):
    def test_login_disables_demo_impersonation_and_logout_revokes_cookie(self):
        directory = self.enterContext(TemporaryDirectory())
        codes = {f"c{i}": f"test-only-access-code-{i}" for i in range(1, 5)}
        self.enterContext(patch.dict("os.environ", {"CREW_HEALTH_ACCESS_CODES": json.dumps(codes)}))
        with TestClient(create_app(Path(directory) / "demo.sqlite3")) as api:
            spoof = {"X-Demo-Viewer": "c2"}
            self.assertEqual(api.get("/crew", headers=spoof).status_code, 401)
            self.assertEqual(api.post("/demo/viewer/c2").status_code, 403)
            credentials = {"crew_id": "c1", "access_code": codes["c1"]}
            self.assertEqual(api.post("/session/login", json=credentials, headers={"Origin": "https://other.test"}).status_code, 403)
            self.assertEqual(api.post("/session/login", json=dict(credentials, access_code="wrong")).status_code, 401)
            response = api.post("/session/login", json=credentials).raise_for_status()
            self.assertIn("httponly", response.headers["set-cookie"].lower())
            self.assertEqual(api.get("/crew/c1/today").status_code, 200)
            self.assertEqual(api.get("/crew", headers=spoof).status_code, 403)
            report = api.post("/crew/c1/symptom", json={"text": "Chest pain", "lang": "en"}).raise_for_status().json()
            self.assertEqual(api.get(f"/events/{report['event_id']}/stream?demo_viewer=c2").status_code, 200)
            old_token = api.cookies["crew_session"]
            api.post("/session/logout").raise_for_status()
            self.assertEqual(api.get("/crew/c1/today", headers={"Cookie": f"crew_session={old_token}"}).status_code, 401)
