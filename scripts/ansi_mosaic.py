"""Render images as colored character mosaics for the terminal (chafa-style).

Technique: one character cell carries two vertical pixels. U+2580 (upper half
block) paints the top pixel with the foreground color and the bottom pixel with
the background color, so a cell grid of CxR shows a Cx2R pixel image. Output is
plain SGR text, so it survives every ANSI terminal (and even survives conhost,
which cannot store non-BMP codepoints at all).

Example:
    python scripts/ansi_mosaic.py --input icons/icon_256.png --width 24
    python scripts/ansi_mosaic.py --banner --out vendor/art/cmder_banner.ans
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is optional for the plain modes
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RESET = "\x1b[0m"
DEFAULT_BG = "\x1b[49m"
HALF_UP = "\u2580"   # upper half block: fg = top pixel, bg = bottom pixel
HALF_DOWN = "\u2584"  # lower half block: fg = bottom pixel
SPACE = " "

# 4x4 ordered dither matrix, normalized to 0..1
BAYER = [
    [0 / 16, 8 / 16, 2 / 16, 10 / 16],
    [12 / 16, 4 / 16, 14 / 16, 6 / 16],
    [3 / 16, 11 / 16, 1 / 16, 9 / 16],
    [15 / 16, 7 / 16, 13 / 16, 5 / 16],
]


def sgr_fg(rgb):
    return "\x1b[38;2;%d;%d;%dm" % rgb


def sgr_bg(rgb):
    return "\x1b[48;2;%d;%d;%dm" % rgb


def quantize(rgb, colors):
    """Map an RGB triple onto the requested palette."""
    if colors == "truecolor":
        return rgb
    if colors == "256":
        r, g, b = rgb
        if r == g == b:
            if r < 8:
                return (16, 0, 0)
            if r > 248:
                return (231, 255, 255)
            return (232 + (r - 8) * 24 // 247,) * 3
        q = lambda v: max(0, min(5, (v - 35) // 40))
        return (16 + 36 * q(r), 16 + 36 * q(g), 16 + 36 * q(b))
    # 16 colors: nearest of the xterm basic palette
    basic = [
        (0, 0, 0), (170, 0, 0), (0, 170, 0), (170, 85, 0),
        (0, 0, 170), (170, 0, 170), (0, 170, 170), (170, 170, 170),
        (85, 85, 85), (255, 85, 85), (85, 255, 85), (255, 255, 85),
        (85, 85, 255), (255, 85, 255), (85, 255, 255), (255, 255, 255),
    ]
    return min(basic, key=lambda c: sum((a - b) ** 2 for a, b in zip(c, rgb)))


def dither(rgb, x, y, amount):
    """Ordered dithering: shift the color by a small threshold offset."""
    if amount <= 0:
        return rgb
    threshold = (BAYER[y % 4][x % 4] - 0.5) * amount
    return tuple(max(0, min(255, int(v + threshold))) for v in rgb)


def sample_rows(image, cols, pixel_rows, alpha_threshold=None):
    """Return a list of pixel_rows, each a list of (r, g, b, alpha) tuples."""
    rgba = image.convert("RGBA")
    target = (cols, pixel_rows)
    scaled = rgba.resize(target, Image.LANCZOS)
    data = scaled.load()
    rows = []
    for y in range(pixel_rows):
        row = []
        for x in range(cols):
            r, g, b, a = data[x, y]
            if alpha_threshold is not None:
                # Line art: keep the strokes crisp instead of letting the
                # resampling filter smear them over the whole bounding box.
                a = 255 if a >= alpha_threshold else 0
                if a == 0:
                    r = g = b = 0
            row.append((r, g, b, a))
        rows.append(row)
    return rows


def average(pixels):
    weight = 0.0
    acc = [0.0, 0.0, 0.0]
    for r, g, b, a in pixels:
        alpha = a / 255.0
        acc[0] += r * alpha
        acc[1] += g * alpha
        acc[2] += b * alpha
        weight += alpha
    if weight <= 0:
        return (0, 0, 0, 0)
    return (int(acc[0] / weight), int(acc[1] / weight), int(acc[2] / weight),
            int(255 * weight / len(pixels)))


def mosaic_lines(image, cols, colors="truecolor", dither_amount=0, alpha_threshold=None):
    """Render the image into terminal lines of half-block cells."""
    w, h = image.size
    # A character cell is about twice as tall as it is wide, and each cell
    # carries two pixel rows, so the pixel grid is cols x (cols * aspect).
    aspect = h / float(w)
    pixel_rows = max(2, int(round(cols * aspect)))
    if pixel_rows % 2:
        pixel_rows += 1
    rows = sample_rows(image, cols, pixel_rows, alpha_threshold)

    lines = []
    for cy in range(0, pixel_rows, 2):
        top_row, bottom_row = rows[cy], rows[cy + 1]
        line = []
        for x in range(cols):
            top = average([top_row[x]])
            bottom = average([bottom_row[x]])
            if top[3] == 0 and bottom[3] == 0:
                line.append(SPACE)
                continue
            if top[3] == 0:
                rgb = quantize(dither(bottom[:3], x, cy + 1, dither_amount), colors)
                line.append(sgr_fg(rgb) + HALF_DOWN + RESET)
                continue
            if bottom[3] == 0:
                rgb = quantize(dither(top[:3], x, cy, dither_amount), colors)
                line.append(sgr_fg(rgb) + DEFAULT_BG + HALF_UP + RESET)
                continue
            fg = quantize(dither(top[:3], x, cy, dither_amount), colors)
            bg = quantize(dither(bottom[:3], x, cy + 1, dither_amount), colors)
            line.append(sgr_fg(fg) + sgr_bg(bg) + HALF_UP + RESET)
        lines.append("".join(line))
    return lines


def gradient_text(text, top, bottom):
    """Color text with a vertical gradient, one SGR pair per character."""
    out = []
    n = max(1, len(text))
    for i, ch in enumerate(text):
        t = i / float(n - 1) if n > 1 else 0.0
        rgb = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        out.append(sgr_fg(rgb) + ch)
    out.append(RESET)
    return "".join(out)


def lambda_mark(icon_path, top=(126, 231, 135), bottom=(86, 204, 242)):
    """Cut the neutral-dark lambda strokes out of the icon tile and colorize them.

    The icon is a saturated green tile with near-black strokes, so the strokes
    are selected by "dark and unsaturated" and everything else is dropped.
    """
    icon = Image.open(icon_path).convert("RGBA")
    w, h = icon.size
    px = icon.load()
    mask = Image.new("L", (w, h), 0)
    mpx = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            saturation = (mx - mn) / float(mx) if mx else 0.0
            if mx < 110 and saturation < 0.35:
                mpx[x, y] = 255
    bbox = mask.getbbox()
    if not bbox:
        raise SystemExit("no lambda strokes found in %s" % icon_path)
    mark = Image.new("RGBA", (bbox[2] - bbox[0], bbox[3] - bbox[1]), (0, 0, 0, 0))
    mp = mark.load()
    mw, mh = mark.size
    for y in range(mh):
        t = y / float(max(1, mh - 1))
        rgb = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        for x in range(mw):
            if mpx[bbox[0] + x, bbox[1] + y] > 0:
                mp[x, y] = (rgb[0], rgb[1], rgb[2], 255)
    return mark


def build_banner(icon_path, width=9, colors="truecolor"):
    """Compose the startup banner: lambda mosaic on the left, text on the right."""
    if Image is None:
        raise SystemExit("Pillow is required to build the banner")

    mark = lambda_mark(icon_path)
    logo_lines = mosaic_lines(mark, width, colors=colors, alpha_threshold=96)

    title = "cmder"
    subtitle = "modernized fork  \u00b7  ConEmu + Clink"
    tagline = "UTF-8 \u00b7 truecolor \u00b7 Nerd icons \u00b7 modern CLI tools"

    title_line = gradient_text(title, (126, 231, 135), (86, 204, 242))
    sub_line = "\x1b[38;2;150;160;170m" + subtitle + RESET
    tag_line = "\x1b[38;2;100;110;120m" + tagline + RESET

    text_lines = [title_line, sub_line, tag_line]
    top_pad = max(0, (len(logo_lines) - len(text_lines)) // 2)

    out = []
    for i, logo in enumerate(logo_lines):
        idx = i - top_pad
        right = text_lines[idx] if 0 <= idx < len(text_lines) else ""
        out.append(logo + "  " + right if right else logo)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="image file to render")
    parser.add_argument("--banner", action="store_true",
                        help="build the cmder startup banner")
    parser.add_argument("--icon", default=os.path.join(ROOT, "icons", "icon_256.png"))
    parser.add_argument("--width", type=int, default=22, help="mosaic width in cells")
    parser.add_argument("--colors", choices=("truecolor", "256", "16"), default="truecolor")
    parser.add_argument("--dither", type=float, default=0.0,
                        help="ordered dither strength in RGB units")
    parser.add_argument("--out", help="output file (default: stdout)")
    args = parser.parse_args(argv)

    if args.banner:
        lines = build_banner(args.icon, args.width, args.colors)
    elif args.input:
        if Image is None:
            raise SystemExit("Pillow is required to render images")
        image = Image.open(args.input).convert("RGBA")
        lines = mosaic_lines(image, args.width, args.colors, args.dither)
    else:
        parser.error("either --input or --banner is required")

    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
