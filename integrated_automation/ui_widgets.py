"""Code-native rounded widgets and truthful, display-only mini trends."""
import math,time
from collections import deque
import tkinter as tk
from tkinter import ttk


def rounded(canvas,x1,y1,x2,y2,r=14,**options):
    r=max(1,min(r,(x2-x1)/2,(y2-y1)/2))
    return canvas.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1,smooth=True,splinesteps=20,**options)

class RoundPanel(ttk.Frame):
    def __init__(self,parent,text='',padding=10,**kwargs):
        super().__init__(parent,**kwargs)
        self.border=tk.Canvas(self,background='white',highlightthickness=0,bd=0)
        self.border.place(x=0,y=0,relwidth=1,relheight=1)
        self.inner=ttk.Frame(self);self.inner.pack(fill='both',expand=True,padx=padding+2,pady=padding)
        self.caption=ttk.Label(self.inner,text=text,font=('Microsoft JhengHei UI',9,'bold'),foreground='#475569');self.caption.pack(anchor='w',pady=(0,5))
        self.body=ttk.Frame(self.inner);self.body.pack(fill='both',expand=True)
        self.bind('<Configure>',self._draw)
    def _draw(self,event=None):
        self.border.delete('all');w=self.winfo_width();h=self.winfo_height()
        if w>4 and h>4:rounded(self.border,1,1,w-2,h-2,16,fill='white',outline='#dfe5ec',width=1)
    def configure(self,cnf=None,**kwargs):
        if isinstance(cnf,dict):kwargs=dict(cnf,**kwargs);cnf=None
        if 'text' in kwargs:self.caption.configure(text=kwargs.pop('text'))
        if 'padding' in kwargs:
            value=kwargs.pop('padding');self.inner.pack_configure(padx=value+2,pady=value)
        return super().configure(cnf,**kwargs)
    config=configure

