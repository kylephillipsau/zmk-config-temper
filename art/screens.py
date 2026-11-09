# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "pyyaml"]
# ///
"""The nice!view screens, drawn in portrait (68 x 160, 1 = ink), and everything made from them.

    uv run art/screens.py

Writes:
  - boards/shields/nice_view_legend/widgets/legend_art.c: the right screen's legends (the 68 x 140
    below the battery and link bar, which the firmware draws itself) and the left screen's cards
    (the 68 x 92 below the status area): the combos, and the left hand's keys on each layer
  - boards/shields/nice_view_legend/widgets/status_glyphs.h: the left screen's icons
  - docs/screens/*.png: each screen in black and white, for the README

The left screen's status area is drawn by widgets/status.c at runtime. left_status() mirrors it
with the firmware's own fonts (lvfont.py), so the README images match the device.
"""
import math
import os
import re
import sys

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SHIELD = os.path.join(REPO, 'boards', 'shields', 'nice_view_legend')
sys.path.insert(0, HERE)
from lvfont import LvFont  # noqa: E402

W, H = 68, 160
F = os.path.join(HERE, 'fonts')
silk = ImageFont.truetype(os.path.join(F, 'Silkscreen-Regular.ttf'), 8)  # 5 px caps
silk_b = ImageFont.truetype(os.path.join(F, 'Silkscreen-Bold.ttf'), 8)
jer24 = ImageFont.truetype(os.path.join(F, 'Jersey10-Regular.ttf'), 24)  # 13 px caps


def glyph(rows):
    return [[c == '#' for c in r] for r in rows]


def rot(g, k):
    for _ in range(k % 4):
        g = [list(r) for r in zip(*g[::-1])]
    return g


def blit(img, g, x, y, ink=1):
    px = img.load()
    for j, row in enumerate(g):
        for i, on in enumerate(row):
            if on and 0 <= x + i < img.width and 0 <= y + j < img.height:
                px[x + i, y + j] = ink


def new():
    img = Image.new('1', (W, H), 0)
    d = ImageDraw.Draw(img)
    d.fontmode = '1'
    return img, d


def text(d, xy, s, font, anchor='l', fill=1):
    """Draw s with the top of its ink at y; anchor 'c' with x None centres it on the screen."""
    b = d.textbbox((0, 0), s, font=font)
    w = b[2] - b[0]
    x, y = xy
    if anchor == 'c':
        x = (W - w) // 2 if x is None else x - w // 2
    elif anchor == 'r':
        x = x - w
    d.text((x - b[0], y - b[1]), s, font=font, fill=fill)
    return w


# ---------------------------------------------------------------------------------------- glyphs

WIFI = glyph([
    "...#####...",
    ".##.....##.",
    "#..#####..#",
    ".##.....##.",
    "...#####...",
    "..#.....#..",
    "....###....",
    ".....#.....",
])
ARROW_U = glyph(["...#...", "..###..", ".#####.", "#######", "..###..", "..###..", "..###.."])
BT = glyph([
    "...#...",
    "...##..",
    ".#.#.#.",
    "..###..",
    "...#...",
    "..###..",
    ".#.#.#.",
    "...##..",
    "...#...",
])
CMD = glyph([
    ".##...##.",
    "#..#.#..#",
    "#..#.#..#",
    ".#######.",
    "...#.#...",
    ".#######.",
    "#..#.#..#",
    "#..#.#..#",
    ".##...##.",
])
OPT = glyph([
    "###..####",
    "...#.....",
    "....#....",
    ".....#...",
    "......###",
])
# On Windows (the WIN layer), the Windows logo and ALT stand in for Cmd and Option.
WIN = glyph([
    "###.###",
    "#.#.#.#",
    "###.###",
    ".......",
    "###.###",
    "#.#.#.#",
    "###.###",
])
ALT = glyph([
    ".#..#.###",
    "#.#.#..#.",
    "###.#..#.",
    "#.#.#..#.",
    "#.#.##.#.",
])
CTRL = glyph([
    "....#....",
    "...#.#...",
    "..#...#..",
    ".#.....#.",
])
SHIFT = glyph([
    "....#....",
    "...#.#...",
    "..#...#..",
    ".#.....#.",
    "###...###",
    "..#...#..",
    "..#...#..",
    "..#####..",
])
CAPS = glyph([
    "....#....",
    "...###...",
    "..#####..",
    ".#######.",
    "###...###",
    "..#...#..",
    "..#####..",
    ".........",
    "..#####..",
])
BOLT = glyph(["...##", "..##.", ".####", "..##.", ".##..", "##..."])

