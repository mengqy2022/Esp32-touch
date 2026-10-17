import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest

from codex_usage import CodexUsage, codex_packet, estimate_cny_fen


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "sessions" / "test.jsonl"
        self.path.parent.mkdir()
        self.now = dt.datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
        self.reader = CodexUsage(self.root)

    def event(self, total, last=None, when=None):
        return json.dumps({"type": "event_msg", "timestamp": (when or self.now).isoformat(),
                           "payload": {"type": "token_count", "info": {
                               "total_token_usage": {"total_tokens": total},
                               "last_token_usage": {"total_tokens": total if last is None else last}}}})

    def write(self, lines, mode="w"):
        with self.path.open(mode, encoding="utf-8") as stream:
            stream.write(lines)
        os.utime(self.path, (self.now.timestamp(), self.now.timestamp()))

    def test_duplicates_and_incremental_append(self):
        self.write(self.event(100) + "\n" + self.event(100) + "\n" + self.event(160, 60) + "\n")
        self.assertEqual(self.reader.read(self.now)[0], 160)
        self.assertEqual(self.reader.read(self.now)[0], 160)
        self.write(self.event(220, 60) + "\n", "a")
        self.assertEqual(self.reader.read(self.now)[0], 220)

    def test_partial_line_and_malformed_record(self):
        self.write("bad json\n" + self.event(100))
        self.assertEqual(self.reader.read(self.now)[0], -1)
        self.write("\n", "a")
        self.assertEqual(self.reader.read(self.now)[0], 100)

    def test_midnight_and_counter_reset(self):
        yesterday = self.now - dt.timedelta(days=1)
        self.write(self.event(1000, when=yesterday) + "\n" + self.event(1100, 100) + "\n" + self.event(40, 40) + "\n")
        self.assertEqual(self.reader.read(self.now)[0], 140)
        self.now += dt.timedelta(days=1)
        self.write(self.event(100, 60) + "\n", "a")
        self.assertEqual(self.reader.read(self.now)[0], 60)

    def test_fork_does_not_include_inherited_total(self):
        self.write(self.event(5000, 30) + "\n" + self.event(5040, 40) + "\n")
        self.assertEqual(self.reader.read(self.now)[0], 70)

    def test_archive_move_and_truncate(self):
        self.write(self.event(100) + "\n")
        self.assertEqual(self.reader.read(self.now)[0], 100)
        archive = self.root / "archived_sessions"
        archive.mkdir()
        self.path.rename(archive / "test.jsonl")
        self.assertEqual(self.reader.read(self.now)[0], 100)
        self.write(self.event(20) + "\n")
        self.assertEqual(self.reader.read(self.now)[0], 120)

    def test_missing_logs_and_wire_limits(self):
        self.assertEqual(self.reader.read(self.now)[0], -1)
        self.assertEqual(codex_packet(100, 1000, 20261014), "PC:CODEX|100|0|20261014")
        self.assertEqual(codex_packet(1 << 70, 0, 20261014), "PC:CODEX|9223372036854775807|0|20261014")

    def test_cache_prices_and_currency(self):
        self.write(json.dumps({'type':'turn_context','payload':{'model':'gpt-6.1-sol'}})+'\n')
        event=json.loads(self.event(101000))
        usage={'input_tokens':100000,'cached_input_tokens':50000,'cache_write_input_tokens':10000,'output_tokens':1000,'total_tokens':101000}
        event['payload']['info']={'total_token_usage':usage,'last_token_usage':usage}
        self.write(json.dumps(event)+'\n','a')
        self.assertEqual(self.reader.read(self.now)[0],101000)
        prices=Path(__file__).with_name('codex_prices.json')
        self.assertEqual(estimate_cny_fen(self.reader.by_model,prices),17)
        self.assertEqual(codex_packet(101000,0,20261014,17),'PC:CODEX|101000|0|20261014|17')
        self.assertEqual(self.reader.read(self.now)[0],101000)
        self.assertEqual(estimate_cny_fen(self.reader.by_model,prices),17)

    def test_long_context_and_unknown_model(self):
        self.write(json.dumps({'type':'turn_context','payload':{'model':'gpt-6-astra'}})+'\n')
        event=json.loads(self.event(301000))
        usage={'input_tokens':300000,'cached_input_tokens':100000,'cache_write_input_tokens':0,'output_tokens':1000,'total_tokens':301000}
        event['payload']['info']={'total_token_usage':usage,'last_token_usage':usage}
        self.write(json.dumps(event)+'\n','a')
        self.reader.read(self.now)
        self.assertEqual(estimate_cny_fen(self.reader.by_model,Path(__file__).with_name('codex_prices.json')),616)
        counts=self.reader.by_model.pop('gpt-6-astra|long')
        self.reader.by_model['unknown|long']=counts
        self.assertEqual(estimate_cny_fen(self.reader.by_model,Path(__file__).with_name('codex_prices.json')),-1)

    def test_context_threshold_and_request_input_fallback(self):
        for context, expected in ((272000, 'short'), (272001, 'long'), (None, 'short')):
            with self.subTest(context=context):
                self.reader = CodexUsage(self.root)
                self.write(json.dumps({'type': 'turn_context', 'payload': {'model': 'gpt-6.1-sol'}}) + '\n')
                event = json.loads(self.event(500000))
                total = dict(input_tokens=490000, cached_input_tokens=0, output_tokens=10000, total_tokens=500000)
                last = dict(input_tokens=100000, cached_input_tokens=0, output_tokens=1000, total_tokens=101000)
                event['payload']['info'] = dict(total_token_usage=total, last_token_usage=last)
                if context is not None:
                    event['payload']['info']['context_tokens'] = context
                self.write(json.dumps(event) + '\n', 'a')
                self.reader.read(self.now)
                self.assertIn('gpt-6.1-sol|' + expected, self.reader.by_model)


if __name__ == "__main__":
    unittest.main()
