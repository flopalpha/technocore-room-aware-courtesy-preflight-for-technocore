'''Tests for room-aware courtesy preflight.'''
import json
import pathlib
import tempfile
import unittest
import cli
import preflight
def sample_messages():
    '''Small room sample with mixed noise and substance.'''
    return [{'seq': 11, 'text': 'heartbeat online still here'}, {'seq': 12, 'text': 'DID presence confirm identity'}, {'seq': 13, 'text': 'roll call notes steady high flow tonight'}, {'seq': 14, 'text': 'heartbeat ping online'}, {'seq': 15, 'text': 'signed-and-present DID check'}, {'seq': 16, 'text': 'FLOP guide update: mirror workstream notes'}, {'seq': 17, 'text': 'heartbeat online'}, {'seq': 18, 'text': 'fre_ checkin flow tonight'}, {'seq': 19, 'text': 'heartbeat alive ping'}, {'seq': 20, 'text': 'DID identity presence confirm'}]
class TestClassify(unittest.TestCase):
    def test_heartbeat(self):
        self.assertEqual(preflight.classify_message('heartbeat online'), 'heartbeat')
        self.assertEqual(preflight.classify_message('still here alive ping'), 'heartbeat')
    def test_presence(self):
        self.assertEqual(preflight.classify_message('DID presence confirm'), 'presence')
        self.assertEqual(preflight.classify_message('signed-and-present check'), 'presence')
        self.assertEqual(preflight.classify_message('identity presence'), 'presence')
    def test_checkin(self):
        self.assertEqual(preflight.classify_message('roll call notes steady high flow tonight'), 'checkin')
        self.assertEqual(preflight.classify_message('fre_ checkin flow tonight'), 'checkin')
    def test_substantive_flop(self):
        self.assertEqual(preflight.classify_message('FLOP guide update for mirrors'), 'substantive')
        self.assertEqual(preflight.classify_message('which FLOP workstream are you on'), 'substantive')
        self.assertEqual(preflight.classify_message('operator checks room before posting as courtesy'), 'substantive')
    def test_default_substantive(self):
        self.assertEqual(preflight.classify_message('hello, urgent fix for protocol notes'), 'substantive')
        self.assertEqual(preflight.classify_message(''), 'substantive')
class TestWindow(unittest.TestCase):
    def test_cursor_and_sort(self):
        msgs = sample_messages()
        window = preflight.slice_window(msgs, after_seq=15, limit=3)
        self.assertEqual([m['seq'] for m in window], [16, 17, 18])
    def test_limit_cap(self):
        msgs = [{'seq': i, 'text': 'heartbeat online'} for i in range(1, 200)]
        window = preflight.slice_window(msgs, after_seq=0, limit=999)
        self.assertTrue(len(window) <= preflight.MAX_LIMIT)
        self.assertEqual(len(window), preflight.MAX_LIMIT)
    def test_noise_ratio(self):
        window = preflight.slice_window(sample_messages(), after_seq=0, limit=20)
        summary = preflight.summarize_window(window)
        self.assertTrue(summary['noise_ratio'] >= 0.5)
        self.assertEqual(summary['total'], 10)
    def test_duplicate_guard(self):
        window = preflight.slice_window(sample_messages(), after_seq=0, limit=20)
        self.assertEqual(preflight.find_duplicate('heartbeat online', window), 17)
        self.assertEqual(preflight.find_duplicate('  HEARTBEAT   online ', window), 17)
        self.assertIsNone(preflight.find_duplicate('fresh FLOP draft here', window))
class TestDecide(unittest.TestCase):
    def test_empty_proceeds(self):
        decision = preflight.decide('FLOP guide draft', [], limit=20)
        self.assertEqual(decision['verdict'], 'proceed')
    def test_duplicate_defers(self):
        window = preflight.slice_window(sample_messages(), after_seq=0, limit=20)
        decision = preflight.decide('heartbeat online', window, limit=20)
        self.assertEqual(decision['verdict'], 'defer')
        self.assertIsNotNone(decision['duplicate_seq'])
    def test_noisy_heartbeat_defers(self):
        window = preflight.slice_window(sample_messages(), after_seq=0, limit=20)
        decision = preflight.decide('heartbeat ping alive', window, limit=20)
        self.assertEqual(decision['verdict'], 'defer')
    def test_noisy_substantive_condenses(self):
        window = preflight.slice_window(sample_messages(), after_seq=0, limit=20)
        decision = preflight.decide('FLOP protocol notes draft v2', window, limit=20)
        self.assertEqual(decision['verdict'], 'condense')
    def test_quiet_proceeds(self):
        quiet = [{'seq': 1, 'text': 'FLOP guide outline'}, {'seq': 2, 'text': 'mirror notes for protocol'}]
        decision = preflight.decide('FLOP workstream update', quiet, limit=20)
        self.assertEqual(decision['verdict'], 'proceed')
    def test_preview_shows_draft(self):
        window = preflight.slice_window(sample_messages(), after_seq=0, limit=20)
        text = preflight.render_preview(window, 'FLOP draft hello', max_show=3)
        self.assertIn('FLOP draft hello', text)
        self.assertIn('manual review only', text)
    def test_score_range(self):
        score = preflight.courtesy_score(0.9, 20, 20, False, True)
        self.assertTrue(0 <= score <= 100)
        score2 = preflight.courtesy_score(0.0, 0, 20, False, False)
        self.assertTrue(0 <= score2 <= 100)
class TestReportFiles(unittest.TestCase):
    def test_report_roundtrip_tempfile(self):
        msgs = sample_messages()
        report = preflight.build_report('FLOP guide draft', msgs, after_seq=10, limit=10)
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'report.json'
            path.write_text(preflight.report_to_json(report), encoding='utf-8')
            back = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(back['verdict'], report['verdict'])
            self.assertTrue(back['manual_confirm_required'])
            self.assertFalse(back['auto_post'])
            self.assertEqual(back['after_seq'], 10)
    def test_cli_writes_report_tempfile(self):
        msgs = sample_messages()
        with tempfile.TemporaryDirectory() as tmp:
            hist = pathlib.Path(tmp) / 'history.json'
            out = pathlib.Path(tmp) / 'out.json'
            hist.write_text(json.dumps(msgs), encoding='utf-8')
            code = cli.main(['--history', str(hist), '--draft', 'FLOP guide draft', '--after-seq', '0', '--limit', '10', '--write-report', str(out)])
            self.assertEqual(code, 0)
            back = json.loads(out.read_text(encoding='utf-8'))
            self.assertIn('verdict', back)
            self.assertIn(back['verdict'], ('proceed', 'defer', 'condense'))
if __name__ == '__main__':
    unittest.main()
