#pragma once
#include <stdbool.h>
#include "lvgl.h"

#define PC_SCREEN_W 160
#define PC_SCREEN_H 88
void pc_screen_init(void);
lv_color_t *pc_screen_open(void); // LVGL thread only
void pc_screen_close(void);
bool pc_screen_refresh(char *status, unsigned size); // LVGL thread only
void pc_screen_gesture(int x1, int y1, int x2, int y2, int wheel);
void pc_screen_handle_line(const char *line); // UART owner only
