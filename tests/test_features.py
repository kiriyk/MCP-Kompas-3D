import unittest
from kompas_local_mcp.adapter import Adapter,PUBLIC_TOOLS

class FeatureTests(unittest.TestCase):
    def test_probed_features_are_exposed(self):
        for name in ('polyline','mixed_contour','bezier','mirror_object','linear_array','circular_array','hatch_polygon'):
            self.assertIn(name,PUBLIC_TOOLS)
            self.assertTrue(callable(getattr(Adapter,name)))

    def test_invalid_vertices_rejected_before_com(self):
        a=object.__new__(Adapter)
        for points in ([[0,0]],[[0,0],[0,0]],[[0,0],[float('nan'),1]],[[0,0],[1,2,3]]):
            with self.assertRaises(ValueError):a.polyline('unused',points)

    def test_invalid_array_does_not_mutate_com(self):
        a=object.__new__(Adapter)
        for count in (0,1,501,2.5,True):
            with self.assertRaises(ValueError):a.linear_array('unused','unused',count,10,0)
        with self.assertRaises(ValueError):a.circular_array('unused','unused',4,0,0,361)
        with self.assertRaises(ValueError):a.mirror_object('unused','unused',0,0,0,0)

    def test_failed_array_rolls_back_earlier_copies(self):
        class FakeCAD:
            def __init__(self):self.calls=0;self.objects=set()
            def ksCopyObj(self,*args):
                self.calls+=1
                if self.calls==2:return 0
                self.objects.add(101);return 101
            def ksDeleteObj(self,ref):self.objects.discard(ref)
            def ksExistObj(self,ref):return ref in self.objects
        a=object.__new__(Adapter);cad=FakeCAD();a._a5=lambda _:cad
        with self.assertRaises(RuntimeError):a._batch_copies('doc',[(1,0,0,10,0,1,0)]*3,4)
        self.assertEqual(cad.objects,set())

    def test_exception_during_composite_deletes_partial_object(self):
        class FakeCAD:
            deleted=None
            def ksEndObj(self):return 202
            def ksDeleteObj(self,ref):self.deleted=ref
        cad=FakeCAD()
        def fail():raise RuntimeError('COM member exception')
        with self.assertRaises(RuntimeError):Adapter._compose(cad,lambda:1,[fail],check_returns=False)
        self.assertEqual(cad.deleted,202)

    def test_rollback_continues_after_one_delete_exception(self):
        class FakeCAD:
            def __init__(self):self.calls=0;self.deleted=[]
            def ksCopyObj(self,*args):
                self.calls+=1
                if self.calls==3:raise RuntimeError('original copy failure')
                return self.calls
            def ksDeleteObj(self,ref):
                self.deleted.append(ref)
                if ref==1:raise RuntimeError('delete failure')
            def ksExistObj(self,ref):return False
        a=object.__new__(Adapter);cad=FakeCAD();a._a5=lambda _:cad
        with self.assertRaisesRegex(RuntimeError,'original copy failure.*remaining API references:.*1'):
            a._batch_copies('doc',[(1,0,0,10,0,1,0)]*3,4)
        self.assertEqual(cad.deleted,[1,2])
