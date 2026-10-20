"""Validated annual exceptions to the user's weekly schedule; no network calls."""
import datetime as dt
import json
from pathlib import Path
import sys


def calendar_packets(data):
    if not isinstance(data, dict):
        raise ValueError('日历必须为 JSON 对象')
    year = data['year']
    if type(year) is not int or not 2000 <= year <= 2099:
        raise ValueError('日历年份必须为 2000–2099')
    masks = [[0, 0] for _ in range(12)]
    seen = set()
    for kind, name in enumerate(('work', 'rest')):
        if not isinstance(data[name], list) or len(data[name]) > 366:
            raise ValueError('work/rest 必须为日期列表')
        for text in data[name]:
            if not isinstance(text, str) or len(text) != 10:
                raise ValueError('日期格式必须为 YYYY-MM-DD')
            date = dt.date.fromisoformat(text)
            if date.year != year or text in seen:
                raise ValueError('日历日期重复、冲突或年份不符')
            seen.add(text)
            masks[date.month - 1][kind] |= 1 << (date.day - 1)
    return [f'SALARY:CAL|{year}|{month}|{work:x}|{rest:x}'
            for month, (work, rest) in enumerate(masks, 1)]


def load_calendar(path=None):
    if path is None:
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        path = base / 'work_calendar.json'
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    calendar_packets(data)
    return data


class CalendarSync:
    def __init__(self, runtime=None):
        self.path = Path(runtime) / 'work_calendar.json' if runtime else None

    def packets(self, year):
        data = load_calendar(self.path if self.path and self.path.exists() else None)
        if data['year'] != year:
            return []
        return calendar_packets(data)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware-header', type=Path, required=True)
    args = parser.parse_args()
    data = load_calendar()
    rows = [line.split('|') for line in calendar_packets(data)]
    text = '// Generated from tools/work_calendar.json; see its source URL.\n#pragma once\n'
    text += '#include "salary.h"\nstatic const salary_calendar_t salary_default_calendar = {\n'
    text += f'    .year = {data["year"]}, .known_months = 0xfff,\n'
    text += '    .work = {' + ','.join('0x' + row[3] for row in rows) + '},\n'
    text += '    .rest = {' + ','.join('0x' + row[4] for row in rows) + '}\n};\n'
    args.firmware_header.write_text(text, encoding='utf-8')
