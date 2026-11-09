"""Patch vendored CaskaydiaCove NF: remove glyphs whose design renders badly
under ConEmu's monospace cell math.

Nothing is stripped today. The vendored fonts now carry on-grid Noto designs
for U+25A3 and U+2B1D (see scripts/font_surgery.py), so removing them would
bring back the GDI fallback drift they used to cause. The strip list stays as
the single place for future evictions after a coverage + render comparison.

    python scripts/patch_fonts.py
"""
import os
import sys

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "vendor", "fonts")
TARGET = "CaskaydiaCoveNerdFont"

# Glyphs to remove from the vendored font. U+25A3 (message footer badge) and
# U+2B1D (status spinner dot) were evicted while the font lacked on-grid
# designs for them; scripts/font_surgery.py now supplies both.
STRIP = []


def strip_glyph(font_path, strip):
    font = TTFont(font_path)
    removed = []

    for table in font["cmap"].tables:
        if not hasattr(table, "cmap"):
            continue
        for code in strip:
            if code in table.cmap:
                del table.cmap[code]
                removed.append("fmt%d:U+%04X" % (table.format, code))

    if removed:
        font.save(font_path)
    return removed


def main():
    failed = False
    for weight in ("Regular", "Bold", "Italic", "BoldItalic"):
        path = os.path.join(FONT_DIR, "%s-%s.ttf" % (TARGET, weight))
        if not os.path.isfile(path):
            print("missing: %s" % path)
            failed = True
            continue
        removed = strip_glyph(path, STRIP)
        print("%s -> %s" % (os.path.basename(path), ", ".join(removed) or "nothing to remove"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
