"""Small Windows executable: per-user install, login startup, USB monitoring.

Uses native Windows dialogs. Only driver installation requests administrator rights.
"""
import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import winreg

import serial.tools.list_ports

from dashboard_agent import run_agent, matching_port
from device_settings import (load_config, save_config, selected_device, query_ch340,
                             driver_summary, install_signed_driver, WCH_PAGE)
from ai_usage import SOURCES
from pc_screen import Window

APP_NAME = 'ESP32TouchDashboard'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
APPROVED_KEY = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'
APP_VERSION = '2026.10.18.3'


def choose_screen_window(root):
    windows = Window()
    while True:
        config = load_config(root / 'config.json')
        targets = windows.list()
        current = (config.get('screen_window') or {}).get('title', '未选择')
        selected = native_command_dialog('PC SCREEN：窗口与触摸控制',
            '当前窗口：' + current + '\n选择后，在设备 SYSTEM → PC SCREEN 查看并触摸控制。'
            '\n只控制所选窗口；关闭窗口后需要重新选择。\n最小化采集与后台操作取决于软件支持；黑屏时请还原窗口。',
            [(501, '停止窗口共享与控制'), (502, '刷新窗口列表')] +
            [(600 + i, target['title'][:100] +
              f"\n{target.get('process') or '未知程序'}  PID {target['pid']}")
             for i, target in enumerate(targets)], root)
        if selected == 502:
            continue
        if selected == 501:
            config.pop('screen_window', None)
        elif 600 <= selected < 600 + len(targets):
            try:
                config['screen_window'] = windows.select(targets[selected - 600])
            except (OSError, ValueError) as error:
                message('窗口选择失败：' + str(error) + '\n\n请先刷新列表后重试。', 16)
                continue
        else:
            return
        save_config(root / 'config.json', config)
        return


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def update_prices(root):
    """Migrate shipped legacy rates; preserve user FX, custom rates and other models."""
    path = root / 'codex_prices.json'
    template = json.loads((resource_root() / 'codex_prices.json').read_text(encoding='utf-8'))
    if not path.exists():
        path.write_text(json.dumps(template, indent=2), encoding='utf-8')
        return
    current = json.loads(path.read_text(encoding='utf-8-sig'))
    updated = json.loads(json.dumps(current))
    old_rates = {
        'gpt-6.1-sol': ([2, .1, 2.5, 10], [4, .2, 5, 15]),
        'gpt-6-astra': ([10, 1, 12.5, 50], [20, 2, 25, 75]),
    }
    fields = ['input_per_million', 'cached_input_per_million', 'cache_write_input_per_million', 'output_per_million']
    models = updated.setdefault('models', {})
    for model, rates in template['models'].items():
        old = models.get(model)
        legacy = old_rates.get(model)
        if old is None or (current.get('currency') == 'USD' and legacy and
                           all([old.get(tier, {}).get(f) for f in fields] == expected
                               for tier, expected in zip(('short', 'long'), legacy))):
            # Do not copy USD defaults into a user-defined CNY price file.
            if current.get('currency') == 'USD':
                models[model] = rates
    if current != updated:
        backup = root / 'codex_prices.before-2026-10-17.json'
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')


def choose_ai_source(root):
    config = load_config(root / 'config.json')
    selected = native_command_dialog('AI 用量来源（备用入口）', '优先在设备主页点选 CODEX / CLAUDE，设备会记住选择。\n也可以在此切换已连接设备的来源。',
                                    [(202, 'Codex\n显示 Codex 的今日 Token 和估算金额'),
                                     (203, 'Claude Code\n显示 Claude Code 的今日 Token 和估算金额')], root)
    source = {202: 'codex', 203: 'claude'}.get(selected)
    if source:
        port = matching_port(serial.tools.list_ports.comports(), config['device'])
        set_device_source(root, port, source)
        config['ai_source'] = source
        save_config(root / 'config.json', config)


