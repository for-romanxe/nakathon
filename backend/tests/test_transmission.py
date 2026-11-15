from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.db import connect
from backend.main import create_app


class TransmissionTest(TestCase):
    def test_mission_reports_blackout_and_window_boundaries(self):
        directory = self.enterContext(TemporaryDirectory())
        path = Path(directory) / "demo.sqlite3"
        with TestClient(create_app(path), headers={"X-Demo-Viewer": "c2"}) as client:
            cases = (
                (42, "20:00", "connected", 0, 57, "08:00"),
                (42, "23:59", "delayed", 0, 57, "08:00"),
                (43, "00:00", "blackout", 14, 57, "08:00"),
                (43, "08:00", "blackout", 14, 57, "08:00"),
                (56, "23:59", "blackout", 1, 57, "08:00"),
                (57, "00:00", "delayed", 0, 57, "08:00"),
                (57, "08:00", "connected", 0, 57, "20:00"),
                (57, "08:30", "delayed", 0, 57, "20:00"),
            )
            for sol, time, state, remaining, next_sol, next_time in cases:
                with self.subTest(sol=sol, time=time):
                    mission = client.post("/demo/clock", json={"sol": sol, "time": time}).raise_for_status().json()
                    self.assertEqual(client.get("/mission").json(), mission)
                    self.assertEqual(mission["comms_state"], state)
                    self.assertEqual((mission["blackout_start_sol"], mission["blackout_end_sol"]), (43, 57))
                    self.assertEqual(mission["blackout_days_remaining"], remaining)
                    self.assertEqual(mission["next_window_at"], {"sol": next_sol, "time": next_time})
                    # Sol 43 08:00 has a nominal 20:00 opening, but blackout moves it.
                    self.assertEqual(mission["next_window"], next_time)
                    self.assertIs(mission["simulation"], True)

    def test_blackout_blocks_dispatch_until_the_first_recovery_window(self):
        directory = self.enterContext(TemporaryDirectory())
        path = Path(directory) / "demo.sqlite3"
        with TestClient(create_app(path), headers={"X-Demo-Viewer": "c2"}) as client:
            client.post("/demo/clock", json={"sol": 46, "time": "08:00"}).raise_for_status()
            c4 = {"X-Demo-Viewer": "c4"}
            event = client.post("/crew/c4/symptom", headers=c4,
                                json={"text": "I have chest pain", "lang": "en"}).raise_for_status().json()
            self.assertIs(event["urgent"], True)
            event_id = event["event_id"]
            packet, = client.get("/tx").raise_for_status().json()
            self.assertEqual(packet["priority"], "warning")
            self.assertEqual((packet["status"], packet["attempts"]), ("queued", 0))
            self.assertEqual(client.post("/tx/send").raise_for_status().json(), [packet])
            self.assertEqual(client.post("/tx/send", json={"event_id": event_id}).raise_for_status().json(), [packet])
            denied = client.post("/tx/send", headers=c4)
            self.assertEqual(denied.status_code, 403)
            self.assertEqual(denied.json(), {
                "error": {"code": "forbidden", "message": "Medical officer access required."},
            })

            client.post("/demo/clock", json={"sol": 57, "time": "07:59"}).raise_for_status()
            self.assertEqual(client.post("/tx/send").raise_for_status().json(), [packet])
            client.post("/demo/clock", json={"sol": 57, "time": "08:00"}).raise_for_status()
            sent, = client.post("/tx/send").raise_for_status().json()
            self.assertEqual((sent["seq"], sent["hash"]), (packet["seq"], packet["hash"]))
            self.assertEqual((sent["status"], sent["attempts"]), ("sent", 1))

    def test_signal_comparison_uses_the_same_packet_and_noise(self):
        directory = self.enterContext(TemporaryDirectory())
        path = Path(directory) / "demo.sqlite3"
        with TestClient(create_app(path), headers={"X-Demo-Viewer": "c2"}) as client:
            client.post("/crew/c2/symptom", json={"text": "I have chest pain", "lang": "en"}).raise_for_status()
            packet, = client.get("/tx").json()
            route = f"/tx/{packet['seq']}/simulate"
            result = client.post(route, json={}).raise_for_status().json()
            self.assertEqual(result, client.post(route, json={}).json())
            self.assertLess(result["wide"]["bit_errors"], result["narrow"]["bit_errors"])
            self.assertGreater(result["wide"]["packet_success_rate"], result["narrow"]["packet_success_rate"])
            self.assertEqual(result["wide"]["relative_energy_per_bit"], 9.0)

            noiseless = client.post(route, json={"noise_sd": 0, "trials": 2}).raise_for_status().json()
            self.assertEqual(noiseless["narrow"]["packet_success_rate"], 1.0)
            self.assertEqual(noiseless["wide"]["bit_error_rate"], 0.0)
            self.assertEqual(client.post(route, json={"wide_amplitude": 1}).status_code, 422)
            self.assertEqual(client.post("/tx/999/simulate", json={}).status_code, 404)
            self.assertEqual(client.get("/tx").json(), [packet])

    def test_warning_summary_retry_and_receipt(self):
        directory = self.enterContext(TemporaryDirectory())
        path = Path(directory) / "demo.sqlite3"
        with TestClient(create_app(path), headers={"X-Demo-Viewer": "c2"}) as client:
            report = client.post("/crew/c2/symptom", json={"text": "I have chest pain", "lang": "en"})
            event_id = report.raise_for_status().json()["event_id"]
            packet, = client.post("/tx", json={"event_id": event_id}).raise_for_status().json()
            seq = packet["seq"]
            self.assertEqual(packet["priority"], "warning")
            self.assertNotIn("symptom_text", packet["payload"])
            self.assertEqual(client.post("/tx/send").json(), [packet])

            client.post("/demo/clock", json={"sol": 16, "time": "08:00"}).raise_for_status()
            sent, = client.post("/tx/send").raise_for_status().json()
            self.assertEqual((sent["status"], sent["attempts"]), ("sent", 1))
            self.assertEqual(client.post("/tx/send").json(), [sent])
            receipt_path = f"/tx/{seq}/receipt"
            missing_receipt = {"status": "missing", "attempt": 1}
            missing, = client.post(receipt_path, json=missing_receipt).raise_for_status().json()
            self.assertEqual(client.get("/tx").json(), [missing])
            self.assertEqual(client.post(receipt_path, json=missing_receipt).status_code, 409)
            self.assertEqual(client.post("/tx/send").json(), [missing])

            # A persisted offset timestamp may sort before the same UTC window.
            with closing(connect(path)) as db, db:
                db.execute("UPDATE tx_packet SET window_id = ? WHERE seq = ?",
                           ("2026-11-14T07:00:00-01:00", seq))
            same_window, = client.post("/tx/send").raise_for_status().json()
            self.assertEqual((same_window["status"], same_window["attempts"]), ("missing", 1))
            with closing(connect(path)) as db, db:
                db.execute("UPDATE tx_packet SET window_id = ? WHERE seq = ?",
                           ("2026-11-14T08:00:00Z", seq))
            client.post("/demo/clock", json={"sol": 16, "time": "20:00"}).raise_for_status()
            retry, = client.post("/tx/send").raise_for_status().json()
            self.assertEqual((retry["seq"], retry["hash"], retry["attempts"]), (seq, packet["hash"], 2))
            self.assertEqual(retry["payload"], packet["payload"])
            stale = client.post(receipt_path, json={"status": "acked", "attempt": 1})
            self.assertEqual(stale.status_code, 409)
            self.assertEqual(stale.json(), {
                "error": {"code": "invalid_receipt", "message": "Receipt does not match the packet's current attempt."},
            })
            client.post("/demo/clock", json={"sol": 43, "time": "08:00"}).raise_for_status()
            ack, = client.post(receipt_path, json={"status": "acked", "attempt": 2}).raise_for_status().json()
            self.assertEqual(ack["status"], "acked")

        with TestClient(create_app(path), headers={"X-Demo-Viewer": "c2"}) as client:
            self.assertEqual(client.get("/tx").json(), [ack])
