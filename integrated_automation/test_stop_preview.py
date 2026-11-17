import queue,threading,time,unittest
from unittest.mock import Mock,patch
from sensors import SensorWorker
from config import defaults
from app import App
from force_reader import read_channel

class StopTests(unittest.TestCase):
 def test_pending_io_cancelled_and_port_closed_by_owner(self):
  entered=threading.Event();released=threading.Event();closed=threading.Event();owners=[]
  class Device:
   def read(self,emit,stop):entered.set();released.wait(1)
   def cancel(self):released.set()
   def close(self):owners.append(threading.get_ident());closed.set()
  worker=SensorWorker('force',defaults(),queue.Queue(),threading.Event(),lambda c:Device())
  worker.start();self.assertTrue(entered.wait(.5));worker.request_stop();worker.join(.5)
  self.assertFalse(worker.is_alive());self.assertTrue(closed.is_set());self.assertEqual(owners,[worker.ident])
 def test_incomplete_modbus_reply_is_interruptible_without_flush(self):
  stop=threading.Event();ser=Mock();ser.write.return_value=8
  def partial(n):stop.set();return b''
  ser.read.side_effect=partial
  with self.assertRaises(InterruptedError):read_channel(ser,1,450,'HH-LL',stop)
  ser.flush.assert_not_called()
