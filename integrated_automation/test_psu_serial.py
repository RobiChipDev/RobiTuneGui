import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch,Mock
from devices import SupplyDevice
from config import defaults

class SerialSupplyTests(unittest.TestCase):
 def open(self,reply):
  port=Mock();port.read_until.return_value=reply
  cfg=dict(defaults(),psu_backend='SERIAL',psu_resource='COM7')
  ctor=Mock(return_value=port)
  with patch.dict(sys.modules,{'serial':SimpleNamespace(Serial=ctor)}),patch('devices.time.sleep') as wait:
   device=SupplyDevice(cfg)
  return device,port,ctor,wait
 def test_field_identity_and_initialization(self):
  d,p,c,w=self.open(b'GW Instek,GPP-6030,SN:GEZ820101,V1.07\n')
  self.assertIn('GPP-6030',d.identity)
  self.assertEqual(c.call_args.kwargs['timeout'],3.0)
  w.assert_called_once_with(1.0)
  self.assertLess(p.mock_calls.index(unittest.mock.call.reset_input_buffer()),p.mock_calls.index(unittest.mock.call.write(b'*IDN?\n')))
  d.close();p.close.assert_called_once()
 def test_empty_and_partial_are_distinct_and_close(self):
  for reply,reason in [(b'','no bytes received'),(b'GW Instek','incomplete reply')]:
   p=Mock();p.read_until.return_value=reply
   with patch.dict(sys.modules,{'serial':SimpleNamespace(Serial=Mock(return_value=p))}),patch('devices.time.sleep'):
    with self.assertRaises(TimeoutError) as ctx:
     SupplyDevice(dict(defaults(),psu_backend='SERIAL',psu_resource='COM7'))
   self.assertIn('*IDN?',str(ctx.exception));self.assertIn(reason,str(ctx.exception))
   self.assertIn('received='+str(len(reply)),str(ctx.exception));p.close.assert_called_once()
 def test_partial_measurement_never_becomes_numeric_value(self):
  d,p,_,_=self.open(b'GW Instek,GPP-6030,V1.07\n')
  p.read_until.return_value=b'48.0'
  with self.assertRaisesRegex(TimeoutError,':MEAS1:VOLT'):
   d.query(':MEAS1:VOLT?')
  d.close()
