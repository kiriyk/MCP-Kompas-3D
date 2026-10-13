import unittest, math
from types import SimpleNamespace
from kompas_local_mcp.adapter import Adapter, PUBLIC_TOOLS

class InspectionTests(unittest.TestCase):
 def test_saving_linked_existing_model_preserves_path(self):
  import tempfile,os
  from pathlib import Path
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'part.m3d';path.write_bytes(b'old')
   doc=SimpleNamespace(DocumentType=4,PathName=str(path),Changed=True)
   def save():
    path.write_bytes(b'new native model');os.utime(path,ns=(1,path.stat().st_mtime_ns+100000));doc.Changed=False;return False
   doc.Save=save
   a=object.__new__(Adapter);a._model_doc=lambda d:doc;a._model5=lambda d:self.fail('Linked model must not SaveAs a temporary name')
   self.assertTrue(a.save_model('d',str(path))['source_identity_preserved'])
   doc.Changed=True;doc.Save=lambda:False
   with self.assertRaisesRegex(RuntimeError,'Existing model save postcondition failed'):a.save_model('d',str(path))
 def test_tools_exposed(self):
  for name in ('select_model_topology','measure_model_geometry','check_model_measurements','check_assembly_intersections','set_model_orientation','set_model_appearance','list_model_bodies','upsert_component','remove_component'):
   self.assertIn(name,PUBLIC_TOOLS)
 def test_query_filters_geometry_not_index(self):
  a=object.__new__(Adapter)
  items=[{'reference':'a','planar':True,'radius_mm':None,'normal':[0,0,1],'owner_name':'cap','bounds_mm':{'min':[0,0,10],'max':[10,10,10]}},{'reference':'b','planar':True,'normal':[1,0,0],'bounds_mm':{'min':[0,0,0],'max':[0,10,10]}}]
  a.list_model_topology=lambda *args,**kw:{'items':items}
  result=a.select_model_topology('d',planar=True,normal=[0,0,-1],bounds_min=[-1,-1,9],bounds_max=[11,11,11])
  self.assertEqual([i['reference'] for i in result['items']],['a'])
 def test_arc_radius_uses_arc_parameter_interface(self):
  a=object.__new__(Adapter)
  curve=SimpleNamespace(IsCircle=lambda:False,IsArc=lambda:True,GetCurveParam=lambda:'arc')
  a.api5=SimpleNamespace(ksCurve3D=lambda c:c,ksArc3dParam=lambda p:SimpleNamespace(radius=41),ksCircle3dParam=lambda p:self.fail('Circle interface used for arc'))
  edge=SimpleNamespace(GetOwnerEntity=lambda:None,GetCurve3D=lambda:curve,IsStraight=lambda:False)
  self.assertEqual(a._topology_properties(edge,'edge',None)['radius_mm'],41)
 def test_query_invalid_before_com(self):
  a=object.__new__(Adapter)
  for kw in ({'normal':[0,0,0]},{'bounds_min':[0,0,0]},{'radius':-1},{'tolerance':float('nan')}):
   with self.assertRaises(ValueError):a.select_model_topology('d',**kw)
 def test_measurement_invalid_before_com(self):
  a=object.__new__(Adapter)
  with self.assertRaises(ValueError):a.measure_model_geometry('d','r','r')
  with self.assertRaises(ValueError):a.check_model_measurements('d',[['a']],2)
  with self.assertRaises(ValueError):a.check_model_measurements('d',[['a','b']],-2)
 def test_measurement_failure_is_not_zero(self):
  a=object.__new__(Adapter);a._model_doc=lambda d:None
  a.model_refs={'a':('d','face','first'),'b':('d','face','second')}
  a._part5=lambda d:SimpleNamespace(GetMeasurer=lambda:SimpleNamespace(SetObject1=lambda o:False))
  with self.assertRaises(RuntimeError):a.measure_model_geometry('d','a','b')
 def test_display_invalid_before_com(self):
  a=object.__new__(Adapter)
  with self.assertRaises(ValueError):a.set_model_orientation('d',projection='invalid')
  with self.assertRaises(ValueError):a.set_model_appearance('d',color=True)
  with self.assertRaises(ValueError):a.set_model_appearance('d',color=1,transparency_percent=101)
 def test_noop_color_does_not_require_update(self):
  from test_model_color import ModelColorTests
  a,p=ModelColorTests().setup_adapter();a.set_model_color('d',0x123456);p.fail_update=True
  self.assertEqual(a.set_model_color('d',0x123456)['color'],0x123456)
 def test_appearance_failed_update_is_not_success(self):
  from test_model_color import ModelColorTests
  a,p=ModelColorTests().setup_adapter();p.fail_update=True
  with self.assertRaisesRegex(RuntimeError,'update failed|rollback incomplete'):
   a.set_model_appearance('d',255,cascade=False)
 def test_appearance_successful_rollback_retains_original_error(self):
  from test_model_color import ModelColorTests
  a,p=ModelColorTests().setup_adapter();original=p.saved;read=p.GetAdvancedColor;calls=[0]
  def read_once_failed():
   calls[0]+=1
   return (False,*p.pending) if calls[0]==2 else read()
  p.GetAdvancedColor=read_once_failed
  with self.assertRaisesRegex(RuntimeError,'^Appearance readback failed$'):
   a.set_model_appearance('d',255,cascade=False)
  self.assertEqual(p.saved,original)
 def test_native_placement_rejects_failed_getters_and_nan(self):
  a=object.__new__(Adapter);a.api5=SimpleNamespace(ksPlacement=lambda p:p)
  for origin in [(False,0,0,0),(True,float('nan'),0,0)]:
   place=SimpleNamespace(GetOrigin=lambda:origin,GetVector=lambda i:(True,*([1,0,0] if i==0 else [0,1,0])))
   with self.assertRaises(RuntimeError):a._placement_info(SimpleNamespace(GetPlacement=lambda:place))
 def test_upsert_existing_component_does_not_insert(self):
  import tempfile
  from pathlib import Path
  a=object.__new__(Adapter);a._model_doc=lambda *args:None
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'source.m3d';path.write_bytes(b'fixture')
   a.list_components=lambda d:{'components':[{'component_reference':'ref','name':'ramp','source_path':str(path)}]}
   a.set_component_placement=lambda *args,**kw:{'component_reference':'ref','placement':{}}
   a.insert_component=lambda *args,**kw:self.fail('Duplicate insertion')
   result=a.upsert_component('d',str(path),'ramp',[0,0,0],[1,0,0],[0,1,0])
   self.assertEqual(result['action'],'reused')
 def test_upsert_ambiguous_name_rejected(self):
  import tempfile
  from pathlib import Path
  a=object.__new__(Adapter);a._model_doc=lambda *args:None
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'source.m3d';path.write_bytes(b'fixture')
   a.list_components=lambda d:{'components':[{'name':'ramp'},{'name':'ramp'}]}
   with self.assertRaises(ValueError):a.upsert_component('d',str(path),'ramp',[0,0,0],[1,0,0],[0,1,0])
if __name__=='__main__':unittest.main()
