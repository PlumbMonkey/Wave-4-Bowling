"""The Reliquary pin set: polished, cracked bone carved with gothic reliefs,
bronze crown collars at the neck, blue light glowing out of the carvings.
(Reference: games/bowling/art/reference/pins_reliquary.webp)

The outline is the regulation pin, so the Godot collider and mass are
unchanged. Relief is carried by maps - colour, normal, emission, ORM - painted
with numpy, so the carvings read in close-up without adding geometry. The
bronze collars and bands are real geometry, a couple of millimetres proud.

Four designs share one texture atlas (2 x 2 quadrants, one per design):
    1 skull with sweeping rib-wings      2 ribcage and spine
    3 cathedral window                   4 skull under a heart of ribs
Each design faces the bowler (-Y). Every pin carries a spine up its back.
"""
import bpy, bmesh, math
import numpy as np
from bowl_common import new_obj, pbr, mat, shade_auto
from lounge_textures import (fbm, grid, lerp, cover, over, save, G, sd_circle, sd_segment,
                             sd_box, _voronoi_lead)
from bowl_pins import PROFILE, H, base_r

FRONT = 1.5 * math.pi           # angle of the -Y side, in [0, 2pi)
Q = 1024                        # pixels per quadrant
DESIGNS = 4
RELIEF = 0.0016                 # metres of carved depth at full height


# ================================================================ geometry ==
def _bone_surface(bm, variant, sides=40, rings=84):
    uvs = {}
    col, row = variant % 2, variant // 2
    hs = [H * (0.5 - 0.5 * math.cos(math.pi * j / rings)) for j in range(rings + 1)]
    grid_v = []
    for h in hs:
        r = base_r(h)
        line = []
        for i in range(sides + 1):
            th = math.tau * i / sides
            v = bm.verts.new((r * math.cos(th), r * math.sin(th), h))
            uvs[v] = ((col + i / sides) * 0.5, (row + h / H) * 0.5)
            line.append(v)
        grid_v.append(line)
    faces = []
    for j in range(rings):
        for i in range(sides):
            a, b = grid_v[j][i], grid_v[j][i + 1]
            c, d = grid_v[j + 1][i + 1], grid_v[j + 1][i]
            if j == rings - 1:
                faces.append(bm.faces.new((a, b, d)))
            else:
                faces.append(bm.faces.new((a, b, c, d)))
    # close the foot with a flat disc (the base is a 51 mm ring, not a point)
    centre = bm.verts.new((0.0, 0.0, 0.0))
    uvs[centre] = ((col + 0.5) * 0.5, (row + 0.004) * 0.5)
    for i in range(sides):
        faces.append(bm.faces.new((centre, grid_v[0][i + 1], grid_v[0][i])))
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in faces:
        f.material_index = 0
        for loop in f.loops:
            loop[layer].uv = uvs[loop.vert]


def tri_wave(x):
    """0 at the troughs, 1 at the points."""
    return 1.0 - np.abs((x % 1.0) * 2.0 - 1.0)


def _band(bm, h_bottom, h_top, proud=0.0025, n=96, rows=5):
    """A metal band hugging the pin between two edge curves h(theta)."""
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    grid_v = []
    for k in range(rows + 1):
        line = []
        for i in range(n + 1):
            th = math.tau * i / n
            hb, ht = h_bottom(th), h_top(th)
            h = hb + (ht - hb) * k / rows
            r = base_r(h) + proud
            line.append(bm.verts.new((r * math.cos(th), r * math.sin(th), h)))
        grid_v.append(line)
    for k in range(rows):
        for i in range(n):
            f = bm.faces.new((grid_v[k][i], grid_v[k][i + 1], grid_v[k + 1][i + 1], grid_v[k + 1][i]))
            f.material_index = 1
            for loop in f.loops:
                loop[layer].uv = (0.0, 0.0)


