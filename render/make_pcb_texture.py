"""The top of the ProMicro NRF52840 clone, from the user's photos: colour, a gold mask and a height map."""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

OUT = sys.argv[1]
K = 40  # px per mm
W, Hh = 18.0, 33.0
F = "/System/Library/Fonts/Supplemental/"
small = ImageFont.truetype(F + "Arial Bold.ttf", round(0.72 * K / 0.72 * 0.72))
label_font = ImageFont.truetype(F + "Arial Rounded Bold.ttf", round(1.75 * K))
label_font2 = ImageFont.truetype(F + "Arial Bold.ttf", round(1.45 * K))
MASK = (16, 16, 18)
GOLD = (214, 176, 96)
HOLE = (6, 6, 6)
SILK = (226, 226, 220)

col = Image.new("RGB", (round(W * K), round(Hh * K)), MASK)
metal = Image.new("L", col.size, 0)
height = Image.new("L", col.size, 128)
dc, dm, dh = ImageDraw.Draw(col), ImageDraw.Draw(metal), ImageDraw.Draw(height)

def px(x, y):  # board mm (y up from the bottom edge) to image px
    return (x * K, (Hh - y) * K)

def circle(d, x, y, r, fill):
    cx, cy = px(x, y); d.ellipse([cx - r * K, cy - r * K, cx + r * K, cy + r * K], fill=fill)

def rect(d, x0, y0, x1, y1, fill, radius=0):
    a, b = px(x0, y1), px(x1, y0)
    d.rounded_rectangle([a[0], a[1], b[0], b[1]], radius=radius * K, fill=fill)

def pad(x, y, square=False, od=1.75, hole=1.0):
    for d, f, hf in ((dc, GOLD, None), (dm, 255, None), (dh, 200, None)):
        if square: rect(d, x - od / 2, y - od / 2, x + od / 2, y + od / 2, f)
        else: circle(d, x, y, od / 2, f)
    circle(dc, x, y, hole / 2, HOLE); circle(dm, x, y, hole / 2, 0); circle(dh, x, y, hole / 2, 20)

def text(x, y, s, font, fill=SILK, anchor="mm"):
    dc.text(px(x, y), s, font=font, fill=fill, anchor=anchor)
    dh.text(px(x, y), s, font=font, fill=150, anchor=anchor)

# 12 through-hole pads down each long edge, 0.6 inch apart, 0.1 inch pitch
left = ["D3", "D2", "GND", "GND", "D1", "D0", "D4", "C6", "D7", "E6", "B4", "B5"]
right = ["RAW", "GND", "RST", "VCC", "F4", "F5", "F6", "F7", "B1", "B3", "B2", "B6"]
xl, xr = W / 2 - 7.62, W / 2 + 7.62
for i in range(12):
    y = 30.0 - i * 2.54
    pad(xl, y, square=(i == 0)); pad(xr, y)
    text(xl + 1.55, y, left[i], small, anchor="lm"); text(xr - 1.55, y, right[i], small, anchor="rm")
# the USB-C shell's tabs go through gold slots either side of the receptacle
for sx in (W / 2 - 4.32, W / 2 + 4.32):
    for d, f in ((dc, GOLD), (dm, 255), (dh, 200)):
        rect(d, sx - 0.55, 29.9, sx + 0.55, 32.1, f, radius=0.55)
    rect(dc, sx - 0.3, 30.2, sx + 0.3, 31.8, HOLE, radius=0.3); rect(dm, sx - 0.3, 30.2, sx + 0.3, 31.8, 0, radius=0.3)
# three round pads at the bottom between the rows, and the SWD pads in the bottom left
for i, nm in enumerate(["B", "B", "B"]):
    pad(W / 2 - 2.54 + i * 2.54, 2.0, od=1.5, hole=0.8)
for i, nm in enumerate(["VDD", "DIO", "CLK", "GND"]):
    y = 9.4 - i * 1.25
    for d, f in ((dc, GOLD), (dm, 255), (dh, 200)):
        rect(d, 5.6, y - 0.42, 6.45, y + 0.42, f)
    text(6.85, y, nm, small, anchor="lm")
# the white label in the middle
rect(dc, W / 2 - 4.9, 14.6, W / 2 + 4.9, 20.6, (236, 236, 232), radius=0.25); rect(dh, W / 2 - 4.9, 14.6, W / 2 + 4.9, 20.6, 160, radius=0.25)
text(W / 2, 19.0, "ProMicro", label_font, fill=(20, 20, 22))
text(W / 2, 16.2, "NRF52840", label_font2, fill=(20, 20, 22))
# a few 0402 parts: grey bodies with tinned ends
random.seed(3)
for (x, y, rot) in [(6.0, 26.8, 0), (7.3, 26.8, 0), (11.0, 26.6, 1), (12.4, 25.0, 0), (6.4, 11.6, 1), (11.8, 11.2, 0), (13.2, 9.8, 1), (9.0, 6.2, 0)]:
    w, h = (1.0, 0.5) if rot == 0 else (0.5, 1.0)
    rect(dc, x - w / 2, y - h / 2, x + w / 2, y + h / 2, (52, 50, 46)); rect(dh, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 210)
    for e in (-1, 1):
        ex, ey = (x + e * (w / 2 - 0.12), y) if rot == 0 else (x, y + e * (h / 2 - 0.12))
        ew, eh = (0.24, h) if rot == 0 else (w, 0.24)
        rect(dc, ex - ew / 2, ey - eh / 2, ex + ew / 2, ey + eh / 2, (190, 190, 186)); rect(dm, ex - ew / 2, ey - eh / 2, ex + ew / 2, ey + eh / 2, 255)
# a silkscreen arrow by pin 1 and the board's outline
text(xl + 1.4, 31.55, "▲", ImageFont.truetype(F + "Arial Unicode.ttf", round(0.6 * K)), anchor="mm")
height = height.filter(ImageFilter.GaussianBlur(1.2))
col.save(f"{OUT}/pcb_colour.png"); metal.save(f"{OUT}/pcb_metal.png"); height.save(f"{OUT}/pcb_height.png")
print("wrote", col.size)
