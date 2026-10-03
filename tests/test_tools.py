"""Offline unit tests; browser smoke exports are documented separately."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('poster',ROOT / 'tools/poster.py')
poster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poster)


class ToolsTest(unittest.TestCase):
    def test_templates_init_and_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            for name in poster.TEMPLATES:
                dest = Path(d) / name
                poster.init(Namespace(template=name,dest=dest))
                source = dest / 'poster.html'
                self.assertEqual(poster.canvas(source),(841.,1189.))
                text = poster.bundle_text(source)
                self.assertNotIn('../assets/',text)
                self.assertNotIn('src="assets/',text)
                self.assertIn('data:image/svg+xml;base64,',text)
                with self.assertRaises(ValueError):
                    poster.init(Namespace(template=name,dest=dest))

    def test_asset_confinement(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d) / 'project'
            parent.mkdir()
            with self.assertRaises(ValueError): poster.local_asset('../private.txt',parent)
            with self.assertRaises(ValueError): poster.local_asset('https://example.org/a.png',parent)
            (parent / 'original.svg').write_text('<svg/>')
            (parent / 'alias.svg').symlink_to(parent / 'original.svg')
            with self.assertRaises(ValueError): poster.local_asset('alias.svg',parent)

    def test_staleness(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / 'project'
            poster.init(Namespace(template='band-story',dest=dest))
            before = poster.fingerprint(dest / 'poster.html')
            (dest / 'assets/logo-slot.svg').write_text('<svg/>')
            self.assertNotEqual(before,poster.fingerprint(dest / 'poster.html'))

    def test_script_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'poster.html'
            source.write_text('<script>alert(1)</script>')
            with self.assertRaises(ValueError): poster.bundle_text(source)


if __name__ == '__main__':
    unittest.main()
