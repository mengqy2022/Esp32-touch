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
| `PC:CODEX\|today_tokens\|daily_goal\|YYYYMMDD\|estimated_CNY_fen` | Local Codex daily token count, user-defined goal, host local calendar date and optional estimated cost in CNY cents. `-1` tokens/cost means unavailable, `0` goal means no goal. Counts/goal/cost use signed 64-bit integers; older packets without a cost field remain supported. |

`PC:CODEX` is independent of `PC:STAT`. Codex packets never make old CPU/GPU
samples appear online. PC data expires after 5 seconds; Codex data after
90 seconds. The dashboard rejects Codex data for a different calendar day.
The host sends Codex telemetry every sampling interval, recomputes usage
every 5 seconds by default, and sends TIME every 15 seconds. After reconnect it
resends NAME, TZOFF and TIME.

Only aggregate token counts are transferred. No prompts, credentials or
account identifiers are included. `daily_goal` is not an official plan quota.
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