def com_settings(root):
    while True:
        config = load_config(root / 'config.json')
        ports = list(serial.tools.list_ports.comports())
        device = config['device']
        selected_port = matching_port(ports, device)
        info = '模式：' + ('手动固定端口' if device.get('mode') == 'manual' else '自动识别 CH340')
        info += '\n目标端口：' + (selected_port or device.get('device', '未选择'))
        info += '\n保存后自动生效；切换端口会释放原串口。\n'
        info += '\n'.join(f'{p.device}：{p.description}' for p in ports) or '未发现 COM 端口'
        buttons = [(301, '自动识别 CH340'), (302, '刷新端口列表'), (303, '检查连接\n暂时释放监控串口，检查 FILE:PONG 响应')]
        buttons += [(400 + i, f'使用 {p.device}\n{p.description}') for i, p in enumerate(ports)]
        selected = native_command_dialog('COM 检查与设置', info, buttons, root)
        if selected == 301:
            config['device'] = dict(vid=0x1A86, pid=0x7523, mode='auto')
            save_config(root / 'config.json', config)
        elif selected == 302:
            continue
        elif selected == 303:
            check_connection(root, selected_port)
        elif 400 <= selected < 400 + len(ports):
            config['device'] = selected_device(ports[selected - 400])
            save_config(root / 'config.json', config)
        else:
            return


@contextmanager
def device_connection(root, port):
    if not port:
        raise RuntimeError('没有已连接的目标串口。请插入设备并选择端口。')
    marker = root / 'paused'
    was_paused = marker.exists()
    marker.touch()
    try:
        if is_running(root):
            deadline = time.monotonic() + 16
            while time.monotonic() < deadline:
                try:
                    state = json.loads((root / 'connection.json').read_text(encoding='utf-8'))
                    if state.get('paused') and not state.get('worker') and time.time() - state['updated'] < 5:
                        break
                except (OSError, ValueError, KeyError):
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError('后台尚未释放串口，请先暂停并升级旧后台程序。')
        import serial
        with serial.Serial(port=None, baudrate=115200, timeout=.2, write_timeout=2) as connection:
            connection.dtr = False
            connection.rts = False
            connection.port = port
            connection.open()
            yield connection
    finally:
        if not was_paused:
            marker.unlink(missing_ok=True)


def set_device_source(root, port, source):
    label = SOURCES[source]
    with device_connection(root, port) as connection:
        connection.reset_input_buffer()
        connection.write(('PC:AI|' + label + '\nPC:AI?\n').encode('ascii'))
        deadline = time.monotonic() + 3
        received = b''
        expected = ('PC:AI_STATE|' + label + '|').encode('ascii')
        while time.monotonic() < deadline:
            received = (received + connection.read(connection.in_waiting or 1))[-8192:]
            if expected in received:
                return
        raise RuntimeError('设备未确认来源切换，请确认固件已升级。')


def check_connection(root, port):
    try:
        with device_connection(root, port) as connection:
            connection.write(b'FILE:PING\n')
            deadline = time.monotonic() + 3
            received = b''
            while time.monotonic() < deadline:
                received = (received + connection.read(connection.in_waiting or 1))[-8192:]
                if b'FILE:PONG' in received:
                    message(port + ' 连接正常，设备已响应 FILE:PONG。')
                    return
            message(port + ' 可以打开，但未收到设备响应。请检查固件、设备选择或连接。')
    except (OSError, RuntimeError) as error:
        message('连接检查失败：' + str(error), 16)


