"""Icon-inventory probe: prints the full set of shape/spinner/icon codepoints
that modern TUIs (opencode,再度 any ANSI/VT app) emit, grouped so a human can
eyeball which glyph designs render off-grid in ConEmu.  Any offender becomes
an entry in scripts\\patch_fonts.py STRIP (the fork ships a "curated" font:
strip the bad designs, GDI font-linking then picks Windows' clean Segoe UI
Symbol designs - no engine changes needed).

Run inside a fork console:  python scripts\\show_glyphs.py
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

GROUPS = [
    ("opencode spinner (blocks style)", ["\u2588", "\u2584", "\u2580", "\u2590", "\u258c", "\u25a0", "\u2b1d"]),
    ("opencode spinner (diamonds style)", ["\u2b25", "\u25c6", "\u2b29", "\u2b2a", "\u00b7"]),
    ("message-badge shapes", ["\u25a3", "\u25a1", "\u25a2"]),
    ("tool-row icons", ["\u0024", "\u2699", "\u2731", "\u25c8", "\u2190", "\u2192", "\u2713", "\u2717", "\u2502", "\u2726", "\u2726"]),
    ("U+2B00 block suite (symbols for legacy computing)", [chr(c) for c in range(0x2b00, 0x2b1f, 2)] + ["\u2b1d"]),
    ("braille spinner set", ["\u280b", "\u2817", "\u2826", "\u2815", "\u2817", "\u2803", "\u2812", "\u2814", "\u2816", "\u2821", "\u2810", "\u2822", "\u2813", "\u2812", "\u2814", "\u2802"]),
    ("box drawing (borders/frames)", ["\u250c", "\u2500", "\u2510", "\u2514", "\u2534", "\u251c", "\u2524", "\u252c", "\u253c", "\u255d", "\u2554", "\u2550", "\u2551"]),
    ("arrows / misc from common CLIs", ["\u2190", "\u2192", "\u2191", "\u2193", "\u21b3", "\u2691", "\u26a0", "\u2705", "\u274c", "\u2713"]),
]

for title, chars in GROUPS:
    print("\u001b[36m== %s\u001b[0m" % title)
    line = "   "
    for ch in chars:
        cp = "U+%04X" % ord(ch)
        line += "%s %s   " % (ch, cp)
        if len(line) > 150:
            print(line)
            line = "   "
    if line.strip():
        print(line)
print("\nWhich designs look WRONG (inner shapes off-grid, clipped, squashed)?")
print("Report the U+XXXX names - each gets one line in scripts\\patch_fonts.py STRIP.")
