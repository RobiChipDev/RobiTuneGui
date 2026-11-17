import math,threading,unittest
from unittest.mock import patch,Mock
from calibration import calibration_scale
from config import defaults
from devices import ForceDevice
from app import App

class CalibrationTests(unittest.TestCase):
 def test_two_point_signed_and_nonzero_origin(self):
  scale,zero=calibration_scale(100,0,300,-2)
  self.assertAlmostEqual((200-zero)*scale,-1)
  self.assertEqual(zero,100)
 def test_bad_calibration_does_not_produce_scale(self):
  for args in [(1,0,1,2),(0,1,2,1),(0,0,math.nan,1)]:
   with self.assertRaises(ValueError):calibration_scale(*args)
 def test_raw_preserved_offset_saved_unknown_scale_remains_blank(self):
  reader=object.__new__(ForceDevice);reader.cfg=dict(defaults(),zero1=100.,zero2=-50.,scale2=None);reader.ser=object();rows=[]
  with patch('devices.read_channel',side_effect=[(200,1.,1.1,b'a'),(-30,1.2,1.3,b'b')]):reader.read(rows.append,threading.Event())
  self.assertEqual(rows[0]['raw_signed_int32'],200);self.assertEqual(rows[0]['raw_zero'],100)
  self.assertEqual(rows[0]['force_N'],1.)
  self.assertEqual(rows[1]['scaled_value'],'');self.assertNotIn('torque_Nm',rows[1])
 def test_stopping_force_prevents_test_start(self):
  app=object.__new__(App);app.connected=True;app.pending_tare=False;app.propellers={};app.propeller_name=Mock();app.cfg=defaults();app.getcfg=lambda:dict(app.cfg);app.force_state='stopping';app.worker=Mock();app.worker.port='COM5'
  with patch('app.messagebox.showerror') as dialog:app.begin()
  app.worker.submit.assert_not_called();dialog.assert_called_once()
 def test_deadline_exposes_stage_duration(self):
  from controller import Controller
  import time
  worker=object.__new__(Controller);worker.deadline=time.monotonic()+10
  self.assertTrue(9.8<worker.phase_duration<=10)
