# ESP32 Touch Dashboard & Toolbox

[![ESP-IDF build](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/build.yml/badge.svg)](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/build.yml)
[![Host tests](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/host-tests.yml/badge.svg)](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/host-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[中文说明](README_CN.md) · [Documentation](docs/README.md) · [Changelog](CHANGELOG.md)

A 320×240 touchscreen dashboard with live PC monitoring, local Codex token
statistics and estimated CNY costs, plus games, system utilities, inventory
management and an offline vocabulary lab. A small Windows companion application
installs per user, starts after login and waits for the USB device automatically.

**Hardware target: `esp32`, ESP-IDF 5.5.4, LVGL 8.4.** The repository name is
historical: the validated device reports ESP32-D0WD-V3, not ESP32-S3. Keep the
target, pin map and display orientation for this board. Other boards need porting.

## Features

| Area | Current behavior |
| --- | --- |
| Home | Date, weekday, Wi-Fi status, clock; CPU/GPU/RAM rings, temperatures and RAM usage. Home stays visible when idle. |
| CODEX | Today's local input + output tokens; optional personal daily goal; estimated cost such as `~¥12.34`. Usage refreshes about every 5 seconds. |
| GAME | Sudoku, 2048 and Flappy. |
| SYSTEM | SD check, system info, Wi-Fi, confirmed touch calibration and PC details. |
| OTHER | SD-backed inventory/BOM and Vocab Lab with local wordbooks, study plans, spaced review and touchscreen dictation. |
| Windows companion | Standalone EXE, login startup controls, USB port detection, pause/resume, price configuration and rotating logs. No Python installation needed for end users. |

PC telemetry requires the companion to run. Games and local utilities remain
usable independently. GPU data depends on a supported NVIDIA driver; CPU
temperature is best effort. Unavailable sensors display `--`. PC data expires
after 5 seconds, Codex data after 90 seconds.

Codex usage comes from locally retained session logs. It is not a server billing
or subscription quota API. Prices are user-supplied configuration, with an
editable default USD/CNY rate of 7.20. Only aggregate telemetry is sent to the
device; no prompts or credentials are transmitted.

## Windows quick start

1. [Download ESP32TouchDashboard.exe](https://github.com/mengqy2022/Esp32-s3-touch/raw/refs/heads/main/dist/ESP32TouchDashboard.exe)
   or build it using the instructions below. The published Windows x64 EXE is
   also available in [dist/](dist/README.md), with a SHA-256 checksum.
2. Connect the device. Install its USB serial driver if Windows does not expose a
   COM port; the tested board uses CH340.
3. Double-click the EXE and accept installation. It installs to
   `%LOCALAPPDATA%/ESP32TouchDashboard` and enables startup for the current user.
4. Open **ESP32 Touch Dashboard** from the Start menu to check the startup status,
   pause/resume monitoring or edit prices. Startup occurs after Windows login.

See the [Windows user guide](docs/WINDOWS_APP_CN.md) for migration, updates,
removal and troubleshooting. Pause monitoring before flashing or using another
serial tool.

## Build from source

Firmware, in an ESP-IDF 5.5.4 environment:

```sh
idf.py set-target esp32
idf.py build
idf.py -p COM5 flash
```

Use the port assigned to your device; COM5 is only an example. For an existing
configured build, keep its configuration rather than resetting the target.

Windows EXE, with Python 3.11 x64 and PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Output: `dist/ESP32TouchDashboard.exe`. The script creates an isolated packaging
environment and pins pyserial/PyInstaller to the validated versions. Full
instructions and manual hardware tests are in the [developer guide](docs/DEVELOPMENT.md).

For a source-only host run (Windows or the existing Linux monitoring path):

```sh
python -m pip install -r tools/requirements.txt
python tools/pc_monitor_host.py --port COM5 --codex-prices tools/codex_prices.json
```

The installer, background supervisor and native control dialog are Windows only.

## Repository layout

```text
main/                  ESP-IDF firmware, LVGL UI, drivers and tools
tools/                 Host sender, Codex reader, Windows app and tests
docs/                  Functionality, app guide, architecture, protocol, roadmap
sdcard_template/       Public starter inventory/BOM and vocabulary examples
.github/workflows/     Firmware CI, host tests, manual Windows packaging
build_exe.ps1          Build the standalone Windows EXE
start_dashboard.ps1    Install if needed, set daily goal and resume
stop_dashboard.ps1     Pause monitoring and release the serial port
```

Git contains source, generic configuration, documentation and the explicitly
published Windows companion EXE with its checksum. Other generated firmware/EXEs,
build environments, recovery images and local runtime data are excluded.
The manual Windows workflow produces a downloadable Actions artifact;
it does not automatically publish a GitHub Release.

## Documentation and contribution

- [System functionality](docs/HOME_DASHBOARD_CN.md)
- [Windows installation and usage](docs/WINDOWS_APP_CN.md)
- [Codex counting and pricing](docs/CODEX_USAGE_CN.md)
- [Architecture](docs/ARCHITECTURE.md) and [serial protocol](docs/PROTOCOL.md)
- [Hardware](docs/HARDWARE.md) and [vocabulary format](docs/VOCABULARY.md)
- [Development and release guide](docs/DEVELOPMENT.md)
- [Validation record](docs/VALIDATION.md) and [future work](docs/ROADMAP_CN.md)
- [Contribution guidelines](CONTRIBUTING.md)

MIT license: [LICENSE](LICENSE). Component and wordbook notices:
[third-party notices](docs/THIRD_PARTY_NOTICES.md). Personal inventory, Codex logs,
flash backups and account data must remain local.
