import unittest
from types import SimpleNamespace
from kompas_local_mcp.adapter import Adapter

class AdvancedEditTests(unittest.TestCase):
 def test_property_validation_before_lookup(self):
  a=object.__new__(Adapter);a._find_native_object=lambda *args: self.fail('COM touched before validation')
  for args in ({},{'angle':float('nan')},{'style':0},{'style':True},{'style':2.5}):
   with self.assertRaises(ValueError):a.set_object_properties('doc','ref',**args)

 def test_absolute_angle_normalized_and_identity_retained(self):
  obj=SimpleNamespace(Angle=2.,Style=1,Reference=123,Update=lambda:True)
  a=object.__new__(Adapter);a._find_native_object=lambda *args:obj;a.api7=SimpleNamespace(IRectangle=lambda _:obj)
  result=a.set_object_properties('doc','ref',angle=360,style=2)
  self.assertEqual((obj.Angle,obj.Style),(0,2));self.assertEqual(result['api_reference'],123)

 def test_dimension_invalid_measurement_does_not_mutate(self):
  obj=SimpleNamespace(Orientation=1,X1=0,Y1=0,X2=1000,Y2=0,X3=500,Y3=100)
  a=object.__new__(Adapter);a._find_dimension=lambda *args:obj
  with self.assertRaises(ValueError):a.edit_linear_dimension('doc','ref',0,0,0,500,100,200)
  self.assertEqual((obj.X2,obj.Y3),(1000,100))

 def test_quarter_arc_bounds_exclude_unvisited_extrema(self):
  from kompas_local_mcp.advanced_edits import arc_points
  pts=arc_points(10,20,5,0,90,False)
  self.assertAlmostEqual(min(p[0] for p in pts),10);self.assertAlmostEqual(min(p[1] for p in pts),20)
  self.assertAlmostEqual(max(p[0] for p in pts),15);self.assertAlmostEqual(max(p[1] for p in pts),25)

 def test_clockwise_arc_includes_other_quadrants(self):
  from kompas_local_mcp.advanced_edits import arc_points
  pts=arc_points(0,0,5,0,90,True)
  self.assertAlmostEqual(min(p[0] for p in pts),-5);self.assertAlmostEqual(min(p[1] for p in pts),-5)

 def test_parallel_offset_ignored_by_api_is_rejected_and_rolled_back(self):
  class Dimension:
   Orientation=0;X1=0;Y1=0;X2=1000;Y2=0;X3=500;Y3=200;calls=0
   def Update(self):
    self.calls+=1
    if self.calls==1:self.X3=0;self.Y3=0
    return True
  obj=Dimension();a=object.__new__(Adapter);a._find_dimension=lambda *args:obj
  with self.assertRaisesRegex(RuntimeError,'offset'):
   a.edit_linear_dimension('doc','ref',0,0,1000,0,0,500,'parallel')
  self.assertEqual((obj.X3,obj.Y3),(500,200))
