# ESP32 触摸仪表盘与工具箱

[![固件构建](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/build.yml/badge.svg)](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/build.yml)
[![主机测试](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/host-tests.yml/badge.svg)](https://github.com/mengqy2022/Esp32-s3-touch/actions/workflows/host-tests.yml)

[English](README.md) · [文档目录](docs/README.md) · [更新记录](CHANGELOG.md)

本项目把电脑监控和本机 Codex 今日 Token／人民币估算费用直接放在
320×240 触摸主界面上。小游戏、系统工具、元器件库存和单词实验室通过
GAME、SYSTEM、OTHER 三个分类进入。Windows 配套 EXE 负责采集与发送数据，
安装后在用户登录时启动，未插设备时等待，插入后自动连接。

> 仓库名保留 `Esp32-s3-touch`，但本次实机报告为 **ESP32-D0WD-V3**。
> 当前工程目标为 **`esp32`**，使用 **ESP-IDF 5.5.4 / LVGL 8.4**。
> 不要因仓库名称把目标切换为 `esp32s3`。引脚定义见 [硬件说明](docs/HARDWARE.md)。

## 当前功能

| 页面／程序 | 功能 |
| --- | --- |
| 主界面 | 日期、星期、Wi-Fi 状态、时钟；CPU/GPU/RAM 圆环、温度、内存用量。闲置时继续显示主页。 |
| CODEX 卡片 | 今日输入＋输出 Token；可选的个人目标进度；`~¥` 人民币估算费用，约每 5 秒更新。 |
| GAME | SUDOKU 数独、2048、FLAPPY。 |
| SYSTEM | SD CHECK、SYSTEM INFO、WIFI、CALIBRATE、PC DETAILS。 |
| OTHER | INVENTORY 库存／BOM、VOCAB LAB 本地词书与学习计划、间隔复习、触屏默写。 |
| Windows EXE | 当前用户安装、登录自启开关、设备检测、暂停／恢复、修改价格和汇率、查看轮换日志。 |

工具的 BACK 返回对应分类，分类的 BACK 返回主页，PC DETAILS 点击返回主页。
电脑数据需要 PC 配套程序持续运行；离线游戏和本地工具可独立使用。
温度／GPU 读取依赖电脑硬件与驱动，不支持的数据显示 `--`。

## EXE 快速使用

1. 获取维护者发布的 `ESP32TouchDashboard.exe`，或按下文自行构建。
   Git 源码中不保存 EXE；目前不承诺已经发布公开下载版本。
2. 把设备接到电脑，确认设备管理器出现串口。测试板使用 CH340，必要时安装对应驱动。
3. 双击 EXE 并选择安装。无需 Python 或管理员权限，安装在
   `%LOCALAPPDATA%/ESP32TouchDashboard`，首次安装会启用当前用户登录自启。
4. 从开始菜单打开 **ESP32 Touch Dashboard**，确认“开机自启：已启用”。
   此处还可以关闭自启、暂停／恢复、打开价格配置与日志。
5. 烧录、库存串口操作或使用其他串口工具之前，先暂停监控；完成后恢复。

**自启发生在 Windows 登录后。关闭自启只影响下次登录；暂停则释放当前串口，
暂停状态会保留到下次登录。** 新电脑上需要安装一次 EXE；本机 Codex 日志不会随设备迁移。
完整步骤见 [Windows 软件手册](docs/WINDOWS_APP_CN.md)。

## Token 与人民币金额

统计来源为本机 Codex 会话日志，按电脑本地日期汇总输入和输出。
缓存输入已经包含在输入计数中。金额按模型的普通输入、缓存读取、缓存写入、
输出单价分别估算，再换算人民币，显示如 `~¥12.34`。
默认示例单价由使用者提供，汇率 7.20 可修改，详见 [统计与价格说明](docs/CODEX_USAGE_CN.md)。

统计不等于官方套餐额度、实际账单或跨电脑总用量。程序不会向设备发送对话文本、
账号凭据或 API Key。缺少有效日志时显示 NO DATA；未知模型／不完整价格时
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

固件、EXE、缓存、依赖环境、Flash 备份、日志和本机设置都不提交 Git。
后续提供下载版时，把 EXE 放入 GitHub Releases 或 Actions 产物。
详见 [开发、测试与发布流程](docs/DEVELOPMENT.md)。

## 文档入口

| 文档 | 内容 |
| --- | --- |
| [详细功能说明](docs/HOME_DASHBOARD_CN.md) | 主界面、全部分类、数据更新和失效行为 |
| [EXE 使用手册](docs/WINDOWS_APP_CN.md) | 安装、自启、暂停、迁移、更新、卸载、排障 |
| [Codex 统计与计价](docs/CODEX_USAGE_CN.md) | 日志口径、默认单价、公式、配置和限制 |
| [硬件说明](docs/HARDWARE.md) | 芯片目标、屏幕、引脚表 |
| [架构说明](docs/ARCHITECTURE.md) | 固件与主机模块、数据流、线程规则 |
| [串口协议](docs/PROTOCOL.md) | PC 遥测与 FILE 文件传输 |
| [词书说明](docs/VOCABULARY.md) | SD 目录、CSV、学习计划 |
| [开发指南](docs/DEVELOPMENT.md) | 构建、测试、源码提交与发布 |
| [验证记录](docs/VALIDATION.md) | 已测试结果与尚未验证的范围 |
| [后续开发设想](docs/ROADMAP_CN.md) | EXE 易用性、资源优化、设备与统计能力 |

历史 V4～V6.1 升级笔记保留在 `docs/`，不代表当前全部行为。
项目采用 [MIT 许可](LICENSE)，第三方组件和词书说明见
[第三方声明](docs/THIRD_PARTY_NOTICES.md)，贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。
