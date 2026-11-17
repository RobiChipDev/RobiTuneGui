import csv,json,tempfile,unittest
from unittest.mock import Mock,patch
from pathlib import Path
from report import generate_report,envelope,svg_plot
from config import defaults
from plan_preview import plan_segments,run_notice

class ReportTests(unittest.TestCase):
 def test_report_failure_is_separate_from_recording_and_reports_original_path(self):
  from controller import Controller
  controller=object.__new__(Controller);controller.emit=Mock()
  with patch('controller.generate_report',side_effect=OSError('disk full')):
   controller.build_report(Path('/example/data.csv'))
  self.assertEqual(controller.emit.call_args_list[0].args,('report_error',{'path':'/example/data.csv','error':'disk full'}))
  self.assertIn('原始紀錄已保存',controller.emit.call_args_list[1].args[1])
 def test_realistic_report_missing_psu_repeated_speed_baseline_and_abort(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'data.csv';c=dict(defaults(),mode='REAL',speeds=[1600,1600],run_name='<script>alert(1)</script>')
   p.with_suffix('.json').write_text(json.dumps(c),encoding='utf-8')
   fields=['elapsed_s','row_type','device','channel','stage','stage_index','target_rpm','force_N','torque_Nm','estimated_rpm','reason','detail']
   rows=[dict(elapsed_s=0,row_type='event',reason='session_begin'),dict(elapsed_s=1,row_type='measurement',device='force',channel=1,stage='baseline',stage_index=0,force_N=.01)]
   for idx in (1,2):
    for t in (10,20):rows.append(dict(elapsed_s=t+(idx-1)*30,row_type='measurement',device='force',channel=1,stage='dwelling',stage_index=idx,target_rpm=1600,force_N=.2))
   rows.extend([dict(elapsed_s=60,row_type='measurement',device='force',channel=1,stage='poststop',stage_index=3,force_N=.01),dict(elapsed_s=61,row_type='event',reason='stage_timed_complete',stage_index=1),dict(elapsed_s=62,row_type='event',reason='session_end',detail='operator_stop')])
   with p.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
   original=p.read_bytes();out=generate_report(p);text=out.read_text()
   self.assertEqual(original,p.read_bytes());self.assertIn('流程中止',text);self.assertIn('0.1900',text)
   self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>alert',text)
   self.assertIn('尚無有效量測',text);self.assertIn('未完成',text);self.assertIn('1 / 2',text)
 def test_report_without_metadata_or_measurements_is_explicitly_incomplete(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'empty.csv';p.write_text('elapsed_s,row_type\n0,event\n',encoding='utf-8')
   text=generate_report(p).read_text();self.assertIn('記錄未正常結束',text);self.assertNotIn('nan',text)
 def test_display_preserves_spike_and_breaks_long_gaps(self):
  pts=[(i,100 if i==555 else 0) for i in range(5000)]
  reduced=envelope(pts,100);self.assertIn((555,100),reduced);self.assertLess(len(reduced),110)
  svg=svg_plot([('sample',[(0,0),(1,1),(20,2),(21,3)],'#000',2)],22)
  self.assertEqual(svg.count('<polyline'),2)
 def test_plan_keeps_duplicate_targets_and_configured_durations(self):
  c=dict(defaults(),speeds=[1800,1800,2200],dwell_s=90,baseline_s=30,poststop_s=60)
  seg=plan_segments(c)
  self.assertEqual([s['speed'] for s in seg if s['kind']=='dwell'],[1800,1800,2200])
  self.assertEqual(sum(s['duration'] for s in seg if s['kind']!='ramp' and s['duration'] is not None),360)
  self.assertEqual(next(s['speed'] for s in seg if s['kind']=='wait'),1500)
 def test_notice_never_calls_poststop_completed_or_abort_successful(self):
  title,detail,*_=run_notice(True,'poststop',42)
  self.assertIn('停機後記錄中',title);self.assertIn('42.0',detail)
  self.assertIn('記錄完成',run_notice(False,'idle',0,True,'sequence_complete')[0])
  self.assertIn('中止',run_notice(False,'idle',0,True,'operator_stop')[0])
  self.assertNotIn('記錄完成',run_notice(False,'idle',0,True,'operator_stop')[0])

if __name__=='__main__':unittest.main()
