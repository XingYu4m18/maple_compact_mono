"""Geometry and verification for Maple Compact Mono release builds."""
from io import BytesIO
from math import isclose
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.varLib.instancer import instantiateVariableFont

SCALE = 5 / 6
WWS_STYLES = {weight + slope for weight in ('Thin', 'ExtraLight', 'Light', 'Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold')
              for slope in ('', ' Italic')} | {'Italic'}


def declare_wws_family(font):
    """These Maple presets are separate families, varying only by weight/slope.

    Without bit 8, Windows can reinterpret 'Compact' as a width qualifier.
    ID 16/17 (falling back to 1/2) already express a WWS-only family; do not
    add conflicting WWS names 21/22. Reject a changed upstream family model.
    """
    names, os2 = font['name'], font['OS/2']
    require(os2.version >= 4, 'WWS declaration requires OS/2 version 4 or newer')
    require(os2.usWidthClass == 5, 'Review changed upstream width classification')
    require(not any(n.nameID in (21, 22) for n in names.names), 'Review upstream WWS names before changing the family model')
    require(names.getBestSubFamilyName() in WWS_STYLES, 'Review non-WWS upstream subfamily')
    os2.fsSelection |= 1 << 8


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compact_name(value):
    return value.replace('Maple Mono', 'Maple Compact Mono').replace('MapleMono', 'MapleCompactMono')


def rename(font):
    for record in font['name'].names:
        if record.nameID in (0, 7, 8, 9, 13, 14):
            continue
        value = record.toUnicode()
        updated = compact_name(value)
        if updated != value:
            record.string = updated.encode(record.getEncoding(), errors='strict')
    if 'CFF ' in font:
        cff = font['CFF '].cff
        cff.fontNames = [compact_name(n) for n in cff.fontNames]
        top = cff.topDictIndex[0]
        for attr in ('FamilyName', 'FullName', 'FontName'):
            if hasattr(top, attr):
                setattr(top, attr, compact_name(getattr(top, attr)))


def preflight(font):
    require(font['head'].unitsPerEm == 1000, 'Expected 1000 units per em')
    require('SIL Open Font License' in (font['name'].getDebugName(13) or ''), 'Review changed upstream license metadata')
    require(not any(t in font for t in ('GPOS', 'kern', 'GDEF', 'BASE', 'MATH', 'COLR', 'SVG ', 'MVAR', 'VARC')),
            'Unsupported positioning/color/variation table; update the adapter before building')
    require('glyf' in font or 'CFF ' in font, 'Expected TrueType or static CFF outlines')
    require('GSUB' in font, 'Expected upstream OpenType substitution rules')
    require(set(w for w, _ in font['hmtx'].metrics.values()) <= {0, 600, 1200}, 'Unsupported source widths')
    if 'fvar' in font:
        require('glyf' in font and set(w for w, _ in font['hmtx'].metrics.values()) <= {0, 600},
                'Only Latin variable fonts are currently supported')
        require([a.axisTag for a in font['fvar'].axes] == ['wght'], 'Unsupported variable axes')


def remove_hints(font):
    for tag in ('fpgm', 'prep', 'cvt ', 'hdmx', 'LTSH', 'VDMX', 'DSIG'):
        if tag in font:
            del font[tag]
    if 'glyf' in font:
        font['maxp'].maxZones = 1


def simple_flags(flags, overlap=False):
    """OVERLAP_SIMPLE belongs on the first point, never on child start points."""
    require(not any(f & 0x80 for f in flags), 'Unsupported reserved TrueType point flag')
    overlap = overlap or any(f & 0x40 for f in flags)
    result = bytearray(f & ~0x40 for f in flags)
    if result and overlap:
        result[0] |= 0x40
    return result


def normalize_simple_overlaps(font):
    """Repair old compact binaries in the controlled Windows comparison only."""
    for glyph in font['glyf'].glyphs.values():
        glyph.expand(font['glyf'])
        if glyph.numberOfContours > 0:
            glyph.flags = simple_flags(glyph.flags)
    font['maxp'].maxZones = max(1, font['maxp'].maxZones)


def static_glyf(font):
    glyf = font['glyf']
    result, metrics = {}, {}
    for name in font.getGlyphOrder():
        width, _ = font['hmtx'][name]
        coords, ends, flags = glyf[name].getCoordinates(glyf)
        coords = [(x - 100, y) if width == 1200 else (round(x * SCALE), y) for x, y in coords]
        glyph = Glyph()
        glyph.numberOfContours = len(ends)
        lsb = 0
        if ends:
            glyph.coordinates = GlyphCoordinates(coords)
            glyph.endPtsOfContours = list(ends)
            compound_overlap = glyf[name].isComposite() and any(c.flags & 0x400 for c in glyf[name].components)
            glyph.flags = simple_flags(flags, compound_overlap)
            glyph.program = Program()
            glyph.program.fromBytecode(b'')
            glyph.recalcBounds(glyf)
            lsb = glyph.xMin
        result[name] = glyph
        metrics[name] = (1000 if width == 1200 else 500 if width else 0, lsb)
    glyf.glyphs = result
    font['hmtx'].metrics = metrics


