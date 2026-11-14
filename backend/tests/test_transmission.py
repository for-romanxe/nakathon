from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app


class TransmissionTest(TestCase):
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
            missing, = client.post(receipt_path, json={"status": "missing", "attempt": 1}).json()
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
