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

#define PIXELS (PC_SCREEN_W * PC_SCREEN_H)
static SemaphoreHandle_t s_lock;
static lv_color_t *s_colors;
static uint32_t s_session, s_frame;
static bool s_ready;
static int64_t s_received;
static char s_status[64] = "Select a window in the PC dashboard";
static const char *TAG = "pcscreen";

static void reply(const char *message) { uart_write_bytes(UART_NUM_0, message, strlen(message)); }
void pc_screen_init(void) { s_lock = xSemaphoreCreateMutex(); configASSERT(s_lock); ESP_LOGI(TAG, "screen protocol ready"); }

lv_color_t *pc_screen_open(void)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    if (!s_colors) s_colors = calloc(PIXELS, sizeof(lv_color_t));
    s_frame = 0;
    s_ready = false;
    s_received = 0;
    s_session = s_colors ? (esp_random() | 1) : 0;
    snprintf(s_status, sizeof(s_status), "%s", s_session ? "Select a window in the PC dashboard" : "Not enough memory");
    ESP_LOGI(TAG, "screen open: colors=%p session=%"PRIu32, s_colors, s_session);
    lv_color_t *result = s_session ? s_colors : NULL;
    xSemaphoreGive(s_lock);
    return result;
}

void pc_screen_close(void)
{
    xSemaphoreTake(s_lock, portMAX_DELAY);
    s_session = 0;
    free(s_colors); s_colors = NULL;
    s_ready = false;
    xSemaphoreGive(s_lock);
}

bool pc_screen_refresh(char *status, unsigned size)
{
    if (xSemaphoreTake(s_lock, 0) != pdTRUE) return false;
    bool changed = s_ready;
    if (changed && s_colors) {
        uint8_t *encoded = (uint8_t *)s_colors;
        for (int i = PIXELS - 1; i >= 0; --i) {
            uint8_t p = encoded[i];
            s_colors[i] = lv_color_make(((p >> 5) & 7) * 255 / 7, ((p >> 2) & 7) * 255 / 7, (p & 3) * 255 / 3);
        }
        s_ready = false;
    }
    if (s_received && esp_timer_get_time() - s_received > 8000000)
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
    if (s_session && s_frame && !s_ready && esp_timer_get_time() - s_received < 8000000) {
        snprintf(message, sizeof(message), "SCREEN:INPUT|%"PRIu32"|%"PRIu32"|%d|%d|%d|%d|%d\n",
                 s_session, s_frame, x1, y1, x2, y2, wheel);
        reply(message);
    }
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
        xSemaphoreGive(s_lock);
        return;
    }
    uint32_t session, frame, expected;
    unsigned length;
    if (sscanf(line, "FRAME|%"SCNu32"|%"SCNu32"|%u|%"SCNu32"%c", &session, &frame, &length, &expected, &extra) != 4 ||
        length < 2 || length > PIXELS * 2 || length % 2 || !frame) {
        reply("SCREEN:ERR|header\n"); return;
    }
    // Reject rather than block the LVGL task while serial bytes arrive.
    xSemaphoreTake(s_lock, portMAX_DELAY);
    bool accepted = session && session == s_session && !s_ready && s_colors;
    xSemaphoreGive(s_lock);
    if (!accepted) { reply("SCREEN:ERR|inactive or busy\n"); return; }
    reply("SCREEN:READY\n");
    uint32_t hash = 2166136261u;
    unsigned decoded = 0, remaining = length;
    bool valid = true;
    int count = -1;
    uint8_t chunk[256];
    int64_t deadline = esp_timer_get_time() + 6000000;
    while (remaining && esp_timer_get_time() < deadline) {
        int got = uart_read_bytes(UART_NUM_0, chunk, remaining > sizeof(chunk) ? sizeof(chunk) : remaining, pdMS_TO_TICKS(200));
        if (got <= 0) continue;
        remaining -= got;
        xSemaphoreTake(s_lock, portMAX_DELAY);
        if (session != s_session || !s_colors) valid = false;
        for (int i = 0; i < got; ++i) {
            hash = (hash ^ chunk[i]) * 16777619u;
            if (count < 0) count = chunk[i];
            else {
                if (!count || decoded + count > PIXELS) valid = false;
                if (valid) memset(((uint8_t *)s_colors) + decoded, chunk[i], count);
                decoded += count;
                count = -1;
            }
        }
        xSemaphoreGive(s_lock);
    }
    xSemaphoreTake(s_lock, portMAX_DELAY);
    valid = valid && !remaining && decoded == PIXELS && hash == expected && session == s_session;
    if (valid) {
        s_frame = frame;
        s_ready = true;
        s_received = esp_timer_get_time();
        snprintf(s_status, sizeof(s_status), "Touch: click / drag   UP / DN: scroll");
    }
    xSemaphoreGive(s_lock);
    reply(valid ? "SCREEN:OK\n" : "SCREEN:ERR|payload\n");
}
