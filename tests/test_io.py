import unittest
from kompas_local_mcp.io_features import pdf_layout

class PdfLayoutTests(unittest.TestCase):
    def test_sheet_preserves_scale(self):
        self.assertEqual(pdf_layout(841,594,'sheet',True),(841,594,1.0))
    def test_a4_fits_both_dimensions(self):
        w,h,s=pdf_layout(1189,841,'A4',True)
        self.assertEqual((w,h),(297,210))
        self.assertLessEqual(1189*s,w)
        self.assertLessEqual(841*s,h)
    def test_portrait_and_invalid_source(self):
        self.assertEqual(pdf_layout(297,210,'A4',False)[:2],(210,297))
        with self.assertRaises(ValueError):pdf_layout(0,210,'A4',True)
        with self.assertRaises(ValueError):pdf_layout(297,210,'bad',True)

class TransferRollbackTests(unittest.TestCase):
    def test_failed_insert_clears_target_temporary_group(self):
        from kompas_local_mcp.adapter import Adapter
        class CAD:
            reference=100
            def __init__(self):self.cleaned=[]
            def ksNewGroup(self,*args):return 10
            def ksAddObjGroup(self,*args):return 1
            def ksEndGroup(self):return 1
            def ksCopyGroupToDocument(self,*args):return 20
            def ksStoreTmpGroup(self,*args):return 0
            def ksClearGroup(self,*args):self.cleaned.append(args);return 1
        a=object.__new__(Adapter);source=CAD();target=CAD()
        a._doc=lambda _:None;a._checked_reference=lambda *_:1
        a._a5=lambda d:source if d=='s' else target
        a.list_objects=lambda d,**kw:{'items':[{'api_reference':1}] if d=='s' else [],'truncated':False}
        with self.assertRaisesRegex(RuntimeError,'Could not insert'):a.copy_objects_to_document('s','t',['ref'])
        self.assertEqual(target.cleaned,[(20,True)])
        self.assertEqual(source.cleaned,[(10,True)])