def build_mesh(c, variant, name):
    bm = bmesh.new()
    _bone_surface(bm, variant)
    points = 8
    # the crown collar on the neck: points down over the shoulder, up toward the head
    _band(bm, lambda th: 0.262 - 0.030 * tri_wave(th / math.tau * points),
          lambda th: 0.282 + 0.018 * tri_wave(th / math.tau * points + 0.5))
    _band(bm, lambda th: 0.2215, lambda th: 0.2275, proud=0.002, rows=1)     # the ring below it
    _band(bm, lambda th: 0.300, lambda th: 0.304, proud=0.0018, rows=1)      # a fine ring above
    _band(bm, lambda th: 0.004, lambda th: 0.017, proud=0.0016, rows=2)      # the foot
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = new_obj(name, bm, c)
    return shade_auto(ob, math.radians(40))


# ================================================================ texture ===
def _bezier(p0, p1, p2, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in np.linspace(0, 1, n)]


def _curve_sd(X, Y, pts):
    d = np.full(X.shape, 1e3, dtype=G)
    for a, b in zip(pts, pts[1:]):
        d = np.minimum(d, sd_segment(X, Y, a[0], a[1], b[0], b[1]))
    return d


def _raised(sd, width):
    """Rounded relief from a distance field: 1 on the ridge, 0 off it."""
    return np.sqrt(np.clip(1.0 - np.clip(sd, 0, None) / width, 0, 1)) * (sd < width)


def _dome(X, Y, cx, cy, rx, ry):
    q = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
    return np.sqrt(np.clip(1.0 - q, 0, 1))


def _skull(X, Y, cx, cy, s):
    """Height and socket mask of a small carved skull."""
    h = np.maximum(_dome(X, Y, cx, cy, 0.015 * s, 0.017 * s),
                   _dome(X, Y, cx, cy - 0.018 * s, 0.010 * s, 0.007 * s) * 0.8)
    socket = np.zeros_like(X)
    for side in (-1, 1):
        socket = np.maximum(socket, cover(sd_circle(X, Y, cx + side * 0.0056 * s, cy + 0.0005,
                                                    0.0042 * s), 0.0006))
    nose = cover(np.maximum(np.abs(X - cx) / (0.0022 * s) + (Y - (cy - 0.0075 * s)) / (0.004 * s),
                            -(Y - (cy - 0.0105 * s)) / (0.001 * s)) - 1.0, 0.1)
    teeth = ((np.abs(Y - (cy - 0.0175 * s)) < 0.0028 * s) & (np.abs(X - cx) < 0.007 * s)
             & (np.abs(((X - cx) / (0.0017 * s)) % 1.0 - 0.5) > 0.36))
    socket = np.maximum(socket, np.maximum(nose, teeth * 1.0))
    return h, socket


