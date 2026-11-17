"""Unit conversions only: no inferred channel role, sign correction or tare."""
import math
G0=9.80665

def normalize_force(value,unit):
    if value=='':return {}
    x=float(value)
    if not math.isfinite(x):raise ValueError('Non-finite force channel value')
    u=unit.strip().replace('·','').replace('⋅','').replace('*','').replace('.','').replace(' ','').lower()
    if u in ('n','gf','kgf'):
        newton=x*{'n':1.,'gf':G0/1000.,'kgf':G0}[u]
        return dict(force_N=newton,force_gf=newton*1000./G0)
    if u in ('nm','n-m','nmm','n-mm','kgfcm','kgf-cm'):
        return dict(torque_Nm=x*{'nm':1.,'n-m':1.,'nmm':.001,'n-mm':.001,'kgfcm':G0*.01,'kgf-cm':G0*.01}[u])
    return {}
