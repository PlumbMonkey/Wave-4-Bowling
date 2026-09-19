"""Build the Phantom Bowling art headless, save the .blend files, export GLBs
straight into the Godot project, and render previews.

    blender -b --factory-startup --python bowl_headless.py -- [--bake] [--balls] [--alley]
            [--void] [--crypt] [--bake2] [--render aim,hall,pins] [--pct 50] [--samples 48]

Outputs:
    blender/Phantom Bowling - Balls.blend          -> games/bowling/art/balls/<id>.glb
    blender/Phantom Bowling - Spectral Lounge.blend -> games/bowling/art/alleys/lounge.glb
"""
import bpy, sys, os, time, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bowl_common as C  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else True
    return default


def wipe_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.node_groups, bpy.data.worlds):
        for d in list(coll):
            try:
                coll.remove(d)
            except Exception:
                pass
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    bpy.context.scene.compositing_node_group = None


TEX = {"lane": "BWL_Lane", "approach": "BWL_Approach", "marble": "BWL_Marble",
       "mask": "BWL_MaskArch", "pit": "BWL_PitGlow", "glass_center": "BWL_GlassGhost",
       "glass_side": "BWL_GlassSide", "portrait": "BWL_GhostPortrait", "banner": "BWL_BannerPin",
       "spectre": ("BWL_BallSpectre", "BWL_BallSpectreEmit"),
       "p": ("BWL_BallP", "BWL_BallPEmit", "BWL_BallPORM"),
       "skull": ("BWL_Skull", "BWL_SkullEmit")}


def textures(bake):
    if bake:
        import bowl_textures
        return bowl_textures.build()
    out = {}
    for k, v in TEX.items():
        out[k] = tuple(C.load_png(n) for n in v) if isinstance(v, tuple) else C.load_png(v)
    return out


def export(objs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.view_layer.update()
    for ob in bpy.data.objects:
        if ob.name in bpy.context.view_layer.objects:
            ob.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_lights=False, export_cameras=False, export_extras=True,
        export_materials='EXPORT', export_image_format='AUTO', export_normals=True)
    return os.path.getsize(path)


def descendants(ob):
    out = [ob]
    for ch in ob.children:
        out += descendants(ch)
    return out


def preview_setup():
    sys.path.insert(0, C.LOUNGE_TOOLS)
    import lounge_scene
    lounge_scene.render_setup()
    lounge_scene.world_setup(0.01)
    lounge_scene.glare_setup(threshold=1.0, size=7)


def render(cam, path, pct, samples):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam]
    sc.eevee.taa_render_samples = samples
    sc.render.resolution_percentage = pct
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print("BOWL rendered", path, "%.1fs" % (time.time() - t))


pct = int(opt("--pct", 50))
samples = int(opt("--samples", 48))
cams = [c.strip() for c in str(opt("--render", "")).split(",") if c.strip() and c != "True"]
renders = os.path.join(C.ROOT, "renders")
bake = bool(opt("--bake", False))

