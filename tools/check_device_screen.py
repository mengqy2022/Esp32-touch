"""Manual COM test: opens PC SCREEN, validates frames, then returns to SYSTEM."""
import argparse
import time
import serial
from pc_screen import WIDTH, HEIGHT, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM5')
    args = parser.parse_args()
    log = []
    with serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=5) as ser:
        ser.dtr = ser.rts = False
        ser.port = args.port
        ser.open()
        buffer = b''
        def wait(prefix, timeout=3):
            nonlocal buffer
            until = time.monotonic() + timeout
            while time.monotonic() < until:
                buffer += ser.read(ser.in_waiting or 1)
                while b'\n' in buffer:
                    raw, buffer = buffer.split(b'\n', 1)
                    line = raw.decode('utf-8', 'replace').strip()
                    log.append(line)
                    if line.startswith(prefix): return line
            raise AssertionError(f'No {prefix}: {log[-8:]}')
        def state():
            ser.write(b'SCREEN:?\n')
            return tuple(map(int, wait('SCREEN:STATE|').split('|')[1:]))
        def displayed(frame):
            until = time.monotonic() + 3
            while time.monotonic() < until:
                result = state()
                if result[1] == frame: return result
                time.sleep(.1)
            raise AssertionError(f'Frame {frame} not consumed by LVGL')
        def send(session, frame, payload, valid=True):
            hash_value = checksum(payload) ^ (0 if valid else 1)
            ser.write(f'SCREEN:FRAME|{session}|{frame}|{len(payload)}|{hash_value}\n'.encode())
            assert wait('SCREEN:') == 'SCREEN:READY'
            # Split payload to exercise the streaming decoder, including odd boundaries.
            for offset in range(0, len(payload), 511): ser.write(payload[offset:offset + 511])
            return wait('SCREEN:', 6)
        assert state()[0] == 0, 'Close PC SCREEN before running this check'
        try:
            previous_session = 0
            for cycle in range(5):
                ser.write(b'SCREEN:OPEN\n')
                until = time.monotonic() + 3
                while time.monotonic() < until:
                    session, frame = state()
                    if session: break
                    time.sleep(.1)
                assert session and session != previous_session, 'No new page session (allocation failure?)'
                previous_session = session
                count, tail = divmod(WIDTH * HEIGHT, 255)
                payload = bytes([255, 0xe0]) * count + (bytes([tail, 0xe0]) if tail else b'')
                assert send(session, 1, payload) == 'SCREEN:OK'
                assert displayed(1) == (session, 1)
                if cycle == 0:
                    assert send(session, 2, payload, False).startswith('SCREEN:ERR|payload')
                    assert state() == (session, 1)
                    assert send(session, 2, b'\x00\x01').startswith('SCREEN:ERR|payload')
                    ser.write(f'SCREEN:FRAME|{session}|2|999999|0\n'.encode())
                    assert wait('SCREEN:').startswith('SCREEN:ERR|header')
                    ser.write(f'SCREEN:FRAME|{session ^ 1}|2|2|0\n'.encode())
                    assert wait('SCREEN:').startswith('SCREEN:ERR|inactive')
                    start = time.monotonic()
                    worst_case = bytes([1, 0xe0, 1, 3]) * (WIDTH * HEIGHT // 2)
                    assert send(session, 3, worst_case) == 'SCREEN:OK'
                    assert displayed(3) == (session, 3)
                    print(f'Maximum payload {len(worst_case)} bytes: {time.monotonic() - start:.2f}s (including display confirmation)')
                ser.write(b'SCREEN:CLOSE\n')
                time.sleep(.2)
                assert state()[0] == 0
                ser.write(b'FILE:PING\n')
                assert wait('FILE:PONG') == 'FILE:PONG'
                print(f'Page allocation / receive / LVGL refresh / close / PING cycle {cycle + 1}: PASS')
        finally:
            ser.write(b'SCREEN:CLOSE\n')
        assert not any(word in '\n'.join(log) for word in ('Guru Meditation', 'abort()', 'watchdog got triggered'))
        print('Bounds, checksum, malformed RLE, stale session, full-size transfer, repeated page lifecycle: PASS')


if __name__ == '__main__': main()
