# Hardware and target

The repository name includes “s3”, but the validated device identifies as
**ESP32-D0WD-V3 revision v3.1**, with 4 MB flash. The existing board design is
documented as ESP32-WROOM-32E/E32R28T. The firmware target is **`esp32`**.
Do not select `esp32s3` without porting and verifying a different board.

- ILI9341 SPI display, 320×240 landscape.
- XPT2046 resistive touch controller, software SPI.
- MicroSD over SPI; use FAT32 and the public `sdcard_template/` contents.
- Common-anode RGB status LED, active low.
- BOOT on GPIO0; the firmware retains long-press touch recalibration.
- Tested USB UART bridge: CH340, VID `1A86`, PID `7523`.
- No implemented battery telemetry and no assumption of external PSRAM.

## PC SCREEN requirements and limits

The current firmware runs on the validated board above without adding PSRAM,
an SD card or Wi-Fi for PC SCREEN. It requires a USB data cable, a working serial
driver and the updated Windows companion; the tested board uses CH340 at 115200 baud.
The application image is 1,590,272 bytes in the supplied 3 MiB application partition.

To fit RAM, the device allocates a 256×140 indexed image plus a 1 KiB palette
(36 KiB total), while the wire frame is 320×176 RGB332 RLE. This supports low-rate
window viewing, zoom and touch commands. Full-window small text, smooth video and
arbitrary minimized/GPU applications are beyond the verified capability; use local
zoom for text and dedicated media controls for NetEase Cloud Music.
The current release does not require changing the board. A higher resolution or
frame-rate goal needs separate memory, display-bus and transport measurements.

## Pin map

The authoritative source is [main/board_pins.h](../main/board_pins.h).

| Peripheral | Signal | GPIO |
| --- | --- | --- |
| LCD | SCK / MOSI / MISO | 14 / 13 / 12 |
| LCD | CS / DC / BL | 15 / 2 / 21 |
| Touch | SCK / MOSI / MISO | 25 / 32 / 39 |
| Touch | CS / IRQ | 33 / 36 |
| SD | SCK / MISO / MOSI / CS | 18 / 19 / 23 / 5 |
| RGB LED | R / G / B | 17 / 22 / 16 |
| BOOT | Button | 0 |

LCD reset is tied to the board reset net, not a dedicated GPIO. GPIO36/39 are
input-only, and the existing mapping accounts for this. This is the current
board mapping, not a universal wiring recommendation for all ESP32 modules.
Check the actual board schematic and boot-strapping behavior before rewiring.

Keep LCD orientation and touch calibration together when porting. Touch results,
Wi-Fi credentials and timezone settings persist in NVS; do not erase flash as a
routine update. Complete flash backups include those settings and remain private.

CPU/GPU temperatures on the screen refer to the PC, not the ESP32.
The current Windows CPU-temperature path is best effort and may display `--`.
