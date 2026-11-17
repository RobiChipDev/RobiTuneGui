import threading
import time
from datetime import datetime,timezone
from devices import ForceDevice,SupplyDevice

class SensorWorker(threading.Thread):
    def __init__(self,name,cfg,out,overflow,factory=None):
        super().__init__(daemon=True,name=name)
        self.device=None;self.device_name=name;self.cfg=cfg;self.out=out;self.overflow=overflow
        self.stop_event=threading.Event();self.factory=factory or (ForceDevice if name=='force' else SupplyDevice)
    def request_stop(self):
        self.stop_event.set()
        dev=self.device
        if dev and hasattr(dev,'cancel'):dev.cancel()
    def emit(self,row):
        import queue
        row.setdefault('device',self.device_name)
        row.setdefault('receive_mono',time.monotonic())
        row.setdefault('utc_time',datetime.now(timezone.utc).isoformat())
        try:self.out.put_nowait(row)
        except queue.Full:self.overflow.set();self.stop_event.set()
    def run(self):
        dev=None
        try:
            dev=self.factory(self.cfg);self.device=dev
            if hasattr(dev,'identity'):self.emit(dict(row_type='identity',detail=dev.identity))
            while not self.stop_event.is_set():
                tick=time.monotonic()
                if self.device_name=='force':dev.cfg=self.cfg
                dev.read(self.emit,self.stop_event)
                self.stop_event.wait(max(0,self.cfg[self.device_name+'_interval']-(time.monotonic()-tick)))
        except Exception as e:
            if not self.stop_event.is_set():self.emit(dict(row_type='error',detail=type(e).__name__+': '+str(e)))
        finally:
            if dev:
                try:dev.close()
                except Exception as e:self.emit(dict(row_type='error',detail='close: '+str(e)))
            self.device=None