class PillButton(tk.Canvas):
    def __init__(self,parent,text='',command=None,role='normal',width=175,height=32,**kw):
        self.text=text;self.command=command;self.role=role;self.ui_state='normal';self.hover=False;self.focused=False
        super().__init__(parent,width=width,height=height,background='white',highlightthickness=0,bd=0,takefocus=1,**kw)
        self.bind('<Configure>',lambda e:self.draw());self.bind('<Button-1>',self.invoke)
        self.bind('<Return>',self.invoke);self.bind('<space>',self.invoke)
        self.bind('<Enter>',lambda e:self.set_hover(True));self.bind('<Leave>',lambda e:self.set_hover(False))
        self.bind('<FocusIn>',lambda e:self.set_focus(True));self.bind('<FocusOut>',lambda e:self.set_focus(False))
        self.draw()
    def set_hover(self,value):self.hover=value;self.draw()
    def set_focus(self,value):self.focused=value;self.draw()
    def invoke(self,event=None):
        if self.ui_state!='disabled' and self.command:
            self.focus_set();self.command()
        return 'break'
    def configure(self,cnf=None,**kwargs):
        if isinstance(cnf,dict):kwargs=dict(cnf,**kwargs);cnf=None
        if 'text' in kwargs:self.text=kwargs.pop('text')
        if 'state' in kwargs:self.ui_state=kwargs.pop('state')
        if 'command' in kwargs:self.command=kwargs.pop('command')
        if 'role' in kwargs:self.role=kwargs.pop('role')
        result=super().configure(cnf,**kwargs)
        if hasattr(self,'ui_state'):self.draw()
        return result
    config=configure
    def draw(self):
        self.delete('all');w=max(12,self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')));h=max(12,self.winfo_height() if self.winfo_height()>1 else int(self.cget('height')))
        dark=self.role in ('primary','mode');danger=self.role in ('danger','mode_locked');disabled=self.ui_state=='disabled'
        bg='#b91c1c' if danger else '#17212f' if dark else '#f8fafc' if self.hover else 'white'
        fg='white' if danger or dark else '#273344';outline=bg if danger or dark else '#dce3eb'
        if disabled and self.role not in ('mode','mode_locked'):bg='#f6f7f9';fg='#a6afb9';outline='#e4e8ee'
        rounded(self,1,1,w-2,h-2,11,fill=bg,outline='#64748b' if self.focused else outline,width=2 if self.focused else 1)
        self.create_text(w/2,h/2,text=self.text,fill=fg,font=('Microsoft JhengHei UI',10 if self.role in ('mode','mode_locked') else 9,'bold' if dark or danger else 'normal'))
        self.configure_cursor()
    def configure_cursor(self):super().configure(cursor='arrow' if self.ui_state=='disabled' else 'hand2')

class TrendSeries:
    def __init__(self,seconds=30,maxlen=1200):self.seconds=seconds;self.points=deque(maxlen=maxlen);self.last_stamp=None;self.source=None
    def clear(self):self.points.clear();self.last_stamp=None
    def add(self,stamp,value,source=None):
        try:stamp=float(stamp);value=float(value)
        except (TypeError,ValueError):return False
        if not math.isfinite(stamp) or not math.isfinite(value):return False
        if source!=self.source:self.clear();self.source=source
        if self.last_stamp is not None and stamp<=self.last_stamp:return False
        self.last_stamp=stamp;self.points.append((stamp,value))
        while self.points and self.points[0][0]<stamp-self.seconds:self.points.popleft()
        return True

class Sparkline(tk.Canvas):
    def __init__(self,parent,height=48):
        super().__init__(parent,width=180,height=height,background='white',highlightthickness=0)
        self.series=TrendSeries();self.gap=2.;self.label='最近 30 秒';self.bind('<Configure>',lambda e:self.draw())
    def push(self,stamp,value,source=None,gap=2.,label=None):
        if label is not None:self.label=label
        self.gap=gap;self.series.add(stamp,value,source);self.draw()
    def draw(self):
        self.delete('all');w=max(80,self.winfo_width());h=max(20,self.winfo_height());left=44;right=w-6;top=6;bottom=max(12,h-17)
        now=time.monotonic();points=[p for p in self.series.points if p[0]>=now-30]
        for frac in (.15,.5,.85):self.create_line(left,top+(bottom-top)*frac,right,top+(bottom-top)*frac,fill='#eef1f5')
        if not points:
            self.create_text(w/2,h/2,text='等待讀值 · 最近 30 秒',font=('',8),fill='#9aa4b2');return
        low=min(v for _,v in points);high=max(v for _,v in points);span=high-low
        if span==0:span=max(abs(high)*.03,1. if self.label.startswith(('rpm','count')) else .002);low-=span/2;high+=span/2
        else:low-=span*.08;high+=span*.08
        high_text=f'{high:.0f}' if abs(high)>=100 else f'{high:.3g}'
        low_text=f'{low:.0f}' if abs(low)>=100 else f'{low:.3g}'
        if self.label.startswith('rpm') and all(v>=0 for _,v in points):low=max(0.,low)
        if high<=low:high=low+1
        self.create_text(right,h-2,text=self.label,anchor='se',font=('',7),fill='#94a0af')
        self.create_text(left-3,top,text=high_text,anchor='e',font=('',7),fill='#94a0af')
        self.create_text(left-3,bottom,text=low_text,anchor='e',font=('',7),fill='#94a0af')
        def xy(t,v):return left+(t-(now-30))/30*(right-left),bottom-(v-low)/(high-low)*(bottom-top)
        segments=[];segment=[];previous=None
        for stamp,value in points:
            if previous is not None and stamp-previous>self.gap:
                if segment:segments.append(segment)
                segment=[]
            segment.extend(xy(stamp,value));previous=stamp
        if segment:segments.append(segment)
        for segment in segments:
            if len(segment)>=4:self.create_line(*segment,fill='#475569',width=1.7)
        x,y=xy(*points[-1]);self.create_oval(x-2,y-2,x+2,y+2,fill='#334155',outline='')