# Silkscreen draws ; ' , . ` as 1-2 px specks, so key labels and symbols use these bolder glyphs.
# Rows 0-4 sit on the caps height; row 5 is a descender.
PUNCT = {
    ';': glyph(["##", "##", "..", "##", "##", ".#"]),
    ':': glyph(["##", "##", "..", "##", "##"]),
    "'": glyph(["##", "##", ".#", "..", ".."]),
    '"': glyph(["##.##", "##.##", ".#..#", ".....", "....."]),
    '`': glyph(["##.", ".##", "...", "...", "..."]),
    ',': glyph(["..", "..", "..", "##", "##", ".#"]),
    '.': glyph(["..", "..", "..", "##", "##"]),
    '/': glyph(["...##", "..##.", ".##..", "##...", "#...."]),
    '\\': glyph(["##...", ".##..", "..##.", "...##", "....#"]),
    '|': glyph(["##", "##", "##", "##", "##", "##"]),
    '~': glyph([".....", ".##.#", "#.##.", ".....", "....."]),
    '&': glyph([".#..", "#.#.", ".#..", "#.##", ".##."]),  # Silkscreen's looks like $
    '^': glyph(["..#..", ".###.", "##.##", ".....", "....."]),  # Silkscreen's is a speck
    '4': glyph(["##.##", "##.##", "#####", "...##", "...##"]),  # Silkscreen's reads as a blob
}


def label(img, d, x, y, s, font=silk_b, gap=1):
    """Draw s with its capitals' tops at y, using PUNCT for small punctuation; returns the width."""
    cap_top = d.textbbox((0, 0), 'H', font=font)[1]
    x0 = x
    for ch in s:
        if ch in PUNCT:
            g = PUNCT[ch]
            blit(img, g, x, y)
            x += len(g[0]) + gap
        elif ch == ' ':
            x += 3
        else:
            d.text((x, y - cap_top), ch, font=font, fill=1)
            x += round(d.textlength(ch, font=font))
    return x - x0


def label_w(d, s, font=silk_b, gap=1):
    probe = Image.new('1', (200, 20))
    return label(probe, ImageDraw.Draw(probe), 0, 5, s, font, gap)


def rows(img, d, y, pairs, step=10):
    """Key on the left in bold, what it does on the right."""
    for key, does in pairs:
        label(img, d, 1, y, key)
        label(img, d, W - 1 - label_w(d, does, silk), y, does, silk)
        y += step
    return y


# ------------------------------------------------------------------------------ the right screen

def status_bar(img, d, level=78, connected=True):
    """The top 20 rows, which the firmware draws (util.c draw_battery and the link symbol)."""
    x, y = 0, 2
    d.rectangle([x, y, x + 28, y + 11], outline=1)
    fill = (level + 2) // 4
    if fill:
        d.rectangle([x + 2, y + 2, x + 1 + fill, y + 9], fill=1)
    d.rectangle([x + 30, y + 3, x + 32, y + 8], fill=1)
    d.line([(x + 31, y + 4), (x + 31, y + 7)], fill=0)
    blit(img, WIFI, W - 12, 3)


def header(d, name):
    d.rectangle([0, 20, W - 1, 33], fill=1)
    text(d, (None, 24), name, silk_b, 'c', fill=0)


def thumbs(img, d, x, y, held, w=3, h=5, gap=1, split=4):
    """The six thumb keys, left outer to right outer, on one baseline: a held key is a solid w x h
    block and a free one only its 1 px base. An outline beside a filled square differs by a pixel
    or two at this size, which can't be read on the panel; these differ by most of their ink."""
    for i in range(6):
        bx = x + i * (w + gap) + (split if i >= 3 else 0)
        top = y if i in held else y + h - 1
        d.rectangle([bx, top, bx + w - 1, y + h - 1], fill=1)


