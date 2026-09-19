"""Render settings, world, compositor bloom, the lamp rig and cameras."""
import bpy, math
from mathutils import Vector
from lounge_common import (col, wipe, BACK_Y, CEIL_Z, GALLERY_Z, DOORS, wall_frame,
                           seg_mapper, WALL_T)

PFX = "LNGLGT_"
WARM = (1.00, 0.66, 0.34)
CANDLE = (1.00, 0.58, 0.26)


def render_setup(res=(1920, 1080), samples=64):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    ee = sc.eevee
    for attr, val in (("taa_render_samples", samples), ("taa_samples", 16),
                      ("use_raytracing", True), ("use_shadows", True),
                      ("shadow_ray_count", 2), ("shadow_step_count", 6)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    if hasattr(ee, "ray_tracing_options"):
        ee.ray_tracing_options.use_denoise = True
        if hasattr(ee.ray_tracing_options, "resolution_scale"):
            ee.ray_tracing_options.resolution_scale = '2'
    if hasattr(ee, "shadow_pool_size"):
        ee.shadow_pool_size = '1024'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.0
    return sc


def world_setup(strength=0.02):
    w = bpy.data.worlds.get("LNG_World") or bpy.data.worlds.new("LNG_World")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.030, 0.022, 0.060, 1.0)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w
    return w


def glare_setup(threshold=1.0, size=7):
    """5.2: the group needs its own Render Layers node; Glare is all sockets and
    its Type takes the UI label ('Bloom', not 'BLOOM')."""
    sc = bpy.context.scene
    ng = sc.compositing_node_group
    if ng is None:
        ng = (bpy.data.node_groups.get("LNG_Comp")
              or bpy.data.node_groups.new("LNG_Comp", "CompositorNodeTree"))
    ng.nodes.clear()
    if not [i for i in ng.interface.items_tree
            if i.item_type == 'SOCKET' and i.in_out == 'OUTPUT']:
        ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers")
    bloom = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    for node, x in ((rl, -400), (bloom, -120), (out, 200)):
        node.location = (x, 0)

    def sock(node, name, value):
        s = node.inputs.get(name)
        if s is not None:
            s.default_value = value
    sock(bloom, "Type", 'Bloom')
    sock(bloom, "Threshold", threshold)
    sock(bloom, "Size", size)
    sock(bloom, "Strength", 0.45)
    sock(bloom, "Saturation", 1.0)
    ng.links.new(rl.outputs["Image"], bloom.inputs["Image"])
    ng.links.new(bloom.outputs["Image"], out.inputs[0])
    sc.compositing_node_group = ng
    return ng


# the game-room lights keep their shadows, or they leak through the walls
SMALL = ("Candelabra", "Sconce", "Jar", "Spirit", "TableLamp", "Standard",
         "FrontFill", "Win_Side")
NO_SPEC = ("Candelabra", "Sconce", "Jar", "TableLamp", "Standard", "Chandelier",
           "Fill", "FrontFill", "Room")


def lamp(c, name, kind, loc, energy, color, size=0.3, rot=None, extra=None):
    d = bpy.data.lights.new(PFX + name, kind)
    d.energy = energy
    d.color = color
    # small practicals don't cast shadows - EEVEE's shadow pool overflows otherwise
    d.use_shadow = not name.startswith(SMALL)
    if name.startswith(NO_SPEC):
        d.specular_factor = 0.06            # no hot spots on the glossy floor / mirror
    if kind == 'AREA':
        d.size = size
    elif kind != 'SUN':
        d.shadow_soft_size = size
    for k, v in (extra or {}).items():
        setattr(d, k, v)
    ob = bpy.data.objects.new(PFX + name, d)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    c.objects.link(ob)
    return ob


def aim(ob, target):
    v = Vector(target) - ob.location
    ob.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
    return ob


