"""Display-only nominal speed schedule; no motion or configuration mutation."""
import tkinter as tk
from tkinter import ttk
from notices import ABORTS, outcome_label

def plan_segments(cfg):
    """Configured timed portions only. Variable waits have no invented duration."""
    segments=[dict(kind='baseline',label='啟動前記錄',duration=cfg['baseline_s'],speed=0),
              dict(kind='wait',label='啟動／確認',duration=None,speed=1500)]
    for i,rpm in enumerate(cfg['speeds'],1):
        segments.extend([dict(kind='ramp',label=f'{i}. 變速',duration=cfg['ramp_ms']/1000,speed=rpm),
                         dict(kind='dwell',label=f'{i}. {rpm} rpm',duration=cfg['dwell_s'],speed=rpm)])
    segments.extend([dict(kind='wait',label='停止確認',duration=None,speed=0),
                     dict(kind='poststop',label='停機後記錄',duration=cfg['poststop_s'],speed=0)])
    return segments

def run_notice(busy,phase,remaining,ended=False,reason='',report_state=''):
    if busy:
        if phase=='poststop':return ('停機後記錄中',f'停機後記錄剩餘 {max(0,remaining):.1f} 秒，請在記錄完成且確認馬達停穩後拆卸設備。','#fff7ed','#9a3412')
        if phase=='stopping':return ('實驗中 · 正在確認停止狀態','尚未完成記錄，後續仍有停機後記錄。','#fff7ed','#9a3412')
        return ('量測中','測試期間請持續監看。馬達停止後仍會繼續記錄。','#eff6ff','#1d4ed8')
    if ended:
        if reason=='sequence_complete':return ('記錄完成 · 請目視確認馬達停穩',report_state or '量測資料已儲存。力規仍持續監看。','#f0fdf4','#166534')
        return ('量測中止' if reason in ABORTS else '量測異常中止',outcome_label(reason)+'。請確認馬達已停穩。'+(' '+report_state if report_state else ''),'#fef2f2','#991b1b')
    return ('待命 · 尚未記錄','開始測試後才保存本次實驗資料。','#f8fafc','#475569')

class PlanPreview(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.cfg=None
        self.note=tk.StringVar()
        ttk.Label(self,text='轉速與時間規劃（示意）',font=('',10,'bold')).pack(anchor='w')
        self.canvas=tk.Canvas(self,height=150,background='white',highlightthickness=0)
        self.canvas.pack(fill='x',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        ttk.Label(self,textvariable=self.note,wraplength=680,foreground='#64748b').pack(anchor='w')
    def update_plan(self,cfg):
        self.cfg=dict(cfg);self.draw()
    def invalid(self):
        self.cfg=None;self.canvas.delete('all');self.note.set('請輸入有效的轉速與時間，預覽尚未套用至實驗設定。')
    def draw(self):
        c=self.canvas;c.delete('all')
        if self.cfg is None:return
        segments=plan_segments(self.cfg);total=sum(s['duration'] or 0 for s in segments)
        w=max(360,c.winfo_width());h=150;left=52;right=w-16;top=24;bottom=112
        high=max(1500,*self.cfg['speeds'])*1.12
        # Give short ramps visible width; the chart is explicitly schematic, not a timed prediction.
        widths=[max(s['duration'] if s['duration'] is not None else total/12,max(total/60,1)) for s in segments];extent=sum(widths)
        x=left;previous=0
        c.create_line(left,top,left,bottom,right,bottom,fill='#cbd5e1')
        c.create_text(4,top,anchor='w',text='rpm',fill='#64748b')
        for s,portion in zip(segments,widths):
            end=x+(right-left)*portion/extent;y=bottom-(bottom-top)*s['speed']/high
            color='#eaf3ff' if s['kind']=='dwell' else '#f1f5f9' if s['kind'] in ('baseline','poststop') else '#fff7ed'
            c.create_rectangle(x,top,end,bottom,fill=color,outline='white')
            py=bottom-(bottom-top)*previous/high
            if s['kind']=='ramp':c.create_line(x,py,end,y,fill='#2563eb',width=2)
            else:
                c.create_line(x,py,x,y,end,y,fill='#2563eb',width=2)
                if end-x>60:c.create_text((x+end)/2,top+12,text=s['label'] if s['kind']=='wait' else (str(s['speed'])+' rpm') if s['speed'] else s['label'],fill='#334155',font=('',8))
                if end-x>44:c.create_text((x+end)/2,bottom+13,text='不定' if s['duration'] is None else f"{s['duration']:g}s",fill='#64748b',font=('',8))
            x=end;previous=s['speed']
        self.note.set(f"固定記錄合計 {self.cfg['baseline_s']+len(self.cfg['speeds'])*self.cfg['dwell_s']+self.cfg['poststop_s']:g}s；每組變速命令 {self.cfg['ramp_ms']/1000:g}s。\n圖為順序示意、短變速段放寬顯示，非等比例時間軸。另有感測器檢查、先啟動至1500 rpm、到速連續2秒確認與停止確認；實際總時間較長。")
