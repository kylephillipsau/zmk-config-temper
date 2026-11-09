"""Both halves as desk.py builds them, as a GLB for the web viewer on kyle.au.

    Blender -b -P render/export_glb.py -- render/mesh render/out/short-temper.glb

glTF carries a Principled BSDF's colour, roughness and metalness and an image plugged straight into
them, so this swaps the procedural bevels and bumps for plain values, and the controller's textures
for a colour map and a metal and roughness map. Each half is joined into one mesh.
"""
import bpy, sys, os
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
MESH, GLB = os.path.abspath(argv[0]), os.path.abspath(argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
# Darks a little lighter than the stills, which light them far harder than a web page can
LIFT = float(os.environ.get("LIFT", "2.0"))

src = open(os.path.join(HERE, "desk.py")).read()
src = src[:src.index("\nfor name in SHOTS:")]
sys.argv = [sys.argv[0], "--", MESH, os.path.dirname(GLB), "16", "1", ""]
ns = {"__name__": "desk", "__file__": os.path.join(HERE, "desk.py")}
exec(compile(src, "desk.py", "exec"), ns)
sc, rig, halves = ns["build"]()


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def plain(m):
    """Keep only what glTF carries: drop the bevel, grain and anisotropy."""
    nt = m.node_tree; b = principled(m)
    for n in list(nt.nodes):
        if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL", "TEX_IMAGE", "SEPARATE_COLOR"):
            nt.nodes.remove(n)
    for key in ("Coat Weight", "Anisotropic"):
        if key in b.inputs: b.inputs[key].default_value = 0.0
    c = b.inputs["Base Color"]
    if not c.is_linked and b.inputs["Metallic"].default_value < 0.5:
        r, g, bl, a = c.default_value
        if max(r, g, bl) < 0.05:
            c.default_value = (r * LIFT, g * LIFT, bl * LIFT, a)


def image(name, rgb, data=False):
    """A new 8-bit image from RGB in 0..1: linear light, stored as sRGB, or raw data."""
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    if data: img.colorspace_settings.name = "Non-Color"
    else: rgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(np.clip(rgb, 0, 1), 1 / 2.4) - 0.055)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = rgb[::-1]
    img.pixels.foreach_set(px.ravel()); img.file_format = "PNG"; img.pack()
    return img


def pixels(path):
    img = bpy.data.images.load(path); w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[::-1]


def controller_top(m):
    """Colour as is; gold where pcb_metal.png is white, with the roughness desk.py maps from it."""
    nt = m.node_tree; b = principled(m)
    for n in list(nt.nodes):
        if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"): nt.nodes.remove(n)
    col = nt.nodes.new("ShaderNodeTexImage"); col.image = bpy.data.images.load(os.path.join(MESH, "pcb_colour.png"))
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    metal = pixels(os.path.join(MESH, "pcb_metal.png"))[..., 0]
    mr = np.zeros(metal.shape + (3,), np.float32)
    mr[..., 1] = 0.42 + (0.2 - 0.42) * metal; mr[..., 2] = metal
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = image("controller metal roughness", mr, data=True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])


for m in bpy.data.materials:
    if not m.node_tree: continue
    if m.name == "Controller top": controller_top(m)
    else: plain(m)

# Empty nodes at the parts the viewer's close-ups look at, named "anchor <part>"
ANCHORS = ['controller top L', 'controller top R']
for name in ANCHORS:
    ob = bpy.data.objects[name]
    centre = sum((ob.matrix_world @ Vector(c) for c in ob.bound_box), Vector()) / 8
    e = bpy.data.objects.new("anchor " + name, None); sc.collection.objects.link(e); e.location = centre

# Bake the modifiers, then join each half into one mesh
bpy.ops.object.select_all(action="DESELECT")
model = [o for o in bpy.data.collections["model"].all_objects if o.type == "MESH"]
for o in model: o.select_set(True)
bpy.context.view_layer.objects.active = model[0]
bpy.ops.object.convert(target="MESH")
for half, root in halves.items():
    parts = [o for o in bpy.data.collections["model"].all_objects if o.type == "MESH" and (o.parent == root or o.parent and o.parent.parent == root)]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    parts[0].name = parts[0].data.name = {"L": "Left half", "R": "Right half"}[half]

os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=GLB, export_format="GLB", export_apply=True, export_yup=True,
    export_cameras=False, export_lights=False, export_extras=False,
    export_meshopt_compression_enable=True,
)
tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
print("wrote", GLB, os.path.getsize(GLB), "bytes,", tris, "triangles")