def variable_glyf(font):
    # Retain the point topology and composite structure required by gvar.
    for name in font.getGlyphOrder():
        glyph = font['glyf'][name]
        if glyph.isComposite():
            for component in glyph.components:
                _, matrix = component.getComponentInfo()
                require(matrix[:4] == (1, 0, 0, 1), 'Unsupported variable composite transform')
                if hasattr(component, 'x'):
                    component.x = round(component.x * SCALE)
        elif hasattr(glyph, 'coordinates'):
            glyph.coordinates = GlyphCoordinates([(round(x * SCALE), y) for x, y in glyph.coordinates])
        if hasattr(glyph, 'program'):
            glyph.program.fromBytecode(b'')
    if 'gvar' in font:
        for variations in font['gvar'].variations.values():
            for variation in variations:
                variation.coordinates = [None if p is None else (round(p[0] * SCALE), p[1]) for p in variation.coordinates]
    if 'HVAR' in font:
        for data in font['HVAR'].table.VarStore.VarData:
            data.Item = [[round(value * SCALE) for value in item] for item in data.Item]
            data.calculateNumShorts()
    font['hmtx'].metrics = {n: (round(w * SCALE), round(lsb * SCALE)) for n, (w, lsb) in font['hmtx'].metrics.items()}


def cff_outlines(font):
    top = font['CFF '].cff.topDictIndex[0]
    require(not hasattr(top, 'FDArray'), 'CID-keyed CFF needs a separate adapter')
    glyphset = font.getGlyphSet()
    charstrings = {}
    for name in font.getGlyphOrder():
        width, _ = font['hmtx'][name]
        require(width in (0, 600), 'CJK CFF not currently provided by upstream')
        pen = T2CharStringPen(round(width * SCALE), glyphset)
        glyphset[name].draw(TransformPen(pen, (SCALE, 0, 0, 1, 0, 0)))
        charstrings[name] = pen.getCharString(private=top.Private, globalSubrs=font['CFF '].cff.GlobalSubrs, optimize=False)
    top.Private.defaultWidthX = 0
    top.Private.nominalWidthX = 0
    for name, charstring in charstrings.items():
        top.CharStrings[name] = charstring
    font['hmtx'].metrics = {n: (round(w * SCALE), round(lsb * SCALE)) for n, (w, lsb) in font['hmtx'].metrics.items()}


def raw_save(font):
    stream = BytesIO()
    font.save(stream)
    return stream.getvalue()


def build_font(source, target, hinted=False):
    with TTFont(source, recalcTimestamp=False) as font:
        preflight(font)
        variable = 'fvar' in font
        flavor = font.flavor
        if variable:
            variable_glyf(font)
        elif 'glyf' in font:
            static_glyf(font)
        else:
            cff_outlines(font)
        remove_hints(font)
        rename(font)
        declare_wws_family(font)
        font['OS/2'].xAvgCharWidth = 500
        font['post'].isFixedPitch = 1
        font['hhea'].advanceWidthMax = max(w for w, _ in font['hmtx'].metrics.values())
        if hinted:
            require(not variable and 'glyf' in font and not flavor, 'Hinting only applies to static TrueType')
            from ttfautohint import ttfautohint
            data = ttfautohint(in_buffer=raw_save(font), no_info=True, default_script='latn', fallback_script='none',
                              windows_compatibility=True, epoch=0)
            target.write_bytes(data)
        else:
            target.write_bytes(raw_save(font))
    return verify_font(source, target, hinted)


def recording(glyphset, name):
    pen = RecordingPen()
    glyphset[name].draw(pen)
    return pen.value


def assert_recording(expected, actual, sx, tx, tolerance):
    require(len(expected) == len(actual), 'Outline command count changed')
    for (op1, pts1), (op2, pts2) in zip(expected, actual):
        require(op1 == op2 and len(pts1) == len(pts2), 'Outline structure changed')
        for p, q in zip(pts1, pts2):
            if p is None:
                require(q is None, 'Implied point changed')
            else:
                require(abs(p[0] * sx + tx - q[0]) <= tolerance and abs(p[1] - q[1]) <= tolerance,
                        'Outline geometry differs from the compact transform')


