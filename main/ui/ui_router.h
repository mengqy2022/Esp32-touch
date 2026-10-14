
#pragma once
#include "lvgl.h"

typedef enum {
    SCREEN_HOME = 0,
    SCREEN_WIFI,
    SCREEN_MONITOR,
    SCREEN_SETTINGS
} ui_screen_id_t;

void ui_router_init(void);
void ui_router_show(ui_screen_id_t id);
