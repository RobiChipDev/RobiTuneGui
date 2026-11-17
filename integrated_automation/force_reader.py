"""RDT-T2S read-only Modbus RTU tester. Only function 03 is implemented.
Manual pp10,28,29: start 450/452, signed int32, selectable word order.
Raw values are NOT labelled as N/Nm until the user verifies scaling/mapping.
"""
import csv
import math
import queue
import struct
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

def crc16(data):
    crc=0xffff
    for b in data:
        crc ^= b
        for _ in range(8):crc=(crc>>1)^0xa001 if crc&1 else crc>>1
    return struct.pack('<H',crc)

def read_request(address,register):
    if not 1<=address<=247 or register not in (450,452):
        raise ValueError('Only station 1–247 and measurement registers 450/452 are allowed')
    p=struct.pack('>BBHH',address,3,register,2)
    return p+crc16(p)

def decode_response(data,address,word_order='HH-LL'):
    if len(data)<5 or data[:1]!=bytes([address]):raise ValueError('回應長度或站號不符')
    if crc16(data[:-2])!=data[-2:]:raise ValueError('CRC 錯誤')
    if data[1]==0x83:raise ValueError('Modbus exception 0x%02X'%data[2])
    if len(data)!=9 or data[1:3]!=b'\x03\x04':raise ValueError('回應格式不符')
    p=data[3:7]
    if word_order=='LL-HH':p=p[2:]+p[:2]
    elif word_order!='HH-LL':raise ValueError('Unknown word order')
    return struct.unpack('>i',p)[0]

def read_channel(ser,address,register,order,stop=None):
    # Use separate known-good manual requests instead of guessing bulk register layout.
    request=read_request(address,register)
    ser.reset_input_buffer()
    start=time.monotonic()
    if stop and stop.is_set():raise InterruptedError('力規讀取已取消')
    written=ser.write(request)
    if written is not None and written!=len(request):raise IOError('力規請求未完整送出')
    response=bytearray();expected=3;deadline=start+.8
    while len(response)<expected:
        if stop and stop.is_set():raise InterruptedError('力規讀取已取消')
        if time.monotonic()>deadline:
            raise TimeoutError('無完整回應；RX='+response.hex(' ').upper())
        response.extend(ser.read(expected-len(response)))
        if len(response)==3:
            if response[1]==0x83:expected=5
            elif response[1]==3 and response[2]==4:expected=9
            else:raise ValueError('非預期回應：'+response.hex(' ').upper())
    end=time.monotonic()
    return decode_response(bytes(response),address,order),start,end,bytes(response)

