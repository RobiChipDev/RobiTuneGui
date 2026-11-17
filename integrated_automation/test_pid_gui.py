"""Real PidDialog widget tests; explicitly skipped if no display is available."""
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pid_dialog import PidDialog
from pid_settings import PARAMETERS
from theme import apply_theme
from test_pid_transactions import worker,execute,replies

class PidGuiTests(unittest.TestCase):
 def setUp(self):
  try:self.root=tk.Tk()
  except tk.TclError as error:
   if 'display' in str(error).lower():self.skipTest('No GUI display: '+str(error))
   raise
  self.addCleanup(self.root.destroy);apply_theme(self.root)
  self.w=worker();self.w.motor.read_pid.return_value={k:128 if k.endswith('_div') else -100 if k.startswith('observer') else 100 for k in PARAMETERS}
  self.app=SimpleNamespace(root=self.root,worker=self.w,connected=True,sim=tk.BooleanVar(self.root,False),busy=False,pending_begin=False,motor_stopped=True)
  self.d=PidDialog(self.app);self.root.update()
 def test_tabs_stringvars_inputs_buttons_and_readonly(self):
  d=self.d;self.assertEqual(len(d.notebook.tabs()),2)
  self.assertEqual([d.notebook.tab(t,'text') for t in d.notebook.tabs()],['Currents / Speed','Observer / PLL'])
  self.assertEqual(str(d.editors['speed_kp'].cget('state')),'disabled')
  d.read_button.invoke();r=dict(self.w.pid.active);self.w.pid_command(r)
  for e in replies(self.w):self.w.pid.accept(e)
  d.result();self.root.update()
  self.assertNotIn('iq_reference_raw',d.editors)
  d.editors['speed_kp'].delete(0,'end');d.editors['speed_kp'].insert(0,'101')
  self.assertEqual(d.notes['speed_kp'].get(),'已修改');self.assertFalse(d.writes['speed_kp'].instate(['disabled']))
  d.drafts['speed_kp'].set('abc');self.assertEqual(d.notes['speed_kp'].get(),'輸入無效');self.assertTrue(d.writes['speed_kp'].instate(['disabled']))
  d.notebook.select(1);self.root.update();self.assertTrue(d.editors['observer_c1'].winfo_ismapped())
  d.steps['observer_c1'][0].invoke();self.assertEqual(d.drafts['observer_c1'].get(),'-101');self.w.motor.write_pid.assert_not_called()
  d.notebook.select(0);d.drafts['speed_kp'].set('101')
  with patch('pid_dialog.messagebox.askokcancel',return_value=True):d.writes['speed_kp'].invoke()
  self.assertEqual(d.notes['speed_kp'].get(),'寫入中');self.assertTrue(d.read_button.instate(['disabled']))
 def test_destroy_reopen_inflight_and_late_stop_reply(self):
  self.d.read_button.invoke();r=dict(self.w.pid.active);self.d.destroy()
  self.d=PidDialog(self.app);self.root.update()
  self.assertTrue(self.d.pending);self.assertTrue(self.d.read_button.instate(['disabled']))
  self.d.read_button.invoke();self.assertEqual(self.w.pid.active['id'],r['id'])
  self.w.pid_command(r);events=replies(self.w);self.w.cancel_pid('STOP');self.d.result()
  for e in events:self.assertFalse(self.w.pid.accept(e))
  self.d.refresh();self.root.update();self.assertEqual(self.d.readouts['speed_kp'].get(),'—');self.assertFalse(self.d.pending)
 def test_success_and_failure_labels_persist_after_refresh(self):
  execute(self.w);self.d.result();self.d.drafts['observer_c1'].set('-90');self.d.drafts['speed_kp'].set('101')
  with patch('pid_dialog.messagebox.askokcancel',return_value=True):self.d.writes['speed_kp'].invoke()
  r=dict(self.w.pid.active);old=dict(self.w.pid.values);self.w.motor.read_pid.side_effect=[old,dict(old,speed_kp=101)];self.w.pid_command(r)
  events=replies(self.w);self.w.pid.accept(events[0]);self.d.refresh();self.assertEqual(self.d.notes['speed_kp'].get(),'讀回驗證中')
  self.w.pid.accept(events[1]);self.d.result();self.d.refresh();self.root.update()
  self.assertEqual(self.d.notes['speed_kp'].get(),'已驗證');self.assertEqual(self.d.drafts['observer_c1'].get(),'-90')
  self.d.drafts['speed_kp'].set('102');self.w.motor.read_pid.side_effect=None;self.w.motor.read_pid.return_value=dict(old,speed_kp=101);self.w.motor.write_pid.side_effect=TimeoutError('test timeout')
  with patch('pid_dialog.messagebox.askokcancel',return_value=True):self.d.writes['speed_kp'].invoke()
  self.w.pid_command(dict(self.w.pid.active))
  for e in replies(self.w):self.w.pid.accept(e)
  self.d.result();self.d.refresh();self.assertEqual(self.d.notes['speed_kp'].get(),'未確認');self.assertIn('test timeout',self.d.status.get())
 def test_tab_style_matches_initial_and_switched_content(self):
  from tkinter import ttk
  d=self.d;style=ttk.Style(d)
  tabs=d.notebook.tabs()
  self.assertEqual(d.notebook.select(),tabs[0])
  inactive,selected=self.root._pid_tab_images
  self.assertEqual(inactive.get(3,3),(238,241,244))
  self.assertEqual(selected.get(3,3),(255,255,255))
  self.assertEqual(selected.get(3,7),(23,105,141))
  self.assertEqual(inactive.height(),selected.height())
  self.assertEqual(style.layout('Pid.TNotebook.Tab')[0][0],'Pid.Tab.surface')
  self.assertEqual(style.lookup('Pid.TNotebook.Tab','foreground',('selected',)),'#24374b')
  self.assertIn('bold',str(style.lookup('Pid.TNotebook.Tab','font',('selected',))))
  self.assertEqual(style.lookup('Pid.TNotebook.Tab','foreground',('!selected',)),'#687b8c')
  heights=[]
  for index,key,other in [(0,'speed_kp','observer_c1'),(1,'observer_c1','speed_kp'),(0,'speed_kp','observer_c1')]:
   d.notebook.select(index);self.root.update()
   self.assertEqual(d.notebook.select(),tabs[index])
   self.assertTrue(d.editors[key].winfo_ismapped())
   self.assertFalse(d.editors[other].winfo_ismapped())
   heights.append(d.notebook.winfo_reqheight())
  self.assertEqual(len(set(heights)),1)
  self.d.destroy();self.d=PidDialog(self.app);self.root.update()
  self.assertEqual(self.d.notebook.index('current'),0)
  self.assertTrue(self.d.editors['speed_kp'].winfo_ismapped())
