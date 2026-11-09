"""Measurement-optimized drift probe: prints ONLY the two groups whose
taxonomy matters right now - the transplanted 2B00 family (yellow) and the
still-fallback misc icons (orange) - in bar-grid rows, so the whole output
fits one console page and can be captured + measured without scrolling.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

GROUPS = [
    ("2B00 suite (transplanted)", (255, 255, 0), [0x2B00, 0x2B02, 0x2B04, 0x2B06, 0x2B08, 0x2B0A, 0x2B0C, 0x2B0E, 0x2B10, 0x2B1A, 0x2B12, 0x2B14, 0x2B16, 0x2B18, 0x2B1A, 0x2B1C]),
    ("misc cli icons (fallback)", (255, 128, 0), [0x21B3, 0x2691, 0x26A0, 0x2705, 0x274C, 0x2718, 0x23FA, 0x23F5, 0x2714, 0x2718, 0x2B95, 0x21BB, 0x279C, 0x27A4]),
]

BAR = "\u2502"
RST = "\x1b[0m"


def fg(r, g, b):
    return "\x1b[38;2;%d;%d;%dm" % (r, g, b)


for title, rgb, cps in GROUPS:
    c = fg(*rgb)
    print(c + "=== %s ===" % title + RST)
    for cp in cps:
        run = chr(cp) * 6
        print(c + BAR + RST + " U+%04X " % cp + c + BAR + RST + " " + c + run + RST + " " + c + BAR + RST)
    print(RST)
