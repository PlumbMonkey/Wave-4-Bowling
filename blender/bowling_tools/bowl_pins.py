"""The bone pin set: regulation pins carved from old bone.

The outline stays within a few millimetres of the USBC pin, so the Godot pin
collider and mass are unchanged and the bone set plays exactly like the
classic one. On top of that shape:

    base   - swells into two knuckle lobes, like the end of a femur
    neck   - the two red stripes become two vertebra rings, with a spine at the back
    head   - a small skull facing the bowler (-Y), eyes glowing faintly violet
    all    - cracks, stains and patina baked into the texture

Exported to games/bowling/art/pins/bone.glb as one mesh at the origin.
"""
import bpy, bmesh, math, os
import numpy as np
from bowl_common import new_obj, pbr, shade_auto, GODOT_ART
from lounge_textures import fbm, grid, lerp, cover, over, save, G, norm01

H = 0.381
PROFILE = [(0.0, 0.0), (0.0258, 0.0), (0.0365, 0.019), (0.0500, 0.057), (0.0605, 0.114),
           (0.0565, 0.165), (0.0435, 0.210), (0.0327, 0.234), (0.03045, 0.239),
           (0.0277, 0.247), (0.0254, 0.254), (0.0228, 0.262), (0.0240, 0.292),
           (0.0300, 0.330), (0.0318, 0.346), (0.0280, 0.365), (0.0160, 0.378), (0.0, 0.381)]
VERTEBRAE = (0.243, 0.258)
EYE_H = 0.352
FRONT = -math.pi / 2           # the face looks down -Y, toward the bowler


def base_r(h):
    hs = [p[1] for p in PROFILE]
    rs = [p[0] for p in PROFILE]
    return float(np.interp(h, hs, rs))


def gauss(x, w):
    return math.exp(-(x / w) ** 2)


def dtheta(a, b):
    return (a - b + math.pi) % math.tau - math.pi


def radius(theta, h):
    r = base_r(h)
    if r <= 0.0:
        return 0.0
    # femur knuckles at the base
    cond = max(0.0, 1.0 - h / 0.075)
    r *= 1.0 + 0.10 * math.cos(2 * theta) * cond
    # a little bony knobbliness everywhere
    r += 0.0012 * math.sin(3 * theta + h * 40) * math.sin(h * 26 + 1.3)
    # vertebra rings, with a spinous process at the back
    for hc in VERTEBRAE:
        r += 0.0042 * gauss(h - hc, 0.0030)
        r += 0.0045 * gauss(dtheta(theta, -FRONT), 0.30) * gauss(h - hc, 0.0045)
    # the skull: deeper front-to-back, narrower at the temples
    s = min(1.0, max(0.0, (h - 0.296) / 0.02))
    r *= 1.0 + s * (0.05 * math.sin(theta) ** 2 - 0.05 * math.cos(theta) ** 2)
    # eye sockets, nose, cheekbones
    for side in (-1, 1):
        r -= 0.0042 * gauss(dtheta(theta, FRONT + side * 0.46), 0.22) * gauss(h - EYE_H, 0.0065)
    r -= 0.0024 * gauss(dtheta(theta, FRONT), 0.12) * gauss(h - 0.338, 0.004)
    r -= 0.0015 * gauss(h - 0.326, 0.003)          # where the jaw meets the skull
    return max(r, 0.0)


def build_mesh(c, name="PIN_bone", loc=(0.0, 0.0, 0.0), sides=40, rings=110):
    bm = bmesh.new()
    uvs = {}
    hs = [H * (0.5 - 0.5 * math.cos(math.pi * j / rings)) for j in range(rings + 1)]
    grid_v = []
    for h in hs:
        row = []
        for i in range(sides + 1):
            th = math.tau * i / sides
            r = radius(th, h)
            v = bm.verts.new((loc[0] + r * math.cos(th), loc[1] + r * math.sin(th), loc[2] + h))
            uvs[v] = (i / sides, h / H)
            row.append(v)
        grid_v.append(row)
    for j in range(rings):
        for i in range(sides):
            a, b = grid_v[j][i], grid_v[j][i + 1]
            cc, d = grid_v[j + 1][i + 1], grid_v[j + 1][i]
            if j == rings - 1:
                bm.faces.new((a, b, d))          # the crown of the head closes to a point
            else:
                bm.faces.new((a, b, cc, d))
    # the base is a ring 51 mm across (a regulation pin's foot), so close it
    # with a flat disc - without this the pin is hollow underneath
    centre = bm.verts.new((loc[0], loc[1], loc[2]))
    uvs[centre] = (0.5, 0.0)
    ring = grid_v[0]
    for i in range(sides):
        bm.faces.new((centre, ring[i + 1], ring[i]))
    layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            loop[layer].uv = uvs[loop.vert]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj(name, bm, c)
    return shade_auto(ob, math.radians(40))      # smooth body, crisp edge round the base


