#include "salary.h"
#include "salary_calendar_default.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static salary_result_t calculate(salary_data_t *data, int year, int month, int day, int hour, int minute, int second)
{
    struct tm local = {.tm_year = year - 1900, .tm_mon = month - 1, .tm_mday = day,
                       .tm_hour = hour, .tm_min = minute, .tm_sec = second};
    salary_result_t result;
    assert(salary_calculate(data, &local, &result));
    return result;
}

int main(void)
{
    salary_data_t data = {.calendar = salary_default_calendar};
    salary_defaults(&data.config);
    assert(salary_config_valid(&data.config));
    assert(salary_month_days(2024, 2) == 29 && salary_month_days(2026, 2) == 28);
    assert(!salary_date_valid(20260229) && !salary_date_valid(20261301));
    assert(!salary_date_valid(19991231) && salary_date_valid(20240229));
    assert(!salary_workday(&data, 2026, 10, 1));
    assert(salary_workday(&data, 2026, 10, 10)); // Saturday makeup day.
    assert(!salary_workday(&data, 2026, 10, 11));
    salary_result_t result = calculate(&data, 2026, 10, 20, 8, 0, 0);
    assert(result.phase == SALARY_BEFORE && result.countdown == 3600 && !result.today_fen);
    assert(result.workdays == 18 && result.daily_seconds == 21600 && result.annual_fen == 7200000);
    result = calculate(&data, 2026, 10, 20, 9, 0, 0);
    assert(result.phase == SALARY_MORNING && result.worked_seconds == 0 && result.countdown == 10800);
    result = calculate(&data, 2026, 10, 20, 10, 30, 0);
    assert(result.today_fen == 8333 && result.worked_seconds == 5400);
    result = calculate(&data, 2026, 10, 20, 12, 0, 0);
    assert(result.phase == SALARY_LUNCH && result.worked_seconds == 10800 && result.countdown == 7200);
    assert(result.today_fen == calculate(&data, 2026, 10, 20, 13, 59, 59).today_fen);
    result = calculate(&data, 2026, 10, 20, 14, 0, 0);
    assert(result.phase == SALARY_AFTERNOON && result.countdown == 10800 && result.worked_seconds == 10800);
    result = calculate(&data, 2026, 10, 20, 17, 0, 0);
    assert(result.phase == SALARY_DONE && result.worked_seconds == 21600 && result.countdown == 0);
    assert(result.today_fen == calculate(&data, 2026, 10, 20, 23, 59, 59).today_fen);
    result = calculate(&data, 2026, 10, 31, 17, 0, 0);
    assert(result.month_fen == data.config.monthly_fen && result.phase == SALARY_REST);
    result = calculate(&data, 2027, 1, 4, 10, 0, 0);
    assert(result.workday && !result.calendar_known);
    assert(salary_set_override(&data, 20261010, 0));
    assert(!salary_workday(&data, 2026, 10, 10));
    assert(salary_set_override(&data, 20261001, 1));
    assert(salary_workday(&data, 2026, 10, 1));
    assert(salary_set_override(&data, 20261001, -1));
    assert(!salary_workday(&data, 2026, 10, 1));
    data.config.use_calendar = 0;
    assert(!salary_workday(&data, 2026, 10, 10));
    assert(salary_workday(&data, 2026, 10, 1));
    data.config.weekdays = 0x7f;
    assert(salary_workday(&data, 2026, 10, 11));
    data.config.monthly_fen = SALARY_MAX_FEN;
    result = calculate(&data, 2026, 10, 31, 23, 59, 59);
    assert(result.month_fen == SALARY_MAX_FEN && result.annual_fen == (int64_t)SALARY_MAX_FEN * 12);
    memset(data.overrides, 0, sizeof(data.overrides));
    for (int day = 1; day <= 31; ++day) assert(salary_set_override(&data, 20260100 + day, 0));
    assert(salary_set_override(&data, 20260201, 1));
    assert(!salary_set_override(&data, 20260202, 1));
    assert(salary_set_override(&data, 20260101, -1));
    assert(salary_set_override(&data, 20260202, 1));
    data.config.weekdays = 0;
    assert(!salary_config_valid(&data.config));
    salary_defaults(&data.config);
    data.config.times[2] = 700;
    assert(!salary_config_valid(&data.config));
    salary_defaults(&data.config);
    data.config.times[3] = 1440;
    assert(!salary_config_valid(&data.config));
    salary_calendar_t calendar = {0};
    assert(salary_calendar_packet(&calendar, "CAL|2026|2|2000|4000"));
    assert(calendar.year == 2026 && calendar.work[1] == 0x2000 && calendar.known_months == 2);
    const char *bad[] = {"CAL|2026|2|10000000|0", "CAL|2026|1|1|1", "CAL|2026|13|0|0", "CAL|2026|1|0|0|extra",
                         "CAL|-2026|1|0|0", "CAL|2026|1|-1|0", "CAL|2026|1|fffffffff|0", "CAL|2026|1||0"};
    salary_calendar_t before = calendar;
    for (unsigned i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
        assert(!salary_calendar_packet(&calendar, bad[i]));
        assert(!memcmp(&before, &calendar, sizeof(before)));
    }
    assert(salary_calendar_packet(&calendar, "CAL|2027|1|0|0"));
    assert(calendar.year == 2027 && calendar.known_months == 1);
    puts("PASS: salary boundaries, lunch, weekends/makeup days, overrides, monthly cap, leap year, money limits and calendar validation");
    return 0;
}
