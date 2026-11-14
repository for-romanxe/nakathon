from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.seed import CONTRACT

OWNER = {"X-Demo-Viewer": "c1"}
CMO = {"X-Demo-Viewer": "c2"}
OTHER = {"X-Demo-Viewer": "c3"}
URL = "/crew/c1/preflight"


class PreflightTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.client = self.enterContext(TestClient(create_app(Path(directory) / "test.db")))
        self.metrics = sorted(CONTRACT["metrics"])
        self.metric = self.metrics[0]

    def put(self, values, headers=OWNER):
        return self.client.put(URL, json={"values": values}, headers=headers)

    def get(self, headers=OWNER):
        return self.client.get(URL, headers=headers)

    def test_own_write_persists_as_manual(self):
        res = self.put({self.metric: 42.5})
        self.assertEqual(res.status_code, 200)
        expected = {"value": 42.5, "source": "manual"}
        self.assertEqual(res.json()["values"][self.metric], expected)
        self.assertEqual(self.get().json()["values"][self.metric], expected)

    def test_partial_upsert_keeps_other_metrics(self):
        if len(self.metrics) < 2:
            self.skipTest("needs two metrics")
        self.assertEqual(self.put({self.metrics[0]: 1}).status_code, 200)
        self.assertEqual(self.put({self.metrics[1]: 2}).status_code, 200)
        values = self.get().json()["values"]
        self.assertEqual(values[self.metrics[0]]["value"], 1)
        self.assertEqual(values[self.metrics[1]]["value"], 2)

    def test_cmo_can_read_but_not_write(self):
        self.put({self.metric: 10})
        res = self.get(CMO)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["values"][self.metric]["value"], 10)
        self.assertEqual(self.put({self.metric: 99}, CMO).status_code, 403)
        self.assertEqual(self.get().json()["values"][self.metric]["value"], 10)

    def test_ordinary_crew_denied(self):
        self.assertEqual(self.get(OTHER).status_code, 403)
        self.assertEqual(self.put({self.metric: 5}, OTHER).status_code, 403)

    def test_opt_out_blocks_cmo_read(self):
        res = self.client.put("/settings", json={"cmo_access": False}, headers=OWNER)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.get(CMO).status_code, 403)
        self.assertEqual(self.get().status_code, 200)

    def test_invalid_payloads_rejected_without_partial_writes(self):
        self.put({self.metric: 7})
        bad = [
            {},
            {self.metric: True},
            {self.metric: "7"},
            {self.metric: -1},
            {"not_a_metric": 1},
            {self.metric: 8, "not_a_metric": 1},
        ]
        for values in bad:
            with self.subTest(values=values):
                self.assertEqual(self.put(values).status_code, 422)
        self.assertEqual(self.client.put(URL, json={}, headers=OWNER).status_code, 422)
        self.assertEqual(self.get().json()["values"][self.metric], {"value": 7, "source": "manual"})

    def test_trends_preflight_matches_and_baseline_unchanged(self):
        trends_url = f"/crew/c1/trends?metric={self.metric}"
        before = self.client.get(trends_url, headers=OWNER)
        self.assertEqual(before.status_code, 200)
        self.assertEqual(self.put({self.metric: 33.3}).status_code, 200)
        after = self.client.get(trends_url, headers=OWNER).json()
        stored = self.get().json()["values"][self.metric]
        self.assertEqual(after["preflight"], stored)
        self.assertEqual(after["preflight"], {"value": 33.3, "source": "manual"})
        before_rest = {k: v for k, v in before.json().items() if k != "preflight"}
        after_rest = {k: v for k, v in after.items() if k != "preflight"}
        self.assertEqual(before_rest, after_rest)
