"""Motor owner/state machine. Sensor workers own their ports; only this thread writes CSV."""
import csv,json,math,queue,threading,time
from collections import deque
from statistics import mean
from pathlib import Path
from datetime import datetime,timezone
from protocol import Motor,SimMotor,TELEMETRY_FIELDS
from sensors import SensorWorker
from session_files import create_session_folder, session_names
from propellers import MOUNTS, direction_factors, outcome_tag, profile, run_label
from summarize import summarize
from report import generate_report
from pid_settings import encode_value
from pid_transactions import PidTransactions

FIELDS=['utc_time','elapsed_s','request_start_s','roundtrip_ms','row_type','device','channel',
 'mode','stage','stage_index','target_rpm','estimated_rpm','reference_rpm','status','faults_hex',
 'raw_signed_int32','scale','raw_zero','scaled_value','unit','supply_V','supply_A','supply_W',
 'supply_set_V','supply_limit_A','supply_current_limited','force_N','force_gf','torque_Nm','board_bus_V','board_temp_C','motor_power_W',
 'iq_raw','id_raw','current_scale_A_per_count','iq_A','id_A','motor_rx_hex',
 'rx_hex','rx_text','reason','detail']

def validate_plan(c):
    for k in ('ramp_ms','dwell_s','baseline_s','poststop_s','max_rpm','reach_timeout_s','force_interval','psu_interval'):
        if not math.isfinite(c[k]):raise ValueError(k+' 必須為有限數字')
    if not 1500<=c['max_rpm']<=7100:raise ValueError('最高轉速1500–7100')
    if not c['speeds'] or len(c['speeds'])>200:raise ValueError('需1–200組轉速')
    if any(not isinstance(x,int) or not 960<=x<=c['max_rpm'] for x in c['speeds']):raise ValueError('轉速960至本次上限')
    if not 500<=c['ramp_ms']<=60000 or int(c['ramp_ms'])!=c['ramp_ms']:raise ValueError('Ramp500–60000整數毫秒')
    if not .5<=c['dwell_s']<=3600:raise ValueError('停留0.5–3600秒')
    if not 1<=c['baseline_s']<=300 or not 1<=c['poststop_s']<=300:raise ValueError('前後記錄1–300秒')
    if not c['ramp_ms']/1000+3<=c['reach_timeout_s']<=180:raise ValueError('到速期限需至少Ramp+3秒且不超過180秒')
    if not .05<=c['force_interval']<=10 or not .2<=c['psu_interval']<=10:raise ValueError('擷取間隔超出範圍')
    ports=[c['port'].upper().strip()]
    if c['force_enabled']:ports.append(c['force_port'].upper().strip())
    if c['psu_enabled'] and c['psu_backend']=='SERIAL':ports.append(c['psu_resource'].upper().strip())
    if len(ports)!=len(set(ports)) or not all(ports):raise ValueError('COM埠不可空白或重複')
    if c['force_parity'] not in ('N','E','O') or c['force_stopbits'] not in (1,2):raise ValueError('力規格式錯誤')
    if c['force_order'] not in ('HH-LL','LL-HH') or not 1<=c['force_addr']<=247:raise ValueError('力規字序或站號錯誤')
    if c['force_baud'] not in (1200,2400,4800,9600,19200,38400,57600,115200):raise ValueError('力規鮑率錯誤')
    if c['psu_backend'] not in ('VISA','SERIAL'):raise ValueError('電供連線方式VISA/SERIAL')
    if c['psu_enabled'] and not c['psu_resource'].strip():raise ValueError('請填電供VISA資源或COM埠')
    if c['psu_enabled'] and c['psu_backend']=='VISA' and c['psu_resource'].upper().startswith('ASRL'):
        raise ValueError('序列埠請選SERIAL並填COM埠，以檢查是否與馬達或力規重複')
    if c['psu_channels'] not in ([1],[1,2]):raise ValueError('電供通道為1或1,2')
    if c['psu_baud'] not in (9600,19200,38400,57600,115200):raise ValueError('電供鮑率需核對面板設定')
    for k in ('zero1','zero2'):
        if not math.isfinite(c.get(k,0.)):raise ValueError('原始零點必須為有限數字')
    for k in ('scale1','scale2'):
        if c[k] is not None and not math.isfinite(c[k]):raise ValueError('倍率必須為有限數字')
    if any(c.get(k,0) not in (0,1,2) for k in ('thrust_channel','torque_channel')):raise ValueError('推力／扭矩通道0未指定或1/2')
    if c.get('thrust_channel',0) and c.get('thrust_channel')==c.get('torque_channel'):raise ValueError('推力與扭矩不能指定同一通道')
    if not isinstance(c.get('run_name',''),str):raise ValueError('實驗名稱必須為文字')
    if not c['folder'].strip():raise ValueError('輸出資料夾不可空白')

