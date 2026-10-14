# PC companion and data tools

Run commands from the repository root. Python 3.11 is the reference environment.

```sh
python -m pip install -r tools/requirements.txt
```

## Monitoring and Windows app

| Source | Role |
| --- | --- |
| `pc_monitor_host.py` | Sends PC stats, time, timezone and Codex telemetry over serial; receives device log output. |
| `codex_usage.py` | Incremental local session-log reader and configurable CNY estimator. |
| `dashboard_agent.py` | Windows single-instance background supervisor, device matching, pause marker and rotating logs. |
| `desktop_dashboard.py` | Windows EXE entry, per-user installation, login startup and native control dialog. |
| `codex_prices.json` | Generic user-supplied price example; not an official price feed. |

```sh
python tools/pc_monitor_host.py --list-ports
python tools/pc_monitor_host.py --port COM5 --codex-prices tools/codex_prices.json
python tools/pc_monitor_host.py --port COM5 --codex-daily-goal 1000000 --codex-prices tools/codex_prices.json
python tools/pc_monitor_host.py --port COM5 --no-codex
```

`--codex-home` overrides the log directory; otherwise `CODEX_HOME` or `~/.codex`
is used. `--codex-refresh` defaults to 5 seconds. `--interval` controls approximate
PC sampling cadence. Run `--help` for all options. The source host is foreground;
use the packaged EXE for Windows login startup and background supervision.

Windows CPU/RAM use ctypes; NVIDIA GPU telemetry uses the existing driver NVML
library; WMI CPU temperatures are best effort. The existing Linux path uses
`/proc` and `nvidia-smi`. Windows installation is not a Linux service.

Build the EXE with root `build_exe.ps1`. [EXE manual](../docs/WINDOWS_APP_CN.md),
[pricing](../docs/CODEX_USAGE_CN.md), [protocol](../docs/PROTOCOL.md).

## Existing data tools

Pause the dashboard before using any tool that opens the same serial port.

| Tool | Usage |
| --- | --- |
| `inventory_tool.py` | Tkinter serial inventory/BOM GUI; list/upload/download/delete SD files, merge supported CSVs. |
| `material_to_inventory.py` | Purchase CSV/ZIP → merged `PRODUCT_NO,MODEL,QTY` inventory. |
| `vocab_convert.py` | Compatible CSV or JSON wordbook → device CSV. |
| `smoke_test.py` | Manual serial file-transfer smoke test. |
| `test_parse.py` | Existing inventory-parser check. |

```sh
python tools/inventory_tool.py
python tools/material_to_inventory.py purchase.csv -o build/INVENTORY.CSV
python tools/vocab_convert.py input.json build/my_book.csv
```

Copy the wordbook to SD `vocabulary/books/`. Keep personal purchase files and
inventory outside version control; the tracked SD template is public sample data.

## Tests

```sh
python -m unittest discover -s tools -p test_codex_usage.py -v
python -m unittest discover -s tools -p test_dashboard_agent.py -v
```

These tests use synthetic logs and ports. `test_serial_burst.py` requires exclusive
access to real hardware, resets it and sends time/usage telemetry.
`test_dialog_runtime.py` is a Windows manual test requiring an installed app with
startup enabled; it creates a temporary dialog and writes a local report in `build/`.
Do not run unrestricted `test_*.py` discovery in CI: hardware and GUI checks are
separate from unit tests. See [development](../docs/DEVELOPMENT.md).
