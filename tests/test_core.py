import math
import unittest
from kompas_local_mcp.core import sheet_point, windows_path, positive, ReferenceStore
from kompas_local_mcp.worker import SerialWorker

class CoreTests(unittest.TestCase):
    def test_delete_invalidates_all_aliases_only_for_same_document(self):
        store=ReferenceStore()
        aliases=[store.add('doc',42) for _ in range(2)]
        other=store.add('other',42)
        store.invalidate_reference('doc',42)
        for token in aliases:
            with self.assertRaises(ValueError):store.get(token,'doc')
        self.assertEqual(store.get(other,'other'),42)

    def test_verified_output_rejects_stale_file_and_preserves_it(self):
        import tempfile
        from pathlib import Path
        from kompas_local_mcp.core import verified_output
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path=Path(folder)/'old.png';path.write_bytes(b'old')
            with self.assertRaises(RuntimeError):verified_output(path,lambda stage:None)
            self.assertEqual(path.read_bytes(),b'old')
            verified_output(path,lambda stage:Path(stage).write_bytes(b'new'))
            self.assertEqual(path.read_bytes(),b'new')
    def test_view_rotation_scale_translation(self):
        x,y=sheet_point(10,20,40,50,.02,90)
        self.assertAlmostEqual(x,39.6);self.assertAlmostEqual(y,50.2)

    def test_windows_path_preserves_unicode(self):
        self.assertEqual(windows_path('C:/work/цех.cdw'),r'C:\work\цех.cdw')
        with self.assertRaises(ValueError):windows_path('../relative.cdw')

    def test_nonfinite_or_nonpositive_dimensions(self):
        for n in [0,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):positive(n,'width')

    def test_stale_and_wrong_document_refs(self):
        a=ReferenceStore('sessionA');b=ReferenceStore('sessionB')
        ref=a.add('doc1',42)
        self.assertEqual(a.get(ref,'doc1'),42)
        for store,doc in [(a,'doc2'),(b,'doc1')]:
            with self.assertRaises(ValueError):store.get(ref,doc)
        a.invalidate('doc1')
        with self.assertRaises(ValueError):a.get(ref,'doc1')

    def test_worker_runs_on_one_thread_and_preserves_exceptions(self):
        import threading
        w=SerialWorker(lambda:object())
        try:
            ids=[w.call(lambda _:threading.get_ident()) for _ in range(4)]
            self.assertEqual(len(set(ids)),1)
            self.assertNotEqual(ids[0],threading.get_ident())
            with self.assertRaises(ValueError):w.call(lambda _:(_ for _ in ()).throw(ValueError('bad')))
            self.assertEqual(w.call(lambda _:7),7)
        finally:w.close()

if __name__=='__main__':unittest.main()