def choose_driver_file(root):
    class OpenFileName(ctypes.Structure):
        _fields_ = [('lStructSize', wintypes.DWORD), ('hwndOwner', wintypes.HWND),
                    ('hInstance', wintypes.HINSTANCE), ('lpstrFilter', wintypes.LPCWSTR),
                    ('lpstrCustomFilter', wintypes.LPWSTR), ('nMaxCustFilter', wintypes.DWORD),
                    ('nFilterIndex', wintypes.DWORD), ('lpstrFile', wintypes.LPWSTR),
                    ('nMaxFile', wintypes.DWORD), ('lpstrFileTitle', wintypes.LPWSTR),
                    ('nMaxFileTitle', wintypes.DWORD), ('lpstrInitialDir', wintypes.LPCWSTR),
                    ('lpstrTitle', wintypes.LPCWSTR), ('Flags', wintypes.DWORD),
                    ('nFileOffset', wintypes.WORD), ('nFileExtension', wintypes.WORD),
                    ('lpstrDefExt', wintypes.LPCWSTR), ('lCustData', wintypes.LPARAM),
                    ('lpfnHook', ctypes.c_void_p), ('lpTemplateName', wintypes.LPCWSTR),
                    ('pvReserved', ctypes.c_void_p), ('dwReserved', wintypes.DWORD), ('FlagsEx', wintypes.DWORD)]
    buffer = ctypes.create_unicode_buffer(32768)
    dialog = OpenFileName(lStructSize=ctypes.sizeof(OpenFileName), lpstrFilter='WCH 安装程序\0*.exe\0\0',
                          lpstrFile=ctypes.cast(buffer, wintypes.LPWSTR), nMaxFile=len(buffer),
                          lpstrTitle='选择 WCH 官方 CH341SER.EXE', Flags=0x1800)
    api = ctypes.WinDLL('comdlg32')
    api.GetOpenFileNameW.argtypes = [ctypes.POINTER(OpenFileName)]
    if api.GetOpenFileNameW(ctypes.byref(dialog)):
        target = root / 'drivers' / 'CH341SER.EXE'
        target.parent.mkdir(exist_ok=True)
        if Path(buffer.value).resolve() != target.resolve():
            shutil.copy2(buffer.value, target)
        install_signed_driver(target)


def driver_dialog(root):
    while True:
        status = driver_summary(query_ch340())
        selected = native_command_dialog('CH340 驱动检查', status + '\n安装时由 Windows 请求管理员权限。\n安装完成后重新插拔设备，再刷新检查。',
                                         [(501, '自动下载并安装\n从 WCH 官方服务器下载，验证发布者签名'),
                                          (502, '打开 WCH 官方下载页面'), (503, '安装已下载的官方驱动'), (504, '刷新驱动状态')], root)
        try:
            if selected == 501:
                from urllib.request import Request, urlopen
                target = root / 'drivers' / 'CH341SER.EXE'
                target.parent.mkdir(exist_ok=True)
                request = Request('https://api1.wch.cn/api/official/website/common/downloadFile?fileName=CH341SER.EXE',
                                  headers={'Referer': WCH_PAGE, 'User-Agent': 'Mozilla/5.0'})
                with urlopen(request, timeout=30) as response:
                    data = response.read(32 * 1024 * 1024 + 1)
                if not data.startswith(b'MZ') or len(data) > 32 * 1024 * 1024:
                    raise RuntimeError('WCH 下载校验未通过，请打开官方页面下载，再选择“安装已下载的官方驱动”。')
                target.write_bytes(data)
                install_signed_driver(target)
            elif selected == 502:
                os.startfile(WCH_PAGE)
            elif selected == 503:
                choose_driver_file(root)
            elif selected != 504:
                return
        except (OSError, RuntimeError, ValueError) as error:
            message(str(error), 16)


def install_root():
    # A portable runtime location can move logs/config off a full system disk.
    configured = os.environ.get('ESP32_DASHBOARD_HOME')
    if configured:
        return Path(configured).resolve()
    if getattr(sys, 'frozen', False) and (Path(sys.executable).parent / 'config.json').is_file():
        return Path(sys.executable).parent
    if getattr(sys, 'frozen', False):
        workspace_runtime = Path(sys.executable).parent.parent / '.dashboard'
        if (workspace_runtime / 'config.json').is_file():
            return workspace_runtime
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command = winreg.QueryValueEx(key, APP_NAME)[0]
        installed = Path(command.split('"')[1]).parent
        if installed.drive.upper() != 'C:' and (installed / 'config.json').is_file():
            return installed
    except (OSError, IndexError):
        pass
    if getattr(sys, 'frozen', False) and Path(sys.executable).drive.upper() != 'C:':
        return Path(sys.executable).parent / '.dashboard'
    return Path(os.environ['LOCALAPPDATA']) / APP_NAME


def message(text, flags=0):
    return ctypes.windll.user32.MessageBoxW(None, text, 'ESP32 Touch Dashboard', flags)


