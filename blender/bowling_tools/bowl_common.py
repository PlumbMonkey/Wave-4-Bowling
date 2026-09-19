"""Shared layout + helpers for the Phantom Bowling art (Blender 5.2 -> glTF -> Godot).

Coordinates: Blender +Y is DOWN THE LANE (Godot -Z), Blender Z is up (Godot Y).
The foul line is y = 0, the lane surface z = 0, the player's lane is x = 0.
Every number that touches physics mirrors games/bowling/scripts/bowling_spec.gd,
so the art lines up with the Godot colliders exactly.

Geometry and texture helpers are borrowed from ../lounge_tools.
"""
import bpy, os, sys, math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                  # ...\blender
LOUNGE_TOOLS = os.path.join(ROOT, "lounge_tools")
if LOUNGE_TOOLS not in sys.path:
    sys.path.append(LOUNGE_TOOLS)

from lounge_common import (col, wipe, new_obj, shade_auto, box, revolve, tube,  # noqa: E402,F401
                           arch_outline, arch_apex, wall_with_openings, wall_mapper,
                           tri_count, mat, TAU, SQ3_2)

GODOT_ART = os.path.normpath(os.path.join(ROOT, "..", "games", "bowling", "art"))
TEX_DIR = os.path.join(ROOT, "textures")

# ------------------------------------------------ mirrors BowlingSpec -------
LANE_HALF = 0.527
LANE_LEN = 18.288
DECK_END = LANE_LEN + 0.872          # 19.16 (positive y here)
PIT_END = 20.35
GUTTER_W = 0.235
GUTTER_DROP = 0.06
CAPPING_TOP = 0.10
APPROACH = 4.6
BALL_R = 0.1085
PIN_SPACING = 0.3048
ROW_SPACING = 0.2640
GX = LANE_HALF + GUTTER_W            # 0.762 - outer edge of the gutter
PITCH = 2.0 * (GX + 0.12)            # 1.764 lane centre to lane centre
LANES = (-2, -1, 0, 1, 2)            # 0 is the playable lane

# ---------------------------------------------------------- hall ------------
HALL_X = 8.0                          # side walls at x = +-8
HALL_Y0, HALL_Y1 = -10.0, 21.2        # front wall, back wall
CEIL = 7.0
BLOCK_X = 2 * PITCH + GX + 0.12       # 4.41 - outer edge of the lane block
COLUMN_X = 4.78
COLUMN_YS = (-3.0, 2.0, 7.0, 12.0, 17.0)


def pin_spots(cx=0.0):
    out = []
    for row in range(4):
        for k in range(row + 1):
            out.append((cx + (k - row * 0.5) * PIN_SPACING, LANE_LEN + row * ROW_SPACING))
    return out


def pbr(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5, base_img=None,
        emit_img=None, emit=(0.0, 0.0, 0.0), emit_str=0.0, orm_img=None,
        alpha=1.0, alpha_from_base=False, method=None):
    """Principled BSDF laid out the way the glTF exporter understands:
    base colour image, emissive image, and an ORM image (G = rough, B = metal)."""
    m = mat(name, base, metallic, rough, emit, emit_str, alpha)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    for n in [n for n in nt.nodes if n.name.startswith("BWL_")]:
        nt.nodes.remove(n)

    def tex(img, y, label, non_color=False):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.name = t.label = label
        t.image = img
        t.location = (-520, y)
        if non_color:
            img.colorspace_settings.name = 'Non-Color'
        return t

    if base_img:
        t = tex(base_img, 300, "BWL_Base")
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha_from_base:
            nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
    if emit_img:
        t = tex(emit_img, 0, "BWL_Emit")
        nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = max(emit_str, 1.0)
    if orm_img:
        t = tex(orm_img, -300, "BWL_ORM", non_color=True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.name = "BWL_Sep"
        sep.location = (-250, -300)
        nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    if method:
        m.surface_render_method = method
    elif alpha < 1.0 or alpha_from_base:
        m.surface_render_method = 'BLENDED'
    return m


def load_png(name):
    """A texture baked by the lounge build (textures/<name>.png)."""
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(os.path.join(TEX_DIR, name + ".png"))
        img.name = name
    return img


def empty(name, loc, c, size=0.2, target=None):
    """An exported marker node - Godot turns LGT_* markers into lights."""
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    ob.location = loc
    if target is not None:
        ob["target"] = list(target)       # exported as glTF extras
    c.objects.link(ob)
    return ob
