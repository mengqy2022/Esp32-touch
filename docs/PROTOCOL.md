# Console serial protocol

One ASCII line per command, terminated by `\n`, at 115200 baud. The existing
`FILE:` protocol remains handled by `file_xfer.c`. `PC:` is dispatched to
`pc_monitor_handle_line()` and `SCREEN:` to `pc_screen_handle_line()` on the same UART reader task.

| Command | Meaning |
| --- | --- |
| `PC:NAME\|hostname` | Host name, truncated to 23 characters. |
| `PC:TZOFF\|minutes` | Persist timezone offset in minutes east of UTC. |
| `PC:TIME\|unix_seconds` | Synchronize wall clock from USB. |
| `PC:STAT\|cpu\|gpu\|cpu_C\|gpu_C\|mem\|used_MB\|total_MB` | Percent loads, temperatures, physical RAM. `-1` means unavailable; memory fields are optional for older senders. |
| `PC:USAGE\|source\|today_tokens\|0\|YYYYMMDD\|estimated_CNY_fen` | Update the independent `CODEX` or `CLAUDE` cache without changing the device selection. Counts/cost use signed 64-bit integers; `-1` means unavailable. The reserved slot is zero. |
| `PC:AI\|source` | Select `CODEX` or `CLAUDE` once and persist the preference on the device. Calls the same function as the touch buttons. Normal telemetry does not send this command. |
| `PC:AI?` | Query selected source. Response: `PC:AI_STATE\|source\|tokens\|YYYYMMDD\|cost_fen\|fresh`. The last flag reports a packet received within 90 seconds; UI also checks tokens and local date. |
| `PC:CODEX\|today_tokens\|0\|YYYYMMDD\|estimated_CNY_fen` | Legacy packet updating the currently selected source. Older packets without cost remain supported; former daily-goal fields are parsed and ignored. |

AI usage is independent of `PC:STAT`. Usage packets never make old CPU/GPU
samples appear online. PC data expires after 5 seconds; each provider's usage expires
independently after 90 seconds. The dashboard rejects usage for a different calendar day.
The host sends both providers' separate caches every sampling interval, recomputes usage
every 5 seconds by default, and sends TIME every 15 seconds. After reconnect it
resends NAME, TZOFF and TIME. It preserves the device's choice across refresh and
reconnect. An explicit standalone `--ai-source` sends a one-time selection at startup.

The paired host and firmware must both support `PC:USAGE` for touch selection.
Older hosts may still overwrite selection with their `PC:AI` commands; update the
companion together with the firmware.

AI usage packets transfer only aggregate token counts. No prompts, credentials or
account identifiers are included. The former daily-goal slot is always zero.
The cost uses locally configured rates and exchange rate, not billed charges.

## Selected PC window (SCREEN)

The dashboard's existing UART owner also sends **320×176 RGB332** frames, with
aspect-preserving letterboxing supplied by the host and HALFTONE downscaling.
The no-PSRAM ESP32 stores a **256×140 indexed cache plus a 256-entry palette**
(36,864 bytes), scaled to the 320×176 display region. Wire and touch coordinates
remain 320×176; the cache does not preserve every wire pixel.
No SD writes, separate serial process, JPEG dependency or baud change is used.

| Command | Response / exchange |
| --- | --- |
| `SCREEN:?` | `SCREEN:STATE\|session\|displayed_frame`; session zero means the page is closed. |
| `SCREEN:OPEN`, `SCREEN:CLOSE` | Queue navigation to PC SCREEN / SYSTEM on the LVGL thread. |
| `SCREEN:APP\|mode\|title` | Set `generic`, `chatgpt` or `music` page metadata. A metadata change clears the frame, changes an active session and requests a UI rebuild; the host queries STATE again to resynchronize. Title is limited to 95 bytes on the device; the host sends at most 90 UTF-8 bytes. |
| `SCREEN:FRAME\|session\|frame\|length\|fnv1a32` | Wait for `SCREEN:READY`, send exactly length binary bytes, then wait for `SCREEN:OK` / `SCREEN:ERR\|reason`. |
| `SCREEN:STATUS\|text` | Show up to 63 ASCII characters and disable input until another frame arrives. |
| `SCREEN:INPUT\|session\|frame\|x1\|y1\|x2\|y2\|wheel` | Device → host click/drag or scroll, in wire coordinates; wheel is -1, 0 or +1. |
| `SCREEN:VIEW\|session\|frame\|zoom\|x\|y` | Device → host zoom around a point in the current view; zoom 1–8, UI cycles 1/2/4/8. |
| `SCREEN:PAN\|session\|frame\|zoom\|dx\|dy` | Device → host pan by signed wire-coordinate deltas, mapped through the zoom factor. |
| `SCREEN:COMMAND\|session\|command` | Device → host selected-player command: `previous`, `play_pause`, `next`, `volume_down`, `volume_up`. |

