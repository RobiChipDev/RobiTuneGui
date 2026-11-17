"""Read-only device adapters. A transport has exactly one owning worker."""
import math
import re
import time
from force_reader import read_channel
from units import normalize_force


def finite(value):
    x=float(value)
    if not math.isfinite(x) or abs(x)>1e30:raise ValueError('Invalid numeric instrument reply')
    return x


class ForceDevice:
    def __init__(self,cfg):
        import serial
        self.cfg=cfg
        self.ser=serial.Serial(cfg['force_port'],cfg['force_baud'],bytesize=8,
            parity=cfg['force_parity'],stopbits=cfg['force_stopbits'],timeout=.03,write_timeout=.5)
    def read(self,emit,stop):
        for ch,reg in ((1,450),(2,452)):
            if stop.is_set():return
            raw,a,b,rx=read_channel(self.ser,self.cfg['force_addr'],reg,self.cfg['force_order'],stop=stop)
            scale=self.cfg.get('scale'+str(ch))
            zero=self.cfg.get('zero'+str(ch),0.)
            value='' if scale is None else (raw-zero)*scale
            unit=self.cfg.get('unit'+str(ch),'')
            normalized=normalize_force(value,unit)
            emit(dict(device='force',channel=ch,raw_signed_int32=raw,
                scale='' if scale is None else scale,raw_zero=zero,scaled_value=value,
                unit=unit,request_start_mono=a,receive_mono=b,rx_hex=rx.hex(' ').upper(),**normalized))
            stop.wait(.005)
    def cancel(self):
        # Cancel pending OS I/O; the owning worker alone closes the port.
        for name in ('cancel_read','cancel_write'):
            fn=getattr(self.ser,name,None)
            if fn:
                try:fn()
                except (OSError,AttributeError):pass
    def close(self):self.ser.close()


class SupplyDevice:
    """GW GPP query-only adapter; all messages pass a fixed allowlist."""
    def __init__(self,cfg,transport=None):
        self.cfg=cfg;self.rm=None;self.serial=False
        try:
            if transport is not None:self.io=transport
            elif cfg['psu_backend']=='SERIAL':
                import serial
                self.serial=True
                self.io=serial.Serial(cfg['psu_resource'],cfg['psu_baud'],timeout=3.0,write_timeout=1.0)
                # Match the successful field probe: let USB CDC settle before IDN.
                time.sleep(1.0)
                self.io.reset_input_buffer()
            else:
                import pyvisa
                self.rm=pyvisa.ResourceManager()
                self.io=self.rm.open_resource(cfg['psu_resource'],open_timeout=1500)
                self.io.timeout=800;self.io.read_termination='\n';self.io.write_termination='\n'
            self.identity=self.query('*IDN?')
            if not re.search(r'GPP[- ]?6030',self.identity,re.I):
                raise ValueError('電供型號不是 GPP-6030：'+self.identity)
        except Exception:
            self.close();raise
    def query(self,cmd):
        if cmd!='*IDN?' and not re.fullmatch(r':(?:MEAS[12]:(?:VOLT|CURR|POWE)|SOUR[12]:(?:VOLT|CURR|CURR:STAT))\?',cmd):
            raise ValueError('Only approved read-only queries are permitted')
        if self.serial:
            self.io.write((cmd+'\n').encode('ascii'));self.io.flush()
            line=self.io.read_until(b'\n',256)
            if not line.endswith(b'\n'):
                reason='no bytes received' if not line else 'incomplete reply (missing LF)'
                raise TimeoutError(f'{cmd}: {reason}; received={len(line)} bytes; raw={line!r}; hex={line.hex(" ")}')
            reply=line.decode('ascii').strip()
        else:reply=str(self.io.query(cmd)).strip()
        if not reply:raise TimeoutError('Empty supply reply')
        return reply
    def read(self,emit,stop):
        for ch in self.cfg['psu_channels']:
            for command,field in (('MEAS:VOLT','supply_V'),('MEAS:CURR','supply_A'),('MEAS:POWE','supply_W'),('SOUR:VOLT','supply_set_V'),('SOUR:CURR','supply_limit_A'),('SOUR:CURR:STAT','supply_current_limited')):
                if stop.is_set():return
                prefix,function=command.split(':',1)
                a=time.monotonic();reply=self.query(f':{prefix}{ch}:{function}?');b=time.monotonic()
                value=finite(reply)
                if field=='supply_current_limited' and value not in (0,1):raise ValueError('Invalid current limit state')
                emit(dict(device='psu',channel=ch,request_start_mono=a,receive_mono=b,
                    **{field:value},rx_text=reply))
    def close(self):
        try:
            if getattr(self,'io',None):self.io.close()
        finally:
            if self.rm:self.rm.close()