def mini_temper(img, d, y):
    """Both halves from the PCB's key positions (keymap_img/temper-board.yaml): 4 px keys on a 5 px
    pitch, which is 18 mm across and 17 mm down on the board, so no two keys touch. The halves sit
    6 px apart; on the board it's about 70 mm."""
    board = yaml.safe_load(open(os.path.join(REPO, 'keymap_img', 'temper-board.yaml')))
    left = [k for k in board['keys'] if k['x'] < board['width'] / 2]
    cx0 = min(k['x'] + k['w'] / 2 for k in left)
    cy0 = min(k['y'] + k['h'] / 2 for k in left)
    for k in left:
        # top left corner of the 4 px key, rounding half up
        kx = math.floor((k['x'] + k['w'] / 2 - cx0) * 5 / 18 + 0.5) - 2
        ky = math.floor((k['y'] + k['h'] / 2 - cy0) * 5 / 17 + 0.5) - 2
        for x in (kx + 4, W - 1 - (kx + 4) - 3):  # the left half, then the right half mirrored
            d.rectangle([x, y + ky + 2, x + 3, y + ky + 5], fill=1)


def legend_base():
    img, d = new()
    status_bar(img, d)
    text(d, (None, 26), 'SHORT', jer24, 'c')
    text(d, (None, 42), 'TEMPER', jer24, 'c')
    mini_temper(img, d, 63)
    # which thumbs to hold for each layer
    y = 98
    for held, name in (((0,), 'NAV'), ((2,), 'SYM'), ((3,), 'NUM'), ((2, 3), 'SYSTEM')):
        thumbs(img, d, 1, y, held)  # as tall as the capitals, and clear of SYSTEM
        label(img, d, W - 1 - label_w(d, name, silk), y, name, silk)
        y += 11
    d.rectangle([0, 146, W - 1, 159], outline=1)
    text(d, (None, 150), 'BASE', silk_b, 'c')
    return img


# ---------------------------------------------------------------------------- each layer, key by key
#
# While a layer is held, each screen shows its own hand's keys in their places on the board: the
# right screen under its header, the left screen below its status area. Columns are 13 px apart,
# the screen's width over five, and rows 15 px, with the board's column stagger and thumb drop at
# that scale. Neighbouring keys share a 1 px border, leaving 12 x 14 px inside each.

KEY_W, KEY_H = 13, 15
BOARD = yaml.safe_load(open(os.path.join(REPO, 'keymap_img', 'temper-board.yaml')))['keys']

# 3 x 5 capitals and digits, for legends of two or three characters. 1 is narrower, so F10-F12 fit.
F35 = {k: glyph(v.split()) for k, v in {
    'A': '.#. #.# ### #.# #.#', 'B': '##. #.# ##. #.# ##.', 'C': '.## #.. #.. #.. .##',
    'D': '##. #.# #.# #.# ##.', 'E': '### #.. ##. #.. ###', 'F': '### #.. ##. #.. #..',
    'G': '.## #.. #.# #.# .##', 'L': '#.. #.. #.. #.. ###', 'P': '##. #.# ##. #.. #..',
    'R': '##. #.# ##. #.# #.#', 'S': '.## #.. .#. ..# ##.', 'T': '### .#. .#. .#. .#.',
    'U': '#.# #.# #.# #.# ###', '0': '### #.# #.# #.# ###', '1': '.# ## .# .# .#',
    '2': '##. ..# .#. #.. ###', '3': '##. ..# .#. ..# ##.', '4': '#.# #.# ### ..# ..#',
    '5': '### #.. ##. ..# ##.', '6': '.## #.. ### #.# ###', '7': '### ..# .#. .#. .#.',
    '8': '### #.# ### #.# ###', '9': '### #.# ### ..# ##.',
}.items()}

