import datetime as dt
import json
import tempfile
import unittest
import os
from pathlib import Path

from ai_usage import ClaudeUsage, AIUsage, ai_packet


class ClaudeUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'projects' / 'demo' / 'session.jsonl'
        self.path.parent.mkdir(parents=True)
        self.now = dt.datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)

    def event(self, identity='m1', output=1000, when=None, model='claude-fable-5-1'):
        return dict(type='assistant', timestamp=(when or self.now).isoformat(), requestId='r-' + identity,
                    message=dict(id=identity, model=model, usage=dict(input_tokens=100000,
                                  cache_read_input_tokens=200000, cache_creation_input_tokens=10000,
                                  output_tokens=output)))

    def write(self, events, mode='w', path=None):
        path = path or self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open(mode, encoding='utf-8') as stream:
            for event in events:
                stream.write(json.dumps(event) + '\n')
        os.utime(path, (self.now.timestamp(), self.now.timestamp()))

    def test_cache_accounting_and_exact_price(self):
        self.write([self.event()])
        sample = AIUsage(self.root / 'codex', self.root)
        # $0.30 + $0.015 + $0.0375 + $0.015 = $0.3675 -> ¥2.65
        self.assertEqual(sample.sample('claude', Path(__file__).with_name('codex_prices.json'), self.now),
                         (311000, int(self.now.strftime('%Y%m%d')), 265, 'CLAUDE'))

    def test_streaming_duplicate_fork_and_subagent(self):
        self.write([self.event(output=10), self.event(output=1000)])
        self.write([self.event()], path=self.path.with_name('fork.jsonl'))
        self.write([self.event('child')], path=self.path.parent / 'subagents' / 'agent.jsonl')
        reader = ClaudeUsage(self.root)
        self.assertEqual(reader.read(self.now)[0], 622000)
        self.assertEqual(reader.read(self.now)[0], 622000)
        self.write([self.event('m2')], mode='a')
        self.assertEqual(reader.read(self.now)[0], 933000)

    def test_partial_line_malformed_truncate_and_midnight(self):
        event = self.event()
        self.path.write_text('garbage\n' + json.dumps(event), encoding='utf-8')
        reader = ClaudeUsage(self.root)
        self.assertEqual(reader.read(self.now)[0], -1)
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write('\n')
        self.assertEqual(reader.read(self.now)[0], 311000)
        self.write([self.event('new', output=2)])
        self.assertEqual(reader.read(self.now)[0], 310002)
        tomorrow = self.now + dt.timedelta(days=1)
        self.write([self.event('next', when=tomorrow)], mode='a')
        os.utime(self.path, (tomorrow.timestamp(), tomorrow.timestamp()))
        self.assertEqual(reader.read(tomorrow)[0], 311000)

    def test_unknown_prices_do_not_fall_back_to_another_source(self):
        self.write([self.event(model='unconfigured-model')])
        sample = AIUsage(self.root / 'missing', self.root)
        prices = Path(__file__).with_name('codex_prices.json')
        tokens, _, cost, label = sample.sample('claude', prices, self.now)
        self.assertEqual((tokens, cost, label), (311000, -1, 'CLAUDE'))
        self.assertEqual(sample.sample('codex', prices, self.now)[0], -1)

    def test_source_switch_keeps_counts_and_costs_separate(self):
        self.write([self.event()])
        codex = self.root / 'codex' / 'sessions' / 'session.jsonl'
        codex.parent.mkdir(parents=True)
        fields = dict(input_tokens=10000, cached_input_tokens=0, output_tokens=1000, total_tokens=11000)
        events = [dict(type='turn_context', payload=dict(model='gpt-6.1-sol')),
                  dict(type='event_msg', timestamp=self.now.isoformat(),
                       payload=dict(type='token_count', info=dict(total_token_usage=fields, last_token_usage=fields)))]
        codex.write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
        reader = AIUsage(self.root / 'codex', self.root)
        prices = Path(__file__).with_name('codex_prices.json')
        for source, expected in (('codex', (11000, 4, 'CODEX')),
                                 ('claude', (311000, 265, 'CLAUDE')),
                                 ('codex', (11000, 4, 'CODEX'))):
            tokens, _, cost, label = reader.sample(source, prices, self.now)
            self.assertEqual((tokens, cost, label), expected)
            packet = ai_packet(tokens, int(self.now.strftime('%Y%m%d')), cost, label)
            self.assertTrue(packet.startswith('PC:USAGE|' + label + '|'))
            self.assertNotIn('PC:AI|', packet)
            self.assertEqual(len(packet.splitlines()), 1)
        with self.assertRaises(ValueError):
            reader.sample('all', prices, self.now)
        with self.assertRaises(ValueError):
            ai_packet(322000, int(self.now.strftime('%Y%m%d')), 269, 'AI TOTAL')

    def test_claude_code_usage_and_source_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'projects' / 'demo' / 'session.jsonl'
            path.parent.mkdir(parents=True)
            now = dt.datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
            event = {'type': 'assistant', 'timestamp': now.isoformat(), 'requestId': 'r1',
                     'message': {'id': 'm1', 'model': 'claude-fable-5-1',
                                 'usage': {'input_tokens': 100, 'cache_read_input_tokens': 20,
                                           'cache_creation_input_tokens': 5, 'output_tokens': 30}}}
            path.write_text(json.dumps(event) + '\n' + json.dumps(event) + '\n', encoding='utf-8')
            reader = ClaudeUsage(root)
            self.assertEqual(reader.read(now)[0], 155)
            prices = Path(__file__).with_name('codex_prices.json')
            sample = AIUsage(root / 'missing-codex', root)
            tokens, day, cost, label = sample.sample('claude', prices, now)
            self.assertEqual((tokens, label), (155, 'CLAUDE'))
            self.assertGreater(cost, 0)
            self.assertEqual(ai_packet(tokens, day, cost, label), f'PC:USAGE|CLAUDE|155|0|{day}|{cost}')


if __name__ == '__main__':
    unittest.main()
