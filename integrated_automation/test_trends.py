import unittest
from ui_widgets import TrendSeries

class TrendTests(unittest.TestCase):
 def test_repeated_ui_refresh_does_not_duplicate_sample(self):
  s=TrendSeries();self.assertTrue(s.add(1,2,'N'));self.assertFalse(s.add(1,2,'N'));self.assertEqual(len(s.points),1)
 def test_calibration_or_unit_change_resets_history(self):
  s=TrendSeries();s.add(1,1,(.01,0,'N'));s.add(2,100,(1,0,'N'))
  self.assertEqual(list(s.points),[(2.,100.)])
 def test_signed_finite_values_and_window(self):
  s=TrendSeries();s.add(1,-3,'N');s.add(2,0,'N');s.add(32,-1,'N');self.assertEqual(list(s.points),[(2.,0.),(32.,-1.)])
  self.assertFalse(s.add(33,float('nan'),'N'));self.assertFalse(s.add(float('inf'),1,'N'))
 def test_out_of_order_sample_does_not_change_history(self):
  s=TrendSeries();s.add(10,2);self.assertFalse(s.add(9,4));self.assertEqual(list(s.points),[(10.,2.)])
