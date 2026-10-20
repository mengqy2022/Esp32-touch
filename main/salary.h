#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

#define SALARY_OVERRIDES 32
#define SALARY_MAX_FEN 100000000u

typedef struct {
    uint32_t monthly_fen;
    uint16_t times[4]; // Minutes since midnight: start, lunch, resume, finish.
    uint8_t weekdays; // Bit 0 = Monday, bit 6 = Sunday.
    uint8_t use_calendar;
    uint8_t boot_cat;
    uint8_t reserved;
} salary_config_t;

typedef struct {
    uint32_t date; // YYYYMMDD, zero = unused.
    uint8_t work;
    uint8_t reserved[3];
} salary_override_t;

typedef struct {
    uint16_t year;
    uint16_t known_months;
    uint32_t work[12];
    uint32_t rest[12];
} salary_calendar_t;

typedef struct {
    salary_config_t config;
    salary_override_t overrides[SALARY_OVERRIDES];
    salary_calendar_t calendar;
} salary_data_t;

typedef enum {
    SALARY_BEFORE, SALARY_MORNING, SALARY_LUNCH, SALARY_AFTERNOON,
    SALARY_DONE, SALARY_REST
} salary_phase_t;

typedef struct {
    salary_phase_t phase;
    bool workday, calendar_known;
    int workdays, worked_seconds, daily_seconds, countdown;
    int64_t today_fen, month_fen, annual_fen;
} salary_result_t;

void salary_defaults(salary_config_t *config);
bool salary_config_valid(const salary_config_t *config);
int salary_month_days(int year, int month);
bool salary_date_valid(uint32_t date);
bool salary_workday(const salary_data_t *data, int year, int month, int day);
bool salary_set_override(salary_data_t *data, uint32_t date, int mode); // -1 automatic, 0 rest, 1 work
bool salary_calculate(const salary_data_t *data, const struct tm *local, salary_result_t *out);
bool salary_calendar_packet(salary_calendar_t *calendar, const char *line);
