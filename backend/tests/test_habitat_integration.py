import os
import sqlite3
import subprocess
from contextlib import closing
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from fastapi.testclient import TestClient

from backend.habitat import FIXED
from backend.main import create_app, habitat_fallback_evidence
from backend.mission import ClockUpdate, DEMO_TIME

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
            self.assertEqual(actions(client), [])
            set_clock(client, 17)
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
            set_clock(client, 17)
            self.assertEqual(actions(client, 16), final)
            for later_sol in (40, 46):
                set_clock(client, later_sol)
                self.assertEqual(actions(client), [])

    def test_undo_lighting(self):
        path = self.demo_path()
        with TestClient(create_app(path)) as client:
            set_clock(client, 16, '09:00')
            lid = one(actions(client, 16), 'lighting')['id']
            r = client.post(f'/habitat/actions/{lid}/undo', headers=C1, json={'reason': 'too dim'})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(client.post(f'/habitat/actions/{lid}/undo', headers=C1).status_code, 409)

    def test_connected_proposal_auto_applies_when_delayed(self):
        path = self.demo_path()
        start = ClockUpdate(sol=16, time='08:00').apply(DEMO_TIME)
        with mock.patch('backend.main.DEMO_TIME', start), TestClient(create_app(path)) as client:
            set_clock(client, 16, '08:00')
            items = actions(client, 16)
            lighting = one(items, 'lighting')
            self.assertEqual(lighting['status'], 'proposed')
            self.assertIs(lighting['auto'], False)
            sid = one(items, 'schedule')['id']
            self.assertEqual(lighting['before_values'], FIXED['lighting'][0])
            self.assertEqual(lighting['after_values'], FIXED['lighting'][1])
            changed = ({'amber': None, 'off': '23:30'}, {'amber': '20:30', 'off': '21:30'})
            with mock.patch.dict(FIXED, {'lighting': changed}):
                set_clock(client, 16, '09:00')
            items = actions(client, 16)
            after = one(items, 'lighting')
            self.assertEqual(after['id'], lighting['id'])
            self.assertEqual(after['before_values'], changed[0])
            self.assertEqual(after['after_values'], changed[1])
            self.assertEqual(after['after'], 'Amber light 20:30 · Lights off 21:30')
            self.assertIsInstance(after['trigger'], dict)
            self.assertEqual(after['status'], 'applied')
            self.assertIs(after['auto'], True)
            self.assertTrue(after['applied_at'])
            schedule = one(items, 'schedule')
            self.assertEqual(schedule['id'], sid)
            self.assertEqual(schedule['status'], 'proposed')
            self.assertTrue(schedule['after'].startswith('EVA') or 'EVA' in schedule['after'])
            self.assertIn('EVA', one(actions(client, 16, 'ko'), 'schedule')['after'])

    def test_sol17_low_sleep_blocks_schedule_release(self):
        path = self.demo_path()
        with TestClient(create_app(path)) as client:
            set_clock(client, 16, '09:00')
            aid = one(actions(client, 16), 'schedule')['id']
            self.assertEqual(client.post(f'/habitat/actions/{aid}/approve', headers=C1).status_code, 200)
            with closing(sqlite3.connect(path)) as db:
                with db:
                    cur = db.execute("UPDATE sample SET value=? WHERE crew_id='c1' AND source_key='c1:sleep:17'", (4.0,))
                    self.assertEqual(cur.rowcount, 1)
            set_clock(client, 17)
            schedule = one(actions(client, 16), 'schedule')
            self.assertEqual(schedule['status'], 'applied')
            self.assertIsNone(schedule['released_at'])
            outcome = schedule['outcome']
            self.assertIs(outcome['rule_satisfied'], False)
            self.assertIs(outcome['released'], False)
            ms = {m['metric']: m for m in outcome['metrics']}
            self.assertGreater(ms['hrv']['after_z'], -1)
            self.assertLess(ms['sleep']['after_z'], -1)

    def test_fallback_evidence_ignores_nonstandard_items(self):
        bundled = [{'id': 'a#p1', 'text': 't'}]
        with mock.patch.dict(os.environ), \
                mock.patch('ml.knowledge.export_evidence.export', return_value=bundled), \
                mock.patch('backend.main.habitat_cite_ids', return_value={'lighting': ('a#p1',)}):
            os.environ.pop('CREW_HEALTH_EVIDENCE', None)
            odd = [None, 'x', [], {'id': []}]
            self.assertEqual(habitat_fallback_evidence(odd), [*odd, *bundled])
            self.assertEqual(habitat_fallback_evidence([]), bundled)

    def test_clock_sync_failure_keeps_state(self):
        path = self.demo_path()
        with TestClient(create_app(path)) as client:
            set_clock(client, 16, '09:00')
            before = actions(client, 16)
            mission = client.get('/mission').json()

            def broken(connection, now, cite_ids):
                connection.execute('DELETE FROM habitat_action WHERE id=?', (before[0]['id'],))
                raise sqlite3.OperationalError('disk I/O error')

            with mock.patch('backend.habitat.sync', side_effect=broken):
                r = client.post('/demo/clock', json={'sol': 17, 'time': '08:00'}, headers=C2)
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.json()['error']['code'], 'clock_sync_failed')
            self.assertEqual(client.get('/mission').json(), mission)
            self.assertEqual(actions(client, 16), before)

    def test_default_database_has_no_actions(self):
        with TestClient(create_app(self.directory / 'default.sqlite3')) as client:
            for sol in (16, 17):
                set_clock(client, sol)
                self.assertEqual(actions(client), [])
            self.assertEqual(client.post('/habitat/actions/1/undo', headers=C1).status_code, 404)

    def test_mission_demo_cites_served_paragraphs(self):
        import os
        from unittest.mock import patch
        path = self.demo_path()
        with patch.dict(os.environ):
            os.environ.pop('CREW_HEALTH_EVIDENCE', None)
            with TestClient(create_app(path)) as client:
                set_clock(client, 16, '09:00')
                cards = actions(client, 16)
                r = client.get('/docs', headers=C1)
                r.raise_for_status()
                served = {f"{doc['id']}#p{p['n']}" for doc in r.json() for p in doc['paragraphs']}
        cited = [cite for card in cards for cite in card['cite_ids']]
        self.assertTrue(cited)
        for cite in cited:
            self.assertIn(cite, served)
