# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["cadquery", "shapely", "pyyaml", "fonttools", "brotli", "trimesh", "numpy"]
# ///
"""Both halves for desk.py and export_glb.py: the case with its controller well running down to the
screen header, the caps and stems, a USB-C receptacle and the header socket. Writes STLs (right
half, then mirrored) and controller.json with where each part sits.

    uv run render/make_meshes.py MESH_DIR
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "case"))
import cadquery as cq
import holster as H
import export_web as W
import trimesh, numpy as np

OUT = sys.argv[1]
h = H.Holster()
cx, cy = H.USB_X, H.BOARD_Y + H.BOARD_H - 28.35          # the controller's centre, as in export_web
PCB = (cx - 9, cx + 9, cy - 16.5, cy + 16.5, H.CASE_H - 3.5, H.CASE_H - 1.9)
WELL_FLOOR = H.CASE_H - 4.5
# The photos show the well running on below the board to a 5-hole header for the nice!view
case = h.keyboard().cut(H.block(cx - 10, cx + 10, cy - 23.0, cy + 19, WELL_FLOOR, H.CASE_H + 2))

def stadium(w, t):
    return cq.Workplane("XZ").rect(w, t).extrude(1).edges("|Y").fillet(t / 2 - 0.01)

# USB-C receptacle: a 8.94 x 3.26 mm stadium shell, open at the front, with a tongue inside
L_USB, WALL = 7.35, 0.25
front = PCB[3] + 0.9
z0 = PCB[5]
outer = cq.Workplane("XZ", origin=(cx, front, z0 + 1.63)).rect(8.94, 3.26).extrude(L_USB).edges("|Y").fillet(1.6)
inner = cq.Workplane("XZ", origin=(cx, front + 0.01, z0 + 1.63)).rect(8.94 - 2 * WALL, 3.26 - 2 * WALL).extrude(L_USB - 0.6).edges("|Y").fillet(1.6 - WALL)
shell = outer.cut(inner)
tongue = cq.Workplane("XY").box(6.69, 4.45, 0.7).translate((cx, front - 0.9 - 4.45 / 2 - 0.0, z0 + 1.63))
contacts = None
for i in range(12):
    c = cq.Workplane("XY").box(0.25, 3.2, 0.03).translate((cx - 2.75 + i * 0.5, front - 1.2 - 1.6, z0 + 1.63 + 0.365))
    contacts = c if contacts is None else contacts.add(c)

# The header socket under the board: 5 holes at 2.54 mm, black
sock_y = cy - 16.5 - 3.6
socket = cq.Workplane("XY").box(12.7, 2.5, 3.0).translate((cx, sock_y, WELL_FLOOR + 1.5))
for i in range(5):
    socket = socket.cut(cq.Workplane("XY").box(1.0, 1.0, 2.5).translate((cx - 5.08 + i * 2.54, sock_y, WELL_FLOOR + 3.0)))
pcb = H.block(*PCB)

_, caps, stems, _, _, _ = W.keyboard_parts(h)
parts = {"caps": caps, "stems": stems, "case": case, "pcb": pcb, "usb_shell": shell, "usb_tongue": tongue, "usb_contacts": contacts, "socket": socket}
yc = None
for name, part in parts.items():
    path = f"{OUT}/{name}_R.stl"
    cq.exporters.export(part, path, tolerance=0.01, angularTolerance=0.05)
m0 = trimesh.load(f"{OUT}/case_R.stl"); yc = (m0.bounds[0][1] + m0.bounds[1][1]) / 2
for name in parts:
    m = trimesh.load(f"{OUT}/{name}_R.stl"); m.apply_translation([0, -yc, 0]); m.export(f"{OUT}/{name}_R.stl")
    l = m.copy(); l.apply_transform(np.diag([-1, 1, 1, 1])); l.export(f"{OUT}/{name}_L.stl")
    print(name, np.round(m.bounds, 2).tolist())
json.dump({"pcb": [PCB[0], PCB[1], PCB[2] - yc, PCB[3] - yc, PCB[4], PCB[5]], "yc": yc}, open(f"{OUT}/controller.json", "w"))
print("pcb", PCB, "yc", yc)
