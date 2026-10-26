import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('build_site', ROOT / 'scripts/build_site.py')
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)
VERSION = 'a' * 40


class SiteBuildTests(unittest.TestCase):
    def test_release_is_complete_and_only_contains_public_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            site.build(output, VERSION)
            files = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
            self.assertEqual(files, set(site.FILES) | {'version.json'})
            self.assertEqual(json.loads((output / 'version.json').read_text()), {'version': VERSION})
            for page in ('index.html', 'diagnose/index.html'):
                html = (output / page).read_text()
                self.assertIn(f'name="app-version" content="{VERSION}"', html)
                self.assertNotIn('content="development"', html)
                assets = re.findall(r'(?:src|href)="([^\"]+\.(?:css|js)[^\"]*)"', html)
                self.assertTrue(assets)
                for asset in assets:
                    self.assertTrue(asset.endswith('?v=' + VERSION))
                    self.assertTrue(((output / page).parent / asset.split('?')[0]).is_file())
            for relative in site.FILES:
                if not relative.endswith('.html'):
                    self.assertEqual((ROOT / relative).read_bytes(), (output / relative).read_bytes())

    def test_new_commit_changes_asset_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'first', Path(directory) / 'second'
            site.build(first, VERSION)
            site.build(second, 'b' * 40)
            self.assertNotEqual((first / 'diagnose/index.html').read_text(),
                                (second / 'diagnose/index.html').read_text())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'keep.txt'
            marker.write_text('keep me')
            with self.assertRaises(ValueError):
                site.build(directory, VERSION)
            self.assertEqual(marker.read_text(), 'keep me')

    def test_bad_versions_and_source_destinations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for version in ('main', '../bad', '', 'a' * 39):
                with self.subTest(version=version), self.assertRaises(ValueError):
                    site.build(Path(directory) / 'output', version)
        for path in (ROOT, ROOT.parent):
            with self.subTest(path=path), self.assertRaises(ValueError):
                site.build(path, VERSION)


if __name__ == '__main__':
    unittest.main()