# Media keys: a speaker with its mark, and transport controls
MUTE = glyph(["...#....", "..##....", "####.#.#", "####..#.", "####.#.#", "..##....", "...#...."])
VOL_UP = glyph(["...#....", "..##....", "####..#.", "####.###", "####..#.", "..##....", "...#...."])
VOL_DN = glyph(["...#....", "..##....", "####....", "####.###", "####....", "..##....", "...#...."])
PREV = glyph(["#..#..#", "#.##.##", "#######", "#.##.##", "#..#..#"])
NEXT = glyph(["#..#..#", "##.##.#", "#######", "##.##.#", "#..#..#"])
PLAY = glyph(["#...#.#", "##..#.#", "###.#.#", "##..#.#", "#...#.#"])
# Backspace and forward Delete, as on a Mac
BKSP = glyph(["...######", "..#.....#", ".#..#.#.#", "#....#..#", ".#..#.#.#", "..#.....#",
              "...######"])
DEL = [row[::-1] for row in BKSP]
# A screenshot of an area: a camera
SHOT = glyph(["...###...", "#########", "#..###..#", "#.#...#.#", "#.#...#.#", "#..###..#",
              "#########"])
# Home and End: to the start and end of the line
HOME = glyph(["#..#...", "#.##...", "#######", "#.##...", "#..#..."])
END = [row[::-1] for row in HOME]
TRI_U = glyph(["..#..", ".###.", "#####"])
TRI_D = TRI_U[::-1]
POWER = glyph(["....#....", ".##.#.##.", "#...#...#", "#...#...#", "#.......#", "#.......#",
               ".#.....#.", "..#####.."])
FLASH = glyph(["..###..", "..###..", "#######", ".#####.", "..###..", "...#...", ".......",
               "#######"])

N = None  # a key that does nothing on the layer
# Each hand's keys, in keymap order: three rows of five, then the thumbs, which these leave out.
# Thumbs are counted from the left on each hand: (outer, middle, inner) on the left hand and
# (inner, middle, outer) on the right. HELD is the thumb, or thumbs, that hold each layer.
KEYS = {
    'NUM': {
        'L': ['1', '2', '3', '4', '5', 'F1', 'F2', 'F3', 'F4', 'F5', 'F11', 'F12', N, N, MUTE],
        'R': ['6', '7', '8', '9', '0', 'F6', 'F7', 'F8', 'F9', 'F10',
              PREV, PLAY, NEXT, VOL_DN, VOL_UP],
    },
    'SYM': {
        'L': ['!', '@', '#', '$', '%', ('BT', '5'), N, DEL, N, N,
              ('BT', '4'), ('BT', '3'), ('BT', '2'), ('BT', '1'), N],
        'R': ['^', '&', '*', '(', ')', '[', ']', '`', '\\', ';', '{', '}', '~', '|', ':'],
    },
    'NAV': {
        'L': ['ESC', 'TAB', N, N, N, CTRL, OPT, CMD, SHIFT, N, N, SHOT, N, N, N],
        'R': [('PG', TRI_U), HOME, ARROW_U, END, BKSP,
              ('PG', TRI_D), rot(ARROW_U, 3), rot(ARROW_U, 2), rot(ARROW_U, 1), N,
              N, N, N, N, N],
    },
    'SYSTEM': {
        'L': [N, N, N, N, ('CLR', 'BT'), N, N, N, N, ('CLR', 'ALL'), N, N, N, N, FLASH],
        'R': [('USB', 'BT'), N, N, POWER, N, N, N, N, N, N, FLASH, N, N, N, N],
    },
}
# NAV's left hand on Windows: the same keys, drawn with Windows modifiers
NAV_WIN_L = ['ESC', 'TAB', N, N, N, CTRL, ALT, WIN, SHIFT, N, N, SHOT, N, N, N]
HELD = {'NUM': {'R': (0,)}, 'SYM': {'L': (2,)}, 'NAV': {'L': (0,)}, 'SYSTEM': {'L': (2,), 'R': (0,)}}


