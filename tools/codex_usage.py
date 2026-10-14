"""Read only Codex token_count events; never send prompts or credentials.

Counts input + output tokens (cached input is already included in input).
Local JSONL records are an implementation detail, not an official quota API.
"""

import datetime as dt
import json
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


class CodexUsage:
    def __init__(self, home=None):
        self.home = Path(home or os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        self.day = None
        self.files = {}
        self.by_model = {}

    def read(self, now=None):
        """Return (today's tokens or -1 if unavailable, YYYYMMDD).

        Each file keeps its cumulative counter across midnight. Repeated usage
        snapshots do not count twice; forked logs start with last_token_usage
        so inherited parent totals are not counted again. Partial final lines
        are left unread until the writer completes them.
        """
        now = now or dt.datetime.now().astimezone()
        day = now.date()
        if day != self.day:
            self.files.clear()
            self.day = day
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        date_code = int(day.strftime("%Y%m%d"))
        available = False
        paths = set()
        for folder in ("sessions", "archived_sessions"):
            root = self.home / folder
            if not root.is_dir():
                continue
            for path in root.rglob("*.jsonl"):
                try:
                    stat = path.stat()
                    # A file last changed before today cannot contain today's usage.
                    if stat.st_mtime < midnight:
                        continue
                    paths.add(path)
                    state = self.files.get(path)
                    if state is None or stat.st_size < state["offset"]:
                        state = {"offset": 0, "previous": None, "tokens": 0, "seen": False,
                                 "model": "unknown", "previous_fields": None, "by_model": {}}
                        self.files[path] = state
                    with path.open("rb") as stream:
                        stream.seek(state["offset"])
                        while True:
                            start = stream.tell()
                            line = stream.readline()
                            if not line or not line.endswith(b"\n"):
                                state["offset"] = start
                                break
                            state["offset"] = stream.tell()
                            self._event(line, state, day)
                    available |= state["seen"]
                except OSError:
                    continue
        # Remove files moved to the archive; count them at their new location.
        self.files = {path: state for path, state in self.files.items() if path in paths}
        total = sum(state["tokens"] for state in self.files.values())
        self.by_model = {}
        for state in self.files.values():
            for model, counts in state['by_model'].items():
                aggregate = self.by_model.setdefault(model, dict(input=0, cached=0, cache_write=0, output=0, unpriced=0))
                for field in aggregate:
                    aggregate[field] += counts[field]
        return (total if available else -1), date_code

    @staticmethod
    def _event(line, state, day):
        # Skip conversation text before JSON decoding. Large prompt records
        # are unnecessary for counters and otherwise inflate resident memory.
        if b'"token_count"' not in line and b'"turn_context"' not in line:
            return
        try:
            event = json.loads(line)
            payload = event.get("payload") or {}
            if event.get('type') == 'turn_context':
                state['model'] = payload.get('model') or 'unknown'
                return
            if event.get("type") != "event_msg" or payload.get("type") != "token_count":
                return
            info = payload.get("info") or {}
            cumulative = (info.get("total_token_usage") or {}).get("total_tokens")
            if type(cumulative) is not int or cumulative < 0:
                return
            timestamp = dt.datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                return
            previous = state["previous"]
            last = (info.get("last_token_usage") or {}).get("total_tokens")
            if previous is None or cumulative < previous:
                delta = last if type(last) is int and 0 <= last <= cumulative else cumulative
            else:
                delta = cumulative - previous
            state["previous"] = cumulative
            current_fields = usage_fields(info.get('total_token_usage'))
            previous_fields = state['previous_fields']
            if previous is None or cumulative < previous:
                fields = usage_fields(info.get('last_token_usage')) or current_fields
            elif current_fields is not None and previous_fields is not None:
                fields = {k: current_fields[k] - previous_fields[k] for k in current_fields}
                if any(v < 0 for v in fields.values()):
                    fields = None
            else:
                fields = None
            state['previous_fields'] = current_fields
            state["seen"] = True
            if timestamp.astimezone().date() == day:
                state["tokens"] += delta
                tier = 'long' if fields and fields['input'] > 272000 else 'short'
                counts = state['by_model'].setdefault(state['model'] + '|' + tier, dict(input=0, cached=0, cache_write=0, output=0, unpriced=0))
                if fields is not None and fields['input'] + fields['output'] == delta and fields['cached'] + fields['cache_write'] <= fields['input']:
                    for key in fields:
                        counts[key] += fields[key]
                else:
                    counts['unpriced'] += delta
        except (ValueError, KeyError, TypeError, AttributeError):
            return


def usage_fields(usage):
    if not isinstance(usage, dict):
        return None
    keys = {'input': 'input_tokens', 'cached': 'cached_input_tokens', 'output': 'output_tokens'}
    result = {key: usage.get(field) for key, field in keys.items()}
    result['cache_write'] = usage.get('cache_write_input_tokens', 0)
    return result if all(type(v) is int and v >= 0 for v in result.values()) else None


def estimate_cny_fen(by_model, price_file):
    """Return rounded estimated fen, or -1 if any consumed tokens lack prices."""
    try:
        prices = json.loads(Path(price_file).read_text(encoding='utf-8-sig'))
        if prices.get('currency') not in ('CNY', 'USD'):
            return -1
        exchange = Decimal(str(prices.get('usd_to_cny', 0))) if prices['currency'] == 'USD' else Decimal(1)
        if not exchange.is_finite() or exchange <= 0:
            return -1
        total = Decimal(0)
        for model, counts in by_model.items():
            if not any(counts.values()):
                continue
            model, tier = model.rsplit('|', 1)
            rate = prices.get('models', {}).get(model) or prices.get('models', {}).get('*')
            if not rate or counts['unpriced']:
                return -1
            rate = rate.get(tier, rate)
            for field, tokens in [('input', counts['input'] - counts['cached'] - counts['cache_write']),
                                  ('cached_input', counts['cached']), ('cache_write_input', counts['cache_write']), ('output', counts['output'])]:
                if tokens == 0:
                    continue
                unit = Decimal(str(rate[field + '_per_million']))
                if not unit.is_finite() or unit < 0:
                    return -1
                total += tokens * unit * exchange / 1_000_000
        if not by_model:
            return -1
        return min((1 << 63) - 1, int((total * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)))
    except (OSError, ValueError, TypeError, KeyError, InvalidOperation):
        return -1


def codex_packet(tokens, goal, day, cost_fen=None):
    """Clamp to the signed 64-bit wire format supported by firmware."""
    ceiling = (1 << 63) - 1
    packet = f"PC:CODEX|{max(-1, min(tokens, ceiling))}|{max(0, min(goal, ceiling))}|{day}"
    return packet if cost_fen is None else packet + f"|{max(-1, min(cost_fen, ceiling))}"
