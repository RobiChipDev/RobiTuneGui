"""Streaming per-stage summaries; raw CSV remains authoritative, no resampling."""
import csv,math
from pathlib import Path

METRICS=('estimated_rpm','raw_signed_int32','scaled_value','force_N','force_gf','torque_Nm',
 'board_bus_V','board_temp_C','motor_power_W','iq_raw','id_raw','iq_A','id_A','supply_V','supply_A','supply_W','supply_set_V','supply_limit_A','supply_current_limited')
UNITS=dict(estimated_rpm='rpm',force_N='N',force_gf='gf',torque_Nm='N.m',board_bus_V='V',
 board_temp_C='C',motor_power_W='W',iq_A='A',id_A='A',supply_V='V',supply_A='A',supply_W='W',supply_set_V='V',supply_limit_A='A')
def summarize(path,cfg=None):
 path=Path(path);groups={};completed=set()
 with path.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   if r.get('reason')=='stage_timed_complete':completed.add((r['stage_index'],r['target_rpm']))
   if r['row_type']!='measurement' or r['stage'] not in ('baseline','dwelling','poststop'):continue
   t=float(r['elapsed_s'])
   for metric in METRICS:
    if r.get(metric,'')=='':continue
    v=float(r[metric])
    if not math.isfinite(v):continue
    key=(r['device'],r['channel'],r['stage'],r['stage_index'],r['target_rpm'],metric,r.get('unit','') if metric=='scaled_value' else UNITS.get(metric,''))
    g=groups.setdefault(key,dict(n=0,mean=0.,m2=0.,low=v,high=v,t0=t,last=t,prev=t,max_gap=0.,sx=0.,sy=0.,sxx=0.,sxy=0.))
    g['max_gap']=max(g['max_gap'],t-g['prev']);g['prev']=t
    g['n']+=1;delta=v-g['mean'];g['mean']+=delta/g['n'];g['m2']+=delta*(v-g['mean'])
    g['low']=min(g['low'],v);g['high']=max(g['high'],v);g['last']=max(g['last'],t)
    x=t-g['t0'];g['sx']+=x;g['sy']+=v;g['sxx']+=x*x;g['sxy']+=x*v
 out=path.with_name(path.stem+'_summary.csv')
 fields=['device','channel','stage','stage_index','target_rpm','metric','unit','n','mean','sample_stddev','min','max','slope_per_s','first_s','last_s','sample_rate_Hz','max_gap_s']
 with out.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for key,g in groups.items():
   n=g['n'];den=n*g['sxx']-g['sx']**2
   r=dict(zip(fields[:7],key));r.update(n=n,mean=g['mean'],sample_stddev=math.sqrt(max(0,g['m2'])/(n-1)) if n>1 else '',
    min=g['low'],max=g['high'],slope_per_s=(n*g['sxy']-g['sx']*g['sy'])/den if den>1e-12 else '',first_s=g['t0'],last_s=g['last'],sample_rate_Hz=(n-1)/(g['last']-g['t0']) if n>1 and g['last']>g['t0'] else '',max_gap_s=g['max_gap'] if n>1 else '')
   w.writerow(r)
 write_stage_table(path,groups,completed,cfg or {})
 return out

