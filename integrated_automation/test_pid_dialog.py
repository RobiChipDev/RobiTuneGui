"""Headless presenter tests (Tcl StringVar, mocked widgets; NOT GUI rendering)."""
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from pid_dialog import PidDialog
from pid_settings import PARAMETERS
from test_pid_transactions import worker,execute,replies

class DialogTests(unittest.TestCase):
 def setUp(self):
  self.tcl=tk.Tcl();self.w=worker();self.w.motor.read_pid.return_value={'speed_kp':2810,'observer_c1':-11264,'speed_kp_div':128}
  execute(self.w)
  self.app=SimpleNamespace(worker=self.w,connected=True,sim=tk.BooleanVar(self.tcl,False),busy=False,pending_begin=False,motor_stopped=True)
  self.d=self.make_dialog()
 def make_dialog(self):
  d=object.__new__(PidDialog);d.app=self.app;d.transaction=self.w.pid;d._syncing=False;d._revision=-1;d.values={}
  d.status=tk.StringVar(self.tcl);d.connection=tk.StringVar(self.tcl)
  d.readouts={k:tk.StringVar(self.tcl) for k in PARAMETERS}
  d.drafts={k:tk.StringVar(self.tcl) for k in PARAMETERS if k!='iq_reference_raw'}
  d.notes={k:tk.StringVar(self.tcl) for k in d.drafts};d.writes={k:Mock() for k in d.drafts}
  d.editors={k:Mock() for k in d.drafts};d.steps={};d.read_button=Mock()
  for k,v in d.drafts.items():v.trace_add('write',lambda *_,key=k:d._draft_changed(key))
  d.result();return d
 def test_step_does_not_send_and_respects_limits(self):
  d=self.d;d.step('observer_c1',-1);self.assertEqual(d.drafts['observer_c1'].get(),'-11265')
  for k,v,delta in [('observer_c1','-32768',-1),('speed_kp','32767',1)]:
   d.drafts[k].set(v);d.step(k,delta);self.assertEqual(d.drafts[k].get(),v)
  self.assertFalse(self.w.pid.view()['pending']);self.w.motor.write_pid.assert_not_called()
 @patch('pid_dialog.messagebox.askokcancel',return_value=True)
 def test_single_write_stages_and_other_drafts_survive(self,confirm):
  d=self.d;d.drafts['speed_kp'].set('2811');d.drafts['observer_c1'].set('-11265');d.write('speed_kp')
  self.assertEqual(d.notes['speed_kp'].get(),'寫入中');self.assertTrue(d.pending)
  request=dict(self.w.pid.active);d.write('observer_c1');self.assertEqual(self.w.pid.active['id'],request['id'])
  self.w.motor.read_pid.side_effect=[dict(d.values),dict(d.values,speed_kp=2811)]
  self.w.pid_command(request);events=replies(self.w)
  self.w.pid.accept(events[0]);d.refresh();self.assertEqual(d.notes['speed_kp'].get(),'讀回驗證中')
  self.w.pid.accept(events[1]);d.result();d.refresh()
  self.assertEqual(d.notes['speed_kp'].get(),'已驗證');self.assertEqual(d.notes['observer_c1'].get(),'已修改')
  self.assertEqual(d.drafts['observer_c1'].get(),'-11265');self.assertIn('2810 → 2811',d.status.get())
 @patch('pid_dialog.messagebox.askokcancel',return_value=False)
 def test_cancel_invalid_and_running_never_submit(self,confirm):
  d=self.d;d.drafts['speed_kp'].set('2811');d.write('speed_kp')
  d.drafts['speed_kp_div'].set('129');d.write('speed_kp_div');self.assertEqual(d.notes['speed_kp_div'].get(),'輸入無效')
  d.app.motor_stopped=False;d.write('speed_kp');self.assertFalse(d.pending)
 def test_snapshot_changed_during_confirmation_rejects(self):
  d=self.d;d.drafts['speed_kp'].set('2811')
  def changed(*a,**kw):self.w.cancel_pid('STOP');d.result();return True
  with patch('pid_dialog.messagebox.askokcancel',side_effect=changed):d.write('speed_kp')
  self.assertFalse(d.pending);self.w.motor.write_pid.assert_not_called()
 def test_failure_clears_and_retains_reason(self):
  d=self.d;r=self.w.request_pid(('speed_kp',2810,2811));self.w.motor.write_pid.side_effect=TimeoutError('timeout')
  self.w.pid_command(r)
  for e in replies(self.w):self.w.pid.accept(e)
  d.result();d.refresh();self.assertFalse(d.pending);self.assertEqual(d.notes['speed_kp'].get(),'未確認')
  self.assertIn('timeout',d.status.get());self.assertTrue(all(v.get()=='' for v in d.drafts.values()))
  for b in d.writes.values():b.configure.assert_called_with(state='disabled')
 def test_read_updates_clean_preserves_dirty(self):
  d=self.d;d.drafts['observer_c1'].set('-11000');d.read();r=dict(self.w.pid.active)
  self.w.motor.read_pid.return_value=dict(d.values,speed_kp=2800);self.w.pid_command(r)
  for e in replies(self.w):self.w.pid.accept(e)
  d.result();self.assertEqual(d.drafts['observer_c1'].get(),'-11000');self.assertEqual(d.drafts['speed_kp'].get(),'2800')
 def test_reopen_uses_shared_pending_and_drafts(self):
  self.d.drafts['observer_c1'].set('-11000');self.d.read();r=dict(self.w.pid.active)
  new=self.make_dialog();self.assertTrue(new.pending);self.assertFalse(new.available());new.read()
  self.assertEqual(self.w.pid.active['id'],r['id']);self.assertEqual(new.drafts['observer_c1'].get(),'-11000')
  self.w.pid_command(r)
  for e in replies(self.w):self.w.pid.accept(e)
  new.result();self.assertFalse(new.pending)
