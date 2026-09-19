"""Rebuild the whole Spectral Manor Lounge.

GUI (Blender MCP / scripting tab):
    import sys
    sys.path.insert(0, r"D:\\DEV Projects 2026 V2\\projects\\Spectral Manor Wave 4\\blender\\lounge_tools")
    import lounge_build; lounge_build.run()

Headless (preferred - builds, saves the .blend, renders a preview):
    blender -b --factory-startup --python lounge_tools\\headless.py -- --render hero

Every phase is idempotent: each wipes its own objects by name prefix first.
"""
import bpy, sys, os, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = ("lounge_common", "lounge_textures", "lounge_materials", "lounge_shell",
           "lounge_fittings", "lounge_furniture", "lounge_rooms", "lounge_scene",
           "lounge_export")


def reload_all():
    while HERE in sys.path:
        sys.path.remove(HERE)
    sys.path.insert(0, HERE)
    mods = {}
    for name in MODULES:
        m = importlib.import_module(name)
        importlib.reload(m)
        mods[name.replace("lounge_", "")] = m
    return mods


def wipe_scene():
    """Drop every datablock - used on a fresh factory-startup scene."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.node_groups, bpy.data.worlds,
                 bpy.data.curves):
        for d in list(coll):
            try:
                coll.remove(d)
            except Exception:
                pass
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    bpy.context.scene.compositing_node_group = None


def load_textures(m):
    """Reuse the baked PNGs when they're already on disk."""
    tex_dir = m["common"].TEX_DIR
    names = {"floor": "LNG_Floor", "stone": "LNG_Stone", "wood": "LNG_Mahogany",
             "lane": "LNG_Lane", "velvet": "LNG_Velvet", "rug_round": "LNG_RugRound",
             "rug_rect": "LNG_RugRect", "banner": "LNG_Banner",
             "portrait_a": "LNG_PortraitA", "portrait_b": "LNG_PortraitB",
             "glass_blue": "LNG_GlassBlue", "glass_storm": "LNG_GlassStorm",
             "emb_bowling": "LNG_EmbBowling", "emb_billiards": "LNG_EmbBilliards",
             "emb_golf": "LNG_EmbGolf", "emb_poker": "LNG_EmbPoker",
             "flame": "LNG_Flame", "golf_screen": "LNG_GolfScreen"}
    out = {}
    for key, name in names.items():
        path = os.path.join(tex_dir, name + ".png")
        if not os.path.exists(path):
            return None
        img = bpy.data.images.get(name)
        if img is None:
            img = bpy.data.images.load(path)
            img.name = name
        out[key] = img
    return out


def run(bake=False):
    m = reload_all()
    tex = None if bake else load_textures(m)
    if tex is None:
        tex = m["textures"].build()
    mats = m["materials"].build(tex)
    m["shell"].build(mats)
    m["fittings"].build(mats)
    m["furniture"].build(mats)
    frames = m["rooms"].build(mats)
    m["scene"].build(frames)
    bpy.context.view_layer.update()
    return {"tris": m["common"].tri_count(),
            "objects": len(bpy.context.scene.objects)}


def render(path, percent=100, camera="LNGCAM_Hero", samples=None):
    sc = bpy.context.scene
    cam = bpy.data.objects.get(camera)
    if cam:
        sc.camera = cam
    if samples:
        sc.eevee.taa_render_samples = samples
    sc.render.use_compositing = True
    sc.render.resolution_percentage = percent
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
