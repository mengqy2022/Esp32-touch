"""Manual live UART check. Pause the Dashboard first; no salary settings changed."""
import argparse
import datetime as dt
import json
from pathlib import Path
import time
from contextlib import ExitStack
import serial

from work_calendar import CalendarSync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    log, heaps, frames = [], [], []
    with serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=5) as port, ExitStack() as cleanup:
        port.dtr = port.rts = False
        port.port = args.port
        port.open()
        def restore_time():
            if port.is_open:
                port.write(f'PC:TIME|{int(time.time())}\n'.encode('ascii'))
        cleanup.callback(restore_time)
        def collect(seconds):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                line = port.readline().decode('utf-8', 'replace').strip()
                if line:
                    log.append(line)

        def state(active):
            first = len(log)
            port.write(b'SALARY:?\nFILE:PING\n')
            collect(1)
            replies = [line.split('|') for line in log[first:] if line.startswith('SALARY:STATE|')]
            assert replies and int(replies[-1][1]) == active, log[first:]
            assert 'FILE:PONG' in log[first:], log[first:]
            assert int(replies[-1][2]) == 1, replies[-1]
            if active:
                frames.append(int(replies[-1][4]))
            return int(replies[-1][3])

        collect(2)
        # Exercise a working Tuesday so the animation timer actually advances.
        simulated = int(dt.datetime(2026, 10, 20, 10, 30, tzinfo=dt.timezone(dt.timedelta(hours=8))).timestamp())
        port.write(f'PC:TZOFF|480\nPC:TIME|{simulated}\n'.encode('ascii'))
        packets = CalendarSync().packets(dt.datetime.now().year)
        port.write(('\n'.join(packets) + '\n').encode('ascii'))
        collect(1)
        assert sum(line == 'SALARY:OK' for line in log) == len(packets), log
        port.write(b'SALARY:CLOSE\n')
        collect(.5)
        baseline = state(0)
        for _ in range(5):
            port.write(b'SALARY:OPEN\n')
            collect(1.5)
            opened = state(1)
            state(1)
            assert frames[-1] > frames[-2], 'Animation stopped during working hours'
            assert baseline - opened >= 13568, (baseline, opened)
            port.write(b'SALARY:CLOSE\n')
            collect(.5)
            heaps.append(state(0))
        assert max(heaps) - min(heaps) < 1024, heaps
        port.write(b'SALARY:CAL|2026|2|ffffffff|0\n')
        start = len(log)
        collect(.5)
        assert 'SALARY:ERR|calendar' in log[start:], log[start:]
        # Animation must also run outside working hours; only earnings pause.
        evening = int(dt.datetime(2026, 10, 20, 22, 0, tzinfo=dt.timezone(dt.timedelta(hours=8))).timestamp())
        port.write(f'PC:TIME|{evening}\nSALARY:OPEN\n'.encode('ascii'))
        collect(1)
        state(1)
        state(1)
        assert frames[-1] > frames[-2], 'Animation stopped after work'
        assert not any(marker in '\n'.join(log) for marker in ('Guru Meditation', 'CORRUPT HEAP', 'assert failed', 'Stack canary'))
    result = dict(passed=True, cycles=5, closed_heap_bytes=heaps, rendered_frames=frames,
                  checks=['calendar_sync', 'invalid_calendar', 'time_sync', 'ping', 'open_close', 'buffer_allocation', 'heap_stability', 'working_and_evening_animation'],
                  limitations=['No physical touch or visual inspection', 'No NVS settings edited'])
    args.report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
