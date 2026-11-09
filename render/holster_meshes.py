# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["cadquery", "shapely", "pyyaml", "fonttools", "brotli", "trimesh", "numpy"]
# ///
"""The faceted holster and the right half, as STLs for holster_scene.py. Run: uv run holster_meshes.py MESH_DIR"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "case"))
import holster as H
from holster import *
import export_web as W
OUT = sys.argv[1].rstrip("/") + "/"
h = Holster()
top, back = h.split(h.body(faceted=True))
back = back.cut(h.name_plate())
case, caps, stems, pcb, usb, chips = W.keyboard_parts(h)
parts = {
    "top": top, "back": back, "clip": h.clip(steel=True), "spine": h.spine(),
    "screws": h.screws().add(h.joins()),
    "case": case, "caps": caps, "stems": stems, "pcb": pcb, "usb": usb, "chips": chips,
}
for name, part in parts.items():
    cq.exporters.export(part, OUT + name + ".stl", tolerance=0.015, angularTolerance=0.08)
    print(name, "ok")
