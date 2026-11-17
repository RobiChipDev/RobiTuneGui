import queue,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from controller import Controller
from config import defaults
from test_v03 import FakeMotor,FakeForce
import test_pid_dialog as presenter

class GateMotor(FakeMotor):
 def __init__(self):
  super().__init__();self.gate=False;self.entered=threading.Event();self.release=threading.Event()
 def sample(self):
  if self.gate:
   self.gate=False;self.entered.set()
   if not self.release.wait(5):raise TimeoutError('gate')
  return super().sample()
 def read_pid(self):return {'speed_kp':100}

class Reproduce(unittest.TestCase):
 def start_worker(self):
  m=GateMotor();w=Controller(lambda p:m,{'force':lambda c:FakeForce(c)})
  # Keep report generation synchronous and empty so cleanup has no report thread.
  w.build_report=lambda p:None
  w.submit('connect',('REAL','COM5'));self.wait(w,lambda k,v:k=='connected' and v)
  self.addCleanup(self.close,w,m);return w,m
 def close(self,w,m):
  m.release.set();w.quit_event.set();w.join(8)
  self.assertFalse(w.is_alive());self.assertIsNone(w.file)
 def wait(self,w,p):
  for _ in range(150):
   k,v=w.events.get(timeout=5)
   if p(k,v):return v
  self.fail('event not found')
 def pending_begin(self,force):
  with tempfile.TemporaryDirectory() as folder:
   w,m=self.start_worker();c=defaults();c.update(folder=folder,force_enabled=force,psu_enabled=False,baseline_s=1,poststop_s=1)
   r=w.request_pid();self.wait(w,lambda k,v:k=='pid_values' and v.get('phase')=='success')
   w.submit('begin',c)
   self.wait(w,lambda k,v:k=='command_error' or (k=='task_event' and v['reason']=='session_begin'))
   try:
    if list(Path(folder).iterdir()):
     if force:
      error=self.wait(w,lambda k,v:k=='command_error' and v['command']=='begin')
      print('OBSERVED force=True: session folder already exists; '+error['error'],flush=True)
     else:
      self.wait(w,lambda k,v:k=='task_event' and v['reason']=='motor_start')
      print('OBSERVED force=False: fake motor starts='+str(m.starts),flush=True)
    self.assertEqual(list(Path(folder).iterdir()),[])
   finally:self.close(w,m)
 def test_force_off_pending_rejects_before_files(self):self.pending_begin(False)
 def test_force_on_pending_rejects_before_files(self):self.pending_begin(True)
 def test_disconnect_stop_does_not_lose_intent(self):
  w,m=self.start_worker();m.gate=True;self.assertTrue(m.entered.wait(5))
  w.submit('disconnect');w.stop_event.set();m.release.set()
  self.wait(w,lambda k,v:k=='log' and '控制器已回覆停止指令' in str(v))
  self.wait(w,lambda k,v:k=='sample')
  print('OBSERVED motor_present='+str(w.motor is not None)+' blocked='+str(w.pid.view()['blocked'])+' queue_empty='+str(w.commands.empty()),flush=True)
  self.assertIsNone(w.motor)
 def test_operation_hint_survives_refresh(self):
  f=presenter.DialogTests();f.setUp();d=f.d
  d.drafts['speed_kp'].set('32767');d.step('speed_kp',1)
  before=d.status.get();d.refresh();self.assertEqual(d.status.get(),before)
