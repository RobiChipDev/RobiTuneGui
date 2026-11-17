"""Real Controller.run/queues with event-gated fake equipment; no physical ports."""
import queue,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from controller import Controller
from config import defaults
from test_v03 import FakeMotor,FakeForce
import test_pid_dialog as presenter
import test_pid_app as app_fixture

class GateMotor(FakeMotor):
 def __init__(self):
  super().__init__();self.gates={};self.pid_value=100
 def arm(self,operation):
  pair=(threading.Event(),threading.Event());self.gates[operation]=pair;return pair
 def gate(self,operation):
  pair=self.gates.pop(operation,None)
  if pair:
   pair[0].set()
   if not pair[1].wait(5):raise TimeoutError('test gate '+operation)
 def sample(self):self.gate('sample');return super().sample()
 def read_pid(self):self.gate('read');return {'speed_kp':self.pid_value}
 def write_pid(self,key,value):self.gate('write');self.pid_value=value

class Harness:
 def __init__(self,case,folder):
  self.case=case;self.motor=GateMotor();self.releases=[];self.events=[]
  self.worker=Controller(lambda p:self.motor,{'force':lambda c:FakeForce(c)})
  self.worker.build_report=lambda p:None
  self.worker.submit('connect',('REAL','COM5'));self.wait(lambda k,v:k=='connected' and v)
  self.cfg=defaults();self.cfg.update(folder=folder,force_enabled=False,psu_enabled=False,poststop_s=1)
 def arm(self,op):
  entered,release=self.motor.arm(op);self.releases.append(release);return entered,release
 def wait(self,p):
  for _ in range(200):
   k,v=self.worker.events.get(timeout=5);self.events.append((k,v))
   if p(k,v):return v
  raise AssertionError('expected event absent')
 def close(self):
  for e in self.releases:e.set()
  self.worker.quit_event.set();self.worker.join(8)
  self.case.assertFalse(self.worker.is_alive());self.case.assertIsNone(self.worker.file)
  self.case.assertTrue(self.motor.closed)
  for t in threading.enumerate():
   if t.name=='Robi report':t.join(5);self.case.assertFalse(t.is_alive())

class InterlockThreadTests(unittest.TestCase):
 def test_pending_all_stages_force_on_and_off(self):
  for force in (False,True):
   for phase in ('read','write','queued_success'):
    with self.subTest(force=force,phase=phase),tempfile.TemporaryDirectory() as folder:
     h=Harness(self,folder);w=h.worker;h.cfg['force_enabled']=force
     try:
      if phase!='queued_success':entered,release=h.arm(phase)
      w.request_pid(('speed_kp',100,200) if phase=='write' else None)
      if phase!='queued_success':
       self.assertTrue(entered.wait(5));w.submit('begin',h.cfg);release.set()
      else:
       h.wait(lambda k,v:k=='pid_values' and v['phase']=='success');w.submit('begin',h.cfg)
      error=h.wait(lambda k,v:k=='command_error' and v['command']=='begin')
      self.assertIn('PID',error['error']);self.assertEqual(list(Path(folder).iterdir()),[])
      self.assertEqual(h.motor.starts,0);self.assertEqual(h.motor.ramps,[])
      self.assertFalse(any(k=='task_event' and v['reason']=='session_begin' for k,v in h.events))
     finally:h.close()
 def test_begin_reservation_excludes_pid_without_holding_lock_over_io(self):
  with tempfile.TemporaryDirectory() as folder:
   h=Harness(self,folder);w=h.worker;entered=threading.Event();release=threading.Event();h.releases.append(release)
   original=w._begin
   def gated(*a):
    entered.set()
    if not release.wait(5):raise TimeoutError('setup gate')
    return original(*a)
   try:
    with patch.object(w,'_begin',side_effect=gated):
     w.submit('begin',h.cfg);self.assertTrue(entered.wait(5))
     with self.assertRaises(ValueError):w.request_pid()
     self.assertTrue(w.pid.view()['experiment']);self.assertEqual(list(Path(folder).iterdir()),[])
     release.set();h.wait(lambda k,v:k=='task_event' and v['reason']=='session_begin')
    self.assertIsNone(w.pid.active)
   finally:h.close()
 def test_disconnect_stop_order_and_repeat_preserve_intent_and_uncertainty(self):
  for order in ('disconnect_stop','stop_disconnect','repeat_stop'):
   with self.subTest(order=order),tempfile.TemporaryDirectory() as folder:
    h=Harness(self,folder);w=h.worker
    try:
     with w.pid.lock:w.pid.unverified=True
     entered,release=h.arm('sample');self.assertTrue(entered.wait(5))
     if order=='stop_disconnect':w.stop_event.set();w.submit('disconnect')
     else:w.submit('disconnect');w.stop_event.set()
     if order=='repeat_stop':w.stop_event.set();w.cancel_pid('repeat STOP')
     release.set();h.wait(lambda k,v:k=='connected' and not v)
     self.assertIsNone(w.motor);self.assertFalse(w.pid.view()['blocked']);self.assertTrue(w.pid_unverified)
     with self.assertRaises(ValueError):w.request_pid()
     w.submit('connect',('REAL','COM5'));h.wait(lambda k,v:k=='connected' and v)
     self.assertFalse(w.pid.view()['blocked']);self.assertTrue(w.pid_unverified)
     w.request_pid();event=h.wait(lambda k,v:k=='pid_values' and v['phase']=='success')
     self.assertTrue(w.pid.accept(event));self.assertFalse(w.pid_unverified)
    finally:h.close()
 def test_write_sent_disconnect_stop_keeps_unverified(self):
  with tempfile.TemporaryDirectory() as folder:
   h=Harness(self,folder);w=h.worker
   try:
    entered,release=h.arm('write');w.request_pid(('speed_kp',100,200))
    self.assertTrue(entered.wait(5));self.assertTrue(w.pid_unverified)
    w.submit('disconnect');w.stop_event.set();release.set()
    h.wait(lambda k,v:k=='connected' and not v)
    self.assertTrue(w.pid_unverified);self.assertFalse(w.pid.view()['blocked'])
    for k,v in h.events:
     if k=='pid_values':self.assertFalse(w.pid.accept(v))
    w.stop_event.set();h.wait(lambda k,v:k=='log' and '停止要求使交易失效' in str(v))
    h.wait(lambda k,v:k=='sample')
    w.stop_event.set();h.wait(lambda k,v:k=='log' and '停止要求使交易失效' in str(v))
    h.wait(lambda k,v:k=='sample')
    self.assertTrue(w.pid_unverified);self.assertFalse(w.pid.view()['blocked']);self.assertIsNone(w.motor)
   finally:h.close()
 def test_disconnect_during_session_preserves_stop_recording(self):
  with tempfile.TemporaryDirectory() as folder:
   h=Harness(self,folder);w=h.worker
   try:
    w.submit('begin',h.cfg);h.wait(lambda k,v:k=='task_event' and v['reason']=='session_begin')
    entered,release=h.arm('sample');self.assertTrue(entered.wait(5))
    w.submit('disconnect');w.stop_event.set();release.set()
    h.wait(lambda k,v:k=='connected' and not v)
    self.assertTrue(any(k=='task_event' and v['reason']=='session_end' for k,v in h.events))
    self.assertIsNone(w.file);self.assertFalse(w.pid.view()['experiment']);self.assertFalse(w.pid.view()['blocked'])
   finally:h.close()
 def test_stop_reports_dropped_prestate_commands(self):
  with tempfile.TemporaryDirectory() as folder:
   h=Harness(self,folder);w=h.worker
   try:
    entered,release=h.arm('sample');self.assertTrue(entered.wait(5))
    for command,value in [('connect',('REAL','COM5')),('begin',h.cfg),('force_tare',1)]:w.submit(command,value)
    w.stop_event.set();release.set()
    seen=set()
    while len(seen)<3:
     v=h.wait(lambda k,v:k=='command_error');seen.add(v['command'])
    self.assertEqual(seen,{'connect','begin','force_tare'});self.assertEqual(list(Path(folder).iterdir()),[])
   finally:h.close()

