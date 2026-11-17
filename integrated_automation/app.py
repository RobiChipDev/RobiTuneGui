"""Compact experiment monitor. Only the controller owns device lifecycles."""
import json,os,queue,subprocess,sys,time,threading,traceback,webbrowser
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from config import defaults, workspace_root
from calibration import calibration_scale
from dashboard import Dashboard
from pid_dialog import PidDialog
from theme import apply_theme
from session_files import latest_session_folder, clean_filename
from propellers import MOUNTS, ROTATIONS, direction_factors, load_catalog, profile, run_label, save_catalog, sorted_catalog
from ui_widgets import RoundPanel,PillButton
from controller import Controller,validate_plan
from plan_preview import PlanPreview,run_notice

EXPERIMENT_GROUP = ('實驗',[('run_name','實驗名稱'),('speeds','轉速清單 rpm'),('max_rpm','本次最高轉速'),('ramp_ms','變速時間 ms'),('dwell_s','各組停留 s'),('baseline_s','啟動前基線 s'),('poststop_s','停機後記錄 s'),('reach_timeout_s','到速等待上限 s'),('folder','工作資料夾'),('mount','安裝方向')])
DEVICE_GROUPS = [
 ('馬達／力規',[('port','馬達 COM'),('force_enabled','啟用力規'),('force_port','力規 COM'),('force_baud','力規鮑率'),('force_addr','站號'),('force_parity','校驗 N/E/O'),('force_stopbits','停止位元 1/2'),('force_order','字序 HH-LL/LL-HH'),('force_interval','力規擷取間隔 s')]),
 ('PID 紀錄',[('speed_kp','Speed Kp（Motor Pilot 手動抄錄）'),('speed_ki','Speed Ki（Motor Pilot 手動抄錄）'),('speed_kd','Speed Kd（Motor Pilot 手動抄錄）')]),
 ('電供',[('psu_enabled','啟用電供擷取'),('psu_backend','SERIAL/VISA'),('psu_resource','COM 或 VISA 資源'),('psu_baud','鮑率'),('psu_channels','額外讀取電供 CH2（CH1 固定讀取）'),('psu_interval','擷取間隔 s')]),
 ('力規 CH1',[('scale1','倍率（預設 0.01）'),('zero1','原始零點'),('unit1','單位 N/gf/kgf/Nm/Nmm/kgfcm')]),
 ('力規 CH2',[('scale2','倍率（預設 0.001）'),('zero2','原始零點'),('unit2','單位 N/gf/kgf/Nm/Nmm/kgfcm')]),
 ('力規通道對應',[('thrust_channel','推力通道 0未指定/1/2'),('torque_channel','扭矩通道 0未指定/1/2')]),
]
EXPERIMENT_KEYS = {key for key,_ in EXPERIMENT_GROUP[1]}
DEVICE_KEYS = {key for _,fields in DEVICE_GROUPS for key,_ in fields}