def autostart(enabled):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            exe = install_root() / (APP_NAME + '.exe')
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}" --background')
            # Clear a prior Task Manager disable flag when the user enables it.
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as approved:
                winreg.SetValueEx(approved, APP_NAME, 0, winreg.REG_BINARY, b'\x02' + b'\x00' * 11)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def startup_status(root=None):
    root = root or install_root()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command = winreg.QueryValueEx(key, APP_NAME)[0]
    except FileNotFoundError:
        command = ''
    expected = f'"{root / (APP_NAME + ".exe")}" --background'
    registered = command.casefold() == expected.casefold() and (root / (APP_NAME + '.exe')).is_file()
    disabled = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
            flag = winreg.QueryValueEx(key, APP_NAME)[0]
            disabled = isinstance(flag, bytes) and len(flag) >= 1 and flag[0] in (3, 7)
    except FileNotFoundError:
        pass
    return dict(enabled=registered and not disabled, registered=registered,
                disabled_by_windows=disabled, command=command, paused=(root / 'paused').exists())


def control_dialog(root):
    """Native command-link dialog; keep the background free of GUI libraries."""
    status = startup_status(root)
    title = '开机自启：' + ('已启用' if status['enabled'] else '未启用')
    info = '监控：' + ('已暂停' if status['paused'] else '自动连接设备')
    config = load_config(root / 'config.json')
    ports = list(serial.tools.list_ports.comports())
    port = matching_port(ports, config['device'])
    info += '\n串口：' + (port or '等待设备')
    info += '\n用量切换：在设备主页点选 CODEX / CLAUDE'
    info += '\nWindows 登录后在后台运行。Token 和人民币估算费用约每 5 秒更新。'
    buttons = [(101, '启用开机自启\n登录后自动运行，并恢复设备监控'),
               (102, '关闭开机自启\n下次登录时不自动运行'),
               (103, '暂停监控\n释放串口，方便烧录或使用其他串口工具'),
               (104, '恢复监控\n自动等待并连接设备'),
               (105, '修改价格和汇率\n打开人民币估算费用配置'),
               (106, '查看运行日志\n查看设备连接和用量更新记录'),
               (107, 'COM 检查与设置\n自动识别、选择端口、测试连接'),
               (108, 'CH340 驱动检查与安装\n检测缺失驱动，从官方来源安装'),
               (109, '切换 AI 用量来源（备用）\n优先在设备主页点选 CODEX / CLAUDE'),
               (110, 'PC SCREEN：选择窗口与触摸控制\n在设备上查看、点击、拖动和滚动所选窗口')]
    try:
        selected = native_command_dialog(title, info, buttons, root)
    except (OSError, AttributeError):
        # Retain a clear status even if a Windows installation lacks TaskDialog.
        selected = {6:101, 7:102, 2:105}.get(message(title + '\n\n' + info + '\n\n是：启用自启并恢复监控\n否：关闭自启\n取消：打开价格配置', 3), 0)
    if selected == 101:
        autostart(True)
        resume(root)
        message('开机自启已启用。下次登录 Windows 后将自动等待设备。')
    elif selected == 102:
        autostart(False)
        message('开机自启已关闭。当前监控继续运行；需要释放串口时可选择“暂停监控”。')
    elif selected == 103:
        (root / 'paused').touch()
        message('监控已暂停，后台会释放串口。选择“恢复监控”即可重新连接。')
    elif selected == 104:
        resume(root)
    elif selected == 105:
        os.startfile(root / 'codex_prices.json')
    elif selected == 106:
        os.startfile(root / 'host.log')
    elif selected == 107:
        com_settings(root)
    elif selected == 108:
        driver_dialog(root)
    elif selected == 109:
        choose_ai_source(root)
    elif selected == 110:
        choose_screen_window(root)


