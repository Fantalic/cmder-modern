"""Glyph transplant surgery: copy well-designed glyph outlines from
OFL-licensed Noto fonts into the vendored CaskaydiaCove NF, so ConEmu
renders those codepoints with the *vendored* monospace advance (no GDI
fallback chain, no advance drift in fixed-cell rendering).

Three passes:
  1. 2B00 suite arrows from Noto Sans Symbols 2 (kept from the first round;
     advances normalized to the font's cell width, missing mirrors built).
  2. Common narrow symbols from Noto Sans Symbols 2 that Caskaydia lacks
     (boxed squares, checks, stars, command/option keys).
  3. Noto Emoji (monochrome, OFL) merge: every single-codepoint emoji the
     donor covers becomes a real glyph of the main font. Advance follows the
     Unicode 16 East Asian Width class - Wide/Fullwidth get 2 cells (2400
     units), everything else 1 cell (1200) - matching wcwidth/go-runewidth
     and the patched ConEmu cell allocator. This removes the GDI font-linking
     hop (BMP only, unreliable for non-BMP) and fixes width drift.

Placement rule: every transplanted glyph is centred on the line box
(ascender 1900 / descender -480 -> centre 710), the house style of the
existing Caskaydia symbols, and shrunk to fit its advance when needed.

License: Noto glyphs are OFL 1.1 - the vendored font folder ships
NotoSansSymbols-OFL.txt and NotoEmoji-OFL.txt as required attribution. The
resulting TTFs are derivative works distributed under the same terms (OFL).

Run: python scripts/font_surgery.py
"""
import os
import re

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.misc.transform import Transform
from fontTools.ttLib import TTFont

DEST = {
    "Regular": r"E:\_tools\cmder_fork\vendor\fonts\CaskaydiaCoveNerdFont-Regular.ttf",
    "Bold":    r"E:\_tools\cmder_fork\vendor\fonts\CaskaydiaCoveNerdFont-Bold.ttf",
}
SYMBOLS2 = r"E:\_tools\cmder_fork\.ai\fonts-donor\Symbols2\NotoSansSymbols2\full\ttf\NotoSansSymbols2-Regular.ttf"
EMOJI = r"E:\_tools\cmder_fork\.ai\fonts-donor\Emoji\NotoEmoji-Variable.ttf"
EAW = r"E:\_tools\cmder_fork\.ai\fonts-donor\EastAsianWidth-16.0.0.txt"

CELL = 1200          # monospace advance of the destination font
WIDE = 2 * CELL      # advance for East Asian Wide/Fullwidth characters
LINE_CENTER = 710    # (hhea.ascent 1900 + descent -480) / 2
MAX_INK_FRACTION = 0.92

# Pass 1: codepoint -> donor codepoint (None = own donor cp); mirrors from 2B0C/2B0A
ARROWS = [
    (0x2B00, 0x2B00), (0x2B02, 0x2B02), (0x2B04, 0x2B04), (0x2B06, 0x2B06),
    (0x2B08, 0x2B08), (0x2B0A, 0x2B0A), (0x2B0C, 0x2B0C),
    (0x2B0E, 0x2B0C), (0x2B10, 0x2B0A),
]

# Pass 2: common one-cell symbols missing from Caskaydia
NARROW_SYMBOLS = [0x25A3, 0x2B1D, 0x2714, 0x2717, 0x2718, 0x2605, 0x2606, 0x2318, 0x2325]

# Pass 3: format/control codepoints that must never get a visible glyph
EMOJI_SKIP = {0x0000, 0x000D, 0x200D, 0x20E3, 0xFE0E, 0xFE0F}


def donor_cmap(donor):
    d = {}
    for st in donor["cmap"].tables:
        if hasattr(st, "cmap"):
            for cp, name in st.cmap.items():
                d.setdefault(cp, name)
    return d


def dest_cmap(dest):
    d = {}
    for st in dest["cmap"].tables:
        if hasattr(st, "cmap"):
            for cp, name in st.cmap.items():
                d.setdefault(cp, name)
    return d


def wide_codepoints(path):
    """Unicode 16 W/F set from EastAsianWidth.txt."""
    out = set()
    rx = re.compile(r"^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*;\s*([A-Z]+)")
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = rx.match(line)
            if not m:
                continue
            first = int(m.group(1), 16)
            last = int(m.group(2), 16) if m.group(2) else first
            if m.group(3) in ("W", "F"):
                out.update(range(first, last + 1))
    return out