def _design(k, X, Y):
    """(height, glow) of design k, in pin-surface metres (X around, Y up)."""
    hgt = np.zeros_like(X)
    glow = np.zeros_like(X)
    bot, top = 0.036, 0.212
    w = 0.052 * np.clip(np.sin(np.pi * (Y - bot) / (top - bot)), 0, 1) ** 0.6
    frame = np.where((Y > bot) & (Y < top), np.abs(X) - w, 1.0)
    inside = frame < -0.004
    hgt = np.maximum(hgt, _raised(np.abs(frame + 0.004), 0.0022))     # the raised frame
    hgt = np.where(inside, -0.55, hgt)                                  # the carved-out field
    glow = np.where(inside, np.clip(-frame / 0.03, 0, 1) * 0.6, 0.0)

    def rib(p0, p1, p2, width):
        nonlocal hgt
        for side in (-1, 1):
            pts = _bezier((side * p0[0], p0[1]), (side * p1[0], p1[1]), (side * p2[0], p2[1]))
            hgt = np.maximum(hgt, _raised(_curve_sd(X, Y, pts), width))

    if k == 0:                                   # skull with sweeping rib-wings
        for i in range(5):
            y0 = 0.126 - i * 0.015
            rib((0.006, y0), (0.030, y0 + 0.012), (0.034, y0 - 0.020 - i * 0.004), 0.0021)
        sk, so = _skull(X, Y, 0.0, 0.152, 1.0)
        hgt = np.maximum(hgt, sk)
        hgt = np.where(so > 0.5, -0.9, hgt)
        glow = np.maximum(glow, so * 1.0)
    elif k == 1:                                 # ribcage and spine
        for y in np.arange(0.050, 0.195, 0.0115):
            hgt = np.maximum(hgt, _raised(sd_box(X, Y, 0.0, y, 0.0034, 0.0042, r=0.002), 0.0016))
        for i in range(7):
            y0 = 0.182 - i * 0.017
            rib((0.004, y0), (0.028, y0 + 0.006), (0.033, y0 - 0.028), 0.0024 - i * 0.0001)
    elif k == 2:                                 # cathedral window
        wdt, sill, spring = 0.052, 0.058, 0.128
        rise = wdt * math.sqrt(3) / 2
        hw = np.where(Y < spring, wdt / 2,
                      np.sqrt(np.clip(wdt ** 2 - (Y - spring) ** 2, 0, None)) - wdt / 2)
        win = np.where((Y > sill) & (Y < spring + rise), np.abs(X) - hw, 1.0)
        hgt = np.maximum(hgt, _raised(np.abs(win), 0.0024))
        hgt = np.maximum(hgt, _raised(np.where((Y > sill) & (Y < spring + 0.01), np.abs(X), 1.0), 0.0018))
        for sx in (-1, 1):
            lan = np.where((Y > spring - 0.01) & (Y < spring + 0.025),
                           np.abs(np.abs(X - sx * wdt / 4) - (0.013 - (Y - spring + 0.01) * 0.35)), 1.0)
            hgt = np.maximum(hgt, _raised(lan, 0.0014))
        hgt = np.maximum(hgt, _raised(np.abs(sd_circle(X, Y, 0.0, spring + 0.030, 0.008)), 0.0016))
        glass = (win < -0.0035) & (hgt < 0.3)
        glow = np.where(glass, 1.0, glow)
    else:                                        # skull under a heart of ribs
        for i in range(4):
            s = 1.0 - i * 0.2
            rib((0.0, 0.100 + i * 0.006), (0.034 * s, 0.150 + i * 0.012), (0.004, 0.196 - i * 0.004),
                0.0022)
        sk, so = _skull(X, Y, 0.0, 0.080, 0.95)
        hgt = np.maximum(hgt, sk)
        hgt = np.where(so > 0.5, -0.9, hgt)
        glow = np.maximum(glow, so)
        hgt = np.maximum(hgt, _raised(np.where((Y > 0.10) & (Y < 0.19), np.abs(X), 1.0), 0.0014) * 0.7)
    glow = np.where(hgt > 0.25, 0.0, glow)       # only the carved-out hollows glow
    return hgt, glow


