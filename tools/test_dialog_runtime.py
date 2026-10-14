"""Show the native control dialog, inspect its controls, then close this test window."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import threading
import time

from desktop_dashboard import install_root, startup_status, native_command_dialog

result = {}
user = ctypes.WinDLL('user32')
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user.EnumChildWindows.argtypes = [wintypes.HWND, callback_type, wintypes.LPARAM]


def inspect_window():
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        def visit(hwnd, param):
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != os.getpid():
                return True
            caption = ctypes.create_unicode_buffer(512)
            user.GetWindowTextW(hwnd, caption, len(caption))
            if caption.value != 'ESP32 Touch Dashboard':
                return True
            texts = []
            def child(control, param):
                text = ctypes.create_unicode_buffer(1024)
                user.GetWindowTextW(control, text, len(text))
                if text.value:
                    texts.append(text.value)
                return True
            user.EnumChildWindows(hwnd, callback_type(child), 0)
            result['texts'] = texts
            user.PostMessageW(hwnd, 0x10, 0, 0)
            return False
        user.EnumWindows(callback_type(visit), 0)
        if result:
            return
        time.sleep(.2)


threading.Thread(target=inspect_window, daemon=True).start()
status = startup_status()
native_command_dialog('开机自启：' + ('已启用' if status['enabled'] else '未启用'), '监控正在运行。',
                      [(101, '启用开机自启'), (102, '关闭开机自启'), (103, '暂停监控'), (104, '恢复监控')], install_root())
result['startup_status'] = status
result['passed'] = status['enabled'] and all(any(label in text for text in result.get('texts', []))
                       for label in ['启用开机自启', '关闭开机自启', '暂停监控', '恢复监控'])
Path(__file__).resolve().parent.parent.joinpath('build/dialog_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
raise SystemExit(0 if result['passed'] else 1)