def cmap_add(dest, cp, name):
    """Add/replace cp in the Unicode cmap subtables (format 4 = BMP only)."""
    for st in dest["cmap"].tables:
        if not hasattr(st, "cmap"):
            continue
        if st.format == 4:
            if cp <= 0xFFFF:
                st.cmap[cp] = name
        elif st.format in (12, 13):
            st.cmap[cp] = name


def remove_glyph(dest, name, cp):
    glyf = dest["glyf"]
    names = dest.getGlyphOrder()
    if name in glyf.keys():
        del glyf[name]
    if name in names:
        names.remove(name)
    if name in dest["hmtx"].metrics:
        del dest["hmtx"].metrics[name]
    for st in dest["cmap"].tables:
        if hasattr(st, "cmap") and st.cmap.get(cp) == name:
            del st.cmap[cp]


def add_fitted(dest, donor, donor_gs, src_name, new_name, advance):
    """Copy a glyph, scale to fit this advance's cell, centre on the line box."""
    upm_scale = dest["head"].unitsPerEm / donor["head"].unitsPerEm

    # decompose first: BoundsPen cannot traverse composite references
    probe = DecomposingRecordingPen(donor_gs)
    donor_gs[src_name].draw(TransformPen(probe, Transform(upm_scale, 0, 0, upm_scale, 0, 0)))
    bounds_pen = BoundsPen(None)
    probe.replay(bounds_pen)
    if not bounds_pen.bounds:
        return None  # whitespace or empty outline - nothing to draw
    x_min, y_min, x_max, y_max = bounds_pen.bounds

    scale = upm_scale
    width = x_max - x_min
    height = y_max - y_min
    limits = []
    if width > 0:
        limits.append(advance * MAX_INK_FRACTION / width)
    if height > 0:
        limits.append((dest["hhea"].ascent - dest["hhea"].descent) * MAX_INK_FRACTION / height)
    shrink = min(limits) if limits else 1.0
    shrink = min(1.0, shrink)
    if shrink < 1.0:
        scale *= shrink

    # bounds grow linearly with the uniform scale around the glyph origin
    cx = (x_min + x_max) / 2.0 * shrink
    cy = (y_min + y_max) / 2.0 * shrink
    dx = advance / 2.0 - cx
    dy = LINE_CENTER - cy
    xform = Transform(scale, 0, 0, scale, dx, dy)

    recording = DecomposingRecordingPen(donor_gs)
    donor_gs[src_name].draw(TransformPen(recording, xform))
    pen = TTGlyphPen(None)
    recording.replay(pen)
    glyph = pen.glyph()
    if not glyph.numberOfContours:
        return None

    names = dest.getGlyphOrder()
    dest["glyf"][new_name] = glyph
    if new_name not in names:
        names.append(new_name)
    lsb = int(round(x_min * shrink + dx))
    dest["hmtx"][new_name] = (advance, lsb)
    return lsb


def pass_arrows(dest, donor):
    """Original 2B00 suite transplant (kept: verified rendering)."""
    cc_upm = dest["head"].unitsPerEm
    dn_upm = donor["head"].unitsPerEm
    scale = cc_upm / dn_upm
    ref_adv = dest["hmtx"]["uniE0B0"][0] if "uniE0B0" in dest["hmtx"].metrics \
        else dest["hmtx"]["space"][0]

    glyf = dest["glyf"]
    names = dest.getGlyphOrder()
    hmtx = dest["hmtx"]
    glyphset = donor.getGlyphSet()
    added = []
    for cp, src_cp in ARROWS:
        src_name = None
        for st in donor["cmap"].tables:
            if hasattr(st, "cmap") and src_cp in st.cmap:
                src_name = st.cmap[src_cp]
                break
        if not src_name:
            print("skip U+%04X: donor missing" % cp)
            continue
        mirrored = src_cp != cp
        new_name = "cmdrMod" + ("-mirror" if mirrored else "") + "-%04X" % cp
        remove_glyph(dest, new_name, cp)

        w_scaled = donor["hmtx"][src_name][0] * scale
        recording = DecomposingRecordingPen(glyphset)
        if mirrored:
            xf = Transform(-scale, 0, 0, scale, w_scaled, 0)
        else:
            xf = Transform(scale, 0, 0, scale, 0, 0)
        glyphset[src_name].draw(TransformPen(recording, xf))

        pen = TTGlyphPen(None)
        recording.replay(pen)
        g = pen.glyph()
        glyf[new_name] = g
        if new_name not in names:
            names.append(new_name)
        hmtx[new_name] = (ref_adv, 0)
        cmap_add(dest, cp, new_name)
        added.append(cp)
    return added


