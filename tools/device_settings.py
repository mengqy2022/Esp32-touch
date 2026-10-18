"""Device preferences, safe config writes and Windows PnP diagnostics."""
import json
from pathlib import Path
import subprocess

CH340_VID = 0x1A86
CH340_PID = 0x7523
WCH_PAGE = 'https://www.wch.cn/downloads/CH341SER_EXE.html'


def load_config(path):
    config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict) or not isinstance(config.get('device'), dict):
        raise ValueError('设备配置格式无效')
    # Migrate the earlier combined mode; each view now belongs to one provider.
    if config.get('ai_source') in (None, 'all'):
        config['ai_source'] = 'codex'
    if config['ai_source'] not in ('codex', 'claude'):
        raise ValueError('AI 来源配置无效')
    interval = config.get('codex_refresh', 5)
    if type(interval) not in (float, int) or not 1 <= interval <= 3600:
        raise ValueError('用量刷新间隔必须为 1～3600 秒')
    device = config['device']
    if device.get('mode', 'auto') not in ('auto', 'manual'):
        raise ValueError('COM 模式配置无效')
    for key in ('vid', 'pid'):
        if type(device.get(key)) is not int or not 0 <= device[key] <= 65535:
            raise ValueError('USB 设备标识无效')
    if device.get('mode') == 'manual' and not device.get('device'):
        raise ValueError('请选择手动 COM 端口')
    target = config.get('screen_window')
    if target is not None:
        if (not isinstance(target, dict) or
                any(type(target.get(key)) is not int or not 0 < target[key] <= maximum
                    for key, maximum in (('hwnd', 2**64 - 1), ('pid', 2**32 - 1), ('cookie', 2**31 - 1)))):
            raise ValueError('窗口配置无效，请重新选择窗口')
    return config


def save_config(path, config):
    path = Path(path)
    updated = dict(config)
    updated.pop('daily_goal', None)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def selected_device(port):
    return dict(mode='manual', device=port.device, vid=port.vid if port.vid is not None else 0,
                pid=port.pid if port.pid is not None else 0,
                serial_number=port.serial_number or '', location=port.location or '')


def query_ch340():
    """Present PnP devices include code 28 devices that have no COM port yet."""
    script = r'''$ErrorActionPreference='Stop'
    [Console]::OutputEncoding=[System.Text.Encoding]::UTF8
    @(Get-CimInstance Win32_PnPEntity | Where-Object {
      $_.Present -ne $false -and $_.PNPDeviceID -match 'USB\\VID_1A86&PID_(7523|5523)'
    } | ForEach-Object { [pscustomobject]@{
      name=$_.Name; id=$_.PNPDeviceID; code=[int]$_.ConfigManagerErrorCode
    } }) | ConvertTo-Json -Compress'''
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, encoding='utf-8', errors='replace', timeout=25,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return None
        devices = json.loads(result.stdout.strip() or '[]')
        return devices if isinstance(devices, list) else [devices]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def driver_summary(devices):
    if devices is None:
        return 'CH340：无法查询驱动状态，可打开设备管理器检查。'
    if not devices:
        return 'CH340：未发现已接入设备；无法据此判断驱动是否已安装。'
    return '\n'.join('CH340：' + str(d.get('name') or 'USB 设备') + '，' +
                     ('驱动正常' if d.get('code') == 0 else
                      '缺少驱动（代码 28）' if d.get('code') == 28 else
                      '设备异常，代码 ' + str(d.get('code'))) for d in devices)


def install_signed_driver(path):
    """Verify the vendor's Authenticode signature before requesting UAC."""
    path = Path(path).resolve()
    if path.suffix.lower() != '.exe':
        raise ValueError('请选择 WCH 官方 CH341SER.EXE 安装程序')
    # ArgumentList is a separate native process argument; the path is never shell code.
    script = r'''param([string]$DriverPath)
    $ErrorActionPreference='Stop'
    $sig=Get-AuthenticodeSignature -LiteralPath $DriverPath
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'QinHeng|WCH|Jiangsu Qin') {
      throw '驱动签名无效或发布者不是 WCH / QinHeng，已取消安装。'
    }
    $p=Start-Process -FilePath $DriverPath -Verb RunAs -Wait -PassThru
    exit $p.ExitCode'''
    # Use an on-disk script to avoid interpolation or PowerShell argument quoting.
    script_path = path.parent / 'install_wch.ps1'
    script_path.write_text(script, encoding='utf-8-sig')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                             '-File', str(script_path), '-DriverPath', str(path)],
                            capture_output=True, encoding='utf-8', errors='replace',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('驱动未安装：用户取消、签名验证失败或安装失败。\n' + result.stderr[-1200:])
