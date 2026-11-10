#!/usr/bin/env python3
"""Build or verify the Compact500 derivative of pinned Maple Mono NF CN 7.9."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'Maple Compact NF CN'
STYLES = {'Regular': 'Regular', 'Bold': 'Bold', 'Italic': 'Italic', 'BoldItalic': 'Bold Italic'}
MODIFIED = int(datetime(2026, 11, 10, tzinfo=timezone.utc).timestamp()) + 2082844800


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def get_sources(source_dir, lock):
    if source_dir is None:
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        archive = cache / 'MapleMono-NF-CN-v7.9.zip'
        if not archive.exists():
            temporary = archive.with_suffix('.part')
            print('Downloading pinned upstream release...', flush=True)
            with urllib.request.urlopen(lock['asset_url'], timeout=60) as src, temporary.open('wb') as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b''):
                    dst.write(chunk)
            check(sha256(temporary) == lock['archive_sha256'], 'Archive SHA256 mismatch')
            temporary.replace(archive)
        check(sha256(archive) == lock['archive_sha256'], 'Cached archive SHA256 mismatch')
        source_dir = cache / 'upstream'
        source_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for name in lock['files']:
                entries = [n for n in z.namelist() if Path(n).name == name]
                check(len(entries) == 1, f'Missing or ambiguous archive entry: {name}')
                (source_dir / name).write_bytes(z.read(entries[0]))
    for name, expected in lock['files'].items():
        path = source_dir / name
        check(path.is_file(), f'Missing upstream font: {path}')
        check(sha256(path) == expected, f'Upstream font SHA256 mismatch: {name}')
    return source_dir


def build(source, target, suffix):
    with TTFont(source, recalcTimestamp=False) as font:
        check(font['head'].unitsPerEm == 1000, 'Unexpected em size')
        check('GPOS' not in font and 'kern' not in font, 'Positioning tables require a separate transformation')
        glyf = font['glyf']
        transformed, metrics = {}, {}
        for name in font.getGlyphOrder():
            width, _ = font['hmtx'][name]
            check(width in (0, 600, 1200), f'Unexpected width: {name}: {width}')
            coords, endpts, flags = glyf[name].getCoordinates(glyf)
            full = width == 1200
            coords = [(x - 100, y) if full else (round(x * 5 / 6), y) for x, y in coords]
            new = Glyph()
            new.numberOfContours = len(endpts)
            lsb = 0
            if endpts:
                new.coordinates = GlyphCoordinates(coords)
                new.endPtsOfContours = list(endpts)
                new.flags = bytearray(flags)
                new.program = Program()
                new.program.fromBytecode(b'')
                new.recalcBounds(glyf)
                lsb = new.xMin
            transformed[name] = new
            metrics[name] = (1000 if full else 500 if width else 0, lsb)
        glyf.glyphs = transformed
        font['hmtx'].metrics = metrics
        for tag in ('fpgm', 'prep', 'cvt ', 'hdmx', 'LTSH', 'VDMX', 'DSIG'):
            if tag in font:
                del font[tag]
        font['OS/2'].xAvgCharWidth = 500
        font['post'].isFixedPitch = 1
        font['hhea'].advanceWidthMax = 1000
        font['head'].modified = MODIFIED
        style = STYLES[suffix]
        names = {
            1: FAMILY, 2: style, 3: f'{FAMILY} 7.9 Compact500 {suffix}',
            4: FAMILY + ('' if style == 'Regular' else ' ' + style),
            5: 'Version 7.900; local Compact500 derivative',
            6: f'MapleCompactNFCN-{suffix}', 16: FAMILY, 17: style,
            18: FAMILY + ' ' + style,
            10: 'Unofficial derivative of Maple Mono NF CN 7.9. Latin width 500; CJK width 1000; CJK outlines unscaled.',
        }
        # Preserve copyright and license records; replace family identification.
        font['name'].names = [n for n in font['name'].names if n.nameID not in names]
        for nameid, value in names.items():
            font['name'].setName(value, nameid, 3, 1, 0x409)
            font['name'].setName(value, nameid, 1, 0, 0)
        target.parent.mkdir(parents=True, exist_ok=True)
        font.save(target)


def verify(source, target, suffix):
    with TTFont(source) as original, TTFont(target, checkChecksums=2) as font:
        check(font.getGlyphOrder() == original.getGlyphOrder(), 'Glyph order changed')
        cmap = font.getBestCmap()
        check(cmap == original.getBestCmap(), 'Unicode mapping changed')
        check(font['GSUB'].compile(font) == original['GSUB'].compile(original), 'GSUB changed')
        check(font['head'].unitsPerEm == original['head'].unitsPerEm == 1000, 'em size changed')
        check(font['post'].isFixedPitch == 1, 'Fixed-pitch flag missing')
        for table, attributes in [('hhea', ['ascent', 'descent', 'lineGap']),
                                  ('OS/2', ['sTypoAscender', 'sTypoDescender', 'sTypoLineGap', 'usWinAscent', 'usWinDescent'])]:
            check(all(getattr(font[table], a) == getattr(original[table], a) for a in attributes), 'Vertical metrics changed')
        check(font['name'].getDebugName(16) == FAMILY, 'Wrong family name')
        for name, (width, _) in original['hmtx'].metrics.items():
            expected = 1000 if width == 1200 else 500 if width else 0
            check(font['hmtx'][name][0] == expected, f'Wrong advance width: {name}')
            a, ep, flags = original['glyf'][name].getCoordinates(original['glyf'])
            b, ep2, flags2 = font['glyf'][name].getCoordinates(font['glyf'])
            expected_coords = [(x - 100, y) if width == 1200 else (round(x * 5 / 6), y) for x, y in a]
            check(list(ep) == list(ep2) and flags == flags2, f'Contour structure changed: {name}')
            check(list(b) == expected_coords, f'Unexpected outline transformation: {name}')
        overhang, maximum = [], 0
        for cp in range(0x4E00, 0xA000):
            name = cmap.get(cp)
            if not name:
                continue
            g = font['glyf'][name]
            if not g.numberOfContours:
                continue
            extent = max(0, -g.xMin, g.xMax - 1000)
            if extent:
                overhang.append(chr(cp))
                maximum = max(maximum, extent)
        return {
            'style': STYLES[suffix], 'glyphs': len(font.getGlyphOrder()),
            'widths': dict(Counter(w for w, _ in font['hmtx'].metrics.values())),
            'gsub_identical': True, 'cmap_identical': True,
            'all_outlines_verified': True, 'vertical_metrics_identical': True,
            'han_overhang_count': len(overhang), 'han_overhang_max_units': maximum,
            'han_overhang_examples': overhang[:12], 'file': target.name,
            'sha256': sha256(target),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, help='Verified upstream TTF directory; otherwise download the pinned release')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'fonts/maple_compact_nf_cn')
    parser.add_argument('--styles', nargs='+', choices=STYLES, default=list(STYLES))
    parser.add_argument('--verify-only', action='store_true', help='Verify existing output without rebuilding')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/validation.json')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'upstream.lock.json').read_text())
    sources = get_sources(args.source_dir, lock)
    reports = []
    for suffix in args.styles:
        source = sources / f'MapleMono-NF-CN-{suffix}.ttf'
        target = args.output_dir / f'MapleCompactNFCN-{suffix}.ttf'
        print(f'{"Verify" if args.verify_only else "Build"}: {suffix}', flush=True)
        if not args.verify_only:
            build(source, target, suffix)
        report = verify(source, target, suffix)
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