def pass_narrow_symbols(dest, donor):
    """Common one-cell symbols, fitted and centred like native Caskaydia icons."""
    donor_gs = donor.getGlyphSet()
    d_cmap = donor_cmap(donor)
    added, missing = [], []
    for cp in NARROW_SYMBOLS:
        src_name = d_cmap.get(cp)
        if not src_name:
            missing.append(cp)
            continue
        new_name = "cmdrSym-%04X" % cp
        remove_glyph(dest, new_name, cp)
        if add_fitted(dest, donor, donor_gs, src_name, new_name, CELL) is not None:
            cmap_add(dest, cp, new_name)
            added.append(cp)
        else:
            missing.append(cp)
    return added, missing


def pass_emoji(dest, donor, wide, skip):
    """Merge every single-codepoint emoji, advance driven by EAW class."""
    donor_gs = donor.getGlyphSet()
    d_cmap = donor_cmap(donor)
    have = dest_cmap(dest)
    cache = {}       # donor glyph name -> destination glyph name (aliases)
    added = replaced = kept = 0
    for cp in sorted(d_cmap):
        if cp < 0x20 or 0x7F <= cp < 0xA0 or cp in skip:
            continue
        src_name = d_cmap[cp]
        advance = WIDE if cp in wide else CELL
        existing = have.get(cp)
        if existing:
            # keep existing text designs, but a Wide char needs a 2-cell glyph
            if not (cp in wide and dest["hmtx"][existing][0] < WIDE):
                kept += 1
                continue
        if src_name in cache:
            cmap_add(dest, cp, cache[src_name])
            added += 1
            continue
        new_name = "cmdrEmoji-%04X" % cp if cp <= 0xFFFF else "cmdrEmoji-%06X" % cp
        remove_glyph(dest, new_name, cp)
        if add_fitted(dest, donor, donor_gs, src_name, new_name, advance) is None:
            continue
        cmap_add(dest, cp, new_name)
        cache[src_name] = new_name
        if existing:
            replaced += 1
        else:
            added += 1
    return added, replaced, kept


def main():
    symbols = TTFont(SYMBOLS2)
    emoji = TTFont(EMOJI)
    wide = wide_codepoints(EAW)
    print("Unicode wide set: %d codepoints" % len(wide))

    for weight, path in DEST.items():
        dest = TTFont(path)
        before = len(dest.getGlyphOrder())
        arrows = pass_arrows(dest, symbols)
        narrow, missing = pass_narrow_symbols(dest, symbols)
        added, replaced, kept = pass_emoji(dest, emoji, wide, EMOJI_SKIP)
        dest.save(path)
        size = os.path.getsize(path)
        print("%s: glyphs %d -> %d | arrows %d | symbols %d | emoji +%d (wide-replaced %d, kept %d) | %.2f MB"
              % (weight, before, len(dest.getGlyphOrder()), len(arrows), len(narrow),
                 added, replaced, kept, size / 1048576.0))
        if missing:
            print("  donor missing / empty:", ", ".join("U+%04X" % c for c in missing))

    # verification pass on the Regular weight
    print("\nverify:")
    dest = TTFont(DEST["Regular"])
    cm = dest_cmap(dest)
    checks = [0x2705, 0x1F4CC, 0x1F600, 0x25A3, 0x2B1D, 0x2714, 0x2713, 0x2764,
              0x2B1B, 0x26A1, 0x2B50, 0x2318, 0x2325, 0x2717, 0x2605,
              0x1F1E6, 0x200D, 0xFE0F]
    for cp in checks:
        name = cm.get(cp)
        if not name:
            print("  U+%04X: (no glyph)" % cp)
            continue
        adv = dest["hmtx"][name][0]
        g = dest["glyf"][name]
        print("  U+%04X -> %-20s adv=%4d bbox=(%d,%d,%d,%d)"
              % (cp, name, adv, g.xMin, g.yMin, g.xMax, g.yMax))


if __name__ == "__main__":
    main()
