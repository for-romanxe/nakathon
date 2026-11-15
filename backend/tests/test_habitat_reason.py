import json
import shutil
import subprocess
import sys
import threading
import time
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from fastapi.testclient import TestClient

from backend import habitat
from backend.db import connect
from backend.main import create_app, habitat_fallback_evidence
from backend.tests.test_habitat_integration import C1, ROOT, actions, one, set_clock

HELD = {'reason': None, 'cite_ids': [], 'hold': True, 'verified': 0, 'runs': []}


def written(target, level, findings, evidence, lang):
    return {'reason': f'{lang}:{target} reason.', 'cite_ids': [], 'hold': False, 'verified': 5, 'runs': []}


class HabitatReasonTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seeded = Path(cls.enterClassContext(TemporaryDirectory())) / 'demo.sqlite3'
        result = subprocess.run([sys.executable, '-m', 'backend.seed', str(cls.seeded), '--mission-demo'],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr

    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.path = self.directory / 'demo.sqlite3'
        shutil.copy(self.seeded, self.path)
        habitat._reason_failed.clear()
        habitat._reason_jobs.clear()
        self.model = self.enterContext(mock.patch('backend.habitat.pipeline.adjustment_reason', side_effect=written))
        self.client = self.enterContext(TestClient(create_app(self.path)))
        set_clock(self.client, 16, '09:00')

    def wait_jobs(self, timeout=3.0):
        deadline = time.monotonic() + timeout
        while habitat._reason_jobs and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(habitat._reason_jobs, {})

    def test_get_returns_and_stores_sentence(self):
        items = actions(self.client, 16)
        for target in ('lighting', 'schedule'):
            self.assertEqual(one(items, target)['reason_text'], f'en:{target} reason.')
        self.assertEqual(self.model.call_count, 2)
        calls = {c.args[0]: c.args for c in self.model.call_args_list}
        self.assertEqual(set(calls), {'lighting', 'schedule'})
        for target, (_, level, findings, evidence, lang) in calls.items():
            self.assertEqual(lang, 'en')
            self.assertIn(level, ('normal', 'advisory', 'caution', 'warning'))
            names = [f['metric'] for f in findings]
            self.assertIn('sleep', names)
            trigger = one(items, target)['trigger']
            if (trigger.get('hrv') or {}).get('z') is not None:
                self.assertIn('hrv', names)
            for f in findings:
                self.assertIsNotNone(f['z'])
            self.assertIsInstance(evidence, list)
            ids = {e.get('id') for e in evidence if isinstance(e, dict)}
            self.assertTrue(set(one(items, target)['cite_ids']) <= ids)
            self.assertTrue(one(items, target)['cite_ids'])
        again = actions(self.client, 16)
        self.assertEqual(again, items)
        self.assertEqual(self.model.call_count, 2)

    def test_languages_stored_separately(self):
        ko = actions(self.client, 16, 'ko')
        self.assertEqual(self.model.call_count, 2)
        en = actions(self.client, 16, 'en')
        self.assertEqual(self.model.call_count, 4)
        for target in ('lighting', 'schedule'):
            self.assertEqual(one(ko, target)['reason_text'], f'ko:{target} reason.')
            self.assertEqual(one(en, target)['reason_text'], f'en:{target} reason.')
        self.assertEqual(sorted(c.args[4] for c in self.model.call_args_list), ['en', 'en', 'ko', 'ko'])
        self.assertEqual(one(actions(self.client, 16, 'ko'), 'lighting')['reason_text'], 'ko:lighting reason.')
        self.assertEqual(one(actions(self.client, 16, 'en'), 'schedule')['reason_text'], 'en:schedule reason.')
        self.assertEqual(self.model.call_count, 4)

    def test_held_result_is_null_and_not_retried(self):
        self.model.side_effect = None
        self.model.return_value = HELD
        for card in actions(self.client, 16):
            self.assertIsNone(card['reason_text'])
        self.assertEqual(self.model.call_count, 2)
        for card in actions(self.client, 16):
            self.assertIsNone(card['reason_text'])
        self.assertEqual(self.model.call_count, 2)

    def test_slow_model_does_not_block_get(self):
        def slow(*args):
            time.sleep(0.4)
            return written(*args)
        self.model.side_effect = slow
        with mock.patch.object(habitat, 'REASON_WAIT', 0.05):
            started = time.monotonic()
            first = actions(self.client, 16)
            self.assertLess(time.monotonic() - started, 0.35)
            for card in first:
                self.assertIsNone(card['reason_text'])
            self.wait_jobs()
            second = actions(self.client, 16)
        for target in ('lighting', 'schedule'):
            self.assertEqual(one(second, target)['reason_text'], f'en:{target} reason.')
        self.assertEqual(self.model.call_count, 2)

    def test_sentence_keeps_other_fields_and_survives_approve(self):
        with closing(connect(self.path)) as connection:
            before = {row['target']: json.loads(row['data']) for row in habitat.list_actions(connection, 'c1', 16)}
        items = actions(self.client, 16)
        with closing(connect(self.path)) as connection:
            after = {row['target']: json.loads(row['data']) for row in habitat.list_actions(connection, 'c1', 16)}
        for target in ('lighting', 'schedule'):
            self.assertEqual(after[target].pop('reason_text'), {'en': f'en:{target} reason.'})
            self.assertEqual(after[target], before[target])
            card = one(items, target)
            self.assertTrue(card['cite_ids'])
            self.assertIsInstance(card['trigger'], dict)
            self.assertEqual(set(card['reason']), {'metric', 'value', 'z'})
            self.assertIsInstance(card['before_values'], dict)
        aid = one(items, 'schedule')['id']
        ok = self.client.post(f'/habitat/actions/{aid}/approve', headers=C1)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()['status'], 'applied')
        self.assertEqual(ok.json()['reason_text'], 'en:schedule reason.')
        schedule = one(actions(self.client, 16), 'schedule')
        self.assertEqual(schedule['status'], 'applied')
        self.assertEqual(schedule['reason_text'], 'en:schedule reason.')
        self.assertEqual(self.model.call_count, 2)

    def test_exception_in_job_is_null_and_not_retried(self):
        self.model.side_effect = RuntimeError('boom')
        with self.assertLogs('backend.habitat', 'WARNING'):
            items = actions(self.client, 16)
        self.assertEqual(len(items), 2)
        for card in items:
            self.assertIsNone(card['reason_text'])
        self.assertEqual(self.model.call_count, 2)
        for card in actions(self.client, 16):
            self.assertIsNone(card['reason_text'])
        self.assertEqual(self.model.call_count, 2)

    def test_slow_model_is_not_waited_for_again_after_window(self):
        def slow(*args):
            time.sleep(1.0)
            return written(*args)
        self.model.side_effect = slow
        with mock.patch.object(habitat, 'REASON_WAIT', 0.3):
            began = time.monotonic()
            for card in actions(self.client, 16):
                self.assertIsNone(card['reason_text'])
            self.assertGreaterEqual(time.monotonic() - began, 0.25)
            time.sleep(max(0.0, began + 0.4 - time.monotonic()))
            started = time.monotonic()
            for card in actions(self.client, 16):
                self.assertIsNone(card['reason_text'])
            self.assertLess(time.monotonic() - started, 0.2)
            self.wait_jobs()
            done = actions(self.client, 16)
        for target in ('lighting', 'schedule'):
            self.assertEqual(one(done, target)['reason_text'], f'en:{target} reason.')
        self.assertEqual(self.model.call_count, 2)

    def test_second_caller_inside_window_gets_sentence(self):
        def slow(*args):
            time.sleep(0.3)
            return written(*args)
        self.model.side_effect = slow
        evidence = habitat_fallback_evidence([])
        results = {}

        def call(name):
            with closing(connect(self.path)) as connection:
                rows = habitat.rows_with_reasons(connection, self.path, evidence, 'c1', 16, 'en')
                results[name] = [habitat.payload(row, 'en') for row in rows]

        with mock.patch.object(habitat, 'REASON_WAIT', 2.0):
            first = threading.Thread(target=call, args=('first',))
            second = threading.Thread(target=call, args=('second',))
            first.start()
            time.sleep(0.05)
            second.start()
            first.join(3.0)
            second.join(3.0)
        self.assertEqual(set(results), {'first', 'second'})
        for items in results.values():
            for target in ('lighting', 'schedule'):
                self.assertEqual(one(items, target)['reason_text'], f'en:{target} reason.')
        self.assertEqual(sorted(c.args[0] for c in self.model.call_args_list), ['lighting', 'schedule'])
