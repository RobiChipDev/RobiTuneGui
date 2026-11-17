"""App event routing with mocked presentation and controllable worker I/O."""
import queue,unittest,threading
from unittest.mock import Mock
from app import App
from config import defaults
from test_pid_transactions import worker
class AppPidTests(unittest.TestCase):
 def setUp(self):
  a=self.a=object.__new__(App);a.preview_q=queue.Queue();a.worker=worker()
  a.connected=True;a.connecting=False;a.pending_begin=False;a.pending_tare=False
  a.propellers={};a.propeller_name=Mock();a.sim=Mock();a.sim.get.return_value=False
  a.force_state='stopped';a.settingbtns=[];a.cfg=defaults();a.cfg['force_enabled']=False
  a.logline=Mock();a.values={};a.vars={};a.dashboard=Mock();a.dashboard.tare_buttons={}
  a.preview=None;a.busy=False;a.motor_stopped=True;a.refresh_notice=Mock()
  for n in ['forcebtn','propeller_combo','device_status','simbtn','startbtn','connectbtn','sensor_status']:setattr(a,n,Mock())
  a.pid_dialog=Mock();a.pid_dialog.winfo_exists.return_value=True
 def test_app_stop_and_poll_refuse_old_read(self):
  a=self.a;r=a.worker.request_pid();a.worker.pid_command(r);a.stop_all();a.poll_once()
  self.assertFalse(a.worker.pid.view()['pending']);self.assertIsNone(a.worker.pid_snapshot)
  self.assertTrue(any('忽略失效' in str(c) for c in a.logline.call_args_list))
 def test_app_routes_matching_result_ignores_old_error(self):
  a=self.a;old=a.worker.request_pid();a.worker.cancel_pid('old connection');new=a.worker.request_pid()
  a.worker.events.put(('pid_values',dict(old,phase='error',error='old timeout')))
  a.poll_once();self.assertEqual(a.worker.pid.active['id'],new['id'])
  a.worker.pid_command(new);a.poll_once();self.assertIsNone(a.worker.pid.active)
  self.assertEqual(a.worker.pid_snapshot,{'speed_kp':100});a.pid_dialog.result.assert_called()
 def test_closed_dialog_result_still_finishes(self):
  a=self.a;a.pid_dialog.winfo_exists.return_value=False;r=a.worker.request_pid();a.worker.pid_command(r)
  a.poll_once();self.assertFalse(a.worker.pid.view()['pending']);self.assertEqual(a.worker.pid_snapshot,{'speed_kp':100})
  a.pid_dialog.result.assert_not_called()
 def test_write_io_stop_is_responsive(self):
  a=self.a;entered=threading.Event();release=threading.Event()
  a.worker.motor.read_pid.side_effect=[{'speed_kp':100},{'speed_kp':200}]
  def write(*args):
   entered.set()
   if not release.wait(3):raise TimeoutError('test gate not released')
  a.worker.motor.write_pid.side_effect=write;r=a.worker.request_pid(('speed_kp',100,200))
  thread=threading.Thread(target=a.worker.pid_command,args=(r,));thread.start()
  try:
   self.assertTrue(entered.wait(3));a.stop_all();self.assertTrue(a.worker.pid_unverified)
   self.assertFalse(a.worker.pid.view()['pending'])
  finally:release.set();thread.join(3)
  self.assertFalse(thread.is_alive());a.poll_once();self.assertTrue(a.worker.pid_unverified);self.assertIsNone(a.worker.pid_snapshot)
