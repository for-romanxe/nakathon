import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

from backend.main import create_app

ROOT = Path(__file__).resolve().parents[2]
C1 = {'X-Demo-Viewer': 'c1'}
C2 = {'X-Demo-Viewer': 'c2'}


def set_clock(client, sol, time='08:00'):
    client.post('/demo/clock', json={'sol': sol, 'time': time}, headers=C2).raise_for_status()


def actions(client, sol=None, lang=None):
    params = {'crew': 'c1'}
    if lang:
        params['lang'] = lang
    r = client.get('/habitat/actions', params=params, headers=C1)
    r.raise_for_status()
    body = r.json()
    assert isinstance(body, list)
    return [a for a in body if sol is None or a['sol'] == sol]


def one(items, target):
    found = [a for a in items if a['target'] == target]
    assert len(found) == 1, found
    return found[0]


class HabitatIntegrationTest(TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))

    def demo_path(self):
        path = self.directory / 'demo.sqlite3'
        result = subprocess.run([sys.executable, '-m', 'backend.seed', str(path), '--mission-demo'],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        return path

    def test_rehearsal_flow_and_restart(self):
        path = self.demo_path()
        with TestClient(create_app(path)) as client:
            set_clock(client, 16, '09:00')
            items = actions(client, 16)
            lighting = one(items, 'lighting')
            self.assertIs(lighting['auto'], True)
            self.assertTrue(lighting['applied_at'])
            schedule = one(items, 'schedule')
            self.assertEqual(schedule['status'], 'proposed')
            self.assertEqual(lighting['crew'], 'c1')
            self.assertEqual(lighting['crew_id'], 'c1')
            self.assertEqual(lighting['tier'], 'auto')
            self.assertEqual(schedule['tier'], 'approve')
            self.assertIs(schedule['auto'], False)
            for card in (lighting, schedule):
                self.assertIsInstance(card['before'], str)
                self.assertIsInstance(card['after'], str)
                self.assertIsInstance(card['before_values'], dict)
                self.assertIsInstance(card['after_values'], dict)
                self.assertIsInstance(card['cite_ids'], list)
                self.assertIsNone(card['reason_text'])
                self.assertIsNone(card['outcome'])
                self.assertEqual(set(card['reason']), {'metric', 'value', 'z'})
            self.assertEqual(lighting['reason']['metric'], 'sleep')
            self.assertEqual(schedule['reason']['metric'], 'hrv')
            self.assertEqual(lighting['after'], 'Amber light 21:00 · Lights off 22:00')
            self.assertEqual(lighting['after_values'], {'amber': '21:00', 'off': '22:00'})
            ko = one(actions(client, 16, 'ko'), 'lighting')
            self.assertEqual(ko['before'], '23:00 소등')
            self.assertEqual(ko['after'], '21:00 앰버 조명 · 22:00 소등')
            self.assertTrue(one(actions(client, 16, 'ko'), 'schedule')['after'].endswith('13:00 시작'))
            aid = schedule['id']
            self.assertEqual(client.post(f'/habitat/actions/{aid}/approve', headers=C2).status_code, 403)
            self.assertEqual(client.post('/habitat/actions/999999/approve', headers=C1).status_code, 404)
            self.assertEqual(client.post(f'/habitat/actions/{aid}/approve', headers=C1, json={'reason': 'x' * 241}).status_code, 422)
            ok = client.post(f'/habitat/actions/{aid}/approve', headers=C1, json={'reason': ' ok '})
            self.assertEqual(ok.status_code, 200)
            self.assertEqual(ok.json()['id'], aid)
            self.assertNotEqual(ok.json()['status'], 'proposed')
            self.assertEqual(client.post(f'/habitat/actions/{aid}/approve', headers=C1).status_code, 409)
            set_clock(client, 18)
            past = actions(client, 16)
            for target in ('lighting', 'schedule'):
                row = one(past, target)
                self.assertTrue(row['released_at'])
                self.assertIsNotNone(row.get('outcome'))
            outcome = one(past, 'schedule')['outcome']
            assert outcome['sol'] == 17
            assert outcome['rule_satisfied'] is True
            assert outcome['released'] is True
            assert isinstance(outcome['metrics'], list)
            ms = {m['metric']: m for m in outcome['metrics']}
            assert set(ms) == {'sleep', 'hrv'}
            for m in outcome['metrics']:
                assert set(m) == {'metric', 'before', 'before_z', 'after', 'after_z'}
                assert isinstance(m['before'], (int, float))
                assert isinstance(m['before_z'], (int, float))
            assert ms['sleep']['after'] == 7.2
            assert isinstance(ms['sleep']['after_z'], (int, float))
            assert isinstance(ms['hrv']['after'], (int, float))
            self.assertAlmostEqual(ms['hrv']['after_z'], -0.6, places=2)
            final = past
        with TestClient(create_app(path)) as client:
            self.assertEqual(actions(client, 16), final)

    def test_undo_lighting(self):
        path = self.demo_path()
        with TestClient(create_app(path)) as client:
            set_clock(client, 16, '09:00')
            lid = one(actions(client, 16), 'lighting')['id']
            r = client.post(f'/habitat/actions/{lid}/undo', headers=C1, json={'reason': 'too dim'})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(client.post(f'/habitat/actions/{lid}/undo', headers=C1).status_code, 409)

    def test_default_database_has_no_actions(self):
        with TestClient(create_app(self.directory / 'default.sqlite3')) as client:
            for sol in (16, 17):
                set_clock(client, sol)
                self.assertEqual(actions(client), [])
            self.assertEqual(client.post('/habitat/actions/1/undo', headers=C1).status_code, 404)
