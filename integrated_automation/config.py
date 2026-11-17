from pathlib import Path

WORKSPACE = Path.home() / 'Documents' / 'Robi'


def workspace_root(output):
 path=Path(output).expanduser()
 return path.parent if path.name.casefold()=='experimentdata' else path


def defaults():
 return dict(run_name='',mount='',speed_kp='',speed_ki='',speed_kd='',port='COM5',speeds=[1500,1600],max_rpm=7100,ramp_ms=3000,dwell_s=10.,
  baseline_s=5.,poststop_s=10.,reach_timeout_s=30.,folder=str(WORKSPACE/'ExperimentData'),
  force_enabled=True,force_port='COM6',force_baud=9600,force_addr=1,force_parity='N',
  force_stopbits=1,force_order='HH-LL',force_interval=.1,zero1=0.,zero2=0.,scale1=.01,scale2=.001,unit1='N',unit2='Nm',thrust_channel=1,torque_channel=2,
  psu_enabled=False,psu_backend='SERIAL',psu_resource='',psu_baud=115200,psu_channels=[1],psu_interval=1.)
