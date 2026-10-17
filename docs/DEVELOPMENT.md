# Development, testing and publishing

This repository tracks source, generic templates, documentation and an explicitly
published Windows companion EXE/checksum in `dist/`. Other generated firmware,
EXEs and personal machine data stay outside Git. Keep the existing `main/`,
`tools/` and `docs/` layout to preserve ESP-IDF and script paths.

## Firmware build

Reference environment: ESP-IDF **5.5.4**, target **esp32**, LVGL **8.4**.
Use an ESP-IDF terminal. The component manager resolves `main/idf_component.yml`.

```sh
# Fresh checkout only; keep an existing configured build's settings.
idf.py set-target esp32
idf.py build
# Substitute your device's actual port.
idf.py -p COM5 flash
```

`sdkconfig.defaults` and `partitions.csv` are source configuration. `sdkconfig`,
`managed_components/` and `build/` are generated/local. Preserve an existing
`sdkconfig` if it contains board-specific settings. In an old build, inspect
`menuconfig` to enable Montserrat 28; editing defaults alone does not override an
existing configuration. Do not erase NVS as a routine upgrade.

Pause the dashboard and close other serial clients before flashing.
`idf.py -p COM5 monitor` also occupies the port: exit it before resuming telemetry.
The original `build_flash.bat` / `build_flash.sh` helpers remain available.
CI runs the existing firmware workflow with the same target and IDF version.

Full-flash backups may contain Wi-Fi and other NVS settings. Keep them locally in
`recovery/`, which is ignored, rather than attaching them to public releases.

## Host development

Use Python 3.11 as the reference version:

```sh
python -m pip install -r tools/requirements.txt
python tools/pc_monitor_host.py --list-ports
python tools/pc_monitor_host.py --port COM5 --codex-prices tools/codex_prices.json
```

The only pip runtime dependency is pyserial 3.5. ctypes/OS providers and the
optional driver-supplied NVML library are used for monitoring. The legacy inventory
GUI uses Tkinter; the monitoring EXE does not bundle a GUI framework.
The installer, agent lock and dialogs are Windows-specific. Linux retains the
terminal host path; its behavior was not newly verified on hardware in this update.

## Windows EXE packaging

本机为避免占用 C 盘，`build_exe.ps1` 默认将打包环境、临时文件、缓存和输出放在
`F:\ESP32TouchDashboard-work\2026-10-17`，可用 `-WorkRoot` 改位置。
EXE 和校验和位于该目录的 `output/`。需要更新仓库发布副本时显式加
`-PublishToRepository`。Windows CI 使用 runner 临时目录，不依赖 F 盘。
本机固件可用 ESP-IDF 终端运行 `./build_firmware.ps1`，同样使用 F 盘构建与缓存。

