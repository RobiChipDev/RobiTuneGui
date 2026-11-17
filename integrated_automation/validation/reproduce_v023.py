"""Deterministic v0.3.23 defect probes, no display/hardware. Expect failures."""
import sys,unittest,threading
from unittest.mock import Mock,patch
sys.path.insert(0,sys.argv.pop(1))
from test_pid_dialog import DialogTests
from controller import Controller
from pid_dialog import PidDialog
class Reproduce(unittest.TestCase):
 def dialog(self):
  f=DialogTests();f.setUp();return f.d
 def test_stop_then_late_read_must_not_restore(self):
  d=self.dialog();d.read();d.result({},'STOP');d.result({'speed_kp':100},'late reply')
  self.assertEqual(d.values,{})
 def test_reopen_must_keep_background_pending(self):
  a=self.dialog();a.read();b=self.dialog();b.app=a.app
  self.assertFalse(b.available())
 def test_old_reply_must_not_clear_new_pending(self):
  d=self.dialog();d.read();d.result({},'STOP');d.read();d.result({'speed_kp':100},'old reply')
  self.assertTrue(d.pending)
 def test_stop_after_write_must_not_clear_unverified(self):
  w=object.__new__(Controller);w.file=None;w.mode='REAL';w.motor=Mock();w.emit=Mock()
  w.stop_event=threading.Event();w.quit_event=threading.Event()
  w.motor.sample.return_value=dict(state=0,rpm=0,faults=0)
  w.motor.read_pid.side_effect=[{'speed_kp':100},{'speed_kp':200}]
  w.motor.write_pid.side_effect=lambda *a:w.stop_event.set()
  w.pid_command(('speed_kp',100,200));self.assertTrue(w.pid_unverified)
 def test_success_row_must_remain_verified(self):
  d=self.dialog();d.drafts['speed_kp'].set('2811')
  with patch('pid_dialog.messagebox.askokcancel',return_value=True):d.write('speed_kp')
  d.result(dict(d.values,speed_kp=2811),'success');d.refresh()
  self.assertIn('已驗證',d.notes['speed_kp'].get())
unittest.main()
