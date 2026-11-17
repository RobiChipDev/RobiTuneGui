import struct
import threading
import unittest
from unittest.mock import Mock

from controller import Controller
from pid_settings import PARAMETERS, register
from protocol import Motor


class PidTests(unittest.TestCase):
    def test_wire_format_for_signed_observer_and_divisors(self):
        motor = object.__new__(Motor)
        motor.request = Mock(return_value=b'')
        motor.write_pid('observer_c1', -11264)
        motor.request.assert_called_once_with(struct.pack('<HHh', 9, 0x351, -11264))
        motor.write_pid('speed_kp_div', 128)
        motor.request.assert_called_with(struct.pack('<HHH', 9, 0x1451, 7))
        with self.assertRaises(ValueError):
            motor.write_pid('iq_reference_raw', 10)
        with self.assertRaises(ValueError):
            motor.write_pid('speed_kp_div', 129)
        vals = [14 if key.endswith('_div') else -100 for key in PARAMETERS]
        motor.request.return_value = struct.pack('<13h', *vals)
        got = motor.read_pid()
        self.assertEqual(got['observer_c1'], -100)
        self.assertEqual(got['speed_ki_div'], 16384)
        motor.request.assert_called_with(struct.pack('<14H', 17, *map(register, PARAMETERS)))

    def test_unsafe_state_and_mismatch(self):
        from test_pid_transactions import worker, execute
        w = worker()
        w.motor.sample.return_value = dict(state=6, rpm=1500, faults=0)
        event = execute(w, ('speed_kp', 100, 200))
        self.assertIn('IDLE', event['error'])
        w.motor.write_pid.assert_not_called()
        w.motor.sample.return_value = dict(state=0, rpm=0, faults=0)
        event = execute(w, ('speed_kp', 100, 200))
        self.assertIn('讀回不符', event['error'])
        self.assertTrue(w.pid_unverified)
        execute(w)
        self.assertFalse(w.pid_unverified)
        w.motor.read_pid.side_effect = [{'speed_kp':100}, {'speed_kp':200}]
        event = execute(w, ('speed_kp', 100, 200))
        self.assertEqual(event['phase'], 'success')
        self.assertEqual(w.pid_snapshot, {'speed_kp':200})