def key_places(hand):
    """Left edge, top and width of each of one hand's 18 keys, in keymap order, on a 68 px wide
    screen. The outer column takes the spare pixel at the screen's edge, so ESC fits."""
    top = min(k['y'] for k in BOARD[:10])
    down = KEY_H / 17  # px per mm down the board, where rows are 17 mm apart
    cols = range(5) if hand == 'L' else range(5, 10)
    outer = 0 if hand == 'L' else 4
    places = []
    for r in range(3):
        for i, c in enumerate(cols):
            x = 0 if (hand, i) == ('L', 0) else 1 + i * KEY_W
            places.append((x, round((BOARD[c]['y'] - top) * down) + r * KEY_H,
                           KEY_W + (i == outer)))
    # On the board the thumbs fan out past the inner column. Here they sit under the three inner
    # columns, keeping their drop.
    thumbs = BOARD[30:33] if hand == 'L' else BOARD[33:36]
    places += [(1 + (i + 2 if hand == 'L' else i) * KEY_W, round((k['y'] - top) * down), KEY_W)
               for i, k in enumerate(thumbs)]
    return places


def as_glyph(d, legend):
    """A legend as rows of pixels, and the height to centre it by (a descender doesn't count)."""
    if isinstance(legend, tuple):  # two lines, 2 px apart
        parts = [as_glyph(d, part) for part in legend]
        w = max(len(g[0]) for g, _ in parts)
        rows = []
        for i, (g, h) in enumerate(parts):
            pad = (w - len(g[0]) + 1) // 2
            rows += [[False] * pad + r + [False] * (w - len(r) - pad) for r in g[:h]]
            if i < len(parts) - 1:
                rows += [[False] * w] * 2
        return rows, len(rows)
    if isinstance(legend, list):
        return legend, len(legend)
    if len(legend) == 1:  # Silkscreen Bold, or one of PUNCT
        probe = Image.new('1', (16, 10), 0)
        w = label(probe, ImageDraw.Draw(probe), 0, 2, legend)
        px = probe.load()
        return [[bool(px[x, y]) for x in range(w)] for y in range(2, 8)], 5
    rows = [[] for _ in range(5)]
    for i, ch in enumerate(legend):
        for r, g in zip(rows, F35[ch]):
            r += ([False] if i else []) + g
    return rows, 5


