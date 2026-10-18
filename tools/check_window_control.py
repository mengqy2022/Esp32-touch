"""Manual Windows integration check; creates and closes only its own test window."""
import ctypes
from ctypes import wintypes as w
import json
import threading
import time
from unittest.mock import patch

from pc_screen import Window, WIDTH, HEIGHT, map_point


def main():
    api = Window()
    u, g = api.u, api.g
    events, state = [], {}
    ready = threading.Event()
    u.CreateWindowExW.restype = w.HWND
    u.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p]
    u.DefWindowProcW.restype = ctypes.c_ssize_t
    u.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    u.DestroyWindow.argtypes = [w.HWND]
    u.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
    g.CreateSolidBrush.restype = w.HBRUSH
    u.FillRect.argtypes = [w.HDC, ctypes.POINTER(w.RECT), w.HBRUSH]
    callback = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    @callback
    def procedure(hwnd, message, wp, lp):
        if message in (0x317, 0x318):
            brush = g.CreateSolidBrush(0x0000ff if not events else 0x00ff00)
            rect = w.RECT(0, 0, 320, 176)
            u.FillRect(wp, ctypes.byref(rect), brush)
            g.DeleteObject(brush)
            return 0
        if message in (0x201, 0x202, 0x20a):
            events.append((message, wp, lp))
            return 0
        if message == 0x10:
            u.DestroyWindow(hwnd)
            return 0
        if message == 2:
            u.PostQuitMessage(0)
            return 0
        return u.DefWindowProcW(hwnd, message, wp, lp)
    class Class(ctypes.Structure):
        _fields_ = [('style', w.UINT), ('procedure', callback), ('class_extra', ctypes.c_int),
                    ('window_extra', ctypes.c_int), ('instance', w.HINSTANCE), ('icon', w.HICON),
                    ('cursor', w.HANDLE), ('brush', w.HBRUSH), ('menu', w.LPCWSTR), ('name', w.LPCWSTR)]
    def thread_main():
        definition = Class(procedure=procedure, name='ESP32DashboardControlTest')
        u.RegisterClassW(ctypes.byref(definition))
        state['hwnd'] = u.CreateWindowExW(0, definition.name, 'ESP32 touch control verification',
                                         0x00cf0000, 50, 50, 336, 215, None, None, None, None)
        u.ShowWindow(state['hwnd'], 5)
        ready.set()
        msg = w.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))
    thread = threading.Thread(target=thread_main, daemon=True)
    thread.start()
    assert ready.wait(3) and state['hwnd'], 'Could not create test window'
    hwnd = state['hwnd']
    pid = w.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    target = api.select(dict(hwnd=hwnd, pid=pid.value, title='Test window'))
    report = {}
    try:
        for minimized in (False, True):
            u.ShowWindow(hwnd, 6 if minimized else 9)
            time.sleep(.2)
            events.clear()
            # This test window paints via WM_PRINT; exercise that explicit fallback.
            with patch.object(api.u, 'PrintWindow', return_value=0):
                before, size = api.capture(target)
            assert any(before[1::2]), 'Unexpected black frame'
            api.gesture(target, size, 80, 40, 200, 120, 0)
            api.gesture(target, size, 160, 88, 160, 88, 1)
            time.sleep(.1)
            with patch.object(api.u, 'PrintWindow', return_value=0):
                after, _ = api.capture(target)
            assert before != after, 'Click did not change rendered content'
            assert [e[0] for e in events] == [0x201, 0x202, 0x20a], events
            report['minimized' if minimized else 'visible'] = dict(capture=True, click=True, drag=True,
                                                                  scroll=True, bytes=len(after), size=size)
        print(json.dumps(report, indent=2))
    finally:
        u.PostMessageW(hwnd, 0x10, 0, 0)
        thread.join(3)
    assert not api.valid(target), 'Closed window identity accepted'
    print('Closed window identity rejected: PASS')


if __name__ == '__main__': main()
