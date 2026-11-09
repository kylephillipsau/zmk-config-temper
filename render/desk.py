"""Studio stills of both Short Temper halves on a desk. Run: blender -b -P scene.py -- MESH_DIR OUT_DIR WIDTH SAMPLES SHOT[,SHOT]"""
import bpy, bmesh, math, sys, os, json
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
MESH, OUT, WIDTH, SAMPLES, SHOTS = argv[0], argv[1], int(argv[2]), int(argv[3]), argv[4].split(",")
HERE = os.path.dirname(os.path.abspath(MESH))
HEIGHT = round(WIDTH / 2.39)
MM = 0.001
E = lambda k, d: float(os.environ.get(k, d))
BEVEL, EXPOSURE, POOL, SHEEN, KEY, RIM = E("BEVEL", 0.00035), E("EXPOSURE", -4.5), E("POOL", 1.0), E("SHEEN", 1.0), E("KEY", 1.0), E("RIM", 0.25)
MATTE, ROUGH, SCREEN, CAPS = E("MATTE", 0.006), E("ROUGH", 0.45), E("SCREEN", 1.2), E("CAPS", 0.007)
GAP, TOE, LS = E("GAP", 40), E("TOE", 7), E("LS", 1.4)
JGRAIN, JBUMP = E("JGRAIN", 1.6), E("JBUMP", 0.12)  # texture coordinates are in mm: the meshes are scaled by their objects  # gap between inner edges (mm), toe-in (deg), light scale
LAYOUT = None
CONTROLLER = json.load(open(os.path.join(MESH, "controller.json")))
DISH, TOP_W = 0.45, 12.6
FONT_TEXT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
FONT_SYM = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
SYMBOLS = set("↑→–’”")