class Controller(threading.Thread):
    @property
    def deadline(self):return self._deadline
    @deadline.setter
    def deadline(self,value):
        self._deadline=value;self.phase_duration=max(0,value-time.monotonic())
    @property
    def phase(self):return self._phase
    @phase.setter
    def phase(self,value):
        self._phase=value
        if not hasattr(self,'phase_history'):self.phase_history=[]
        self.phase_history.append((time.monotonic(),value,getattr(self,'index',-1)+1,getattr(self,'target',0)))
        if not getattr(self,'file',None):self.phase_history=self.phase_history[-2:]
    def __init__(self,motor_factory=None,sensor_factory=None):
        super().__init__(daemon=True)
        self.commands=queue.Queue();self.events=queue.Queue();self.sensor_q=queue.Queue(maxsize=2000)
        self.overflow=threading.Event();self.stop_event=threading.Event();self.quit_event=threading.Event()
        self.psu_worker=None;self.psu_cfg=None;self.psu_pending=None;self.psu_q=queue.Queue(maxsize=2000)
        self.force_worker=None;self.force_cfg=None;self.force_state='stopped';self.force_stop_requested=False
        self.tare_samples = {'1': deque(maxlen=100), '2': deque(maxlen=100)}
        self.stopped_sample_at = None
        self.motor=None;self.file=None;self.workers=[];self.phase='disconnected';self.mode='SIMULATION'
        self.target=0;self.index=-1;self.latest={};self.motor_factory=motor_factory or Motor
        self.pid = PidTransactions()
        self.disconnect_requested = False
        self.sensor_factory=sensor_factory;self.close_after=False;self.start()
    def emit(self,k,v):self.events.put((k,v))
    def submit(self, k, v=None):
        with self.pid.lock:
            if k == 'disconnect':
                # This intent survives STOP's queue drain until disconnect completes.
                self.disconnect_requested = True
                self.cancel_pid('已要求斷線，等待停止及紀錄處理', blocked=True)
            self.commands.put((k, v))

    def start_block_reason(self):
        with self.pid.lock:
            reason = self.pid.start_reason()
            if reason:
                return reason
            if self.stop_event.is_set() or self.quit_event.is_set():
                return '停止要求處理中，不能開始實驗。'
            if not self.motor:
                return '請先連線馬達。'
            return ''

    @property
    def pid(self):
        if not hasattr(self, '_pid'):self._pid = PidTransactions()
        return self._pid

    @pid.setter
    def pid(self, value):self._pid = value

    @property
    def pid_unverified(self):return self.pid.view()['unverified']

    @property
    def pid_snapshot(self):return self.pid.view()['values'] or None

    def cancel_pid(self, reason, blocked=None):
        self.pid.invalidate(reason, blocked)
        self.emit('log', self.pid.view()['status'])

    def request_pid(self, update=None):
        with self.pid.lock:
            if self.stop_event.is_set() or self.quit_event.is_set():
                raise ValueError('已提出停止要求，請稍後重新讀取。')
            if not self.motor or self.mode != 'REAL':
                raise ValueError('請先連線實機。')
            request = self.pid.reserve(update)
            self.commands.put(('pid_write' if update else 'pid_read', request))
            self.emit('log', self.pid.describe(request) + '：送出請求。')
            return request

    def write(self,row):
        if not self.file:return
        r=dict(row);recv=r.pop('receive_mono',time.monotonic());start=r.pop('request_start_mono',None)
        r.setdefault('utc_time',datetime.now(timezone.utc).isoformat())
        r['elapsed_s']=round(recv-self.origin,6)
        if start is not None:r.update(request_start_s=round(start-self.origin,6),roundtrip_ms=round((recv-start)*1000,3))
        phase,index,target=self.phase,self.index+1,self.target
        for at,ph,idx,tgt in reversed(self.phase_history):
            if at<=recv:phase,index,target=ph,idx,tgt;break
        r.setdefault('stage',phase);r.setdefault('stage_index',index);r.setdefault('target_rpm',target)
        r['mode']=self.mode
        self.writer.writerow(r);self.file.flush()
    def event(self,reason,detail=''):
        self.write(dict(row_type='event',device='controller',reason=reason,detail=detail))
        self.emit('task_event',dict(reason=reason,detail=detail,stage_index=self.index+1))
        self.emit('log',reason+(': '+detail if detail else ''))
    FORCE_COMM=('force_port','force_baud','force_addr','force_parity','force_stopbits','force_order','force_interval')
    def start_force(self,c,mode=None):
        validate_plan(c)
        mode=mode or self.mode
        if mode=='SIMULATION':
            if self.force_worker and self.force_worker.is_alive():raise ValueError('請先停止實機力規，再切換模擬')
            self.emit('force_state',dict(state='simulation',detail='模擬不讀實體力規'));return
        if self.motor and self.mode!=mode:raise ValueError('力規與馬達模式不一致，請先斷線')
        if not c['force_enabled']:raise ValueError('力規未啟用，請先在裝置設定啟用')
        if self.force_worker and self.force_worker.is_alive():
            if self.force_worker.stop_event.is_set():raise ValueError('力規正在釋放連接埠，請稍後再試')
            if any(c[k]!=self.force_cfg[k] for k in self.FORCE_COMM):raise ValueError('力規通訊設定已變更；請先停止讀取再重新開始')
            self.force_cfg=dict(c);self.force_worker.cfg=dict(c)
            return
        if not self.motor:self.mode=mode
        self.clear_tare_samples()
        self.force_cfg=dict(c);self.force_stop_requested=False
        factory=None if not self.sensor_factory else self.sensor_factory['force']
        self.force_worker=SensorWorker('force',dict(c),self.sensor_q,self.overflow,factory)
        self.force_state='connecting';self.emit('force_state',dict(state='connecting',detail='正在開啟 '+c['force_port']))
        self.force_worker.start()
    def stop_force(self):
        if self.file:raise ValueError('實驗期間不可停止力規；請先STOP結束實驗')
        if self.force_worker and self.force_worker.is_alive():
            self.force_stop_requested=True;self.force_worker.request_stop()
            self.force_state='stopping';self.emit('force_state',dict(state='stopping',detail='正在釋放連接埠'))
        else:
            self.force_worker=None;self.force_state='stopped';self.emit('force_state',dict(state='stopped',detail='力規未啟動／已停止'))
    def check_force_exit(self):
        if self.force_worker and not self.force_worker.is_alive():
            self.force_worker=None
            if self.force_stop_requested:
                self.force_state='stopped';self.emit('force_state',dict(state='stopped',detail='已停止，連接埠已釋放'))
            elif self.force_state!='error':
                self.force_state='error';self.emit('force_state',dict(state='error',detail='擷取意外結束，請重新開始讀取'))
    def apply_force(self,c):
        if self.file:raise ValueError('實驗中鎖定校正設定')
        validate_plan(c)
        if self.force_worker and self.force_worker.is_alive():self.start_force(c,'REAL')
        self.emit('log','力規換算設定已套用；讀取保持運作。')
    PSU_COMM = ('psu_backend','psu_resource','psu_baud','psu_channels','psu_interval')

    def apply_psu(self, c, mode=None):
        if self.file:
            raise ValueError('實驗期間不可變更電供擷取設定')
        validate_plan(c)
        mode = mode or self.mode
        if self.motor and mode != self.mode:
            raise ValueError('請先斷線再切換模式')
        if mode == 'SIMULATION' or not c['psu_enabled']:
            self.psu_pending = None
            worker = getattr(self, 'psu_worker', None)
            if worker:
                worker.request_stop()
            self.emit('psu_state', dict(state='stopped',detail='未啟用實體電供擷取'))
            return
        if not self.motor:
            self.mode = mode
        worker = getattr(self, 'psu_worker', None)
        if worker and worker.is_alive():
            if not worker.stop_event.is_set() and all(c[k] == self.psu_cfg[k] for k in self.PSU_COMM):
                return
            self.psu_pending = dict(c)
            worker.request_stop()
            self.emit('psu_state',dict(state='stopping',detail='正在釋放舊連線，完成後套用新設定'))
            return
        self._open_psu(c)

    def _open_psu(self, c):
        self.psu_pending = None
        self.psu_cfg = dict(c)
        self.psu_q = queue.Queue(maxsize=2000)
        factory = None if not self.sensor_factory else self.sensor_factory['psu']
        self.psu_worker = SensorWorker('psu',dict(c),self.psu_q,self.overflow,factory)
        self.emit('psu_state',dict(state='connecting',detail='正在開啟 '+c['psu_resource']))
        self.psu_worker.start()

    def service_psu(self):
        worker = getattr(self,'psu_worker',None)
        if not worker:
            return
        # A stopped/replaced worker's queue must not refresh the display or CSV.
        while not self.psu_q.empty():
            row = self.psu_q.get_nowait()
            if not worker.stop_event.is_set():
                if self.file and (not self.cfg['psu_enabled'] or (row.get('row_type','measurement')=='measurement' and row.get('channel') not in self.cfg['psu_channels'])):
                    continue
                try:self.sensor_q.put_nowait(row)
                except queue.Full:self.overflow.set();worker.request_stop();break
        if not worker.is_alive():
            self.psu_worker = None
            if self.psu_pending is not None:
                self._open_psu(self.psu_pending)

    def clear_tare_samples(self):
        for samples in self.tare_samples.values():
            samples.clear()

    def tare_force(self, channel):
        if self.file or self.mode != 'REAL' or not self.motor:
            raise ValueError('歸零需要連線的實機馬達，且目前未在記錄。')
        if self.force_state != 'reading' or not self.force_worker or not self.force_worker.is_alive() or self.force_worker.stop_event.is_set():
            raise ValueError('請先開始力規讀取。')
        motor = self.motor.sample()
        now = time.monotonic()
        if motor['state'] != 0 or motor['rpm'] != 0 or motor['faults']:
            self.clear_tare_samples()
            raise ValueError('請確認馬達已停穩並回到無故障 IDLE。')
        samples = [(stamp, raw) for stamp, raw in self.tare_samples[str(channel)] if now-stamp <= 1.5]
        if len(samples) < 3 or samples[-1][0]-samples[0][0] < .5 or now-samples[-1][0] > .5:
            raise ValueError('有效樣本不足。請等力規持續讀取後再試。')
        counts = [raw for _, raw in samples]
        if max(counts)-min(counts) > 2:
            raise ValueError('力規讀值尚未穩定（樣本差超過 2 count）。')
        zero = mean(counts)
        self.apply_force(dict(self.force_cfg, **{f'zero{channel}': zero}))
        self.emit('force_tared', (channel, zero))

    def _check_pid_write(self, update):
        key, expected, value = update
        encode_value(key, value)
        sample = self.motor.sample()
        if sample['state'] != 0 or sample['rpm'] != 0 or sample['faults']:
            raise ValueError('寫入需要無故障 IDLE 且回授為 0 rpm。')
        before = self.motor.read_pid()
        if before[key] != expected:
            raise ValueError('板端數值已變更，請重新讀取。')

    def pid_command(self, request):
        update = request['update']
        sent = False
        actual = None
        def valid():
            with self.pid.lock:
                if not self.pid.matches(request) or self.stop_event.is_set() or self.quit_event.is_set():
                    raise ValueError('STOP／連線變更使交易失效。')
        try:
            valid()
            if self.file or self.mode != 'REAL' or not self.motor:
                raise ValueError('請先連線實機，並結束實驗。')
            if update is not None:
                key, expected, value = update
                self._check_pid_write(update)
                with self.pid.lock:
                    valid()
                    self.pid.mark_sent(request)
                    sent = True
                # Do not hold the state lock across I/O: STOP must remain responsive.
                self.motor.write_pid(key, value)
                self.emit('pid_values', dict(request, phase='verifying'))
            actual = self.motor.read_pid()
            if update is not None and actual[key] != value:
                raise ValueError(f'讀回不符：要求 {value}，板端 {actual[key]}。請重新讀取確認。')
            valid()
            event = dict(request, phase='success', values=actual)
        except Exception as error:
            event = dict(request, phase='error', error=type(error).__name__ + ': ' + str(error))
        event.update(write_may_have_been_sent=sent, observed_values=actual)
        # Even an invalidated write produces an audit result; only a matching
        # current request may install a snapshot or clear unverified in accept().
        self.emit('log', self.pid.describe(request) + '：' + str(event))
        self.emit('pid_values', event)

    def begin(self, c):
        # Reserve before any device I/O or file creation. The same lock protects
        # PID reservation, but is released before running the experiment setup.
        with self.pid.lock:
            reason = self.start_block_reason()
            if reason:
                raise ValueError(reason)
            generation = self.pid.reserve_experiment()
        try:
            self._begin(c, generation)
        finally:
            if not self.file:
                self.pid.release_experiment()

    def _begin(self, c, generation):
        validate_plan(c)
        if any(w.is_alive() for w in self.workers):
            raise ValueError('上一輪資料擷取尚未結束，暫無法開始新測試。')
        if self.file or not self.motor:
            raise ValueError('請先連線並等待上一輪結束')
        s=self.motor.sample()
        if s['state']!=0 or s['faults'] or s['mode']!=3:
            raise ValueError(f"啟動條件未滿足：狀態={s['status']}；故障=0x{s['faults']:X}；控制模式={s['mode']}（SPEED應為3）")
        if self.mode=='SIMULATION' and self.force_worker and self.force_worker.is_alive():
            raise ValueError('模擬測試前請先停止實機力規')
        if self.mode == 'REAL' and c['psu_enabled']:
            worker = getattr(self,'psu_worker',None)
            if worker and worker.is_alive() and (worker.stop_event.is_set() or any(c[k]!=self.psu_cfg[k] for k in self.PSU_COMM)):
                raise ValueError('電供設定正在切換，請等待完成後再開始')
        self.cfg = dict(c)
        self.latest = {}
        self.target = 0
        self.index = -1
        self.ready = set()
        self.required = set()
        self.failed = False
        self.reason = ''
        self.stop_detail = ''
        self.stop_confirmed = False
        self.overflow.clear()
        while not self.sensor_q.empty():
            self.sensor_q.get_nowait()
        propeller=c.get('propeller')
        if propeller:
            propeller=profile(*(propeller[key] for key in ('dimension','blades','material','number')), propeller.get('rotation',''))
            if not propeller['rotation'] or c.get('mount') not in MOUNTS:
                raise ValueError('請先設定所選螺旋槳的旋向與本次安裝方向。')
            self.cfg['propeller']=propeller
        label=run_label(propeller['name']+'_'+MOUNTS[c['mount']],c['speeds']) if propeller else None
        pid_readback = self.motor.read_pid() if self.pid_snapshot is not None and self.mode == 'REAL' else None
        with self.pid.lock:
            if self.stop_event.is_set() or self.quit_event.is_set() or self.pid.blocked or self.pid.generation != generation:
                raise ValueError('啟動檢查期間狀態已變更，取消建立測次。')
        folder=create_session_folder(c['folder'],self.mode,c['speeds'],c.get('run_name',''),label_override=label)
        self.path=folder/'data.csv'
        factors = direction_factors(c.get('mount'), (propeller or {}).get('rotation'))
        metadata=dict(self.cfg,mode=self.mode,version='0.3.29',direction_factors=factors,
            pid_board_readback=pid_readback,firmware_scale_config=getattr(self.motor,'scale_config',None),
            conversion_gravity_m_s2=9.80665,firmware_identity='operator must verify; not read back',
            note='simulation never opens physical sensor ports; measured channels kept separate')
        self.path.with_suffix('.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        self.file = self.path.open('x', encoding='utf-8-sig', newline='')
        self.writer = csv.DictWriter(self.file, fieldnames=FIELDS)
        self.writer.writeheader()
        self.origin = time.monotonic()
        self.phase_history = []
        self.phase = 'preflight'
        self.deadline = self.origin + 12
        self.workers = []
        self.emit('session_folder',str(folder))
        self.event('session_begin', str(self.path))
        self.emit('force_reset', None)
        if self.mode=='REAL':
            for name in ('force','psu'):
                if c[name+'_enabled']:
                    channels=(1,2) if name=='force' else c['psu_channels']
                    for ch in channels:
                        fields=('raw_signed_int32',) if name=='force' else ('supply_V','supply_A','supply_W')
                        for f in fields:
                            self.required.add((name, str(ch), f))
                    factory=None if not self.sensor_factory else self.sensor_factory[name]
                    if name == 'force':
                        self.start_force(c)
                        continue
                    if not getattr(self,'psu_worker',None) or not self.psu_worker.is_alive():
                        self._open_psu(c)
        self.event('preflight','啟動前確認各通道資料；馬達尚未啟動')
    def drain(self):
        for _ in range(2000):
            try:r=self.sensor_q.get_nowait()
            except queue.Empty:break
            name=r['device'];ch=str(r.get('channel',''));typ=r.get('row_type','measurement');r['row_type']=typ
            in_session=bool(self.file) and r.get('receive_mono',time.monotonic())>=self.origin
            if in_session:self.write(r)
            if typ=='error':
                self.emit('log',name+' 錯誤：'+r['detail'])
                if name=='psu':self.emit('psu_state',dict(state='error',detail=r['detail']))
                if name=='force':
                    self.clear_tare_samples()
                    self.force_state='error';self.emit('force_state',dict(state='error',detail=r['detail']))
                if in_session and self.phase not in ('stopping','poststop'):self.halt(name+'_error',r['detail'])
            elif typ=='identity':
                if name=='psu':self.emit('psu_state',dict(state='reading',detail='已連線：'+r['detail']))
            elif typ=='measurement':
                for f in ('raw_signed_int32','supply_V','supply_A','supply_W'):
                    if f in r:
                        key=(name,ch,f);self.latest[key]=r['receive_mono']
                        if in_session:self.ready.add(key)
                if name=='force' and self.force_state=='connecting':
                    self.force_state='reading';self.emit('force_state',dict(state='reading',detail='持續監看中'))
                if (name=='force' and ch in self.tare_samples and not self.file
                        and self.stopped_sample_at is not None
                        and abs(r['receive_mono']-self.stopped_sample_at) <= .5
                        and 'raw_signed_int32' in r):
                    self.tare_samples[ch].append((r['receive_mono'], r['raw_signed_int32']))
                self.emit('sensor',r)
    def halt(self,reason,detail=''):
        if not self.file:
            if self.motor:
                try:self.motor.stop();self.emit('log','控制器已回覆停止指令。請確認馬達已停穩。')
                except Exception as e:self.emit('log','停止指令未獲確認，請依現場停機程序確認馬達已停穩：'+str(e))
            return
        if self.phase in ('stopping','poststop'):return
        self.reason=reason;self.stop_detail=detail;self.event('stop_requested',reason+(' '+detail if detail else ''))
        self.phase='stopping';self.deadline=time.monotonic()+5
        if self.motor:
            try:self.motor.stop();self.event('stop_command_ack');self.emit('log','控制器已回覆停止指令。')
            except Exception as e:self.event('stop_command_unconfirmed',str(e));self.emit('log','停止指令未獲控制器確認，請依現場停機程序確認馬達已停穩。')
        else:self.enter_post(False)
    def enter_post(self,confirmed):
        self.stop_confirmed=confirmed;self.phase='poststop';self.deadline=time.monotonic()+self.cfg['poststop_s']
        self.event('stop_state_confirmed' if confirmed else 'stop_state_unconfirmed',
            '控制狀態不等於機械停穩；繼續記錄力規')
    def finish(self):
        for w in self.workers:w.request_stop()
        for w in self.workers:w.join(1.2)
        self.drain();self.event('session_end',self.reason)
        self.file.close()
        self.file = None
        self.pid.release_experiment()
        self.workers = [w for w in self.workers if w.is_alive()]
        self.phase = 'idle' if self.motor else 'disconnected'
        propeller=self.cfg.get('propeller')
        tag=outcome_tag(self.reason,self.stop_detail) if propeller else ''
        if tag:
            folder=self.path.parent
            name=propeller['name']
            tagged_name=name+tag+folder.name[len(name):]
            try:
                for candidate in session_names(tagged_name):
                    destination=folder.with_name(candidate)
                    if destination.exists():continue
                    try:folder.rename(destination)
                    except FileExistsError:continue
                    self.path=destination/self.path.name
                    break
                else:raise FileExistsError(tagged_name)
            except OSError as exc:self.emit('log','無法標記輸出資料夾，原始紀錄已保存：'+str(exc))
        self.emit('log','CSV已保存：'+str(self.path))
        try:self.emit('log','摘要已保存：'+str(summarize(self.path,self.cfg)))
        except Exception as e:self.emit('log','原始CSV已保存，摘要建立失敗：'+str(e))
        self.emit('finished',str(self.path))
        # The report only reads closed files, outside the motor owner thread.
        report_thread=threading.Thread(target=self.build_report,args=(self.path,),name='Robi report',daemon=False)
        report_thread.start()
        if self.close_after:self.disconnect()
    def build_report(self,path):
        try:
            output=generate_report(path)
            self.emit('report_ready',str(output));self.emit('log','圖表報告已保存：'+str(output))
        except Exception as e:
            self.emit('report_error',dict(path=str(path),error=str(e)))
            self.emit('log','原始紀錄已保存，圖表報告建立失敗：'+str(e))
    def service_disconnect(self):
        if not getattr(self, 'disconnect_requested', False):
            return
        if self.file:
            self.close_after = True
            self.halt('disconnect_requested')
        else:
            self.disconnect()

    def disconnect(self):
        self.cancel_pid('正在斷線', blocked=True)
        try:
            if self.motor:
                self.halt('disconnect_idle')
                self.motor.close()
        finally:
            self.motor = None
            self.phase = 'disconnected'
            self.close_after = False
            with self.pid.lock:
                self.disconnect_requested = False
                # The transition has completed, not a forced PID unlock.
                self.pid.release_experiment()
                self.cancel_pid('馬達已斷線', blocked=False)
            self.emit('connected', False)

    def clear_stopped_commands(self):
        with self.pid.lock:
            self.cancel_pid('停止要求使交易失效')
            while not self.commands.empty():
                command, _ = self.commands.get_nowait()
                if command == 'disconnect':
                    self.disconnect_requested = True
                elif command not in ('pid_read', 'pid_write'):
                    # App may already show connecting/pending_begin/pending_tare.
                    self.emit('command_error', dict(command=command, error='STOP 已取消尚未執行的命令。'))
            self.stop_event.clear()

    def next_stage(self):
        if self.stop_event.is_set() or self.quit_event.is_set():self.halt('operator_stop');return
        self.index+=1
        if self.index>=len(self.cfg['speeds']):self.halt('sequence_complete');return
        self.target=self.cfg['speeds'][self.index];self.motor.ramp(self.target,self.cfg['ramp_ms'])
        self.phase='ramping';self.stable_since=None;self.deadline=time.monotonic()+self.cfg['reach_timeout_s'];self.event('stage_ramp')
    def advance(self,s,now):
        if not self.file:return
        if self.phase=='stopping':
            if s and s['state'] in (0,10,11):self.enter_post(True)
            elif now>=self.deadline:self.enter_post(False)
            return
        if self.phase=='poststop':
            if now>=self.deadline:self.finish()
            return
        if self.overflow.is_set():self.halt('sensor_queue_overflow');return
        if s is None:self.halt('motor_unavailable');return
        if s['faults'] or s['state'] in (10,11):self.halt('motor_fault',hex(s['faults']));return
        if self.phase!='preflight':
            for key in self.required:
                limit=max(2.,self.cfg['force_interval']*3) if key[0]=='force' else max(5.,self.cfg['psu_interval']*3)
                if now-self.latest.get(key,-1e30)>limit:self.halt('sensor_stale',str(key));return
        if self.phase=='preflight':
            if self.required<=self.ready:
                self.phase='baseline';self.deadline=now+self.cfg['baseline_s'];self.event('baseline_begin')
            elif now>self.deadline:self.halt('sensor_preflight_timeout')
        elif self.phase=='baseline':
            if s['state']!=0:self.halt('unexpected_motor_motion');return
            if now>=self.deadline:
                self.target=1500;self.motor.ramp(1500,self.cfg['ramp_ms'])
                if self.stop_event.is_set() or self.quit_event.is_set():self.halt('operator_stop_before_start');return
                self.motor.start();self.phase='starting';self.deadline=time.monotonic()+40;self.event('motor_start')
        elif self.phase=='starting':
            if s['state']==6:self.phase='startup_settle';self.stable_since=None;self.deadline=now+self.cfg['reach_timeout_s']
            elif now>self.deadline:self.halt('startup_timeout')
        elif self.phase in ('startup_settle','ramping'):
            if s['state']!=6:self.halt('unexpected_non_RUN');return
            if abs(s['rpm']-self.target)<=max(12,self.target*.01):
                if self.stable_since is None:self.stable_since=now
                if now-self.stable_since>=2:
                    if self.phase=='startup_settle':self.next_stage()
                    else:self.phase='dwelling';self.deadline=now+self.cfg['dwell_s'];self.event('dwell_begin')
            else:self.stable_since=None
            if self.phase in ('startup_settle','ramping') and now>self.deadline:self.halt('speed_not_reached')
        elif self.phase=='dwelling':
            if s['state']!=6 or abs(s['rpm']-self.target)>max(60,.05*self.target):self.halt('speed_deviation')
            elif now>=self.deadline:self.event('stage_timed_complete','未使用力規穩定判定');self.next_stage()
    def run(self):
        while True:
            k=None
            try:
                if self.stop_event.is_set() or self.quit_event.is_set():
                    self.clear_stopped_commands()
                    self.halt('application_close' if self.quit_event.is_set() else 'operator_stop')
                self.service_disconnect()
                if self.quit_event.is_set() and not self.file:break
                try:k,v=self.commands.get_nowait()
                except queue.Empty:k=None
                if k=='connect':
                    if self.motor:raise ValueError('請先斷線')
                    if v[0]=='SIMULATION' and self.force_worker and self.force_worker.is_alive():raise ValueError('請先停止實機力規，再切換模擬連線')
                    if v[0]=='SIMULATION' and getattr(self,'psu_worker',None) and self.psu_worker.is_alive():raise ValueError('請先在裝置設定停用電供擷取，再切換模擬連線')
                    self.cancel_pid('正在建立新的連線世代', blocked=True)
                    self.mode,self.port=v
                    self.emit('log','馬達連線握手中：'+self.port)
                    try:self.motor=SimMotor() if self.mode=='SIMULATION' else self.motor_factory(self.port)
                    except Exception as exc:
                        self.motor = None
                        self.cancel_pid('連線失敗', blocked=False)
                        self.emit('connected', False)
                        self.emit('connect_result', dict(ok=False, error=type(exc).__name__ + ': ' + str(exc)))
                        raise
                    with self.pid.lock:
                        self.cancel_pid('已連線', blocked=self.disconnect_requested)
                    self.emit('connect_result',dict(ok=True))
                    self.phase='idle';self.emit('connected',True);self.emit('log','已連線，尚未啟動馬達')
                elif k=='psu_apply':self.apply_psu(v[1],v[0])
                elif k=='force_start':self.start_force(v[1],v[0])
                elif k=='force_stop':self.stop_force()
                elif k=='force_apply':self.apply_force(v)
                elif k in ('pid_read','pid_write'):self.pid_command(v)
                elif k=='force_tare':self.tare_force(v)
                elif k=='begin':self.begin(v)
                elif k=='finish_poststop':
                    if self.file and self.phase=='poststop' and self.path.parent==v:
                        self.event('poststop_ended_by_operator','操作者提前結束停機後記錄')
                        self.finish()
                elif k=='ack':
                    if not self.motor or self.file:raise ValueError('僅可在未測試且已連線時清除故障')
                    self.motor.ack()
                    self.emit('fault_ack',None)
                elif k == 'disconnect':
                    self.service_disconnect()
                self.service_psu();self.drain();self.check_force_exit();s=None
                if self.motor:
                    a=time.monotonic()
                    try:
                        s=self.motor.sample();b=time.monotonic()
                        self.write(dict(row_type='measurement',device='motor',receive_mono=b,request_start_mono=a,
                            estimated_rpm=s['rpm'],reference_rpm=s['reference'],status=s['status'],faults_hex=hex(s['faults']),**{k:s.get(k,'') for k in TELEMETRY_FIELDS}))
                    except Exception as e:
                        self.emit('log','馬達讀取失敗：'+str(e))
                        if self.file:
                            self.event('motor_communication_error',str(e));self.halt('motor_communication_error',str(e))
                        self.cancel_pid('馬達通訊失敗，連線已中斷', blocked=False)
                        self.motor.close();self.motor=None;self.emit('connected',False)
                if s and not self.file and s['state']==0 and s['rpm']==0 and not s['faults']:
                    self.stopped_sample_at = b
                else:
                    self.stopped_sample_at = None
                    self.clear_tare_samples()
                self.advance(s,time.monotonic())
                now=time.monotonic();ages={'/'.join(k):round(now-t,3) for k,t in self.latest.items()}
                self.emit('sample',dict(sample=s,sample_mono=b if s is not None else now,mode=self.mode,phase=self.phase,target=self.target,
                    stage_index=self.index+1,phase_duration=getattr(self,'phase_duration',0),remaining=max(0,getattr(self,'deadline',now)-now) if self.file else 0,ages=ages,busy=bool(self.file)))
            except ValueError as e:
                self.emit('command_error',dict(command=k,error=str(e)))
                self.emit('log','設定／資料錯誤：'+str(e))
                if self.file:self.halt('validation_error',str(e))
            except Exception as e:
                self.emit('command_error',dict(command=k,error=str(e)))
                self.emit('log','錯誤：'+str(e))
                if self.file:
                    try:self.halt('controller_error',str(e))
                    except Exception:
                        self.emit('log','記錄／停止流程失敗，已中止；請用實體斷電確認停機。')
                        # Disk failures must not leave the state machine issuing further ramps.
                        if self.motor:
                            try:self.motor.stop()
                            except Exception:pass
                        for w in self.workers:w.request_stop()
                        try:self.file.close()
                        except Exception:pass
                        self.file = None
                        with self.pid.lock:
                            self.pid.release_experiment()
                        self.phase = 'idle' if self.motor else 'disconnected'
                else:self.phase='idle' if self.motor else 'disconnected'
            self.quit_event.wait(.1) if not self.quit_event.is_set() else time.sleep(.1)
        for w in self.workers:w.request_stop()
        if self.force_worker:
            self.force_worker.request_stop();self.force_worker.join(1.2)
        if getattr(self,'psu_worker',None):
            self.psu_worker.request_stop();self.psu_worker.join(2)
        if self.motor:self.motor.close()