def reliquary_textures():
    S = 2 * Q
    base = np.zeros((S, S, 3), dtype=G)
    normal = np.zeros((S, S, 3), dtype=G)
    emit = np.zeros((S, S, 3), dtype=G)
    orm = np.zeros((S, S, 3), dtype=G)
    u, v = grid(Q, Q)
    th = u * math.tau
    hh = v * H
    rr = np.interp(hh, [p[1] for p in PROFILE], [p[0] for p in PROFILE]).astype(G)
    rr = np.maximum(rr, 0.004)
    for k in range(DESIGNS):
        n1 = fbm(Q, Q, 6, 5, seed=400 + k)
        n2 = fbm(Q, Q, 7, 14, seed=410 + k)
        dth_f = (th - FRONT + math.pi) % math.tau - math.pi
        dth_b = (th - (FRONT - math.pi) + math.pi) % math.tau - math.pi
        Xf, Xb = dth_f * rr, dth_b * rr
        hgt, glow = _design(k, Xf * 0.87, hh)          # designs drawn a touch wider
        # a spine up every pin's back
        for y in np.arange(0.045, 0.215, 0.012):
            hgt = np.maximum(hgt, _raised(sd_box(Xb, hh, 0.0, y, 0.0028, 0.0036, r=0.0016), 0.0013) * 0.8)
        # bronze: a diamond with side spikes above the carving
        dia = (np.abs(Xf) / 0.0075 + np.abs(hh - 0.222) / 0.011 - 1.0) * 0.007
        spikes = np.minimum(sd_segment(Xf, hh, -0.020, 0.222, 0.020, 0.222) - 0.0012, 1.0)
        bronze = np.clip(cover(dia, 0.0005) + cover(spikes, 0.0005) * 0.9, 0, 1)
        hgt = np.maximum(hgt, bronze * 0.9)
        # cracks: a sparse Voronoi network in surface metres, plus chips
        rng = np.random.default_rng(420 + k)
        pts = np.stack([rng.uniform(0, 0.4, 26), rng.uniform(0, H, 26)], 1).astype(G)
        lead, _ = _voronoi_lead((th * 0.06).astype(G), hh.astype(G), pts)
        crack = cover(lead - 0.00022 - n2 * 0.0003, 0.00025) * np.clip((n1 - 0.45) * 4.0, 0, 1)
        chips = np.clip((n2 - 0.86) * 10, 0, 1)
        hgt = hgt - crack * 0.35

        # colour: polished ivory marbled with grey, lighter on the ridges, dark in the hollows
        vein = (1.0 - np.abs(np.sin(n1 * 22 + n2 * 9))) ** 18
        col = lerp((0.62, 0.56, 0.45), (0.88, 0.83, 0.72), np.clip(n1 * 0.8 + 0.2, 0, 1))
        grime = np.clip((0.05 - hh) / 0.05, 0, 1) + np.clip(1.0 - np.abs(hh - 0.225) / 0.02, 0, 1) * 0.6
        col = lerp(col, (0.36, 0.30, 0.22), np.clip(grime * 0.45 + (n2 - 0.6) * 0.8, 0, 0.55))
        col = over(col, (0.52, 0.48, 0.44), vein * 0.5)
        col = col * (0.62 + 0.38 * np.clip(hgt + 0.55, 0, 1.4) / 1.4)[..., None]
        col = over(col, (0.22, 0.16, 0.10), np.clip(crack * 0.9 + chips * 0.5, 0, 1))
        col = over(col, (0.03, 0.05, 0.11), np.clip(glow * 1.3, 0, 1) * 0.85)      # dark carved hollows
        col = lerp(col, lerp((0.30, 0.21, 0.10), (0.62, 0.46, 0.22), n1), bronze)

        # normal map from the height field (tangent = around, bitangent = up)
        z = hgt * RELIEF
        dzdx = np.gradient(z, axis=1) / (math.tau * rr / Q)
        dzdy = np.gradient(z, axis=0) / (H / Q)
        nrm = np.stack([-dzdx, -dzdy, np.ones_like(z)], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)

        r0, c0 = (k // 2) * Q, (k % 2) * Q
        base[r0:r0 + Q, c0:c0 + Q] = col
        normal[r0:r0 + Q, c0:c0 + Q] = nrm * 0.5 + 0.5
        emit[r0:r0 + Q, c0:c0 + Q] = lerp((0, 0, 0), (0.22, 0.50, 1.0), np.clip(glow, 0, 1) ** 2.2)
        orm[r0:r0 + Q, c0:c0 + Q] = np.stack([np.ones_like(z), lerp((0.28,), (0.36,), bronze)[..., 0],
                                              bronze], -1)
    return (save("BWL_RelqBase", base), save("BWL_RelqNormal", normal),
            save("BWL_RelqEmit", emit), save("BWL_RelqORM", orm))


def materials(tex):
    base, normal, emit, orm = tex
    m = pbr("BWL_RelqBone", base_img=base, emit_img=emit, emit_str=1.4, orm_img=orm)
    nt = m.node_tree
    t = nt.nodes.new("ShaderNodeTexImage")
    t.name = t.label = "BWL_Normal"
    t.image = normal
    normal.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(t.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    bronze = mat("BWL_RelqBronze", (0.40, 0.28, 0.13), metallic=1.0, rough=0.48)
    return m, bronze


def build(c):
    tex = reliquary_textures()
    bone, bronze = materials(tex)
    obs = []
    for k in range(DESIGNS):
        ob = build_mesh(c, k, "PIN_reliquary_%d" % (k + 1))
        ob.data.materials.append(bone)
        ob.data.materials.append(bronze)
        obs.append(ob)
    return obs
