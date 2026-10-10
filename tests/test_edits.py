import unittest
from kompas_local_mcp.edits import checked_resize, apply_properties

class EditTests(unittest.TestCase):
    def test_resize_validation_precedes_com(self):
        for w,h in ((0,1),(1,-2),(float('nan'),1),(1,float('inf'))):
            with self.assertRaises(ValueError):checked_resize(w,h)
    def test_failed_update_restores_original_geometry(self):
        class Object:
            Width=100;Height=200;calls=0
            def Update(self):
                self.calls+=1
                return self.calls>1
        obj=Object()
        with self.assertRaisesRegex(RuntimeError,'Update failed'):apply_properties(obj,{'Width':500,'Height':800})
        self.assertEqual((obj.Width,obj.Height),(100,200))
    def test_partial_setter_exception_restores_prior_changes(self):
        class Object:
            Width=100
            @property
            def Height(self):return 200
            @Height.setter
            def Height(self,v):
                if v!=200:raise RuntimeError('setter failed')
            def Update(self):return True
        obj=Object()
        with self.assertRaisesRegex(RuntimeError,'setter failed'):apply_properties(obj,{'Width':500,'Height':800})
        self.assertEqual(obj.Width,100)

    def test_text_edit_uses_native_replace_without_resetting_font(self):
        from types import SimpleNamespace
        from kompas_local_mcp.adapter import Adapter
        font=SimpleNamespace(FontName='Arial',Height=4.4,WidthFactor=1.,Color=42,Bold=True,Italic=False,Underline=False,TextLineStep=1.)
        class Ole:
            def QueryInterface(self,*args):return font
        item=SimpleNamespace(_oleobj_=Ole(),Update=lambda:True)
        class Text:
            _str='Original';Count=1
            @property
            def Str(self):return self._str
            @Str.setter
            def Str(self,value):self._str=value;font.FontName='GOST type A';font.Height=3.5
            def Replace(self,old,new,case,word,all):
                assert old==self._str
                self._str=new;return True
            def TextLine(self,index):return SimpleNamespace(Count=1,TextItem=lambda _:item)
        class FontFactory:
            CLSID='font'
            def __call__(self,raw):return raw
        text=Text();obj=SimpleNamespace(Update=lambda:True,Reference=101)
        a=object.__new__(Adapter);a._find_native_object=lambda *args:obj
        a.api7=SimpleNamespace(IText=lambda _:text,ITextFont=FontFactory());a.com=SimpleNamespace(IID_IDispatch='dispatch')
        a.edit_text('doc','ref','New — ×')
        self.assertEqual(text.Str,'New — ×');self.assertEqual(font.FontName,'Arial');self.assertEqual(font.Height,4.4)

    def test_complex_source_text_rejected_without_assignment(self):
        from types import SimpleNamespace
        from kompas_local_mcp.adapter import Adapter
        for lines,items in ((2,1),(1,2)):
            class Text:
                Count=lines;assigned=False
                @property
                def Str(self):return 'Original'
                @Str.setter
                def Str(self,value):self.assigned=True
                def TextLine(self,index):return SimpleNamespace(Count=items,TextItem=lambda _:None)
            text=Text();a=object.__new__(Adapter);a._find_native_object=lambda *args:None
            a.api7=SimpleNamespace(IText=lambda _:text)
            with self.assertRaises(ValueError):a.edit_text('doc','ref','Replacement')
            self.assertFalse(text.assigned)
