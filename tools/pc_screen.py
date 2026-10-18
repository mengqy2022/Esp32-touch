"""One selected Win32 client window, over the existing serial connection."""
import ctypes
from ctypes import wintypes as w
import secrets
import sys
import time

WIDTH, HEIGHT = 160, 88
PROPERTY = 'ESP32TouchDashboard.SelectedWindow'


def encode_frame(bgra):
    if len(bgra) != WIDTH * HEIGHT * 4:
        raise ValueError('Invalid bitmap size')
    pixels = bytes((bgra[i + 2] & 224) | ((bgra[i + 1] >> 3) & 28) | (bgra[i] >> 6)
                   for i in range(0, len(bgra), 4))
    result = bytearray()
    last, count = pixels[0], 0
    for pixel in pixels:
        if pixel != last or count == 255:
            result.extend((count, last))
            last, count = pixel, 0
        count += 1
    result.extend((count, last))
    return bytes(result)


def checksum(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


def viewport(width, height):
    if not 0 < width <= 16384 or not 0 < height <= 16384:
        raise ValueError('Window size unavailable')
    scale = min(WIDTH / width, HEIGHT / height)
    dw, dh = max(1, int(width * scale)), max(1, int(height * scale))
    return (WIDTH - dw) // 2, (HEIGHT - dh) // 2, dw, dh


def map_point(x, y, size):
    left, top, width, height = viewport(*size)
    if not left <= x < left + width or not top <= y < top + height:
        raise ValueError('Touch outside window')
    return min(size[0] - 1, (x - left) * size[0] // width), min(size[1] - 1, (y - top) * size[1] // height)


class Window:
    def __init__(self):
        if sys.platform != 'win32':
            raise OSError('Window sharing requires Windows')
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.g = ctypes.WinDLL('gdi32', use_last_error=True)
        self.last_size = None
        signatures = [
            (self.u, 'GetDC', w.HDC, [w.HWND]),
            (self.u, 'ReleaseDC', ctypes.c_int, [w.HWND, w.HDC]),
            (self.u, 'GetPropW', w.HANDLE, [w.HWND, w.LPCWSTR]),
            (self.u, 'SetPropW', w.BOOL, [w.HWND, w.LPCWSTR, w.HANDLE]),
            (self.u, 'GetWindowThreadProcessId', w.DWORD, [w.HWND, ctypes.POINTER(w.DWORD)]),
            (self.u, 'GetClientRect', w.BOOL, [w.HWND, ctypes.POINTER(w.RECT)]),
            (self.u, 'IsWindowVisible', w.BOOL, [w.HWND]),
            (self.u, 'IsWindow', w.BOOL, [w.HWND]),
            (self.u, 'IsIconic', w.BOOL, [w.HWND]),
            (self.u, 'SendMessageTimeoutW', ctypes.c_ssize_t,
             [w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT, ctypes.POINTER(ctypes.c_size_t)]),
            (self.u, 'PostMessageW', w.BOOL, [w.HWND, w.UINT, w.WPARAM, w.LPARAM]),
            (self.u, 'ChildWindowFromPointEx', w.HWND, [w.HWND, w.POINT, w.UINT]),
            (self.u, 'MapWindowPoints', ctypes.c_int, [w.HWND, w.HWND, ctypes.POINTER(w.POINT), w.UINT]),
            (self.g, 'CreateCompatibleDC', w.HDC, [w.HDC]),
            (self.g, 'CreateCompatibleBitmap', w.HBITMAP, [w.HDC, ctypes.c_int, ctypes.c_int]),
            (self.g, 'SelectObject', w.HANDLE, [w.HDC, w.HANDLE]),
            (self.g, 'DeleteObject', w.BOOL, [w.HANDLE]),
            (self.g, 'DeleteDC', w.BOOL, [w.HDC]),
            (self.g, 'PatBlt', w.BOOL, [w.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.DWORD]),
            (self.g, 'StretchBlt', w.BOOL, [w.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        w.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.DWORD]),
            (self.g, 'GetDIBits', ctypes.c_int, [w.HDC, w.HBITMAP, w.UINT, w.UINT, ctypes.c_void_p, ctypes.c_void_p, w.UINT]),
        ]
        for dll, name, result, args in signatures:
            function = getattr(dll, name)
            function.restype, function.argtypes = result, args

    def list(self):
        result = []
        callback = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        self.u.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
        @callback
        def visit(hwnd, _):
            title = ctypes.create_unicode_buffer(512)
            self.u.GetWindowTextW(hwnd, title, len(title))
            if title.value and self.u.IsWindowVisible(hwnd):
                pid = w.DWORD()
                self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value != __import__('os').getpid():
                    result.append(dict(hwnd=hwnd, pid=pid.value, title=title.value))
            return True
        self.u.EnumWindows.argtypes = [callback, w.LPARAM]
        self.u.EnumWindows(visit, 0)
        return result

    def select(self, target):
        pid = w.DWORD()
        self.u.GetWindowThreadProcessId(target['hwnd'], ctypes.byref(pid))
        if pid.value != target['pid']:
            raise OSError('Window closed; refresh the list')
        cookie = secrets.randbelow(0x7ffffffe) + 1
        if not self.u.SetPropW(target['hwnd'], PROPERTY, cookie):
            raise OSError('Cannot select this window (check application privileges)')
        return dict(target, cookie=cookie)

    def valid(self, target):
        pid = w.DWORD()
        self.u.GetWindowThreadProcessId(target['hwnd'], ctypes.byref(pid))
        return (bool(self.u.IsWindow(target['hwnd'])) and pid.value == target['pid'] and
                self.u.GetPropW(target['hwnd'], PROPERTY) == target['cookie'])

    def size(self, target):
        if not self.valid(target):
            raise OSError('Selected window closed; select it again')
        rect = w.RECT()
        if not self.u.GetClientRect(target['hwnd'], ctypes.byref(rect)):
            raise OSError('Cannot read window size')
        size = rect.right, rect.bottom
        identity = target['hwnd'], target['cookie']
        if self.u.IsIconic(target['hwnd']) and not all(size):
            if self.last_size and self.last_size[0] == identity:
                return self.last_size[1]
            raise ValueError('Restore window once before minimizing it')
        viewport(*size)
        self.last_size = identity, size
        return size

    def capture(self, target):
        width, height = size = self.size(target)
        # Bound GDI allocation even for huge or malicious window dimensions.
        if width * height > 16_000_000:
            raise OSError('Window too large; resize it')
        screen = self.u.GetDC(None)
        source = self.g.CreateCompatibleDC(screen)
        output = self.g.CreateCompatibleDC(screen)
        bitmap = self.g.CreateCompatibleBitmap(screen, width, height)
        small = self.g.CreateCompatibleBitmap(screen, WIDTH, HEIGHT)
        if not all((screen, source, output, bitmap, small)):
            for handle in (bitmap, small):
                if handle: self.g.DeleteObject(handle)
            for dc in (source, output):
                if dc: self.g.DeleteDC(dc)
            if screen: self.u.ReleaseDC(None, screen)
            raise OSError('Cannot allocate window bitmap')
        old = self.g.SelectObject(source, bitmap)
        old_small = self.g.SelectObject(output, small)
        try:
            self.g.PatBlt(source, 0, 0, width, height, 0x00000042)
            answer = ctypes.c_size_t()
            # shortcut: WM_PRINTCLIENT depends on the app; use Windows Graphics Capture if broader support is needed.
            if not self.u.SendMessageTimeoutW(target['hwnd'], 0x317, source, 4 | 8 | 16,
                                              2 | 0x20, 350, ctypes.byref(answer)):
                raise OSError('Window not responding to capture')
            self.g.PatBlt(output, 0, 0, WIDTH, HEIGHT, 0x00000042)
            left, top, dw, dh = viewport(width, height)
            if not self.g.StretchBlt(output, left, top, dw, dh, source, 0, 0, width, height, 0x00cc0020):
                raise OSError('Cannot scale window bitmap')
            self.g.SelectObject(output, old_small)
            header = ctypes.create_string_buffer(__import__('struct').pack('<IiiHHIIiiII', 40, WIDTH, -HEIGHT, 1, 32, 0, WIDTH * HEIGHT * 4, 0, 0, 0, 0))
            bits = ctypes.create_string_buffer(WIDTH * HEIGHT * 4)
            if self.g.GetDIBits(output, small, 0, HEIGHT, bits, header, 0) != HEIGHT:
                raise OSError('Cannot read window bitmap')
            return encode_frame(bits.raw), size
        finally:
            self.g.SelectObject(source, old)
            self.g.SelectObject(output, old_small)
            self.g.DeleteObject(bitmap)
            self.g.DeleteObject(small)
            self.g.DeleteDC(source)
            self.g.DeleteDC(output)
            self.u.ReleaseDC(None, screen)

    def gesture(self, target, size, x1, y1, x2, y2, wheel):
        if self.size(target) != size:
            raise ValueError('Window resized; wait for the next frame')
        start, end = map_point(x1, y1, size), map_point(x2, y2, size)
        hwnd = target['hwnd']
        point = w.POINT(*start)
        for _ in range(16):
            child = self.u.ChildWindowFromPointEx(hwnd, point, 1 | 2 | 4)
            if not child or child == hwnd: break
            self.u.MapWindowPoints(hwnd, child, ctypes.byref(point), 1)
            hwnd = child
        finish = w.POINT(*end)
        self.u.MapWindowPoints(target['hwnd'], hwnd, ctypes.byref(finish), 1)
        def post(message, flags, x, y):
            if not self.valid(target) or not self.u.PostMessageW(hwnd, message, flags, (x & 65535) | ((y & 65535) << 16)):
                raise OSError('Window rejected pointer input')
        if wheel:
            self.u.MapWindowPoints(hwnd, None, ctypes.byref(point), 1)
            post(0x20a, ((wheel * 120) & 65535) << 16, point.x, point.y)
            return
        post(0x200, 0, point.x, point.y)
        post(0x201, 1, point.x, point.y)
        try:
            for step in range(1, 9):
                post(0x200, 1, point.x + (finish.x - point.x) * step // 8,
                     point.y + (finish.y - point.y) * step // 8)
                time.sleep(.01)
        finally:
            post(0x202, 0, finish.x, finish.y)


class Mirror:
    """Runs on the telemetry thread; never opens another serial connection."""
    def __init__(self, target=None, windows=None):
        self.target = target
        self.windows = windows or (Window() if target else None)
        self.buffer = b''
        self.session = self.frame = 0
        self.shown = None

    def read(self, ser):
        self.buffer += ser.read(ser.in_waiting) if ser.in_waiting else b''
        lines = []
        while b'\n' in self.buffer:
            raw, self.buffer = self.buffer.split(b'\n', 1)
            line = raw.decode('utf-8', 'replace').strip()
            lines.append(line)
            if not line.startswith('SCREEN:'): continue
            fields = line.split('|')
            try:
                if fields[0] == 'SCREEN:STATE' and len(fields) in (2, 3):
                    session = int(fields[1])
                    if session != self.session:
                        self.shown = None
                    self.session = session
                elif fields[0] == 'SCREEN:INPUT' and len(fields) == 8:
                    session, frame, x1, y1, x2, y2, wheel = map(int, fields[1:])
                    if (self.shown and (session, frame) == self.shown[:2] and
                            time.monotonic() - self.shown[3] < 8 and wheel in (-1, 0, 1)):
                        self.windows.gesture(self.target, self.shown[2], x1, y1, x2, y2, wheel)
            except (OSError, ValueError) as error:
                print('SCREEN| ' + str(error), flush=True)
        self.buffer = self.buffer[-4096:]
        return lines

    def wait(self, ser, expected, timeout, stop_event):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not (stop_event and stop_event.is_set()):
            for line in self.read(ser):
                if line == expected: return True
                if line.startswith('SCREEN:ERR'): return False
            time.sleep(.01)
        return False

    def tick(self, ser, stop_event=None):
        self.read(ser)
        ser.write(b'SCREEN:?\n')
        # STATE is delivered on the next loop; firmware refreshes it on every query.
        if not self.session: return
        if not self.target:
            ser.write(b'SCREEN:STATUS|Select a window in the PC dashboard\n')
            return
        try:
            payload, size = self.windows.capture(self.target)
        except (OSError, ValueError) as error:
            self.shown = None
            print('SCREEN| ' + str(error), flush=True)
            ser.write(b'SCREEN:STATUS|Window unavailable; select again or restore it\n')
            return
        self.frame = self.frame % 0xffffffff + 1
        session = self.session
        ser.write(f'SCREEN:FRAME|{session}|{self.frame}|{len(payload)}|{checksum(payload)}\n'.encode('ascii'))
        if not self.wait(ser, 'SCREEN:READY', 1, stop_event): return
        # Once READY arrives, finish the binary frame even if stopping to leave UART aligned.
        ser.write(payload)
        if self.wait(ser, 'SCREEN:OK', 6, None):
            self.shown = session, self.frame, size, time.monotonic()
        else:
            self.shown = None