def hand_keys(img, d, y0, hand, legends, held=()):
    """One hand's keys from row y0: outlines with legends, a dot for a key that does nothing, and
    the thumbs, with the held ones solid. Returns the row below the lowest key."""
    places = [(x, y0 + y, w) for x, y, w in key_places(hand)]
    for i, (x, y, w) in enumerate(places):
        box = [x, y, x + w, y + KEY_H]
        if i >= 15 and i - 15 in held:
            d.rectangle(box, fill=1)
        elif i >= 15 or legends[i] is not None:
            d.rectangle(box, outline=1)
    for i, (x, y, w) in enumerate(places[:15]):
        if legends[i] is None:
            d.point([(x + w // 2, y + KEY_H // 2)], fill=1)
            continue
        g, h = as_glyph(d, legends[i])
        inside, gw = w - 1, len(g[0])
        assert gw <= inside and h <= KEY_H - 1, legends[i]
        # When it can't be centred exactly, the odd pixel goes beside the edge with more ink, so
        # the lighter edge is the one that meets the border.
        left_ink = sum(r[0] for r in g)
        right_ink = sum(r[-1] for r in g)
        gx = (inside - gw + (left_ink >= right_ink)) // 2
        blit(img, g, x + 1 + gx, y + 1 + (KEY_H - h) // 2)
    return max(y for _, y, _ in places) + KEY_H + 1


def notes(img, d, y, lines):
    """Icon and text lines under the keys, saying what an icon does."""
    for icon, words in lines:
        if icon is not None:
            blit(img, icon, 1, y - (len(icon) - 5) // 2)
        label(img, d, 14, y, words, silk)
        y += 11
    return y


def legend_layer(name):
    """The right screen while a layer is held: its name, then the right hand's keys."""
    img, d = new()
    status_bar(img, d)
    header(d, name)
    bottom = hand_keys(img, d, 38, 'R', KEYS[name]['R'], HELD[name].get('R', ()))
    if name == 'SYSTEM':
        notes(img, d, bottom + 7, [(POWER, 'SOFT OFF'), (None, 'HOLD 2 SEC'),
                                    (FLASH, 'FLASH')])
    return img


def legend_num():
    return legend_layer('NUM')


def legend_sym():
    return legend_layer('SYM')


def legend_nav():
    return legend_layer('NAV')


def legend_system():
    return legend_layer('SYSTEM')


# ------------------------------------------------------------------------------- the left screen

LVF = {k: LvFont(os.path.join(SHIELD, 'fonts', f'lv_font_{k}.c'))
       for k in ('silkscreen_8', 'silkscreen_bold_8', 'jersey_1x')}


def lv_text(img, font, x, w, cap_y, align, s, fill=1):
    """draw_text() in draw.c: cap_y is the top of the capitals."""
    f = LVF[font]
    lw = f.width(s)
    last = f.glyphs[s[-1]]
    assert lw - (last[1] - (last[2] + last[4])) <= w, f'{s!r} in {font} is {lw} px, box is {w} px'
    if align == 'c':
        x += (w - lw) // 2
    elif align == 'r':
        x += w - lw
    f.draw(img, x, cap_y - f.cap_top(), s, fill)


def badge_x(g):
    """Where a glyph sits across a 12 px badge: centred, and when it can't be exactly, the odd
    pixel goes beside the edge with more ink, as badge_x() in widgets/status.c does."""
    left_ink, right_ink = sum(r[0] for r in g), sum(r[-1] for r in g)
    return 1 + (10 - len(g[0]) + (left_ink > right_ink)) // 2


def left_status(img, d, layer='BASE', l=87, r=92, charging=False, r_charging=False, usb=False,
                active=0, connected=(0,), bonded=(0, 1), held=(), caps=False, windows=False):
    """Portrait rows 0-67: what draw_status() in widgets/status.c draws."""
    for x, name, level, chg in ((0, 'L', l, charging), (36, 'R', r, r_charging)):
        if chg:
            # A charging half reads its battery as full whatever its charge, so show no level.
            blit(img, BOLT, x, 0)
            lv_text(img, 'silkscreen_8', x, 31, 0, 'r', 'CHG')
            continue
        lv_text(img, 'silkscreen_bold_8', x, 31, 0, 'l', name)
        lv_text(img, 'silkscreen_8', x, 31, 0, 'r', '--' if level < 0 else f'{level}%')
        for i in range(10):
            on = level >= 0 and i < (level + 5) // 10
            d.rectangle([x + i * 3, 8 if on else 11, x + i * 3 + 1, 11], fill=1)
    d.rectangle([0, 15, W - 1, 30], fill=1)
    lv_text(img, 'jersey_1x', 0, W, 18, 'c', layer, fill=0)
    if usb:
        d.rectangle([0, 34, W - 1, 45], fill=1)
        lv_text(img, 'silkscreen_bold_8', 0, W, 38, 'c', 'USB', fill=0)
    else:
        for i in range(5):
            x, y = 1 + i * 13, 34
            solid = i == active and i in connected
            if solid:
                d.rectangle([x, y, x + 11, y + 11], fill=1)
            elif i == active:
                d.rectangle([x, y, x + 11, y + 11], outline=1)
                d.rectangle([x + 1, y + 1, x + 10, y + 10], outline=1)
            elif i in connected:
                d.rectangle([x, y, x + 11, y + 11], outline=1)
            elif i in bonded:
                for k in range(0, 12, 2):
                    d.point([(x + k, y), (x + k, y + 11), (x, y + k), (x + 11, y + k)], fill=1)
            lv_text(img, 'silkscreen_bold_8', x, 12, y + 3, 'c', str(i + 1), fill=0 if solid else 1)
    gui, alt = (WIN, ALT) if windows else (CMD, OPT)
    for i, (name, g) in enumerate((('cmd', gui), ('opt', alt), ('ctrl', CTRL), ('shift', SHIFT),
                                   ('caps', CAPS))):
        x = i * 14
        on = name in held or (name == 'caps' and caps)
        d.rectangle([x, 50, x + 11, 62], fill=1) if on else d.rectangle([x, 50, x + 11, 62], outline=1)
        blit(img, g, x + badge_x(g), 50 + (13 - len(g)) // 2, ink=0 if on else 1)
    d.line([(0, 65), (W - 1, 65)], fill=1)


def left_combos(img, d):
    """Portrait rows 68-159: the base layer's combos, from config/temper.keymap."""
    text(d, (None, 71), 'COMBOS', silk_b, 'c')
    d.point([(x, 79) for x in range(0, W, 2)], fill=1)
    rows(img, d, 84, [
        ('Q W', 'TAB'),
        ('W E', 'ESC'),
        ('S D', 'CAPS'),
        ('U I', 'ENTER'),
        ('I O', 'BKSP'),
        ('O P', 'BKSP'),
        ('J K', '-'),
        ('K L', '='),
    ], step=9)


def left_screen(layer='BASE', windows=False, **kw):
    """The whole left screen: on Base the combos card, and while a layer is held the left hand's
    keys in its place. With windows, the WIN layer is on: Windows modifiers, and WIN for BASE."""
    img, d = new()
    shown = 'WIN' if windows and layer == 'BASE' else layer
    left_status(img, d, layer=shown, windows=windows, **kw)
    if layer == 'BASE':
        left_combos(img, d)
    else:
        keys = NAV_WIN_L if windows and layer == 'NAV' else KEYS[layer]['L']
        bottom = hand_keys(img, d, 70, 'L', keys, HELD[layer].get('L', ()))
        if layer == 'SYSTEM':
            notes(img, d, bottom + 4, [(FLASH, 'FLASH')])
    return img


# --------------------------------------------------------------------------------------- output

LEGENDS = [
    ('legend_base', legend_base, 20, 'Base: the name, the board, and the thumbs for each layer'),
    ('legend_num', legend_num, 20, 'NUM: numbers, F keys and media'),
    ('legend_sym', legend_sym, 20, 'SYM: symbols, Delete and Bluetooth slots'),
    ('legend_nav', legend_nav, 20, 'NAV: arrows, navigation and modifiers'),
    ('legend_system', legend_system, 20, 'SYSTEM: Bluetooth, USB, soft off and the bootloaders'),
    ('left_combos', left_screen, 68, 'Left screen below the status area: the combos'),
    ('left_num', lambda: left_screen('NUM'), 68, 'Left screen on NUM: the left hand\'s keys'),
    ('left_sym', lambda: left_screen('SYM'), 68, 'Left screen on SYM: the left hand\'s keys'),
    ('left_nav', lambda: left_screen('NAV'), 68, 'Left screen on NAV: the left hand\'s keys'),
    ('left_nav_win', lambda: left_screen('NAV', windows=True), 68,
     'Left screen on NAV with Windows keys: the left hand\'s keys'),
    ('left_system', lambda: left_screen('SYSTEM'), 68,
     'Left screen on SYSTEM: the left hand\'s keys'),
]


def to_native(portrait, top):
    """The part of a portrait screen from row top down, turned to the panel's landscape rows."""
    return portrait.crop((0, top, W, H)).transpose(Image.Transpose.ROTATE_270)


def encode(native):
    """LV_IMG_CF_INDEXED_1BIT rows, MSB first, ink as index 0."""
    w, h = native.size
    px = native.load()
    data = []
    for y in range(h):
        for bx in range((w + 7) // 8):
            b = 0
            for bit in range(8):
                x = bx * 8 + bit
                b = (b << 1) | (1 if x >= w or not px[x, y] else 0)
            data.append(b)
    return data


def decode(src, name):
    """Read an image back out of the generated C, to check the round trip."""
    body = re.search(name + r'_map\[\] = \{(.*?)\};', src, re.S).group(1)
    body = re.sub(r'#if.*?#endif', '', body, flags=re.S)
    data = [int(v, 16) for v in re.findall(r'0x[0-9a-f]{2}', body)]
    hdr = re.search(r'lv_img_dsc_t ' + name + r' = \{(.*?)\};', src, re.S).group(1)
    w = int(re.search(r'header\.w = (\d+)', hdr).group(1))
    h = int(re.search(r'header\.h = (\d+)', hdr).group(1))
    img = Image.new('1', (w, h))
    px = img.load()
    stride = (w + 7) // 8
    for y in range(h):
        for x in range(w):
            px[x, y] = 0 if (data[y * stride + x // 8] >> (7 - x % 8)) & 1 else 1
    return img


def c_image(name, comment, native):
    data = encode(native)
    lines = ['        ' + ', '.join(f'0x{b:02x}' for b in data[i:i + 18]) + ','
             for i in range(0, len(data), 18)]
    attr = 'LV_ATTRIBUTE_IMG_' + name.upper()
    return f'''/* {comment} */
#ifndef {attr}
#define {attr}
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST {attr} uint8_t {name}_map[] = {{
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
        0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
        0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#else
        0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
        0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#endif

{chr(10).join(lines)}
}};

const lv_img_dsc_t {name} = {{
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = {native.width},
    .header.h = {native.height},
    .data_size = {8 + len(data)},
    .data = {name}_map,
}};
'''


def write_art():
    parts = ['''/*
 * Generated by art/screens.py. Do not edit by hand; edit art/screens.py and re-run it.
 *
 * SPDX-License-Identifier: MIT
 */

#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif
''']
    natives = {name: to_native(fn(), top) for name, fn, top, _ in LEGENDS}
    for name, _, _, comment in LEGENDS:
        parts.append(c_image(name, comment, natives[name]))
    src = '\n'.join(parts)
    for name, native in natives.items():
        back = decode(src, name)
        assert back.size == native.size and back.tobytes() == native.tobytes(), name
    with open(os.path.join(SHIELD, 'widgets', 'legend_art.c'), 'w') as f:
        f.write(src)


def write_glyphs():
    out = ['/*', ' * Generated by art/screens.py. Do not edit by hand.', ' *',
           ' * SPDX-License-Identifier: MIT', ' */', '', '#pragma once', '',
           '#include "draw.h" // struct glyph', '']
    for name, g in (('glyph_cmd', CMD), ('glyph_opt', OPT), ('glyph_win', WIN),
                    ('glyph_alt', ALT), ('glyph_ctrl', CTRL),
                    ('glyph_shift', SHIFT), ('glyph_caps', CAPS), ('glyph_bolt', BOLT)):
        w = len(g[0])
        out.append(f'static const uint16_t {name}_rows[] = {{')
        for r in g:
            bits = sum(1 << (w - 1 - x) for x, on in enumerate(r) if on)
            out.append(f'    0x{bits:04x}, // {"".join("#" if b else "." for b in r)}')
        out += ['};', f'static const struct glyph {name} = {{{w}, {len(g)}, {name}_rows}};', '']
    with open(os.path.join(SHIELD, 'widgets', 'status_glyphs.h'), 'w') as f:
        f.write('\n'.join(out))


def framed(screen, scale=4, pad=14, radius=18, border=3):
    """Black on white, scaled with hard pixel edges, in a thin rounded bezel."""
    face = Image.new('L', screen.size, 255)
    face.paste(0, mask=screen.convert('L'))
    face = face.resize((screen.width * scale, screen.height * scale), Image.NEAREST)
    w, h = face.width + 2 * (pad + border), face.height + 2 * (pad + border)
    ss = 4
    big = Image.new('L', (w * ss, h * ss), 255)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=radius * ss,
                                          outline=0, width=border * ss)
    img = big.resize((w, h), Image.LANCZOS)
    img.paste(face, (pad + border, pad + border))
    return img


def write_images():
    out = os.path.join(REPO, 'docs', 'screens')
    os.makedirs(out, exist_ok=True)
    screens = {
        'left.png': left_screen(),
        'left-num.png': left_screen('NUM'),
        'left-sym.png': left_screen('SYM'),
        'left-nav.png': left_screen('NAV'),
        'left-system.png': left_screen('SYSTEM'),
        'left-win.png': left_screen(windows=True, active=2, connected=(2,), bonded=(0, 1, 2)),
        'left-nav-win.png': left_screen('NAV', windows=True, active=2, connected=(2,),
                                        bonded=(0, 1, 2), held=('cmd',)),
        'right-base.png': legend_base(),
        'right-num.png': legend_num(),
        'right-sym.png': legend_sym(),
        'right-nav.png': legend_nav(),
        'right-system.png': legend_system(),
    }
    for name, screen in screens.items():
        framed(screen).save(os.path.join(out, name), optimize=True)
    return screens


if __name__ == '__main__':
    write_art()
    write_glyphs()
    screens = write_images()
    print('wrote legend_art.c, status_glyphs.h and docs/screens:', ', '.join(screens))
