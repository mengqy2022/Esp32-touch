"""Local Claude Code usage and selectable Codex/Claude telemetry. No API calls."""
import datetime as dt
import json
import os
from pathlib import Path

from codex_usage import CodexUsage, estimate_cny_fen, codex_packet

SOURCES = {'codex': 'CODEX', 'claude': 'CLAUDE'}


class ClaudeUsage:
    def __init__(self, home=None):
        self.home = Path(home or os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')
        self.day = None
        self.files = {}
        self.by_model = {}

    def read(self, now=None):
        now = now or dt.datetime.now().astimezone()
        day = now.date()
        if self.day != day:
            self.files.clear()
            self.day = day
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        paths = set()
        # Subagents are included by the recursive scan. Never inspect credentials.
        for path in (self.home / 'projects').rglob('*.jsonl'):
            try:
                stat = path.stat()
                if stat.st_mtime < midnight:
                    continue
                paths.add(path)
                state = self.files.get(path)
                if state is None or stat.st_size < state['offset']:
                    state = {'offset': 0, 'events': {}}
                    self.files[path] = state
                with path.open('rb') as stream:
                    stream.seek(state['offset'])
                    while True:
                        offset = stream.tell()
                        line = stream.readline()
                        if not line or not line.endswith(b'\n'):
                            state['offset'] = offset
                            break
                        state['offset'] = stream.tell()
                        self._event(line, state, day)
            except OSError:
                continue
        self.files = {p: s for p, s in self.files.items() if p in paths}
        # The same assistant message may appear in multiple transcript snapshots.
        events = {}
        for state in self.files.values():
            for key, record in state['events'].items():
                old = events.get(key)
                if old is None or record[0] >= old[0]:
                    events[key] = record
        self.by_model = {}
        for _, model, fields in events.values():
            counts = self.by_model.setdefault(model + '|short', dict(input=0, cached=0, cache_write=0, output=0, unpriced=0))
            for key, value in fields.items():
                counts[key] += value
        tokens = sum(c['input'] + c['output'] for c in self.by_model.values())
        return (tokens if events else -1), int(day.strftime('%Y%m%d'))

    @staticmethod
    def _event(line, state, day):
        if b'"usage"' not in line:
            return
        try:
            event = json.loads(line)
            if event.get('type') != 'assistant':
                return
            timestamp = dt.datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            if timestamp.tzinfo is None or timestamp.astimezone().date() != day:
                return
            message = event['message']
            usage = message['usage']
            values = [usage.get('input_tokens'), usage.get('cache_read_input_tokens', 0),
                      usage.get('cache_creation_input_tokens', 0), usage.get('output_tokens')]
            if not all(type(v) is int and v >= 0 for v in values):
                return
            identity = message.get('id') or event.get('uuid')
            if not identity:
                return  # Cannot safely deduplicate a record without identity.
            key = (event.get('requestId', ''), identity)
            normal, cached, write, output = values
            # Anthropic input excludes cache tokens; the shared price engine uses inclusive input.
            fields = dict(input=normal + cached + write, cached=cached, cache_write=write, output=output)
            record = (timestamp.timestamp(), message.get('model') or 'unknown', fields)
            old = state['events'].get(key)
            if old is None or record[0] >= old[0]:
                state['events'][key] = record
        except (ValueError, KeyError, TypeError, AttributeError):
            return


class AIUsage:
    def __init__(self, codex_home=None, claude_home=None):
        self.readers = {'codex': CodexUsage(codex_home), 'claude': ClaudeUsage(claude_home)}

    def sample(self, source, prices, now=None):
        if source not in SOURCES:
            raise ValueError('Unknown AI source')
        reader = self.readers[source]
        tokens, day = reader.read(now)
        cost = estimate_cny_fen(reader.by_model, prices) if prices and tokens >= 0 else -1
        return tokens, day, cost, SOURCES[source]


def ai_packet(tokens, day, cost, label):
    if label not in SOURCES.values():
        raise ValueError('Unknown AI source label')
    # Updating either provider must never change the selection made on the device.
    # Reuse the integer validation and reserved zero slot of the legacy encoder.
    fields = codex_packet(tokens, 0, day, cost).split('|', 1)[1]
    return 'PC:USAGE|' + label + '|' + fields
