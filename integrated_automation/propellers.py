"""Local catalog and experiment naming."""
import json
import os
import re
import tempfile
from pathlib import Path

from config import WORKSPACE

LEGACY_CATALOG = Path.home() / 'Documents' / 'RobiV03Logs' / 'propellers.json'


ROTATIONS = ('CW', 'CCW')
MOUNTS = {'正裝': 'NormalMount', '反裝': 'FlippedMount'}


def direction_factors(mount, rotation):
    if mount not in MOUNTS or rotation not in ROTATIONS:
        return {}
    return {'thrust': -1 if mount == '正裝' else 1,
            'torque': -1 if rotation == 'CW' else 1}


def profile(dimension, blades, material, number, rotation=''):
    if rotation not in ('', *ROTATIONS):
        raise ValueError('槳葉標示旋向須為 CW 或 CCW。')
    dimension, material, number = (v.strip() for v in (dimension, material, number))
    if not all(re.fullmatch(r'[\w%.+-]{1,24}', v) for v in (dimension, material, number)):
        raise ValueError('尺寸、材質與編號須填寫，請使用文字、數字或 % . + -')
    blades = int(blades)
    if not 1 <= blades <= 99:
        raise ValueError('槳葉數須介於 1 和 99')
    number = number.zfill(2)
    return dict(dimension=dimension, blades=blades, material=material, number=number,
                rotation=rotation, name=f'{dimension}_{blades}-Blade_{material}_No{number}'+(f'_{rotation}' if rotation else ''))


def catalog_path(root):
    return root / 'DeviceSettings' / 'propellers.json'


def load_catalog(root):
    path = catalog_path(root)
    if root == WORKSPACE and not path.exists():
        path = LEGACY_CATALOG
    try:
        entries = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(entries, list):
        raise ValueError('螺旋槳清單必須是 JSON 陣列')
    result = {}
    for row in entries:
        entry = profile(row['dimension'], row['blades'], row['material'], row['number'], row.get('rotation',''))
        result[entry['name']] = entry
    return result


def save_catalog(root, entries):
    catalog = catalog_path(root)
    catalog.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=catalog.parent, delete=False, mode='w', encoding='utf-8') as stream:
        path = Path(stream.name)
        try:
            json.dump(list(entries.values()), stream, ensure_ascii=False, indent=2)
        except Exception:
            stream.close()
            path.unlink()
            raise
    try:
        os.replace(path, catalog)
    finally:
        path.unlink(missing_ok=True)


def run_label(name, speeds):
    low, high = min(speeds), max(speeds)
    if low == high:
        interval = str(low)
    elif all(a >= b for a, b in zip(speeds, speeds[1:])):
        interval = f'{high}-{low}'
    else:
        interval = f'{low}-{high}'
    return f"{name}_{interval}RPM_" + '-'.join(map(str, speeds))


def outcome_tag(reason, detail):
    if reason == 'sequence_complete':
        return ''
    if reason in ('operator_stop', 'operator_stop_before_start', 'application_close', 'disconnect_requested'):
        return '_Abort'
    if reason == 'motor_fault' and re.fullmatch(r'0x[0-9a-fA-F]+', detail) and int(detail, 16):
        return '_Error-' + detail
    return '_Error-' + reason.replace('_', '-')


def sorted_catalog(entries):
    """Display order only; never rewrite stored identities or sample numbers."""
    def natural(value):
        return tuple((0, int(part)) if part.isdigit() else (1, part.casefold())
                     for part in re.split(r'(\d+)', str(value)) if part)
    def key(item):
        name, row = item
        return (natural(row['dimension']), int(row['blades']), natural(row['material']),
                natural(row['number']), {'CW': 0, 'CCW': 1}.get(row['rotation'], 2), name)
    return dict(sorted(entries.items(), key=key))
