"""Small Windows executable: per-user install, login startup, USB monitoring.

Uses native Windows dialogs; no GUI framework or administrator privileges.
"""
import argparse
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

APP_NAME = 'ESP32TouchDashboard'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
APPROVED_KEY = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'


def install_root():
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
    info += '\nWindows 登录后在后台运行，插入设备后自动连接。\nToken 和人民币估算费用约每 5 秒更新。'
    buttons = [(101, '启用开机自启\n登录后自动运行，并恢复设备监控'),
               (102, '关闭开机自启\n下次登录时不自动运行'),
               (103, '暂停监控\n释放串口，方便烧录或使用其他串口工具'),
               (104, '恢复监控\n自动等待并连接设备'),
               (105, '修改价格和汇率\n打开人民币估算费用配置'),
               (106, '查看运行日志\n查看设备连接和用量更新记录')]
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
    prices = root / 'codex_prices.json'
    if not prices.exists():
        shutil.copy2(Path(sys._MEIPASS) / 'codex_prices.json', prices)
    config = root / 'config.json'
    if not config.exists():
        device = dict(vid=0x1A86, pid=0x7523)
        candidates = [p for p in serial.tools.list_ports.comports() if p.vid == device['vid'] and p.pid == device['pid']]
        if len(candidates) == 1:
            p = candidates[0]
            device.update(device=p.device, location=p.location, serial_number=p.serial_number)
        config.write_text(json.dumps(dict(device=device, codex_refresh=5, daily_goal=0), ensure_ascii=False, indent=2), encoding='utf-8')
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
        message('已安装并启用登录自启。\n\n插入设备后会自动更新 PC、Token 和人民币估算费用。\n从开始菜单打开 ESP32 Touch Dashboard 可以暂停或恢复。\n\n安装位置：' + str(root))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--pause', action='store_true')
    parser.add_argument('--resume', action='store_true')
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
        from codex_usage import CodexUsage, estimate_cny_fen
        usage = CodexUsage()
        tokens, day = usage.read()
        prices = Path(sys._MEIPASS) / 'codex_prices.json'
        report = dict(tokens=tokens, day=day, estimated_cny_fen=estimate_cny_fen(usage.by_model, prices),
                      ports=[p.device for p in serial.tools.list_ports.comports()],
                      models=sorted(usage.by_model), executable=sys.executable)
        Path(args.self_test).write_text(json.dumps(report, indent=2), encoding='utf-8')
        return
    if args.install:
        install(args.quiet)
    elif args.background:
        run_agent(root / 'config.json')
    elif args.pause:
        (root / 'paused').touch()
    elif args.resume:
        resume(root)
    elif args.enable_autostart or args.disable_autostart:
        autostart(args.enable_autostart)
    elif not (root / 'config.json').exists():
        if message('安装 ESP32 Touch Dashboard 并启用登录自启？\n\n无需 Python 或管理员权限，插入设备后自动连接。\n价格使用你设置的单价和汇率，只显示估算金额。', 4) == 6:
            install()
    else:
        control_dialog(root)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        root = install_root()
        root.mkdir(parents=True, exist_ok=True)
        (root / 'error.log').write_text(str(error), encoding='utf-8')
        if '--background' not in sys.argv and '--quiet' not in sys.argv:
            message(str(error), 16)
        raise
