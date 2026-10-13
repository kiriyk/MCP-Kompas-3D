import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
from tower_runs import RunStore
class RunTests(unittest.TestCase):
 def test_repeat_returns_same_verified_run_without_duplication(self):
  with tempfile.TemporaryDirectory() as td:
   store=RunStore(td);run=store.begin();(run/'part.m3d').write_bytes(b'valid');store.publish(run,'design',{'native_verified':True,'component_count':36})
   self.assertEqual(store.reusable('design'),run)
   self.assertIsNone(store.reusable('other'))
   (run/'part.m3d').write_bytes(b'changed');self.assertIsNone(store.reusable('design'))
 def test_publish_requires_verified_result_inside_root(self):
  with tempfile.TemporaryDirectory() as td:
   store=RunStore(td)
   with self.assertRaises(ValueError):store.publish(Path(td).parent,'design',{'native_verified':True})
   with self.assertRaises(ValueError):store.publish(store.begin(),'design',{'native_verified':False})
 def test_failed_stage_keeps_last_good_manifest(self):
  with tempfile.TemporaryDirectory() as td:
   store=RunStore(td);run=store.begin();(run/'part.m3d').write_bytes(b'valid');store.publish(run,'design',{'native_verified':True})
   failed=store.begin();(failed/'partial.m3d').write_bytes(b'partial')
   self.assertEqual(store.reusable('design'),run)
