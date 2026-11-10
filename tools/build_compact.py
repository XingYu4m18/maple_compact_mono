#!/usr/bin/env python3
"""Build Maple Compact Mono packages using the upstream release asset layout."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import urllib.request
import zipfile

from compact_font import build_font, compact_name, require

ROOT = Path(__file__).resolve().parents[1]
ASSET_RE = re.compile(r'^MapleMono(?:Normal)?(?:NL)?-(?:TTF(?:-AutoHint)?|OTF|Variable|Woff2|(?:NF|CN|NF-CN)(?:-unhinted)?)\.zip$')
FONT_SUFFIXES = ('.ttf', '.otf', '.woff2')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def api_request(url):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'maple-compact-mono'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def release_catalog(version):
    pinned = json.loads((ROOT / 'upstream.release.json').read_text())
    if version.removeprefix('v') == pinned['tag_name'].removeprefix('v'):
        release = pinned
    else:
        require(version == 'latest' or re.fullmatch(r'v?\d+(?:\.\d+){1,2}', version), 'Use a stable version or latest')
        endpoint = 'latest' if version == 'latest' else 'tags/v' + version.removeprefix('v')
        release = api_request('https://api.github.com/repos/subframe7536/maple-font/releases/' + endpoint)
    tag = release['tag_name']
    require(re.fullmatch(r'v\d+(?:\.\d+){1,2}', tag), 'Unsupported upstream tag')
    require(not release['draft'] and not release['prerelease'], 'Select a stable release')
    packages = []
    for asset in release['assets']:
        name = asset['name']
        if not name.endswith('.zip'):
            continue
        require(ASSET_RE.fullmatch(name), f'New upstream package format requires adapter review: {name}')
        sha = asset.get('digest') or ''
        require(re.fullmatch(r'sha256:[0-9a-f]{64}', sha), f'No verified SHA256 for {name}')
        url = f'https://github.com/subframe7536/maple-font/releases/download/{tag}/{name}'
        require(asset['browser_download_url'] == url, 'Unexpected package URL')
        packages.append({'name': name, 'output': compact_name(name), 'url': url, 'sha256': sha[7:]})
    require(packages, 'No supported source packages')
    return {'tag': tag, 'source': release['html_url'], 'packages': packages}


def download(package, cache):
    path = cache / package['name']
    if path.exists() and digest(path) == package['sha256']:
        return path
    cache.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.part')
    for attempt in range(3):
        try:
            print('Download:', package['name'], flush=True)
            with urllib.request.urlopen(package['url'], timeout=180) as src, temporary.open('wb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            require(digest(temporary) == package['sha256'], 'Source archive SHA256 mismatch')
            temporary.replace(path)
            return path
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2)


def is_hinted(name):
    return name.endswith('-AutoHint.zip') or (any(x in name for x in ('-NF', '-CN')) and '-unhinted' not in name)


def zip_package(folder, output):
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(folder.rglob('*')):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(folder).as_posix(), (2026, 11, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_package(package, catalog, output, cache, styles=None):
    archive = download(package, cache)
    output.mkdir(parents=True, exist_ok=True)
    target_zip = output / package['output']
    hinted = is_hinted(package['name'])
    with tempfile.TemporaryDirectory(prefix='maple-compact-') as temp:
        temp = Path(temp)
        sources, result = temp / 'source', temp / 'package'
        sources.mkdir(); result.mkdir()
        with zipfile.ZipFile(archive) as z:
            entries = [n for n in z.namelist() if n.lower().endswith(FONT_SUFFIXES)]
            require(entries and len({Path(n).name for n in entries}) == len(entries), 'Missing or ambiguous source font entries')
            if styles:
                style_re = re.compile(r'-(?:' + '|'.join(re.escape(s) for s in styles) + r')\.(?:ttf|otf)(?:\.woff2)?$')
                entries = [n for n in entries if style_re.search(Path(n).name)]
                require(entries, 'No font matched --styles; variable packages should be built without this filter')
            for entry in entries:
                (sources / Path(entry).name).write_bytes(z.read(entry))
        reports = []
        for source in sorted(sources.iterdir()):
            target = result / compact_name(source.name)
            print('Build:', target.name, flush=True)
            report = build_font(source, target, hinted)
            report['sha256'] = digest(target)
            reports.append(report)
            print('Verified:', target.name, flush=True)
        shutil.copyfile(ROOT / 'OFL.txt', result / 'OFL.txt')
        shutil.copyfile(ROOT / 'THIRD_PARTY_NOTICES.md', result / 'THIRD_PARTY_NOTICES.md')
        shutil.copytree(ROOT / 'licenses', result / 'licenses')
        (result / 'README.txt').write_text(
            'Maple Compact Mono\n\n'
            'https://github.com/XingYu4m18/maple_compact_mono\n'
            f'Based on {catalog["source"]}\n'
            f'Package: {package["output"]}\n'
            'Install the font files using your operating system font installer.\n'
            'Latin width: 500; CJK width (CN packages): 1000. CJK outlines retain their size.\n'
            'Italic CJK may extend beyond character cells. Font rendering varies by application.\n'
            'See OFL.txt and THIRD_PARTY_NOTICES.md for licenses and attribution.\n'
        )
        manifest = {'upstream_tag': catalog['tag'], 'release_tag': catalog['release_tag'], 'source_package': package['name'],
                    'source_archive_sha256': package['sha256'], 'package': package['output'],
                    'font_count': len(reports), 'fonts': reports}
        (result / 'compact-build.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        zip_package(result, target_zip)
        sha_path = target_zip.with_suffix('.sha256')
        sha_path.write_text(digest(target_zip))
        reports_dir = output / 'reports'; reports_dir.mkdir(exist_ok=True)
        (reports_dir / (package['output'] + '.json')).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        print(f'Package ready: {target_zip.name} ({len(reports)} fonts)', flush=True)
    return target_zip


def release_notes(catalog, repo='XingYu4m18/maple_compact_mono'):
    tag = catalog['release_tag']
    lines = [f'# Maple Compact Mono {tag}', '',
             f'基于 [Maple Mono {catalog["tag"]}]({catalog["source"]})，英文宽度由 600 收至 500，中文占位由 1200 收至 1000，中文字形大小保持不变。', '',
             '覆盖上游全部字重、Ligature / NL / Normal / NormalNL，以及 TTF、OTF、WOFF2、Variable、NF、CN、NF-CN 各下载包。hinted 包重新生成 hinting，可变字体保留字重轴。', '',
             '本修订声明 WWS 字体家族，修复 Windows DirectWrite 将 Compact 误作样式描述而从家族名中移除的问题；同时修正展平字形的重叠标志位置，使字体可通过 Chromium 的 OpenType 检查。中文占位、字形轮廓和字体家族命名规则保持不变。发布前使用 Windows DirectWrite 与 Chromium 检查实际 NF-CN 包的全部 16 个字重／斜体。', '',
             '## 下载', '', '| 上游分类 | Compact 下载 | 校验 |', '| :--- | :--- | :--- |']
    for p in catalog['packages']:
        base = f'https://github.com/{repo}/releases/download/{tag}/'
        lines.append(f'| `{p["name"]}` | [{p["output"]}]({base}{p["output"]}) | [SHA256]({base}{p["output"][:-4]}.sha256) |')
    lines += ['', '推荐中文编程环境选择 **MapleCompactMono-NF-CN-unhinted.zip**。只选择一套造型和 hinting 版本安装，避免同名字体互相覆盖。', '',
              '每包包含许可证、来源声明和逐字体构建验证报告。中文斜体可能伸出字符格；收窄英文会改变原有字形比例。', '',
              '字体遵循 SIL Open Font License 1.1。安装及新版构建方法见仓库 README。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream-version', default='7.9', help='Stable upstream version, or latest')
    parser.add_argument('--release-tag', help='Output release tag: upstream tag, optionally followed by -compact.N')
    parser.add_argument('--asset', help='One upstream or Compact .zip asset name')
    parser.add_argument('--all', action='store_true', help='Build every package in the upstream release')
    parser.add_argument('--list', action='store_true', help='List all supported packages without downloading fonts')
    parser.add_argument('--catalog-only', action='store_true', help='Write catalog, matrix and release notes without building fonts')
    parser.add_argument('--styles', nargs='+', help='Optional static style filter for a smoke test, e.g. Regular Italic')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--cache-dir', type=Path, default=ROOT / '.cache' / 'release')
    args = parser.parse_args()
    require(not (args.all and args.asset), 'Select --all or --asset')
    catalog = release_catalog(args.upstream_version)
    release_tag = args.release_tag or catalog['tag']
    require(re.fullmatch(re.escape(catalog['tag']) + r'(?:-compact\.[1-9]\d*)?', release_tag),
            'Release tag must match the upstream tag, optionally followed by -compact.N')
    catalog['release_tag'] = release_tag
    if args.list:
        print('\n'.join(p['output'] for p in catalog['packages']))
        return
    output = args.output_dir or ROOT / 'dist' / release_tag
    output.mkdir(parents=True, exist_ok=True)
    (output / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    (output / 'matrix.json').write_text(json.dumps({'asset': [p['name'] for p in catalog['packages']]}))
    (output / 'release-notes.md').write_text(release_notes(catalog, os.environ.get('GITHUB_REPOSITORY', 'XingYu4m18/maple_compact_mono')))
    if args.catalog_only:
        print(f'{catalog["tag"]}: {len(catalog["packages"])} packages')
        return
    wanted = args.asset.replace('MapleCompactMono', 'MapleMono') if args.asset else 'MapleMono-NF-CN-unhinted.zip'
    packages = catalog['packages'] if args.all else [p for p in catalog['packages'] if p['name'] == wanted]
    require(packages, 'Package not found; use --list')
    for package in packages:
        build_package(package, catalog, output, args.cache_dir, args.styles)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        raise SystemExit(f'Error: {error}') from error
