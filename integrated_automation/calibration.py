import math

def calibration_scale(raw_a,value_a,raw_b,value_b):
    if not all(math.isfinite(x) for x in (raw_a,value_a,raw_b,value_b)):raise ValueError('校正值必須為有限數字')
    if raw_a==raw_b or value_a==value_b:raise ValueError('兩點的原始值與已知值必須各不相同')
    scale=(value_b-value_a)/(raw_b-raw_a)
    return scale,raw_a-value_a/scale
