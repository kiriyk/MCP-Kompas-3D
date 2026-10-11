import unittest
from kompas_local_mcp.adapter import Adapter,PUBLIC_TOOLS

class AssemblyTests(unittest.TestCase):
 def test_assembly_commands_available(self):
  for name in ('insert_component','set_component_placement','list_components','export_model'):
   self.assertIn(name,PUBLIC_TOOLS)
 def test_bad_placement_rejected_before_com(self):
  self.assertTrue(hasattr(Adapter,'set_component_placement'))
  a=object.__new__(Adapter)
  for origin,x,y in (([0,0],[1,0,0],[0,1,0]),([0,0,0],[2,0,0],[0,1,0]),([0,0,0],[1,0,0],[1,0,0]),([float('nan'),0,0],[1,0,0],[0,1,0])):
   with self.assertRaises(ValueError):a.set_component_placement('d','r',origin,x,y)
 def test_invalid_export_format_rejected_before_com(self):
  self.assertTrue(hasattr(Adapter,'export_model'))
  a=object.__new__(Adapter)
  with self.assertRaises(ValueError):a.export_model('d',r'C:\work\a.obj','obj')
 def test_stl_validation_rejects_truncated_binary(self):
  self.assertTrue(hasattr(Adapter,'export_model'))
  import tempfile,struct
  from pathlib import Path
  from kompas_local_mcp.model_io import inspect_stl
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'test.stl';p.write_bytes(b' ' *80+struct.pack('<I',2)+b' ' *50)
   with self.assertRaises(ValueError):inspect_stl(p)
if __name__=='__main__':unittest.main()
