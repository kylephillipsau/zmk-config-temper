"""Studio stills of the Short Temper holster. Run: blender -b -P scene.py -- MESH_DIR OUT_DIR WIDTH SAMPLES SHOT[,SHOT]"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index("--") + 1:]
MESH, OUT, WIDTH, SAMPLES, SHOTS = argv[0], argv[1], int(argv[2]), int(argv[3]), argv[4].split(",")
HEIGHT = round(WIDTH / 2.39)
MM = 0.001
BEVEL = float(os.environ.get("BEVEL", "0.00035"))
LAYERS = os.environ.get("LAYERS", "0") == "1"  # 0.2 mm print lines alias into streaks at these distances
EXPOSURE = float(os.environ.get("EXPOSURE", "-4.5"))
POOL = float(os.environ.get("POOL", "1.0"))
SHEEN = float(os.environ.get("SHEEN", "1.0"))
KEY = float(os.environ.get("KEY", "1.0"))  # scales the key and the strip above
RIM = float(os.environ.get("RIM", "0.25"))
MATTE = float(os.environ.get("MATTE", "0.006"))  # the black's colour
ROUGH = float(os.environ.get("ROUGH", "0.45"))
CENTRE = Vector((58.0, 48.0, 0.0)) * MM

GROUPS = {
    "keyboard": ((0, 0, 84), ["case", "caps", "stems", "pcb", "usb", "chips"]),
    "screws": ((0, 0, 44), ["screws"]),
    "top": ((0, 0, 0), ["top"]),
    "back": ((0, 0, -30), ["back"]),
    "clip": ((0, 0, -68), ["clip"]),
    "spine": ((0, -38, -98), ["spine"]),
}

def material(name, colour, rough, metal=0.0, spec=0.5, layers=None, grain=None, coat=0.0, layer_axis="Z", turn=0.0, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs: b.inputs[key].default_value = spec; break
    if coat and "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    if sheen and "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
        if "Sheen Roughness" in b.inputs: b.inputs["Sheen Roughness"].default_value = 0.4
    height = None
    if layers and LAYERS:  # print layers along Z, in object space
        tc = nt.nodes.new("ShaderNodeTexCoord"); w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"; w.bands_direction = layer_axis; w.inputs["Scale"].default_value = 2 * math.pi / (20 * layers * MM)
        w.inputs["Distortion"].default_value = 0.0
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(turn))
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], w.inputs["Vector"]); height = w.outputs["Fac"]
    if grain:  # fine surface texture
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = grain; n.inputs["Detail"].default_value = 6
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        if height is None: height = n.outputs["Fac"]
        else:
            mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "ADD"
            nt.links.new(height, mix.inputs[0]); sc = nt.nodes.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 0.5
            nt.links.new(n.outputs["Fac"], sc.inputs[0]); nt.links.new(sc.outputs[0], mix.inputs[1]); height = mix.outputs[0]
    bevel = nt.nodes.new("ShaderNodeBevel"); bevel.samples = 8; bevel.inputs["Radius"].default_value = BEVEL
    if height is not None:
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.18
        bump.inputs["Distance"].default_value = 0.00004
        nt.links.new(bevel.outputs["Normal"], bump.inputs["Normal"])
        nt.links.new(height, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    else:
        nt.links.new(bevel.outputs["Normal"], b.inputs["Normal"])
    return m

MATS = {}

def make_materials():
    MATS.update({
    "top": material("Matte black PETG", (MATTE, MATTE, MATTE * 1.08), ROUGH, spec=0.35, layers=0.2),
    "back": material("Matte black PETG, back", (MATTE, MATTE, MATTE * 1.08), ROUGH, spec=0.35, layers=0.2),
    # The clip prints on its long edge, so its layers run across its width
    "clip": material("Matte black nylon", (MATTE, MATTE, MATTE * 1.08), ROUGH, spec=0.35, layers=0.2, layer_axis="X", turn=20.0),
    "spine": material("Spring steel", (0.62, 0.62, 0.64), 0.26, metal=1.0),
    "screws": material("Black oxide", (0.035, 0.035, 0.037), 0.33, metal=1.0),
    "case": material("Case PLA", (0.014, 0.014, 0.016), 0.6, layers=0.2),
    "caps": material("Keycap PBT", (0.03, 0.03, 0.032), 0.78, spec=0.22, grain=9000),
    "stems": material("Switch", (0.01, 0.01, 0.011), 0.5),
    "pcb": material("PCB", (0.012, 0.012, 0.013), 0.45),
    "usb": material("USB shell", (0.75, 0.75, 0.76), 0.22, metal=1.0),
    "chips": material("Chips", (0.01, 0.01, 0.01), 0.4),
})

def load(name):
    bpy.ops.wm.stl_import(filepath=os.path.join(MESH, name + ".stl"), global_scale=MM)
    ob = bpy.context.selected_objects[0]; ob.name = name
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-7)
    bm.to_mesh(ob.data); bm.free()
    ob.data.shade_smooth()
    try: ob.data.set_sharp_from_angle(angle=math.radians(32))
    except Exception as e: print("smooth by angle failed", e)
    # Weight normals by face area, so big flat faces stay flat beside small rounded ones
    try:
        wn = ob.modifiers.new("weighted", "WEIGHTED_NORMAL"); wn.mode = "FACE_AREA"; wn.keep_sharp = True
    except Exception as e: print("weighted normals failed", e)
    ob.data.materials.clear(); ob.data.materials.append(MATS[name])
    return ob

def look(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_materials()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("METAL", "NONE"):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            for d in prefs.devices: d.use = True
            break
        except Exception as e: print("device", kind, e)
    sc.cycles.device = "GPU" if prefs.compute_device_type != "NONE" else "CPU"
    print("devices", [(d.name, d.type, d.use) for d in prefs.devices], sc.cycles.device)
    sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 10; sc.cycles.glossy_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = WIDTH, HEIGHT
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        for look_name in ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Punchy", "Punchy"):
            try: sc.view_settings.look = look_name; break
            except Exception: pass
    except Exception as e: print("view", e)
    sc.view_settings.exposure = EXPOSURE
    print("view", sc.view_settings.view_transform, sc.view_settings.look)
    world = bpy.data.worlds.new("World"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0025, 0.0027, 0.003, 1)
    global MODEL, GROUND
    MODEL = bpy.data.collections.new("model"); sc.collection.children.link(MODEL)
    GROUND = bpy.data.collections.new("ground"); sc.collection.children.link(GROUND)
    rig = bpy.data.objects.new("rig", None); sc.collection.objects.link(rig)
    nodes = {}
    for g, (move, parts) in GROUPS.items():
        e = bpy.data.objects.new(g, None); sc.collection.objects.link(e); e.parent = rig
        e["move"] = [v * MM for v in move]
        for p in parts:
            ob = load(p); ob.parent = e; ob.location = -CENTRE
            for c in list(ob.users_collection): c.objects.unlink(ob)
            MODEL.objects.link(ob)
        nodes[g] = e
    return sc, rig, nodes

def floor(sc, z, rough=0.24, shade=0.03):
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, z)); f = bpy.context.object; f.name = "floor"
    m = bpy.data.materials.new("Floor"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (shade, shade, shade * 1.06, 1); b.inputs["Roughness"].default_value = rough
    f.data.materials.append(m)
    for c in list(f.users_collection): c.objects.unlink(f)
    GROUND.objects.link(f)
    return f

def area(sc, name, loc, target, size, energy, colour=(1, 1, 1), size_y=None, spread=None):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.color = colour
    if size_y: l.shape = "RECTANGLE"; l.size = size; l.size_y = size_y
    else: l.size = size
    if spread is not None: l.spread = math.radians(spread)
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc; look(o, target)
    o.visible_camera = False
    o.light_linking.receiver_collection = MODEL
    return o

def spot(sc, name, loc, target, energy, size_deg, blend=1.0, colour=(1, 1, 1), radius=0.05):
    l = bpy.data.lights.new(name, "SPOT"); l.energy = energy * POOL; l.spot_size = math.radians(size_deg); l.spot_blend = blend; l.color = colour
    l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc; look(o, target)
    o.light_linking.receiver_collection = GROUND
    return o

def camera(sc, loc, target, lens, fstop, focus):
    c = bpy.data.cameras.new("cam"); c.lens = lens; c.sensor_width = 36
    c.dof.use_dof = fstop is not None
    if fstop: c.dof.aperture_fstop = fstop
    if focus: c.dof.focus_distance = focus
    o = bpy.data.objects.new("cam", c); sc.collection.objects.link(o); o.location = loc; look(o, target); sc.camera = o
    c.clip_start = 0.005; c.clip_end = 20
    return o

WARM, COOL = (1.0, 0.84, 0.68), (0.70, 0.83, 1.0)

def studio(sc, t, z_floor, key=30.0, rim=1.0, halo=(0.0, 0.16)):
    """Strip lights that draw the edges of black plastic, a soft key, and a pool of light on the floor behind."""
    t = Vector(t)
    area(sc, "key", t + Vector((-0.30, -0.28, 0.42)), t, 0.40, key * KEY, WARM, 0.22)
    area(sc, "rim right", t + Vector((0.30, 0.34, 0.12)), t, 0.035, 110 * rim * RIM, COOL, 0.7, spread=30)
    area(sc, "rim left", t + Vector((-0.34, 0.26, 0.10)), t, 0.035, 70 * rim * RIM, WARM, 0.6, spread=30)
    area(sc, "top strip", t + Vector((0.0, 0.05, 0.45)), t, 0.6, 26 * rim * KEY, (1, 1, 1), 0.03)
    spot(sc, "halo", t + Vector((halo[0], halo[1] + 0.05, 0.75)), (t.x + halo[0], t.y + halo[1] + 0.12, z_floor), 7000, 26, 1.0, (0.86, 0.9, 1.0), 0.3)
    floor(sc, z_floor)
    cam = sc.camera.location; back = (cam - t).normalized()
    area(sc, "sheen", cam + back * 0.35 + Vector((0, 0, 0.12)), t, 1.0, 250 * SHEEN, (1, 1, 1), 0.6)

def shot_hero(sc, rig, nodes):
    rig.rotation_euler = (0, 0, math.radians(-18))
    t = Vector((0.004, 0.004, 0.0))
    cam = camera(sc, (0.40, -0.47, 0.19), t, 85, 4.0, None)
    cam.data.dof.focus_distance = (cam.location - Vector((0.03, -0.03, 0.012))).length
    studio(sc, t, -0.05)

def shot_exploded(sc, rig, nodes):
    for g, e in nodes.items(): e.location = Vector(e["move"])
    # Lay the stack along X: model Z to world X, model X to world Y, model Y to world Z
    rig.matrix_world = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    t = Vector((0.0, 0.0, 0.0))
    cam = camera(sc, (0.37, -0.74, 0.16), t, 70, 7.1, None)
    cam.data.dof.focus_distance = (cam.location - Vector((0.0, -0.02, 0.0))).length
    studio(sc, t, -0.09, key=24)

def shot_back(sc, rig, nodes):
    # Face down, so the clip is on top: the J's curl up front, the leg curve behind
    rig.rotation_euler = (0, math.radians(180), 0)
    sc.view_settings.exposure = EXPOSURE - 0.2
    t = Vector((-0.024, -0.016, 0.008))
    cam = camera(sc, (-0.43, -0.49, 0.11), t, 85, 5.6, None)
    cam.data.dof.focus_distance = (cam.location - Vector((0.004, -0.058, 0.016))).length
    studio(sc, t, -0.0185, rim=0.45)

def shot_side(sc, rig, nodes):
    # Standing as it's worn, seen from the side and behind
    rig.rotation_euler = (math.radians(-90), 0, 0)
    sc.view_settings.exposure = EXPOSURE + 0.45
    t = Vector((0.0, 0.0, 0.004))
    cam = camera(sc, (-0.78, -0.40, 0.17), t, 85, 5.6, None)
    cam.data.dof.focus_distance = (cam.location - Vector((-0.03, -0.02, 0.04))).length
    studio(sc, t, -0.0515)

def shot_name(sc, rig, nodes):
    # Standing as worn, close on the front face where the name is, with the tether corner behind
    rig.rotation_euler = (math.radians(-90), 0, 0)
    sc.view_settings.exposure = EXPOSURE - 0.3
    t = Vector((-0.052, -0.012, -0.004))
    cam = camera(sc, (-0.26, -0.17, 0.035), t, 100, 2.8, None)
    cam.data.dof.focus_distance = (cam.location - Vector((-0.056, -0.014, -0.006))).length
    studio(sc, t, -0.0515, key=8)

def shot_keys(sc, rig, nodes):
    rig.rotation_euler = (0, 0, math.radians(200))
    t = Vector((0.0, 0.02, 0.006))
    cam = camera(sc, (0.05, -0.36, 0.13), t, 105, 2.8, None)
    cam.data.dof.focus_distance = (cam.location - Vector((0.0, -0.03, 0.012))).length
    studio(sc, t, -0.05, key=18)

for name in SHOTS:
    sc, rig, nodes = build()
    globals()["shot_" + name](sc, rig, nodes)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    sc.render.image_settings.file_format = "PNG"
    try: sc.render.image_settings.color_depth = "16"
    except Exception: pass
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath)
