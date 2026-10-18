#include "pc_screen.h"
#include "ui.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include "driver/uart.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"

#define WIRE_PIXELS (PC_SCREEN_W * PC_SCREEN_H)
#define PIXELS (PC_SCREEN_BUF_W * PC_SCREEN_BUF_H)
#define PALETTE_BYTES (256 * sizeof(lv_color32_t))
static SemaphoreHandle_t s_lock;
static uint8_t *s_pixels;
static uint32_t s_session, s_frame;
static bool s_ready;
static int64_t s_received;
static char s_status[64] = "Select a window in the PC dashboard";
static char s_app[16] = "generic";
static char s_title[96] = "";
static const char *TAG = "pcscreen";

static void reply(const char *message) { uart_write_bytes(UART_NUM_0, message, strlen(message)); }
void pc_screen_init(void) { s_lock = xSemaphoreCreateMutex(); configASSERT(s_lock); ESP_LOGI(TAG, "screen protocol ready"); }

uint8_t *pc_screen_open(void)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    if (s_session && s_pixels) {
        uint8_t *result = s_pixels;
        xSemaphoreGive(s_lock);
        return result;
    }
    if (!s_pixels) {
        s_pixels = calloc(PALETTE_BYTES + PIXELS, 1);
        if (s_pixels) {
            lv_color32_t *palette = (lv_color32_t *)s_pixels;
            for (unsigned i = 0; i < 256; ++i) {
                palette[i].ch.red = ((i >> 5) & 7) * 255 / 7;
                palette[i].ch.green = ((i >> 2) & 7) * 255 / 7;
                palette[i].ch.blue = (i & 3) * 255 / 3;
                palette[i].ch.alpha = 255;
            }
        }
    }
    s_frame = 0;
    s_ready = false;
    s_received = 0;
    s_session = s_pixels ? (esp_random() | 1) : 0;
    snprintf(s_status, sizeof(s_status), "%s", s_session ? "Select a window in the PC dashboard" : "Not enough memory");
    ESP_LOGI(TAG, "screen open: pixels=%p session=%"PRIu32, s_pixels, s_session);
    uint8_t *result = s_session ? s_pixels : NULL;
    xSemaphoreGive(s_lock);
    return result;
}

void pc_screen_close(void)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    s_session = 0;
    free(s_pixels); s_pixels = NULL;
    s_ready = false;
    snprintf(s_app, sizeof(s_app), "generic");
    s_title[0] = 0;
    xSemaphoreGive(s_lock);
}

bool pc_screen_refresh(char *status, unsigned size)
{
    if (xSemaphoreTake(s_lock, 0) != pdTRUE) return false;
    bool changed = s_ready;
    if (changed && s_pixels) {
        s_ready = false;
    }
    if (s_received && esp_timer_get_time() - s_received > 25000000)
        snprintf(s_status, sizeof(s_status), "Waiting for PC / window unavailable");
    snprintf(status, size, "%s", s_status);
    xSemaphoreGive(s_lock);
    return changed;
}

void pc_screen_gesture(int x1, int y1, int x2, int y2, int wheel)
{
    char message[128];
    xSemaphoreTake(s_lock, portMAX_DELAY);
    // Never act on a frame which has not reached the display yet.
    if (s_session && s_frame && !s_ready && esp_timer_get_time() - s_received < 25000000) {
        snprintf(message, sizeof(message), "SCREEN:INPUT|%"PRIu32"|%"PRIu32"|%d|%d|%d|%d|%d\n",
                 s_session, s_frame, x1, y1, x2, y2, wheel);
        reply(message);
    }
    xSemaphoreGive(s_lock);
}

void pc_screen_view(int zoom, int x, int y, bool pan)
{
    char message[64];
    xSemaphoreTake(s_lock, portMAX_DELAY);
    if (s_session) {
        zoom = zoom < 1 ? 1 : zoom > 8 ? 8 : zoom;
        snprintf(message, sizeof(message), "SCREEN:%s|%"PRIu32"|%"PRIu32"|%d|%d|%d\n",
                 pan ? "PAN" : "VIEW", s_session, s_frame, zoom, x, y);
        reply(message);
    }
    xSemaphoreGive(s_lock);
}

void pc_screen_command(const char *command)
{
    char message[96];
    xSemaphoreTake(s_lock, portMAX_DELAY);
    if (s_session && command && *command) {
        snprintf(message, sizeof(message), "SCREEN:COMMAND|%"PRIu32"|%.40s\n", s_session, command);
        reply(message);
    }
    xSemaphoreGive(s_lock);
}

void pc_screen_get_app(char *app, unsigned app_size, char *title, unsigned title_size)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    if (app && app_size) snprintf(app, app_size, "%s", s_app);
    if (title && title_size) snprintf(title, title_size, "%s", s_title);
    xSemaphoreGive(s_lock);
}

