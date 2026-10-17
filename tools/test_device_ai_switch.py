"""Manual hardware regression: independent caches, selection and reboot persistence.

Pause the companion first. Uses synthetic counts only while testing and restores
the original source. Does not alter prices, calibration or filesystem contents.
The selection command calls the same firmware function as the touch buttons;
this verifies firmware behavior, not a physical finger tap.
"""
import argparse
import datetime as dt
from pathlib import Path
import time

import serial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM5')
    args = parser.parse_args()
    day = int(dt.datetime.now().strftime('%Y%m%d'))
    chunks = []
    checks = {}
    with serial.Serial(port=None, baudrate=115200, timeout=.2, write_timeout=2) as connection:
        connection.dtr = False
        connection.rts = False
        connection.port = args.port
        connection.open()

        def query(commands=''):
            connection.reset_input_buffer()
            connection.write((commands + 'PC:AI?\n').encode('ascii'))
            received = b''
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                received += connection.read(connection.in_waiting or 1)
                for line in received.decode('utf-8', 'replace').splitlines(keepends=True):
                    if line.startswith('PC:AI_STATE|') and line.endswith('\n'):
                        chunks.append(received)
                        fields = line.strip().split('|')
                        return fields[1], *(int(value) for value in fields[2:])
            chunks.append(received)
            raise RuntimeError('No AI state response from device')

        original = query()[0]
        try:
            packets = (f'PC:USAGE|CODEX|12345|0|{day}|123\n'
                       f'PC:USAGE|CLAUDE|67890|0|{day}|456\n')
            checks['codex_cache'] = query(packets + 'PC:AI|CODEX\n') == ('CODEX', 12345, day, 123, 1)
            checks['claude_cache'] = query('PC:AI|CLAUDE\n') == ('CLAUDE', 67890, day, 456, 1)
            checks['stream_does_not_override_selection'] = query(packets * 3) == ('CLAUDE', 67890, day, 456, 1)
            invalid = (f'PC:USAGE|CLAUDE|-2|0|{day}|999\n'
                       f'PC:USAGE|UNKNOWN|999|0|{day}|999\nPC:AI|UNKNOWN\n')
            checks['invalid_packets_preserve_state'] = query(invalid) == ('CLAUDE', 67890, day, 456, 1)
            checks['switch_back_recovers_codex'] = query('PC:AI|CODEX\n') == ('CODEX', 12345, day, 123, 1)
            query('PC:AI|CLAUDE\n')
            connection.rts = True
            time.sleep(.15)
            connection.rts = False
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                chunks.append(connection.read(connection.in_waiting or 1))
            state = query()
            checks['selection_survives_reset'] = state[0] == 'CLAUDE'
            checks['reboot_does_not_reuse_old_counts'] = state == ('CLAUDE', -1, 0, -1, 0)
            checks['cache_updates_after_reset'] = query(packets) == ('CLAUDE', 67890, day, 456, 1)
        finally:
            query('PC:AI|' + original + '\n')
    log = b''.join(chunks).decode('utf-8', 'replace')
    checks['no_crash'] = not any(marker in log for marker in ('Guru Meditation', 'abort()', 'Task watchdog got triggered'))
    output = Path(__file__).resolve().parent.parent / 'build/device_ai_switch_validation.log'
    output.write_text(log, encoding='utf-8')
    for name, passed in checks.items():
        print(f'{name}: {"PASS" if passed else "FAIL"}')
    print(f'Log: {output}')
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
