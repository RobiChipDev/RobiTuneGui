"""Tk dashboard components; display only, no device or motion commands."""
import math
import time
from ui_widgets import RoundPanel,Sparkline
import tkinter as tk
from tkinter import ttk

PHASES = {'disconnected':'未連線', 'idle':'待命', 'preflight':'感測器檢查',
          'baseline':'啟動前記錄', 'starting':'馬達啟動', 'startup_settle':'啟動後到速確認', 'ramping':'變速／到速確認',
          'dwelling':'定速記錄', 'stopping':'等待停止狀態', 'poststop':'停機後記錄'}

def pretty(value, digits=2):
    if value is None or value == '':return '—'
    try:
        x=float(value)
        return f'{x:.{digits}f}' if math.isfinite(x) else '—'
    except (TypeError,ValueError):return '—'

from notices import ABORTS, fault_label, outcome_label

class SpeedGauge(tk.Canvas):
    def __init__(self,parent):
        super().__init__(parent,width=230,height=154,bg='white',highlightthickness=0)
        self.rpm=None;self.target=0;self.limit=2600;self.simulation=True;self.fault=False
        self.bind('<Configure>',lambda e:self.draw())
    def update_value(self,rpm,target,limit,simulation,fault=False):
        self.rpm=rpm;self.target=target;self.limit=max(1,limit);self.simulation=simulation;self.fault=fault;self.configure(bg='#fff1f2' if fault else 'white');self.draw()
    def draw(self):
        self.delete('all');w=max(160,self.winfo_width());h=max(90,self.winfo_height());cx=w/2;cy=h*.57;r=min(w*.39,h*.49)
        box=(cx-r,cy-r,cx+r,cy+r)
        self.create_arc(*box,start=-35,extent=250,style='arc',outline='#ef4444' if self.fault else '#edf0f4',width=8)
        if self.rpm is not None:
            extent=250*max(0,min(abs(self.rpm)/self.limit,1))
            if extent:self.create_arc(*box,start=215-extent,extent=extent,style='arc',outline='#334155',width=8)
        def point(v,radius):
            a=math.radians(215-250*max(0,min(v/self.limit,1)));return cx+radius*math.cos(a),cy-radius*math.sin(a)
        for i in range(21):
            x1,y1=point(self.limit*i/20,r*1.13);x2,y2=point(self.limit*i/20,r*(1.03 if i%5==0 else 1.08))
            self.create_line(x1,y1,x2,y2,fill='#a2adbb',width=2 if i%5==0 else 1)
        if self.target>0:
            x1,y1=point(self.target,r*.92);x2,y2=point(self.target,r*1.17);self.create_line(x1,y1,x2,y2,fill='#94a3b8',width=2)
        self.create_text(cx,h*.50,text=pretty(self.rpm,0),font=('Segoe UI',max(16,min(32,int(h*.29/float(self.tk.call('tk','scaling'))))),'bold'),fill='#b91c1c' if self.fault else '#17212f')
        self.create_text(cx,h*.77,text='RPM',font=('Segoe UI',9),fill='#8490a0')
        self.create_text(cx,h-2,text=f'0–{self.limit} rpm  ·  '+('模擬回授' if self.simulation else '板端回授'),anchor='s',font=('',7),fill='#8490a0')

