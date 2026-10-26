#!/usr/bin/env python3
"""Package only public site files and stamp a Git commit into all asset URLs."""
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
FILES = (
    'index.html', 'update-check.js', '.nojekyll', 'LICENSE',
    'diagnose/index.html', 'diagnose/style.css', 'diagnose/engine.js', 'diagnose/app.js',
    'data/topics.json', 'data/dependencies.json', 'data/cn-curriculum-standards.json',
    'data/questions.json', 'data/id-aliases.json',
)


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
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.html':
            html = source.read_text(encoding='utf-8')
            html = html.replace('name="app-version" content="development"',
                                f'name="app-version" content="{version}"')
            html = re.sub(r'((?:src|href)="[^"?]+\.(?:js|css))"',
                          lambda match: f'{match[1]}?v={version}"', html)
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
