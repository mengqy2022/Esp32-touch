# 月薪猫界面图片说明

这些图片随 2026-10-20 月薪猫源码更新上传，供 README 和操作手册展示关键功能。

## 采集方式

- 直接编译并运行当前 `main/salary_ui.c`、`salary.c`、`font_salary16.c`、`ui_widgets.c`、`ui_theme.c` 和 `salary_cat.rle`，使用工程中的 LVGL 8.4。
- 使用 320×240 离屏显示回调截取 LVGL 像素，采用 RGB565、字节交换、48 KiB LVGL 堆及相同页面字体设置；PNG 不作字体替换或画面重绘。
- 固定示例时间为 2026-10-20 10:30，月薪 6,000 元，09:00–12:00、14:00–17:00，使用内置 2026 中国调休日历。补班截图单独固定到 2026-10-10 10:30。
- 设置和校时由离屏程序的内存替身提供；点击实际 LVGL 控件进入各页。今日／本月／年薪金额、18 个工作日和补班提示在采集时作断言检查。
- GIF 连续采样 24 次，每次间隔 140 毫秒；编码合并相邻重复画面后为 23 帧，总时长 3.36 秒，循环播放。它展示动画会变化，不是设备帧率或流畅度测试。

这是**当前界面的软件渲染截图，不是实物照片**，没有模拟 LCD 背光、拍摄效果或实体触摸。
设备构建、烧录与运行检查另见 [验证记录](../../VALIDATION.md)；触摸手感、NVS 重启记忆和实物观感仍需实测。

## 文件与图注

| 文件 | 展示功能 |
| --- | --- |
| [animated-dashboard.gif](animated-dashboard.gif) | 黑白主页与持续播放的透明灰阶猫咪 |
| [today.png](today.png) | 今日已赚 83.33 元、今日已工作 01:30:00、午休倒计时 |
| [month.png](month.png) | 轻触金额后切换到本月累计估算 3,083.33 元 |
| [annual.png](annual.png) | 再次轻触切换到年薪估算 72,000 元 |
| [settings.png](settings.png) | 设备端月薪和班次设置列表，可上下滑动 |
| [salary-input.png](salary-input.png) | 月薪金额输入、DEL 删除与 OK 确认 |
| [weekdays.png](weekdays.png) | 每周工作日选择，周一至周五高亮 |
| [date-override.png](date-override.png) | 指定日期设为上班、休息或自动 |
| [makeup-workday.png](makeup-workday.png) | 2026-10-10 周六补班计薪，底部提示“调休上班” |

猫咪来源和字体许可见 [素材说明](../../../assets/salary_cat/README.md)，原图不因截图而改变许可。
