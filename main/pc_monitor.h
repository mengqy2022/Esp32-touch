#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// PC Monitor: receives time + CPU/GPU/MEM telemetry from the PC host tool
// (tools/pc_monitor_host.py) over the Type-C serial port (console UART).
//
// Wire protocol (one ASCII line, '\n' terminated, sent by the host):
//   PC:TIME|<unix_seconds>                 -> set device wall clock (USB source)
//   PC:TZOFF|<minutes east of UTC>         -> set + persist device timezone
//   PC:STAT|<cpu%>|<gpu%>|<cpu_C>|<gpu_C>|<mem%>|<mem_used_MB>|<mem_total_MB>  (any value may be -1 = n/a)
//   PC:NAME|<hostname>                    -> shown on the monitor screen
//   PC:CODEX|<today_tokens>|0|<YYYYMMDD>|<estimated_CNY_fen>
//             (-1 tokens/cost = unavailable; cost field optional)
//   PC:AI|CODEX/CLAUDE                    -> selected independent usage source
//   PC:USAGE|CODEX/CLAUDE|<tokens>|0|<YYYYMMDD>|<CNY_fen> -> update one cache without selecting it
//   PC:AI?                               -> PC:AI_STATE|<source>|<tokens>|<day>|<cost>|<fresh>
//
// Lines are dispatched from file_xfer.c (the single owner of the UART) by
// calling pc_monitor_handle_line().

#define PCMON_HOST_MAX  24

typedef struct {
    bool link;               // a PC packet was received within the last 5 s
    uint32_t last_pkt_s;     // seconds since the last PC packet
    bool have_time;          // TIME received from this PC at least once
    int cpu_load;            // 0..100, -1 = n/a
    int gpu_load;            // 0..100, -1 = n/a
    int mem_load;            // 0..100, -1 = n/a
    int mem_used_mb;        // used RAM MB, -1 = n/a
    int mem_total_mb;       // total RAM MB, -1 = n/a
    int cpu_temp;            // Celsius, -1 = n/a
    int gpu_temp;            // Celsius, -1 = n/a
    char host[PCMON_HOST_MAX]; // hostname / PC name, "" if unknown
    int64_t codex_tokens;
    char ai_source[16];      // selected local usage source
    int64_t codex_cost_fen;   // estimated CNY cents, -1 = unavailable
    int codex_day;
    bool codex_link;          // valid Codex packet received within 90 s
} pc_monitor_status_t;

// Zero the state (call once during boot).
void pc_monitor_init(void);

// Parse one protocol line (without the "PC:" prefix and trailing newline).
// Called from the serial reader task.
void pc_monitor_handle_line(const char *line);

// Select a provider on the device and persist it. Called by touch UI or UART.
bool pc_monitor_select_ai_source(const char *source);

// Copy the current status (thread-safe snapshot).
void pc_monitor_get(pc_monitor_status_t *out);

#ifdef __cplusplus
}
#endif
