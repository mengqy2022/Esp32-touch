import struct
import unittest
from unittest.mock import Mock, patch

from pc_screen import (WIDTH, HEIGHT, Mirror, checksum, encode_frame, map_point,
                       viewport, crop_viewport, map_view_point)
from pc_monitor_host import connect


class Serial:
    def __init__(self):
        self.incoming = b''
        self.written = []
    @property
    def in_waiting(self): return len(self.incoming)
    def read(self, count):
        result, self.incoming = self.incoming[:count], self.incoming[count:]
        return result
    def write(self, data): self.written.append(data)


class ScreenTests(unittest.TestCase):
    def test_rle_roundtrip_and_maximum_length(self):
        for data in (bytes(WIDTH * HEIGHT * 4), bytes([0, 0, 255, 0, 255, 0, 0, 0]) * (WIDTH * HEIGHT // 2)):
            encoded = encode_frame(data)
            decoded = b''.join(bytes([value]) * count for count, value in zip(encoded[::2], encoded[1::2]))
            self.assertEqual(len(decoded), WIDTH * HEIGHT)
            self.assertLessEqual(len(encoded), WIDTH * HEIGHT * 2)
            self.assertTrue(all(encoded[::2]))
        self.assertEqual(checksum(b'hello'), 0x4f9f2cab)
        with self.assertRaises(ValueError): encode_frame(b'bad')

    def test_letterbox_mapping_and_boundaries(self):
        self.assertEqual(viewport(320, 176), (0, 0, 320, 176))
        self.assertEqual(map_point(319, 175, (320, 176)), (319, 175))
        self.assertEqual(viewport(100, 100), (72, 0, 176, 176))
        with self.assertRaises(ValueError): map_point(71, 88, (100, 100))
        with self.assertRaises(ValueError): map_point(320, 0, (320, 176))
        for size in ((0, 100), (100, -1), (20000, 100)):
            with self.assertRaises(ValueError): viewport(*size)

    def test_partial_lines_and_input_requires_current_frame(self):
        import time
        window = Mock()
        mirror = Mirror(dict(hwnd=1), window)
        ser = Serial()
        ser.incoming = b'SCREEN:STA'
        mirror.read(ser)
        self.assertEqual(mirror.session, 0)
        ser.incoming = b'TE|21|0\nSCREEN:INPUT|21|1|10|10|20|20|0\n'
        mirror.read(ser)
        window.gesture.assert_not_called()
        self.assertEqual(mirror.session, 21)
        mirror.shown = 21, 1, (320, 176), time.monotonic()
        ser.incoming = b'SCREEN:INPUT|21|1|10|10|20|20|0\n'
        mirror.read(ser)
        window.gesture.assert_called_once_with(mirror.target, (320, 176), 10, 10, 20, 20, 0,
                                                {'zoom': 1, 'x': .5, 'y': .5})
        window.reset_mock()
        for data in (b'SCREEN:INPUT|22|1|10|10|20|20|0\n', b'SCREEN:INPUT|21|2|10|10|20|20|0\n',
                     b'SCREEN:INPUT|21|1|10|10|20|20|99\n', b'SCREEN:INPUT|x\n'):
            ser.incoming = data
            mirror.read(ser)
        window.gesture.assert_not_called()
        ser.incoming = b'SCREEN:STATE|0\n'
        mirror.read(ser)
        self.assertIsNone(mirror.shown)

    def test_no_payload_without_ready(self):
        window = Mock()
        window.capture.return_value = (b'\xff\x00', (320, 176))
        mirror = Mirror(dict(hwnd=1), window)
        mirror.session = 21
        ser = Serial()
        mirror.wait = Mock(return_value=False)
        mirror.tick(ser)
        self.assertEqual(len(ser.written), 3)
        self.assertEqual(ser.written[1], b'SCREEN:APP|generic|\n')
        self.assertTrue(ser.written[2].startswith(f'SCREEN:FRAME|21|{mirror.frame}|2|'.encode()))

    def test_successful_handshake_retains_mapping(self):
        window = Mock()
        window.capture.return_value = (b'\xff\x00', (320, 176))
        mirror = Mirror(dict(hwnd=1), window)
        mirror.session = 21
        mirror.wait = Mock(return_value=True)
        ser = Serial()
        mirror.tick(ser)
        self.assertEqual(ser.written[-1], b'\xff\x00')
        self.assertEqual(mirror.shown[:3], (21, mirror.frame, (320, 176)))

    def test_zoom_crop_and_mapping(self):
        self.assertEqual(crop_viewport(320, 176, 2, (.5, .5)), (80, 44, 160, 88))
        self.assertEqual(map_view_point(0, 0, (320, 176), 2, (.5, .5)), (80, 44))
        self.assertEqual(map_view_point(319, 175, (320, 176), 2, (.5, .5)), (239, 131))
        self.assertEqual(crop_viewport(1000, 100, 2), (409, 0, 181, 100))

    def test_device_view_command_changes_capture_view(self):
        window = Mock()
        window.capture.return_value = (b'\xff\x00', (320, 176))
        mirror = Mirror(dict(hwnd=1), window)
        mirror.session = 21
        mirror.wait = Mock(return_value=True)
        ser = Serial()
        mirror.tick(ser)
        ser.incoming = f'SCREEN:VIEW|21|{mirror.frame}|2|80|44\n'.encode()
        mirror.read(ser)
        self.assertEqual(mirror.view['zoom'], 2)

    def test_switch_clears_old_frame_and_capture_process(self):
        import time
        mirror = Mirror(dict(hwnd=1), Mock())
        mirror.shown = 21, 44, (320, 176), time.monotonic()
        mirror.session = 21
        ser = Serial()
        with patch('pc_screen.Window'):
            mirror.set_target(dict(hwnd=2, title='Yomi'), ser)
        self.assertIsNone(mirror.shown)
        ser.incoming = b'SCREEN:INPUT|21|44|10|10|10|10|0\n'
        mirror.read(ser)
        mirror.windows.gesture.assert_not_called()

    def test_media_command_requires_current_session(self):
        window = Mock()
        mirror = Mirror(dict(hwnd=1), window)
        mirror.session = 21
        ser = Serial()
        ser.incoming = b'SCREEN:COMMAND|22|play_pause\nSCREEN:COMMAND|21|play_pause\n'
        mirror.read(ser)
        window.command.assert_called_once_with(mirror.target, 'play_pause')

    def test_hung_capture_process_is_terminated(self):
        from pc_screen import CaptureProcess
        capture = CaptureProcess()
        capture.target = dict(hwnd=1)
        capture.process = Mock()
        capture.connection = Mock()
        capture.connection.poll.return_value = False
        process = capture.process
        with self.assertRaises(OSError):
            capture.capture(dict(hwnd=1), {})
        process.terminate.assert_called_once()
        self.assertIsNone(capture.process)

    def test_window_identity_can_use_pid_and_class_without_property(self):
        target = dict(hwnd=123, pid=77, class_name='Chrome_WidgetWin_1',
                      cookie=42, property_bound=False)
        self.assertEqual(target['property_bound'], False)

    def test_serial_connection_does_not_toggle_esp32_reset_lines(self):
        fake = Mock()
        with patch('pc_monitor_host.serial.Serial', return_value=fake) as serial_open:
            self.assertIs(connect('COM5'), fake)
        serial_open.assert_called_once_with(port=None, baudrate=115200, timeout=0.2, write_timeout=18)
        self.assertFalse(fake.dtr)
        self.assertFalse(fake.rts)
        self.assertEqual(fake.port, 'COM5')
        fake.open.assert_called_once_with()


if __name__ == '__main__': unittest.main()
