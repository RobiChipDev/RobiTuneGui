"""Deterministic event-order tests: no sleep, serial ports or GUI stand-ins."""
import queue,threading,unittest
from unittest.mock import Mock
from controller import Controller
from pid_transactions import PidTransactions

def worker():
    w=object.__new__(Controller)
    w.commands=queue.Queue();w.events=queue.Queue()
    w.stop_event=threading.Event();w.quit_event=threading.Event()
    w.file=None;w.mode='REAL';w.motor=Mock();w.pid=PidTransactions()
    w.motor.sample.return_value=dict(state=0,rpm=0,faults=0)
    w.motor.read_pid.return_value={'speed_kp':100}
    return w

def replies(w):
    result=[]
    while not w.events.empty():
        k,v=w.events.get_nowait()
        if k=='pid_values':result.append(v)
    return result

def execute(w,update=None):
    r=w.request_pid(update);w.pid_command(r)
    events=replies(w)
    for e in events:w.pid.accept(e)
    return events[-1]

class TransactionTests(unittest.TestCase):
    def test_read_in_flight_stop_late_reply_does_not_restore(self):
        w=worker();r=w.request_pid()
        def reply():w.stop_event.set();w.cancel_pid('STOP');return {'speed_kp':100}
        w.motor.read_pid.side_effect=reply;w.pid_command(r)
        for e in replies(w):self.assertFalse(w.pid.accept(e))
        self.assertEqual(w.pid.view()['values'],{});self.assertFalse(w.pid.view()['pending'])

    def test_success_already_queued_then_stop_rejects_old_result(self):
        w=worker();r=w.request_pid();w.pid_command(r);events=replies(w)
        w.stop_event.set();w.cancel_pid('STOP')
        for e in events:self.assertFalse(w.pid.accept(e))
        self.assertIsNone(w.pid_snapshot)

    def test_write_sent_stop_unverified_persists_until_fresh_read(self):
        w=worker();w.motor.read_pid.side_effect=[{'speed_kp':100},{'speed_kp':200}]
        def sent(*a):w.stop_event.set();w.cancel_pid('STOP')
        w.motor.write_pid.side_effect=sent;r=w.request_pid(('speed_kp',100,200));w.pid_command(r)
        events=replies(w)
        for e in events:self.assertFalse(w.pid.accept(e))
        self.assertTrue(w.pid_unverified);self.assertIsNone(w.pid_snapshot)
        self.assertTrue(events[-1]['write_may_have_been_sent'])
        self.assertEqual(events[-1]['observed_values'],{'speed_kp':200})
        # No real stop loop in this synchronous fixture; explicitly release STOP.
        w.stop_event.clear();w.motor.read_pid.side_effect=None;w.motor.read_pid.return_value={'speed_kp':200}
        execute(w);self.assertFalse(w.pid_unverified)

    def test_stop_after_write_success_queued_is_conservative(self):
        w=worker();w.motor.read_pid.side_effect=[{'speed_kp':100},{'speed_kp':200}]
        r=w.request_pid(('speed_kp',100,200));w.pid_command(r);events=replies(w)
        w.cancel_pid('STOP')
        for e in events:self.assertFalse(w.pid.accept(e))
        self.assertTrue(w.pid_unverified)

    def test_old_reply_cannot_finish_new_pending_or_replace_values(self):
        w=worker();old=w.request_pid();w.pid_command(old);events=replies(w)
        w.cancel_pid('STOP');new=w.request_pid()
        for e in events:self.assertFalse(w.pid.accept(e))
        self.assertEqual(w.pid.active['id'],new['id']);self.assertTrue(w.pid.view()['pending'])
        w.motor.read_pid.return_value={'speed_kp':300};w.pid_command(new)
        for e in replies(w):w.pid.accept(e)
        for e in events:self.assertFalse(w.pid.accept(e))
        self.assertEqual(w.pid_snapshot,{'speed_kp':300})

    def test_disconnect_reconnect_rejects_old_generation(self):
        w=worker();r=w.request_pid();w.pid_command(r);events=replies(w)
        w.submit('disconnect');self.assertFalse(w.pid.view()['pending'])
        with self.assertRaises(ValueError):w.request_pid()
        w.cancel_pid('new connection',blocked=False);new=w.request_pid()
        for e in events:self.assertFalse(w.pid.accept(e))
        self.assertNotEqual(r['generation'],new['generation']);self.assertTrue(w.pid.view()['pending'])

    def test_single_flight_and_cancellation_release(self):
        w=worker();r=w.request_pid()
        with self.assertRaises(ValueError):w.request_pid()
        w.cancel_pid('STOP');w.pid_command(r);self.assertEqual(w.motor.read_pid.call_count,0)
        self.assertFalse(w.pid.view()['pending']);execute(w);self.assertFalse(w.pid.view()['pending'])

    def test_each_stage_and_result_survives_refresh_view(self):
        w=worker();execute(w);w.pid.edit('speed_kp','200');w.pid.drafts['observer_c1']='-9'
        r=w.request_pid(('speed_kp',100,200));self.assertEqual(w.pid.view()['rows']['speed_kp'],'寫入中')
        w.motor.read_pid.side_effect=[{'speed_kp':100},{'speed_kp':200}];w.pid_command(r)
        events=replies(w);self.assertEqual(events[0]['phase'],'verifying')
        w.pid.accept(events[0]);self.assertEqual(w.pid.view()['rows']['speed_kp'],'讀回驗證中')
        w.pid.accept(events[1]);self.assertEqual(w.pid.view()['rows']['speed_kp'],'已驗證')
        self.assertEqual(w.pid.view()['drafts']['observer_c1'],'-9')
        self.assertIn('Speed Kp 100 → 200',w.pid.view()['status'])
        self.assertFalse(w.pid_unverified);self.assertFalse(w.pid.view()['pending'])

    def test_write_exception_and_read_failure_release_pending(self):
        w=worker();w.motor.write_pid.side_effect=TimeoutError('write timeout')
        execute(w,('speed_kp',100,200))
        self.assertTrue(w.pid_unverified);self.assertFalse(w.pid.view()['pending'])
        self.assertEqual(w.pid.view()['rows']['speed_kp'],'未確認')
        self.assertIn('Speed Kp 100 → 200',w.pid.view()['status']);self.assertIn('write timeout',w.pid.view()['status'])
        w.motor.read_pid.side_effect=TimeoutError('read timeout');execute(w)
        self.assertTrue(w.pid_unverified);self.assertFalse(w.pid.view()['pending'])

    def test_safety_expected_readback_and_readonly(self):
        for sample,update,expected_error in [
            (dict(state=6,rpm=1500,faults=0),('speed_kp',100,200),'IDLE'),
            (dict(state=0,rpm=0,faults=1),('speed_kp',100,200),'IDLE'),
            (dict(state=0,rpm=0,faults=0),('speed_kp',99,200),'已變更'),
            (dict(state=0,rpm=0,faults=0),('iq_reference_raw',0,1),'僅供讀取'),
            (dict(state=0,rpm=0,faults=0),('speed_kp_div',128,129),'除數')]:
            with self.subTest(update=update,sample=sample):
                w = worker()
                w.motor.sample.return_value = sample
                if update[0] in ('iq_reference_raw', 'speed_kp_div'):
                    with self.assertRaisesRegex(ValueError, expected_error):
                        w.request_pid(update)
                    w.motor.sample.assert_not_called()
                    w.motor.read_pid.assert_not_called()
                    self.assertTrue(w.commands.empty())
                else:
                    event = execute(w, update)
                    self.assertIn(expected_error, event['error'])
                w.motor.write_pid.assert_not_called()
                self.assertFalse(w.pid.view()['pending'])
        w=worker();e=execute(w,('speed_kp',100,200));self.assertIn('讀回不符',e['error']);self.assertTrue(w.pid_unverified)

    def test_stop_before_write_and_wrong_mode_or_recording(self):
        for mode,file in [('SIMULATION',None),('REAL',object())]:
            w=worker();w.mode=mode;w.file=file
            if mode != 'REAL':
                with self.assertRaisesRegex(ValueError,'連線實機'):w.request_pid(('speed_kp',100,200))
            else:execute(w,('speed_kp',100,200))
            w.motor.write_pid.assert_not_called()
        w=worker()
        def before():w.cancel_pid('STOP');return {'speed_kp':100}
        w.motor.read_pid.side_effect=before;r=w.request_pid(('speed_kp',100,200));w.pid_command(r)
        w.motor.write_pid.assert_not_called();self.assertFalse(w.pid_unverified)

    def test_unverified_blocks_experiment(self):
        from config import defaults
        w=worker();execute(w,('speed_kp',100,200))
        with self.assertRaisesRegex(ValueError,'未確認'):w.begin(defaults())

    def test_error_from_old_request_does_not_clear_new(self):
        w=worker();r=w.request_pid();w.cancel_pid('disconnect');new=w.request_pid()
        self.assertFalse(w.pid.accept(dict(r,phase='error',error='late timeout')))
        self.assertEqual(w.pid.active['id'],new['id'])
