#pragma once
#include "lvgl.h"

typedef struct {
    lv_color_t bg;
    lv_color_t panel;
    lv_color_t panel2;
    lv_color_t primary;
    lv_color_t accent;
    lv_color_t text;
    lv_color_t text_dim;
    lv_coord_t radius;
    lv_coord_t padding;
} ui_theme_t;

const ui_theme_t *ui_theme_get(void);
void ui_theme_apply_screen(lv_obj_t *screen);
lv_obj_t *ui_create_card(lv_obj_t *parent);
lv_obj_t *ui_create_title(lv_obj_t *parent, const char *text);