def native_command_dialog(title, info, buttons, root):
    # Activate Windows common-controls v6 without adding a GUI dependency.
    manifest = root / 'dialog.manifest'
    manifest.write_text('''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity version="1.0.0.0" processorArchitecture="*" name="ESP32Dashboard.Dialog" type="win32"/>
<dependency><dependentAssembly><assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/></dependentAssembly></dependency>
</assembly>''', encoding='utf-8')
    class ActCtx(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.ULONG), ('dwFlags', wintypes.DWORD), ('lpSource', wintypes.LPCWSTR),
                    ('wProcessorArchitecture', wintypes.USHORT), ('wLangId', wintypes.USHORT),
                    ('lpAssemblyDirectory', wintypes.LPCWSTR), ('lpResourceName', wintypes.LPCWSTR),
                    ('lpApplicationName', wintypes.LPCWSTR), ('hModule', wintypes.HMODULE)]
    class Button(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('nButtonID', ctypes.c_int), ('pszButtonText', wintypes.LPCWSTR)]
    class Config(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('cbSize', wintypes.UINT), ('hwndParent', wintypes.HWND), ('hInstance', wintypes.HINSTANCE),
                    ('dwFlags', wintypes.UINT), ('dwCommonButtons', wintypes.UINT), ('pszWindowTitle', wintypes.LPCWSTR),
                    ('pszMainIcon', ctypes.c_void_p), ('pszMainInstruction', wintypes.LPCWSTR), ('pszContent', wintypes.LPCWSTR),
                    ('cButtons', wintypes.UINT), ('pButtons', ctypes.POINTER(Button)), ('nDefaultButton', ctypes.c_int),
                    ('cRadioButtons', wintypes.UINT), ('pRadioButtons', ctypes.c_void_p), ('nDefaultRadioButton', ctypes.c_int),
                    ('pszVerificationText', wintypes.LPCWSTR), ('pszExpandedInformation', wintypes.LPCWSTR),
                    ('pszExpandedControlText', wintypes.LPCWSTR), ('pszCollapsedControlText', wintypes.LPCWSTR),
                    ('pszFooterIcon', ctypes.c_void_p), ('pszFooter', wintypes.LPCWSTR), ('pfCallback', ctypes.c_void_p),
                    ('lpCallbackData', ctypes.c_ssize_t), ('cxWidth', wintypes.UINT)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateActCtxW.argtypes = [ctypes.POINTER(ActCtx)]
    kernel.CreateActCtxW.restype = ctypes.c_void_p
    context = ActCtx(cbSize=ctypes.sizeof(ActCtx), lpSource=str(manifest))
    handle = kernel.CreateActCtxW(ctypes.byref(context))
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    cookie = ctypes.c_size_t()
    kernel.ActivateActCtx.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    kernel.DeactivateActCtx.argtypes = [wintypes.DWORD, ctypes.c_size_t]
    kernel.ReleaseActCtx.argtypes = [ctypes.c_void_p]
    activated = kernel.ActivateActCtx(handle, ctypes.byref(cookie))
    try:
        if not activated:
            raise ctypes.WinError(ctypes.get_last_error())
        controls = ctypes.WinDLL('comctl32')
        labels = (Button * len(buttons))(*(Button(number, text) for number, text in buttons))
        config = Config(cbSize=ctypes.sizeof(Config), dwFlags=0x18, dwCommonButtons=0x20,
                        pszWindowTitle='ESP32 Touch Dashboard', pszMainInstruction=title, pszContent=info,
                        cButtons=len(buttons), pButtons=labels, cxWidth=320)
        selected = ctypes.c_int()
        controls.TaskDialogIndirect.argtypes = [ctypes.POINTER(Config), ctypes.POINTER(ctypes.c_int), ctypes.c_void_p, ctypes.c_void_p]
        result = controls.TaskDialogIndirect(ctypes.byref(config), ctypes.byref(selected), None, None)
        if result != 0:
            raise OSError(f'TaskDialog error {result:#x}')
        return selected.value
    finally:
        if activated:
            kernel.DeactivateActCtx(0, cookie)
        kernel.ReleaseActCtx(handle)


def is_running(root):
    try:
        pid = int((root / 'agent.pid').read_text())
    except (OSError, ValueError):
        return False
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        name = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_uint(len(name))
        kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint)]
        if not kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            return False
        return Path(name.value).resolve() == (root / (APP_NAME + '.exe')).resolve()
    finally:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle(handle)


