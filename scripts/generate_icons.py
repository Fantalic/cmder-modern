# -*- coding: utf-8 -*-
"""Rebuilds icons/cmder*.ico and icons/icon_*.png for this fork.

Design: modern flat rounded-square tile with a vertical two-stop gradient,
a soft top highlight, and the classic lambda (λ) glyph typeset in the
bundled JetBrainsMono Nerd Font. Each target size is rendered directly
(supersampled, then downscaled), so small sizes stay crisp instead of
being blurry downscales of one master.

Usage:  python scripts/generate_icons.py [font_path]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(os.path.dirname(HERE), "icons")
DEFAULT_FONT = os.path.join(
    os.path.dirname(HERE), "vendor", "fonts", "JetBrainsMonoNerdFont-Regular.ttf"
)

# (output name, top color, bottom color)
VARIANTS = [
    ("",          (139, 195, 74), (76, 155, 9)),    # default cmder green
    ("_green",    (168, 223, 99), (96, 176, 39)),   # lighter green
    ("_blue",     (64, 156, 255), (27, 100, 217)),
    ("_purple",   (142, 90, 242), (106, 53, 201)),
    ("_orange",   (245, 138, 37), (217, 106, 8)),
    ("_red",      (229, 68, 58),  (194, 43, 34)),
    ("_yellow",   (242, 194, 48), (217, 160, 18)),
]

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 32, 48, 256]
GLYPH = "λ"
GLYPH_COLOR = (35, 37, 41, 255)

# Small sizes need a proportionally heavier glyph to stay readable.
GLYPH_MIN_RATIO = 0.58
GLYPH_MAX_RATIO = 0.62
# Below this pixel size-typeset, switch to the Bold face so the lambda's
# strokes keep at least one solid pixel width after downsampling.
BOLD_BELOW = 48


def ratio_at(size):
    return GLYPH_MIN_RATIO + (GLYPH_MAX_RATIO - GLYPH_MIN_RATIO) * min(
        1.0, max(0.0, (size - 16) / (128 - 16))
    )


def draw_tile(size, top, bottom, font_path):
    """Render one icon at `size`, supersampled 4x for antialiasing."""
    ss = size * 4
    radius = int(ss * 0.225)

    tile = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    grad = Image.new("RGBA", (ss, ss))
    for y in range(ss):
        t = y / (ss - 1)
        col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(ss):
            grad.putpixel((x, y), col)
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, ss - 1, ss - 1), radius=radius, fill=255
    )
    tile.paste(grad, (0, 0), mask)

    # Soft top highlight rim
    rim = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(
        (int(ss * 0.045), int(ss * 0.045),
         ss - int(ss * 0.045), int(ss * 0.045) + int(ss * 0.03)),
        radius=int(ss * 0.03), fill=(255, 255, 255, 46),
    )
    rim = rim.filter(ImageFilter.GaussianBlur(ss / 64))
    tile.alpha_composite(rim)

    # Lambda with a soft drop shadow, typeset in the Nerd Font.
    # Tiny sizes use the Bold face so strokes survive the downscale.
    fsize = int(ss * ratio_at(size) * (1.12 if size < BOLD_BELOW else 1.0))
    face = os.path.join(os.path.dirname(font_path), "JetBrainsMonoNerdFont-Bold.ttf")
    font = ImageFont.truetype(face if size < BOLD_BELOW else font_path, fsize)
    tmp = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), GLYPH, font=font)
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    gx = (ss - gw) // 2 - bbox[0]
    gy = int((ss - gh) * 0.52) - bbox[1]

    shadow = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text(
        (gx + fsize // 22, gy + fsize // 20), GLYPH, font=font, fill=(0, 0, 0, 90)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(fsize / 26))
    tile.alpha_composite(shadow)
    d = ImageDraw.Draw(tile)
    d.text((gx, gy), GLYPH, font=font, fill=GLYPH_COLOR)

    return tile.resize((size, size), Image.LANCZOS)


def main():
    font = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FONT
    if not os.path.isfile(font):
        raise SystemExit("font not found: %s" % font)

    for suffix, top, bottom in VARIANTS:
        # 1) PNG exports (upstream naming parity)
        for s in PNG_SIZES:
            tile = draw_tile(s, top, bottom, font)
            png = os.path.join(ICON_DIR, "icon_%d%s.png" % (s, suffix))
            tile.save(png)
        # 2) ICO with every embedded size
        ico_name = "cmder%s.ico" % (suffix or "")
        ico_path = os.path.join(ICON_DIR, ico_name)
        logo = Image.new("RGBA", ICO_SIZES[-1:] * 2)
        master = draw_tile(ICO_SIZES[-1], top, bottom, font)
        master.save(ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES])
        print("wrote %s" % os.path.relpath(ico_path, os.path.dirname(ICON_DIR)))


if __name__ == "__main__":
    main()
