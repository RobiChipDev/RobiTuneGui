import csv
import struct
import tempfile
import time
import unittest
from pathlib import Path
from protocol import Motor, ProtocolError, header, ramp_payload
from config import defaults
from controller import Controller, validate_plan

class FakeSerial:
    """Deterministic board emulator; literal register IDs derived from firmware."""
    def __init__(self):
        self.buffer=bytearray();self.writes=[];self.closed=False
        self.pending=None;self.target=1500;self.duration=3000;self.reject=False;self.corrupt=False
    def reset_input_buffer(self):self.buffer.clear()
    def close(self):self.closed=True
    def read(self,n):
        n=min(n,2) # force fragmented packet delivery
        out=bytes(self.buffer[:n]);del self.buffer[:n];return out
    def write(self,b):
        self.writes.append(b)
        if self.pending is not None:
            word=self.pending;self.pending=None;kind=9
            b=header(word)+b
        else:
            word=struct.unpack('<I',b[:4])[0];kind=word&15
            if kind==9:
                assert len(b)==4, 'DMA requires separate header and payload writes'
                self.pending=word
                return
        if kind==5:self.buffer.extend(header(word))
        elif kind==6:self.buffer.extend(header(0x36))
        else:
            payload=b[4:];cmd=struct.unpack('<H',payload[:2])[0]
            reply=b''
            if cmd==0x11:
                if payload[2:]==bytes.fromhex('490019005900990089009105d105591bd1081109'):
                    reply=struct.pack('<BIiiBHhfhh',0,0,-1200,1998,3,24,-2,12.5,-200,300)
                elif payload[2:]==bytes.fromhex('2901'):
                    reply=struct.pack('<Hfff',12,.0004,.001,6.)
                elif payload[2:]==bytes.fromhex('a901'):
                    reply=struct.pack('<HiH',6,self.target,self.duration)
                else:raise AssertionError('Unexpected register IDs')
            elif cmd==9:
                assert payload[2:6]==bytes.fromhex('a9010600')
                self.target,self.duration=struct.unpack('<iH',payload[6:])
            elif cmd not in (0x19,0x21,0x39):raise AssertionError('Unexpected command')
            reply+=b'\x01' if self.reject else b'\x00'
            hdr=bytearray(header(10|len(reply)<<4))
            if self.corrupt:hdr[3]^=0x10
            self.buffer.extend(hdr+reply)

class ProtocolTests(unittest.TestCase):
    def test_golden_payload(self):
        self.assertEqual(ramp_payload(1500,3000).hex(),'0900a9010600dc050000b80b')
        self.assertEqual(header(6).hex(),'06000060')
    def test_handshake_read_ramp_and_stop(self):
        s=FakeSerial();m=Motor('',serial_instance=s)
        sample=m.sample()
        self.assertEqual(sample['mode'],3)
        self.assertEqual(sample['board_temp_C'],-2)
        self.assertEqual(sample['motor_power_W'],12.5)
        self.assertAlmostEqual(sample['iq_A'],-.2,places=6)
        self.assertEqual(sample['rpm'],-1200)
        m.ramp(1500,3000);m.start();m.stop();m.ack()
        self.assertEqual(s.writes[-1],b'\x39\x00')
    def test_rejection_and_crc(self):
        s=FakeSerial();m=Motor('',serial_instance=s);s.reject=True
        with self.assertRaises(ProtocolError):m.start()
        s.reject=False;s.corrupt=True
        with self.assertRaises(ProtocolError):m.sample()
    def test_timeout_identifies_beacon_and_closes_port(self):
        class Silent(FakeSerial):
            def read(self,n):
                time.sleep(.01)
                return b''
        s=Silent()
        with self.assertRaisesRegex(ProtocolError, 'BEACON negotiation 1.*received 0/4') as cm:
            Motor('',serial_instance=s)
        self.assertTrue(s.closed)
        self.assertEqual(len(s.writes),1)  # no blind retries
        self.assertIn('TX',str(cm.exception))

    def test_timeout_identifies_first_read_without_motion(self):
        class MissingScale(FakeSerial):
            def write(self,b):
                result=super().write(b)
                if b==bytes.fromhex('11002901'):self.buffer.clear()
                return result
            def read(self,n):
                if not self.buffer:time.sleep(.01)
                return super().read(n)
        s=MissingScale()
        with self.assertRaisesRegex(ProtocolError,'MCP request 11 00 29 01.*received 0/4'):
            Motor('',serial_instance=s)
        self.assertTrue(s.closed)
        self.assertEqual(s.writes[-1],bytes.fromhex('11002901'))

    def test_limits(self):
        for rpm,ms in [(-1,3000),(1500,65536)]:
            with self.assertRaises(ValueError):ramp_payload(rpm,ms)
        c=defaults();c.update(speeds=[960],max_rpm=2600,ramp_ms=3000,dwell_s=30,reach_timeout_s=30)
        validate_plan(c)
        for key,val in [('speeds',[3000]),('dwell_s',float('nan')),('reach_timeout_s',2)]:
            with self.assertRaises(ValueError):validate_plan(dict(c,**{key:val}))

