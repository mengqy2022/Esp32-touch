#include "salary.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

void salary_defaults(salary_config_t *c)
{
    *c = (salary_config_t){.monthly_fen = 600000, .times = {540, 720, 840, 1020},
                           .weekdays = 0x1f, .use_calendar = 1};
}

bool salary_config_valid(const salary_config_t *c)
{
    return c && c->monthly_fen <= SALARY_MAX_FEN && c->weekdays && !(c->weekdays & 0x80) &&
           c->use_calendar <= 1 && c->boot_cat <= 1 && c->times[0] < c->times[1] &&
           c->times[1] <= c->times[2] && c->times[2] < c->times[3] && c->times[3] < 1440;
}

int salary_month_days(int year, int month)
{
    static const int days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (year < 2000 || year > 2099 || month < 1 || month > 12) return 0;
    return days[month - 1] + (month == 2 && year % 4 == 0);
}

bool salary_date_valid(uint32_t date)
{
    int days = salary_month_days(date / 10000, date / 100 % 100);
    return date % 100 > 0 && date % 100 <= (unsigned)days;
}

static int weekday(int year, int month, int day)
{
    static const int offsets[] = {0,3,2,5,0,3,5,1,4,6,2,4};
    year -= month < 3;
    int sunday = (year + year / 4 - year / 100 + year / 400 + offsets[month - 1] + day) % 7;
    return (sunday + 6) % 7;
}

bool salary_workday(const salary_data_t *d, int year, int month, int day)
{
    uint32_t date = year * 10000 + month * 100 + day;
    if (!salary_date_valid(date)) return false;
    for (int i = 0; i < SALARY_OVERRIDES; ++i)
        if (d->overrides[i].date == date) return d->overrides[i].work;
    if (d->config.use_calendar && d->calendar.year == year &&
        (d->calendar.known_months & (1u << (month - 1)))) {
        uint32_t bit = 1u << (day - 1);
        if (d->calendar.work[month - 1] & bit) return true;
        if (d->calendar.rest[month - 1] & bit) return false;
    }
    return (d->config.weekdays & (1u << weekday(year, month, day))) != 0;
}

bool salary_set_override(salary_data_t *d, uint32_t date, int mode)
{
    if (!salary_date_valid(date) || mode < -1 || mode > 1) return false;
    int empty = -1;
    for (int i = 0; i < SALARY_OVERRIDES; ++i) {
        if (!d->overrides[i].date) empty = i;
        if (d->overrides[i].date == date) {
            d->overrides[i] = (salary_override_t){.date = mode < 0 ? 0 : date, .work = mode > 0};
            return true;
        }
    }
    if (mode < 0) return true;
    if (empty < 0) return false;
    d->overrides[empty] = (salary_override_t){.date = date, .work = mode > 0};
    return true;
}

bool salary_calculate(const salary_data_t *d, const struct tm *t, salary_result_t *out)
{
    if (!d || !t || !out || !salary_config_valid(&d->config)) return false;
    int year = t->tm_year + 1900, month = t->tm_mon + 1;
    if (!salary_date_valid(year * 10000 + month * 100 + t->tm_mday) ||
        t->tm_hour < 0 || t->tm_hour > 23 || t->tm_min < 0 || t->tm_min > 59 ||
        t->tm_sec < 0 || t->tm_sec > 60) return false;
    *out = (salary_result_t){.annual_fen = (int64_t)d->config.monthly_fen * 12,
        .calendar_known = d->calendar.year == year && (d->calendar.known_months & (1u << (month - 1)))};
    int completed = 0;
    for (int day = 1; day <= salary_month_days(year, month); ++day) {
        if (salary_workday(d, year, month, day)) {
            ++out->workdays;
            if (day < t->tm_mday) ++completed;
        }
    }
    int now = t->tm_hour * 3600 + t->tm_min * 60 + t->tm_sec;
    int a = d->config.times[0] * 60, b = d->config.times[1] * 60;
    int c = d->config.times[2] * 60, e = d->config.times[3] * 60;
    out->daily_seconds = b - a + e - c;
    out->workday = salary_workday(d, year, month, t->tm_mday);
    if (!out->workday) out->phase = SALARY_REST;
    else if (now < a) { out->phase = SALARY_BEFORE; out->countdown = a - now; }
    else if (now < b) { out->phase = SALARY_MORNING; out->countdown = b - now; out->worked_seconds = now - a; }
    else if (now < c) { out->phase = SALARY_LUNCH; out->countdown = c - now; out->worked_seconds = b - a; }
    else if (now < e) { out->phase = SALARY_AFTERNOON; out->countdown = e - now; out->worked_seconds = b - a + now - c; }
    else { out->phase = SALARY_DONE; out->worked_seconds = out->daily_seconds; }
    int64_t seconds = (int64_t)out->workdays * out->daily_seconds;
    if (seconds) {
        out->today_fen = (int64_t)d->config.monthly_fen * out->worked_seconds / seconds;
        out->month_fen = (int64_t)d->config.monthly_fen *
                        ((int64_t)completed * out->daily_seconds + out->worked_seconds) / seconds;
    }
    return true;
}

bool salary_calendar_packet(salary_calendar_t *cal, const char *line)
{
    if (!cal || !line || strncmp(line, "CAL|", 4)) return false;
    unsigned values[4];
    const char *cursor = line + 4;
    for (int i = 0; i < 4; ++i) {
        const char *start = cursor;
        while ((*cursor >= '0' && *cursor <= '9') ||
               (i >= 2 && ((*cursor >= 'a' && *cursor <= 'f') || (*cursor >= 'A' && *cursor <= 'F')))) ++cursor;
        if (cursor == start || cursor - start > (i < 2 ? 4 : 8) || *cursor != (i < 3 ? '|' : 0)) return false;
        errno = 0;
        unsigned long value = strtoul(start, NULL, i < 2 ? 10 : 16);
        if (errno || value > UINT32_MAX) return false;
        values[i] = value;
        if (i < 3) ++cursor;
    }
    unsigned year = values[0], month = values[1], work = values[2], rest = values[3];
    if (!salary_month_days(year, month) || (work & rest)) return false;
    uint32_t allowed = UINT32_MAX >> (32 - salary_month_days(year, month));
    if ((work | rest) & ~allowed) return false;
    if (cal->year != year) *cal = (salary_calendar_t){.year = year};
    cal->work[month - 1] = work;
    cal->rest[month - 1] = rest;
    cal->known_months |= 1u << (month - 1);
    return true;
}
