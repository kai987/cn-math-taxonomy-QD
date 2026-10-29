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
            output = (Path(directory) / 'site').resolve()
            site.build(output, VERSION)
            files = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
            stable = {'.nojekyll', 'LICENSE', 'index.html', 'diagnose/index.html', 'update-check.js', 'version.json'}
            assets = {f'assets/{VERSION}/{p}' for p in site.VERSIONED_FILES}
            self.assertEqual(files, stable | assets)
            self.assertEqual(json.loads((output / 'version.json').read_text()), {'version': VERSION})
            for page in ('index.html', 'diagnose/index.html'):
                html = (output / page).read_text()
                self.assertIn(f'name="app-version" content="{VERSION}"', html)
                self.assertNotIn('content="development"', html)
                base = re.search(r'name="app-assets-base" content="([^"]+)"', html)[1]
                self.assertEqual(((output / page).parent / base).resolve(),
                                 (output / 'assets' / VERSION).resolve())
                refs = re.findall(r'(?:src|href)="([^\"]+\.(?:css|js)[^\"]*)"', html)
                self.assertTrue(refs)
                for asset in refs:
                    resolved = ((output / page).parent / asset.split('?')[0]).resolve()
                    self.assertTrue(resolved.is_file())
                    if resolved.name == 'update-check.js':
                        self.assertEqual(resolved, (output / 'update-check.js').resolve())
                        self.assertTrue(asset.endswith('?v=' + VERSION))
                    else:
                        self.assertTrue(resolved.is_relative_to(output / 'assets' / VERSION))
                        self.assertNotIn('?', asset)
            for relative in site.FILES:
                if not relative.endswith('.html'):
                    self.assertEqual((ROOT / relative).read_bytes(),
                                     (output / site.public_path(relative, VERSION)).read_bytes())
            self.assertFalse((output / 'data').exists())
            self.assertFalse((output / 'diagnose' / 'app.js').exists())

    def test_a_new_release_cannot_resolve_an_old_asset_path_to_new_content(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'first', Path(directory) / 'second'
            next_version = 'b' * 40
            site.build(first, VERSION)
            site.build(second, next_version)
            self.assertNotEqual((first / 'diagnose/index.html').read_text(),
                                (second / 'diagnose/index.html').read_text())
            for relative in site.VERSIONED_FILES:
                self.assertTrue((first / 'assets' / VERSION / relative).is_file())
                self.assertTrue((second / 'assets' / next_version / relative).is_file())
                self.assertFalse((second / 'assets' / VERSION / relative).exists())
            # Recovery stays available even when old app/CSS/data paths return 404.
            self.assertTrue((second / 'update-check.js').is_file())
            self.assertTrue((second / 'version.json').is_file())

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
