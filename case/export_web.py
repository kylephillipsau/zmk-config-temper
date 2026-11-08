#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["cadquery", "shapely", "pyyaml", "fonttools", "brotli"]
# ///
"""Build the 3D viewer: turns the CAD parts into compact meshes and fills in viewer/template.html.

    uv run case/export_web.py     # writes case/viewer/index.html and out/short-temper-holster.glb
"""
import base64
import io
import json
import math
import struct
import sys
from pathlib import Path

import cadquery as cq
import yaml
from fontTools import subset
from fontTools.ttLib import TTFont
from shapely.geometry import box as sbox

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import holster as H  # noqa: E402

UNITS = 50  # mesh positions are stored as 16-bit integers, in 1/50 mm
CAP_BOTTOM, STEM = 12.0, 14.0


def keyboard_parts(h):
    """A display model of the right half, in its case. The keys come from the real PCB."""
    board = yaml.safe_load((HERE.parent / "keymap_img/temper-board.yaml").read_text(encoding="utf-8"))
    inner_edge = min(p[0] for p in board["outlines"][1])
    right = list(range(5, 10)) + list(range(15, 20)) + list(range(25, 30)) + [33, 34, 35]
    caps, stems = None, None
    for index in right:
        k = board["keys"][index]
        x, y = k["x"] - inner_edge + H.BOARD_X, H.BOARD_Y + H.BOARD_H - k["y"]
        angle = -k["r"]
        cap = (
            cq.Workplane("XY").workplane(offset=CAP_BOTTOM).rect(17.5, 16.5).extrude(H.KEYTOP_H - CAP_BOTTOM)
            .faces(">Z").edges().chamfer(0.9)
            .rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, 0))
        )
        stem = H.block(-STEM / 2, STEM / 2, -STEM / 2, STEM / 2, H.CASE_H, CAP_BOTTOM + 0.2).rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, 0))
        caps = cap if caps is None else caps.add(cap)
        stems = stem if stems is None else stems.add(stem)
    # The controller sits in a well in the case, at the top of the inner edge
    cx, cy = H.USB_X, H.BOARD_Y + H.BOARD_H - 28.35
    case = h.keyboard().cut(H.block(cx - 10, cx + 10, cy - 18.5, cy + 19, H.CASE_H - 4.5, H.CASE_H + 2))
    pcb = H.block(cx - 9, cx + 9, cy - 16.5, cy + 16.5, H.CASE_H - 3.5, H.CASE_H - 1.9)
    usb = H.block(cx - 4.5, cx + 4.5, cy + 11.5, cy + 18.2, H.CASE_H - 1.9, H.CASE_H + 1.3)
    chips = H.block(cx - 5, cx + 5, cy - 6, cy + 6, H.CASE_H - 1.9, H.CASE_H - 1.0)
    return case, caps, stems, pcb, usb, chips


def mesh(work, tolerance=0.06, angular=0.3):
    vertices, triangles = [], []
    for shape in work.vals():
        v, t = shape.tessellate(tolerance, angular)
        base = len(vertices)
        vertices += [(p.x, p.y, p.z) for p in v]
        triangles += [(a + base, b + base, c + base) for a, b, c in t]
    position = b"".join(struct.pack("<3h", *(round(c * UNITS) for c in p)) for p in vertices)
    index = struct.pack(f"<{len(triangles) * 3}I", *[i for t in triangles for i in t])
    return {
        "vertices": len(vertices),
        "triangles": len(triangles),
        "position": base64.b64encode(position).decode(),
        "index": base64.b64encode(index).decode(),
    }


def font_data():
    font = TTFont(HERE.parent / "keymap_img/fonts/osifont-lgpl3fe.ttf")
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    keep = subset.Subsetter(options)
    keep.populate(unicodes=list(range(0x20, 0x7F)) + [0xB0, 0xD7, 0x2013])
    keep.subset(font)
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode()


def main():
    h = H.Holster()
    body, clip = h.body(), h.clip(steel=True)
    top, back = h.split(h.body(faceted=True))
    back = back.cut(h.name_plate())
    fit = h.test_fit(body)
    case, caps, stems, pcb, usb, chips = keyboard_parts(h)
    blade, bolts = h.spine(), h.screws()

    # Every key should sit inside the traced case
    worst = 0.0
    for shape in caps.vals():
        bb = shape.BoundingBox()
        for x in (bb.xmin, bb.xmax):
            for y in (bb.ymin, bb.ymax):
                worst = max(worst, h.case.exterior.distance(sbox(x - 0.01, y - 0.01, x + 0.01, y + 0.01)) if not h.case.buffer(0).contains(sbox(x - 0.01, y - 0.01, x + 0.01, y + 0.01)) else 0)
    print(f"keys reach {worst:.1f} mm past the case (bounding boxes, so rotated keys read high)")

    parts = {
        "holster": mesh(body), "faceted": mesh(top), "back": mesh(back), "joins": mesh(h.joins()), "fit": mesh(fit), "clip": mesh(clip), "spine": mesh(blade), "screws": mesh(bolts),
        "case": mesh(case), "caps": mesh(caps), "stems": mesh(stems), "pcb": mesh(pcb),
        "usb": mesh(usb), "chips": mesh(chips),
    }
    for name, part in parts.items():
        print(f"{name}: {part['triangles']} triangles, {(len(part['position']) + len(part['index'])) // 1024} KB")

    force, _ = h.spring_check()
    def facts(*parts):
        # Both shapes have the same footprint, so take it from the plain one, and the depth from all the parts
        bb = H.solid(body).BoundingBox()
        boxes = [H.solid(part).BoundingBox() for part in parts]
        depth = max(b.zmax for b in boxes) - min(b.zmin for b in boxes)
        return {"size": f"{bb.xlen:.0f} × {bb.ylen:.0f} × {depth:.0f} mm", "grams": round(sum(H.printed_grams(part) for part in parts))}

    data = {
        "units": UNITS,
        "parts": parts,
        "leg": {"x": h.leg_x, "y": h.leg_y, "z": h.leg_z, "r": H.THIGH_R, "tilt": H.TILT, "edge": h.edge_s, "slant": H.POCKET_ANGLE, "clipW": h.clip_w},
        "facts": {"force": round(force), "plain": facts(body), "faceted": facts(top, back)},
    }
    template = (HERE / "viewer/template.html").read_text(encoding="utf-8")
    page = template.replace("/*FONT*/", font_data()).replace("/*DATA*/", json.dumps(data, separators=(",", ":")))
    (HERE / "viewer/index.html").write_text(page, encoding="utf-8")
    print(f"viewer/index.html: {len(page) / 1048576:.1f} MB")

    assembly = cq.Assembly(name="short-temper-holster")
    for name, part, colour in (
        ("holster", body, (0.16, 0.17, 0.18)), ("clip", clip, (0.45, 0.46, 0.48)), ("spine", blade, (0.75, 0.76, 0.78)),
        ("case", case, (0.08, 0.08, 0.09)), ("keycaps", caps, (0.13, 0.13, 0.14)),
    ):
        assembly.add(part, name=name, color=cq.Color(*colour))
    H.OUT.mkdir(exist_ok=True)
    assembly.save(str(H.OUT / "short-temper-holster.glb"), "GLTF", tolerance=0.06, angularTolerance=0.3)


if __name__ == "__main__":
    main()
