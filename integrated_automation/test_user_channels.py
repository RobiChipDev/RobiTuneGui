import threading
import unittest
from unittest.mock import patch
from config import defaults
from devices import ForceDevice

class UserChannels(unittest.TestCase):
    def test_confirmed_default_thrust_and_torque_scales(self):
        cfg=defaults()
        self.assertEqual((cfg['thrust_channel'],cfg['torque_channel']),(1,2))
        reader=object.__new__(ForceDevice);reader.cfg=cfg;reader.ser=object()
        rows=[]
        with patch('devices.read_channel',side_effect=[(123,1.,1.1,b'raw1'),(-456,1.2,1.3,b'raw2')]):
            reader.read(rows.append,threading.Event())
        self.assertEqual(rows[0]['scaled_value'],1.23)
        self.assertEqual(rows[0]['force_N'],1.23)
        self.assertEqual(rows[1]['unit'],'Nm')
        self.assertEqual(rows[1]['raw_signed_int32'],-456)
        self.assertEqual(cfg['scale2'],.001)
        self.assertAlmostEqual(rows[1]['scaled_value'],-.456)
        self.assertAlmostEqual(rows[1]['torque_Nm'],-.456)
