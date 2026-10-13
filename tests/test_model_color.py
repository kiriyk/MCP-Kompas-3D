"""Regression: native color must be applied, opaque and independently readable."""
import unittest
from types import SimpleNamespace
from kompas_local_mcp.adapter import Adapter


class NativeColor:
    def __init__(self):
        self.saved = (0x909090, .5, .6, .8, .8, 1., .5)
        self.pending = self.saved
        self.useColor = -1
        self.UseColor = -1
        self.fail_update = False
        self._oleobj_ = SimpleNamespace(QueryInterface=lambda *args: self)

    def GetAdvancedColor(self):
        return (True, *self.pending)

    def SetAdvancedColor(self, *values):
        self.pending = values
        return True

    def Update(self):
        if self.fail_update:
            return False
        self.saved = self.pending
        return True


class ModelColorTests(unittest.TestCase):
    def setup_adapter(self):
        a = object.__new__(Adapter)
        p = NativeColor()
        doc = SimpleNamespace(TopPart=p)
        a._part5 = lambda _: p
        a._model_doc = lambda *args: doc
        a.api7 = SimpleNamespace(IKompasDocument3D=lambda obj: obj,
                                 IColorParam7=lambda obj: obj)
        a.api7.IColorParam7.CLSID = 'color-interface'
        a.com = SimpleNamespace(IID_IDispatch='dispatch')
        return a, p

    def test_color_is_applied_as_opaque(self):
        a, p = self.setup_adapter()
        result = a.set_model_color('part', 0x33FF6B)
        self.assertEqual(p.saved[0], 0x33FF6B)
        self.assertEqual(p.saved[5], 1., 'SDK opacity: zero makes the model invisible')
        self.assertEqual(result['color'], 0x33FF6B)

    def test_failed_update_does_not_report_success(self):
        a, p = self.setup_adapter()
        p.fail_update = True
        with self.assertRaises(RuntimeError):
            a.set_model_color('part', 255)


if __name__ == '__main__':
    unittest.main()
