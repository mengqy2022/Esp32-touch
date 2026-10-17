# Windows 下载包

[下载 ESP32TouchDashboard.exe](https://github.com/mengqy2022/Esp32-touch/raw/refs/heads/main/dist/ESP32TouchDashboard.exe)
· [SHA-256 校验文件](SHA256SUMS.txt)
· [完整安装与使用手册](../docs/WINDOWS_APP_CN.md)

这是 Windows x64 配套程序，版本为 2026.10.17.2，使用 Python 3.11 和
PyInstaller 6.22.3，文件大小约 7.52 MiB。首次运行选择安装，无需另装 Python。
安装后登录 Windows 自动等待设备，连接后发送电脑监控和本机 Codex／Claude Code 独立用量数据。

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

首次双击安装后，从开始菜单打开 **ESP32 Touch Dashboard**，可以设置登录自启、
暂停／恢复、价格与汇率，以及 COM 检查／选择、CH340 驱动检查／安装入口。
设备主页支持 CODEX／CLAUDE 触摸切换并记住选择；EXE 来源切换为备用入口。
请同步更新固件与配套程序，以支持独立来源数据包。自启发生在用户登录后，未连接设备时后台等待。

已有安装时，升级前先暂停并结束旧后台，再运行下载的新程序进行显式安装：

```powershell
.\ESP32TouchDashboard.exe --install
```

已有设备配置和自定义价格／汇率保留，旧内置 USD 单价自动迁移并备份，旧每日目标删除。
仅双击下载的新 EXE 可能打开现有控制窗口，
不等于替换已安装程序；详见使用手册的更新章节。

本目录只保留发布用 EXE、校验和及说明。临时产物、其他固件、日志、
本机配置、个人 Codex 日志和恢复备份不在下载包中。

设备触摸切换依赖配套新固件；旧固件不识别新版的独立来源数据包。
WCH 的下载页面校验可能阻止自动下载，此时可从官方页面手动下载后选本地安装。
驱动安装验证发布者签名并请求 Windows 管理员权限，本次没有实际安装驱动。
