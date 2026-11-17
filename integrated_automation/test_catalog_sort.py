import unittest
from propellers import profile, sorted_catalog

class CatalogSortTests(unittest.TestCase):
 def test_numeric_order_pair_adjacency_and_no_mutation(self):
  rows=[profile('1206',2,'PA6+40CF','00','CW'),profile('1050',3,'PA6+40CF','10','CW'),profile('1050',3,'PA6+40CF','2','CCW'),profile('1050',3,'PA6+40CF','2','CW')]
  entries={r['name']:r for r in rows}
  before=list(entries)
  ordered=list(sorted_catalog(entries).values())
  self.assertEqual([(x['dimension'],x['number'],x['rotation']) for x in ordered],[('1050','02','CW'),('1050','02','CCW'),('1050','10','CW'),('1206','00','CW')])
  self.assertEqual(list(entries),before)
 def test_text_codes_and_unknown_rotation_remain_supported(self):
  rows=[profile(d,3,'Black','00',r) for d,r in [('A10',''),('A2','CCW'),('A2','CW'),('A2','')]]
  ordered=list(sorted_catalog({x['name']:x for x in rows}).values())
  self.assertEqual([(x['dimension'],x['rotation']) for x in ordered],[('A2','CW'),('A2','CCW'),('A2',''),('A10','')])