class InterlockFunctionTests(unittest.TestCase):
 def test_controller_rejects_before_io_and_creation(self):
  for state in ('pending','unverified','blocked'):
   for force in (False,True):
    with self.subTest(state=state,force=force),patch.object(Controller,'start'):
     w=Controller();w.motor=Mock();w.mode='REAL';c=defaults();c['force_enabled']=force
     if state=='pending':w.pid.reserve()
     else:setattr(w.pid,state,True)
     with patch('controller.create_session_folder') as create:
      with self.assertRaises(ValueError):w.begin(c)
      create.assert_not_called();w.motor.sample.assert_not_called();w.motor.read_pid.assert_not_called()
     self.assertFalse(w.pid.view()['experiment'])
 def test_begin_failure_releases_reservation(self):
  with patch.object(Controller,'start'):
   w=Controller();w.motor=Mock();w.mode='REAL';w.motor.sample.side_effect=TimeoutError('sample fail')
   with self.assertRaises(TimeoutError):w.begin(defaults())
   self.assertFalse(w.pid.view()['experiment']);w.request_pid()
 def app(self):
  f=app_fixture.AppPidTests();f.setUp();a=f.a;a.worker.port='COM5';a.getcfg=Mock(return_value=defaults());return a
 def test_app_before_confirmation_and_button(self):
  a=self.app();a.worker.request_pid()
  with patch('app.messagebox.showerror') as error,patch('app.messagebox.askokcancel') as confirm:
   a.begin();error.assert_called_once();confirm.assert_not_called()
  a.poll_once();a.startbtn.configure.assert_called_with(state='disabled')
  self.assertFalse(any(k=='begin' for k,v in list(a.worker.commands.queue)))
 def test_app_rechecks_after_confirmation_pid_or_connection(self):
  for change in ('pid','connection','unverified'):
   with self.subTest(change=change):
    a=self.app()
    def during(*args,**kwargs):
     if change=='pid':a.worker.request_pid()
     elif change=='connection':a.worker.cancel_pid('disconnect',blocked=True)
     else:a.worker.pid.unverified=True
     return True
    with patch('app.messagebox.askokcancel',side_effect=during),patch('app.messagebox.showerror') as error:
     a.begin();error.assert_called_once()
    self.assertFalse(any(k=='begin' for k,v in list(a.worker.commands.queue)))
 def test_hint_persistence_priority_and_next_valid_edit(self):
  f=presenter.DialogTests();f.setUp();d=f.d
  d.drafts['speed_kp'].set('32767');d.step('speed_kp',1);hint=d.status.get()
  for _ in range(3):d.refresh();self.assertEqual(d.status.get(),hint)
  d.drafts['speed_kp'].set('bad');d.refresh();self.assertEqual(d.status.get(),hint)
  d.drafts['speed_kp'].set('100');d.refresh();self.assertNotEqual(d.status.get(),hint)
  f.w.cancel_pid('STOP');d.result();important=d.status.get();d.operation_hint('low priority');d.refresh()
  self.assertEqual(d.status.get(),important)
 def test_force_monitor_is_not_pid_experiment_gate(self):
  with patch.object(Controller,'start'):
   w=Controller();w.pid.reserve();c=defaults()
   w.start_force(c,'SIMULATION')
   self.assertTrue(w.pid.view()['pending'])
