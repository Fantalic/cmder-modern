"""Generate a modern East Asian Width (W/F) interval table for ConEmu.

ConEmu's `is_char_cjk()` in src/common/wcwidth.cpp still uses a hand-written
range list from the 2000s: it misses whole emoji blocks (faces U+1F600-1F64F),
so ConEmu allocates 1 cell where modern terminal UIs (wcwidth / go-runewidth,
ambiguous = 1) allocate 2 - every TUI row containing such an icon shifts.

This tool parses EAST ASIAN WIDTH data (Unicode 16.0.0) and rewrites the body
of `is_char_cjk()` with a generated binary-search interval table. Only W and F
characters become double-width; ambiguous (A) characters stay 1-cell, matching
get_wcwidth()'s documented Far-Border requirement.

Usage (from the cmder fork):
  python scripts/conemu-patch/gen_wide_table.py ^
      --eaw .ai/fonts-donor/EastAsianWidth-16.0.0.txt ^
      --wcwidth E:/_tools/ConEmu_upstream/src/common/wcwidth.cpp

The result is committed as a standalone .patch next to this script; the
generator exists so a future Unicode revision can be picked up mechanically.
"""
import argparse
import re
import sys

FUNC_RE = re.compile(r"bool is_char_cjk\(ucs32 ucs\)\s*\{.*?\n\}", re.S)

TEMPLATE = '''bool is_char_cjk(ucs32 ucs)
{
\t/* East Asian Wide (W) or Full-width (F) intervals, generated from
\t   Unicode __VERSION__ EastAsianWidth.txt by
\t   scripts/conemu-patch/gen_wide_table.py - do not edit by hand.
\t   Ambiguous (A) characters deliberately stay 1-cell: see get_wcwidth(). */
\tstatic const struct interval wide[] =
\t{
__ROWS__
\t};
\treturn bisearch(ucs, wide, countof(wide));
}'''


def parse_eaw(path):
    """Return (version, merged [(first, last)] of W/F intervals)."""
    version = "unknown"
    raw = []
    line_re = re.compile(r"^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*;\s*([A-Z]+)")
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                m = re.search(r"EastAsianWidth-([0-9.]+)\.txt", line)
                if m:
                    version = m.group(1)
                continue
            m = line_re.match(line)
            if not m:
                continue
            first = int(m.group(1), 16)
            last = int(m.group(2), 16) if m.group(2) else first
            if m.group(3) in ("W", "F"):
                raw.append((first, last))
    raw.sort()
    merged = []
    for first, last in raw:
        if merged and first <= merged[-1][1] + 1:
            if last > merged[-1][1]:
                merged[-1] = (merged[-1][0], last)
        else:
            merged.append((first, last))
    return version, merged


def render_rows(intervals, per_line=3):
    cells = ["0x%04X, 0x%04X" % (a, b) for a, b in intervals]
    lines = []
    for i in range(0, len(cells), per_line):
        lines.append("\t\t{ " + " }, { ".join(cells[i:i + per_line]) + " }")
    return ",\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eaw", required=True)
    ap.add_argument("--wcwidth", required=True)
    args = ap.parse_args()

    version, intervals = parse_eaw(args.eaw)
    if not intervals:
        sys.exit("no W/F intervals parsed")

    source = open(args.wcwidth, "rb").read()
    has_bom = source.startswith(b"\xef\xbb\xbf")
    text = source.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")

    body = TEMPLATE.replace("__VERSION__", version) \
                   .replace("__ROWS__", render_rows(intervals))
    patched, count = FUNC_RE.subn(lambda _m: body, text, count=1)
    if count != 1:
        sys.exit("is_char_cjk() not found in " + args.wcwidth)

    patched = patched.replace("\n", newline)
    data = (b"\xef\xbb\xbf" if has_bom else b"") + patched.encode("utf-8")
    with open(args.wcwidth, "wb") as f:
        f.write(data)
    print("unicode %s: %d W/F intervals written to %s"
          % (version, len(intervals), args.wcwidth))


if __name__ == "__main__":
    main()
