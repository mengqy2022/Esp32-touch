# Windows 下载包

[下载 ESP32TouchDashboard.exe](https://github.com/mengqy2022/Esp32-touch/raw/refs/heads/main/dist/ESP32TouchDashboard.exe)
· [SHA-256 校验文件](SHA256SUMS.txt)
· [完整安装与使用手册](../docs/WINDOWS_APP_CN.md)
· [下载 PC SCREEN 设备固件包](https://github.com/mengqy2022/Esp32-touch/raw/refs/heads/main/dist/ESP32Touch-PC-SCREEN-firmware.zip)
· [固件烧录说明](PC_SCREEN_FIRMWARE_CN.md)

这是 Windows x64 配套程序，版本为 2026.10.18.4，使用 Python 3.11 和
PyInstaller 6.22.3，文件大小约 12.97 MiB。无需另装 Python。
安装后登录 Windows 自动等待设备，连接后发送电脑监控和本机 Codex／Claude Code 独立用量数据。

**2026-10-20 源码更新：** [月薪猫与界面截图](../docs/SALARY_CAT_CN.md)已加入工程，
本地配套 EXE `2026.10.20.1` 和新固件已完成构建及实机检查。
本次同步源码、素材与图文说明，**本目录现有 EXE／固件下载包仍为 2026-10-18 版，不含月薪猫**；
需要此功能时请按 [开发指南](../docs/DEVELOPMENT.md)构建当前源码，勿将旧下载包当作新版。

## 2026-10-18 更新内容

| 更新 | 如何使用 |
| --- | --- |
| 深色桌面 GUI | 双击进入控制中心，左侧选择设备连接、PC SCREEN、AI 用量、设置与日志；可连续操作 |
| 指定窗口投射与切换 | 在 PC SCREEN 按标题／进程搜索，双击或点“共享所选窗口”；设备进入 SYSTEM → PC SCREEN，更换目标无需重开串口 |
| 局部放大与滚动 | 设备先触摸想看的位置，再按 2X／4X／8X 放大；放大后拖动平移，FIT 返回全图，UP／DN 滚动 ChatGPT 等窗口；轻触同时发送点击 |
| 网易云快捷控制 | 选择 `cloudmusic.exe`，设备显示 PREV／PLAY／NEXT／VOL-／VOL+，不提供实时播放进度 |
| 游戏升级 | 新增 SNAKE／BREAKOUT，改进数独键盘与高亮、2048 滑动及 Flappy 画面；顶部 II 暂停、GO 继续、NEW 重开／换题 |
| .4 黑屏修复 | 后台独立保留解包运行环境，关闭 GUI 后继续采集，修复一直停在 `Switching window...` 的问题 |

这些功能集成于原有系统；升级设备请同时下载上方完整固件包。
适用硬件为已验证的 **ESP32-D0WD-V3、4 MB Flash、ILI9341 320×240 + XPT2046**，
不能直接用于 ESP32-S3。PC SCREEN 是低频指定窗口查看，细字需局部放大；
最小化、GPU 窗口和后台控制取决于软件，详见 [使用手册](../docs/WINDOWS_APP_CN.md)。

## 从 GitHub 下载

使用上面的下载链接，或打开本目录的 `ESP32TouchDashboard.exe` 文件页面，
点击 **Download raw file**。不要把 GitHub 文件页面另存为 HTML 后改成 EXE。
程序未进行代码签名，Windows 可能显示发布者未知。

下载后可在 PowerShell 中核对哈希：

```powershell
Get-FileHash -LiteralPath .\ESP32TouchDashboard.exe -Algorithm SHA256
```

将结果与 `SHA256SUMS.txt` 比较。校验文件用于检查下载完整性。
源码、构建脚本和依赖版本也保留在仓库中，可自行构建。

## 安装与更新

双击 EXE 打开 GUI 并启动后台；在“设备连接”保存端口、连接／恢复或暂停监控。
需要创建开始菜单入口及启用登录自启时，显式运行 `ESP32TouchDashboard.exe --install`。
“设置与日志”管理自启和日志，“AI 用量”打开价格与汇率配置；
“设备连接”提供 COM 检查／选择、CH340 驱动检查／安装入口。
设备主页支持 CODEX／CLAUDE 触摸切换并记住选择；EXE 来源切换为备用入口。
请同步更新固件与配套程序，以支持独立来源数据包。自启发生在用户登录后，未连接设备时后台等待。

安装沿用运行目录：从非 C 盘首次运行默认使用 EXE 旁 `.dashboard`，已有目录可继续使用；
无其他配置且从 C 盘运行时回退到 `%LOCALAPPDATA%/ESP32TouchDashboard`。
需避免系统盘新增应用数据时，请按手册设置运行目录和解包目录。

已有安装时，升级前先暂停并结束旧后台，再运行下载的新程序进行显式安装：

```powershell
.\ESP32TouchDashboard.exe --install
```

已有设备配置和自定义价格／汇率保留，旧内置 USD 单价自动迁移并备份，旧每日目标删除。
仅双击下载的新 EXE 可能打开现有控制窗口，
不等于替换已安装程序；详见使用手册的更新章节。

本目录保留发布用 EXE、PC SCREEN 完整系统固件 ZIP、校验和及说明。临时产物、其他固件、日志、
本机配置、个人 Codex 日志和恢复备份不在下载包中。

设备触摸切换依赖配套新固件；旧固件不识别新版的独立来源数据包。
WCH 的下载页面校验可能阻止自动下载，此时可从官方页面手动下载后选本地安装。
驱动安装验证发布者签名并请求 Windows 管理员权限，本次没有实际安装驱动。

### Windows temporary-directory compatibility

The bundled `ESP32TouchDashboard.exe` uses `%TEMP%` for PyInstaller extraction instead of a developer-specific `F:` path. It should therefore start on PCs without an `F:` drive, provided the current user's Windows temporary directory is writable. Future builds leave `-RuntimeTemp` unset by default.