void pc_screen_handle_line(const char *line)
{
    char message[96], extra;
    if (!strcmp(line, "OPEN")) { ESP_LOGI(TAG, "SCREEN OPEN"); ui_set_screen(SCREEN_PC_SCREEN); return; }
    if (!strcmp(line, "CLOSE")) { ui_set_screen(SCREEN_SYSTEM_MENU); return; }
    if (!strcmp(line, "?")) {
        xSemaphoreTake(s_lock, portMAX_DELAY);
        snprintf(message, sizeof(message), "SCREEN:STATE|%"PRIu32"|%"PRIu32"\n", s_session, s_ready ? 0 : s_frame);
        xSemaphoreGive(s_lock);
        reply(message);
        return;
    }
    if (!strncmp(line, "STATUS|", 7)) {
        xSemaphoreTake(s_lock, portMAX_DELAY);
        snprintf(s_status, sizeof(s_status), "%.63s", line + 7);
        s_received = 0;
        s_frame = 0;
        if (s_pixels) memset(s_pixels + PALETTE_BYTES, 0, PIXELS);
        s_ready = false;
        xSemaphoreGive(s_lock);
        return;
    }
    if (!strncmp(line, "APP|", 4)) {
        char app[16] = "generic", title[96] = "";
        sscanf(line + 4, "%15[^|]|%95[^\n]", app, title);
        xSemaphoreTake(s_lock, portMAX_DELAY);
        bool changed = strcmp(s_app, app) != 0 || strcmp(s_title, title) != 0;
        snprintf(s_app, sizeof(s_app), "%s", app);
        snprintf(s_title, sizeof(s_title), "%s", title);
        xSemaphoreGive(s_lock);
        if (changed) {
            xSemaphoreTake(s_lock, portMAX_DELAY);
            if (s_session) s_session = esp_random() | 1;
            s_frame = 0;
            s_ready = false;
            if (s_pixels) memset(s_pixels + PALETTE_BYTES, 0, PIXELS);
            xSemaphoreGive(s_lock);
            if (ui_get_screen() == SCREEN_PC_SCREEN) ui_draw_all();
        }
        return;
    }
    uint32_t session, frame, expected;
    unsigned length;
    if (sscanf(line, "FRAME|%"SCNu32"|%"SCNu32"|%u|%"SCNu32"%c", &session, &frame, &length, &expected, &extra) != 4 ||
        length < 2 || length > WIRE_PIXELS * 2 || length % 2 || !frame) {
        reply("SCREEN:ERR|header\n"); return;
    }
    // Reject rather than block the LVGL task while serial bytes arrive.
    xSemaphoreTake(s_lock, portMAX_DELAY);
    bool accepted = session && session == s_session && !s_ready && s_pixels;
    xSemaphoreGive(s_lock);
    if (!accepted) { reply("SCREEN:ERR|inactive or busy\n"); return; }
    reply("SCREEN:READY\n");
    uint32_t hash = 2166136261u;
    unsigned decoded = 0, remaining = length;
    bool valid = true;
    int count = -1;
    uint8_t chunk[256];
    int64_t deadline = esp_timer_get_time() + 18000000;
    while (remaining && esp_timer_get_time() < deadline) {
        int got = uart_read_bytes(UART_NUM_0, chunk, remaining > sizeof(chunk) ? sizeof(chunk) : remaining, pdMS_TO_TICKS(200));
        if (got <= 0) continue;
        remaining -= got;
        xSemaphoreTake(s_lock, portMAX_DELAY);
        if (session != s_session || !s_pixels) valid = false;
        for (int i = 0; i < got; ++i) {
            hash = (hash ^ chunk[i]) * 16777619u;
            if (count < 0) count = chunk[i];
            else {
                if (!count || decoded + count > WIRE_PIXELS) valid = false;
                if (valid) {
                    for (unsigned n = 0; n < count; ++n) {
                        unsigned source = decoded + n;
                        unsigned sx = source % PC_SCREEN_W;
                        unsigned sy = source / PC_SCREEN_W;
                        unsigned dx = sx * PC_SCREEN_BUF_W / PC_SCREEN_W;
                        unsigned dy = sy * PC_SCREEN_BUF_H / PC_SCREEN_H;
                        s_pixels[PALETTE_BYTES + dy * PC_SCREEN_BUF_W + dx] = chunk[i];
                    }
                }
                decoded += count;
                count = -1;
            }
        }
        xSemaphoreGive(s_lock);
    }
    xSemaphoreTake(s_lock, portMAX_DELAY);
    valid = valid && !remaining && decoded == WIRE_PIXELS && hash == expected && session == s_session;
    if (valid) {
        s_frame = frame;
        s_ready = true;
        s_received = esp_timer_get_time();
        snprintf(s_status, sizeof(s_status), "Touch: click / drag   UP / DN: scroll");
    }
    xSemaphoreGive(s_lock);
    reply(valid ? "SCREEN:OK\n" : "SCREEN:ERR|payload\n");
}
