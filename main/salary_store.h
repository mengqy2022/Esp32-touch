#pragma once
#include "salary.h"
#include "esp_err.h"

void salary_store_init(void);
void salary_store_snapshot(salary_data_t *out);
esp_err_t salary_store_config(const salary_config_t *config);
esp_err_t salary_store_override(uint32_t date, int mode);
esp_err_t salary_store_calendar(const char *packet);
