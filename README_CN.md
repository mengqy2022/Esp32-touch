# ESP32 触摸仪表盘与工具箱

[![固件构建](https://github.com/mengqy2022/Esp32-touch/actions/workflows/build.yml/badge.svg)](https://github.com/mengqy2022/Esp32-touch/actions/workflows/build.yml)
[![主机测试](https://github.com/mengqy2022/Esp32-touch/actions/workflows/host-tests.yml/badge.svg)](https://github.com/mengqy2022/Esp32-touch/actions/workflows/host-tests.yml)

[English](README.md) · [文档目录](docs/README.md) · [更新记录](CHANGELOG.md)

本项目把电脑监控和本机 Codex／Claude Code 今日 Token／人民币估算费用直接放在
320×240 触摸主界面上，并可投射指定 PC 软件窗口、局部放大及触摸控制。
小游戏、系统工具、元器件库存和单词实验室通过
GAME、SYSTEM、OTHER 三个分类进入。Windows 配套 EXE 负责采集与发送数据，
安装后在用户登录时启动，未插设备时等待，插入后自动连接。

> 本次实机报告为 **ESP32-D0WD-V3**。
> 当前工程目标为 **`esp32`**，使用 **ESP-IDF 5.5.4 / LVGL 8.4**。
> 不要因仓库名称把目标切换为 `esp32s3`。引脚定义见 [硬件说明](docs/HARDWARE.md)。

## 当前功能

| 页面／程序 | 功能 |
| --- | --- |
| 主界面 | 日期、星期、Wi-Fi 状态、时钟；CPU/GPU/RAM 圆环、温度、内存用量。闲置时继续显示主页。 |
| AI 用量卡片 | 在设备主页点选 CODEX／CLAUDE，独立查看今日用量并记住选择；左侧 Token、右侧 `~¥` 人民币估算金额，约每 5 秒更新，无每日限额。 |
| GAME | SUDOKU 数独、2048、FLAPPY、SNAKE 贪吃蛇、BREAKOUT 打砖块；统一暂停／继续和重新开始。 |
| SYSTEM | PC SCREEN、SD CHECK、SYSTEM INFO、WIFI、CALIBRATE、PC DETAILS。 |
| OTHER | INVENTORY 库存／BOM、VOCAB LAB 本地词书与学习计划、间隔复习、触屏默写。 |
| Windows EXE | 深色桌面 GUI：设备连接、PC SCREEN、AI 用量、设置与日志；支持窗口搜索与切换、COM 检查、CH340 驱动检查／安装入口和登录自启。 |

工具的 BACK 返回对应分类，分类的 BACK 返回主页，PC DETAILS 点击返回主页。
电脑数据需要 PC 配套程序持续运行；离线游戏和本地工具可独立使用。
温度／GPU 读取依赖电脑硬件与驱动，不支持的数据显示 `--`。

## EXE 快速使用

1. [下载 ESP32TouchDashboard.exe](https://github.com/mengqy2022/Esp32-touch/raw/refs/heads/main/dist/ESP32TouchDashboard.exe)，
   或按下文自行构建。仓库 [dist 下载说明](dist/README.md)包含 Windows x64 程序与 SHA-256 校验文件。
2. 把设备接到电脑，确认设备管理器出现串口。测试板使用 CH340，必要时安装对应驱动。
3. 双击 EXE 打开控制中心，在“设备连接”选择端口，点击“连接 / 恢复监控”。
   无需另装 Python；安装驱动时才需要管理员权限。
4. 如需安装到当前用户并创建开始菜单入口，运行 `ESP32TouchDashboard.exe --install`；
   安装沿用当前运行目录并启用登录自启。从非 C 盘首次运行时默认使用 EXE 旁的 `.dashboard`，
   已有运行目录可继续使用，完整路径规则见软件手册。
5. 烧录、库存串口操作或使用其他串口工具之前，先暂停监控；完成后恢复。

**自启发生在 Windows 登录后。关闭自启只影响下次登录；暂停则释放当前串口，
暂停状态会保留到下次登录。** 新电脑需要自启时请安装一次 EXE；本机 Codex 日志不会随设备迁移。
完整步骤见 [Windows 软件手册](docs/WINDOWS_APP_CN.md)。

## 本次更新：PC SCREEN 与游戏

这是原有系统的新增功能，保留主页、AI 用量、库存和词书。
当前配套 EXE 为 **2026.10.18.4**；旧设备需同时更新
[完整系统固件](dist/PC_SCREEN_FIRMWARE_CN.md)。

1. 在 EXE 左侧进入 **PC SCREEN**，按窗口标题或进程名搜索，双击目标或点击“共享所选窗口”。
2. 在设备进入 **SYSTEM → PC SCREEN**。切换软件时在 EXE 重新选择即可，无需重开串口；“停止共享”清除选择。
3. 先轻触想看的位置，再点击放大按钮，依次切换 **2X → 4X → 8X → FIT**；
   以最后触摸位置为中心，放大后拖动平移，FIT 恢复全图。轻触也会向目标发送左键点击。
4. **UP / DN** 滚动 ChatGPT 等窗口；选择网易云音乐 `cloudmusic.exe` 后，设备显示
   **PREV / PLAY / NEXT / VOL- / VOL+** 专用控制按钮。

画面采用 320×176 RGB332 串口帧与节省内存的 256×140 索引缓存。
整窗缩小仍会损失细字，请使用局部放大；115200 波特率适合低频查看和操作，
不适合视频。最小化／GPU 窗口的采集和后台触摸响应取决于软件；优先让目标与 Dashboard 均以普通权限运行。
**2026.10.18.4 修复关闭 GUI 后停在 `Switching window...` 的问题**，关闭控制中心后后台仍继续运行。

GAME 新增贪吃蛇与打砖块；2048 支持滑动／方向键，数独改为大数字键盘并增加行列／宫格高亮，
Flappy 更新背景和状态显示。各游戏顶部 **II** 暂停、**GO** 继续、**NEW** 重开；数独 NEW 换题。
具体操作见 [系统功能](docs/HOME_DASHBOARD_CN.md)，实测范围见 [验证记录](docs/VALIDATION.md)。

## Token 与人民币金额

统计来源为本机 Codex 和 Claude Code 会话日志，按电脑本地日期汇总输入和输出。
直接点选设备主页用量卡片上的 CODEX／CLAUDE，立即切换各自的 Token 与金额。
设备记住选择，电脑刷新／重连不会覆盖；EXE 控制窗口提供备用切换入口。
缓存输入已经包含在输入计数中。金额按模型的普通输入、缓存读取、缓存写入、
输出单价分别估算，再换算人民币，显示如 `~¥12.34`。
默认示例单价由使用者提供，汇率 7.20 可修改，详见 [统计与价格说明](docs/CODEX_USAGE_CN.md)。

统计不等于官方套餐额度、实际账单或跨电脑总用量。AI 用量数据包不会向设备发送对话文本、
账号凭据或 API Key；启用 PC SCREEN 后会传送所选窗口画面，请留意窗口中的私人内容。
缺少有效日志时显示 NO DATA；未知模型／不完整价格时
金额显示 `~¥--`。PC 数据超过 5 秒、Codex 数据超过 90 秒未更新会失效。

## 开发构建

固件在 ESP-IDF 5.5.4 环境中构建：

```powershell
idf.py set-target esp32
idf.py build
idf.py -p COM5 flash
```

首次克隆时选择目标；已有本机配置则保留。COM5 是示例，请换成实际串口。
Windows EXE 使用 Python 3.11 x64 构建：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

产物位于 `dist/ESP32TouchDashboard.exe`。终端版主机工具可直接运行：

```powershell
python -m pip install -r tools/requirements.txt
python tools/pc_monitor_host.py --port COM5 --codex-prices tools/codex_prices.json
```

仓库明确保留 `dist/ESP32TouchDashboard.exe`、[PC SCREEN 完整系统固件 ZIP](dist/PC_SCREEN_FIRMWARE_CN.md) 与校验文件作为下载包。
其他固件／EXE、缓存、依赖环境、Flash 备份、日志和本机设置不提交 Git。
后续版本也可以放入 GitHub Releases，便于保留版本与下载记录。
详见 [开发、测试与发布流程](docs/DEVELOPMENT.md)。

## 文档入口

| 文档 | 内容 |
| --- | --- |
| [详细功能说明](docs/HOME_DASHBOARD_CN.md) | 主界面、全部分类、数据更新和失效行为 |
| [EXE 使用手册](docs/WINDOWS_APP_CN.md) | 安装、自启、暂停、迁移、更新、卸载、排障 |
| [Codex 统计与计价](docs/CODEX_USAGE_CN.md) | 日志口径、默认单价、公式、配置和限制 |
| [硬件说明](docs/HARDWARE.md) | 芯片目标、屏幕、引脚表 |
| [架构说明](docs/ARCHITECTURE.md) | 固件与主机模块、数据流、线程规则 |
| [串口协议](docs/PROTOCOL.md) | PC 遥测、SCREEN 画面／触摸与 FILE 文件传输 |
| [词书说明](docs/VOCABULARY.md) | SD 目录、CSV、学习计划 |
| [开发指南](docs/DEVELOPMENT.md) | 构建、测试、源码提交与发布 |
| [验证记录](docs/VALIDATION.md) | 已测试结果与尚未验证的范围 |
| [后续开发设想](docs/ROADMAP_CN.md) | EXE 易用性、资源优化、设备与统计能力 |

历史 V4～V6.1 升级笔记保留在 `docs/`，不代表当前全部行为。
项目采用 [MIT 许可](LICENSE)，第三方组件和词书说明见
[第三方声明](docs/THIRD_PARTY_NOTICES.md)，贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。
