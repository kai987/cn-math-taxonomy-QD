#!/usr/bin/env python3
"""Package public pages with assets isolated in this release's Git SHA directory."""
import argparse
import json
from pathlib import Path
import posixpath
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
FILES = (
    'index.html', 'update-check.js', '.nojekyll', 'LICENSE',
    'diagnose/index.html', 'diagnose/style.css', 'diagnose/engine.js', 'diagnose/app.js',
    'data/topics.json', 'data/dependencies.json', 'data/cn-curriculum-standards.json',
    'data/questions.json', 'data/id-aliases.json',
)
VERSIONED_FILES = frozenset(relative for relative in FILES
                            if relative.endswith(('.css', '.json'))
                            or (relative.endswith('.js') and relative != 'update-check.js'))


def public_path(relative, version):
    return f'assets/{version}/{relative}' if relative in VERSIONED_FILES else relative


def build(output, version):
    if not re.fullmatch(r'[a-f0-9]{40}', version):
        raise ValueError('version must be a full Git commit SHA (40 lowercase hex characters)')
    output = Path(output).resolve()
    if output == ROOT or ROOT.is_relative_to(output):
        raise ValueError('output must not be the source directory or one of its parents')
    # Never remove or mix in existing files: a release must have an exact file set.
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('output directory must be empty')
    for relative in FILES:
        source = ROOT / relative
        target = output / public_path(relative, version)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.html':
            html = source.read_text(encoding='utf-8')
            html = html.replace('name="app-version" content="development"',
                                f'name="app-version" content="{version}"')
            page_dir = posixpath.dirname(relative) or '.'
            assets_base = posixpath.relpath(f'assets/{version}', page_dir) + '/'
            html, count = re.subn(r'(name="app-assets-base" content=")[^"]*(")',
                                  lambda match: match[1] + assets_base + match[2], html)
            if count != 1:
                raise ValueError(f'{relative} must have exactly one app-assets-base meta tag')

            def asset_url(match):
                asset = match[2]
                asset_source = posixpath.normpath(posixpath.join(page_dir, asset))
                if asset_source in VERSIONED_FILES:
                    destination = posixpath.relpath(public_path(asset_source, version), page_dir)
                    return match[1] + destination + match[3]
                # Keep the recovery bootstrap at a stable root path so stale
                # HTML can still offer an update when its old assets are gone.
                if asset_source == 'update-check.js':
                    return match[1] + asset + '?v=' + version + match[3]
                return match[0]

            html = re.sub(r'((?:src|href)=")([^"?]+\.(?:js|css))(")', asset_url, html)
            target.write_text(html, encoding='utf-8')
        else:
            shutil.copyfile(source, target)
    (output / 'version.json').write_text(json.dumps({'version': version}) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    build(args.output, args.version)
    print(f'Site built at {args.output} ({args.version})')
