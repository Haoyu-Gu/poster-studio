"""Opt-in browser/print/packaging smoke test using an explicitly synthetic fixture."""
from argparse import Namespace
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('poster',ROOT / 'tools/poster.py')
poster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poster)


@unittest.skipUnless(os.environ.get('POSTERKIT_BROWSER_TESTS') == '1','Opt-in browser test')
class BrowserTest(unittest.TestCase):
    def test_export_qr_package_and_staleness(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            project, final, archive = root/'project', root/'final', root/'delivery.zip'
            poster.init(Namespace(template='band-story',dest=project))
            source = project / 'poster.html'
            # Clearly synthetic, no numerical claims. This is not a paper draft.
            text = source.read_text().replace('TODO:','Sample:').replace('TODO','Sample').replace('DEMO','Sample')
            text = text.replace('https://example.org/','https://example.net/layout-test')
            text = text.replace('example.org','example.net')
            text = text.replace('<h1>Sample: Method</h1>','<h1>Synthetic layout fixture</h1>')
            source.write_text(text)
            (project / 'assets/qr-demo.svg').unlink()
            poster.qr(Namespace(url='https://example.net/layout-test',out=project/'assets/qr-demo.svg'))
            poster.render(Namespace(source=source,out=final,dpi=300,draft=False))
            report = json.loads((final/'check_report.json').read_text())
            self.assertEqual(report['pdf_pages'],1)
            self.assertFalse(report['errors'])
            self.assertTrue(all(q['target_matches'] for q in report['qr_checks']))
            # Unused assets must not leak into a delivery archive.
            (project / 'assets/unused.txt').write_text('Do not ship this unused fixture.')
            poster.package(Namespace(project=project,final=final,out=archive))
            with zipfile.ZipFile(archive) as z:
                self.assertIn('poster.pdf',z.namelist())
                self.assertIn('poster_300dpi.png',z.namelist())
                self.assertFalse(any('notes/' in n for n in z.namelist()))
                self.assertFalse(any('unused.txt' in n for n in z.namelist()))
            # A source edit must invalidate packaging of the old exported version.
            source.write_text(source.read_text() + '\n<!-- changed -->')
            with self.assertRaises(ValueError):
                poster.package(Namespace(project=project,final=final,out=root/'stale.zip'))


if __name__ == '__main__':
    unittest.main()
