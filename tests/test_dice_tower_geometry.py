import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))

class TowerGeometryTests(unittest.TestCase):
 def test_nominal_tower_passages_exceed_cube_diagonal(self):
  import importlib.util
  self.assertIsNotNone(importlib.util.find_spec('dice_tower_parameters'),'Missing clearance calculation')
  from dice_tower_parameters import tower_parameters,validate_dice_clearances
  p=tower_parameters();r=validate_dice_clearances(p)
  self.assertEqual(p['height'],220);self.assertEqual(p['width'],90);self.assertEqual(p['wall'],3)
  self.assertGreater(r['end_gap_mm'],40.10)
  self.assertGreater(r['exit_headroom_mm'],40.10)
 def test_oversize_cube_or_long_baffle_rejected(self):
  import importlib.util
  self.assertIsNotNone(importlib.util.find_spec('dice_tower_parameters'))
  from dice_tower_parameters import tower_parameters,validate_dice_clearances
  for field,value in (('dice',30),('baffle_projection',65)):
   p=tower_parameters();p[field]=value
   with self.assertRaises(ValueError):validate_dice_clearances(p)
if __name__=='__main__':unittest.main()