def material(name, colour, rough, metal=0.0, spec=0.5, grain=None, grain_strength=0.18, coat=0.0, aniso=0.0, radial=False, bump_mm=0.04):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs: b.inputs[key].default_value = spec; break
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        if "Coat Roughness" in b.inputs: b.inputs["Coat Roughness"].default_value = 0.02
    if aniso and "Anisotropic" in b.inputs:
        b.inputs["Anisotropic"].default_value = aniso
        if radial:
            tg = nt.nodes.new("ShaderNodeTangent"); tg.direction_type = "RADIAL"; tg.axis = "Z"
            nt.links.new(tg.outputs["Tangent"], b.inputs["Tangent"])
    bevel = nt.nodes.new("ShaderNodeBevel"); bevel.samples = 8; bevel.inputs["Radius"].default_value = BEVEL
    if grain:
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = grain; n.inputs["Detail"].default_value = 6
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = grain_strength
        bump.inputs["Distance"].default_value = bump_mm * MM
        nt.links.new(bevel.outputs["Normal"], bump.inputs["Normal"])
        nt.links.new(n.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    else:
        nt.links.new(bevel.outputs["Normal"], b.inputs["Normal"])
    return m

def glass(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.95, 0.95, 0.95, 1); b.inputs["Roughness"].default_value = 0.0
    b.inputs["Transmission Weight"].default_value = 1.0; b.inputs["IOR"].default_value = 1.49
    return m

def screen_material(name, path):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(path); tex.interpolation = "Closest"
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.012, 0.013, 0.012, 1)   # ink
    mix.inputs[7].default_value = (0.50, 0.52, 0.49, 1)      # the memory LCD's pale grey
    nt.links.new(tex.outputs["Color"], mix.inputs[0])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    nt.links.new(mix.outputs[2], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = SCREEN
    b.inputs["Roughness"].default_value = 0.3
    return m

def pcb_material():
    """The controller's top from make_pcb_texture.py: colour, where it's gold, and the pads' relief."""
    m = bpy.data.materials.new("Controller top"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    def tex(name, colour):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(MESH, name))
        if not colour: n.image.colorspace_settings.name = "Non-Color"
        n.interpolation = "Cubic"; return n
    col, metal, height = tex("pcb_colour.png", True), tex("pcb_metal.png", False), tex("pcb_height.png", False)
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(metal.outputs["Color"], b.inputs["Metallic"])
    rough = nt.nodes.new("ShaderNodeMapRange"); rough.inputs["To Min"].default_value = 0.42; rough.inputs["To Max"].default_value = 0.2
    nt.links.new(metal.outputs["Color"], rough.inputs["Value"]); nt.links.new(rough.outputs["Result"], b.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.00004
    nt.links.new(height.outputs["Color"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

MATS = {}
def make_materials():
    black = (MATTE, MATTE, MATTE * 1.08)
    MATS.update({
        "case": material("Matte black case", black, ROUGH, spec=0.35),
        "caps": material("Dark grey blank caps", (0.009, 0.009, 0.0095), 0.62, spec=0.22),
        "stems": material("Switch", (0.01, 0.01, 0.011), 0.5),
        "pcb": material("Controller PCB edge", (0.012, 0.012, 0.013), 0.45),
        "pcb_top": pcb_material(),
        "usb_shell": material("USB-C shell", (0.82, 0.82, 0.83), 0.3, metal=1.0, aniso=0.3),
        "usb_tongue": material("USB-C tongue", (0.012, 0.012, 0.013), 0.4),
        "usb_contacts": material("Gold contacts", (0.92, 0.72, 0.38), 0.2, metal=1.0),
        "socket": material("Header socket", (0.010, 0.010, 0.011), 0.5, spec=0.35),
    })

def tidy(ob, mat, angle=32):
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-7); bm.to_mesh(ob.data); bm.free()
    ob.data.shade_smooth()
    try: ob.data.set_sharp_from_angle(angle=math.radians(angle))
    except Exception as e: print("smooth by angle failed", e)
    wn = ob.modifiers.new("weighted", "WEIGHTED_NORMAL"); wn.mode = "FACE_AREA"; wn.keep_sharp = True
    ob.data.materials.clear(); ob.data.materials.append(MATS[mat])

def link(ob, parent):
    for c in list(ob.users_collection): c.objects.unlink(ob)
    MODEL.objects.link(ob); ob.parent = parent

def load(name, mat, parent, angle=32):
    bpy.ops.wm.stl_import(filepath=os.path.join(MESH, name + ".stl"), global_scale=MM)
    ob = bpy.context.selected_objects[0]; ob.name = name
    tidy(ob, mat, angle); link(ob, parent); return ob

def plane(name, w, h, loc, mat, parent):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((sx * w / 2, sy * h / 2, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs); uv = bm.loops.layers.uv.new()
    for loop, co in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): loop[uv].uv = co
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); MODEL.objects.link(ob); ob.parent = parent; ob.location = loc
    me.materials.append(MATS[mat] if isinstance(mat, str) else mat); return ob

def cylinder(name, r, h, loc, parent, mats, verts=128, bevel=0.0004):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    ob = bpy.context.object; ob.name = name
    for m in mats: ob.data.materials.append(MATS[m])
    if len(mats) > 1:
        for p in ob.data.polygons: p.material_index = 1 if p.normal.z > 0.9 else 0
    ob.data.shade_smooth()
    try: ob.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    if bevel:
        bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 4; bv.limit_method = "ANGLE"
    link(ob, parent); return ob

def legends(halves, caps):
    fonts = {"text": bpy.data.fonts.load(FONT_TEXT), "sym": bpy.data.fonts.load(FONT_SYM)}
    dg = bpy.context.evaluated_depsgraph_get()
    for k in LAYOUT["keys"]:
        txt = k["legend"]; sym = any(ch in SYMBOLS for ch in txt)
        word = len(txt) > 2 and " " not in txt
        size, dy = (3.3, 2.4) if word else (3.7, 2.6) if " " in txt else (4.6, 1.9)
        if txt in ("→", "↑"): size, dy = (5.0, 2.6) if txt == "↑" else (4.0, 3.6)
        if txt in ("–", "*"): size, dy = 4.4, 2.6
        cu = bpy.data.curves.new("legend", "FONT"); cu.body = txt; cu.font = fonts["sym" if sym else "text"]
        cu.size = size * MM; cu.align_x = "CENTER"; cu.align_y = "CENTER"
        tmp = bpy.data.objects.new("tmp", cu); bpy.context.scene.collection.objects.link(tmp)
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
        # Flat on the top's tilted plane, lifted just clear of the cylindrical dish at its widest
        hw = max(abs(v.co.x) for v in me.vertices) / MM
        lift = DISH * min(1.0, (2 * hw / TOP_W) ** 2) + 0.04
        ob = bpy.data.objects.new("legend " + txt, me); MODEL.objects.link(ob); ob.parent = halves[k["half"]]
        r, t = math.radians(k["r"]), math.tan(math.radians(k["tilt"]))
        ly = k["top_back"] + dy
        ob.location = (MM * (k["x"] - ly * math.sin(r)), MM * (k["y"] + ly * math.cos(r)), MM * (k["z"] + t * ly - DISH + lift))
        ob.rotation_euler = (math.radians(k["tilt"]), 0, r)
        me.materials.append(MATS["legend_dark" if k["colour"] == "orange" else "legend"])

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_materials()
    sc = bpy.context.scene; sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("METAL", "NONE"):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            for d in prefs.devices: d.use = True
            break
        except Exception as e: print("device", kind, e)
    sc.cycles.device = "GPU" if prefs.compute_device_type != "NONE" else "CPU"
    sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = os.environ.get("DENOISE", "1") == "1"
    sc.cycles.max_bounces = 12; sc.cycles.glossy_bounces = 6; sc.cycles.transmission_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = WIDTH, HEIGHT
    sc.view_settings.view_transform = "AgX"
    for look_name in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try: sc.view_settings.look = look_name; break
        except Exception: pass
    sc.view_settings.exposure = EXPOSURE
    world = bpy.data.worlds.new("World"); sc.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0025, 0.0027, 0.003, 1)
    global MODEL, GROUND
    MODEL = bpy.data.collections.new("model"); sc.collection.children.link(MODEL)
    GROUND = bpy.data.collections.new("ground"); sc.collection.children.link(GROUND)
    rig = bpy.data.objects.new("rig", None); sc.collection.objects.link(rig)
    halves = {}
    for half, sign in (("L", -1), ("R", 1)):
        e = bpy.data.objects.new("half " + half, None); sc.collection.objects.link(e); e.parent = rig
        e.location = (sign * GAP / 2 * MM, 0, 0); e.rotation_euler = (0, 0, math.radians(-sign * TOE))
        halves[half] = e
        for part in ("case", "caps", "stems", "pcb", "usb_shell", "usb_tongue", "usb_contacts", "socket"):
            load(f"{part}_{half}", part, e, angle=40)
        # the board's printed top, the same way up on both halves, as on the real ones
        x0, x1, y0, y1, z0, z1 = CONTROLLER["pcb"]
        cx = (x0 + x1) / 2 * (1 if half == "R" else -1)
        plane("controller top " + half, (x1 - x0) * MM, (y1 - y0) * MM, (cx * MM, (y0 + y1) / 2 * MM, (z1 + 0.004) * MM), "pcb_top", e)
    bpy.context.view_layer.update()
    return sc, rig, halves

def floor(sc, z, rough=0.24, shade=0.03):
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, z)); f = bpy.context.object; f.name = "floor"
    m = bpy.data.materials.new("Floor"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (shade, shade, shade * 1.06, 1); b.inputs["Roughness"].default_value = rough
    f.data.materials.append(m)
    for c in list(f.users_collection): c.objects.unlink(f)
    GROUND.objects.link(f)

def look(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()

def area(sc, name, loc, target, size, energy, colour=(1, 1, 1), size_y=None, spread=None):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.color = colour
    if size_y: l.shape = "RECTANGLE"; l.size = size; l.size_y = size_y
    else: l.size = size
    if spread is not None: l.spread = math.radians(spread)
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc; look(o, target)
    o.visible_camera = False; o.light_linking.receiver_collection = MODEL
    return o

def spot(sc, name, loc, target, energy, size_deg, blend=1.0, colour=(1, 1, 1), radius=0.05):
    l = bpy.data.lights.new(name, "SPOT"); l.energy = energy * POOL; l.spot_size = math.radians(size_deg); l.spot_blend = blend; l.color = colour
    l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc; look(o, target)
    o.light_linking.receiver_collection = GROUND

def camera(sc, loc, target, lens, fstop, focus_point):
    c = bpy.data.cameras.new("cam"); c.lens = lens; c.sensor_width = 36
    c.dof.use_dof = fstop is not None
    o = bpy.data.objects.new("cam", c); sc.collection.objects.link(o); o.location = loc; look(o, target); sc.camera = o
    if fstop: c.dof.aperture_fstop = fstop; c.dof.focus_distance = (Vector(loc) - Vector(focus_point)).length
    c.clip_start = 0.005; c.clip_end = 30
    return o

WARM, COOL = (1.0, 0.84, 0.68), (0.70, 0.83, 1.0)

def studio(sc, t, z_floor, key=30.0, rim=1.0, halo=(0.0, 0.16), s=None):
    s = s or LS; t = Vector(t); e = s * s
    area(sc, "key", t + Vector((-0.30, -0.28, 0.42)) * s, t, 0.40 * s, key * KEY * e, WARM, 0.22 * s)
    area(sc, "rim right", t + Vector((0.30, 0.34, 0.12)) * s, t, 0.035 * s, 110 * rim * RIM * e, COOL, 0.7 * s, spread=30)
    area(sc, "rim left", t + Vector((-0.34, 0.26, 0.10)) * s, t, 0.035 * s, 70 * rim * RIM * e, WARM, 0.6 * s, spread=30)
    area(sc, "top strip", t + Vector((0.0, 0.05, 0.45)) * s, t, 0.6 * s, 26 * rim * KEY * e, (1, 1, 1), 0.03 * s)
    spot(sc, "halo", t + Vector((halo[0], halo[1] + 0.05, 0.75)) * s, (t.x + halo[0] * s, t.y + (halo[1] + 0.12) * s, z_floor), 7000 * e, 26, 1.0, (0.86, 0.9, 1.0), 0.3 * s)
    floor(sc, z_floor)
    cam = sc.camera.location; back = (cam - t).normalized()
    area(sc, "sheen", cam + back * 0.35 * s + Vector((0, 0, 0.12 * s)), t, 1.0 * s, 250 * SHEEN * e, (1, 1, 1), 0.6 * s)

def point(halves, half, x, y, z):
    return halves[half].matrix_world @ Vector((x * MM, y * MM, z * MM))

def shot_hero(sc, rig, halves):
    # Framed like the Sofle's, scaled to the Temper's smaller halves
    t = Vector((0.0, 0.005, 0.008))
    camera(sc, (0.135, -0.62, 0.23), t, 70, 5.6, point(halves, "L", -25, -10, 15))
    studio(sc, t, 0.0)

def shot_controller(sc, rig, halves):
    # Close on the right half's controller, from in front and to the left
    x0, x1, y0, y1, z0, z1 = CONTROLLER["pcb"]
    t = point(halves, "R", (x0 + x1) / 2 + 10, (y0 + y1) / 2 - 3, 6)
    sc.view_settings.exposure = EXPOSURE - 0.2
    camera(sc, t + Vector((-0.045, -0.13, 0.20)), t, 100, 5.6, point(halves, "R", (x0 + x1) / 2, (y0 + y1) / 2, 6))
    studio(sc, t, 0.0, key=16, s=0.9)

def shot_port(sc, rig, halves):
    # From behind the right half, into the USB-C port, with the board and the keys beyond
    x0, x1, y0, y1, z0, z1 = CONTROLLER["pcb"]
    t = point(halves, "R", (x0 + x1) / 2 + 12, (y0 + y1) / 2, 7)
    sc.view_settings.exposure = EXPOSURE - 0.1
    camera(sc, t + Vector((-0.11, 0.17, 0.10)), t, 100, 4.0, point(halves, "R", (x0 + x1) / 2, y1, 7.5))
    studio(sc, t, 0.0, key=16, s=0.9)

for name in SHOTS:
    sc, rig, halves = build()
    globals()["shot_" + name](sc, rig, halves)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    sc.render.image_settings.file_format = "PNG"
    try: sc.render.image_settings.color_depth = "16"
    except Exception: pass
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath)