# ================================================================ texture ===
def bone_texture():
    S = 1024
    u, v = grid(S, S)
    th = u * math.tau
    h = v * H
    n1 = fbm(S, S, 6, 6, seed=301)
    n2 = fbm(S, S, 7, 18, seed=302)
    rgb = lerp((0.50, 0.43, 0.31), (0.86, 0.80, 0.65), np.clip(n1 * 0.7 + 0.3, 0, 1))
    # stains pool low and in the crevices
    stain = np.clip((0.09 - h) / 0.09, 0, 1) * 0.5 + np.clip(n2 - 0.6, 0, 1) * 1.2
    rgb = lerp(rgb, (0.32, 0.25, 0.16), np.clip(stain, 0, 0.7))
    # hairline cracks
    crack = (1.0 - np.abs(np.sin(n2 * 38.0 + th * 2.0))) ** 60
    rgb = over(rgb, (0.20, 0.15, 0.10), np.clip(crack * 0.8, 0, 1))
    # vertebra rings: yellower discs with dark gaps between
    for hc in (0.243, 0.258):
        disc = np.exp(-((h - hc) / 0.004) ** 2)
        rgb = lerp(rgb, (0.78, 0.66, 0.44), disc * 0.6)
    for hg in (0.2355, 0.2505, 0.2655):
        rgb = over(rgb, (0.15, 0.10, 0.07), cover(np.abs(h - hg) - 0.0009, 0.0006) * 0.85)
    # the face, on the front of the head (arc-length coordinates, metres)
    dth = (th - (math.tau + FRONT) + math.pi) % math.tau - math.pi
    a = dth * 0.031
    b = h - EYE_H
    emit = np.zeros_like(rgb)
    for side in (-1, 1):
        sock = ((a - side * 0.0135) / 0.0085) ** 2 + (b / 0.0078) ** 2 - 1.0
        rgb = over(rgb, (0.30, 0.22, 0.14), cover(np.abs(sock * 0.01) - 0.001, 0.0006))
        inside = cover(sock * 0.01, 0.0005)
        rgb = lerp(rgb, (0.02, 0.015, 0.02), inside)
        glow = np.clip(1.0 - (((a - side * 0.0135) / 0.004) ** 2 + (b / 0.0036) ** 2), 0, 1)
        emit = over(emit, (0.55, 0.22, 1.0), glow)
    nose = np.maximum(np.abs(a) / 0.0045 + (b + 0.0115) / 0.008, -(b + 0.0135) / 0.003) - 1.0
    rgb = lerp(rgb, (0.03, 0.02, 0.02), cover(nose * 0.006, 0.0005))
    teeth = (b < -0.021) & (b > -0.029) & (np.abs(a) < 0.017)
    gap = np.abs(((a + 0.017) / 0.0034) % 1.0 - 0.5) > 0.40
    rgb[teeth] = (0.80, 0.74, 0.58)
    rgb[teeth & gap] = (0.08, 0.05, 0.03)
    rgb[(np.abs(b + 0.025) < 0.0006) & (np.abs(a) < 0.017)] = (0.10, 0.06, 0.04)
    return save("BWL_BonePin", rgb), save("BWL_BonePinEmit", emit)


def build(c):
    base, emit = bone_texture()
    m = pbr("BWL_BonePinMat", base_img=base, emit_img=emit, emit_str=1.5, rough=0.42)
    ob = build_mesh(c)
    ob.data.materials.append(m)
    return ob, m
