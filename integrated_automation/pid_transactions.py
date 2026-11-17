"""PID transaction state shared by the controller and UI; no hardware I/O here."""
from threading import RLock
from pid_settings import PARAMETERS, encode_value

class PidTransactions:
    def __init__(self):
        self.lock = RLock()
        self.generation = 0
        self.sequence = 0
        self.active = None
        self.values = {}
        self.drafts = {}
        self.rows = {}
        self.status = '請先讀取板端參數。'
        self.unverified = False
        self.blocked = False
        self.revision = 0
        self.experiment = False
        self.hint = ''
        self.important = False

    def matches(self, request):
        return bool(self.active and request and
                    request['id'] == self.active['id'] and
                    request['generation'] == self.generation == self.active['generation'])

    def reserve(self, update=None):
        with self.lock:
            if self.active or self.blocked or self.experiment:
                raise ValueError('PID 交易、實驗或連線轉換尚未完成。')
            # Validate before any state mutation: rejected input must not strand
            # pending or erase a previous result. Freeze caller-owned lists too.
            if update is not None:
                if not isinstance(update, (tuple, list)) or len(update) != 3:
                    raise ValueError('寫入請求須包含參數、舊值與新值。')
                key, expected, value = update
                if not isinstance(key, str) or key not in PARAMETERS:
                    raise ValueError('未知的 PID 參數。')
                if type(expected) is not int:
                    raise ValueError('expected 舊值須為整數。')
                encode_value(key, value)
                update = (key, expected, value)
            request = dict(id=self.sequence + 1, generation=self.generation, update=update)
            description = self.describe(request)
            self.hint = ''
            self.important = False
            self.sequence += 1
            self.active = dict(request, sent=False)
            if update:
                self.rows[update[0]] = '寫入中'
            self.status = description + '：已排入交易。'
            return request

    @staticmethod
    def describe(request):
        prefix = f"PID #{request['id']} / G{request['generation']}"
        update = request.get('update')
        return prefix + (f' {PARAMETERS[update[0]][1]} {update[1]} → {update[2]}' if update else ' 讀取板端')

    def mark_sent(self, request):
        with self.lock:
            if not self.matches(request):
                raise ValueError('交易已失效，未再送出寫入。')
            self.active['sent'] = True
            self.unverified = True

    def invalidate(self, reason, blocked=None):
        with self.lock:
            active = self.active
            if active and active.get('sent'):
                self.unverified = True
            self.hint = ''
            self.important = True
            self.generation += 1
            self.active = None
            self.values = {}
            self.drafts = {}
            self.rows = {}
            detail = self.describe(active) + '：' if active else ''
            if active and active.get('update'):
                self.rows[active['update'][0]] = '未確認' if active.get('sent') else '已取消'
            self.status = detail + reason + ('；寫入可能已送出，結果未確認，請重新讀取。' if self.unverified else '；請重新讀取。')
            if blocked is not None:
                self.blocked = blocked
            self.revision += 1

    def accept(self, event):
        with self.lock:
            if not self.matches(event):
                return False
            update = self.active['update']
            phase = event['phase']
            if phase == 'verifying':
                if update:self.rows[update[0]] = '讀回驗證中'
                self.status = self.describe(event) + '：讀回驗證中…'
                return True
            if phase not in ('success', 'error'):
                return False
            old = self.values
            self.hint = ''
            self.important = phase == 'error'
            if phase == 'success':
                self.values = dict(event['values'])
                for key, value in self.values.items():
                    if key not in old or self.drafts.get(key, str(old[key])) == str(old[key]) or (update and key == update[0]):
                        self.drafts[key] = str(value)
                self.unverified = False
                # A fresh read resolves uncertainty, but is not a successful write.
                if not update:self.rows = {}
                if update:self.rows[update[0]] = '已驗證'
                self.status = self.describe(event) + ('：寫入成功，已讀回驗證。' if update else '：已讀取板端。')
            else:
                self.values = {}
                self.drafts = {}
                self.rows = {}
                if update:self.rows[update[0]] = '未確認' if self.unverified else '失敗'
                self.status = self.describe(event) + '：' + ('未確認' if self.unverified else '失敗') + '；' + event['error']
            self.active = None
            self.revision += 1
            return True

    def _message_is_protected(self):
        # Internal callers hold lock; input hints must not hide safety/results.
        return bool(self.important or self.unverified or self.active)

    def view(self):
        with self.lock:
            message = self.status if self._message_is_protected() else (self.hint or self.status)
            return dict(
                values=dict(self.values), drafts=dict(self.drafts), rows=dict(self.rows),
                pending=bool(self.active), status=message, revision=self.revision,
                experiment=self.experiment, blocked=self.blocked, unverified=self.unverified,
            )

    def operation_hint(self, text):
        with self.lock:
            if not self._message_is_protected():
                self.hint = text

    def clear_hint(self):
        with self.lock:
            self.hint = ''

    def start_reason(self):
        with self.lock:
            if self.blocked:
                return '連線轉換中，暫時不能開始實驗。'
            if self.active:
                return 'PID 交易尚未完成，請等待回覆被確認後再開始。'
            if self.unverified:
                return 'PID／PLL 寫入狀態未確認，請先重新讀取板端數值。'
            if self.experiment:
                return '實驗已取得執行資格，請等待上一輪結束。'
            return ''

    def reserve_experiment(self):
        """Reserve under the PID lock; Controller remains the lifecycle owner."""
        with self.lock:
            reason = self.start_reason()
            if reason:
                raise ValueError(reason)
            self.experiment = True
            return self.generation

    def release_experiment(self):
        """Release experiment eligibility only, never write uncertainty."""
        with self.lock:
            self.experiment = False

    def edit(self, key, text):
        with self.lock:
            if self.active or key not in self.values or self.blocked:return
            if self.drafts.get(key) != text:
                self.drafts[key] = text
                self.rows.pop(key, None)
                try:
                    encode_value(key, int(text))
                except ValueError:
                    pass
                else:
                    self.hint = '' 
