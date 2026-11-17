"""One exclusive directory per experiment; no existing capture is overwritten."""
import re
from datetime import datetime
from pathlib import Path


def clean_filename(value):
    text=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value or ''))
    text=re.sub(r'\s+','_',text).strip(' ._')
    return text


def safe_label(value):
    return clean_filename(value)[:48].rstrip(' ._')


def session_names(name):
    yield name
    for index in range(26 + 26 * 26):
        prefix = chr(65 + index // 26 - 1) if index >= 26 else ''
        yield f'{name}_{prefix}{chr(65 + index % 26)}'


def create_session_folder(base,mode,speeds,run_name='',stamp=None, *, label_override=None):
    root=Path(base).expanduser();root.mkdir(parents=True,exist_ok=True)
    label=label_override or safe_label(run_name)
    if not label:
        label='-'.join(str(n) for n in speeds[:4])+'rpm'
        if len(speeds)>4:label+=f'_等{len(speeds)}組'
    stamp=stamp or datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    name=label if mode=='REAL' else f'{label}_{safe_label(mode)}_{safe_label(stamp)}'
    if len(name.encode('utf-16-le'))//2>220:
        raise ValueError('螺旋槳名稱與轉速清單組合過長，請縮短後再開始')
    for candidate in session_names(name):
        path=root/candidate
        try:path.mkdir();return path
        except FileExistsError:continue
    raise FileExistsError('無法建立獨立實驗資料夾：同名資料夾過多')


def latest_session_folder(base):
    root=Path(base).expanduser()
    if not root.exists():return root
    candidates=[]
    for child in root.iterdir():
        if child.is_dir() and (child/'data.csv').is_file() and (child/'data.json').is_file():
            candidates.append(child)
    return max(candidates,key=lambda p:(p.stat().st_mtime_ns,p.name)) if candidates else root
