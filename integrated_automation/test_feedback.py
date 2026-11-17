import queue,threading,time,unittest
from unittest.mock import Mock,patch
from app import App
from controller import Controller
from config import defaults

class FeedbackTests(unittest.TestCase):
 def test_stop_does_not_stop_force_monitor(self):
  app=object.__new__(App);app.worker=Mock();app.pending_begin=True;app.logline=Mock()
  app.stop_all();app.worker.stop_event.set.assert_called_once();app.worker.submit.assert_not_called();self.assertFalse(app.pending_begin)
 def test_failed_connect_has_explicit_result_and_worker_survives(self):
  def fail(port):raise OSError('COM busy diagnostic')
  worker=Controller(motor_factory=fail)
  try:
   worker.submit('connect',('REAL','COM5'));result=None;deadline=time.monotonic()+1
   while time.monotonic()<deadline:
    try:k,v=worker.events.get(timeout=.1)
    except queue.Empty:continue
    if k=='connect_result':result=v;break
   self.assertFalse(result['ok']);self.assertIn('COM busy diagnostic',result['error']);self.assertTrue(worker.is_alive())
  finally:worker.quit_event.set();worker.join(1)
 def test_duplicate_connect_not_enqueued(self):
  app=object.__new__(App);app.connected=False;app.connecting=True;app.worker=Mock();app.logline=Mock()
  app.connect();app.worker.submit.assert_not_called()
 def test_ui_poll_recovers_scheduling_after_callback_error(self):
  app=object.__new__(App);app.poll_once=Mock(side_effect=ValueError('widget fail'));app.callback_error=Mock();app.root=Mock()
  app.poll();app.callback_error.assert_called_once();app.root.after.assert_called_once_with(100,app.poll)
 def test_connection_failure_displays_error(self):
  app=object.__new__(App);app.preview_q=queue.Queue();app.worker=Mock();app.worker.events=queue.Queue();app.worker.events.put(('connect_result',dict(ok=False,error='timeout trace')))
  app.connected=False;app.pending_begin=False;app.pending_tare=False;app.propellers={};app.propeller_name=Mock();app.sim=Mock();app.force_state='stopped';app.forcebtn=Mock();app.settingbtns=[];app.propeller_combo=Mock();app.device_status=Mock();app.cfg=defaults();app.simbtn=Mock();app.startbtn=Mock();app.connecting=True;app.connectbtn=Mock();app.logline=Mock();app.values={};app.vars={};app.dashboard=Mock();app.dashboard.tare_buttons={};app.preview=None;app.busy=False;app.sensor_status=Mock()
  app.refresh_notice=Mock()
  with patch('app.messagebox.showerror') as dialog:app.poll_once()
  self.assertFalse(app.connecting);dialog.assert_called_once_with('馬達連線失敗','timeout trace')
