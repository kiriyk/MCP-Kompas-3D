import unittest
from kompas_local_mcp.adapter import Adapter, PUBLIC_TOOLS

class ModelTests(unittest.TestCase):
 def adapter(self,method):
  self.assertTrue(callable(getattr(Adapter,method,None)),f'Missing {method}')
  return object.__new__(Adapter)

 def test_model_commands_exposed(self):
  for name in ('create_part','create_assembly','model_state','save_model','open_model','close_model','create_sketch','sketch_polygon','sketch_circle','extrude','set_extrusion_depth','rebuild_model'):
   self.assertIn(name,PUBLIC_TOOLS)

 def test_invalid_name_rejected_before_com(self):
  a=self.adapter('create_part')
  for name in ('','  '):
   with self.assertRaises(ValueError):a.create_part(name)

 def test_invalid_plane_rejected_before_com(self):
  a=self.adapter('create_sketch')
  with self.assertRaises(ValueError):a.create_sketch('unused','AB')
  with self.assertRaises(ValueError):a.create_sketch('unused','XY',offset=float('nan'))

 def test_invalid_profiles_rejected_before_com(self):
  a=self.adapter('sketch_polygon')
  for points in ([[0,0],[1,1]],[[0,0],[1,1],[2,2]],[[0,0],[3,3],[0,3],[3,0]],[[0,0],[2,0],[2,float('inf')]],[[0,0],[1,0],[1,0],[0,1]]):
   with self.assertRaises(ValueError):a.sketch_polygon('unused','unused',points)

 def test_bad_extrusion_rejected_before_com(self):
  a=self.adapter('extrude')
  for depth in (0,-1,float('nan')):
   with self.assertRaises(ValueError):a.extrude('unused','unused',depth)
  with self.assertRaises(ValueError):a.extrude('unused','unused',10,operation='unknown')

 def test_model_reference_cannot_cross_documents_or_kinds(self):
  a=self.adapter('_model_ref')
  a.model_refs={'key':('doc','sketch',object())}
  with self.assertRaises(ValueError):a._model_ref('other','key','sketch')
  with self.assertRaises(ValueError):a._model_ref('doc','key','component')
  with self.assertRaises(ValueError):a._model_ref('doc','old','sketch')

 def test_empty_model_has_no_fake_gabarit(self):
  from kompas_local_mcp.model_documents import solid_bounds
  self.assertIsNone(solid_bounds((False,0,0,0,0,0,0)))
  self.assertIsNone(solid_bounds((True,1e300,1e300,1e300,-1e300,-1e300,-1e300)))
  self.assertEqual(solid_bounds((True,0,0,0,20,30,40)),{'min':[0.,0.,0.],'max':[20.,30.,40.],'size':[20.,30.,40.]})

if __name__=='__main__':unittest.main()
