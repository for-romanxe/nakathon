import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app


ROOT = Path(__file__).resolve().parents[2]


def seed_demo(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "backend.seed", str(path), "--mission-demo"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )


def metric(payload: dict, name: str) -> dict:
    return next(item for item in payload["metrics"] if item["metric"] == name)


def today_at(client: TestClient, crew: str, sol: int, time: str = "08:00") -> dict:
    client.post("/demo/clock", json={"sol": sol, "time": time},
                headers={"X-Demo-Viewer": "c2"}).raise_for_status()
    return client.get(f"/crew/{crew}/today", headers={"X-Demo-Viewer": crew}).raise_for_status().json()


class MissionDemoSeedTest(TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))

    def demo_path(self, name: str = "demo.sqlite3") -> Path:
        path = self.directory / name
        result = seed_demo(path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(path.exists())
        return path

    def assert_scenario(self, client: TestClient):
        sol16 = today_at(client, "c1", 16)
        self.assertAlmostEqual(metric(sol16, "sleep")["value"], 5.1, places=2)
        self.assertAlmostEqual(metric(sol16, "hrv")["z"], -2.5, places=1)

        sol17 = today_at(client, "c1", 17)
        sleep = metric(sol17, "sleep")
        self.assertAlmostEqual(sleep["value"], 7.2, places=2)
        self.assertGreaterEqual(sleep["z"], -1)
        self.assertAlmostEqual(metric(sol17, "hrv")["z"], -0.6, delta=0.2)

        sol46 = today_at(client, "c4", 46)
        self.assertTrue(all(item["value"] is not None for item in sol46["metrics"]))
        return sol46

    def test_fresh_paths_are_populated_equivalently(self):
        first, second = self.demo_path("first.sqlite3"), self.demo_path("second.sqlite3")
        snapshots = []
        for path in (first, second):
            with TestClient(create_app(path)) as client:
                self.assert_scenario(client)
                snapshots.append([today_at(client, crew, sol)
                                  for crew, sol in (("c1", 16), ("c1", 17), ("c4", 46))])
        self.assertEqual(*snapshots)

    def test_default_app_uses_separate_database(self):
        self.demo_path()
        with TestClient(create_app(self.directory / "default.sqlite3")) as client:
            sol16 = today_at(client, "c1", 16)
            self.assertNotAlmostEqual(metric(sol16, "sleep")["value"] or 0, 5.1, places=2)
            self.assertEqual(today_at(client, "c4", 46)["events"], [])

    def test_existing_path_is_rejected(self):
        path = self.directory / "existing.sqlite3"
        with TestClient(create_app(path)):
            pass
        before = path.read_bytes()
        result = seed_demo(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_existing_directory_file_or_sidecar_is_rejected(self):
        directory = self.directory / "dir.sqlite3"
        directory.mkdir()
        plain = self.directory / "plain.sqlite3"
        plain.write_bytes(b"keep")
        sidecar_target = self.directory / "sidecar.sqlite3"
        sidecar = self.directory / "sidecar.sqlite3-wal"
        sidecar.write_bytes(b"wal")
        for path in (directory, plain, sidecar_target):
            with self.subTest(path=path.name):
                result = seed_demo(path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("refusing to overwrite existing path", result.stderr)
        self.assertTrue(directory.is_dir())
        self.assertEqual(list(directory.iterdir()), [])
        self.assertEqual(plain.read_bytes(), b"keep")
        self.assertFalse(sidecar_target.exists())
        self.assertEqual(sidecar.read_bytes(), b"wal")

    def test_startup_and_restart_keep_scenario_and_live_event(self):
        path = self.demo_path()
        with TestClient(create_app(path)) as client:
            sol46 = self.assert_scenario(client)
            self.assertEqual(sol46["events"], [])
            event = client.post("/crew/c4/symptom", headers={"X-Demo-Viewer": "c4"},
                                json={"text": "I have chest pain", "lang": "en"}).raise_for_status().json()
            self.assertIs(event["urgent"], True)
            live = today_at(client, "c4", 46)
            self.assertEqual(live["status"]["level"], "warning")
            self.assertEqual(len(live["events"]), 1)

        with TestClient(create_app(path)) as client:
            restarted = self.assert_scenario(client)
            self.assertEqual(restarted["events"], live["events"])
            self.assertEqual(restarted["status"], live["status"])
