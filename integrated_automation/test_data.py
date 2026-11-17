import csv,tempfile,unittest
from pathlib import Path
from controller import FIELDS
from summarize import summarize
from units import normalize_force,G0

class ConversionTests(unittest.TestCase):
 def test_force_units_and_signed_values(self):
  self.assertAlmostEqual(normalize_force(-1000,'gf')['force_N'],-G0)
  self.assertAlmostEqual(normalize_force(1,'kgf')['force_gf'],1000)
  self.assertAlmostEqual(normalize_force(1,'N')['force_gf'],1000/G0)
 def test_torque_units(self):
  self.assertEqual(normalize_force(1000,'N·mm')['torque_Nm'],1)
  self.assertEqual(normalize_force(-1,'N.m')['torque_Nm'],-1)
  self.assertAlmostEqual(normalize_force(1,'kgf·cm')['torque_Nm'],.0980665)
 def test_unknown_units_and_scale_remain_blank(self):
  self.assertEqual(normalize_force('', 'N'),{})
  self.assertEqual(normalize_force(10,'kg'),{})
  self.assertEqual(normalize_force(10,''),{})
  with self.assertRaises(ValueError):normalize_force(float('nan'),'N')

class AdapterTests(unittest.TestCase):
 def test_force_adapter_records_normalized_units(self):
  import struct,threading,types
  from unittest.mock import patch
  from config import defaults
  from devices import ForceDevice
  from force_reader import crc16
  class Serial:
   def __init__(self,*a,**kw):self.buf=b''
   def reset_input_buffer(self):self.buf=b''
   def write(self,b):
    d=b'\x01\x03\x04'+struct.pack('>i',-1000);self.buf=d+crc16(d)
   def flush(self):pass
   def read(self,n):d,self.buf=self.buf[:n],self.buf[n:];return d
   def close(self):pass
  c=defaults();c.update(scale1=1,scale2=1,unit1='gf',unit2='Nmm')
  with patch.dict('sys.modules',{'serial':types.SimpleNamespace(Serial=Serial)}):
   d=ForceDevice(c);rows=[];d.read(rows.append,threading.Event());d.close()
  self.assertAlmostEqual(rows[0]['force_N'],-G0)
  self.assertEqual(rows[1]['torque_Nm'],-1)
 def test_nonfinite_motor_power_rejected(self):
  import struct
  from protocol import Motor,ProtocolError
  m=object.__new__(Motor);m.current_scale=.001
  m.request=lambda p:struct.pack('<BIiiBHhfhh',0,0,0,0,3,24,25,float('nan'),0,0)
  with self.assertRaises(ProtocolError):m.sample()

class StageTableTests(unittest.TestCase):
 def build(self,d,completed=True,power=10):
  p=Path(d)/'capture.csv'
  with p.open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
   for t in (1.,2.,3.):
    base=dict(row_type='measurement',stage='dwelling',stage_index=1,target_rpm=1500,elapsed_s=t)
    w.writerow(dict(base,device='motor',estimated_rpm=1500,board_bus_V=24,board_temp_C=27,motor_power_W=8))
    w.writerow(dict(base,device='force',channel=1,raw_signed_int32=-1000,scale=1,scaled_value=-1000,unit='gf',**normalize_force(-1000,'gf')))
    w.writerow(dict(base,device='force',channel=2,raw_signed_int32=1000,scale=1,scaled_value=1000,unit='Nmm',**normalize_force(1000,'Nmm')))
    w.writerow(dict(base,device='psu',channel=1,supply_W=power,supply_A=1,supply_set_V=24,supply_limit_A=3,supply_current_limited=0))
    w.writerow(dict(base,device='psu',channel=2,supply_W=999))
   if completed:w.writerow(dict(row_type='event',elapsed_s=4,stage='dwelling',stage_index=1,target_rpm=1500,reason='stage_timed_complete'))
  return p
 def read_stage(self,p,c):
  summarize(p,c)
  return list(csv.DictReader(p.with_name(p.stem+'_stages.csv').read_text(encoding='utf-8-sig').splitlines()))[0]
 def test_mapping_efficiency_and_mixed_power_sources(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.build(d);r=self.read_stage(p,dict(thrust_channel=1,torque_channel=2))
   self.assertAlmostEqual(float(r['Fz_mean_N']),-G0)
   self.assertAlmostEqual(float(r['Tz_mean_Nm']),1)
   self.assertEqual(float(r['Wi_mean_W']),10);self.assertEqual(float(r['Wo_motorpilot_mean_W']),8)
   self.assertAlmostEqual(float(r['eff_signed_gf_per_W']),-100)
   self.assertAlmostEqual(float(r['eff_abs_gf_per_W']),100)
   self.assertEqual(r['stage_complete'],'True')
   summary=list(csv.DictReader(p.with_name(p.stem+'_summary.csv').read_text(encoding='utf-8-sig').splitlines()))
   g=next(r for r in summary if r['device']=='force' and r['channel']=='1' and r['metric']=='force_N')
   self.assertEqual(float(g['sample_rate_Hz']),1);self.assertEqual(float(g['max_gap_s']),1)
 def test_unassigned_channels_do_not_invent_Fz_or_Tz(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.read_stage(self.build(d),{})
   self.assertEqual(r['Fz_mean_N'],'');self.assertEqual(r['Tz_mean_Nm'],'');self.assertEqual(r['eff_signed_gf_per_W'],'')
   self.assertNotEqual(r['ch1_force_mean_N'],'')
 def test_zero_power_and_incomplete_stage_do_not_compute_efficiency(self):
  for completed,power in ((True,0),(False,10)):
   with tempfile.TemporaryDirectory() as d:
    r=self.read_stage(self.build(d,completed,power),dict(thrust_channel=1,torque_channel=2))
    self.assertEqual(r['eff_signed_gf_per_W'],'')
    self.assertIn('eff_not_computed',r['quality_note'])

if __name__=='__main__':unittest.main()