class Dashboard(ttk.Frame):
    def __init__(self,parent,on_tare=None):
        super().__init__(parent)
        self.pack(fill='both',expand=True)
        self.columnconfigure(0,weight=1,uniform='panels');self.columnconfigure(2,weight=1,uniform='panels');self.columnconfigure(4,weight=1,uniform='panels');self.columnconfigure(1,minsize=8);self.columnconfigure(3,minsize=8);self.rowconfigure(1,weight=1)
        top=ttk.Frame(self);top.grid(row=0,column=0,columnspan=5,sticky='ew',pady=(0,8))
        for col in (0,2,4):top.columnconfigure(col,weight=1,uniform='meters')
        top.columnconfigure(1,minsize=8);top.columnconfigure(3,minsize=8)
        speed_box=RoundPanel(top,text='轉速回授',padding=10);speed_box.grid(row=0,column=0,sticky='nsew')
        self.speed_card=speed_box;self.gauge=SpeedGauge(speed_box.body);self.gauge.pack(fill='both',expand=True)
        self.rpm_trend=Sparkline(speed_box.body,height=35);self.rpm_trend.pack(fill='x')
        self.tare_buttons={}
        self.force_trends={};self.force_titles={};self.force_cards={};self.force_raw={};self.force_fresh={}
        for ch in (1,2):
            box=RoundPanel(top,text=f'CH{ch} · '+('推力' if ch==1 else '扭矩'),padding=10);box.grid(row=0,column=ch*2,sticky='nsew');self.force_titles[ch]=box
            self.force_cards[ch]=tk.StringVar(value='—');self.force_raw[ch]=tk.StringVar(value='原始值 —');self.force_fresh[ch]=tk.StringVar(value='尚未讀取')
            readout = ttk.Frame(box.body)
            readout.pack(fill='x')
            ttk.Label(readout,textvariable=self.force_cards[ch],font=('Segoe UI',30,'bold'),foreground='#0f172a').pack(side='left')
            ttk.Label(readout,textvariable=self.force_raw[ch],font=('Segoe UI',7),foreground='#64748b').pack(side='left',padx=(6,0))
            controls=ttk.Frame(box.body)
            controls.pack(fill='x')
            if on_tare:
                self.tare_buttons[ch]=ttk.Button(controls,text='歸零',width=5,state='disabled',command=lambda channel=ch:on_tare(channel))
                self.tare_buttons[ch].pack(side='right')
            ttk.Label(controls,textvariable=self.force_fresh[ch],foreground='#68717d').pack(side='left')
            self.force_trends[ch]=Sparkline(box.body,height=58);self.force_trends[ch].pack(fill='both',expand=True,pady=(7,0))
        flow_card=RoundPanel(self,text='實驗流程',padding=8);flow_card.grid(row=1,column=0,columnspan=3,sticky='nsew')
        flow=flow_card.body
        heading=ttk.Frame(flow);heading.pack(fill='x')
        self.phase_text=tk.StringVar(value='待命 · 尚未開始記錄')
        ttk.Label(heading,textvariable=self.phase_text,font=('',10,'bold')).pack(side='left')
        ttk.Button(heading,text='完整清單',command=self.show_all).pack(side='right')
        self.task_box=ttk.Frame(flow);self.task_box.pack(fill='both',expand=True);self.task_box.columnconfigure(0,weight=2);self.task_box.columnconfigure(2,weight=1)
        for col,title in enumerate(('任務','狀態','時間／進度')):ttk.Label(self.task_box,text=title,foreground='#64748b').grid(row=0,column=col,sticky='w')
        self.task_widgets=[]
        for i in range(8):
            name=ttk.Label(self.task_box);state=ttk.Label(self.task_box,width=7)
            cell=ttk.Frame(self.task_box);clock=ttk.Label(cell,width=16);clock.pack(side='left');bar=ttk.Progressbar(cell,maximum=100,length=70);bar.pack(side='left',fill='x',expand=True)
            name.grid(row=i+1,column=0,sticky='w',pady=1);state.grid(row=i+1,column=1,sticky='w');cell.grid(row=i+1,column=2,sticky='ew')
            self.task_widgets.append((name,state,cell,clock,bar))
        right_card=RoundPanel(self,text='狀態與保護',padding=8);right_card.grid(row=1,column=4,sticky='nsew')
        right=right_card.body
        self.motor_state=tk.StringVar(value='未連線');ttk.Label(right,textvariable=self.motor_state,font=('',12,'bold')).pack(anchor='w')
        lamps=ttk.Frame(right);lamps.pack(fill='x',pady=5);self.lamps={}
        for i,(bit,label) in enumerate([(1,'FOC 逾時'),(2,'母線過壓'),(4,'母線欠壓'),(8,'過溫'),(16,'啟動失敗'),(32,'回授異常'),(64,'Break／過流'),(128,'軟體錯誤')]):
            lamp=tk.Label(lamps,text='● '+label,fg='#9ca3af',bg='#ffffff',anchor='w',font=('Microsoft JhengHei UI',9));lamp.grid(row=i//2,column=i%2,sticky='w',padx=(0,12),pady=3);self.lamps[bit]=lamp
        self.fault_note=tk.StringVar(value='尚無有效資料');self.fault_label=ttk.Label(right,textvariable=self.fault_note,wraplength=290,foreground='#68717d');self.fault_label.pack(anchor='w')
        self.run_note=tk.StringVar(value='');ttk.Label(right,textvariable=self.run_note,wraplength=330,foreground='#475569').pack(anchor='w',pady=4)
        readings_card=RoundPanel(self,text='電氣與溫度 · 未接入顯示 —',padding=6);readings_card.grid(row=2,column=0,columnspan=5,sticky='ew',pady=(8,6))
        readings=readings_card.body
        self.reading_cells=[];self.readings={}
        specs=[('bus','板端 DC Bus'),('amps','Imotor · 電供'),('wi','Wi · 輸入功率'),('wo','Wo · Pilot'),('temp','板端溫度'),('iq','Iq'),('id','Id'),('eff','推力／輸入功率'),('supply','電供實測電壓'),('limits','設定電壓／限流'),('cc','電供限流狀態'),('coil','線圈 T2／環境溫度')]
        for i,(key,label) in enumerate(specs):
            col=i%4;row=i//4;readings.columnconfigure(col,weight=1,uniform='readouts')
            cell=ttk.Frame(readings);cell.grid(row=row,column=col,sticky='ew',padx=8,pady=2)
            label_widget=ttk.Label(cell,text=label,foreground='#64748b',font=('',8));label_widget.pack(anchor='w')
            v=tk.StringVar(value='—');self.readings[key]=v;value_widget=ttk.Label(cell,textvariable=v,font=('',11,'bold'));value_widget.pack(anchor='w');self.reading_cells.append((key,label_widget,value_widget))
        self.psu_extra=tk.StringVar(value='電供 CH2：未啟用擷取')
        ttk.Label(readings,textvariable=self.psu_extra,foreground='#64748b',font=('',8)).grid(row=3,column=0,columnspan=4,sticky='w',padx=8)
        self.plan=None;self.completed=set();self.done_keys=set();self.started=False;self.ended=False;self.reason='';self.phase='disconnected';self.index=0;self.active=False;self.sample=None;self.rows=[];self.remaining=0;self.duration=0;self.alert=''
    def compact_readings(self):
        self.speed_card.configure(padding=6)
        self.rpm_trend.configure(height=20)
        for ch,trend in self.force_trends.items():
            self.force_titles[ch].configure(padding=6);trend.configure(height=30)
        short={'bus':'VBUS','amps':'CH1 電流','wi':'CH1 Wi','wo':'Wo','temp':'板溫','iq':'Iq','id':'Id','eff':'gf/W','supply':'電供 CH1 V','limits':'設定 V/A','cc':'CC','coil':'T2／環溫'}
        for key,label,value in self.reading_cells:
            label.pack_forget();value.pack_forget();label.configure(text=short[key]);label.pack(side='left',padx=(0,4));value.pack(side='right')
    def set_plan(self,speeds,baseline,dwell,poststop):
        plan=(tuple(speeds),baseline,dwell,poststop)
        if self.plan==plan:return
        self.plan=plan;self.started=False;self.ended=False;self.completed=set();self.done_keys=set();self.reason=''
        self.rows=[('preflight','感測器檢查'),('baseline',f'啟動前記錄 · {baseline:g}s'),('starting','啟動至 1500 rpm')]+[(f'stage{i}',f'{i}. {rpm} rpm · {dwell:g}s') for i,rpm in enumerate(speeds,1)]+[('stopping','確認停機'),('poststop',f'停機後記錄 · {poststop:g}s')]
        self.render_tasks()
    def event(self,event):
        reason=event['reason']
        if reason=='session_begin':self.alert='';self.completed=set();self.done_keys=set();self.started=True;self.ended=False;self.reason=''
        if reason=='stage_timed_complete':self.completed.add(event['stage_index'])
        done={'baseline_begin':'preflight','motor_start':'baseline','stop_state_confirmed':'stopping','session_end':'poststop'}
        if reason in done:self.done_keys.add(done[reason])
        if reason=='stage_ramp' and event['stage_index']==1:self.done_keys.add('starting')
        if reason=='stop_requested':
            self.reason=event['detail']
            if self.reason.partition(' ')[0] not in ABORTS and self.reason!='sequence_complete':
                self.alert=outcome_label(self.reason)
        if reason=='stop_state_unconfirmed' and not self.alert:self.alert=outcome_label(reason)
        if reason=='session_end':self.ended=True;self.reason=event['detail']
    def task_state(self,key):
        current=f'stage{self.index}' if self.phase in ('ramping','dwelling') else 'starting' if self.phase=='startup_settle' else self.phase
        done=(int(key[5:]) in self.completed) if key.startswith('stage') else key in self.done_keys
        if done:return '已完成','#68717d',False
        if self.active and key==current:return '執行中','#334155',True
        if self.ended and self.reason!='sequence_complete':return '未完成','#b91c1c',False
        return '等待中','#64748b',False
    def render_tasks(self):
        rows=self.rows
        if len(rows)>8:
            stages=[r for r in rows if r[0].startswith('stage')];j=max(0,min(len(stages)-3,self.index-2))
            rows=rows[:3]+stages[j:j+3]+rows[-2:]
        for i,widgets in enumerate(self.task_widgets):
            name,state,cell,clock,bar=widgets
            if i>=len(rows):
                self.task_box.rowconfigure(i+1,weight=0)
                for w in (name,state,cell):w.grid_remove()
                continue
            self.task_box.rowconfigure(i+1,weight=1)
            for w in (name,state,cell):w.grid()
            key,title=rows[i];status,color,active=self.task_state(key)
            name.configure(text=title,foreground='#20252b');state.configure(text=status,foreground=color)
            if active:
                wait=self.phase in ('preflight','starting','startup_settle','ramping','stopping')
                clock.configure(text=f'{max(0,self.duration-self.remaining):.1f}/{self.duration:.0f}s'+(' 上限' if wait else ''))
                bar['value']=min(100,max(0,100*(self.duration-self.remaining)/self.duration)) if self.duration else 0
                bar.pack(side='left',fill='x',expand=True)
            else:
                seconds=self.plan[1] if key=='baseline' else self.plan[3] if key=='poststop' else self.plan[2] if key.startswith('stage') else None
                clock.configure(text=f'{seconds:g}/{seconds:g}s' if status=='已完成' and seconds is not None else '完成' if status=='已完成' else '—');bar.pack_forget()
    def show_all(self):
        win=tk.Toplevel(self);win.title('完整實驗任務清單');win.geometry('620x420')
        tree=ttk.Treeview(win,columns=('task','status'),show='headings');tree.heading('task',text='任務');tree.heading('status',text='狀態');tree.column('task',width=380);tree.column('status',width=140)
        sb=ttk.Scrollbar(win,command=tree.yview);sb.pack(side='right',fill='y');tree.configure(yscrollcommand=sb.set);tree.pack(fill='both',expand=True)
        for key,title in self.rows:tree.insert('', 'end',values=(title,self.task_state(key)[0]))
    def update_sample(self,v,limit):
        self.sample=v['sample'];self.active=v['busy'];self.phase=v['phase'];self.index=v.get('stage_index',0);self.remaining=v.get('remaining',0);self.duration=v.get('phase_duration',0)
        s=self.sample
        if s and s['faults']:self.alert=fault_label(s['faults'])
        self.gauge.update_value(s['rpm'] if s else None,v['target'] if self.active else 0,limit,v['mode']=='SIMULATION',fault=bool(self.alert))
        title='流程完成' if self.ended and self.reason=='sequence_complete' else '流程中止' if self.ended else PHASES.get(self.phase,self.phase)
        self.phase_text.set(title+f' · {len(self.completed)}/{len(self.plan[0]) if self.plan else 0} 組完成')
        self.motor_state.set((s['status']+' · '+str(s['rpm'])+' rpm') if s else '未連線／無有效資料')
        for bit,lamp in self.lamps.items():lamp.configure(fg='#dc2626' if s and s['faults']&bit else '#64748b' if s else '#94a3b8')
        self.fault_note.set(self.alert or ('已中止' if self.ended and self.reason in ABORTS else '無故障' if s else '尚無有效資料'))
        self.fault_label.configure(foreground='#b91c1c' if self.alert else '#68717d')
        self.run_note.set(f"目標 {v['target']} rpm · 板端命令 {s['reference'] if s else '—'} rpm"+('\n等待階段的時間為上限，非成功倒數。' if self.phase in ('starting','startup_settle','ramping') else ''))
        for key,source,unit in [('bus','board_bus_V','V'),('wo','motor_power_W','W'),('temp','board_temp_C','°C'),('iq','iq_A','A'),('id','id_A','A')]:self.readings[key].set(pretty(s.get(source) if s else None)+' '+unit)
        if s:self.rpm_trend.push(v.get('sample_mono',time.monotonic()),s['rpm'],source=v['mode'],label='rpm · 30s')
        self.render_tasks()
    def reset_trends(self):
        self.rpm_trend.series.clear();self.rpm_trend.draw()
        for trend in self.force_trends.values():trend.series.clear();trend.draw()
    def update_sensors(self,data,cfg,force_state,busy,factors=None):
        now=time.monotonic()
        factors=factors or {}
        for ch in (1,2):
            role='推力' if ch==cfg['thrust_channel'] else '扭矩' if ch==cfg['torque_channel'] else '力規'
            self.force_titles[ch].configure(text=f'CH{ch} · {role}')
            d=data.get(f'force CH{ch}',{});age=now-d.get('received',-1e30)
            status='即時' if force_state=='reading' and age<=2 else '資料過期' if force_state=='reading' else '通訊異常' if force_state=='error' else '停止讀取／保留值' if d else '尚未讀取'
            value=d.get('scaled_value');unit=d.get('unit',cfg[f'unit{ch}'])
            factor=factors.get({'推力':'thrust','扭矩':'torque'}.get(role),1)
            has_value=value not in ('',None)
            numeric=value*factor if has_value else d.get('raw_signed_int32')
            self.force_cards[ch].set(pretty(numeric,3)+' '+unit if has_value else '— '+unit)
            self.force_raw[ch].set('原量測 '+pretty(value,3)+' '+unit if has_value else
                                   '原始計數 '+pretty(d.get('raw_signed_int32'),0))
            source=(d.get('scale'),d.get('raw_zero'),unit,role,factor)
            if d and force_state=='reading' and age<=2:self.force_trends[ch].push(d['received'],numeric,source=source,gap=max(2.,cfg['force_interval']*3),label=(unit if value not in ('',None) else 'count')+' · 30s')
            else:self.force_trends[ch].draw()
            self.force_fresh[ch].set(status+(f' · {age:.1f}s 前' if d and age<10000 else ''))
        p=data.get('psu CH1',{});fresh=cfg.get('psu_enabled',False) and now-p.get('received',-1e30)<=max(5.,cfg.get('psu_interval',1.)*3);note='（保留）' if p and not fresh else ''
        for key,source,unit in [('amps','supply_A','A'),('wi','supply_W','W'),('supply','supply_V','V')]:self.readings[key].set(pretty(p.get(source))+' '+unit+note)
        self.readings['limits'].set(pretty(p.get('supply_set_V'))+' V / '+pretty(p.get('supply_limit_A'))+' A'+note)
        cc=p.get('supply_current_limited');self.readings['cc'].set(('● CC 限流' if cc==1 else 'CV／未限流' if cc==0 else '—')+note)
        thrust=data.get('force CH'+str(cfg['thrust_channel']),{});gf=thrust.get('force_gf');w=p.get('supply_W')
        eff=gf*factors.get('thrust',1)/w if fresh and force_state=='reading' and now-thrust.get('received',-1e30)<=2 and gf is not None and w is not None and w>0 else None
        self.readings['eff'].set(pretty(eff)+' gf/W · 即時估算' if eff is not None else '— gf/W')
        self.readings['coil'].set('— / — °C · 尚未接入')
        if hasattr(self,'psu_extra'):
            q=data.get('psu CH2',{})
            if not cfg.get('psu_enabled') or 2 not in cfg.get('psu_channels',[1]):text='電供 CH2：未啟用擷取'
            elif not q:text='電供 CH2：等待讀值'
            else:
                state='即時' if now-q.get('received',-1e30)<=max(5.,cfg.get('psu_interval',1.)*3) else '資料過期'
                cc2=q.get('supply_current_limited')
                text='電供 CH2：'+pretty(q.get('supply_V'))+' V ｜ '+pretty(q.get('supply_A'))+' A ｜ '+pretty(q.get('supply_W'))+' W ｜ 設定 '+pretty(q.get('supply_set_V'))+' V / '+pretty(q.get('supply_limit_A'))+' A ｜ '+('CC' if cc2==1 else 'CV／未限流' if cc2==0 else '狀態未知')+' ｜ '+state
            self.psu_extra.set(text)
