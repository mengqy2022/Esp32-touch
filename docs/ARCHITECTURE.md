# Architecture

The firmware owns the display and local tools. The host sends numeric telemetry;
it does not stream screenshots or render the embedded UI.

```mermaid
flowchart LR
    OS[PC CPU / RAM / GPU providers] --> Host[pc_monitor_host.py]
    Logs[Local Codex session logs] --> Usage[codex_usage.py]
    Prices[Configured prices and FX] --> Usage
    Usage --> Host
    App[Windows installer and controls] --> Agent[dashboard_agent.py]
    Agent --> Host
    Host -->|PC lines over USB UART| RX[file_xfer.c single reader]
    RX --> PC[pc_monitor.c state]
    PC --> UI[ui.c / LVGL dashboard]
    RX -->|FILE commands| SD[SD files]
    SD --> Tools[Inventory / Vocab Lab]
    Tools --> UI
```

## Firmware modules

| Module | Responsibility |
| --- | --- |
| `main/main.c` | Startup, services and application tasks; home remains visible at idle. |
| `main/ui.c`, `ui.h` | Dashboard, category navigation, tool screens and refresh logic. |
| `main/lv_port.c` | LVGL task, display/touch integration and UI command queue. |
| `main/pc_monitor.c`, `pc_monitor.h` | PC telemetry parser, state snapshots, timestamps and independent validity. |
| `main/file_xfer.c` | Sole console UART reader; dispatches PC lines and FILE transfers. |
| `main/net_utils.c` | USB/Wi-Fi time sync, timezone and time source tracking. |
| `main/sd_monitor.c` | SD lifecycle and scan/check operations. |
| `main/wifi_mgr.c` | Scan, connect, stored credentials and reconnect. |
| `main/inventory.c`, `main/vocabulary.c` | SD-backed tools and their data engines. |
| LCD/touch drivers and `board_pins.h` | Board-specific hardware implementation. |

LVGL objects must be accessed from its task; other tasks post commands using
`lv_port_post_cmd()`. Keep long filesystem/network operations out of the drawing
loop. Preserve the shared UART reader rather than adding competing readers.

The UART fix processes every complete line in a read chunk and retains a partial
line across reads. FILE:PUT binary data begins only after FILE:READY, so it must not
be concatenated ahead of that handshake. Firmware logs and protocol replies share
the output stream; the host/tool must distinguish them by prefix.

Codex updates are independent of PC samples. Receiving a CODEX line does not extend
the lifetime of STAT values. CPU/GPU/RAM expire in 5 seconds, Codex in 90 seconds;
Codex also requires the matching local date. Counts and cost use signed 64-bit values.
The yen sign uses a tiny dedicated glyph rather than a large additional font.

## Host modules

| Module | Responsibility |
| --- | --- |
| `tools/desktop_dashboard.py` | Per-user install, Run registration, native dialogs, control commands. |
| `tools/dashboard_agent.py` | Single-instance file lock, device polling/matching, telemetry worker supervision, pause marker, rotating logs. |
| `tools/pc_monitor_host.py` | In-process worker; samples OS providers, synchronizes time, sends PC packets, reads device logs. Also runnable directly in a terminal. |
| `tools/codex_usage.py` | Incremental offsets, counter deltas, daily/model aggregation, pricing and packet formatting. |

The background supervisor runs its telemetry worker in a Python thread, avoiding a
second Python host subprocess. PyInstaller onefile still has bootloader/worker OS
processes. The Windows control dialog is transient; the background needs no GUI loop.

The agent polls ports approximately every 2 seconds. It prefers configured identity
details and waits if several candidates cannot be resolved. Matching CH340 hardware
is not proof of dashboard firmware; capability handshake is future work.

Config is read at agent startup; price JSON is read during each usage recomputation.
There is no persistent database for usage: offsets and counters live in memory,
and a restart reconstructs today's counts from retained logs. Directory enumeration
still occurs on every scan, even though file contents are read incrementally.

## Privacy and boundaries

The firmware receives host name, aggregate loads, temperatures, RAM, time/date,
token count, personal goal and estimated cost. It receives no conversation content
or account credentials. The reader accesses log bytes locally but decodes only
model/usage records. Runtime log reports may contain local paths or usage figures
and should be reviewed before sharing.

The host does not query actual billing, fetch exchange rates or update itself.
Automatic startup belongs to the logged-in Windows user. Serial exclusivity is
still required between telemetry, inventory transfers, flashing and monitors.
