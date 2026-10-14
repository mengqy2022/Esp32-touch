#pragma once
#include "lvgl.h"

lv_obj_t *ui_create_action_button(lv_obj_t *parent, const char *text, lv_event_cb_t cb, int id);
lv_obj_t *ui_create_status_bar(lv_obj_t *parent);
