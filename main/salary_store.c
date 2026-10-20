#include "salary_store.h"
#include "salary_calendar_default.h"
#include <string.h>
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"

static salary_data_t s_data;
static SemaphoreHandle_t s_lock;

static esp_err_t write_blob(const char *key, const void *value, size_t size)
{
    nvs_handle_t handle;
    esp_err_t error = nvs_open("salary_cat", NVS_READWRITE, &handle);
    if (error != ESP_OK) return error;
    error = nvs_set_blob(handle, key, value, size);
    if (error == ESP_OK) error = nvs_commit(handle);
    nvs_close(handle);
    return error;
}

void salary_store_init(void)
{
    s_lock = xSemaphoreCreateMutex();
    configASSERT(s_lock);
    salary_defaults(&s_data.config);
    s_data.calendar = salary_default_calendar;
    nvs_handle_t handle;
    if (nvs_open("salary_cat", NVS_READONLY, &handle) != ESP_OK) return;
    salary_config_t config;
    size_t size = sizeof(config);
    if (nvs_get_blob(handle, "config_v1", &config, &size) == ESP_OK &&
        size == sizeof(config) && salary_config_valid(&config)) s_data.config = config;
    salary_override_t overrides[SALARY_OVERRIDES];
    size = sizeof(overrides);
    if (nvs_get_blob(handle, "dates_v1", overrides, &size) == ESP_OK && size == sizeof(overrides)) {
        for (int i = 0; i < SALARY_OVERRIDES; ++i)
            if (salary_date_valid(overrides[i].date) && overrides[i].work <= 1)
                salary_set_override(&s_data, overrides[i].date, overrides[i].work);
    }
    salary_calendar_t calendar;
    size = sizeof(calendar);
    if (nvs_get_blob(handle, "calendar_v1", &calendar, &size) == ESP_OK && size == sizeof(calendar) &&
        calendar.year >= salary_default_calendar.year && calendar.year <= 2099 && calendar.known_months == 0xfff) {
        bool valid = true;
        for (int month = 0; month < 12; ++month) {
            uint32_t allowed = UINT32_MAX >> (32 - salary_month_days(calendar.year, month + 1));
            if ((calendar.work[month] & calendar.rest[month]) ||
                ((calendar.work[month] | calendar.rest[month]) & ~allowed)) valid = false;
        }
        if (valid) s_data.calendar = calendar;
    }
    nvs_close(handle);
}

void salary_store_snapshot(salary_data_t *out)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    *out = s_data;
    xSemaphoreGive(s_lock);
}

esp_err_t salary_store_config(const salary_config_t *config)
{
    if (!salary_config_valid(config)) return ESP_ERR_INVALID_ARG;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    esp_err_t error = ESP_OK;
    if (memcmp(config, &s_data.config, sizeof(*config))) {
        error = write_blob("config_v1", config, sizeof(*config));
        if (error == ESP_OK) s_data.config = *config;
    }
    xSemaphoreGive(s_lock);
    return error;
}

esp_err_t salary_store_override(uint32_t date, int mode)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    salary_data_t next = s_data;
    esp_err_t error = salary_set_override(&next, date, mode) ? ESP_OK : ESP_ERR_INVALID_ARG;
    if (error == ESP_OK && memcmp(next.overrides, s_data.overrides, sizeof(next.overrides))) {
        error = write_blob("dates_v1", next.overrides, sizeof(next.overrides));
        if (error == ESP_OK) memcpy(s_data.overrides, next.overrides, sizeof(next.overrides));
    }
    xSemaphoreGive(s_lock);
    return error;
}

esp_err_t salary_store_calendar(const char *packet)
{
    // Accumulate all 12 months before replacing a usable offline calendar.
    static salary_calendar_t pending;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    esp_err_t error = salary_calendar_packet(&pending, packet) ? ESP_OK : ESP_ERR_INVALID_ARG;
    if (error == ESP_OK && pending.known_months == 0xfff &&
        memcmp(&pending, &s_data.calendar, sizeof(pending))) {
        error = write_blob("calendar_v1", &pending, sizeof(pending));
        if (error == ESP_OK) s_data.calendar = pending;
    }
    if (error == ESP_OK && pending.known_months == 0xfff) memset(&pending, 0, sizeof(pending));
    xSemaphoreGive(s_lock);
    return error;
}
