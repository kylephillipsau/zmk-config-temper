"""A scene the stills use, as a GLB for the web viewer on kyle.au.

    Blender -b -P render/export_glb.py -- render/mesh render/out/short-temper.glb
    Blender -b -P render/export_glb.py -- render/holster-mesh render/out/short-temper-holster.glb holster

The first is both halves as desk.py builds them, one mesh per part. The second is the
faceted holster as holster_scene.py builds it, one mesh per part, and each part's node carries
"explode": how far it moves in the exploded view, in metres, y up.

glTF carries a Principled BSDF's colour, roughness and metalness and an image plugged straight into
them, so this swaps the procedural bevels and bumps for plain values, and the controller's textures
for a colour map and a metal and roughness map.
"""
import bpy, sys, os
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
MESH, GLB = os.path.abspath(argv[0]), os.path.abspath(argv[1])
SCENE = argv[2] if len(argv) > 2 else "desk"
SOURCE = {"desk": "desk.py", "holster": "holster_scene.py"}[SCENE]
HERE = os.path.dirname(os.path.abspath(__file__))
# Darks a little lighter than the stills, which light them far harder than a web page can
LIFT = float(os.environ.get("LIFT", "2.0"))

src = open(os.path.join(HERE, SOURCE)).read()
src = src[:src.index("\nfor name in SHOTS:")]
sys.argv = [sys.argv[0], "--", MESH, os.path.dirname(GLB), "16", "1", ""]
ns = {"__name__": SCENE, "__file__": os.path.join(HERE, SOURCE)}
exec(compile(src, SOURCE, "exec"), ns)
sc, rig, groups = ns["build"]()


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
            # No higher than 0.03, so blacks that are already lighter stay as they are
            k = max(1.0, min(LIFT, 0.03 / max(r, g, bl)))
            c.default_value = (r * k, g * k, bl * k, a)


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


if SCENE == "holster":
    # The same caps as the desk model, which the holster stills light from further off
    principled(bpy.data.materials["Keycap PBT"]).inputs["Base Color"].default_value = (0.009, 0.009, 0.0095, 1)

for m in bpy.data.materials:
    if not m.node_tree: continue
    if m.name == "Controller top": controller_top(m)
    else: plain(m)



def join(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects: o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1: bpy.ops.object.join()
    objects[0].name = objects[0].data.name = name


# Bake the modifiers first
bpy.ops.object.select_all(action="DESELECT")
model = [o for o in bpy.data.collections["model"].all_objects if o.type == "MESH"]
for o in model: o.select_set(True)
bpy.context.view_layer.objects.active = model[0]

if SCENE == "desk":
    # Empty nodes at the parts the viewer's close-ups look at, named "anchor <part>"
    for name in ("controller top L", "controller top R"):
        ob = bpy.data.objects[name]
        centre = sum((ob.matrix_world @ Vector(c) for c in ob.bound_box), Vector()) / 8
        e = bpy.data.objects.new("anchor " + name, None); sc.collection.objects.link(e); e.location = centre
    bpy.ops.object.convert(target="MESH")
    # One mesh per part, both halves together, so the viewer can show a part on its own
    PARTS = {"case": ["case_"], "keycaps": ["caps_"], "switches": ["stems_"],
             "controller": ["pcb_", "controller top ", "usb_", "socket_"]}
    for part, prefixes in PARTS.items():
        model = [o for o in bpy.data.collections["model"].all_objects if o.type == "MESH"]
        join([o for o in model if any(o.name.startswith(x) for x in prefixes)], part)
    left = [o.name for o in bpy.data.collections["model"].all_objects if o.type == "MESH" and o.name not in PARTS]
    assert not left, f"objects in no part: {left}"
else:
    bpy.ops.object.convert(target="MESH")
    for name, group in groups.items():
        join([o for o in group.children if o.type == "MESH"], name.capitalize())
        x, y, z = group["move"]
        group["explode"] = [x, z, -y]   # glTF is y up
        del group["move"]

os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=GLB, export_format="GLB", export_apply=True, export_yup=True,
    export_cameras=False, export_lights=False, export_extras=SCENE == "holster",
    export_meshopt_compression_enable=True,
)
tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
print("wrote", GLB, os.path.getsize(GLB), "bytes,", tris, "triangles")
