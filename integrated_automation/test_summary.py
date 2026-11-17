import csv,tempfile,unittest
from pathlib import Path
from summarize import summarize
class SummaryTests(unittest.TestCase):
 def test_linear_slope_and_missing_values(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'raw.csv';fields=['row_type','device','channel','stage','stage_index','target_rpm','elapsed_s','raw_signed_int32','unit']
   with p.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for t in range(4):w.writerow(dict(row_type='measurement',device='force',channel=1,stage='dwelling',stage_index=1,target_rpm=1500,elapsed_s=100+t,raw_signed_int32=2*t+1))
   rows=list(csv.DictReader(summarize(p).read_text(encoding='utf-8-sig').splitlines()))
   self.assertEqual(len(rows),1);self.assertEqual(float(rows[0]['mean']),4.);self.assertEqual(float(rows[0]['slope_per_s']),2.)
