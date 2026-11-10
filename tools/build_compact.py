#!/usr/bin/env python3
"""Build or verify Compact500 from pinned or explicitly selected Maple Mono releases."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import zipfile

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('mono', 'nf', 'cn', 'nf-cn')
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


def variant_config(variant, no_ligatures=False):
    parts = [] if variant == 'mono' else variant.upper().split('-')
    upstream_prefix = 'MapleMono' + ('NL' if no_ligatures else '') + ''.join('-' + x for x in parts)
    labels = (['Mono'] if variant == 'mono' else []) + (['NL'] if no_ligatures else []) + parts
    return {
        'key': ('nl-' if no_ligatures else '') + variant,
        'family': 'Maple Compact ' + ' '.join(labels),
        'prefix': 'MapleCompact' + ''.join(labels),
        'upstream_prefix': upstream_prefix,
        'asset': upstream_prefix + ('-TTF' if variant == 'mono' else '') + '.zip',
        'folder': 'maple_compact_' + '_'.join(x.lower() for x in labels),
    }


def pinned_variant(pinned, config):
    asset = pinned['variants'][config['key']]
    return {'upstream': pinned['upstream'], 'version': pinned['version'],
            'release_url': pinned['release_url'], 'variant': config['key'],
            'asset_url': asset['asset_url'], 'archive_sha256': asset['archive_sha256'],
            'files': dict(asset['files'])}


def resolve_release(version, pinned, config):
    if version is None:
        return pinned_variant(pinned, config)
    check(version == 'latest' or re.fullmatch(r'v?\d+(?:\.\d+){1,2}', version),
          'Use latest or a stable version such as 7.9; prereleases are not selected')
    endpoint = 'latest' if version == 'latest' else 'tags/v' + version.removeprefix('v')
    request = urllib.request.Request(
        'https://api.github.com/repos/subframe7536/maple-font/releases/' + endpoint,
        headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'maple-compact-mono'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    tag = release['tag_name']
    check(re.fullmatch(r'v\d+(?:\.\d+){1,2}', tag), 'Unsupported release tag format')
    check(not release['prerelease'] and not release['draft'], 'Expected a stable, published release')
    assets = [a for a in release['assets'] if a['name'] == config['asset']]
    check(len(assets) == 1, f'Release has no unique {config["asset"]} asset; update the adapter first')
    asset = assets[0]
    digest = asset.get('digest') or ''
    check(re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'Release asset lacks a GitHub SHA256 digest')
    expected_url = f'https://github.com/subframe7536/maple-font/releases/download/{tag}/{config["asset"]}'
    check(asset['browser_download_url'] == expected_url, 'Unexpected upstream asset URL')
    lock = {
        'upstream': pinned['upstream'], 'version': tag.removeprefix('v'),
        'release_url': release['html_url'], 'asset_url': expected_url,
        'archive_sha256': digest.removeprefix('sha256:'),
        'variant': config['key'],
        'files': {f'{config["upstream_prefix"]}-{style}.ttf': None for style in STYLES},
    }
    # Known-release hashes must also match the committed manifest.
    if lock['version'] == pinned['version']:
        known = pinned_variant(pinned, config)
        check(lock['archive_sha256'] == known['archive_sha256'], 'Known upstream release digest changed')
        lock['files'] = known['files']
    return lock


def get_sources(source_dir, lock):
    if source_dir is None or any(v is None for v in lock['files'].values()):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        archive = cache / f'{lock["variant"]}-v{lock["version"]}.zip'
        if not archive.exists():
            temporary = archive.with_suffix('.part')
            print(f'Downloading upstream release {lock["version"]}...', flush=True)
            with urllib.request.urlopen(lock['asset_url'], timeout=60) as src, temporary.open('wb') as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b''):
                    dst.write(chunk)
            check(sha256(temporary) == lock['archive_sha256'], 'Archive SHA256 mismatch')
            temporary.replace(archive)
        check(sha256(archive) == lock['archive_sha256'], 'Cached archive SHA256 mismatch')
        extracted = cache / f'upstream-{lock["version"]}-{lock["variant"]}'
        extracted.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for name in lock['files']:
                entries = [n for n in z.namelist() if Path(n).name == name]
                check(len(entries) == 1, f'Missing or ambiguous archive entry: {name}')
                (extracted / name).write_bytes(z.read(entries[0]))
                actual = sha256(extracted / name)
                expected = lock['files'][name]
                check(expected is None or expected == actual, f'Archive font hash mismatch: {name}')
                lock['files'][name] = actual
        if source_dir is None:
            source_dir = extracted
    for name, expected in lock['files'].items():
        path = source_dir / name
        check(path.is_file(), f'Missing upstream font: {path}')
        check(sha256(path) == expected, f'Upstream font SHA256 mismatch: {name}')
    return source_dir


def preflight(source):
    with TTFont(source) as font:
        check('glyf' in font and 'GSUB' in font, f'Unsupported font tables: {source.name}')
        check(not any(t in font for t in ('fvar', 'GPOS', 'kern', 'COLR', 'SVG ')),
              f'Unsupported variable, positioning or color tables: {source.name}')
        check(font['head'].unitsPerEm == 1000, f'Unsupported em size: {source.name}')
        check('SIL Open Font License' in (font['name'].getDebugName(13) or ''),
              f'Upstream license metadata changed; review before adapting: {source.name}')
        check(set(w for w, _ in font['hmtx'].metrics.values()) <= {0, 600, 1200},
              f'Unsupported advance widths: {source.name}')


def build(source, target, suffix, version, config):
    family = config['family']
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
        font['hhea'].advanceWidthMax = max(w for w, _ in metrics.values())
        font['head'].modified = MODIFIED
        style = STYLES[suffix]
        names = {
            1: family, 2: style, 3: f'{family} {version} Compact500 {suffix}',
            4: family + ('' if style == 'Regular' else ' ' + style),
            5: f'Version {version}; local Compact500 derivative',
            6: f'{config["prefix"]}-{suffix}', 16: family, 17: style,
            18: family + ' ' + style,
            10: f'Unofficial Compact500 derivative of {config["upstream_prefix"]} {version}. Narrow glyphs scaled horizontally; full-width outlines unscaled.',
        }
        # Preserve copyright and license records; replace family identification.
        font['name'].names = [n for n in font['name'].names if n.nameID not in names]
        for nameid, value in names.items():
            font['name'].setName(value, nameid, 3, 1, 0x409)
            font['name'].setName(value, nameid, 1, 0, 0)
        target.parent.mkdir(parents=True, exist_ok=True)
        font.save(target)


def verify(source, target, suffix, config):
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
        check(font['name'].getDebugName(16) == config['family'], 'Wrong family name')
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
    parser.add_argument('--variant', choices=(*VARIANTS, 'all'), default='nf-cn', help='Base packaging variant; all builds mono, nf, cn and nf-cn')
    parser.add_argument('--no-ligatures', action='store_true', help='Use official NL source packages; do not strip features from ligature packages')
    parser.add_argument('--upstream-version', help='Explicit stable version (e.g. 7.9) or latest; default uses upstream.lock.json')
    parser.add_argument('--resolve-only', action='store_true', help='Resolve and print the release manifest without downloading or building fonts')
    parser.add_argument('--source-dir', type=Path, help='Verified upstream TTF directory; otherwise download the pinned release')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--styles', nargs='+', choices=STYLES, default=list(STYLES))
    parser.add_argument('--verify-only', action='store_true', help='Verify existing output without rebuilding')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    pinned = json.loads((ROOT / 'upstream.lock.json').read_text())
    if args.variant == 'all' and args.report:
        parser.error('--report is for a single variant; all writes per-variant reports')
    variants = VARIANTS if args.variant == 'all' else (args.variant,)
    for variant in variants:
        config = variant_config(variant, args.no_ligatures)
        lock = resolve_release(args.upstream_version, pinned, config)
        if args.resolve_only:
            print(json.dumps(lock, ensure_ascii=False, indent=2))
            continue
        print(f'Upstream: {lock["version"]}, variant: {config["key"]}', flush=True)
        base = ROOT / 'dist' / ('upstream-' + lock['version']) if args.upstream_version else ROOT
        output = args.output_dir or (base / 'fonts' / config['folder'])
        if args.variant == 'all' and args.output_dir:
            output = output / config['folder']
        report_path = args.report or (base / 'reports' / ('validation.json' if config['key'] == 'nf-cn' else config['key'] + '.json'))
        sources = get_sources(args.source_dir, lock)
        # Check every selected style before writing any output fonts in this variant.
        for suffix in args.styles:
            preflight(sources / f'{config["upstream_prefix"]}-{suffix}.ttf')
        reports = []
        for suffix in args.styles:
            source = sources / f'{config["upstream_prefix"]}-{suffix}.ttf'
            target = output / f'{config["prefix"]}-{suffix}.ttf'
            print(f'{"Verify" if args.verify_only else "Build"}: {suffix}', flush=True)
            if not args.verify_only:
                build(source, target, suffix, lock['version'], config)
            report = verify(source, target, suffix, config)
            report['upstream_version'] = lock['version']
            report['variant'] = config['key']
            reports.append(report)
            print(json.dumps(report, ensure_ascii=False), flush=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n')
        resolved = report_path.with_name(report_path.stem + '.upstream.json')
        resolved.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        raise SystemExit(f'Error: {error}') from error
