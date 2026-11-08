"""Icon-grid probe v2: prints every candidate icon wrapped in hard vertical
bars. The bars are drawn with a codepoint we treat as grid-anchor (│, U+2502,
which the vendored font renders correctly); every glyph row contains the icon
repeated 6x between bars. Any per-glyph advance error accumulates 6x and is
visible as ragged right edge against the closing bar. Blank/tofu icons show
as □-shaped hollows instantly.

Every group gets a distinct RGB foreground so rows don't blend; the ruler
column is per group colored for eyeballing.

Report only entries where the closing bar looks ragged or an icon shows a
hollow: that's the codepoint for the strip/transplant list.

Run:  python scripts\\show_glyphs.py
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

GROUPS = [
    ("opencode spinner (blocks)", (255, 96, 64), [0x2588, 0x2584, 0x2580, 0x2590, 0x258C, 0x25A0, 0x2B1D]),
    ("opencode spinners (diamonds)", (0, 255, 96), [0x2B25, 0x25C6, 0x2B29, 0x2B2A, 0xB7]),
    ("badge shapes", (255, 0, 255), [0x25A3, 0x25A1, 0x25A2]),
    ("tool-row icons", (0, 255, 255), [0x24, 0x2699, 0x2731, 0x25C8, 0x2190, 0x2192, 0x2713, 0x2717, 0x2502, 0x2726]),
    ("2B00 block suite", (255, 255, 0), [0x2B00, 0x2B02, 0x2B04, 0x2B06, 0x2B08, 0x2B0A, 0x2B0C, 0x2B0E, 0x2B10, 0x2B1A, 0x2B12, 0x2B14, 0x2B16, 0x2B18, 0x2B1A, 0x2B1C]),
    ("braille", (255, 255, 255), [0x280B, 0x2817, 0x2826, 0x2815, 0x2803, 0x2812, 0x2814, 0x2816, 0x2821, 0x2810, 0x2822, 0x2813]),
    ("box drawing", (0, 192, 255), [0x250C, 0x2500, 0x2510, 0x2514, 0x251C, 0x2524, 0x252C, 0x253C, 0x255D, 0x2554, 0x2550, 0x2551]),
    ("misc cli icons", (255, 128, 0), [0x2191, 0x2193, 0x21B3, 0x2691, 0x26A0, 0x2705, 0x274C, 0x2718, 0x23CE, 0x23FA, 0x23F5, 0x2714, 0x2B95, 0x21BB, 0x279C, 0x27A4]),
]

BAR = "\u2502"
RST = "\x1b[0m"


def fg(r, g, b):
    return "\x1b[38;2;%d;%d;%dm" % (r, g, b)


def main():
    print("icon-grid probe v2. lines: [bar] U+XXXX [bar] glyph*6 [bar]  <- ragged edge at final bar = advance off-grid")
    for title, rgb, cps in GROUPS:
        c = fg(*rgb)
        print("")
        print(c + "=== %s ===" % title + RST)
        for cp in cps:
            run = chr(cp) * 6
            lab = "U+%04X" % cp
            print(c + BAR + RST + " %-10s " % lab + c + BAR + RST + " " + c + run + RST + " " + c + BAR + RST)


if __name__ == "__main__":
    main()
