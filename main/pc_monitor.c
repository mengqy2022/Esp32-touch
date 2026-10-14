#include "pc_monitor.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "net_utils.h"

static const char *TAG = "pcmon";

// Host telemetry: marked stale when no packet arrives for this long.
#define PCMON_LINK_TIMEOUT_MS 5000

static pc_monitor_status_t s_state;
static int64_t s_last_pkt_us;
static bool s_rx_since_boot;
static uint32_t s_stat_count;
static int64_t s_last_codex_us;
static bool s_codex_received;
static portMUX_TYPE s_lock = portMUX_INITIALIZER_UNLOCKED;

void pc_monitor_init(void)
{
    memset(&s_state, 0, sizeof(s_state));
    s_state.cpu_load = -1;
    s_state.gpu_load = -1;
    s_state.mem_load = -1;
    s_state.cpu_temp = -1;
    s_state.gpu_temp = -1;
    s_state.mem_used_mb = -1;
    s_state.mem_total_mb = -1;
    s_state.codex_tokens = -1;
    s_state.codex_cost_fen = -1;
    s_last_codex_us = 0;
    s_codex_received = false;
    s_last_pkt_us = 0;
    s_rx_since_boot = false;
}

static int clamp_i(int v, int lo, int hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

// Read one '|'-separated field; advances *p to the next field.
// Returns true when a valid integer was parsed.
static bool next_i(const char **p, int *out)
{
    const char *s = *p;
    if (!s || *s == '\0') return false;
    errno = 0;
    char *end = NULL;
    long v = strtol(s, &end, 10);
    if (end == s) return false;
    *out = (int)v;
    *p = (*end == '|') ? end + 1 : end;
    return true;
}

static void handle_stat(const char *p)
{
    int cpu = -1, gpu = -1, ct = -1, gt = -1, mem = -1, mem_used = -1, mem_total = -1;
    if (next_i(&p, &cpu) && next_i(&p, &gpu) && next_i(&p, &ct) &&
        next_i(&p, &gt)) {
        next_i(&p, &mem); // optional 5th field
        next_i(&p, &mem_used); // optional 6th field
        next_i(&p, &mem_total); // optional 7th field
    } else {
        ESP_LOGW(TAG, "malformed STAT packet");
        return;
    }
    cpu = cpu < 0 ? -1 : clamp_i(cpu, 0, 100);
    gpu = gpu < 0 ? -1 : clamp_i(gpu, 0, 100);
    mem = mem < 0 ? -1 : clamp_i(mem, 0, 100);
    ct  = ct  < 0 ? -1 : clamp_i(ct, 0, 150);
    gt  = gt  < 0 ? -1 : clamp_i(gt, 0, 150);

    portENTER_CRITICAL(&s_lock);
    s_state.cpu_load = cpu;
    s_state.gpu_load = gpu;
    s_state.mem_load = mem;
    s_state.mem_used_mb = mem_used;
    s_state.mem_total_mb = mem_total;
    s_state.cpu_temp = ct;
    s_state.gpu_temp = gt;
    s_rx_since_boot = true;
    s_last_pkt_us = esp_timer_get_time();
    portEXIT_CRITICAL(&s_lock);

    // Telemetry reception proof-log: first packet immediately, then one line
    // per ~10 packets so the console stays readable (one STAT per second).
    s_stat_count++;
    if (s_stat_count == 1) {
        ESP_LOGI(TAG, "PC host online: telemetry streaming");
    } else if (s_stat_count % 10 == 0) {
        ESP_LOGI(TAG, "telemetry: cpu=%d%% gpu=%d%% mem=%d%% cpuT=%dC gpuT=%dC",
                 cpu, gpu, mem, ct, gt);
    }
}

static void handle_time(const char *p)
{
    errno = 0;
    char *end = NULL;
    long long v = strtoll(p, &end, 10);
    if (end == p) {
        ESP_LOGW(TAG, "malformed TIME packet");
        return;
    }
    net_time_from_usb((time_t)v);
    portENTER_CRITICAL(&s_lock);
    s_state.have_time = true;
    portEXIT_CRITICAL(&s_lock);
    ESP_LOGI(TAG, "clock synced from PC: %lld", v);
}

static void handle_tzoff(const char *p)
{
    errno = 0;
    char *end = NULL;
    long v = strtol(p, &end, 10);
    if (end == p) {
        ESP_LOGW(TAG, "malformed TZOFF packet");
        return;
    }
    if (net_tz_apply((int)v) == ESP_OK) {
        ESP_LOGI(TAG, "timezone set from PC: %ld min", v);
    }
}

static void handle_name(const char *p)
{
    portENTER_CRITICAL(&s_lock);
    snprintf(s_state.host, sizeof(s_state.host), "%.*s",
             (int)(sizeof(s_state.host) - 1), p ? p : "");
    portEXIT_CRITICAL(&s_lock);
}

void pc_monitor_handle_line(const char *line)
{
    if (!line) return;

    if (strncmp(line, "STAT|", 5) == 0) {
        handle_stat(line + 5);
    } else if (strncmp(line, "TIME|", 5) == 0) {
        handle_time(line + 5);
    } else if (strncmp(line, "TZOFF|", 6) == 0) {
        handle_tzoff(line + 6);
    } else if (strncmp(line, "NAME|", 5) == 0) {
        handle_name(line + 5);
    } else if (strncmp(line, "CODEX|", 6) == 0) {
        const char *p = line + 6;
        char *end;
        errno = 0;
        long long used = strtoll(p, &end, 10);
        if (end == p || *end != '|' || errno || used < -1) return;
        p = end + 1;
        long long goal = strtoll(p, &end, 10);
        if (end == p || *end != '|' || errno || goal < 0) return;
        p = end + 1;
        long day = strtol(p, &end, 10);
        if (end == p || (*end && *end != '|') || errno || day < 20200101 || day > 20991231) return;
        long long cost = -1;
        if (*end == '|') {
            p = end + 1;
            cost = strtoll(p, &end, 10);
            if (end == p || *end || errno || cost < -1) return;
        }
        portENTER_CRITICAL(&s_lock);
        s_state.codex_tokens = used;
        s_state.codex_goal = goal;
        s_state.codex_day = (int)day;
        s_state.codex_cost_fen = cost;
        bool first = !s_codex_received;
        s_codex_received = true;
        s_last_codex_us = esp_timer_get_time();
        portEXIT_CRITICAL(&s_lock);
        if (first) ESP_LOGI(TAG, "Codex usage online: %lld tokens, goal=%lld, day=%ld, estimated_CNY_fen=%lld", used, goal, day, cost);
    } else {
        // Unknown PC: command - ignore (forward compatible).
        return;
    }
}

void pc_monitor_get(pc_monitor_status_t *out)
{
    if (!out) return;
    int64_t now_us = esp_timer_get_time();
    portENTER_CRITICAL(&s_lock);
    *out = s_state;
    bool received = s_rx_since_boot;
    int64_t last_pkt_us = s_last_pkt_us;
    out->codex_link = s_codex_received && now_us - s_last_codex_us < 90000000LL;
    portEXIT_CRITICAL(&s_lock);

    if (!received) {
        out->link = false;
        out->last_pkt_s = 0;
    } else {
        int64_t age_ms = (now_us - last_pkt_us) / 1000;
        out->link = age_ms < PCMON_LINK_TIMEOUT_MS;
        out->last_pkt_s = (uint32_t)(age_ms < 0 ? 0 : age_ms / 1000);
    }
}
