import os,tempfile,unittest
from pathlib import Path
from session_files import create_session_folder,latest_session_folder,safe_label

class SessionFolderTests(unittest.TestCase):
 def test_each_run_is_exclusive_even_with_identical_clock(self):
  with tempfile.TemporaryDirectory() as base:
   first=create_session_folder(base,'REAL',[1500,1600],'槳A／正轉',stamp='20261103_140000')
   (first/'data.csv').write_text('original')
   second=create_session_folder(base,'REAL',[1500,1600],'槳A／正轉',stamp='20261103_140000')
   self.assertNotEqual(first,second);self.assertEqual(first.parent,Path(base));self.assertEqual((first/'data.csv').read_text(),'original')
 def test_unsafe_name_does_not_escape_base_and_has_windows_safe_leaf(self):
  with tempfile.TemporaryDirectory() as base:
   folder=create_session_folder(base,'REAL',[1500],'../../A<>:"/\\|?* .',stamp='20261103_140000')
   self.assertEqual(folder.parent,Path(base));self.assertFalse(any(c in folder.name for c in '<>:"/\\|?*'))
   self.assertFalse(folder.name.endswith(('.', ' ')))
 def test_default_name_includes_test_speeds(self):
  with tempfile.TemporaryDirectory() as base:
   folder=create_session_folder(base,'SIMULATION',[1500,1600])
   self.assertTrue(folder.name.startswith('1500-1600rpm_SIMULATION_'))
 def test_open_latest_ignores_unrelated_directories_and_retains_legacy_files(self):
  with tempfile.TemporaryDirectory() as base:
   root=Path(base);legacy=root/'REAL_old.csv';legacy.write_text('legacy')
   one=create_session_folder(root,'REAL',[1500],stamp='one');two=create_session_folder(root,'REAL',[1600],stamp='two')
   for folder in (one,two):
    (folder/'data.csv').write_text('sample');(folder/'data.json').write_text('{}')
   (root/'unrelated').mkdir();os.utime(one,(100,100));os.utime(two,(200,200))
   self.assertEqual(latest_session_folder(root),two);self.assertEqual(legacy.read_text(),'legacy')
 def test_empty_root_falls_back_to_base(self):
  with tempfile.TemporaryDirectory() as base:self.assertEqual(latest_session_folder(base),Path(base))
