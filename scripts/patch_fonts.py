"""Patch vendored CaskaydiaCove NF: remove glyphs whose NF-patch design renders
badly under ConEmu's monospace cell math, so ConEmu's FontName2 fallback (and
the GDI font-link fallback) picks a well-designed symbol font instead.

The strip list is deliberately small and evidenced; add entries only after a
coverage + render comparison. Run after every vendor/font refresh:

    python scripts/patch_fonts.py
"""
import os
import sys

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "vendor", "fonts")
TARGET = "CaskaydiaCoveNerdFont"

# U+25A3 (WHITE SQUARE CONTAINING SMALL BLACK SQUARE; opencode message footer
# badge) and U+2B1D (BLACK MEDIUM SMALL SQUARE; opencode status spinner inactive
# dot). CaskaydiaCove's NF-patch designs for these two sit off-grid under
# ConEmu; Segoe UI Symbol draws them correctly.
STRIP = [0x25A3, 0x2B1D]


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
