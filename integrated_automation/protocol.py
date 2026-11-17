"""Host MCP v2 / ASPEP, grounded in supplied MCSDK 6.4.2 firmware.
No firmware files are changed. Synchronous commands only; no automatic retries.
"""
import math
from collections import deque
import struct
import time
from pid_settings import PARAMETERS, decode_value, encode_value, register

CRC4 = (0, 7, 14, 9, 11, 12, 5, 2, 1, 6, 15, 8, 10, 13, 4, 3)
STATES = {0:'IDLE', 2:'ALIGNMENT', 4:'START', 6:'RUN', 8:'STOP',
          10:'FAULT_NOW', 11:'FAULT_OVER', 12:'ICLWAIT', 16:'CHARGE_BOOT_CAP',
          17:'OFFSET_CALIB', 19:'SWITCH_OVER', 20:'WAIT_STOP_MOTOR',
          21:'OTF_DETECTION', 22:'OTF_BRAKE'}

# ID = (element << 6) | (type << 3) | motor 1; MCSDK supplied source.
REG = dict(status=0x49,faults=0x19,speed=0x59,reference=0x99,mode=0x89,
           bus_V=0x591,board_temp_C=0x5d1,motor_power_W=0x1b59,iq=0x8d1,id=0x911,scale=0x129)
TELEMETRY_FIELDS=('board_bus_V','board_temp_C','motor_power_W','iq_raw','id_raw',
                  'current_scale_A_per_count','iq_A','id_A','motor_rx_hex')

class ProtocolError(Exception):
    pass

def header(value):
    value &= 0x0fffffff
    crc = 0
    for shift in range(0, 28, 4):
        crc = CRC4[crc ^ ((value >> shift) & 15)]
    return struct.pack('<I', value | crc << 28)

def ramp_payload(rpm, duration):
    if not 0 <= rpm <= 12000 or not 0 <= duration <= 65535:
        raise ValueError('Invalid RPM or ramp duration')
    # SET_DATA_ELEMENT|motor1, SPEED_RAMP RAW|motor1, raw size, rpm, duration.
    return struct.pack('<HHHiH', 0x09, 0x1a9, 6, rpm, duration)

