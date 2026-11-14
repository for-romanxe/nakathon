from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app


class CrewAccessTest(TestCase):
    def test_cmo_can_read_but_cannot_modify_and_opt_out_survives_restart(self):
        directory = self.enterContext(TemporaryDirectory())
        path = Path(directory) / "demo.sqlite3"
        cmo = {"X-Demo-Viewer": "c2"}
        other = {"X-Demo-Viewer": "c3"}
        with TestClient(create_app(path)) as api:
            report = api.post("/crew/c1/symptom", json={"text": "Chest pain", "lang": "en"}).raise_for_status().json()
            url = f"/events/{report['event_id']}"
            seq = api.get("/tx", headers=cmo).raise_for_status().json()[0]["seq"]
            self.assertEqual(api.get("/crew", headers=other).status_code, 403)
            self.assertEqual(api.get("/crew/c1/today", headers=other).status_code, 403)
            self.assertEqual(api.get(url, headers=other).status_code, 403)
            self.assertEqual(api.get(f"{url}/stream?demo_viewer=c3").status_code, 403)
            self.assertEqual(api.get(f"{url}/stream?demo_viewer=c1", headers=other).status_code, 400)
            self.assertEqual(api.get(f"{url}/stream?demo_viewer=c1").status_code, 200)
            self.assertEqual(api.get(f"{url}/stream?demo_viewer=C2", headers=cmo).status_code, 200)
            self.assertEqual(api.get("/tx", headers=other).status_code, 403)
            self.assertEqual(api.get(url, headers=cmo).status_code, 200)
            self.assertEqual(api.post(f"{url}/share", headers=cmo).status_code, 403)
            self.assertEqual(api.post(f"{url}/override", headers=cmo, json={"reason": "other"}).status_code, 403)
            api.post(f"{url}/share").raise_for_status()
            roster = api.get("/crew", headers=cmo).raise_for_status().json()
            self.assertEqual(roster[0]["shared_event_ids"], [report["event_id"]])
            api.put("/settings", json={"cmo_access": False}).raise_for_status()
        with TestClient(create_app(path)) as api:
            self.assertFalse(api.get("/settings").raise_for_status().json()["cmo_access"])
            self.assertEqual(api.get("/crew/c1/today", headers=cmo).status_code, 403)
            self.assertEqual(api.get(url, headers=cmo).status_code, 403)
            self.assertEqual(api.get("/tx", headers=cmo).raise_for_status().json(), [])
            self.assertEqual(api.post(f"/tx/{seq}/simulate", headers=cmo, json={}).status_code, 404)
            api.post("/demo/clock", json={"sol": 16, "time": "08:00"}).raise_for_status()
            api.post("/tx/send", headers=cmo).raise_for_status()
            self.assertTrue(api.get(url).raise_for_status().json()["shared"])
            api.put("/settings", json={"cmo_access": True}).raise_for_status()
            packet = api.get("/tx", headers=cmo).raise_for_status().json()[0]
            self.assertEqual((packet["seq"], packet["status"]), (seq, "queued"))