def build_lights(frames):
    c = col("LNG_Lights", col("Lounge"))
    wipe(PFX)
    from lounge_fittings import CHAND, CANDELABRA_SITES, LANTERN_SITES
    from lounge_furniture import SEAT_C

    # the fire
    lamp(c, "Fire", 'POINT', (0.0, BACK_Y - 0.75, 0.75), 1400.0, (1.0, 0.45, 0.12), 0.45)
    lamp(c, "FireSpill", 'AREA', (0.0, BACK_Y - 1.2, 0.8), 250.0, (1.0, 0.5, 0.2), 1.6,
         rot=(math.radians(90), 0, math.radians(180)))

    # chandelier: a big soft warm source plus a downward throw
    cx, cy, cz = CHAND
    lamp(c, "Chandelier", 'POINT', (cx, cy, cz - 1.2), 3200.0, WARM, 1.2)
    lamp(c, "ChandelierDown", 'SPOT', (cx, cy, cz - 0.3), 3000.0, WARM, 1.0,
         rot=(0, 0, 0), extra={"spot_size": math.radians(110), "spot_blend": 0.9})

    for i, (x, y) in enumerate(CANDELABRA_SITES):
        lamp(c, "Candelabra%d" % i, 'POINT', (x, y, 2.15), 160.0, CANDLE, 0.2)
    from lounge_shell import column_sites
    for i, (x, y, _) in enumerate(column_sites()):
        v = Vector((-x, 1.6 - y)); v.normalize()
        lamp(c, "Sconce%d" % i, 'POINT', (x + v.x * 0.75, y + v.y * 0.75, 3.7), 130.0,
             CANDLE, 0.2)
    for i, (x, y) in enumerate(LANTERN_SITES):
        lamp(c, "Spirit%d" % i, 'POINT', (x, y, 1.6), 70.0, (0.35, 0.55, 1.0), 0.15)

    # the ghost glows, the seating gets a candle wash
    gx, gy = SEAT_C[0], SEAT_C[1] + 0.25
    lamp(c, "Ghost", 'POINT', (gx, gy - 0.3, 1.9), 90.0, (0.55, 0.7, 1.0), 0.3)
    for i, (x, y) in enumerate(((-2.7, 3.2), (2.7, 3.2), (-2.7, 0.2), (2.7, 0.2))):
        lamp(c, "Jar%d" % i, 'POINT', (x, y, 0.85), 18.0, CANDLE, 0.08)
    for s in (-1, 1):
        lamp(c, "TableLamp%d" % (s > 0), 'POINT', (s * 7.6, -0.45, 1.3), 60.0, WARM, 0.2)
        lamp(c, "Standard%d" % (s > 0), 'POINT', (s * 8.6, 0.6, 2.3), 120.0, WARM, 0.3)

    # moonlight through the stained glass, violet through the storm window
    from lounge_shell import windows
    from lounge_common import WALLS
    for name, _, _ in WALLS:
        tw = seg_mapper(name)
        _, d, n, _ = wall_frame(name)
        for k, (u, w, sill, spring, kind) in enumerate(windows(name)):
            p = tw(u, (sill + spring) * 0.5 + 0.8, -2.2)
            col_ = (0.62, 0.35, 1.0) if kind == "storm" else (0.35, 0.50, 1.0)
            en = 450.0 if kind == "storm" else 220.0
            ob = lamp(c, "Win_%s%d" % (name, k), 'AREA', tuple(p), en, col_, 1.5)
            ob.data.shape = 'RECTANGLE'
            ob.data.size_y = 3.2
            aim(ob, tuple(p - n * 5.0 + Vector((0, 0, -3.0))))

    # the game rooms spill their colour through the doors
    tints = {"bowling": (1.0, 0.45, 0.30), "billiards": (0.45, 1.0, 0.55),
             "golf": (0.45, 0.85, 1.0), "poker": (1.0, 0.40, 0.28)}
    for slug, F in frames.items():
        lamp(c, "Room_" + slug, 'POINT', F(0, 3.5, 3.3), 550.0, tints[slug], 0.8)
        lamp(c, "RoomFill_" + slug, 'POINT', F(0, 1.2, 2.8), 180.0, tints[slug], 0.6)
        if slug == "bowling":
            ob = lamp(c, "Pins", 'SPOT', F(0, 5.6, 2.2), 260.0, (1, 0.9, 0.8), 0.1,
                      extra={"spot_size": math.radians(50), "spot_blend": 0.5})
            aim(ob, F(0, 6.9, 0.2))
        if slug == "billiards":
            for b in (3.15, 4.65):
                ob = lamp(c, "Pool%.0f" % (b * 10), 'SPOT', F(0, b, 2.0), 180.0,
                          (0.85, 1.0, 0.8), 0.15,
                          extra={"spot_size": math.radians(80), "spot_blend": 0.6})
                aim(ob, F(0, b, 0.0))

    # soft top fill so the gallery and ceiling don't drop to black
    ob = lamp(c, "Fill", 'AREA', (0.0, 0.0, CEIL_Z - 1.0), 900.0, (0.60, 0.50, 0.85),
              14.0, rot=(0, 0, 0))
    ob.data.shape = 'RECTANGLE'
    ob.data.size_y = 12.0
    lamp(c, "FrontFill", 'POINT', (0.0, -6.0, 5.0), 500.0, (0.75, 0.62, 0.60), 3.0)
    return c


def build_cameras():
    c = col("LNG_Cameras", col("Lounge"))
    wipe("LNGCAM_")

    def cam(name, loc, target, lens, shift_y=0.0):
        d = bpy.data.cameras.new("LNGCAM_" + name)
        d.lens = lens
        d.clip_start = 0.05
        d.clip_end = 200.0
        d.shift_y = shift_y
        ob = bpy.data.objects.new("LNGCAM_" + name, d)
        ob.location = loc
        c.objects.link(ob)
        aim(ob, target)
        return ob

    hero = cam("Hero", (0.0, -6.8, 2.1), (0.0, 20.0, 2.1), 14.0, shift_y=0.06)
    cam("Fireplace", (0.0, -1.2, 1.7), (0.0, 8.0, 2.6), 24.0)
    cam("Bowling", (-4.5, 0.5, 1.7), (-10.5, 6.0, 1.6), 24.0)
    cam("Poker", (4.5, 0.5, 1.7), (10.5, 6.0, 1.6), 24.0)
    cam("Gallery", (0.0, -6.0, 9.2), (0.0, 8.0, 7.0), 18.0)
    bpy.context.scene.camera = hero
    return hero


def build(frames):
    render_setup()
    world_setup()
    glare_setup()
    build_lights(frames)
    return build_cameras()
