import csv,json,queue,tempfile,threading,time,unittest
from pathlib import Path
from config import defaults
from controller import Controller,validate_plan
from devices import SupplyDevice

class FakeMotor:
 def __init__(self,*args):self.state=0;self.rpm=0;self.target=0;self.starts=0;self.stops=0;self.ramps=[];self.closed=False;self.fail=False
 def sample(self):
  if self.fail:raise TimeoutError('injected motor timeout')
  return dict(state=self.state,status='RUN' if self.state==6 else 'IDLE',rpm=self.rpm,reference=self.target,mode=3,faults=0,board_bus_V=24,board_temp_C=25,motor_power_W=12.5,iq_raw=-200,id_raw=0,current_scale_A_per_count=.001,iq_A=-.2,id_A=0,motor_rx_hex='mock')
 def ramp(self,rpm,ms):self.target=rpm;self.ramps.append(rpm);self.rpm=rpm if self.state==6 else 0
 def start(self):self.starts+=1;self.state=6;self.rpm=self.target
 def stop(self):self.stops+=1;self.state=0;self.rpm=0
 def close(self):self.closed=True
 def ack(self):pass

class FakeForce:
 def __init__(self,cfg):self.closed=False;self.fail=False;self.slow=False;self.entered=threading.Event()
 def read(self,emit,stop):
  self.entered.set()
  if self.slow:stop.wait(.7)
  if self.fail:raise TimeoutError('injected force failure')
  for ch in (1,2):
   now=time.monotonic();emit(dict(device='force',channel=ch,raw_signed_int32=100*ch,
    scale=.01,scaled_value=ch,request_start_mono=now,receive_mono=now))
 def close(self):self.closed=True

class FakeSupply:
 identity='GW INSTEK,GPP-6030,TEST,1.0'
 def __init__(self,cfg):self.closed=False
 def read(self,emit,stop):
  for ch in (1,2):
   for f,v in (('supply_V',24 if ch==1 else 10),('supply_A',1 if ch==1 else .1),('supply_W',24 if ch==1 else 1)):
    now=time.monotonic();emit(dict(device='psu',channel=ch,request_start_mono=now,receive_mono=now,**{f:v}))
 def close(self):self.closed=True

class SupplyTransport:
 def __init__(self):self.queries=[];self.closed=False
 def query(self,q):
  self.queries.append(q)
  return 'GW INSTEK,GPP-6030,SN,1.0' if q=='*IDN?' else '0' if q.endswith(':STAT?') else '1.25'
 def close(self):self.closed=True