def verify_static(original, font, hinted):
    cmap = original.getBestCmap()
    outside, extent = 0, 0
    if 'glyf' in original:
        for name in original.getGlyphOrder():
            width, _ = original['hmtx'][name]
            expected = 1000 if width == 1200 else 500 if width else 0
            require(font['hmtx'][name][0] == expected, f'Wrong advance: {name}')
            a, ep, af = original['glyf'][name].getCoordinates(original['glyf'])
            b, eq, bf = font['glyf'][name].getCoordinates(font['glyf'])
            require(list(ep) == list(eq), f'Contour endpoints changed: {name}')
            wanted = [(x - 100, y) if width == 1200 else (round(x * SCALE), y) for x, y in a]
            require(list(b) == wanted, f'Unexpected outline transform: {name}')
            require([f & 1 for f in af] == [f & 1 for f in bf], f'On/off-curve point flags changed: {name}')
            require(not any(f & 0xC0 for f in bf[1:]) and (not bf or not bf[0] & 0x80),
                    f'Invalid serialized overlap/reserved flag: {name}')
        for cp in range(0x4E00, 0xA000):
            name = cmap.get(cp)
            if name:
                g = font['glyf'][name]
                if g.numberOfContours:
                    amount = max(0, -g.xMin, g.xMax - 1000)
                    outside += amount > 0
                    extent = max(extent, amount)
    else:
        a, b = original.getGlyphSet(), font.getGlyphSet()
        for name in original.getGlyphOrder():
            require(font['hmtx'][name][0] == round(original['hmtx'][name][0] * SCALE), f'Wrong CFF advance: {name}')
            assert_recording(recording(a, name), recording(b, name), SCALE, 0, 1.0)
    return {'han_overhang_count': outside, 'han_overhang_max_units': extent}


def verify_variable(original, font):
    require(original['fvar'].compile(original) == font['fvar'].compile(font), 'Variable axis/instance metadata changed')
    for weight in (100, 250, 400, 650, 800):
        left = instantiateVariableFont(original, {'wght': weight}, inplace=False)
        right = instantiateVariableFont(font, {'wght': weight}, inplace=False)
        # gvar/IUP rounding can differ by a small fraction after anisotropic scaling.
        for name in left.getGlyphOrder():
            require(right['hmtx'][name][0] == round(left['hmtx'][name][0] * SCALE), f'Variable advance mismatch: {name}')
            a, ends, _ = left['glyf'][name].getCoordinates(left['glyf'])
            b, ends2, _ = right['glyf'][name].getCoordinates(right['glyf'])
            require(list(ends) == list(ends2), 'Variable contour structure changed')
            require(len(a) == len(b) and all(abs(x * SCALE - u) <= 2 and abs(y - v) <= 1 for (x, y), (u, v) in zip(a, b)),
                    f'Variable outline mismatch at weight {weight}: {name}')
    return {'variable_weight_samples': [100, 250, 400, 650, 800]}


def verify_font(source, target, hinted=False):
    with TTFont(source) as original, TTFont(target, checkChecksums=2) as font:
        require(original.getBestCmap() == font.getBestCmap(), 'Unicode mappings changed')
        require(original.getGlyphOrder() == font.getGlyphOrder()[:len(original.getGlyphOrder())], 'Source glyph order changed')
        require(original['GSUB'].compile(original) == font['GSUB'].compile(font), 'Substitution rules changed')
        require(font['head'].unitsPerEm == 1000, 'em size changed')
        for table, attrs in [('hhea', ['ascent', 'descent', 'lineGap']),
                            ('OS/2', ['sTypoAscender', 'sTypoDescender', 'sTypoLineGap', 'usWinAscent', 'usWinDescent'])]:
            require(all(getattr(original[table], a) == getattr(font[table], a) for a in attrs), 'Vertical metrics changed')
        require(font['name'].getDebugName(1) == compact_name(original['name'].getDebugName(1)), 'Family name does not follow upstream')
        require(font['name'].getDebugName(0) == original['name'].getDebugName(0), 'Copyright changed')
        require(font['name'].getDebugName(13) == original['name'].getDebugName(13), 'License metadata changed')
        require(font['OS/2'].fsSelection == original['OS/2'].fsSelection | (1 << 8), 'WWS flag missing or other style flags changed')
        require(not any(n.nameID in (21, 22) for n in font['name'].names), 'Conflicting WWS names')
        renamed = {(n.nameID, n.platformID, n.platEncID, n.langID): n.toUnicode() for n in font['name'].names}
        for n in original['name'].names:
            expected = n.toUnicode() if n.nameID in (0, 7, 8, 9, 13, 14) else compact_name(n.toUnicode())
            require(renamed.get((n.nameID, n.platformID, n.platEncID, n.langID)) == expected,
                    f'Name record changed unexpectedly: {n.nameID}/{n.platformID}/{n.langID}')
        variable = 'fvar' in original
        require(('fvar' in font) == variable, 'Variable font became static')
        if hinted:
            require('fpgm' in font and 'prep' in font, 'Hinted package lacks regenerated instructions')
        else:
            require(not any(t in font for t in ('fpgm', 'prep', 'cvt ')), 'Outdated hinting retained')
        if 'glyf' in font:
            require(font['maxp'].maxZones in (1, 2), 'Invalid TrueType maxZones')
        detail = verify_variable(original, font) if variable else verify_static(original, font, hinted)
        return {'file': target.name, 'family': font['name'].getDebugName(1), 'glyphs': len(font.getGlyphOrder()),
                'variable': variable, 'hinted': hinted, 'wws_family_declared': True, 'all_name_records_verified': True,
                'all_outlines_verified': True, 'cmap_identical': True,
                'gsub_identical': True, 'vertical_metrics_identical': True, **detail}