def resume(root):
    (root / 'paused').unlink(missing_ok=True)
    if not is_running(root):
        subprocess.Popen([str(root / (APP_NAME + '.exe')), '--background'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW, cwd=root)


def install(quiet=False):
    if not getattr(sys, 'frozen', False):
        raise RuntimeError('Install from the packaged EXE, not the Python source.')
    root = install_root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / (APP_NAME + '.exe')
    if Path(sys.executable).resolve() != target.resolve():
        if is_running(root):
            raise RuntimeError('已有安装正在运行。请先在任务管理器结束 ESP32TouchDashboard，再更新 EXE。')
        shutil.copy2(sys.executable, target)
    update_prices(root)
    config = root / 'config.json'
    if not config.exists():
        device = dict(vid=0x1A86, pid=0x7523)
        candidates = [p for p in serial.tools.list_ports.comports() if p.vid == device['vid'] and p.pid == device['pid']]
        if len(candidates) == 1:
            p = candidates[0]
            device.update(device=p.device, location=p.location, serial_number=p.serial_number)
        save_config(config, dict(device=device, codex_refresh=5, ai_source='codex'))
    else:
        save_config(config, load_config(config))
    (root / 'version.txt').write_text(APP_VERSION, encoding='ascii')
    autostart(True)
    # A Start-menu entry opens the lightweight control dialog.
    shortcut = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/ESP32 Touch Dashboard.lnk'
    ps = "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($args[0]); $s.TargetPath=$args[1]; $s.WorkingDirectory=$args[2]; $s.Save()"
    # No shell interpolation of paths: arguments are quoted separately by subprocess.
    command = "& { " + ps + " } '" + str(shortcut).replace("'", "''") + "' '" + str(target).replace("'", "''") + "' '" + str(root).replace("'", "''") + "'"
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                   creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    resume(root)
    if not quiet:
        message('已安装并启用登录自启。\n\n插入设备后会自动更新 PC 状态、所选来源的 Token 和人民币估算费用。\n从开始菜单打开 ESP32 Touch Dashboard 可检查 COM、安装驱动、切换 Codex / Claude Code。\n\n安装位置：' + str(root))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=APP_VERSION)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--pause', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--ai-source', choices=tuple(SOURCES), help='Select a connected device source once')
    parser.add_argument('--enable-autostart', action='store_true')
    parser.add_argument('--disable-autostart', action='store_true')
    parser.add_argument('--self-test', metavar='REPORT')
    parser.add_argument('--status', metavar='REPORT')
    args = parser.parse_args()
    root = install_root()
    if args.status:
        Path(args.status).write_text(json.dumps(startup_status(root), ensure_ascii=False, indent=2), encoding='utf-8')
        return
    if args.self_test:
        from ai_usage import AIUsage
        usage = AIUsage()
        prices = resource_root() / 'codex_prices.json'
        sources = {}
        for provider in SOURCES:
            tokens, day, cost, label = usage.sample(provider, prices)
            sources[provider] = dict(tokens=tokens, day=day, estimated_cny_fen=cost, label=label)
        report = dict(sources=sources,
                      ports=[p.device for p in serial.tools.list_ports.comports()],
                      models=sorted(set(usage.readers['codex'].by_model) | set(usage.readers['claude'].by_model)),
                      driver=driver_summary(query_ch340()), executable=sys.executable)
        Path(args.self_test).write_text(json.dumps(report, indent=2), encoding='utf-8')
        return
    if args.ai_source:
        config = load_config(root / 'config.json')
        port = matching_port(serial.tools.list_ports.comports(), config['device'])
        set_device_source(root, port, args.ai_source)
        config['ai_source'] = args.ai_source
        save_config(root / 'config.json', config)
    elif args.install:
        install(args.quiet)
    elif args.background:
        run_agent(root / 'config.json')
    elif args.pause:
        (root / 'paused').touch()
    elif args.resume:
        resume(root)
    elif args.enable_autostart or args.disable_autostart:
        autostart(args.enable_autostart)
    else:
        root.mkdir(parents=True, exist_ok=True)
        if not (root / 'config.json').exists():
            save_config(root / 'config.json', dict(device=dict(vid=0x1A86, pid=0x7523), ai_source='codex'))
        update_prices(root)
        if getattr(sys, 'frozen', False) and not (root / (APP_NAME + '.exe')).exists():
            shutil.copy2(sys.executable, root / (APP_NAME + '.exe'))
        resume(root)
        from dashboard_gui import DashboardGUI
        DashboardGUI(root, sys.modules[__name__]).run()


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        main()
    except Exception as error:
        root = install_root()
        root.mkdir(parents=True, exist_ok=True)
        (root / 'error.log').write_text(str(error), encoding='utf-8')
        if '--background' not in sys.argv and '--quiet' not in sys.argv:
            message(str(error), 16)
        raise
