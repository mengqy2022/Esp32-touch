"""Small desktop control panel; the serial agent runs independently."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import json
import os


class DashboardGUI:
    BG, PANEL, SIDE, TEXT, DIM = '#212121', '#2f2f2f', '#171717', '#eeeeee', '#aaaaaa'

    def __init__(self, root, actions):
        self.root, self.api = Path(root), actions
        self.window = tk.Tk()
        self.window.title('ESP32 Touch Dashboard')
        self.window.geometry('1040x700')
        self.window.minsize(850, 600)
        self.window.configure(bg=self.BG)
        self.window.option_add('*Font', ('Microsoft YaHei UI', 10))
        self.events = queue.Queue()
        self.targets = []
        self.page = None
        style = ttk.Style(self.window)
        style.theme_use('clam')
        style.configure('Treeview', background=self.PANEL, fieldbackground=self.PANEL,
                        foreground=self.TEXT, rowheight=34, borderwidth=0)
        style.configure('Treeview.Heading', background=self.SIDE, foreground=self.TEXT)
        style.map('Treeview', background=[('selected', '#36594d')])
        style.configure('TCombobox', fieldbackground=self.PANEL, background=self.PANEL, foreground=self.TEXT)
        sidebar = tk.Frame(self.window, bg=self.SIDE, width=200)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self.label(sidebar, 'ESP32 Touch', 18, bg=self.SIDE).pack(anchor='w', padx=20, pady=(25, 2))
        self.label(sidebar, '设备控制中心', color=self.DIM, bg=self.SIDE).pack(anchor='w', padx=20, pady=(0, 25))
        for name in ('设备连接', 'PC SCREEN', 'AI 用量', '设置与日志'):
            self.button(sidebar, name, lambda value=name: self.show(value)).pack(fill='x', padx=12, pady=5)
        self.label(sidebar, '关闭窗口后\n后台监控继续运行', color=self.DIM, bg=self.SIDE).pack(side='bottom', padx=18, pady=24)
        self.content = tk.Frame(self.window, bg=self.BG)
        self.content.pack(side='top', fill='both', expand=True, padx=28, pady=22)
        self.status = tk.StringVar(value='准备就绪')
        self.label(self.window, '', color=self.DIM, textvariable=self.status).pack(side='bottom', anchor='w', padx=28, pady=10)
        self.show('设备连接')
        self.window.after(100, self.poll)

    def label(self, parent, text, size=10, color=None, bg=None, **kwargs):
        return tk.Label(parent, text=text, font=('Microsoft YaHei UI', size), fg=color or self.TEXT,
                        bg=bg or self.BG, justify='left', anchor='w', **kwargs)

    def button(self, parent, text, callback):
        return tk.Button(parent, text=text, command=callback, bg=self.PANEL, fg=self.TEXT,
                         activebackground='#444444', activeforeground=self.TEXT, relief='flat',
                         bd=0, padx=16, pady=10, cursor='hand2', takefocus=True)

    def work(self, action, completed=None):
        self.status.set('处理中…')
        def run():
            try:
                result = action()
                self.events.put((completed, result, None))
            except Exception as error:
                self.events.put((None, None, str(error)))
        threading.Thread(target=run, daemon=True).start()

    def poll(self):
        try:
            while True:
                callback, result, error = self.events.get_nowait()
                if error:
                    self.status.set(error)
                    messagebox.showerror('操作未完成', error, parent=self.window)
                else:
                    self.status.set('操作完成')
                    if callback:
                        callback(result)
        except queue.Empty:
            pass
        if self.page == '设备连接':
            self.refresh_status()
        self.window.after(500, self.poll)

    def config(self):
        return self.api.load_config(self.root / 'config.json')

    def save(self, config):
        self.api.save_config(self.root / 'config.json', config)

    def row(self):
        frame = tk.Frame(self.content, bg=self.BG)
        frame.pack(fill='x', pady=8)
        return frame

    def show(self, page):
        self.page = page
        for child in self.content.winfo_children():
            child.destroy()
        self.label(self.content, page, 23).pack(anchor='w', pady=(0, 15))
        if page == '设备连接':
            self.connection = self.label(self.content, '', 13)
            self.connection.pack(anchor='w', pady=12)
            row = self.row()
            self.button(row, '连接 / 恢复监控', lambda: self.work(lambda: self.api.resume(self.root))).pack(side='left', padx=(0, 10))
            self.button(row, '暂停并释放串口', lambda: (self.root / 'paused').touch()).pack(side='left')
            self.ports = list(self.api.serial.tools.list_ports.comports())
            self.port = ttk.Combobox(self.content, state='readonly', width=65,
                                    values=['自动识别 CH340'] + [f'{p.device} · {p.description}' for p in self.ports])
            self.port.current(0)
            device = self.config()['device']
            if device.get('mode') == 'manual':
                for index, port in enumerate(self.ports, 1):
                    if port.device == device.get('device'):
                        self.port.current(index)
            self.port.pack(anchor='w', pady=12)
            row = self.row()
            self.button(row, '保存端口', self.save_port).pack(side='left', padx=(0, 10))
            self.button(row, '刷新', lambda: self.show(page)).pack(side='left', padx=(0, 10))
            self.button(row, '检查连接', self.check_port).pack(side='left')
            self.button(self.content, 'CH340 驱动检查与安装', lambda: self.work(lambda: self.api.driver_dialog(self.root))).pack(anchor='w', pady=15)
            self.refresh_status()
        elif page == 'PC SCREEN':
            self.current = self.label(self.content, '当前：' + (self.config().get('screen_window') or {}).get('title', '未选择'))
            self.current.pack(anchor='w', pady=5)
            self.label(self.content, '选择窗口后，在设备 SYSTEM → PC SCREEN 查看。\n网易云显示控制页；其他窗口支持 2X 放大、拖动查看和 UP / DN 滚动。', color=self.DIM).pack(anchor='w', pady=8)
            search_row = self.row()
            self.search = tk.StringVar()
            entry = tk.Entry(search_row, textvariable=self.search, bg=self.PANEL, fg=self.TEXT,
                             insertbackground=self.TEXT, relief='flat')
            entry.pack(side='left', fill='x', expand=True, ipady=8)
            self.button(search_row, '刷新窗口', self.refresh_windows).pack(side='left', padx=(10, 0))
            table = tk.Frame(self.content, bg=self.BG)
            table.pack(fill='both', expand=True, pady=10)
            self.tree = ttk.Treeview(table, columns=('title', 'process'), show='headings', selectmode='browse')
            self.tree.heading('title', text='窗口名称')
            self.tree.heading('process', text='所属程序')
            self.tree.column('title', width=420)
            self.tree.column('process', width=170)
            scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
            scroll.pack(side='right', fill='y')
            self.tree.configure(yscrollcommand=scroll.set)
            self.tree.pack(side='left', fill='both', expand=True)
            self.tree.bind('<Double-1>', lambda _: self.select_window())
            self.search.trace_add('write', lambda *_: self.filter_windows())
            row = self.row()
            self.button(row, '共享所选窗口', self.select_window).pack(side='left', padx=(0, 10))
            self.button(row, '停止共享', self.stop_window).pack(side='left')
            self.refresh_windows()
        elif page == 'AI 用量':
            self.label(self.content, '在设备主页点选 CODEX / CLAUDE 即可切换。\n这里保留备用入口；两种来源分别统计，不合并。', 12).pack(anchor='w', pady=16)
            row = self.row()
            for source, title in (('codex', 'Codex'), ('claude', 'Claude Code')):
                self.button(row, title, lambda value=source: self.work(lambda: self.select_source(value))).pack(side='left', padx=(0, 12))
            self.button(self.content, '编辑价格和汇率', lambda: os.startfile(self.root / 'codex_prices.json')).pack(anchor='w', pady=20)
        else:
            row = self.row()
            self.button(row, '开启登录自启', lambda: self.api.autostart(True)).pack(side='left', padx=(0, 10))
            self.button(row, '关闭登录自启', lambda: self.api.autostart(False)).pack(side='left')
            self.button(self.content, '导入月薪猫工作日日历', self.import_calendar).pack(anchor='w', pady=8)
            self.label(self.content, '配置与日志：' + str(self.root), color=self.DIM, wraplength=650).pack(anchor='w', pady=12)
            self.button(self.content, '打开运行目录', lambda: os.startfile(self.root)).pack(anchor='w', pady=8)
            log = tk.Text(self.content, bg=self.PANEL, fg=self.TEXT, relief='flat', wrap='word', height=16)
            log.pack(fill='both', expand=True, pady=12)
            path = self.root / 'host.log'
            if path.exists():
                with path.open('rb') as stream:
                    stream.seek(max(0, path.stat().st_size - 12000))
                    log.insert('1.0', stream.read().decode('utf-8', 'replace'))
            log.configure(state='disabled')

    def refresh_status(self):
        try:
            state = json.loads((self.root / 'connection.json').read_text(encoding='utf-8'))
            import time
            active = time.time() - state.get('updated', 0) < 8 and state.get('worker')
            text = '监控已暂停' if (self.root / 'paused').exists() else '后台运行中' if active else '等待连接 / 后台未运行'
            self.connection.configure(text=f'{text}    {state.get("port") or "未连接设备"}\n\n当前共享：' + (self.config().get('screen_window') or {}).get('title', '未选择'))
        except (OSError, ValueError):
            self.connection.configure(text='等待连接设备')

    def save_port(self):
        config = self.config()
        index = self.port.current()
        config['device'] = self.api.selected_device(self.ports[index - 1]) if index > 0 else dict(vid=0x1A86, pid=0x7523, mode='auto')
        self.save(config)
        self.status.set('端口已保存')

    def check_port(self):
        config = self.config()
        port = self.api.matching_port(self.api.serial.tools.list_ports.comports(), config['device'])
        self.work(lambda: self.api.check_connection(self.root, port))

    def refresh_windows(self):
        self.work(lambda: self.api.Window().list(), self.loaded_windows)

    def loaded_windows(self, targets):
        self.targets = targets
        if self.page == 'PC SCREEN':
            self.filter_windows()

    def filter_windows(self):
        self.tree.delete(*self.tree.get_children())
        term = self.search.get().casefold()
        for index, target in enumerate(self.targets):
            if term in (target['title'] + ' ' + target.get('process', '')).casefold():
                self.tree.insert('', 'end', iid=str(index), values=(target['title'], target.get('process', '未知程序')))

    def select_window(self):
        selected = self.tree.selection()
        if not selected:
            self.status.set('请先选择一个窗口')
            return
        target = self.targets[int(selected[0])]
        def select():
            config = self.config()
            config['screen_window'] = self.api.Window().select(target)
            self.save(config)
            return target['title']
        self.work(select, lambda title: self.window_selected(title))

    def window_selected(self, title):
        self.status.set('已保存选择：' + title + '；数秒内生效')
        if self.page == 'PC SCREEN':
            self.current.configure(text='当前：' + title)

    def stop_window(self):
        config = self.config()
        config.pop('screen_window', None)
        self.save(config)
        self.window_selected('未选择')

    def select_source(self, source):
        config = self.config()
        port = self.api.matching_port(self.api.serial.tools.list_ports.comports(), config['device'])
        self.api.set_device_source(self.root, port, source)
        config['ai_source'] = source
        self.save(config)

    def import_calendar(self):
        path = filedialog.askopenfilename(parent=self.window, title='导入工作日日历', filetypes=[('JSON 日历', '*.json')])
        if not path:
            return
        def save():
            from work_calendar import load_calendar
            data = load_calendar(path)
            target = self.root / 'work_calendar.json'
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)
            return data['year']
        self.work(save, lambda year: self.status.set(f'已导入 {year} 年工作日日历；当前年份匹配时约60秒内同步，工资和班次请在设备设置'))

    def run(self):
        self.window.mainloop()
