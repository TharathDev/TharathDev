"""
Convert a portrait into ASCII art for the profile card.

usage: python make_ascii.py <cutout.png> <ascii.txt> [rows] [crop=l,t,r,b]

The input should be a PNG with a transparent background (e.g. produced with
`rembg`). Transparent pixels become spaces; brighter pixels get denser glyphs,
so the art reads naturally as light text on the dark card.
"""
import sys
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

RAMP = " .'`^,:;Il!i><~+_-?][}{1)(|tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
CELL_ASPECT = 9.63 / 20  # glyph width / line height used in generate.py

src, out = sys.argv[1], sys.argv[2]
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 25
im = Image.open(src).convert("RGBA")
if len(sys.argv) > 4:
    im = im.crop(tuple(int(v) for v in sys.argv[4].split(",")))

alpha = im.getchannel("A")
gray = ImageOps.grayscale(im)
gray = ImageOps.equalize(gray, mask=alpha.point(lambda a: 255 if a > 128 else 0))
gray = ImageEnhance.Contrast(gray).enhance(1.3).filter(ImageFilter.DETAIL)

cols = round(rows * im.width / im.height / CELL_ASPECT)
small = gray.resize((cols, rows), Image.LANCZOS)
small_a = alpha.resize((cols, rows), Image.BILINEAR)

lines = []
for y in range(rows):
    row = ""
    for x in range(cols):
        if small_a.getpixel((x, y)) < 100:
            row += " "
        else:
            v = small.getpixel((x, y))
            row += RAMP[max(1, round(v / 255 * (len(RAMP) - 1)))]
    lines.append(row.rstrip())

open(out, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
