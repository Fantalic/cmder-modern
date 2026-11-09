"""Coverage audit: for every codepoint in the icon inventory, check which
font actually renders it - the vendored CaskaydiaCove NF directly, or via
the Windows fallback chain (Segoe UI Symbol / Segoe UI). Codepoints missing
everywhere print as tofu boxes in the terminal.

Writes: .ai/diagnostics/coverage_audit.txt
"""
import struct

FONTS = {
    "vendored": r"E:\_tools\cmder_fork\vendor\fonts\CaskaydiaCoveNerdFont-Regular.ttf",
    "SegoeSym": r"C:\Windows\Fonts\seguisym.ttf",
    "SegoeUI": r"C:\Windows\Fonts\segoeui.ttf",
}


def cmap_cover(path, cp):
    data = open(path, "rb").read()
    num = struct.unpack(">H", data[4:6])[0]
    cmap = None
    for i in range(num):
        tag, cs, off, ln = struct.unpack(">4sIII", data[12 + i * 16: 12 + (i + 1) * 16])
        if tag == b"cmap":
            cmap = off
    n = struct.unpack(">H", data[cmap + 2: cmap + 4])[0]
    for i in range(n):
        pid, eid, off = struct.unpack(">HHI", data[cmap + 4 + i * 8: cmap + 4 + (i + 1) * 8])
        so = cmap + off
        fo = struct.unpack(">H", data[so:so + 2])[0]
        if fo == 4:
            sx = struct.unpack(">H", data[so + 6: so + 8])[0]
            sc = sx // 2
            ends = struct.unpack(">%dH" % sc, data[so + 14: so + 14 + sx])
            starts = struct.unpack(">%dH" % sc, data[so + 16 + sx: so + 16 + 2 * sx])
            for s, e in zip(starts, ends):
                if s <= cp <= e:
                    return True
        if fo == 12:
            ng = struct.unpack(">I", data[so + 12: so + 16])[0]
            gp = so + 16
            for _ in range(min(ng, 6000)):
                s, e, sid = struct.unpack(">III", data[gp: gp + 12])
                gp += 12
                if s <= cp <= e and sid != 0xFFFFFFFF:
                    return True
    return False


GROUPS = {
    "opencode spinner blocks": [0x2588, 0x2584, 0x2580, 0x2590, 0x258C, 0x25A0, 0x2B1D],
    "opencode spinner diamonds": [0x2B25, 0x25C6, 0x2B29, 0x2B2A, 0x00B7],
    "message badge shapes": [0x25A3, 0x25A1, 0x25A2],
    "tool-row icons": [0x0024, 0x2699, 0x2731, 0x25C8, 0x2190, 0x2192, 0x2713, 0x2717, 0x2502, 0x2726],
    "2B00 block suite (user-flagged drift)": [0x2B00, 0x2B02, 0x2B04, 0x2B06, 0x2B08, 0x2B0A, 0x2B0C, 0x2B0E,
                                               0x2B10, 0x2B12, 0x2B14, 0x2B16, 0x2B18, 0x2B1A, 0x2B1C],
    "braille": [0x280B, 0x2817, 0x2826, 0x2815, 0x2803, 0x2812, 0x2814, 0x2816, 0x2821, 0x2810, 0x2822, 0x2813],
    "box drawing": [0x250C, 0x2500, 0x2510, 0x2514, 0x251C, 0x2524, 0x252C, 0x253C, 0x255D, 0x2554, 0x2550, 0x2551],
    "arrows misc": [0x2191, 0x2193, 0x21B3, 0x2691, 0x26A0, 0x2705, 0x274C, 0x2713, 0x2718],
    "extra modern-TUI suspects": [0x23FA, 0x23F5, 0x23CE, 0x2714, 0x2718, 0x25B2, 0x25BC, 0x25AE, 0x25CF, 0x25CB, 0x2022, 0x2026, 0x279C, 0x26A1, 0x27A4, 0x25B6, 0x25C0, 0x2B95, 0x21BB],
    "powerline segments": [0xE0B0, 0xE0B1, 0xE0B2, 0xE0B3, 0xE0B6],
}

rows = []
out = open(r"E:\_tools\cmder_fork\.ai\diagnostics\coverage_audit.txt", "w", encoding="utf-8")
for group, cps in GROUPS.items():
    out.write("== %s\n" % group)
    for cp in cps:
        state = []
        for name, path in FONTS.items():
            try:
                state.append(name if cmap_cover(path, cp) else None)
            except Exception as e:
                state.append("ERR")
        present = [s for s in state if s and s != "ERR"]
        verdict = "vendored" if "vendored" in present else ("fallback:%s" % "+".join(present) if present else "TOFU-NOT-RENDERED")
        rows.append((group, cp, verdict))
        out.write("  U+%04X -> %s\n" % (cp, verdict))
out.write("\n## drift/tofu summary\n")
for group, cp, verdict in rows:
    if verdict != "vendored":
        out.write("NEEDS-FIX U+%04X (%s): %s\n" % (cp, group, verdict))
out.close()

# console summary
counts = {}
for group, cp, verdict in rows:
    counts.setdefault(verdict.split(":")[0] if verdict != "TODO" else verdict, []).append("U+%04X" % cp)
for k, v in counts.items():
    print(k, len(v))
print("NEEDS-FIX list:")
for group, cp, verdict in rows:
    if verdict != "vendored":
        print("  U+%04X (%s): %s" % (cp, group, verdict))
