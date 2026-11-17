"""Motor 1 MCP register mapping from the supplied MCSDK 6.4.2 firmware."""
# Register element, label, wire value format.
PARAMETERS = {
    'speed_kp': (2, 'Speed Kp', 'h'),
    'speed_ki': (3, 'Speed Ki', 'h'),
    'speed_kp_div': (81, 'Speed Kp divisor', 'H'),
    'speed_ki_div': (82, 'Speed Ki divisor', 'H'),
    'iq_kp': (6, 'Torque (Iq) Kp', 'h'),
    'iq_ki': (7, 'Torque (Iq) Ki', 'h'),
    'id_kp': (10, 'Flux (Id) Kp', 'h'),
    'id_ki': (11, 'Flux (Id) Ki', 'h'),
    'observer_c1': (13, 'Observer C1', 'h'),
    'observer_c2': (14, 'Observer C2', 'h'),
    'pll_kp': (18, 'PLL Kp', 'h'),
    'pll_ki': (17, 'PLL Ki', 'h'),
    'iq_reference_raw': (37, 'Torque Reference（raw，唯讀）', 'h'),
}
DIVISORS = tuple(1 << i for i in range(16))


def register(key):
    return (PARAMETERS[key][0] << 6) | 0x11


def encode_value(key, value):
    if key == 'iq_reference_raw':
        raise ValueError('Torque Reference 僅供讀取。')
    if type(value) is not int:
        raise ValueError('請輸入整數。')
    if PARAMETERS[key][2] == 'H':
        if value not in DIVISORS:
            raise ValueError('除數必須為 1 到 32768 之間的 2 次方。')
        return value.bit_length() - 1
    minimum = -32768 if key in ('observer_c1', 'observer_c2') else 0
    if not minimum <= value <= 32767:
        raise ValueError(f'數值須在 {minimum} 至 32767 之間。')
    return value


def decode_value(key, value):
    if PARAMETERS[key][2] == 'H':
        if not 0 <= value < len(DIVISORS):
            raise ValueError('板端回報了無效的除數指數。')
        return DIVISORS[value]
    return value
