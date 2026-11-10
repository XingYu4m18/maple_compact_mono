#!/usr/bin/env python3
"""Controlled Windows DirectWrite regression using immutable v7.9 binaries.

Only metadata is changed: the old, already-compacted outlines and hinting are
kept, isolating naming behavior from geometry. System installation is confined
to the explicitly enabled disposable Windows CI runner.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

from fontTools.ttLib import TTFont
from compact_font import declare_wws_family, require

FAMILY = 'Maple Compact Mono NF CN'
PACKAGE = 'MapleCompactMono-NF-CN.zip'
BASE_URL = 'https://github.com/XingYu4m18/maple_compact_mono/releases/download/v7.9/'


def download(url, path):
    with urllib.request.urlopen(url, timeout=180) as src, path.open('wb') as dst:
        shutil.copyfileobj(src, dst)


def prepare(root):
    root.mkdir(parents=True, exist_ok=True)
    archive = root / PACKAGE
    sha_path = root / PACKAGE.replace('.zip', '.sha256')
    download(BASE_URL + sha_path.name, sha_path)
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != sha_path.read_text().strip():
        download(BASE_URL + PACKAGE, archive)
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == sha_path.read_text().strip(), 'Release checksum mismatch')
    modes = ('original', 'dense', 'names_only', 'wws_only', 'fixed')
    for mode in modes:
        (root / mode).mkdir(exist_ok=True)
    styles = []
    with zipfile.ZipFile(archive) as z:
        for entry in z.namelist():
            if not entry.endswith('.ttf'):
                continue
            source = root / 'original' / Path(entry).name
            source.write_bytes(z.read(entry))
            with TTFont(source) as font:
                names, os2 = font['name'], font['OS/2']
                require(not os2.fsSelection & (1 << 8), 'Expected historical font without WWS declaration')
                require(all('Maple Mono' not in n.toUnicode() for n in names.names if n.nameID in (1, 3, 4, 6, 16, 21)),
                        'Historical font has an unrenamed family field')
                styles.append({'file': source.name, 'full_name': names.getDebugName(4), 'weight': os2.usWeightClass,
                               'style': 'italic' if os2.fsSelection & 1 else 'normal'})
            for mode in modes[1:]:
                with TTFont(source, recalcTimestamp=False) as font:
                    before = {t: font.getTableData(t) for t in font.keys() if t not in ('GlyphOrder', 'head', 'name', 'OS/2')}
                    names = font['name']
                    if mode == 'dense':
                        for n in names.names:
                            if n.nameID not in (0, 7, 8, 9, 13, 14):
                                n.string = n.toUnicode().replace('Compact', 'Dense').encode(n.getEncoding())
                    if mode == 'names_only':
                        # Explicit preferred names alone do not declare a WWS family.
                        style = names.getBestSubFamilyName()
                        names.setName(FAMILY, 16, 3, 1, 0x409)
                        names.setName(style, 17, 3, 1, 0x409)
                    if mode in ('wws_only', 'fixed'):
                        declare_wws_family(font)
                    target = root / mode / source.name
                    font.save(target)
                with TTFont(target) as font:
                    require(all(font.getTableData(t) == data for t, data in before.items()), 'Non-name/style font table changed')
    require(len(styles) == 16, 'Expected all 16 released static faces')
    (root / 'styles.json').write_text(json.dumps(styles, indent=2))


def native(root, executable):
    results = {}
    cases = [('original', '-'), ('dense', '-'), ('names_only', '-'), ('wws_only', FAMILY)] if (root / 'original').exists() else []
    for mode, expected in cases + [('fixed', FAMILY)]:
        result = subprocess.run([str(executable), str(root / mode), expected], capture_output=True, text=True)
        print(mode, result.stdout, result.stderr, flush=True)
        require(result.returncode == 0, 'DirectWrite check failed: ' + mode + ': ' + result.stdout + result.stderr)
        results[mode] = {'families': [s.removeprefix('FAMILY ') for s in result.stdout.splitlines() if s.startswith('FAMILY ')],
                         'native_log': result.stdout}
        print('::notice title=DirectWrite ' + mode + '::' + json.dumps(results[mode]['families']), flush=True)
    if cases:
        results['compact_word_hypothesis_reproduced'] = (results['original']['families'] == ['Maple Mono NF CN']
                                                        and results['dense']['families'] == ['Maple Dense Mono NF CN'])
        print('::notice title=Compact name parsing hypothesis::' + str(results['compact_word_hypothesis_reproduced']), flush=True)
    (root / 'directwrite-results.json').write_text(json.dumps(results, indent=2))


def prepare_candidate(root, archive):
    """Test the actual uploaded release ZIP, without modifying its font bytes."""
    root.mkdir(parents=True, exist_ok=True)
    fixed = root / 'fixed'
    fixed.mkdir(exist_ok=True)
    expected = archive.with_suffix('.sha256').read_text().strip()
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == expected, 'Candidate package checksum mismatch')
    styles = []
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('compact-build.json'))
        require(manifest['font_count'] == 16, 'Candidate package is incomplete')
        for entry in manifest['fonts']:
            data = z.read(entry['file'])
            require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'Candidate font checksum mismatch')
            target = fixed / Path(entry['file']).name
            target.write_bytes(data)
            with TTFont(target) as font:
                require(font['OS/2'].fsSelection & (1 << 8), 'Candidate lacks WWS declaration')
                require(font['name'].getBestFamilyName() == FAMILY, 'Wrong candidate family')
                styles.append({'file': target.name, 'full_name': font['name'].getDebugName(4), 'weight': font['OS/2'].usWeightClass,
                               'style': 'italic' if font['OS/2'].fsSelection & 1 else 'normal'})
    (root / 'styles.json').write_text(json.dumps(styles, indent=2))


def install(root):
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and os.name == 'nt',
            'System font installation is only allowed on a disposable GitHub Windows runner')
    import winreg
    dest = Path(os.environ['WINDIR']) / 'Fonts'
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts',
                        0, winreg.KEY_SET_VALUE) as key:
        for source in (root / 'fixed').glob('*.ttf'):
            target = dest / source.name
            shutil.copyfile(source, target)
            with TTFont(source) as font:
                label = font['name'].getDebugName(4) + ' (TrueType)'
            winreg.SetValueEx(key, label, 0, winreg.REG_SZ, target.name)
            require(ctypes.windll.gdi32.AddFontResourceW(str(target)) > 0, 'Cannot register font')
    ctypes.windll.user32.SendNotifyMessageW(0xFFFF, 0x001D, 0, 0)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('dist/windows-check'))
    p.add_argument('--native', type=Path)
    p.add_argument('--package', type=Path, help='Verify an actual candidate ZIP and its adjacent SHA256 instead of historical ablation cases')
    p.add_argument('--install-ci-fonts', action='store_true')
    args = p.parse_args()
    try:
        if args.package:
            prepare_candidate(args.root, args.package)
        else:
            prepare(args.root)
        if args.native:
            native(args.root, args.native.resolve())
        if args.install_ci_fonts:
            install(args.root)
            if args.native:
                result = subprocess.run([str(args.native.resolve()), str(args.root / 'fixed'), FAMILY, '--system'],
                                        capture_output=True, text=True)
                print(result.stdout, result.stderr, flush=True)
                require(result.returncode == 0, 'Installed DirectWrite family check failed: ' + result.stdout + result.stderr)
                print('::notice title=Installed DirectWrite family::All 16 weights/styles match the correct system font files', flush=True)
    except Exception as error:
        print('::error::' + str(error).replace('\n', '%0A'), flush=True)
        raise