class Motor:
    def __init__(self, port, baud=1843200, serial_instance=None):
        self.stage = "open serial"
        self.trace = deque(maxlen=24)
        real_serial = serial_instance is None
        if serial_instance is None:
            import serial
            serial_instance = serial.Serial(port, baudrate=baud, timeout=.05,
                                            write_timeout=.5)
        self.ser = serial_instance
        self.rx_limit = 256
        try:
            if real_serial:
                time.sleep(.5)  # USB VCP line-coding settling; no command retry.
            self.ser.reset_input_buffer()
            self.trace.append("OPEN %s baud=%s 8N1" % (port, baud))
            beacon = 5 | (7 << 8) | (7 << 14)  # CRC off, 256B RX/TXS, no async
            for _ in range(3):
                self.stage = "BEACON negotiation %d" % (_ + 1)
                self.send(header(beacon))
                kind, reply = self.packet()
                if kind != 5:
                    raise ProtocolError('Expected ASPEP beacon')
                negotiated = reply & 0x0fffffff
                if (negotiated & 0xf0) != 0:
                    raise ProtocolError('Unsupported ASPEP version/data CRC')
                if negotiated == beacon:
                    break
                beacon = negotiated
            else:
                raise ProtocolError('ASPEP negotiation failed')
            self.rx_limit = (((beacon >> 8) & 63) + 1) * 32
            self.stage = "PING configuration"
            self.send(header(6))
            kind, reply = self.packet()
            if kind != 6 or reply & 0x30 != 0x30:
                raise ProtocolError('ASPEP connection not configured')
            self.stage = 'GET scale configuration'
            scales=self.request(struct.pack('<HH',0x11,REG['scale']))
            if len(scales)!=14:raise ProtocolError('Missing scale configuration')
            size,voltage,current,frequency=struct.unpack('<Hfff',scales)
            if size!=12 or any(not math.isfinite(v) or v<=0 for v in (voltage,current,frequency)):
                raise ProtocolError('Invalid firmware scale configuration')
            self.current_scale=current
            self.scale_config=dict(voltage=voltage,current=current,frequency=frequency)
        except Exception as exc:
            self.ser.close()
            raise ProtocolError(str(exc) + "\nConnection trace:\n" + "\n".join(self.trace)) from exc

    def send(self, data):
        written = self.ser.write(data)
        self.trace.append("TX " + data.hex(" ").upper())
        if written is not None and written != len(data):
            raise ProtocolError("Partial serial write at " + self.stage)

    def exact(self, n, deadline):
        data = bytearray()
        while len(data) < n:
            if time.monotonic() >= deadline:
                raise ProtocolError('Serial response timeout at %s: received %d/%d bytes [%s]; no automatic command retry' % (self.stage, len(data), n, data.hex(' ').upper()))
            chunk = self.ser.read(n - len(data))
            if chunk:
                self.trace.append("RX " + chunk.hex(" ").upper())
                data.extend(chunk)
        return bytes(data)

    def packet(self):
        deadline = time.monotonic() + 1.0
        raw = self.exact(4, deadline)
        word, = struct.unpack('<I', raw)
        if header(word) != raw:
            raise ProtocolError('ASPEP header CRC mismatch')
        kind = word & 15
        if kind in (9, 10):
            length = (word >> 4) & 0x1fff
            if length > 256:
                raise ProtocolError('Unexpected packet length')
            return kind, self.exact(length, deadline)
        if kind == 15:
            raise ProtocolError('ASPEP NACK: ' + hex(word))
        if kind not in (5, 6):
            raise ProtocolError('Unexpected ASPEP type: ' + str(kind))
        return kind, word

    def request(self, payload):
        if len(payload) > self.rx_limit:
            raise ProtocolError('Request exceeds negotiated size')
        self.stage = "MCP request " + payload[:4].hex(" ").upper()
        # Firmware arms payload DMA only after receiving/decoding the header.
        # Mirror supervisor's IntraPause; never resend a motion command.
        self.send(header(9 | len(payload) << 4))
        if hasattr(self.ser, "flush"):
            self.ser.flush()
        time.sleep(.005)
        self.send(payload)
        kind, data = self.packet()
        if kind != 10 or not data:
            raise ProtocolError('Expected synchronous MCP response')
        if data[-1] != 0:
            raise ProtocolError('MCP command rejected: 0x%02x' % data[-1])
        return data[:-1]

    def sample(self):
        regs=[REG[k] for k in ('status','faults','speed','reference','mode','bus_V','board_temp_C','motor_power_W','iq','id')]
        data=self.request(struct.pack('<11H',0x11,*regs))
        if len(data)!=26:raise ProtocolError('Unexpected telemetry length: %d'%len(data))
        state,faults,rpm,reference,mode,bus,temp,power,iq,id_=struct.unpack('<BIiiBHhfhh',data)
        if not math.isfinite(power):raise ProtocolError('Non-finite motor power reply')
        return dict(state=state,status=STATES.get(state,str(state)),faults=faults,rpm=rpm,reference=reference,mode=mode,
            board_bus_V=bus,board_temp_C=temp,motor_power_W=power,iq_raw=iq,id_raw=id_,
            current_scale_A_per_count=self.current_scale,iq_A=iq*self.current_scale,id_A=id_*self.current_scale,
            motor_rx_hex=data.hex(' ').upper())

    def read_pid(self):
        keys = tuple(PARAMETERS)
        payload = struct.pack('<' + 'H' * (len(keys) + 1), 0x11, *(register(key) for key in keys))
        reply = self.request(payload)
        if len(reply) != 2 * len(keys):
            raise ProtocolError('PID／PLL 讀回長度不符。')
        values = struct.unpack('<' + ''.join(PARAMETERS[key][2] for key in keys), reply)
        return {key: decode_value(key, value) for key, value in zip(keys, values)}

    def write_pid(self, key, value):
        encoded = encode_value(key, value)
        reply = self.request(struct.pack('<HH' + PARAMETERS[key][2], 0x09, register(key), encoded))
        if reply:
            raise ProtocolError('PID／PLL 寫入回覆格式不符。')

    def ramp(self, rpm, ms):
        self.request(ramp_payload(rpm, ms))
        data = self.request(struct.pack('<HH', 0x11, 0x1a9))
        if len(data) != 8:
            raise ProtocolError('Missing ramp readback')
        size, actual, duration = struct.unpack('<HiH', data)
        # Firmware integer speed unit quantizes RPM to multiples of 6.
        if size != 6 or abs(actual-rpm) > 5 or duration != ms:
            raise ProtocolError('Ramp readback mismatch: %s' % ((actual, duration),))

    def start(self): self.request(struct.pack('<H', 0x19))
    def stop(self): self.request(struct.pack('<H', 0x21))
    def ack(self): self.request(struct.pack('<H', 0x39))
    def close(self): self.ser.close()

class SimMotor:
    """Explicit simulation: never opens a serial port."""
    def __init__(self):
        self.state, self.rpm, self.target = 0, 0., 0
        self.t = time.monotonic()
        self.ready = 0
    def ramp(self, rpm, ms):
        self.target, self.ms = rpm, max(ms, 1)
    def start(self):
        self.state, self.ready = 4, time.monotonic()+2
    def sample(self):
        now = time.monotonic()
        dt, self.t = now-self.t, now
        if self.state == 4 and now >= self.ready: self.state = 6
        if self.state in (4, 6):
            delta = max(1, 1500*dt/(self.ms/1000))
            self.rpm += max(-delta, min(delta, self.target-self.rpm))
        else: self.rpm = 0
        return dict(state=self.state, status=STATES[self.state], faults=0,
                    rpm=round(self.rpm), reference=self.target, mode=3)
    def stop(self): self.state = 0
    def ack(self): pass
    def close(self): pass
