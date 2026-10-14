"""Read-only device regression test: several commands in one UART write.

Sends FILE:PING, real local Codex counts and wall-clock synchronization.
Does not upload/delete files or change calibration. Close the host first.
"""
import argparse
import pathlib
import sys
import time

import serial

from codex_usage import CodexUsage, codex_packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM5")
    args = parser.parse_args()
    tokens, day = CodexUsage().read()
    if tokens < 0:
        raise SystemExit("No readable local Codex usage records")
    chunks = []
    with serial.Serial(args.port, 115200, timeout=0.2, write_timeout=2) as port:
        port.dtr = False
        port.rts = True
        time.sleep(0.15)
        port.rts = False
        boot_deadline = time.monotonic() + 5
        while time.monotonic() < boot_deadline:
            chunks.append(port.read(port.in_waiting or 1))
        # Deliberately use one write: the old receiver lost later lines.
        burst = "\n".join([
            "FILE:PING", "FILE:PING", f"PC:TIME|{int(time.time())}",
            codex_packet(tokens, 0, day), "FILE:PING", ""
        ]).encode("ascii")
        port.write(burst)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            chunks.append(port.read(port.in_waiting or 1))
        # Also verify a command split across successive writes.
        port.write(b"FILE:PI")
        time.sleep(0.15)
        port.write(b"NG\r\n")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            chunks.append(port.read(port.in_waiting or 1))
    log = b"".join(chunks).decode("utf-8", "replace")
    out = pathlib.Path(__file__).resolve().parent.parent / "build/serial_burst_validation.log"
    out.parent.mkdir(exist_ok=True)
    out.write_text(log, encoding="utf-8")
    checks = {
        "home_ready": "Home dashboard ready" in log,
        "all_four_pings": log.count("FILE:PONG") == 4,
        "time_received": "clock synced from PC" in log,
        "codex_received": f"Codex usage online: {tokens} tokens" in log,
        "no_crash": not any(s in log for s in ("Guru Meditation", "abort()", "Task watchdog got triggered")),
    }
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    for line in log.splitlines():
        if any(s in line for s in ("Home dashboard ready", "Codex usage online", "FILE:PONG", "clock synced")):
            print(line)
    print(f"Validation log: {out}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
