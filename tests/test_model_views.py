import unittest
from kompas_local_mcp.adapter import Adapter,PUBLIC_TOOLS

class ModelViewTests(unittest.TestCase):
 def test_model_view_tools_exposed(self):
  for n in ('create_model_view','create_section_view','update_model_views','model_view_state'):
   self.assertIn(n,PUBLIC_TOOLS)
 def test_bad_view_arguments_before_com(self):
  self.assertTrue(hasattr(Adapter,'create_model_view'));a=object.__new__(Adapter)
  with self.assertRaises(ValueError):a.create_model_view('d',r'C:\part.m3d','front','v',0,0,scale=0)
  with self.assertRaises(ValueError):a.create_model_view('d',r'C:\part.m3d','unknown','v',0,0)
 def test_section_requires_a_nonzero_straight_line(self):
  self.assertTrue(hasattr(Adapter,'create_section_view'));a=object.__new__(Adapter)
  for points in ([[0,0]],[[0,0],[0,0]],[[0,0],[float('nan'),1]],[[0,0],[1,1],[2,0]]):
   with self.assertRaises(ValueError):a.create_section_view('d',1,points,'A',0,0)
 def test_activating_linked_view_preserves_scale(self):
  from types import SimpleNamespace
  class View:
   Number=1;Name='linked';Scale=1.;X=0.;Y=0.;Angle=0.;ObjectCount=4;ViewType=2
   def __init__(self):self._current=False
   @property
   def Current(self):return self._current
   @Current.setter
   def Current(self,value):self._current=value;self.Scale=0.
   def Update(self):return True
  view=View();views=SimpleNamespace(ViewByNumber=lambda n:view,ActiveView=view)
  a=object.__new__(Adapter);a._views=lambda d:views
  def open_view(n):view._current=True;return 0
  a._a5=lambda d:SimpleNamespace(ksOpenView=open_view)
  self.assertEqual(a.set_active_view('doc',1)['scale'],1.)
if __name__=='__main__':unittest.main()