class Tests(unittest.TestCase):
 def wait(self,p,timeout=14):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   if p():return
   time.sleep(.02)
  self.fail('wait timed out')
 def cfg(self,folder):
  c=defaults();c.update(folder=folder,ramp_ms=500,dwell_s=.5,baseline_s=1.,poststop_s=1.,reach_timeout_s=6.,speeds=[1500],force_interval=.05,psu_interval=.2)
  return c
 def close(self,w):w.quit_event.set();w.join(5);self.assertFalse(w.is_alive())
 def wait_finished(self, worker, path, timeout=14):
  deadline = time.monotonic() + timeout
  while True:
   remaining = deadline - time.monotonic()
   if remaining <= 0:
    self.fail(f'timed out waiting for finished: {path}')
   try:
    key, value = worker.events.get(timeout=remaining)
   except queue.Empty:
    self.fail(f'timed out waiting for finished: {path}')
   if key == 'finished' and Path(value) == path:
    return
 def test_complete_with_pre_post_and_psu(self):
  with tempfile.TemporaryDirectory() as folder:
   m=FakeMotor();f=FakeForce(None);p=FakeSupply(None)
   w=Controller(lambda port:m,{'force':lambda c:f,'psu':lambda c:p})
   try:
    w.submit('connect',('REAL','COM5'));self.wait(lambda:w.motor is not None)
    c=self.cfg(folder);c.update(psu_enabled=True,psu_resource='USB::TEST',psu_channels=[1,2])
    w.submit('begin',c);self.wait(lambda:w.file is not None)
    self.wait_finished(w, w.path)
    self.assertEqual(w.path.name,'data.csv')
    self.assertEqual(w.path.parent.parent,Path(folder))
    self.assertTrue(all((w.path.parent/name).is_file() for name in ('data.csv','data.json','data_summary.csv','data_stages.csv')))
    self.assertFalse(list(Path(folder).glob('*.csv')))
    rows=list(csv.DictReader(w.path.read_text(encoding='utf-8-sig').splitlines()))
    force=[r for r in rows if r['device']=='force']
    self.assertTrue(any(r['stage']=='baseline' for r in force))
    self.assertTrue(any(r['stage']=='poststop' for r in force))
    self.assertEqual({r['channel'] for r in rows if r['device']=='psu' and r['supply_W']},{'1','2'})
    self.assertTrue(any(r['motor_power_W']=='12.5' for r in rows))
    self.assertTrue(any(r['reason']=='stage_timed_complete' for r in rows))
    self.assertTrue(any(r['reason']=='stop_state_confirmed' for r in rows))
    self.assertTrue(any(r['reason']=='session_end' and r['detail']=='sequence_complete' for r in rows))
    self.assertEqual(m.starts,1);self.assertTrue(m.stops>=1);self.assertFalse(f.closed);self.assertFalse(p.closed);self.assertTrue(w.psu_worker.is_alive());self.assertTrue(w.force_worker.is_alive())
    self.assertTrue(all(float(r['elapsed_s'])>=0 for r in rows))
   finally:self.close(w)
 def test_simulation_opens_no_sensor(self):
  def forbidden(c):raise AssertionError('SIMULATION must never open sensors')
  with tempfile.TemporaryDirectory() as folder:
   w=Controller(sensor_factory={'force':forbidden,'psu':forbidden})
   try:
    w.submit('connect',('SIMULATION','COM5'));self.wait(lambda:w.motor is not None)
    c=self.cfg(folder);c.update(psu_enabled=True,psu_resource='USB::TEST')
    w.submit('begin',c);self.wait(lambda:w.phase=='baseline');w.stop_event.set();self.wait(lambda:w.file is None)
    rows=list(csv.DictReader(w.path.read_text(encoding='utf-8-sig').splitlines()))
    self.assertFalse(any(r['device'] in ('force','psu') for r in rows))
   finally:self.close(w)
 def test_preflight_error_never_starts(self):
  def fail(c):raise OSError('cannot open force')
  with tempfile.TemporaryDirectory() as folder:
   m=FakeMotor();w=Controller(lambda p:m,{'force':fail})
   try:
    w.submit('connect',('REAL','COM5'));self.wait(lambda:w.motor is not None)
    w.submit('begin',self.cfg(folder));self.wait(lambda:getattr(w,'reason','')=='force_error');self.wait(lambda:w.file is None)
    self.assertEqual(m.starts,0)
    rows=list(csv.DictReader(w.path.read_text(encoding='utf-8-sig').splitlines()))
    self.assertTrue(any(r['row_type']=='error' and r['device']=='force' for r in rows))
   finally:self.close(w)
 def test_slow_force_does_not_block_motor_stop(self):
  with tempfile.TemporaryDirectory() as folder:
   m=FakeMotor();f=FakeForce(None);w=Controller(lambda p:m,{'force':lambda c:f})
   try:
    w.submit('connect',('REAL','COM5'));self.wait(lambda:w.motor is not None)
    w.submit('begin',self.cfg(folder));self.wait(lambda:m.starts==1)
    f.entered.clear();f.slow=True;self.wait(lambda:f.entered.is_set())
    now=time.monotonic();w.stop_event.set();self.wait(lambda:m.stops>0,timeout=.6)
    self.assertLess(time.monotonic()-now,.6)
    self.wait(lambda:w.file is None)
    self.assertNotIn(1600,m.ramps)
   finally:self.close(w)
 def test_sensor_failure_aborts_sequence(self):
  with tempfile.TemporaryDirectory() as folder:
   m=FakeMotor();f=FakeForce(None);w=Controller(lambda p:m,{'force':lambda c:f})
   try:
    w.submit('connect',('REAL','COM5'));self.wait(lambda:w.motor is not None)
    c=self.cfg(folder);c['speeds']=[1500,1600];w.submit('begin',c);self.wait(lambda:m.starts==1)
    f.fail=True;self.wait(lambda:w.file is None)
    self.assertNotIn(1600,m.ramps);self.assertGreater(m.stops,0)
   finally:self.close(w)
 def test_query_allowlist(self):
  t=SupplyTransport();c=defaults();c['psu_channels']=[1,2]
  p=SupplyDevice(c,t);rows=[];p.read(rows.append,threading.Event())
  self.assertEqual(t.queries,['*IDN?',':MEAS1:VOLT?',':MEAS1:CURR?',':MEAS1:POWE?',':SOUR1:VOLT?',':SOUR1:CURR?',':SOUR1:CURR:STAT?',':MEAS2:VOLT?',':MEAS2:CURR?',':MEAS2:POWE?',':SOUR2:VOLT?',':SOUR2:CURR?',':SOUR2:CURR:STAT?'])
  self.assertEqual(len(rows),12);self.assertTrue(all('?' in q and ';' not in q for q in t.queries))
  for bad in ('*RST','OUTP ON','VOLT 60','*IDN?;OUTP ON'):
   with self.assertRaises(ValueError):p.query(bad)
  p.close();self.assertTrue(t.closed)
 def test_wrong_supply_model_rejected_and_closed(self):
  t=SupplyTransport();t.query=lambda q:'OTHER SUPPLY'
  with self.assertRaises(ValueError):SupplyDevice(defaults(),t)
  self.assertTrue(t.closed)
 def test_config_ports_and_finites(self):
  c=defaults();validate_plan(c)
  for k,v in [('force_port','COM5'),('baseline_s',float('nan')),('psu_channels',[2]),('scale1',float('inf'))]:
   with self.assertRaises(ValueError):validate_plan(dict(c,**{k:v}))
 def test_stop_outside_recording(self):
  m=FakeMotor();w=Controller(lambda p:m)
  try:
   w.submit('connect',('REAL','COM5'));self.wait(lambda:w.motor is not None)
   m.state=6;w.stop_event.set();self.wait(lambda:m.stops>0)
   self.assertEqual(m.state,0)
  finally:self.close(w)
 def test_stage_labels_follow_receive_time(self):
  import io
  w=Controller();w.quit_event.set();w.join(2)
  w.file=io.StringIO();w.writer=csv.DictWriter(w.file,fieldnames=__import__('controller').FIELDS);w.writer.writeheader()
  w.origin=100.;w.phase_history=[(100.,'baseline',0,0),(110.,'dwelling',1,1500)]
  w.write(dict(device='force',row_type='measurement',receive_mono=109.,raw_signed_int32=1))
  row=list(csv.DictReader(w.file.getvalue().splitlines()))[0]
  self.assertEqual(row['stage'],'baseline');self.assertEqual(row['target_rpm'],'0');w.file=None
 def test_stale_sensor_aborts(self):
  w=Controller();w.quit_event.set();w.join(2)
  w.file=True;w.phase='dwelling';w.cfg=defaults();w.required={('force','1','raw_signed_int32')};w.latest={}
  reasons=[];w.halt=lambda r,d='':reasons.append(r)
  w.advance(FakeMotor().sample(),time.monotonic())
  self.assertEqual(reasons,['sensor_stale']);w.file=None
 def test_pending_stop_does_not_ramp(self):
  w=Controller();w.quit_event.set();w.join(2);w.stop_event.set();w.motor=FakeMotor()
  w.next_stage();self.assertEqual(w.motor.ramps,[])

if __name__=='__main__':unittest.main()