# ------------------------------------------------------------------ balls ---
if opt("--balls"):
    wipe_scene()
    import bowl_balls
    tex = textures(bake)
    bake = False
    M = bowl_balls.materials(tex)
    c = C.col("BWL_Balls")
    roots = {k: bowl_balls.build(k, (0.0, 0.0, 0.0), c, M) for k in bowl_balls.BALLS}
    for k, r in roots.items():
        size = export(descendants(r), os.path.join(C.GODOT_ART, "balls", k + ".glb"))
        print("BOWL exported ball", k, size)
    # line them up for a preview, on a black marble slab
    for i, k in enumerate(bowl_balls.BALLS):
        roots[k].location = ((i - 1) * 0.30, 0.0, C.BALL_R)
        roots[k].rotation_euler = (0.0, 0.0, 0.25 * (i - 1))
    import bmesh
    bm = bmesh.new()
    C.box(bm, 0, 0, -0.01, 3, 3, 0.02)
    C.new_obj("BWL_Slab", bm, c, [C.mat("BWL_SlabMat", (0.02, 0.02, 0.025), rough=0.08)])
    preview_setup()
    for name, loc, en, colr in (("Key", (-0.8, -1.2, 1.0), 60, (1.0, 0.75, 0.5)),
                                ("Rim", (0.9, 0.8, 0.6), 40, (0.6, 0.4, 1.0)),
                                ("Fill", (0.0, -1.5, 0.3), 8, (0.8, 0.8, 1.0))):
        d = bpy.data.lights.new("BWLLGT_" + name, 'AREA')
        d.energy, d.color, d.size = en, colr, 0.8
        lo = bpy.data.objects.new("BWLLGT_" + name, d)
        lo.location = loc
        from mathutils import Vector
        lo.rotation_euler = (Vector((0, 0, 0.1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        c.objects.link(lo)
    d = bpy.data.cameras.new("BWLCAM_Balls")
    d.lens = 70
    cam = bpy.data.objects.new("BWLCAM_Balls", d)
    cam.location = (0.0, -1.55, 0.32)
    from mathutils import Vector
    cam.rotation_euler = (Vector((0, 0, 0.1)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    c.objects.link(cam)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.ROOT, "Phantom Bowling - Balls.blend"))
    if "balls" in cams:
        render("BWLCAM_Balls", os.path.join(renders, "bowl_balls.png"), pct, samples)

# ------------------------------------------------------------------- pins ---
if opt("--pins"):
    wipe_scene()
    sys.path.insert(0, C.LOUNGE_TOOLS)
    import bowl_pins
    from mathutils import Vector
    c = C.col("BWL_Pins")
    ob, m = bowl_pins.build(c)
    size = export([ob], os.path.join(C.GODOT_ART, "pins", "bone.glb"))
    print("BOWL exported bone pin", size, len(ob.data.polygons), "faces")
    # a preview rack on a strip of lane
    import bmesh
    for k, (x, y) in enumerate(C.pin_spots(0.0)):
        dup = bpy.data.objects.new("PIN_rack_%d" % k, ob.data)
        dup.location = (x, y - C.LANE_LEN, 0.0)
        c.objects.link(dup)
    ob.location = (0.0, -6.0, 0.0)            # the export copy, parked out of shot
    bm = bmesh.new()
    C.box(bm, 0, 0.4, -0.02, 1.4, 2.4, 0.04)
    C.new_obj("BWL_DeckSlab", bm, c, [C.mat("BWL_DeckMat", (0.55, 0.36, 0.2), rough=0.1)])
    preview_setup()
    for name, loc, en, colr in (("Key", (-1.0, -1.4, 1.4), 120, (1.0, 0.8, 0.6)),
                                ("Rim", (0.8, 1.6, 1.0), 80, (0.6, 0.4, 1.0))):
        d = bpy.data.lights.new("BWLLGT_" + name, 'AREA')
        d.energy, d.color, d.size = en, colr, 1.0
        lo = bpy.data.objects.new("BWLLGT_" + name, d)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0.4, 0.15)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        c.objects.link(lo)
    d = bpy.data.cameras.new("BWLCAM_Pins")
    d.lens = 55
    cam = bpy.data.objects.new("BWLCAM_Pins", d)
    cam.location = (0.35, -1.25, 0.34)
    cam.rotation_euler = (Vector((0.0, 0.35, 0.19)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    c.objects.link(cam)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.ROOT, "Phantom Bowling - Bone Pins.blend"))
    render("BWLCAM_Pins", os.path.join(renders, "bowl_bone_pins.png"), pct, samples)

# -------------------------------------------------------------- reliquary ---
if opt("--reliquary"):
    wipe_scene()
    sys.path.insert(0, C.LOUNGE_TOOLS)
    import bowl_reliquary
    from mathutils import Vector
    import bmesh
    c = C.col("BWL_Reliquary")
    obs = bowl_reliquary.build(c)
    size = export(obs, os.path.join(C.GODOT_ART, "pins", "reliquary.glb"))
    print("BOWL exported reliquary", size, [len(o.data.polygons) for o in obs])
    for k, (x, y) in enumerate(C.pin_spots(0.0)):
        dup = bpy.data.objects.new("PIN_rack_%d" % k, obs[k % len(obs)].data)
        dup.location = (x, y - C.LANE_LEN, 0.0)
        c.objects.link(dup)
    for i, o in enumerate(obs):
        o.location = (i * 0.2 - 0.3, -6.0, 0.0)          # export copies, out of shot
    bm = bmesh.new()
    C.box(bm, 0, 0.4, -0.02, 1.6, 2.6, 0.04)
    C.new_obj("BWL_DeckSlab", bm, c, [C.mat("BWL_DeckMat2", (0.30, 0.17, 0.08), rough=0.06)])
    preview_setup()
    for name, loc, en, colr in (("Key", (-0.9, -1.3, 1.2), 90, (1.0, 0.78, 0.55)),
                                ("Fill", (1.0, -1.1, 0.6), 30, (0.55, 0.6, 1.0)),
                                ("Rim", (0.0, 1.8, 1.2), 120, (0.5, 0.4, 1.0))):
        d = bpy.data.lights.new("BWLLGT_" + name, 'AREA')
        d.energy, d.color, d.size = en, colr, 1.0
        lo = bpy.data.objects.new("BWLLGT_" + name, d)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0.4, 0.15)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        c.objects.link(lo)
    d = bpy.data.cameras.new("BWLCAM_Relq")
    d.lens = 50
    cam = bpy.data.objects.new("BWLCAM_Relq", d)
    cam.location = (0.0, -1.15, 0.30)
    cam.rotation_euler = (Vector((0.0, 0.35, 0.19)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    c.objects.link(cam)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.ROOT, "Phantom Bowling - Reliquary Pins.blend"))
    render("BWLCAM_Relq", os.path.join(renders, "bowl_reliquary_pins.png"), pct, samples)

# ------------------------------------------------------------------ alley ---
if opt("--alley"):
    wipe_scene()
    import bowl_alley
    tex = textures(bake)
    t0 = time.time()
    root = bowl_alley.build(tex)
    bpy.context.view_layer.update()
    print("BOWL alley built: %d tris, %d objects, %.1fs" % (C.tri_count(),
          len(bpy.context.scene.objects), time.time() - t0))
    objs = list(bpy.data.collections["BWL_LoungeArt"].all_objects) + \
        list(bpy.data.collections["BWL_LoungeMarkers"].all_objects)
    size = export(objs, os.path.join(C.GODOT_ART, "alleys", "lounge.glb"))
    print("BOWL exported alley", size)
    preview_setup()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.ROOT, "Phantom Bowling - Spectral Lounge.blend"))
    for cname in cams:
        if cname == "balls":
            continue
        render("BWLCAM_" + cname.capitalize(), os.path.join(renders, "bowl_lounge_%s.png" % cname),
               pct, samples)

