"""Offline HTML/SVG experiment report. Reads closed CSV; never touches devices."""
import csv
import html
import json
import math
import os
import statistics
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pid_settings import PARAMETERS

COLORS = {'rpm':'#2563eb', 'force':'#0f766e', 'torque':'#7c3aed', 'power':'#c26916'}
PHASES = {'preflight':'檢查', 'baseline':'啟動前', 'starting':'啟動',
          'startup_settle':'到速確認', 'ramping':'變速確認', 'dwelling':'定速記錄',
          'stopping':'停止確認', 'poststop':'停機後記錄'}
EVENTS = {'session_begin':'開始記錄', 'baseline_begin':'啟動前記錄開始',
          'motor_start':'送出啟動', 'stage_ramp':'送出轉速命令', 'dwell_begin':'定速記錄開始',
          'stage_timed_complete':'本組計時完成', 'stop_requested':'請求停止',
          'stop_command_ack':'停止命令收到回覆', 'stop_state_confirmed':'控制器停止狀態確認',
          'stop_state_unconfirmed':'控制器停止狀態未確認', 'session_end':'記錄結束', 'poststop_ended_by_operator':'提前結束停機後記錄'}

def num(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None

def fmt(value, digits=3):
    v = num(value)
    return '—' if v is None else f'{v:.{digits}f}'

def mean(values):
    return statistics.mean(values) if values else None

def table(headers, rows):
    esc = lambda x: html.escape(str(x))
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def envelope(points, limit=1800):
    """Keep chronological min/max per bucket instead of hiding narrow peaks."""
    if len(points) <= limit:
        return points
    out = [points[0]]
    size = math.ceil(len(points) / (limit // 2))
    for start in range(0, len(points), size):
        bucket = points[start:start+size]
        for i in sorted({min(range(len(bucket)), key=lambda j:bucket[j][1]),
                         max(range(len(bucket)), key=lambda j:bucket[j][1])}):
            out.append(bucket[i])
    out.append(points[-1])
    return out

def svg_plot(series, duration, spans=(), height=225, show_time=True, keep_axis=False, overlay=False):
    """Each series: label, [(seconds,value)], color, gap threshold."""
    w=1120; left=76; right=22; top=24; bottom=height-(38 if show_time else 8)
    if overlay:right=162
    values=[v for _,pts,_,_ in series for _,v in pts]
    if not values and not keep_axis:
        return '<p class="missing">尚無有效量測，不以 0 代替。</p>'
    def bounds(samples):
        low=min(samples,default=0); high=max(samples,default=0)
        pad=(high-low)*.1 if high>low else max(abs(high)*.1,.001)
        return low-pad,high+pad

    x=lambda t:left+(w-left-right)*t/max(duration,.001)
    low,high=bounds(values)
    y=lambda v,lo,hi:bottom-(bottom-top)*(v-lo)/(hi-lo)
    out=[f'<svg role="img" aria-label="量測趨勢，橫軸為經過秒數" viewBox="0 0 {w} {height}">']
    for a,b,phase,target in spans:
        color='#eaf3ff' if phase=='dwelling' else '#f1f5f9' if phase in ('baseline','poststop') else '#fff7ed'
        title=html.escape(PHASES.get(phase,phase)+(f' {target} rpm' if phase=='dwelling' else ''))
        out.append(f'<rect x="{x(a):.2f}" y="{top}" width="{max(0,x(b)-x(a)):.2f}" height="{bottom-top}" fill="{color}"><title>{title}: {a:.1f}–{b:.1f} s</title></rect>')
    axes=[(low,high,'','#526172',left-9,'end',bool(values))]
    if overlay:
        axes=[]
        for i,(label,points,color,_) in enumerate(series):
            lo,hi=bounds([v for _,v in points])
            pos=(left-9,w-right+9,w-right+83)[i]
            axes.append((lo,hi,label,color,pos,'end' if i==0 else 'start',bool(points)))
    for axis,(lo,hi,label,color,pos,anchor,available) in enumerate(axes):
        if label:
            out.append(f'<text x="{pos}" y="15" text-anchor="{anchor}" style="fill:{color}">{html.escape(label)}</text>')
        for i in range(5):
            v=lo+(hi-lo)*i/4; yy=y(v,lo,hi)
            if axis==0:
                out.append(f'<path d="M {left} {yy:.2f} H {w-right}" stroke="#dce4ec" stroke-width=".8"/>')
            if available:
                out.append(f'<text x="{pos}" y="{yy+4:.2f}" text-anchor="{anchor}" style="fill:{color}">{v:.4g}</text>')
    for i in range(7):
        t=duration*i/6; xx=x(t)
        out.append(f'<path d="M {xx:.2f} {top} V {bottom}" stroke="#dce4ec" stroke-width=".8"/>')
        if show_time: out.append(f'<text x="{xx:.2f}" y="{height-16}" text-anchor="middle">{t:.0f}</text>')
    if show_time: out.append(f'<text x="{w-right}" y="{height-2}" text-anchor="end">經過時間 (s)</text>')
    if not values:
        out.append(f'<text x="{(left+w-right)/2}" y="{(top+bottom)/2}" text-anchor="middle">尚無有效量測，不以 0 代替。</text>')
    for label,points,color,gap in series:
        lo,hi=bounds([v for _,v in points]) if overlay else (low,high)
        chunks=[]; current=[]; previous=None
        for p in points:
            if previous is not None and p[0]-previous>gap:
                chunks.append(current);current=[]
            current.append(p);previous=p[0]
        if current:chunks.append(current)
        for chunk in chunks:
            reduced=envelope(chunk)
            coords=' '.join(f'{x(t):.2f},{y(v,lo,hi):.2f}' for t,v in reduced)
            out.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.7"><title>{html.escape(label)}</title></polyline>')
            if len(chunk)==1:
                out.append(f'<circle cx="{x(chunk[0][0]):.2f}" cy="{y(chunk[0][1],lo,hi):.2f}" r="2" fill="{color}"/>')
    if overlay:
        out.append(f'<line visibility="hidden" y1="{top}" y2="{bottom}" stroke="#475569"/>')
        out.append(f'<rect class="overlay-hit" x="{left}" y="{top}" width="{w-left-right}" height="{bottom-top}" fill="transparent"/>')
    return ''.join(out)+'</svg>'

def overlay_chart(items,duration,spans):
    chart=svg_plot(items,duration,spans,280,keep_axis=True,overlay=True)
    samples=json.dumps(items,ensure_ascii=False,allow_nan=False).replace('<',r'\u003c')
    return f'''<section id="trend-overlay"><h2>轉速、推力與扭矩疊圖</h2>
<p class="note">三色曲線各用同色縱軸。移動游標可看各通道最近的原始取樣，長間隔不補值。</p>
{chart}<p class="note overlay-readout">移動游標查看讀值。</p>
<script type="application/json">{samples}</script>
<script>
(() => {{
 const box=document.getElementById('trend-overlay');
 const svg=box.querySelector('svg'), hit=box.querySelector('.overlay-hit');
 const line=svg.querySelector('line'), out=box.querySelector('.overlay-readout');
 const data=JSON.parse(box.querySelector('[type="application/json"]').textContent);
 hit.addEventListener('pointermove',event=>{{
   const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
   const left=hit.x.baseVal.value, width=hit.width.baseVal.value;
   const x=Math.max(left,Math.min(left+width,p.x)), t=(x-left)/width*{duration};
   line.setAttribute('x1',x); line.setAttribute('x2',x); line.setAttribute('visibility','visible');
   out.textContent=t.toFixed(2)+' s  ｜  '+data.map(([unit,points,color,gap])=>{{
     let lo=0,hi=points.length;
     while(lo<hi){{const m=(lo+hi)>>1;if(points[m][0]<t)lo=m+1;else hi=m;}}
     const a=points[lo-1], b=points[lo];
     const v=a&&(!b||t-a[0]<=b[0]-t)?a:b;
     const valid=v&&Math.abs(v[0]-t)<=gap/2&&!(a&&b&&b[0]-a[0]>gap&&a[0]<t&&t<b[0]);
     return (valid?Number(v[1].toPrecision(5)):'—')+' '+unit;
   }}).join('  ｜  ');
 }});
 hit.addEventListener('pointerleave',()=>{{line.setAttribute('visibility','hidden');out.textContent='移動游標查看讀值。';}});
}})();
</script></section>'''


def read_run(path, cfg=None):
    path=Path(path)
    if cfg is None:
        cfg=json.loads(path.with_suffix('.json').read_text(encoding='utf-8-sig')) if path.with_suffix('.json').exists() else {}
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not {'elapsed_s','row_type'}<=set(reader.fieldnames or []):
            raise ValueError('請選取原始 data.csv，勿選 summary 或 stages 統計檔。')
        rows=[r for r in reader if num(r.get('elapsed_s')) is not None]
    rows.sort(key=lambda r:float(r['elapsed_s']))
    measured=[r for r in rows if r.get('row_type')=='measurement']
    events=[r for r in rows if r.get('row_type')=='event']
    duration=max((float(r['elapsed_s']) for r in rows),default=0)
    spans=[]
    for r in rows:
        t=float(r['elapsed_s']); key=(r.get('stage',''),r.get('stage_index',''))
        if not spans or key!=spans[-1][4]:
            if spans:spans[-1][1]=t
            spans.append([t,duration,key[0],r.get('target_rpm',''),key])
    return cfg,rows,measured,events,duration,[s[:4] for s in spans]

def generate_report(path, cfg=None):
    path=Path(path)
    cfg,rows,m,events,duration,spans=read_run(path,cfg)
    esc=html.escape
    factors=cfg.get('direction_factors') or {}
    thrust=cfg.get('thrust_channel',0);torque=cfg.get('torque_channel',0)
    thrust_sign=factors.get('thrust',1)
    torque_sign=factors.get('torque',1)
    metric_factors={('force',thrust,'force_N'):thrust_sign, ('force',torque,'torque_Nm'):torque_sign}
    direction_note=(f'方向換算 · 推力 × {thrust_sign:+d} ｜ 扭矩 × {torque_sign:+d}'
                    if factors else '方向換算未設定 · 顯示原量測方向')
    def points(device,channel,metric,subset=None):
        factor=metric_factors.get((device,channel,metric),1)
        return [(float(r['elapsed_s']),num(r.get(metric))*factor) for r in (m if subset is None else subset)
                if r.get('device')==device and (channel is None or r.get('channel')==str(channel)) and num(r.get(metric)) is not None]
    def values(device,ch,metric,subset):return [v for _,v in points(device,ch,metric,subset)]
    def series(label,device,ch,metric,color):
        return (label,points(device,ch,metric),color,max(2.,3*cfg.get('force_interval',.1)) if device=='force' else max(5.,3*cfg.get('psu_interval',1)) if device=='psu' else 2.)
    end=[e for e in events if e.get('reason')=='session_end']
    reason=end[-1].get('detail','') if end else ''
    status='流程完成' if reason=='sequence_complete' else '流程中止' if end else '記錄未正常結束'
    try:stamp=datetime.fromisoformat(rows[0]['utc_time']).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S UTC+8')
    except (ValueError,KeyError,IndexError):stamp='時間未提供'
    completed={e.get('stage_index') for e in events if e.get('reason')=='stage_timed_complete'}
    completed_targets=[e.get('target_rpm','') for e in events if e.get('reason')=='stage_timed_complete']
    last_target=end[-1].get('target_rpm','') if end else ''
    peak_rpm=max(values('motor',None,'estimated_rpm',m),default=None)
    reached=' / '.join(completed_targets) or '無'
    stages=sorted({r.get('stage_index') for r in m if r.get('stage')=='dwelling'},key=lambda s:int(s or 0))
    base=[r for r in m if r.get('stage')=='baseline']; post=[r for r in m if r.get('stage')=='poststop']
    post_end=max((float(r['elapsed_s']) for r in post),default=0)
    post_tail=[r for r in post if float(r['elapsed_s'])>=post_end-10]
    baseline=mean(values('force',thrust,'force_N',base))
    stage_rows=[]; detail_rows=[]
    for idx in stages:
        part=[r for r in m if r.get('stage')=='dwelling' and r.get('stage_index')==idx]
        t0=min(float(r['elapsed_s']) for r in part);t1=max(float(r['elapsed_s']) for r in part)
        tail=[r for r in part if float(r['elapsed_s'])>=t1-30]
        f=mean(values('force',thrust,'force_N',part));ft=mean(values('force',thrust,'force_N',tail))
        target=part[0].get('target_rpm','')
        stage_rows.append([idx,target,'完成' if idx in completed else '未完成',fmt(t1-t0,1),fmt(mean(values('motor',None,'estimated_rpm',part)),1),fmt(f,4),fmt(ft,4),fmt(ft-baseline if ft is not None and baseline is not None else None,4),fmt(mean(values('force',torque,'torque_Nm',part)),5)])
        for start in range(0,max(1,math.ceil((t1-t0)/30))):
            a=start*30;b=min((start+1)*30,t1-t0)
            chunk=[r for r in part if t0+a<=float(r['elapsed_s']) and (float(r['elapsed_s'])<t0+b or (b==t1-t0 and float(r['elapsed_s'])<=t1))]
            detail_rows.append([idx,target,f'{a:.0f}–{b:.1f}',fmt(mean(values('motor',None,'estimated_rpm',chunk)),1),fmt(mean(values('force',thrust,'force_N',chunk)),4),fmt(mean(values('force',torque,'torque_Nm',chunk)),5)])
    quality=[]
    for device,ch in sorted({(r.get('device',''),r.get('channel','')) for r in m}):
        times=[float(r['elapsed_s']) for r in m if r.get('device')==device and r.get('channel')==ch]
        gaps=[b-a for a,b in zip(times,times[1:])]
        quality.append([device+(f' CH{ch}' if ch else ''),len(times),fmt((len(times)-1)/(times[-1]-times[0]) if len(times)>1 and times[-1]>times[0] else None,2),fmt(max(gaps) if gaps else None,3)])
    fault_rows=[]
    for r in m:
        try:
            if int(r.get('faults_hex') or '0',16):fault_rows.append(r)
        except ValueError:pass
    errors=[r for r in rows if r.get('row_type')=='error' or any(k in r.get('reason','') for k in ('error','timeout','stale','overflow','unconfirmed'))]
    sections=[]
    def chart(title,items,show_time=False):
        legend=''.join(f'<span style="color:{color}">{esc(label)}</span>' for label,_,color,_ in items)
        sections.append('<div class="trend-panel"><h3>'+esc(title)+'</h3><div class="legend">'+legend+'</div>'
                        +svg_plot(items,duration,spans,155 if show_time else 125,show_time,keep_axis=True)+'</div>')
    chart('轉速與命令 (rpm)',[series('板端估測轉速','motor',None,'estimated_rpm',COLORS['rpm']),series('板端命令值','motor',None,'reference_rpm','#94a3b8')])
    chart(f'推力 (N) · CH{thrust}' if thrust else '推力通道未指定',[series('推力','force',thrust,'force_N',COLORS['force'])])
    chart(f'扭矩 (Nm) · CH{torque}' if torque else '扭矩通道未指定',[series('扭矩','force',torque,'torque_Nm',COLORS['torque'])],show_time=True)
    overlay=overlay_chart([
        series('rpm','motor',None,'estimated_rpm',COLORS['rpm']),
        series('N','force',thrust,'force_N',COLORS['force']),
        series('N·m','force',torque,'torque_Nm',COLORS['torque']),
    ],duration,spans)
    electric=[]
    for title,device,metric,unit in [('Motor Pilot 回報功率','motor','motor_power_W','W'),('板端母線電壓','motor','board_bus_V','V'),('板端溫度','motor','board_temp_C','°C'),('Iq','motor','iq_A','A'),('Id','motor','id_A','A'),('電供輸入功率 CH1','psu','supply_W','W'),('電供電流 CH1','psu','supply_A','A')]:
        electric.append('<section><h2>'+title+' ('+unit+')</h2>'+svg_plot([series(title,device,1 if device=='psu' else None,metric,COLORS['power'])],duration,spans,190)+'</section>')
    for ch in (1,2):electric.append(f'<section><h2>CH{ch} 原始計數 (count)</h2>'+svg_plot([series('原始計數','force',ch,'raw_signed_int32','#475569')],duration,spans,190)+'</section>')
    zero_rows=[]
    for label,ch,metric,digits in [('推力 N',thrust,'force_N',4),('扭矩 Nm',torque,'torque_Nm',5)]:
        a=mean(values('force',ch,metric,base));b=mean(values('force',ch,metric,post_tail))
        zero_rows.append([label,fmt(a,digits),fmt(b,digits),fmt(b-a if a is not None and b is not None else None,digits)])
    event_rows=[[fmt(e['elapsed_s'],2),EVENTS.get(e.get('reason'),e.get('reason','')),e.get('stage_index',''),e.get('target_rpm',''),e.get('detail','') if e.get('reason')!='session_begin' else ''] for e in events]
    board_pid=cfg.get('pid_board_readback') or {}
    board_pid_rows=[[PARAMETERS[key][1], value] for key,value in board_pid.items() if key in PARAMETERS]
    pid_rows=[[label, cfg.get(key) or '—'] for label,key in
              [('Speed Kp','speed_kp'),('Speed Ki','speed_ki'),('Speed Kd','speed_kd')]]
    styles='''body{margin:0;background:#fff;color:#17212f;font:15px "Segoe UI","Microsoft JhengHei",sans-serif}main{max-width:1180px;margin:auto;padding:30px 26px}header{border-bottom:2px solid #17212f;padding-bottom:18px}h1{font-size:28px;margin:0 0 9px}h2{font-size:18px;margin:0 0 10px}h3{font-size:15px}.trend-panel h3{margin:8px 0 3px}p{line-height:1.65}small,.note{color:#596879}section{border:1px solid #dbe3eb;border-radius:12px;padding:18px;margin:16px 0;break-inside:avoid}svg{width:100%;height:auto;display:block}svg text{font:12px "Segoe UI","Microsoft JhengHei",sans-serif;fill:#526172}.legend{display:flex;gap:22px;font-weight:600;font-size:13px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}.card{border:1px solid #dbe3eb;border-radius:10px;padding:15px}.card b{display:block;font-size:23px;margin:7px 0}.good{color:#0f766e}.warn{color:#b45309}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:10px 9px;text-align:right;border-bottom:1px solid #e2e8f0;white-space:nowrap}th{background:#f1f5f9;color:#344457}th:first-child,td:first-child{text-align:left}tbody tr:nth-child(even){background:#fafbfd}td:last-child{white-space:normal}details{margin:20px 0}summary{cursor:pointer;font-size:18px;font-weight:600;padding:12px 0}.missing{padding:25px;background:#f8fafc;color:#64748b}.actions{float:right}button{background:#fff;border:1px solid #cbd5e1;border-radius:6px;padding:9px;cursor:pointer}@media(max-width:700px){main{padding:18px 12px}.cards{grid-template-columns:repeat(2,1fr)}section{padding:10px}}@media print{main{max-width:none;padding:0}.actions{display:none}section{border-radius:0}details{display:block}svg{max-height:230px}}'''
    body=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Robi 實驗報告</title><style>{styles}</style></head><body><main>
<header><button class="actions" onclick="window.print()">列印 / 存成 PDF</button><h1>Robi 實驗報告</h1><div>{esc((cfg.get('propeller') or {}).get('name') or cfg.get('run_name') or ' / '.join(map(str,cfg.get('speeds',[])))+' rpm')} · {esc(stamp)}</div><p class="note">{esc(cfg.get('mode','未知模式'))} · 記錄版本 {esc(str(cfg.get('version','未知')))} · 原始來源 {esc(path.name)}</p></header>
<p class="note">已完成定速點 {esc(reached)} rpm ｜ 最高板端回授 {fmt(peak_rpm,0)} rpm{f' ｜ 結束時目標 {esc(last_target)} rpm' if last_target else ''}</p>
<div class="cards"><div class="card">記錄結果<b class="{'good' if reason=='sequence_complete' else 'warn'}">{status}</b>{esc(reason or '沒有 session_end 事件')}</div><div class="card">總記錄時間<b>{duration:.1f} s</b>包含啟動與停機後記錄</div><div class="card">完成轉速組數<b>{len(completed)} / {len(cfg.get('speeds',[]))}</b>計時完成不等於力規穩定</div><div class="card">故障 / 異常紀錄<b>{len(fault_rows)} / {len(errors)}</b>故障量測筆數 / 異常筆數</div></div>
<p class="note">{esc(direction_note)}</p>
<p class="note">各圖使用相同時間軸。藍底為定速記錄，灰底為啟動前／停機後，淡橘為啟動或轉換。曲線保留原始點；大量資料以分桶最小／最大值縮減顯示，通訊長間隔斷線呈現，不平滑補值。</p>
{overlay}
<section aria-label="轉速、推力與扭矩三聯圖"><h2>轉速、推力與扭矩</h2>{''.join(sections)}</section>
<section><h2>各轉速統計</h2><p class="note">全段平均包含到速後尚未穩定的資料。「末段」取該組最後最多 30 秒，僅為比較視窗，不自動判定穩定。扣基準值僅在本報告另列，不改寫原始紀錄。</p>{table(['組','目標 rpm','狀態','量測跨度 s','平均 rpm','全段推力 N','末段推力 N','末段扣基準 N','全段扭矩 Nm'],stage_rows)}</section>
<section><h2>啟動前與停機後基準</h2>{table(['量測','啟動前平均','停機後最後最多10秒平均','前後差值'],zero_rows)}<p class="note">停機後平均可能仍包含回復過程；程式未量測機械停穩時間，也無法識別儀器上的人工歸零。前後差值不是校正準確度。</p></section>
<details open><summary>每組轉速的 30 秒分段趨勢</summary>{table(['組','目標 rpm','組內時間 s','平均 rpm','平均推力 N','平均扭矩 Nm'],detail_rows)}</details>
<details><summary>電氣、溫度與原始計數</summary><p class="note">Motor Pilot 回報功率不是獨立量測的軸端機械功率。未接電供的讀值顯示缺值，不以 Pilot 功率代替輸入功率。</p>{''.join(electric)}</details>
<details><summary>取樣品質與事件</summary>{table(['設備','量測筆數','平均 Hz','最大間隔 s'],quality)}{table(['時間 s','事件','組','目標 rpm','說明'],event_rows)}</details>
<section><h2>PID／PLL 板端讀回</h2>{table(['參數','板端值'],board_pid_rows) if board_pid_rows else '<p class="note">本輪未讀回板端參數。</p>'}</section>
<section><h2>Speed PID 手動紀錄</h2><p class="note">來自操作者抄錄。空白表示未記錄。</p>{table(["參數","紀錄值"],pid_rows)}</section>
<details><summary>本次設定</summary><pre>{esc(json.dumps(cfg,ensure_ascii=False,indent=2))}</pre></details>
</main></body></html>'''
    output=path.with_name(path.stem+'_report.html')
    fd,tmp=tempfile.mkstemp(prefix='.report-',suffix='.tmp',dir=output.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(body)
        os.replace(tmp,output)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return output

if __name__=='__main__':
    import sys
    print(generate_report(sys.argv[1]))
