# Console serial protocol

One ASCII line per command, terminated by `\n`, at 115200 baud. The existing
`FILE:` protocol remains handled by `file_xfer.c`. `PC:` is dispatched to
`pc_monitor_handle_line()` on the same UART reader task.

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

Only aggregate token counts are transferred. No prompts, credentials or
account identifiers are included. The former daily-goal slot is always zero.
The cost uses locally configured rates and exchange rate, not billed charges.

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
