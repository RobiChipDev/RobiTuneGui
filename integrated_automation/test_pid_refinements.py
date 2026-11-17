"""Focused .26 regressions: atomic input handling and observable thread outcomes."""
import queue
import threading
import unittest
from unittest.mock import patch
from pid_transactions import PidTransactions


def assert_competition(case, state):
    ready = threading.Barrier(3)
    outcomes = queue.Queue()

    def attempt(name, reserve):
        try:
            ready.wait(timeout=3)
            reserve()
        except ValueError as error:
            outcomes.put((name, 'rejected', str(error)))
        except BaseException as error:
            outcomes.put((name, 'unexpected', repr(error)))
        else:
            outcomes.put((name, 'acquired', ''))

    threads = [threading.Thread(target=attempt, args=('pid', state.reserve)),
               threading.Thread(target=attempt, args=('experiment', state.reserve_experiment))]
    for thread in threads:
        thread.start()
    try:
        ready.wait(timeout=3)
    finally:
        for thread in threads:
            thread.join(4)
        case.assertFalse(any(t.is_alive() for t in threads), 'reservation thread did not terminate')
    results = [outcomes.get_nowait() for _ in range(outcomes.qsize())]
    case.assertEqual(len(results), 2, results)
    case.assertEqual({name for name, _, _ in results}, {'pid', 'experiment'})
    case.assertFalse([r for r in results if r[1] == 'unexpected'], results)
    case.assertEqual(sum(kind == 'acquired' for _, kind, _ in results), 1, results)
    rejected = [r for r in results if r[1] == 'rejected']
    case.assertEqual(len(rejected), 1, results)
    case.assertIn(rejected[0][2], ('PID 交易、實驗或連線轉換尚未完成。',
                                 'PID 交易尚未完成，請等待回覆被確認後再開始。'))
    case.assertNotEqual(bool(state.active), state.experiment)


class RefinementTests(unittest.TestCase):
    def test_invalid_inputs_are_atomic_and_recoverable(self):
        invalid = [(), ('speed_kp',), 'bad', 1, {'key': 'speed_kp'},
                   ('unknown', 0, 1), ([], 0, 1), ('speed_kp', True, 1),
                   ('speed_kp', '100', 101), ('speed_kp', 100, True),
                   ('speed_kp', 100, 32768), ('speed_kp', 100, -1),
                   ('speed_kp_div', 128, 3), ('iq_reference_raw', 0, 1)]
        for update in invalid:
            with self.subTest(update=update):
                state = PidTransactions()
                state.operation_hint('preserve hint')
                before = state.view()
                with self.assertRaises(ValueError):
                    state.reserve(update)
                self.assertEqual(state.view(), before)
                self.assertEqual(state.sequence, 0)
                request = state.reserve()
                self.assertTrue(state.accept(dict(request, phase='success', values={'speed_kp': 100})))
                self.assertFalse(state.view()['pending'])

    def test_invalid_input_does_not_damage_existing_transaction(self):
        state = PidTransactions()
        request = state.reserve(('speed_kp', 100, 101))
        state.mark_sent(request)
        before, active = state.view(), dict(state.active)
        with self.assertRaises(ValueError):
            state.reserve(('unknown', 0, 1))
        self.assertEqual(state.view(), before)
        self.assertEqual(state.active, active)
        self.assertTrue(state.accept(dict(request, phase='success', values={'speed_kp': 101})))

    def test_update_list_is_copied_and_signed_divisor_values_remain_valid(self):
        state = PidTransactions()
        update = ['observer_c1', -100, -101]
        request = state.reserve(update)
        update[2] = 999
        self.assertEqual(request['update'], ('observer_c1', -100, -101))
        state.invalidate('test')
        state.reserve(('speed_kp_div', 128, 32768))

    def test_competing_reservations_report_both_results(self):
        assert_competition(self, PidTransactions())

    def test_injected_runtime_error_makes_competition_assertion_fail(self):
        # This is a test-of-the-test; the expected assertion is NOT a normal
        # transaction failure or a hardware fault.
        state = PidTransactions()
        with patch.object(state, 'reserve_experiment', side_effect=RuntimeError('injected audit fault')):
            with self.assertRaisesRegex(AssertionError, 'RuntimeError'):
                assert_competition(self, state)

    def test_release_preserves_uncertainty_and_reservation_can_recover(self):
        state = PidTransactions()
        state.reserve_experiment()
        state.unverified = True
        state.release_experiment()
        self.assertFalse(state.experiment)
        self.assertTrue(state.unverified)
        with self.assertRaises(ValueError):
            state.reserve_experiment()
        request = state.reserve()
        state.accept(dict(request, phase='success', values={'speed_kp': 100}))
        self.assertEqual(state.reserve_experiment(), state.generation)
        state.release_experiment()

    def test_finished_wait_matches_run_and_has_explicit_timeout(self):
        from pathlib import Path
        from types import SimpleNamespace
        from test_v03 import Tests
        fixture = Tests()
        events = queue.Queue()
        events.put(('finished', '/other/data.csv'))
        events.put(('finished', '/target/data.csv'))
        fixture.wait_finished(SimpleNamespace(events=events), Path('/target/data.csv'), timeout=1)
        self.assertTrue(events.empty())
        with self.assertRaisesRegex(AssertionError, 'timed out waiting for finished'):
            fixture.wait_finished(SimpleNamespace(events=events), Path('/target/data.csv'), timeout=.01)

    def test_available_reads_one_shared_snapshot(self):
        from test_pid_dialog import DialogTests
        fixture = DialogTests()
        fixture.setUp()
        try:
            with patch.object(fixture.d.transaction, 'view', wraps=fixture.d.transaction.view) as view:
                self.assertTrue(fixture.d.available())
                self.assertEqual(view.call_count, 1)
        finally:
            fixture.doCleanups()
