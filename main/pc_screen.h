#pragma once
#include <stdbool.h>
#include "lvgl.h"

#define PC_SCREEN_W 320
#define PC_SCREEN_H 176
// The wire frame keeps the full panel size; the no-PSRAM target stores a
// slightly smaller indexed image and scales it to the same display rectangle.
#define PC_SCREEN_BUF_W 256
#define PC_SCREEN_BUF_H 140
void pc_screen_init(void);
uint8_t *pc_screen_open(void); // LVGL thread only; palette (1 KiB) + RGB332 pixels
void pc_screen_close(void);
bool pc_screen_refresh(char *status, unsigned size); // LVGL thread only
void pc_screen_gesture(int x1, int y1, int x2, int y2, int wheel);
void pc_screen_view(int zoom, int x, int y, bool pan);
void pc_screen_command(const char *command);
void pc_screen_get_app(char *app, unsigned app_size, char *title, unsigned title_size);
void pc_screen_handle_line(const char *line); // UART owner only
