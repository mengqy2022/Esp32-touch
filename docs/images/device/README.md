# 主页与分类界面图片说明

本组图片随 2026-10-20 文档更新上传，供中英文 README 和 [系统图文手册](../../HOME_DASHBOARD_CN.md) 展示导航与主要功能。

## 采集方式

- 从当前 `main/ui.c` 原样提取主页、分类页、控件样式、金额字体和数据刷新函数，在本机编译并使用工程的 LVGL 8.4 离屏运行；没有重画界面或替换字体。
- 输出为 320×240，RGB565、字节交换、48 KiB LVGL 堆，使用 Montserrat 14 / 16 字体及工程的 130 DPI 设置，通过显示刷新回调读取像素，PNG 保留原始尺寸。
- 时钟、Wi-Fi 和 PC 状态由内存替身提供。固定时间 2026-10-20 10:30，CPU 32%、GPU 18%、RAM 46%，温度和内存均为展示用数据。
- Codex 示例为 128,000 Token、12.34 元，Claude 示例为 64,000 Token、5.67 元；均为合成数据，不使用私人日志，也不用于演示计价公式。
- 通过实际 AI 按钮事件与刷新函数切换 Claude；分类页直接调用实际构建函数，菜单导航和 BACK 的硬件回调未执行。采集时检查日期、两组 Token 文本和 5 / 6 / 3 个分类入口数量。

这些是**当前源码的界面渲染截图，不是实物照片**，不包含 LCD 背光、拍摄效果或触摸延迟。
截图检查不代替实体触摸、串口传输、重启记忆或所有子页面的验收；本次仅更新图片和文档，
未重新构建、烧录或替换下载包。硬件验证范围见 [验证记录](../../VALIDATION.md)。

## 文件与图注

| 文件 | 展示功能 |
| --- | --- |
| [home.png](home.png) | 日期／时钟、PC 在线状态、CPU/GPU/RAM 圆环、Codex 用量与估算金额，以及三个分类入口 |
| [home-claude.png](home-claude.png) | 设备主页选中 CLAUDE 的按钮高亮，以及独立 Token 与金额显示 |
| [game.png](game.png) | SUDOKU、2048、FLAPPY、SNAKE、BREAKOUT 五款游戏入口 |
| [system.png](system.png) | SD CHECK、SYSTEM INFO、WIFI、CALIBRATE、PC DETAILS、PC SCREEN 六个工具入口 |
| [other.png](other.png) | INVENTORY、VOCAB LAB、SALARY CAT 三个功能入口 |

月薪猫的动态预览及设置配图另见 [月薪猫图片说明](../salary-cat/README.md)。
