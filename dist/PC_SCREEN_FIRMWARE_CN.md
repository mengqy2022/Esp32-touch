# PC SCREEN 完整系统固件

[下载固件 ZIP](https://github.com/mengqy2022/Esp32-touch/raw/refs/heads/main/dist/ESP32Touch-PC-SCREEN-firmware.zip)
· [下载配套 EXE](https://github.com/mengqy2022/Esp32-touch/raw/refs/heads/main/dist/ESP32TouchDashboard.exe)
· [SHA-256](SHA256SUMS.txt)

此包是原有系统的完整升级固件，包含 PC SCREEN 指定窗口投射、触摸控制、
局部放大、网易云快捷控制，以及 Snake、Breakout 和原有游戏的升级。
配套 EXE 使用 2026.10.18.4 或更新版本，修复关闭 GUI 后后台采集失效的问题。

适用硬件：本工程已验证的 ESP32-D0WD-V3、4 MB Flash、ILI9341 320×240 屏幕，
接线见 `main/board_pins.h`。工程文件夹名称中有 S3，但此固件目标是 **ESP32，不能烧录到 ESP32-S3**。
固件使用 ESP-IDF 5.5.4 构建，已在 COM5 设备烧录、校验，并由用户确认 ChatGPT 画面可显示。

## 烧录

1. 下载并解压 ZIP，核对仓库中的 ZIP 校验值；包内也包含三个固件文件各自的校验值。
2. 在 Dashboard 暂停监控，等待串口释放，关闭其他串口工具。
3. 打开已配置 ESP-IDF / esptool 的终端，进入解压目录，使用设备实际 COM 号执行：

```powershell
python -m esptool --chip esp32 --port COM5 --baud 460800 --before default_reset --after hard_reset write_flash "@flash_args"
```

写入布局：

| 文件 | 地址 |
| --- | --- |
| `bootloader.bin` | `0x1000` |
| `partition-table.bin` | `0x8000` |
| `esp32_touch_toolbox_vocab_lab.bin` | `0x10000` |

使用此命令保留现有 NVS 中的 Wi-Fi 设置和触摸校准；不要执行整片擦除。
包中仅包含构建产物，不包含设备 Flash 备份、NVS、账号、日志或本机配置。

## 使用

烧录复位后恢复 Dashboard 监控，在 GUI 的 PC SCREEN 页面选择窗口，
设备进入 SYSTEM → PC SCREEN。先轻触目标位置再放大，以最后触摸位置为中心；
放大后拖动移动取景，FIT 回到全图，UP / DN 滚动。

Dashboard 的 GUI 可以关闭，后台仍会继续运行。权限不一致会限制窗口采集和控制，
建议目标软件与 Dashboard 都用普通权限启动；最小化和 GPU 窗口能否采集取决于软件。
设备仍采用节省内存的索引缓存，整窗缩小后的极细字体请用局部放大查看。
