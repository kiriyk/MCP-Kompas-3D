import unittest
from kompas_local_mcp.adapter import Adapter, PUBLIC_TOOLS

class ComplexTests(unittest.TestCase):
    def test_complex_commands_exposed(self):
        for name in ('loft','sweep','shell','fillet','sketch_arc','list_model_topology','set_model_display','export_model_png'):
            self.assertIn(name,PUBLIC_TOOLS)
            self.assertTrue(callable(getattr(Adapter,name,None)))

    def test_invalid_inputs_rejected_before_com(self):
        a=object.__new__(Adapter)
        for refs in ([],['a'],['a','a']):
            with self.assertRaises(ValueError):a.loft('d',refs)
        with self.assertRaises(ValueError):a.loft('d',['a','b'],operation='unknown')
        for r in (0,-1,float('nan')):
            with self.assertRaises(ValueError):a.fillet('d',['e'],r)
            with self.assertRaises(ValueError):a.shell('d',['f'],r)
            with self.assertRaises(ValueError):a.sketch_arc('d','s',0,0,r,0,90)
        with self.assertRaises(ValueError):a.fillet('d',[],2)
        with self.assertRaises(ValueError):a.shell('d',[],2)
        with self.assertRaises(ValueError):a.sweep('d','s',[])
        with self.assertRaises(ValueError):a.list_model_topology('d',kind='vertex')
        with self.assertRaises(ValueError):a.set_model_display('d',transparency_percent=101)

    def test_topology_invalidated_without_losing_feature_references(self):
        a=object.__new__(Adapter)
        a.model_refs={'e':('d','edge',object()),'f':('d','face',object()),'s':('d','sketch',object()),'other':('other','face',object())}
        a._invalidate_topology('d')
        self.assertEqual(set(a.model_refs),{'s','other'})

    def test_edge_without_vertex_does_not_construct_a_com_class(self):
        from types import SimpleNamespace
        a=object.__new__(Adapter)
        definition=SimpleNamespace(IsStraight=lambda:True,GetVertex=lambda start:None)
        def unexpected(raw):raise AssertionError('Null vertex must not become COM class creation')
        a.api5=SimpleNamespace(ksEdgeDefinition=lambda raw:definition,ksVertexDefinition=unexpected)
        self.assertIsNone(a._edge_bounds(SimpleNamespace(GetDefinition=lambda:definition)))

    def test_display_noop_does_not_require_native_update(self):
        from test_model_color import ModelColorTests
        a,p=ModelColorTests().setup_adapter()
        doc=a._model_doc('d');doc.DrawMode=3;doc.ShadedWireframe=True
        doc.HideAllPlanes=False;doc.HideAllSketches=False
        p.fail_update=True
        result=a.set_model_display('d',transparency_percent=0)
        self.assertEqual(result['transparency_percent'],0)

if __name__=='__main__':unittest.main()