# ---------------------------------------------------------- void + crypt ---
TEX2 = {"nebula": "BWL_Nebula", "void_mask": "BWL_VoidMask", "void_glass": "BWL_VoidGlass",
        "void_banner": "BWL_VoidBanner", "star_ceiling": "BWL_StarCeiling", "compass": "BWL_Compass",
        "crypt_lane": ("BWL_CryptLane", "BWL_CryptLaneEmit"),
        "crypt_approach": ("BWL_CryptApproach", "BWL_CryptApproachEmit"),
        "neon_mask": "BWL_NeonMask", "bride": "BWL_BridePanel", "mural_a": "BWL_MuralA",
        "mural_b": "BWL_MuralB", "sigils": "BWL_Sigils", "star_map": "BWL_StarMap"}


def textures2(which, bake):
    import bowl_textures2 as T2
    if bake:
        return T2.build_void() if which == "void" else T2.build_crypt()
    out = {}
    for k, v in TEX2.items():
        try:
            out[k] = tuple(C.load_png(n) for n in v) if isinstance(v, tuple) else C.load_png(v)
        except RuntimeError:
            pass
    return out


for alley_id, flag, title in (("void", "--void", "The Void"), ("crypt", "--crypt", "The Crypt")):
    if not opt(flag):
        continue
    wipe_scene()
    mod = importlib.import_module("bowl_" + alley_id)
    tex = textures(False)
    tex.update(textures2(alley_id, bool(opt("--bake2", False))))
    t0 = time.time()
    root = mod.build(tex)
    bpy.context.view_layer.update()
    print("BOWL %s built: %d tris, %d objects, %.1fs" % (alley_id, C.tri_count(),
          len(bpy.context.scene.objects), time.time() - t0))
    art = "BWL_%sArt" % alley_id.capitalize()
    objs = list(bpy.data.collections[art].all_objects) + \
        list(bpy.data.collections["BWL_%sMarkers" % alley_id.capitalize()].all_objects)
    objs = [o for o in objs if o.type != 'MESH' or len(o.data.polygons)]
    size = export(objs, os.path.join(C.GODOT_ART, "alleys", alley_id + ".glb"))
    print("BOWL exported", alley_id, size)
    preview_setup()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.ROOT, "Phantom Bowling - %s.blend" % title))
    for cname in cams:
        if cname == "balls":
            continue
        render("BWLCAM_" + cname.capitalize(), os.path.join(renders, "bowl_%s_%s.png" % (alley_id, cname)),
               pct, samples)
