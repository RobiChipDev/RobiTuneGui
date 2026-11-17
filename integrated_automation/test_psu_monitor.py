import csv,queue,tempfile,time,unittest,threading
from config import defaults
from controller import Controller
from devices import SupplyDevice
from test_v03 import FakeMotor,SupplyTransport
class Supply:
 identity='GW INSTEK,GPP-6030,MOCK,1'
 def __init__(self,cfg):self.cfg=cfg;self.closed=False;self.fail=False
 def read(self,emit,stop):
  if self.fail:raise TimeoutError('injected')
  for ch in self.cfg['psu_channels']:
   now=time.monotonic();emit(dict(device='psu',channel=ch,receive_mono=now,request_start_mono=now,supply_V=24.,supply_A=1.,supply_W=24.))
 def close(self):self.closed=True
class PsuMonitorTests(unittest.TestCase):
 def setUp(self):
  self.devices=[];self.motor=FakeMotor();self.overlap=False
  def factory(c):
   if any(not d.closed for d in self.devices):self.overlap=True
   d=Supply(c);self.devices.append(d);return d
  self.w=Controller(lambda p:self.motor,{'psu':factory})
  self.c=dict(defaults(),force_enabled=False,psu_enabled=True,psu_resource='COM7',psu_interval=.2)
 def tearDown(self):
  self.w.quit_event.set();self.w.join(5);self.assertFalse(self.w.is_alive())
  self.assertTrue(all(d.closed for d in self.devices));self.assertFalse(self.overlap)
 def wait(self,p,timeout=12):
  until=time.monotonic()+timeout
  while time.monotonic()<until:
   if p():return
   time.sleep(.01)
  self.fail('condition timeout')
 def start(self):
  self.w.submit('psu_apply',('REAL',self.c));self.wait(lambda:('psu','1','supply_V') in self.w.latest)
 def test_idle_without_motor_files_and_reapply_reuses(self):
  self.start();worker=self.w.psu_worker
  self.assertIsNone(self.w.motor);self.assertIsNone(self.w.file);self.assertEqual(self.motor.starts,0)
  self.w.submit('psu_apply',('REAL',self.c));time.sleep(.3)
  self.assertIs(self.w.psu_worker,worker);self.assertEqual(len(self.devices),1)
 def test_ch2_switch_and_disable_release(self):
  self.start();self.w.submit('psu_apply',('REAL',dict(self.c,psu_channels=[1,2])))
  self.wait(lambda:('psu','2','supply_V') in self.w.latest);self.assertEqual(len(self.devices),2)
  self.w.submit('psu_apply',('REAL',dict(self.c,psu_enabled=False)));self.wait(lambda:self.w.psu_worker is None)
 def test_simulation_no_open(self):
  self.w.submit('psu_apply',('SIMULATION',self.c));time.sleep(.3);self.assertEqual(self.devices,[])
 def test_error_retry(self):
  self.start();self.devices[0].fail=True;self.wait(lambda:self.w.psu_worker is None)
  self.w.submit('psu_apply',('REAL',self.c));self.wait(lambda:len(self.devices)==2)
 def test_session_and_stop_disconnect_preserve_monitor(self):
  with tempfile.TemporaryDirectory() as folder:
   self.c.update(folder=folder,ramp_ms=500,dwell_s=.5,baseline_s=1.,poststop_s=1.,reach_timeout_s=6.,speeds=[1500])
   self.start();old=self.w.psu_worker
   self.w.submit('connect',('REAL','COM5'));self.wait(lambda:self.w.motor is not None)
   self.w.submit('begin',self.c);self.wait(lambda:self.w.file is not None);path=self.w.path
   deadline=time.monotonic()+12
   while True:
    k,v=self.w.events.get(timeout=max(.01,deadline-time.monotonic()))
    if k=='finished':break
    if time.monotonic()>deadline:self.fail('no finished')
   self.assertIs(self.w.psu_worker,old);self.assertTrue(old.is_alive())
   with path.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
   power=[r for r in rows if r['device']=='psu' and r['row_type']=='measurement']
   self.assertTrue(power);self.assertTrue(all(r['channel']=='1' for r in power));self.assertTrue(all(float(r['elapsed_s'])>=0 for r in power))
   self.w.stop_event.set();time.sleep(.3);self.assertTrue(old.is_alive())
   self.w.submit('disconnect');self.wait(lambda:self.w.motor is None);self.assertTrue(old.is_alive())
 def test_adapter_only_selected_channels(self):
  for channels in ([1],[1,2]):
   t=SupplyTransport();d=SupplyDevice(dict(self.c,psu_channels=channels),t);rows=[]
   d.read(rows.append,threading.Event());d.close()
   self.assertEqual({r['channel'] for r in rows},set(channels));self.assertEqual(len(rows),6*len(channels))
   self.assertTrue(all(q.endswith('?') for q in t.queries))
