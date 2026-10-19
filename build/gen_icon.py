"""build/gen_icon.py  –  Generate app.ico for the app window and installer."""

import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "app", "assets", "app.ico")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

SIZE = 256
img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

# Gradient background
grad = Image.new("RGBA", (SIZE, SIZE))
for y in range(SIZE):
    t = y / SIZE
    r = int(30  + (20  - 30)  * t)
    g = int(80  + (60  - 80)  * t)
    b = int(220 + (180 - 220) * t)
    for x in range(SIZE):
        xt = x / SIZE
        rb = int(r + (120 - r) * xt * 0.3)
        gb = int(g + (40  - g) * xt * 0.1)
        bb = int(b + (255 - b) * xt * 0.15)
        grad.putpixel((x, y), (rb, gb, bb, 255))

# Rounded-square mask
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle([4, 4, SIZE-4, SIZE-4], radius=56, fill=255)
img.paste(grad, (0, 0), mask)

# Glyph  "S" for Studio
d = ImageDraw.Draw(img)
font_path = None
for name in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
    for root in (r"C:\Windows\Fonts",):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            font_path = p
            break
    if font_path:
        break

fnt = (ImageFont.truetype(font_path, 140) if font_path
       else ImageFont.load_default())
text = "S"
bb = d.textbbox((0, 0), text, font=fnt)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
d.text(((SIZE - tw) / 2 - bb[0], (SIZE - th) / 2 - bb[1] + 6),
       text, font=fnt, fill=(255, 255, 255, 240))

sizes = [(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)]
img.save(OUT, format="ICO", sizes=sizes)
print("Icon written to", OUT)
