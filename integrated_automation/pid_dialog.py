"""Grouped board readback and one-at-a-time edits; never write on +/- clicks."""
import tkinter as tk
from tkinter import messagebox, ttk

from pid_settings import PARAMETERS, DIVISORS, encode_value


class PidDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title('PID／PLL 板端參數')
        self.transient(app.root)
        self.values = {}
        self.transaction = app.worker.pid
        self._syncing = False
        self._revision = -1
        self.readouts, self.drafts, self.notes = {}, {}, {}
        self.editors, self.steps, self.writes = {}, {}, {}
        self._styles()
        panel = ttk.Frame(self, padding=16)
        panel.pack(fill='both', expand=True)
        top = ttk.Frame(panel)
        top.pack(fill='x', pady=(0, 10))
        ttk.Label(top, text='PID / PLL', style='Pid.Title.TLabel').pack(side='left')
        self.read_button = ttk.Button(top, text='讀取板端', command=self.read,
                                      style='Pid.Action.TButton')
        self.read_button.pack(side='right')
        self.connection = tk.StringVar(self, '尚未讀取')
        ttk.Label(panel, textvariable=self.connection, style='Pid.Muted.TLabel').pack(anchor='w', pady=(0, 10))
        notebook = ttk.Notebook(panel, style='Pid.TNotebook')
        notebook.pack(fill='both', expand=True)
        currents = ttk.Frame(notebook, padding=(4, 12))
        observer = ttk.Frame(notebook, padding=(4, 12))
        notebook.add(currents, text='Currents / Speed')
        notebook.add(observer, text='Observer / PLL')
        self.notebook = notebook
        self._group(currents, 'Speed PI regulator', (
            ('speed_kp', 'Kp'), ('speed_ki', 'Ki'),
            ('speed_kp_div', 'Kp divisor'), ('speed_ki_div', 'Ki divisor')))
        self._group(currents, 'Torque (Iq) PI regulator', (('iq_kp', 'Kp'), ('iq_ki', 'Ki')))
        readonly = ttk.Frame(currents, padding=(12, 2))
        readonly.pack(fill='x', pady=(0, 8))
        ttk.Label(readonly, text='Torque Reference', style='Pid.Muted.TLabel').pack(side='left')
        self.readouts['iq_reference_raw'] = tk.StringVar(self, '—')
        ttk.Label(readonly, textvariable=self.readouts['iq_reference_raw'],
                  style='Pid.Value.TLabel').pack(side='left', padx=12)
        ttk.Label(readonly, text='raw · 唯讀', style='Pid.Muted.TLabel').pack(side='left')
        self._group(currents, 'Flux (Id) PI regulator', (('id_kp', 'Kp'), ('id_ki', 'Ki')))
        self._group(observer, 'State Observer with PLL', (
            ('observer_c1', 'C1'), ('observer_c2', 'C2'),
            ('pll_kp', 'PLL Kp'), ('pll_ki', 'PLL Ki')))
        ttk.Label(observer, text='C1 / C2 保留正負號；所有數值以板端讀回為準。',
                  style='Pid.Muted.TLabel').pack(anchor='w', padx=12)
        ttk.Separator(panel).pack(fill='x', pady=(10, 8))
        self.status = tk.StringVar(self, '請先讀取板端；＋／− 只修改輸入值，不會立即寫入。')
        ttk.Label(panel, textvariable=self.status, wraplength=650,
                  style='Pid.Status.TLabel').pack(anchor='w')
        ttk.Label(panel, text='單項寫入並讀回驗證。條件：實機連線、無故障 IDLE、0 rpm、未記錄。',
                  wraplength=650, style='Pid.Muted.TLabel').pack(anchor='w', pady=(6, 0))
        self.result()

    @property
    def pending(self):
        return self.transaction.view()['pending']

    def _styles(self):
        # Namespaced styles leave the main application theme unchanged.
        style = ttk.Style(self)
        style.configure('Pid.Title.TLabel', font=('Microsoft JhengHei UI', 16, 'bold'))
        style.configure('Pid.Value.TLabel', font=('Consolas', 12), foreground='#24374b')
        style.configure('Pid.Muted.TLabel', foreground='#687b8c')
        style.configure('Pid.Status.TLabel', foreground='#17698d')
        # Use one fixed-size surface for both states: no raised inactive border.
        # Images live on the root so closing/reopening a dialog keeps the style valid.
        root = self.app.root
        if not hasattr(root, '_pid_tab_images'):
            inactive = tk.PhotoImage(master=root, width=8, height=8)
            inactive.put('#eef1f4', to=(0, 0, 8, 8))
            selected = tk.PhotoImage(master=root, width=8, height=8)
            selected.put('#ffffff', to=(0, 0, 8, 8))
            selected.put('#17698d', to=(0, 6, 8, 8))
            root._pid_tab_images = (inactive, selected)
            style.element_create('Pid.Tab.surface', 'image', inactive,
                                 ('selected', selected), border=(0, 0, 0, 2), sticky='nswe')
        style.layout('Pid.TNotebook.Tab', [
            ('Pid.Tab.surface', {'sticky': 'nswe', 'children': [
                ('Notebook.padding', {'sticky': 'nswe', 'children': [
                    ('Notebook.label', {'sticky': ''})]})]})])
        style.configure('Pid.TNotebook', background='#ffffff', borderwidth=0)
        style.configure('Pid.TNotebook.Tab', padding=(24, 9),
                        font=('Microsoft JhengHei UI', 10), foreground='#687b8c')
        style.map('Pid.TNotebook.Tab',
                  foreground=[('selected', '#24374b'), ('!selected', '#687b8c')],
                  font=[('selected', ('Microsoft JhengHei UI', 10, 'bold')),
                        ('!selected', ('Microsoft JhengHei UI', 10))])
        style.configure('Pid.Action.TButton', padding=(10, 5), foreground='#17698d')
        style.configure('Pid.Step.TButton', padding=(5, 3), foreground='#17698d')

    def _group(self, parent, title, fields):
        group = ttk.LabelFrame(parent, text=title, padding=(12, 8))
        group.pack(fill='x', pady=(0, 10))
        for col, title in enumerate(('參數', '板端讀值', '待寫入值', '操作', '狀態')):
            ttk.Label(group, text=title, style='Pid.Muted.TLabel').grid(row=0, column=col, sticky='w', padx=(0, 12), pady=(0, 4))
        group.columnconfigure(2, weight=1)
        for row, (key, label) in enumerate(fields, 1):
            ttk.Label(group, text=label, width=12).grid(row=row, column=0, sticky='w')
            self.readouts[key] = tk.StringVar(self, '—')
            ttk.Label(group, textvariable=self.readouts[key], width=9,
                      style='Pid.Value.TLabel', anchor='e').grid(row=row, column=1, padx=(0, 16))
            self.drafts[key] = tk.StringVar(self, '')
            box = ttk.Frame(group)
            box.grid(row=row, column=2, sticky='w', padx=(0, 12), pady=3)
            if key.endswith('_div'):
                editor = ttk.Combobox(box, textvariable=self.drafts[key], values=DIVISORS,
                                      width=12, state='disabled', font=('Consolas', 12))
                editor.pack()
            else:
                minus = ttk.Button(box, text='−', width=2, style='Pid.Step.TButton', command=lambda k=key: self.step(k, -1))
                minus.pack(side='left')
                editor = ttk.Entry(box, textvariable=self.drafts[key], width=9, justify='right', font=('Consolas', 12))
                editor.pack(side='left', padx=3)
                plus = ttk.Button(box, text='+', width=2, style='Pid.Step.TButton', command=lambda k=key: self.step(k, 1))
                plus.pack(side='left')
                self.steps[key] = (minus, plus)
            self.editors[key] = editor
            self.writes[key] = ttk.Button(group, text='寫入', style='Pid.Action.TButton', command=lambda k=key: self.write(k))
            self.writes[key].grid(row=row, column=3, padx=(0, 12))
            self.notes[key] = tk.StringVar(self, '未讀取')
            ttk.Label(group, textvariable=self.notes[key], width=9, style='Pid.Status.TLabel').grid(row=row, column=4, sticky='w')
            self.drafts[key].trace_add('write', lambda *_, k=key: self._draft_changed(k))

    def available(self):
        app = self.app
        state = self.transaction.view()
        application_busy = app.busy or app.pending_begin
        transaction_busy = state['pending'] or state['blocked'] or state['experiment']
        return (
            app.connected and not app.sim.get()
            and not application_busy and not transaction_busy
            and not app.worker.stop_event.is_set()
        )

    def _draft_changed(self, key):
        if not self._syncing:self.transaction.edit(key, self.drafts[key].get())
        if key not in self.values:
            note = '未讀取'
        else:
            try:
                value = int(self.drafts[key].get())
                encode_value(key, value)
                note = '已修改' if value != self.values[key] else '未修改'
            except ValueError:
                note = '輸入無效'
        draft_note = note
        note = self.transaction.view()['rows'].get(key, note)
        self.notes[key].set(note)
        enabled = self.available() and self.app.motor_stopped and draft_note == '已修改'
        self.writes[key].configure(state='normal' if enabled else 'disabled')

    def refresh(self):
        if self._revision != self.transaction.view()['revision']:
            self.result()
            return
        self.status.set(self.transaction.view()['status'])
        available = self.available()
        self.read_button.configure(state='normal' if available else 'disabled')
        self.connection.set('未連線／模擬模式' if not self.app.connected or self.app.sim.get()
                            else '交易進行中…' if self.pending else
                            '已有板端讀值 · 寫入仍須符合停機條件' if self.values else '尚未讀取板端')
        for key, editor in self.editors.items():
            enabled = available and key in self.values
            editor.configure(state=('readonly' if key.endswith('_div') else 'normal') if enabled else 'disabled')
            for button in self.steps.get(key, ()):
                button.configure(state='normal' if enabled else 'disabled')
            self._draft_changed(key)

    def operation_hint(self, text):
        self.transaction.operation_hint(text)
        self.status.set(self.transaction.view()['status'])

    def step(self, key, delta):
        if not self.available() or key not in self.values:
            return
        try:
            value = int(self.drafts[key].get()) + delta
            encode_value(key, value)
        except ValueError as error:
            self.operation_hint(str(error))
            return
        self.drafts[key].set(str(value))

    def read(self):
        if self.available():
            try:
                self.app.worker.request_pid()
            except ValueError as error:
                self.operation_hint(str(error))
            self.refresh()

    def write(self, key):
        if not self.available() or not self.app.motor_stopped or key not in self.values:
            self.operation_hint('請先讀取板端，並確認符合停機寫入條件。')
            return
        try:
            value = int(self.drafts[key].get())
            encode_value(key, value)
        except ValueError as error:
            self.operation_hint(str(error))
            return
        self.transaction.clear_hint()
        expected = self.values[key]
        generation = self.transaction.generation
        if value == expected:
            self.transaction.clear_hint()
            self.operation_hint('數值與板端相同。')
            return
        if not messagebox.askokcancel('確認寫入', f'{PARAMETERS[key][1]}：{expected} → {value}\n確認馬達已停穩。', parent=self):
            return
        if not self.available() or not self.app.motor_stopped or self.values.get(key) != expected or self.transaction.generation != generation:
            self.operation_hint('狀態或板端快照已變更，請重新確認。')
            return
        try:
            self.app.worker.request_pid((key, expected, value))
        except ValueError as error:
            self.operation_hint(str(error))
        self.refresh()

    def result(self):
        view = self.transaction.view()
        self._revision = view['revision']
        self.values = view['values']
        self._syncing = True
        try:
            for key, var in self.readouts.items():
                var.set(str(self.values.get(key, '—')))
            for key, draft in self.drafts.items():
                draft.set(view['drafts'].get(key, ''))
        finally:self._syncing = False
        self.status.set(view['status'])
        self.refresh()
