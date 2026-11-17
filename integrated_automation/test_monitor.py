import queue,tempfile,time,unittest
from controller import Controller
from config import defaults
from test_v03 import FakeMotor,FakeForce

class MonitorTests(unittest.TestCase):
 def wait(self,p,timeout=12):
  until=time.monotonic()+timeout
  while time.monotonic()<until:
   if p():return
   time.sleep(.01)
  self.fail('monitor condition timed out')
 def make(self):
  self.opens=0;self.devices=[]
  def factory(c):
   self.opens+=1;f=FakeForce(c);self.devices.append(f);return f
  self.motor=FakeMotor();self.w=Controller(lambda p:self.motor,{'force':factory})
 def tearDown(self):
  if hasattr(self,'w'):self.w.quit_event.set();self.w.join(3);self.assertFalse(self.w.is_alive())
 def cfg(self,folder):
  c=defaults();c.update(folder=folder,ramp_ms=500,dwell_s=.5,baseline_s=1.,poststop_s=1.,reach_timeout_s=6.,speeds=[1500],force_interval=.05);return c
 def test_idle_monitor_then_record_then_idle_reuses_same_port(self):
  self.make()
  with tempfile.TemporaryDirectory() as folder:
   c=self.cfg(folder);self.w.submit('force_start',('REAL',c));self.wait(lambda:self.w.force_state=='reading')
   force=self.w.force_worker;self.w.submit('connect',('REAL','COM5'));self.wait(lambda:self.w.motor is not None)
   self.w.submit('begin',c);self.wait(lambda:self.w.file is not None);self.wait(lambda:self.w.file is None)
   self.assertEqual(self.opens,1);self.assertIs(self.w.force_worker,force);self.assertTrue(force.is_alive());self.assertFalse(self.devices[0].closed)
   old=self.w.latest[('force','1','raw_signed_int32')];self.wait(lambda:self.w.latest[('force','1','raw_signed_int32')]>old)
 def test_apply_calibration_without_reopening_and_double_start_is_idempotent(self):
  self.make();c=defaults();self.w.submit('force_start',('REAL',c));self.wait(lambda:self.w.force_state=='reading');old=self.w.force_worker
  c=dict(c,scale2=.001,zero1=10.);self.w.submit('force_apply',c);self.wait(lambda:self.w.force_worker.cfg['zero1']==10.)
  self.w.submit('force_start',('REAL',c));time.sleep(.15)
  self.assertIs(self.w.force_worker,old);self.assertEqual(self.opens,1);self.assertEqual(self.w.force_worker.cfg['scale2'],.001)
 def test_stop_releases_and_explicit_restart_opens_once(self):
  self.make();c=defaults();self.w.submit('force_start',('REAL',c));self.wait(lambda:self.w.force_state=='reading')
  self.w.submit('force_stop');self.wait(lambda:self.w.force_state=='stopped');self.assertTrue(self.devices[0].closed)
  self.w.submit('force_start',('REAL',c));self.wait(lambda:self.w.force_state=='reading');self.assertEqual(self.opens,2)
 def test_simulation_monitor_does_not_open_physical_port(self):
  self.make();self.w.submit('force_start',('SIMULATION',defaults()));time.sleep(.2);self.assertEqual(self.opens,0)
 def test_simulation_connection_rejected_while_real_monitor_active(self):
  self.make();self.w.submit('force_start',('REAL',defaults()));self.wait(lambda:self.w.force_state=='reading')
  self.w.submit('connect',('SIMULATION','COM5'));time.sleep(.2);self.assertIsNone(self.w.motor);self.assertTrue(self.w.force_worker.is_alive())
 def test_comm_change_rejected_without_second_owner(self):
  self.make();c=defaults();self.w.submit('force_start',('REAL',c));self.wait(lambda:self.w.force_state=='reading')
  self.w.submit('force_apply',dict(c,force_port='COM7'));time.sleep(.2)
  self.assertEqual(self.opens,1);self.assertEqual(self.w.force_cfg['force_port'],'COM6')
