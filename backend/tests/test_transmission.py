from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app


class TransmissionTest(TestCase):
    def test_signal_comparison_uses_the_same_packet_and_noise(self):
        directory = self.enterContext(TemporaryDirectory())
        path = Path(directory) / "demo.sqlite3"
        with TestClient(create_app(path)) as client:
            client.post("/crew/c1/symptom", json={"text": "I have chest pain", "lang": "en"}).raise_for_status()
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
        with TestClient(create_app(path)) as client:
            report = client.post("/crew/c1/symptom", json={"text": "I have chest pain", "lang": "en"})
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
            self.assertEqual(client.post(receipt_path, json=missing_receipt).status_code, 409)
            self.assertEqual(client.post("/tx/send").json(), [missing])

            client.post("/demo/clock", json={"sol": 16, "time": "20:00"}).raise_for_status()
            retry, = client.post("/tx/send").raise_for_status().json()
            self.assertEqual((retry["seq"], retry["hash"], retry["attempts"]), (seq, packet["hash"], 2))
            self.assertEqual(retry["payload"], packet["payload"])
            self.assertEqual(client.post(receipt_path, json={"status": "acked", "attempt": 1}).status_code, 409)
            ack, = client.post(receipt_path, json={"status": "acked", "attempt": 2}).raise_for_status().json()
            self.assertEqual(ack["status"], "acked")

        with TestClient(create_app(path)) as client:
            self.assertEqual(client.get("/tx").json(), [ack])
