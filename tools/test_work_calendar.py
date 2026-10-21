import json
from pathlib import Path
import re
import tempfile
import unittest

from work_calendar import CalendarSync, calendar_packets, load_calendar

ROOT = Path(__file__).resolve().parent.parent


class CalendarTests(unittest.TestCase):
    def test_default_and_firmware_agree(self):
        data = load_calendar()
        packets = calendar_packets(data)
        self.assertEqual(len(packets), 12)
        masks = [line.split('|') for line in packets]
        header = (ROOT / 'main/salary_calendar_default.h').read_text()
        for name, index in (('work', 3), ('rest', 4)):
            values = re.search(r'\.' + name + r' = \{([^}]+)\}', header)[1]
            self.assertEqual([int(v, 16) for v in values.split(',')], [int(v[index], 16) for v in masks])
        self.assertEqual(int(masks[9][3], 16), 1 << 9)
        self.assertEqual(int(masks[9][4], 16), 0x7f)

    def test_invalid_dates_and_conflicts(self):
        bad = [dict(year=True, work=[], rest=[]), dict(year=2026, work=['2026-02-29'], rest=[]),
               dict(year=2026, work=['2027-01-01'], rest=[]),
               dict(year=2026, work=['2026-01-01'], rest=['2026-01-01']),
               dict(year=2026, work=['2026-01-01'] * 2, rest=[]),
               dict(year=2026, work='2026-01-01', rest=[]),
               dict(year=2026, work=['20260101'], rest=[])]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                calendar_packets(data)

    def test_unknown_year_is_not_claimed_as_covered(self):
        self.assertEqual(CalendarSync().packets(2027), [])

    def test_custom_calendar_reloads_and_repeats_for_device_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'work_calendar.json'
            path.write_text(json.dumps(dict(year=2027, work=['2027-01-02'], rest=[])))
            sync = CalendarSync(directory)
            first = sync.packets(2027)
            self.assertEqual(first, sync.packets(2027))
            path.write_text(json.dumps(dict(year=2027, work=[], rest=['2027-01-02'])))
            self.assertNotEqual(first, sync.packets(2027))

    def test_all_animation_frames_decode_to_expected_size(self):
        header = (ROOT / 'main/salary_cat_frames.h').read_text()
        frames = re.findall(r'\{(\d+), (\d+), (\d+)\}', header)
        data = (ROOT / 'main/salary_cat.rle').read_bytes()
        offset = 0
        decoded_frames = []
        for start, length, duration in frames:
            start, length, duration = map(int, (start, length, duration))
            self.assertEqual(start, offset)
            self.assertGreaterEqual(duration, 70)
            payload = data[start:start + length]
            self.assertEqual(len(payload), length)
            self.assertEqual(length % 2, 0)
            self.assertTrue(all(payload[::2]))
            self.assertEqual(sum(payload[::2]), 112 * 112)
            pixels = b''.join(bytes([value]) * count for count, value in zip(payload[::2], payload[1::2]))
            self.assertIn(0, pixels, 'Each frame must retain a transparent background')
            decoded_frames.append(pixels)
            offset += length
        self.assertEqual(offset, len(data))
        ranges = re.findall(r'\{(\d+), (\d+)\}', header)
        self.assertEqual(len(ranges), 8)
        start = 0
        for first, count in ranges:
            self.assertEqual(int(first), start)
            self.assertGreater(int(count), 1)
            self.assertGreater(len(set(decoded_frames[int(first):int(first) + int(count)])), 1,
                               'Each weekday must contain changing animation frames')
            start += int(count)
        self.assertEqual(start, len(frames))

    def test_salary_font_covers_all_page_text(self):
        text = (ROOT / 'main/salary_ui.c').read_text(encoding='utf-8')
        font = (ROOT / 'main/font_salary16.c').read_text(encoding='utf-8')
        points = re.search(r'codepoints\[\] = \{([^}]+)', font)[1]
        covered = {int(value, 16) for value in points.split(',')}
        self.assertFalse({ord(c) for c in text if ord(c) > 127} - covered)


if __name__ == '__main__':
    unittest.main()
