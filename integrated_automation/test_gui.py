"""Opt-in Tk smoke checks; set ROBI_GUI_TESTS=1 on a desktop/test display."""
import os,unittest,time
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('ROBI_GUI_TESTS')=='1','requires explicit test display')
class GuiTests(unittest.TestCase):
 def test_dashboard_and_settings_fit_and_apply(self):
  import tkinter as tk
  from app import App
  root=tk.Tk();errors=[]
  with patch('app.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)):
   app=App(root)
   try:
    for _ in range(5):root.update();time.sleep(.03)
    self.assertTrue(app.statuslabel.winfo_ismapped());self.assertGreater(app.statuslabel.winfo_height(),5)
    self.assertLess(app.statuslabel.winfo_rooty()+app.statuslabel.winfo_height(),root.winfo_rooty()+root.winfo_height())
    self.assertTrue(all(app.dashboard.force_titles[ch].winfo_ismapped() for ch in (1,2)))
    self.assertEqual(sum(w[0].winfo_ismapped() for w in app.dashboard.task_widgets),7)
    initial=app.sim.get();app.toggle_mode();self.assertNotEqual(app.sim.get(),initial);app.toggle_mode()
    app.connected=True;app.toggle_mode();self.assertEqual(app.sim.get(),initial);app.connected=False
    from ui_widgets import PillButton
    from unittest.mock import Mock
    command=Mock();button=PillButton(root,text='probe',command=command)
    button.configure(state='disabled');button.invoke();command.assert_not_called()
    button.configure(state='normal');button.invoke();command.assert_called_once();button.destroy()
    app.open_settings();root.update();app.dialogs[-1].destroy()
    app.open_devices();root.update();app.dialogs[-1].destroy()
    for child in app.outer.winfo_children():
     self.assertTrue(child.winfo_ismapped())
     self.assertLessEqual(child.winfo_rooty()+child.winfo_height(),root.winfo_rooty()+root.winfo_height())
    self.assertEqual(root.cget('background'),'#ffffff')
    widths=[app.dashboard.speed_card.winfo_width()]+[app.dashboard.force_titles[ch].winfo_width() for ch in (1,2)]
    self.assertLessEqual(max(widths)-min(widths),1)
    self.assertTrue(all(lamp.cget('background')=='#ffffff' for lamp in app.dashboard.lamps.values()))
    self.assertFalse(errors)
   finally:app.worker.quit_event.set();app.worker.join(2);root.destroy()