Frames contain `(count, RGB332_pixel)` byte pairs. Count must be 1–255, decoded
length exactly **56,320 pixels**; encoded length must be even and **2–112,640 bytes**.
FNV-1a uses offset 2166136261, multiplier 16777619, unsigned 32-bit wrapping.
Header/session/busy rejection occurs before READY: the host must not send any
payload in that case. After READY, the receiver drains the announced bytes even
when decoding fails, subject to an **18-second total receive deadline**.
No other host writes may interleave with a binary frame. OK confirms validation;
STATE reports its frame number after LVGL consumes the pending update. Decoding
writes the single indexed cache with a mutex per chunk; this is not atomic
full-frame buffer swapping, and a rejected payload can have modified cache pixels.

The device sends `SCREEN:INPUT|session|frame|x1|y1|x2|y2|wheel` on release or scroll.
Coordinates use the 320×176 wire image; wheel is -1, 0 or +1. The host accepts input
only for its latest acknowledged session/frame, younger than **25 seconds**,
inside the letterbox viewport, with unchanged client dimensions. Selection is
bound to HWND, PID, window class and, where permitted, a random window property
which disappears when destroyed. PID/class checks remain when property access is denied.
No automatic selection of another window is allowed. Pointer messages are sent
to the selected application's child control; the desktop cursor is not moved.

VIEW maps the last touched point through the current viewport; zoomed drag pans
instead of sending a pointer drag. FIT restores the full view. Music mode sends
targeted WM_APPCOMMAND controls without raster frames; its title is the selected
window title, not live playback metadata. Metadata changes and selected-target
reloads do not require reopening the UART. Capture runs in a separate process
which is terminated on timeout so a hung target cannot block subsequent switching.

At 115200 baud, the worst-case frame alone takes about **9.78 seconds** on the wire;
the measured maximum-frame exchange including display confirmation was about 10.17 seconds.
Telemetry shares this UART and can be delayed by frames. Flat application UI
compresses better. This is a low-rate remote control view.
WM_PRINT support, background input and minimized rendering depend on the app.

## Existing FILE commands

File names refer to the device filesystem (normally `/sdcard/...`). Responses
share the UART with firmware logs, so clients must match the `FILE:` prefix.

| Command | Response / exchange |
| --- | --- |
| `FILE:PING` | `FILE:PONG` |
| `FILE:LIST\|path` | Zero or more `FILE:ENTRY\|path\|size\|file/dir`, then `FILE:DONE`; error on failure. Empty path defaults to `/sdcard`. |
| `FILE:PUT\|path\|byte_count` | Wait for `FILE:READY`, then send exactly `byte_count` raw bytes. Device replies `FILE:OK` or `FILE:ERR\|reason`. |
| `FILE:GET\|path` | `FILE:READY\|byte_count`, exactly that many raw bytes, then `FILE:DONE` or an error. |
| `FILE:DEL\|path` | `FILE:OK` or `FILE:ERR\|reason`. |

Do not append a PUT binary payload before receiving READY. During raw transfer,
do not interleave telemetry. A host OS port normally has one client: pause the
dashboard before file tools, flashing or a serial monitor, then resume afterward.

## Line framing and compatibility

The shared reader processes all newline-terminated commands in one UART chunk,
including a line split across reads; CRLF is accepted. The previous implementation
discarded bytes following the first line in a read, losing CODEX after STAT.
The input line buffer is 512 bytes; normal telemetry must fit in it. This is a
local console protocol with no authentication or general-purpose escaping.
Avoid `|` and newlines in text fields.

Older hosts may omit the CODEX cost and extended STAT memory fields. Older
firmware without CODEX support cannot show tokens; older firmware without the
multi-line fix may lose packets even when the host log shows them sent.
No firmware identity or capabilities handshake is implemented yet.

Manual UART burst regression and publishing guidance are in
[DEVELOPMENT.md](DEVELOPMENT.md). Counting/pricing assumptions are in
[CODEX_USAGE_CN.md](CODEX_USAGE_CN.md).
