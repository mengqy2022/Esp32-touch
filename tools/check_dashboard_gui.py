"""GUI smoke check with isolated configuration; never controls the real device."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock
import desktop_dashboard as desktop
from dashboard_gui import DashboardGUI


def main():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        desktop.save_config(root / 'config.json', dict(device=dict(vid=0x1A86, pid=0x7523)))
        api = SimpleNamespace(**{name: getattr(desktop, name) for name in
                               ('load_config', 'save_config', 'serial', 'matching_port', 'selected_device')})
        api.Window = Mock()
        target = dict(hwnd=123, pid=456, cookie=789, title='网易云音乐', process='cloudmusic.exe')
        api.Window.return_value.list.return_value = [target]
        api.Window.return_value.select.return_value = target
        gui = DashboardGUI(root, api)
        try:
            for page in ('PC SCREEN', 'AI 用量', '设置与日志', '设备连接', 'PC SCREEN'):
                gui.show(page)
                gui.window.update()
            gui.loaded_windows([target])
            gui.search.set('cloudmusic')
            assert len(gui.tree.get_children()) == 1
            gui.search.set('missing')
            assert not gui.tree.get_children()
            gui.search.set('网易云')
            gui.tree.selection_set('0')
            gui.select_window()
            import time
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                gui.window.update()
                if desktop.load_config(root / 'config.json').get('screen_window'):
                    break
                time.sleep(.02)
            assert desktop.load_config(root / 'config.json')['screen_window'] == target
            gui.stop_window()
            assert 'screen_window' not in desktop.load_config(root / 'config.json')
            print('GUI navigation, window search, selection and stop: PASS')
        finally:
            gui.window.destroy()


if __name__ == '__main__':
    main()