On Windows, with Python 3.11 x64 available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
# Optional explicit interpreter:
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1 -PythonPath C:\Python311\python.exe
```

The script creates `.packaging/`, installs `tools/requirements-build.txt`, embeds
the generic pricing template and builds a onefile, windowless EXE:

```text
dist/ESP32TouchDashboard.exe
```

pyserial 3.5 and PyInstaller 6.22.3 are pinned to the validated environment.
Transitive dependencies and the interpreter are not hash-locked; this is version
pinning, not a guarantee of byte-identical output. Build on the target OS.
The first build needs network access for dependencies; end users need no Python.
Do not install the freshly built EXE over a running installation during tests.

## Unit checks

From the repository root:

```sh
python -m unittest discover -s tools -p test_codex_usage.py -v
python -m unittest discover -s tools -p test_dashboard_agent.py -v
python -m unittest discover -s tools -p test_ai_usage.py -v
python -m unittest discover -s tools -p test_device_settings.py -v
python -m unittest discover -s tools -p test_desktop_settings.py -v
python -m py_compile tools/codex_usage.py tools/dashboard_agent.py tools/desktop_dashboard.py tools/pc_monitor_host.py
git diff --check
```

Tests use synthetic logs and USB port records, not the user's live session data.
They cover duplicate counters, partial lines, date changes, fork handling,
archive moves, pricing, long-context fallback and device identity selection.
Host tests run on Windows and Linux in `.github/workflows/host-tests.yml`.
These unit tests do not verify native dialogs, actual serial access or Windows login.

## Manual integration checks

These checks require a real device or Windows desktop and must not be included in
unrestricted unit-test discovery.

For independent AI caches and persistent selection, pause the companion and run
`python tools/test_device_ai_switch.py --port COM5`. It uses synthetic counters,
calls the same selection function as the touch buttons through the serial protocol,
checks reboot persistence, then restores the original source. Resume the companion
afterward to replace test counts with real usage. This does not replace tapping the
physical CODEX / CLAUDE buttons and inspecting their highlight and displayed values.

1. Pause the installed agent and close serial monitors. Confirm another client can
   open the device port.
2. For UART regression, run `python tools/test_serial_burst.py --port COM5`.
   This resets the board, sends three PING commands together with TIME and local
   Codex telemetry, then a fourth PING split across writes. It requires readable
   local usage logs and checks four PONGs, startup, time, CODEX and crash markers.
   It writes `build/serial_burst_validation.log`; it does not validate CNY pricing.
3. On Windows, with the app installed and startup enabled, create `build/` if absent
   and run `python tools/test_dialog_runtime.py`. It inspects its own temporary
   native dialog, closes it and writes `build/dialog_validation.json`. It does not
   click the real control window's setting buttons.
4. Resume monitoring. Verify home, PC details, token/cost display and category
   navigation; confirm sensors unavailable on that computer display `--`.
5. Separately test actual Windows logout/login, reboot, USB unplug/replug and
   multiple CH340 devices. See the recorded limits in [validation](VALIDATION.md).

Avoid running the live tests as part of a source/doc-only cleanup. They occupy the
serial port, can reset the device and generate machine-specific reports.

## Source and published package updates

Inspect `git status` and review the diff in GitHub Desktop before committing.
Include modified `main/`, new host modules/tests, generic price template,
requirements, scripts, docs and workflow definitions.

The only published build outputs allowed in Git are
`dist/ESP32TouchDashboard.exe` and `dist/SHA256SUMS.txt`; `dist/README.md` explains
the download. To update the package, build and verify the EXE, regenerate its
SHA-256 checksum and commit both together.

Do not commit `build/`, other `dist/` output, `.packaging/`, `managed_components/`, `recovery/`,
other EXE/BIN/ELF/MAP files, local SDK configuration, `.log` files, installed LocalAppData
contents, Codex logs, credentials or personal CSVs. `.gitignore` covers current
generated paths; ignore rules do not remove files already tracked by Git.

Example review commands:

```sh
git status --short
git diff --stat
git diff --check
git check-ignore build/app.bin recovery/device.bin dist/temporary.exe
```

Suggested commit title: `feat: integrate home dashboard and Windows companion`.
Keep the current development in **Unreleased** until a maintainer chooses a release
version; documented sample prices are configuration assumptions, not product claims.

## Distributing binaries later

The manual `.github/workflows/windows-exe.yml` workflow builds a Windows x64
EXE and SHA-256 checksum as an Actions artifact retained for 14 days. After this
workflow is pushed, run **Actions → Windows EXE package → Run workflow**.
It does not install the app or create a Release. Hosted runners cannot test the
physical device or interactive desktop flow.

For a public version, choose a tag/version, test on a clean Windows machine,
record firmware/host compatibility, then attach the EXE or ZIP and checksum to
GitHub Releases. Keep source history separate from downloadable binaries.
Ship firmware only when the board target and flash layout are clear; no recovery
image with private NVS. Consider a signing certificate before broad distribution.

Before releasing, review [third-party notices](THIRD_PARTY_NOTICES.md). PyInstaller
has a bundling exception; the packaged application also includes Python, pyserial
and supporting runtime components whose license notices should accompany a package.
Current source workflows are unsigned and do not automate release publication.
