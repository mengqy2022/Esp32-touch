"""Windows login agent: wait for the configured USB device and supervise telemetry."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import time

import serial.tools.list_ports


def matching_port(ports, device):
    matches = [p for p in ports if p.vid == device['vid'] and p.pid == device['pid']]
    serial_number = device.get('serial_number')
    if serial_number:
        matches = [p for p in matches if p.serial_number == serial_number]
    if len(matches) == 1:
        return matches[0].device
    for key in ('location', 'device'):
        preferred = device.get(key)
        if preferred:
            selected = [p for p in matches if getattr(p, key, None) == preferred]
            if len(selected) == 1:
                return selected[0].device
    return None


class LogStream:
    def __init__(self, logger):
        self.logger = logger
        self.buffer = ''
    def write(self, text):
        self.buffer += text
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            if line:
                self.logger.info(line)
        return len(text)
    def flush(self):
        pass


def run_agent(config_path, quit_event=None):
    config_path = Path(config_path).resolve()
    runtime = config_path.parent
    runtime.mkdir(parents=True, exist_ok=True)
    lock = (runtime / 'agent.lock').open('a+b')
    lock.seek(0)
    if lock.read(1) == b'':
        lock.write(b'0')
        lock.flush()
    lock.seek(0)
    import msvcrt
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock.close()
        return
    logger = logging.getLogger('dashboard')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(runtime / 'host.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    sys.stdout = sys.stderr = LogStream(logger)
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    from pc_monitor_host import main as host_main
    (runtime / 'agent.pid').write_text(str(os.getpid()), encoding='ascii')
    logger.info('Agent started; waiting for USB device %04X:%04X', config['device']['vid'], config['device']['pid'])
    worker = None
    stop_worker = None
    connected = None
    previous_state = None
    quit_event = quit_event or threading.Event()
    try:
        while not quit_event.is_set():
            paused = (runtime / 'paused').exists()
            port = None if paused else matching_port(serial.tools.list_ports.comports(), config['device'])
            state = 'paused' if paused else port or 'waiting for device'
            if state != previous_state:
                logger.info('State: %s', state)
                previous_state = state
            if worker and (not worker.is_alive() or port != connected):
                stop_worker.set()
                worker.join(timeout=12)
                if worker.is_alive():
                    quit_event.wait(1)
                    continue
                worker = None
                connected = None
            if port and worker is None:
                options = ['--port', port, '--codex-refresh', str(config.get('codex_refresh', 5)),
                           '--codex-daily-goal', str(config.get('daily_goal', 0)),
                           '--codex-prices', str(runtime / 'codex_prices.json')]
                stop_worker = threading.Event()
                worker = threading.Thread(target=host_main, args=(options, stop_worker), daemon=True)
                worker.start()
                connected = port
                logger.info('Telemetry started on %s (in-process)', port)
            quit_event.wait(2)
    finally:
        if stop_worker:
            stop_worker.set()
        if worker:
            worker.join(timeout=12)
        (runtime / 'agent.pid').unlink(missing_ok=True)
        handler.close()
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    run_agent(args.config)


if __name__ == '__main__':
    main()