class App:
 def __init__(self,root):
  self.root=root;self.worker=Controller();self.connected=False;self.connecting=False;self.busy=False;self.pending_begin=False;self.pending_tare=False;self.motor_stopped=False
  self.cfg=defaults();self.values={};self.force_state='stopped';self.last_callback_error=None;self.history=[];self.dialogs=[];self.latest_output_dir=None;self.report_state='';self.last_notice=None;self.last_notice_key=None
  root.title('Robi v0.3.29 · 實驗監看');root.geometry('1180x790');root.minsize(1040,700)
  style=apply_theme(root)
  outer=ttk.Frame(root,padding=(14,10));self.outer=outer;outer.pack(fill='both',expand=True)
  heading=ttk.Frame(outer);heading.pack(fill='x',pady=(0,8))
  ttk.Label(heading,text='Robi',font=('Segoe UI',20,'bold'),foreground='#17212f').pack(side='left')
  ttk.Label(heading,text='  馬達實驗工作台  /  v0.3.29',foreground='#788392').pack(side='left')
  self.sim=tk.BooleanVar(value=True)
  self.simbtn=PillButton(heading,text='實機鎖定（僅模擬）',command=self.toggle_mode,role='mode_locked',width=230,height=40);self.simbtn.pack(side='right')
  workspace=ttk.Frame(outer);workspace.pack(fill='both',expand=True)
  rail=ttk.Frame(workspace,width=190);rail.pack(side='left',fill='y',padx=(0,10))
  controls_card=RoundPanel(rail,text='測試控制',padding=9);controls_card.pack(fill='x',pady=(0,8));controls=controls_card.body
  self.connectbtn=PillButton(controls,text='馬達連線',command=self.connect);self.connectbtn.pack(fill='x',pady=3)
  PillButton(controls,text='馬達斷線',command=lambda:self.worker.submit('disconnect')).pack(fill='x',pady=3)
  self.forcebtn=PillButton(controls,text='開始力規讀取',command=self.toggle_force);self.forcebtn.pack(fill='x',pady=3)
  self.startbtn=PillButton(controls,text='開始測試',command=self.begin,role='primary',height=36);self.startbtn.pack(fill='x',pady=(7,3))
  PillButton(controls,text='STOP  停止馬達',command=self.stop_all,role='danger',height=36).pack(fill='x',pady=3)
  PillButton(controls,text='清除故障',command=lambda:self.worker.submit('ack')).pack(fill='x',pady=(3,0))
  self.settingbtns=[]
  groups=(
   ('實驗', [('實驗設定',self.open_settings),('載入實驗',self.load),('儲存實驗',self.save)], True),
   ('報告與輸出', [('開啟圖表報告',self.open_report),('輸出資料夾',self.open_folder)], False),
   ('操作紀錄', [('完整操作紀錄',self.show_log)], False),
   ('裝置與螺旋槳', [('裝置設定',self.open_devices),('PID／PLL',self.open_pid),('螺旋槳管理',self.add_propeller)], True))
  for title,items,lock in groups:
   panel=RoundPanel(rail,text=title,padding=5);panel.pack(fill='x',pady=(0,4))
   for label,command in items:
    button=PillButton(panel.body,text=label,command=command,height=27)
    button.pack(fill='x',pady=1)
    if lock:self.settingbtns.append(button)
  main=ttk.Frame(workspace);main.pack(side='left',fill='both',expand=True)
  self.device_status=tk.StringVar(value='馬達：未連線  |  力規：已停止')
  ttk.Label(main,textvariable=self.device_status,foreground='#5f6d7f',font=('',9,'bold')).pack(anchor='w')
  catalog_error=''
  try:self.propellers=load_catalog(workspace_root(self.cfg['folder']))
  except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
   self.propellers={};catalog_error=str(exc)
  self.propeller_name=tk.StringVar(value='未選擇')
  propeller_row=ttk.Frame(main);propeller_row.pack(fill='x',pady=(4,0))
  ttk.Label(propeller_row,text='螺旋槳').pack(side='left',padx=(0,8))
  self.propeller_combo=ttk.Combobox(propeller_row,textvariable=self.propeller_name,state='readonly',style='Propeller.TCombobox',
   values=('未選擇',*self.propellers),width=38)
  self.propeller_combo.pack(side='left',fill='x',expand=True)
  if catalog_error:root.after_idle(lambda: self.logline('螺旋槳清單讀取失敗：'+catalog_error))
  self.summary=tk.StringVar();ttk.Label(main,textvariable=self.summary,foreground='#7d8998',wraplength=1000,font=('',8)).pack(anchor='w',pady=(3,7))
  self.notice=tk.Frame(main,bg='#f8fafc',padx=10,pady=5);self.notice.pack(fill='x',pady=(0,6))
  self.notice_row=tk.Frame(self.notice,bg='#f8fafc');self.notice_row.pack(fill='x')
  self.notice_title=tk.Label(self.notice_row,text='',font=('Microsoft JhengHei UI',13,'bold'),bg='#f8fafc',anchor='w');self.notice_title.pack(side='left',fill='x',expand=True)
  self.finish_poststop_button=ttk.Button(self.notice_row,text='停止記錄',command=self.finish_poststop)
  self.notice_detail=tk.Label(self.notice,text='',font=('Microsoft JhengHei UI',9),bg='#f8fafc',anchor='w',wraplength=1000);self.notice_detail.pack(fill='x')
  self.dashboard=Dashboard(main,self.tare_force)
  status=RoundPanel(outer,text='操作狀態 · 測試期間請持續監看',padding=5);self.status_frame=status;status.pack(fill='x',pady=(7,0))
  self.action_status=tk.StringVar(value='待命。模擬模式不連實體設備；實機連線後自動開啟已啟用的力規監看。')
  self.statuslabel=ttk.Label(status.body,textvariable=self.action_status,foreground='#4b5563',wraplength=1100);self.statuslabel.pack(anchor='w')
  self.refresh_plan();self.fit_window();root.report_callback_exception=self.callback_error;root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
 def fit_window(self):
  # Tk fonts follow the OS DPI; measure the actual widgets before sizing.
  self.root.update_idletasks()
  screen_w=self.root.winfo_screenwidth();screen_h=self.root.winfo_screenheight()
  max_w=max(900,screen_w-50);max_h=max(620,screen_h-70)
  if self.root.winfo_reqheight()>max_h:
   # Compact the dashboard on shorter/high-DPI screens; no outer scrolling.
   import tkinter.font as tkfont
   self.outer.configure(padding=(10,5));self.status_frame.configure(padding=3)
   self.dashboard.compact_readings();self.root.update_idletasks()
   for step in range(3):
    if self.root.winfo_reqheight()<=max_h:break
    ttk.Style(self.root).configure('.',font=('Microsoft JhengHei UI',max(7,8-step)))
    ttk.Style(self.root).configure('TButton',padding=(5,1))
    ttk.Style(self.root).configure('TLabelframe.Label',font=('',max(7,8-step),'bold'))
    def shrink(w):
     if 'font' in w.keys() and w.cget('font'):
      try:
       actual=tkfont.Font(root=self.root,font=w.cget('font')).actual();size=actual['size']
       w.configure(font=(actual['family'],max(7,round(abs(size)*.88)),actual['weight']))
      except tk.TclError:pass
     for child in w.winfo_children():shrink(child)
    shrink(self.root);self.dashboard.gauge.configure(height=100)
    self.root.update_idletasks()
    if self.root.winfo_reqheight()<=max_h:break
  width=min(max_w,max(1100,self.root.winfo_reqwidth()+24))
  height=min(max_h,max(740,self.root.winfo_reqheight()+24))
  self.root.minsize(min(width,1000),min(height,700));self.root.geometry(f'{width}x{height}')
 def psu_active(self):
  worker=getattr(self.worker,'psu_worker',None)
  return bool(worker and worker.is_alive())
 def toggle_mode(self):
  if self.psu_active():
   messagebox.showinfo('模式切換','請先在裝置設定停用電供擷取，再切換模式。',parent=self.root);return
  if self.connected or self.connecting or self.force_state in ('reading','connecting','stopping'):return
  if self.sim.get() and not messagebox.askokcancel('解除實機鎖定','解除後可連接實體設備。是否繼續？',parent=self.root):return
  self.sim.set(not self.sim.get());self.mode_changed()
 def mode_changed(self):
  self.values={};self.dashboard.reset_trends();self.logline('模擬模式：不開啟實體設備。' if self.sim.get() else '實機模式：尚未啟動馬達。')
 def refresh_plan(self):
  c=self.cfg;speeds=' → '.join(map(str,c['speeds'][:8]))+(' …' if len(c['speeds'])>8 else '')
  self.summary.set(f"本次：{speeds} rpm  ｜  變速 {c['ramp_ms']/1000:g}s  ｜  各停留 {c['dwell_s']:g}s  ｜  基線／停機後 {c['baseline_s']:g}/{c['poststop_s']:g}s")
  self.dashboard.set_plan(c['speeds'],c['baseline_s'],c['dwell_s'],c['poststop_s'])
 def logline(self,s):
  text=str(s);self.history.append(time.strftime('%H:%M:%S')+' '+text);self.history=self.history[-2000:]
  self.action_status.set(text.splitlines()[0])
 def callback_error(self,exc_type,exc,tb):
  detail=''.join(traceback.format_exception(exc_type,exc,tb))
  if self.last_callback_error==detail:return
  self.last_callback_error=detail;self.logline('介面錯誤：'+str(exc)+'\n'+detail);messagebox.showerror('介面執行錯誤',detail[-3500:])
 def getcfg(self):
  validate_plan(self.cfg);return dict(self.cfg)
 def connect(self):
  if self.connected or self.connecting:return
  if not self.worker.is_alive():messagebox.showerror('控制執行緒停止','請重新啟動程式。');return
  self.connecting=True;self.logline('正在連線馬達 '+self.cfg['port']+'；不啟動馬達。')
  self.worker.submit('connect',('SIMULATION' if self.sim.get() else 'REAL',self.cfg['port']))
 def can_tare(self):
  return (self.connected and self.motor_stopped and not self.sim.get()
          and self.force_state=='reading' and not (self.busy or self.pending_begin or self.pending_tare))
 def tare_force(self,channel):
  if not self.can_tare():return
  if not messagebox.askokcancel(f'CH{channel} 軟體歸零','請確認馬達已停穩，且力規未受外力。將以近期穩定讀值設定軟體零點。',parent=self.root):return
  if not self.can_tare():return
  self.pending_tare=True
  self.worker.submit('force_tare',channel)
 def toggle_force(self):
  if self.busy or self.pending_begin or self.pending_tare:return
  if self.force_state in ('reading','connecting','stopping'):
   self.worker.submit('force_stop');self.logline('已請求停止力規監看。')
  else:
   self.values={k:v for k,v in self.values.items() if not k.startswith('force ')}
   self.worker.submit('force_start',('SIMULATION' if self.sim.get() else 'REAL',self.getcfg()))
   self.logline('正在開啟力規監看；不啟動馬達。')
 def set_propellers(self,entries,selected):
  entries=sorted_catalog(entries)
  self.propellers=entries
  self.propeller_combo.configure(values=('未選擇',*entries))
  self.propeller_name.set(selected if selected in entries else '未選擇')

 def add_propeller(self):
  if self.busy or self.pending_begin:return
  root=workspace_root(self.cfg['folder'])
  try:entries=load_catalog(root)
  except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
   messagebox.showerror('無法讀取螺旋槳清單',str(exc),parent=self.root);return
  win=tk.Toplevel(self.root);win.title('螺旋槳管理');win.transient(self.root);win.grab_set()
  frame=ttk.Frame(win,padding=14);frame.pack(fill='both',expand=True)
  columns=('dimension','blades','material','number','rotation')
  labels=('尺寸代碼','葉片數','材質','樣品編號','槳葉標示旋向')
  table=ttk.Treeview(frame,columns=columns,show='headings',height=6,selectmode='browse')
  for key,label in zip(columns,labels):
   table.heading(key,text=label);table.column(key,width=105,anchor='center')
  scroll=ttk.Scrollbar(frame,orient='vertical',command=table.yview)
  table.configure(yscrollcommand=scroll.set)
  table.grid(row=0,column=0,columnspan=2,sticky='nsew',pady=(0,10))
  scroll.grid(row=0,column=2,sticky='ns',pady=(0,10))
  frame.rowconfigure(0,weight=1);frame.columnconfigure(1,weight=1)
  def render():
   table.delete(*table.get_children())
   for name,entry in sorted_catalog(entries).items():table.insert('','end',iid=name,values=[entry[k] or '未設定' for k in columns])
  render()
  values=[tk.StringVar(win) for _ in columns]
  for row,(label,value) in enumerate(zip(labels,values),1):
   ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=4)
   widget=ttk.Combobox(frame,textvariable=value,values=ROTATIONS,state='readonly',style='Propeller.TCombobox') if row==5 else ttk.Entry(frame,textvariable=value,width=28)
   widget.grid(row=row,column=1,sticky='ew',pady=4)
  preview=tk.StringVar(win)
  def refresh(*_):
   try:preview.set(profile(*(v.get() for v in values))['name'] if values[-1].get() else '請選擇槳葉標示旋向。')
   except ValueError:preview.set('請輸入完整的螺旋槳資料。')
  for value in values:value.trace_add('write',refresh)
  refresh()
  name_row=ttk.Frame(frame)
  name_row.grid(row=6,column=0,columnspan=2,sticky='ew',pady=8)
  ttk.Label(name_row,textvariable=preview).pack(side='left',fill='x',expand=True)
  def copy_name():
   try:
    entry=profile(*(v.get() for v in values))
    if not entry['rotation']:raise ValueError('請選擇槳葉標示旋向。')
   except ValueError as exc:
    messagebox.showerror('無法複製名稱',str(exc),parent=win)
    return
   win.clipboard_clear()
   win.clipboard_append(entry['name'])
  ttk.Button(name_row,text='複製名稱',command=copy_name).pack(side='right',padx=(8,0))
  def persist(updated):
   nonlocal entries
   try:save_catalog(root,updated)
   except OSError as exc:
    messagebox.showerror('無法儲存螺旋槳清單',str(exc),parent=win);return False
   entries=updated
   self.set_propellers(entries,self.propeller_name.get())
   render()
   return True
  def save(as_new=False):
   try:
    entry=profile(*(v.get() for v in values));name=entry['name']
    if not entry['rotation']:raise ValueError('請選擇槳葉標示旋向。')
    if any(key.casefold()==name.casefold() for key in entries):raise ValueError('已存在同名螺旋槳。')
   except ValueError as exc:
    messagebox.showerror('無法新增螺旋槳',str(exc),parent=win);return
   legacy=next((key for key in entries if key.casefold()==name.rsplit('_',1)[0].casefold()),None)
   updated=dict(entries)
   if legacy and not entries[legacy]['rotation'] and not as_new:
    if not messagebox.askyesno('補登旋向',f'是否為舊項目 {legacy} 補登 {entry["rotation"]}？',parent=win):return
    del updated[legacy]
   else:legacy=None
   selected=self.propeller_name.get()
   updated[name]=entry
   if persist(updated):
    if selected==legacy:self.propeller_name.set(name)
    for value in values:value.set('')
  def delete():
   selected=table.selection()
   if not selected:return
   name=selected[0]
   if messagebox.askyesno('刪除螺旋槳',f'確定從清單刪除 {name}？',parent=win):
    persist({key:entry for key,entry in entries.items() if key!=name})
  def copy_selected(_event):
   selected=table.selection()
   if selected:
    for key,value in zip(columns,values):value.set(entries[selected[0]][key])
  table.bind('<<TreeviewSelect>>',copy_selected)
  table.bind('<Double-1>',copy_selected)
  ttk.Button(frame,text='刪除所選項目',command=delete).grid(row=7,column=0,sticky='w')
  actions=ttk.Frame(frame)
  actions.grid(row=7,column=1,sticky='e')
  ttk.Button(actions,text='另存新檔',command=lambda:save(as_new=True)).pack(side='left',padx=(0,8))
  ttk.Button(actions,text='儲存',command=save).pack(side='left')

 def begin(self):
  if self.pending_tare:
   return
  try:
   if not self.connected:
    raise ValueError('請先連線馬達')
   reason = self.worker.start_block_reason()
   if reason:
    raise ValueError(reason)
   generation = self.worker.pid.generation
   c = self.getcfg()
   propeller = self.propellers.get(self.propeller_name.get())
   if propeller:
    if not propeller['rotation'] or c.get('mount') not in MOUNTS:
     raise ValueError('請在螺旋槳管理確認旋向，並在實驗設定選擇正裝或反裝。')
    c['propeller'] = dict(propeller)
   if c['port'].upper() != self.worker.port.upper():
    raise ValueError('馬達通訊埠已變更，請中斷連線後重新連接。')
   if self.force_state == 'stopping':
    raise ValueError('力規連接埠正在釋放，請稍後再試')
  except Exception as error:
   messagebox.showerror('設定錯誤', str(error))
   return
  if self.worker.mode == 'REAL' and not messagebox.askokcancel('實機啟動',
   '會先檢查感測器並記錄基線，再啟動至1500rpm並執行轉速清單。\n確認固定、槳葉與作業區；首輪無槳驗證，測試期間請持續監看。\n無法停機請使用實體動力斷電。開始？'):
   return
  reason = self.worker.start_block_reason()
  if not self.connected or self.worker.pid.generation != generation:
   reason = '啟動確認期間連線或停止狀態已變更，請重新確認。'
  if reason:
   messagebox.showerror('無法開始實驗', reason)
   return
  self.pending_begin = True
  self.worker.submit('begin', c)
 def stop_all(self):
  self.pending_begin=False;self.pending_tare=False;self.worker.stop_event.set();self.worker.cancel_pid('已提出停止要求');self.update_pid_dialog();self.logline('已提出停止要求。力規仍持續監看，請確認馬達已停穩。')
 def _parse(self,variables):
  c=dict(self.cfg)
  for k,var in variables.items():
   x=var.get();base=defaults()[k]
   if k=='psu_channels':
    c[k]=[1,2] if x else [1]
    continue
   if isinstance(base,bool):c[k]=bool(x)
   elif isinstance(base,list):c[k]=[int(n.strip()) for n in str(x).replace('，',',').split(',')]
   elif k in ('scale1','scale2'):c[k]=float(x) if str(x).strip() else None
   elif isinstance(base,int):c[k]=int(x)
   elif isinstance(base,float):c[k]=float(x)
   else:c[k]=str(x).strip()
  if c.get('mount')=='未設定':c['mount']=''
  for k in ('force_parity','force_order','psu_backend'):c[k]=c[k].upper()
  validate_plan(c);return c
 def commit(self,c):
  if self.busy or self.pending_begin or self.pending_tare:raise ValueError('記錄或歸零期間鎖定設定')
  validate_plan(c)
  root=workspace_root(c['folder'])
  changed=root!=workspace_root(self.cfg['folder'])
  if changed:entries=load_catalog(root)
  if self.force_state in ('reading','connecting','stopping'):
   if any(c[k]!=self.cfg[k] for k in self.worker.FORCE_COMM) or not c['force_enabled']:raise ValueError('更改力規通訊設定前，請先停止力規讀取')
   self.worker.submit('force_apply',dict(c))
  self.cfg=dict(c)
  self.worker.submit('psu_apply',('SIMULATION' if self.sim.get() else 'REAL',dict(c)))
  if changed:
   self.latest_output_dir=None
   self.set_propellers(entries,'未選擇')
  self.refresh_plan();self.logline('設定已套用。')
 def form(self,title,groups,read_settings=None):
  if self.busy or self.pending_begin:return
  win=tk.Toplevel(self.root);win.title(title);win.transient(self.root);self.dialogs.append(win)
  tabs=ttk.Notebook(win);tabs.pack(fill='both',expand=True,padx=8,pady=8);variables={}
  for label,fields in groups:
   page=ttk.Frame(tabs,padding=12);tabs.add(page,text=label);page.columnconfigure(1,weight=1)
   for i,(key,text) in enumerate(fields):
    value=self.cfg[key];var=tk.BooleanVar(value=value) if isinstance(value,bool) else tk.StringVar(value=','.join(map(str,value)) if isinstance(value,list) else '' if value is None else str(value));variables[key]=var
    ttk.Label(page,text=text).grid(row=i,column=0,sticky='w',pady=4,padx=(0,12))
    widget=ttk.Checkbutton(page,variable=var) if isinstance(value,bool) else ttk.Entry(page,textvariable=var,width=38)
    if key=='mount':
     if not var.get():var.set('未設定')
     widget=ttk.Combobox(page,textvariable=var,values=('未設定',*MOUNTS),state='readonly',style='Propeller.TCombobox')
    if key=='psu_channels':
     var=tk.BooleanVar(value=2 in value);variables[key]=var
     widget=ttk.Checkbutton(page,variable=var)
    widget.grid(row=i,column=1,sticky='ew')
  buttons=ttk.Frame(win,padding=8);buttons.pack(fill='x')
  def apply():
   try:self.commit(read_settings(variables) if read_settings else self._parse(variables))
   except Exception as e:messagebox.showerror('設定',str(e),parent=win)
  ttk.Button(buttons,text='套用設定',command=apply).pack(side='left')
  ttk.Button(buttons,text='關閉',command=win.destroy).pack(side='right')
  return win,tabs,variables,buttons
 def experiment_name(self,c,propeller):
  return c['run_name'].strip() or (
   run_label(propeller['name']+'_'+MOUNTS.get(c.get('mount'),'MountUnset'),c['speeds']) if propeller
   else '-'.join(map(str,c['speeds']))+'RPM')

 def open_settings(self):
  automatic=''
  original_output=self.cfg['folder']
  original_root=str(workspace_root(original_output))
  def read_settings(variables):
   c=self._parse(variables)
   root=c['folder'].strip()
   if not root:raise ValueError('請指定工作資料夾。')
   c['folder']=original_output if root==original_root else str(Path(root).expanduser()/'ExperimentData')
   if c['run_name']==automatic:c['run_name']=''
   return c
  result=self.form('實驗設定',[EXPERIMENT_GROUP],read_settings)
  if not result:return
  win,tabs,variables,buttons=result
  page=tabs.nametowidget(tabs.tabs()[0])
  variables['folder'].set(original_root)
  def browse():
   path=filedialog.askdirectory(parent=win,initialdir=variables['folder'].get())
   if path: variables['folder'].set(path)
  ttk.Button(page,text='瀏覽…',command=browse).grid(row=8,column=2,padx=(6,0))
  ttk.Label(page,text='可自訂名稱，儲存時預填為 JSON 檔名。',foreground='#68717d').grid(row=0,column=2,padx=(6,0))
  output_label=ttk.Label(page,foreground='#68717d')
  output_label.grid(row=10,column=1,columnspan=2,sticky='w')
  preview=PlanPreview(page);preview.grid(row=11,column=0,columnspan=2,sticky='ew',pady=(8,0))
  def refresh_preview(*args):
   nonlocal automatic
   try:c=read_settings(variables)
   except (ValueError,TypeError,OverflowError):preview.invalid();return
   previous=automatic
   propeller=self.propellers.get(self.propeller_name.get())
   automatic=self.experiment_name(dict(c,run_name=''),propeller)
   if variables['run_name'].get().strip() in ('',previous):variables['run_name'].set(automatic)
   output_label.configure(text="量測輸出位置："+str(Path(c["folder"]).expanduser()))
   preview.update_plan(c)
  for key in ('speeds','ramp_ms','dwell_s','baseline_s','poststop_s','max_rpm','reach_timeout_s','folder','mount'):
   variables[key].trace_add('write',refresh_preview)
  selection_trace=self.propeller_name.trace_add('write',refresh_preview)
  def release_selection_trace(event):
   if event.widget is win:self.propeller_name.trace_remove('write',selection_trace)
  win.bind('<Destroy>',release_selection_trace,add='+')
  page.grid_slaves(row=0,column=1)[0].bind('<FocusOut>',refresh_preview)
  refresh_preview();win.geometry('760x700');win.minsize(640,640)

 def open_pid(self):
  dialog=getattr(self,'pid_dialog',None)
  if dialog and dialog.winfo_exists():
   dialog.lift()
   return
  self.pid_dialog=PidDialog(self)
  self.pid_dialog.refresh()

 def update_pid_dialog(self):
  dialog=getattr(self,'pid_dialog',None)
  if dialog and dialog.winfo_exists():dialog.result()

 def open_devices(self):
  result=self.form('裝置設定',DEVICE_GROUPS)
  if not result:return
  win,tabs,variables,buttons=result
  ttk.Button(buttons,text='載入裝置',command=lambda:self.load('device',result)).pack(side='left',padx=4)
  ttk.Button(buttons,text='儲存裝置',command=lambda:self.save('device',win)).pack(side='left',padx=4)
  ttk.Button(buttons,text='列出 COM／VISA',command=self.resources).pack(side='left',padx=4)
  for ch in (1,2):
   page=tabs.nametowidget(tabs.tabs()[ch+2])
   usage=tk.StringVar(win)
   def update_usage(*_,ch=ch,usage=usage):
    roles=[title for key,title in (('thrust_channel','推力'),('torque_channel','扭矩')) if variables[key].get().strip()==str(ch)]
    usage.set('通道用途：'+('、'.join(roles) if roles else '未指定'))
   for key in ('thrust_channel','torque_channel'):variables[key].trace_add('write',update_usage)
   update_usage()
   ttk.Label(page,textvariable=usage).grid(row=3,column=0,columnspan=2,sticky='w')
   ttk.Button(page,text=f'CH{ch} 兩點校正',command=lambda ch=ch:self.calibrate(ch,variables)).grid(row=4,column=1,sticky='w',pady=8)
   ttk.Label(page,text='換算=(原始值−原始零點)×倍率。校正結果填回後，請按「套用設定」生效。').grid(row=5,column=0,columnspan=2,sticky='w')
 def calibrate(self,ch,variables):
  win=tk.Toplevel(self.root);win.title(f'CH{ch} 兩點校正');values=[]
  ttk.Label(win,text='填入兩個已知負載對應的原始值；已知值使用通道設定單位。\n扭矩=已知力×力臂，注意正負方向。').grid(row=0,column=0,columnspan=2,padx=12,pady=10)
  for i,label in enumerate(('原始值 A','已知值 A','原始值 B','已知值 B')):
   ttk.Label(win,text=label).grid(row=i+1,column=0,padx=8,pady=4);var=tk.StringVar();values.append(var);ttk.Entry(win,textvariable=var).grid(row=i+1,column=1,padx=8)
  def calculate():
   try:
    scale,zero=calibration_scale(*[float(v.get()) for v in values]);variables[f'scale{ch}'].set(f'{scale:.12g}');variables[f'zero{ch}'].set(f'{zero:.12g}');win.destroy()
   except Exception as e:messagebox.showerror('校正',str(e),parent=win)
  ttk.Button(win,text='填回校正面板（仍需按套用）',command=calculate).grid(row=5,column=0,columnspan=2,pady=10)
 def load(self,kind='experiment',dialog=None):
  if self.busy or self.pending_begin:return
  parent=dialog[0] if dialog else self.root
  try:
   folder=workspace_root(self.cfg['folder'])/('DeviceSettings' if kind=='device' else 'ExperimentSettings')
   folder.mkdir(parents=True,exist_ok=True)
   path=filedialog.askopenfilename(parent=parent,initialdir=str(folder),filetypes=[('JSON','*.json')])
   if not path:return
   values=json.loads(Path(path).read_text(encoding='utf-8-sig'))
   keys=DEVICE_KEYS if kind=='device' else EXPERIMENT_KEYS
   subset={k:values[k] for k in keys if k in values}
   if not subset or values.get('settings_type',kind)!=kind:raise ValueError('此 JSON 不包含對應設定')
   selected=None
   if kind=='experiment' and values.get('propeller'):
    item=values['propeller']
    selected=profile(*(item[k] for k in ('dimension','blades','material','number')), item.get('rotation',''))
   if kind=='experiment':subset.setdefault('mount','')
   self.commit(dict(self.cfg,**subset))
   if kind=='experiment':
    if selected:self.propellers[selected['name']]=selected
    self.propeller_combo.configure(values=('未選擇',*self.propellers))
    self.propeller_name.set(selected['name'] if selected else '未選擇')
   if dialog:
    for k,var in dialog[2].items():
     value=self.cfg[k]
     var.set((2 in value) if k=='psu_channels' else ','.join(map(str,value)) if isinstance(value,list) else '' if value is None else value)
  except Exception as e:messagebox.showerror('載入設定',str(e),parent=parent)

 def save(self,kind='experiment',parent=None):
  if self.busy or self.pending_begin:return
  parent=parent or self.root
  try:
   c=self.getcfg()
   keys=DEVICE_KEYS if kind=='device' else EXPERIMENT_KEYS
   data={k:v for k,v in c.items() if k in keys}
   data['settings_type']=kind
   if kind=='experiment':
    selected=self.propellers.get(self.propeller_name.get())
    data['propeller']=selected
    name=self.experiment_name(c,selected)
    name=clean_filename(name) or 'Experiment'
   else:name='device'
   folder=workspace_root(c['folder'])/('DeviceSettings' if kind=='device' else 'ExperimentSettings')
   folder.mkdir(parents=True,exist_ok=True)
   if kind=='device':
    path=folder/'device.json'
    if path.exists() and not messagebox.askyesno('儲存裝置設定','是否覆寫工作資料夾中的 device.json？',parent=parent):return
   else:
    path=filedialog.asksaveasfilename(parent=parent,initialdir=str(folder),initialfile=name+'.json',defaultextension='.json',filetypes=[('JSON','*.json')])
   if path and Path(path).name.casefold()=='propellers.json':
    raise ValueError('propellers.json 為螺旋槳清單專用檔名。')
   if path:Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  except Exception as e:messagebox.showerror('儲存設定',str(e),parent=parent)
 def open_folder(self,all_runs=False):
  try:
   root=Path(self.cfg['folder']).expanduser();root.mkdir(parents=True,exist_ok=True)
   path=root if all_runs else self.latest_output_dir if self.latest_output_dir and self.latest_output_dir.is_dir() and self.latest_output_dir.parent==root else latest_session_folder(root)
   if sys.platform=='win32':os.startfile(str(path))
   else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(path)])
  except Exception as e:messagebox.showerror('資料夾',str(e))
 def resources(self):
  def scan():
   try:
    from serial.tools import list_ports
    self.worker.emit('log','COM：'+', '.join(p.device+' '+p.description for p in list_ports.comports()))
   except Exception as e:self.worker.emit('log','COM：'+str(e))
   try:
    import pyvisa
    rm=pyvisa.ResourceManager();self.worker.emit('log','VISA：'+repr(rm.list_resources()));rm.close()
   except Exception as e:self.worker.emit('log','VISA 列舉不可用（SERIAL 連線不受影響）：'+str(e))
  threading.Thread(target=scan,daemon=True).start()
 def open_report(self):
  if self.busy or self.pending_begin:
   messagebox.showinfo('圖表報告','本輪量測尚未結束，完成後即可開啟圖表報告。');return
  folder=self.latest_output_dir or latest_session_folder(Path(self.cfg['folder']).expanduser())
  path=Path(folder)/'data_report.html'
  if path.is_file():webbrowser.open(path.resolve().as_uri())
  else:messagebox.showinfo('圖表報告','本輪報告尚未產生。舊版紀錄可用 generate_report_windows.bat 選取 data.csv 補產生。')
 def finish_poststop(self):
  if self.busy and self.dashboard.phase=='poststop' and self.latest_output_dir:
   self.finish_poststop_button.state(['disabled'])
   self.worker.submit('finish_poststop',self.latest_output_dir)

 def refresh_notice(self):
  d=self.dashboard
  args=run_notice(self.busy,d.phase,d.remaining,d.ended,d.reason,self.report_state)
  if args!=self.last_notice:
   title,detail,bg,fg=args;self.notice.configure(bg=bg);self.notice_row.configure(bg=bg);self.notice_title.configure(text=title,bg=bg,fg=fg);self.notice_detail.configure(text=detail,bg=bg,fg=fg);self.last_notice=args
   self.root.title('Robi v0.3.29 · '+title+(f' {max(0,d.remaining):.0f}s' if self.busy and d.phase=='poststop' else ''))
  key='poststop' if self.busy and d.phase=='poststop' else 'ended' if d.ended and not self.busy else 'active' if self.busy else 'idle'
  if key!=self.last_notice_key:
   if key=='poststop':
    self.finish_poststop_button.state(['!disabled'])
    self.finish_poststop_button.pack(side='right',padx=(8,0))
   else:self.finish_poststop_button.pack_forget()
   if key in ('poststop','ended'):
    self.root.bell()
   self.last_notice_key=key
 def show_log(self):
  win=tk.Toplevel(self.root);win.title('完整操作紀錄');win.geometry('900x440');text=tk.Text(win,wrap='word');text.pack(fill='both',expand=True);text.insert('end','\n'.join(self.history));text.configure(state='disabled')
 def poll(self):
  try:self.poll_once()
  except Exception:self.callback_error(*sys.exc_info())
  finally:self.root.after(100,self.poll)
 def poll_once(self):
  for _ in range(500):
   try:key,value=self.worker.events.get_nowait()
   except queue.Empty:break
   if key=='log':self.logline(value)
   elif key=='task_event':
    self.dashboard.event(value)
    if value['reason']=='session_begin':self.pending_begin=False;self.report_state='';self.busy=True
   elif key=='fault_ack':self.dashboard.alert=''
   elif key=='session_folder':self.latest_output_dir=Path(value)
   elif key=='finished':self.latest_output_dir=Path(value).parent;self.busy=False;self.report_state='原始紀錄已保存，圖表報告產生中…'
   elif key=='report_ready':
    if self.latest_output_dir==Path(value).parent:self.report_state='圖表報告已保存，可按「開啟圖表報告」。'
   elif key=='report_error':
    if self.latest_output_dir==Path(value['path']).parent:self.report_state='原始紀錄已保存；圖表報告失敗，請查看操作紀錄。'
   elif key=='pid_values':
    if self.worker.pid.accept(value):
     self.update_pid_dialog()
     self.logline(self.worker.pid.view()['status'])
    else:self.logline('忽略失效 PID 回覆：'+str(value))
   elif key=='force_tared':
    channel,zero=value
    self.pending_tare=False
    self.cfg[f'zero{channel}']=zero
    self.values.pop(f'force CH{channel}',None)
    self.dashboard.force_trends[channel].series.clear()
    self.logline(f'CH{channel} 已設定軟體零點（{zero:.3f} count）。')
   elif key=='psu_state':
    self.logline('電供：'+value['detail'])
    if value['state']!='reading':
     self.values.pop('psu CH1',None);self.values.pop('psu CH2',None)
   elif key=='force_reset':self.values={}
   elif key=='sensor':
    name=value['device']+' CH'+str(value['channel']);data=self.values.setdefault(name,{})
    for field in ('raw_signed_int32','scale','raw_zero','scaled_value','unit','force_N','force_gf','torque_Nm','supply_V','supply_A','supply_W','supply_set_V','supply_limit_A','supply_current_limited'):
     if field in value:data[field]=value[field]
    data['received']=value['receive_mono']
   elif key=='force_state':
    self.force_state=value['state'];self.logline('力規：'+value['detail'])
   elif key=='connect_result':
    self.connecting=False
    if not value['ok']:messagebox.showerror('馬達連線失敗',value['error'])
   elif key=='connected':
    self.connected=value
    self.update_pid_dialog()
    if value:self.worker.submit('psu_apply',('SIMULATION' if self.sim.get() else 'REAL',self.getcfg()))
    if value and self.cfg['force_enabled']:self.worker.submit('force_start',('SIMULATION' if self.sim.get() else 'REAL',self.getcfg()))
   elif key=='sample':
    sample=value['sample']
    self.motor_stopped=bool(sample and sample['state']==0 and sample['rpm']==0 and not sample['faults'])
    self.busy=value['busy'];self.dashboard.update_sample(value,self.cfg['max_rpm'])
   elif key=='command_error':
    self.pending_begin=False
    if value.get('command')=='force_tare':self.pending_tare=False
    if value.get('command')=='connect' and self.connecting:
     self.connecting=False;messagebox.showerror('馬達連線失敗',value['error'])
  locked=self.busy or self.pending_begin or self.pending_tare
  self.connectbtn.configure(state='disabled' if self.connected or self.connecting else 'normal',text='連線中…' if self.connecting else '馬達連線')
  self.simbtn.configure(role='mode_locked' if self.sim.get() else 'mode',text=('實機鎖定（僅模擬）' if self.sim.get() else '實機已解鎖'),state='disabled' if self.connected or self.connecting or self.psu_active() or self.force_state in ('connecting','reading','stopping') else 'normal')
  self.startbtn.configure(state='disabled' if locked or not self.connected or self.worker.start_block_reason() else 'normal')
  self.forcebtn.configure(text='停止力規讀取' if self.force_state in ('reading','connecting') else '停止中…' if self.force_state=='stopping' else '開始力規讀取',state='disabled' if locked or self.force_state=='stopping' else 'normal')
  self.propeller_combo.configure(state='disabled' if locked else 'readonly')
  for b in self.settingbtns:b.configure(state='disabled' if locked else 'normal')
  mode='模擬' if self.sim.get() else '實機'
  state={'reading':'持續監看','connecting':'連線中','stopping':'停止中','error':'通訊異常','stopped':'已停止','simulation':'模擬不擷取'}.get(self.force_state,self.force_state)
  self.device_status.set(f"{mode}  |  馬達：{'連線中' if self.connecting else '已連線' if self.connected else '未連線'}  |  力規：{state}  |  {'記錄中' if self.busy else '未記錄'}")
  propeller=self.propellers.get(self.propeller_name.get(),{})
  factors=direction_factors(self.cfg.get('mount'),propeller.get('rotation'))
  self.dashboard.update_sensors(self.values,self.cfg,self.force_state,self.busy,factors)
  for button in self.dashboard.tare_buttons.values():
   button.configure(state='normal' if self.can_tare() else 'disabled')
  dialog=getattr(self,'pid_dialog',None)
  if dialog and dialog.winfo_exists():dialog.refresh()
  self.refresh_notice()
 def close(self):
  if self.busy and not messagebox.askokcancel('結束','將停止馬達並完成停機後記錄。請確認實體停穩。'):return
  self.pending_begin=False;self.worker.quit_event.set();self.root.after(100,self.wait_close)
 def wait_close(self):
  if self.worker.is_alive():self.root.after(100,self.wait_close)
  else:self.root.destroy()

if __name__=='__main__':
 root=tk.Tk();App(root);root.mainloop()