def write_stage_table(path,groups,completed,cfg):
 stages=sorted({(k[3],k[4]) for k in groups if k[2]=='dwelling'},key=lambda x:int(x[0]))
 fields=['stage_index','target_rpm','stage_complete','speed_mean_rpm','speed_min_rpm','speed_max_rpm','speed_std_rpm','speed_n',
 'Imotor_min_A','Imotor_max_A','Imotor_mean_A','Imotor_n','Wi_min_W','Wi_max_W','Wi_mean_W','Wi_n',
 'Fz_mean_N','Fz_mean_gf','Fz_std_N','Fz_slope_N_per_s','Fz_n','Tz_mean_Nm','Tz_std_Nm','Tz_n',
 'Wo_motorpilot_mean_W','board_bus_mean_V','board_temp_mean_C','Iq_mean_A','Id_mean_A',
 'ch1_raw_mean','ch2_raw_mean','ch1_force_mean_N','ch2_force_mean_N','ch1_torque_mean_Nm','ch2_torque_mean_Nm',
 'psu_set_mean_V','psu_limit_mean_A','current_limit_observed','eff_signed_gf_per_W','eff_abs_gf_per_W','force_power_overlap_s','quality_note']
 def stats(stage,device,channel,metric):
  for key,g in groups.items():
   if key[0]==device and key[1]==str(channel) and key[2]=='dwelling' and key[3:5]==stage and key[5]==metric:return g
  return None
 def sd(g):return math.sqrt(max(0,g['m2'])/(g['n']-1)) if g['n']>1 else ''
 def slope(g):
  n=g['n'];den=n*g['sxx']-g['sx']**2
  return (n*g['sxy']-g['sx']*g['sy'])/den if den>1e-12 else ''
 output=path.with_name(path.stem+'_stages.csv')
 with output.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for stage in stages:
   r=dict(stage_index=stage[0],target_rpm=stage[1],stage_complete=stage in completed);notes=[]
   if stage not in completed:notes.append('incomplete_stage')
   speed=stats(stage,'motor','','estimated_rpm')
   if speed:r.update(speed_mean_rpm=speed['mean'],speed_min_rpm=speed['low'],speed_max_rpm=speed['high'],speed_std_rpm=sd(speed),speed_n=speed['n'])
   amps=stats(stage,'psu',1,'supply_A');power=stats(stage,'psu',1,'supply_W')
   if amps:r.update(Imotor_min_A=amps['low'],Imotor_max_A=amps['high'],Imotor_mean_A=amps['mean'],Imotor_n=amps['n'])
   for metric,col in (('supply_set_V','psu_set_mean_V'),('supply_limit_A','psu_limit_mean_A')):
    g=stats(stage,'psu',1,metric)
    if g:r[col]=g['mean']
   limited=stats(stage,'psu',1,'supply_current_limited')
   if limited:r['current_limit_observed']=limited['high']>=1
   if power:r.update(Wi_min_W=power['low'],Wi_max_W=power['high'],Wi_mean_W=power['mean'],Wi_n=power['n'])
   else:notes.append('no_psu_CH1_power')
   for metric,column in (('motor_power_W','Wo_motorpilot_mean_W'),('board_bus_V','board_bus_mean_V'),('board_temp_C','board_temp_mean_C'),('iq_A','Iq_mean_A'),('id_A','Id_mean_A')):
    g=stats(stage,'motor','',metric)
    if g:r[column]=g['mean']
   for ch in (1,2):
    for metric,col in (('raw_signed_int32',f'ch{ch}_raw_mean'),('force_N',f'ch{ch}_force_mean_N'),('torque_Nm',f'ch{ch}_torque_mean_Nm')):
     g=stats(stage,'force',ch,metric)
     if g:r[col]=g['mean']
   thrust=stats(stage,'force',cfg.get('thrust_channel',0),'force_N')
   torque=stats(stage,'force',cfg.get('torque_channel',0),'torque_Nm')
   if thrust:
    from units import G0
    r.update(Fz_mean_N=thrust['mean'],Fz_mean_gf=thrust['mean']*1000/G0,Fz_std_N=sd(thrust),Fz_slope_N_per_s=slope(thrust),Fz_n=thrust['n'])
   else:notes.append('thrust_channel_or_unit_unconfirmed_or_missing')
   if torque:r.update(Tz_mean_Nm=torque['mean'],Tz_std_Nm=sd(torque),Tz_n=torque['n'])
   else:notes.append('torque_channel_or_unit_unconfirmed_or_missing')
   if thrust and power:
    overlap=max(0,min(thrust['last'],power['last'])-max(thrust['t0'],power['t0']));r['force_power_overlap_s']=overlap
    if stage in completed and power['mean']>0 and min(thrust['n'],power['n'])>=2 and overlap>0:
     eff=r['Fz_mean_gf']/power['mean'];r.update(eff_signed_gf_per_W=eff,eff_abs_gf_per_W=abs(eff));notes.append('eff_ratio_of_stage_means_not_instantaneous')
    else:notes.append('eff_not_computed_incomplete_or_insufficient_or_nonpositive_power')
   r['quality_note']=';'.join(notes);w.writerow(r)

if __name__=='__main__':
 import sys
 print(summarize(sys.argv[1]))