class Reader:
    def __init__(self,root):
        self.root=root;self.q=queue.Queue();self.stop=threading.Event();self.thread=None
        root.title('Robi 力規 RS485 唯讀測試');root.geometry('860x700')
        box=ttk.Frame(root,padding=16);box.pack(fill='both',expand=True)
        ttk.Label(box,text='RDT-T2S 雙通道唯讀擷取',font=('',18,'bold')).pack(anchor='w')
        ttk.Label(box,text='只發送 03 讀取；不改參數、不歸零、不校正。請先核對設備 F7 實際設定。').pack(anchor='w',pady=8)
        form=ttk.Frame(box);form.pack(fill='x');self.vars={};self.inputs=[]
        defaults=[('port','COM 埠','COM6'),('baud','鮑率','9600'),('addr','站號','1'),
                  ('parity','校驗 N/E/O','N'),('stopbits','停止位元 1/2','1'),
                  ('order','字序 HH-LL / LL-HH','HH-LL'),('interval','每組讀取間隔 (秒)','0.1'),
                  ('scale1','CH1 倍率（未確認留空）',''),('scale2','CH2 倍率（未確認留空）',''),
                  ('folder','輸出資料夾',str(Path.home()/'Documents'/'RobiForceLogs'))]
        for i,(key,label,value) in enumerate(defaults):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',pady=3)
            var=tk.StringVar(value=value);self.vars[key]=var
            ent=ttk.Entry(form,textvariable=var,width=62);ent.grid(row=i,column=1,sticky='ew',padx=8,pady=3)
            self.inputs.append(ent)
        form.columnconfigure(1,weight=1)
        row=ttk.Frame(box);row.pack(fill='x',pady=10)
        self.btn=ttk.Button(row,text='開始讀取並存 CSV',command=self.start);self.btn.pack(side='left')
        ttk.Button(row,text='停止擷取',command=self.stop.set).pack(side='left',padx=10)
        self.value=tk.StringVar(value='CH1 原始值：—     CH2 原始值：—')
        ttk.Label(box,textvariable=self.value,font=('',14,'bold')).pack(anchor='w',pady=8)
        self.log=tk.Text(box,height=10,wrap='word');self.log.pack(fill='both',expand=True)
        ttk.Label(box,text='本工具不連 COM5、不控制馬達。顯示原始值不等於推力／扭矩。').pack(anchor='w',pady=5)
        root.after(100,self.poll);root.protocol('WM_DELETE_WINDOW',self.close)

    def start(self):
        if self.thread and self.thread.is_alive():return
        try:
            c={k:v.get().strip() for k,v in self.vars.items()}
            c['baud']=int(c['baud']);c['addr']=int(c['addr']);c['stopbits']=int(c['stopbits'])
            c['interval']=float(c['interval']);c['parity']=c['parity'].upper()
            c['order']=c['order'].upper()
            if c['baud'] not in (1200,2400,4800,9600,19200,38400,57600,115200):raise ValueError('鮑率不在手冊範圍')
            if c['parity'] not in ('N','E','O') or c['stopbits'] not in (1,2):raise ValueError('校驗／停止位元無效')
            if not math.isfinite(c['interval']) or not .05<=c['interval']<=10:raise ValueError('間隔須介於 0.05–10 秒')
            if c['order'] not in ('HH-LL','LL-HH'):raise ValueError('字序需 HH-LL 或 LL-HH')
            if not c['folder']:raise ValueError('輸出資料夾不可空白')
            for k in ('scale1','scale2'):
                c[k]=None if not c[k] else float(c[k])
                if c[k] is not None and (not math.isfinite(c[k]) or c[k]<=0):raise ValueError('倍率需為正數')
            read_request(c['addr'],450)
        except Exception as e:messagebox.showerror('設定錯誤',str(e));return
        self.stop.clear();self.btn.configure(state='disabled')
        for ent in self.inputs:ent.configure(state='disabled')
        self.thread=threading.Thread(target=self.acquire,args=(c,),daemon=True);self.thread.start()

    def acquire(self,c):
        ser=None
        try:
            import serial
            ser=serial.Serial(c['port'],c['baud'],bytesize=8,parity=c['parity'],
                              stopbits=c['stopbits'],timeout=.03,write_timeout=.5)
            folder=Path(c['folder']);folder.mkdir(parents=True,exist_ok=True)
            path=folder/('force_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.csv')
            origin=time.monotonic()
            self.q.put(('log','輸出：'+str(path)))
            self.q.put(('log','TX CH1: '+read_request(c['addr'],450).hex(' ').upper()))
            self.q.put(('log','TX CH2: '+read_request(c['addr'],452).hex(' ').upper()))
            fields=['utc_time','elapsed_s','channel','request_start_s','receive_s','roundtrip_ms',
                    'raw_signed_int32','scale','scaled_value','unit','rx_hex','error']
            with path.open('x',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
                failed=0
                while not self.stop.is_set():
                    tick=time.monotonic();values={}
                    for channel,reg in ((1,450),(2,452)):
                        if self.stop.is_set():break
                        row=dict(utc_time=datetime.now(timezone.utc).isoformat(),
                                 elapsed_s=round(time.monotonic()-origin,6),channel=channel)
                        try:
                            raw,a,b,rx=read_channel(ser,c['addr'],reg,c['order'])
                            scale=c['scale'+str(channel)]
                            scaled='' if scale is None else raw*scale
                            row.update(utc_time=datetime.now(timezone.utc).isoformat(),elapsed_s=round(b-origin,6),
                                request_start_s=round(a-origin,6),receive_s=round(b-origin,6),
                                roundtrip_ms=round((b-a)*1000,3),raw_signed_int32=raw,
                                scale='' if scale is None else scale,scaled_value=scaled,rx_hex=rx.hex(' ').upper())
                            values[channel]=(raw,scaled);failed=0
                        except Exception as e:
                            failed+=1;row['error']=str(e)
                            self.q.put(('log',f'CH{channel}: {e}'))
                        writer.writerow(row);f.flush()
                        # At 9600 8N1 Modbus RTU requires ~3.65 ms silent gap.
                        self.stop.wait(max(.004, 3.5*11/c['baud']))
                    self.q.put(('values',values))
                    if failed>=6:raise RuntimeError('連續無有效回應，已停止；核對 F7 與接線')
                    self.stop.wait(max(0,c['interval']-(time.monotonic()-tick)))
            self.q.put(('log','擷取結束，CSV 已保存。'))
        except Exception as e:self.q.put(('log','錯誤：'+str(e)))
        finally:
            if ser:ser.close()
            self.q.put(('done',None))

    def poll(self):
        while True:
            try:k,v=self.q.get_nowait()
            except queue.Empty:break
            if k=='log':self.log.insert('end',v+'\n');self.log.see('end')
            elif k=='values':
                text=[]
                for channel in (1,2):
                    x=v.get(channel)
                    text.append(f'CH{channel}: 無有效資料' if x is None else
                        f'CH{channel} 原始={x[0]}'+('' if x[1]=='' else f' 換算={x[1]:.6g}'))
                self.value.set('    |    '.join(text))
            elif k=='done':
                self.btn.configure(state='normal')
                for ent in self.inputs:ent.configure(state='normal')
        self.root.after(100,self.poll)
    def close(self):
        self.stop.set();self.root.after(100,self.wait_close)
    def wait_close(self):
        if self.thread and self.thread.is_alive():self.root.after(100,self.wait_close)
        else:self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();Reader(root);root.mainloop()
