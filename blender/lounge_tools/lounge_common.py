"""Shared helpers and layout for the Spectral Manor Lounge (Blender 5.2, EEVEE).

The Wave 4 hub: a two-storey gothic hall with four archways - bowling and cards
on the angled walls, billiards and golf either side of the fireplace.

Module names are all prefixed `lounge_` so they can never be shadowed by the
Art Room / Luminarium packages (`common`, `shell`...) in a shared session.

Axes: +Y is the fireplace (back) wall, the hero camera looks down +Y from -Y.
"""
import bpy, bmesh, math, os
from mathutils import Vector

TAU = math.tau
SQ3_2 = math.sqrt(3.0) / 2.0

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                         # ...\blender
TEX_DIR = os.path.join(ROOT, "textures")
BLEND_PATH = os.path.join(ROOT, "Spectral Manor Lounge.blend")

# ---------------------------------------------------------------- layout ----
BACK_Y   =  8.0        # fireplace wall
BACK_HX  =  8.5        # back wall runs x = -8.5 .. 8.5
SIDE_X   = 12.5        # side walls
DIAG_Y   =  4.0        # where the angled walls meet the side walls
FRONT_Y  = -9.0
GALLERY_Z = 8.0        # balcony floor
CEIL_Z   = 16.0
WALL_T   = 0.60
BALC_D   = 1.35        # balcony depth
DOOR_W   = 3.6         # arch opening width (tympanum width)
DOOR_SPRING = 4.0      # doorway lintel / arch spring (hood mould must clear the balcony)
DOOR_INNER_W = 3.0     # the actual door gap inside the frame
ARCH_X   = 5.6         # billiards / golf arch centres on the back wall

# Wall segments, walked anticlockwise seen from above so the outward normal is
# (dy, -dx). Each: (name, p0, p1)
WALLS = [
    ("Back",   (BACK_HX, BACK_Y), (-BACK_HX, BACK_Y)),
    ("DiagL",  (-BACK_HX, BACK_Y), (-SIDE_X, DIAG_Y)),
    ("SideL",  (-SIDE_X, DIAG_Y), (-SIDE_X, FRONT_Y)),
    ("Front",  (-SIDE_X, FRONT_Y), (SIDE_X, FRONT_Y)),
    ("SideR",  (SIDE_X, FRONT_Y), (SIDE_X, DIAG_Y)),
    ("DiagR",  (SIDE_X, DIAG_Y), (BACK_HX, BACK_Y)),
]

# The four game doors: wall, u along the wall from p0, game slug, emblem tint
DOORS = [
    ("Back",  BACK_HX + ARCH_X,  "billiards", "green"),   # x = -5.6
    ("Back",  BACK_HX - ARCH_X,  "golf",      "green"),   # x = +5.6
    ("DiagL", None,              "bowling",   "red"),     # centred
    ("DiagR", None,              "poker",     "red"),
]

FLOOR_POLY = [(-BACK_HX, BACK_Y), (-SIDE_X, DIAG_Y), (-SIDE_X, FRONT_Y),
              (SIDE_X, FRONT_Y), (SIDE_X, DIAG_Y), (BACK_HX, BACK_Y)]
FLOOR_BOUNDS = (-SIDE_X, FRONT_Y, SIDE_X, BACK_Y)     # x0, y0, x1, y1

RUG_C = (0.0, 1.6)     # the seating circle
RUG_R = 4.3
COMPASS_C = (0.0, -4.2)


def wall(name):
    for n, p0, p1 in WALLS:
        if n == name:
            return Vector((*p0, 0.0)), Vector((*p1, 0.0))
    raise KeyError(name)


def wall_frame(name):
    """(p0, direction, outward normal, length) of a wall segment."""
    p0, p1 = wall(name)
    d = p1 - p0
    L = d.length
    d.normalize()
    n = Vector((d.y, -d.x, 0.0))
    return p0, d, n, L


def seg_mapper(name):
    """to_world(u, z, depth) for a wall - depth > 0 goes out through the wall."""
    p0, d, n, L = wall_frame(name)
    return lambda u, z, dep: p0 + d * u + Vector((0.0, 0.0, z)) + n * dep


def door_u(entry):
    wname, u, *_ = entry
    if u is None:
        u = wall_frame(wname)[3] * 0.5
    return u


def at_wall(name, u, inset=0.0, z=0.0):
    """World point on a wall's room face, pulled *inset* metres into the room."""
    return seg_mapper(name)(u, z, -inset)


def wall_yaw(name):
    """Z rotation that turns local +Y into the wall's outward normal."""
    _, _, n, _ = wall_frame(name)
    return math.atan2(-n.x, n.y)


# ------------------------------------------------------------ collections ---
def col(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    tgt = parent or bpy.context.scene.collection
    if c.name not in tgt.children:
        tgt.children.link(c)
    return c


def wipe(prefix):
    for ob in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)


# -------------------------------------------------------------- materials ---
def mat(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5,
        emit=None, emit_str=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Emission Color"].default_value = (*(emit or (0.0, 0.0, 0.0)), 1.0)
    b.inputs["Emission Strength"].default_value = emit_str
    if alpha < 1.0:
        m.surface_render_method = 'BLENDED'
    m.diffuse_color = (*base, alpha)
    return m


def textured(name, image, kind='BASE', base=(0.5, 0.5, 0.5), metallic=0.0,
             rough=0.5, emit_str=0.0, emit=(1.0, 1.0, 1.0)):
    """Principled with *image* driving Base Color and/or Emission Color.

    kind: 'BASE', 'EMIT', or 'BOTH'. glTF-safe - one image node, no maths.
    """
    m = mat(name, base, metallic, rough, emit, emit_str)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.get("LNG_Tex")
    if tex is None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.name = tex.label = "LNG_Tex"
        tex.location = (-430.0, 180.0)
    tex.image = image
    tex.interpolation = 'Smart'
    if kind in ('BASE', 'BOTH'):
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if kind in ('EMIT', 'BOTH'):
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    return m


# ------------------------------------------------------------------ mesh ----
def new_obj(name, bm, collection, materials=()):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    for m in materials:
        me.materials.append(m)
    return ob


def shade_auto(ob, angle=math.radians(35)):
    """5.2 has no SMOOTH_BY_ANGLE modifier - write sharp edges into the mesh."""
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(math.pi) <= angle
    bm.to_mesh(me)
    bm.free()
    return ob


def apply_uvs(bm, uvs):
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            loop[layer].uv = uvs.get(loop.vert, (0.0, 0.0))
    return bm


def planar_uvs(ob, axis='Z', scale=1.0, offset=(0.0, 0.0)):
    """Box-ish projection along one axis - fine for planks, marble, plaster."""
    me = ob.data
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    idx = {'X': (1, 2), 'Y': (0, 2), 'Z': (0, 1)}[axis]
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            layer.data[li].uv = (co[idx[0]] * scale + offset[0],
                                 co[idx[1]] * scale + offset[1])
    return ob


# -------------------------------------------------------------- primitives --
def box(bm, cx, cy, cz, sx, sy, sz, rot_z=0.0):
    hs = (sx * 0.5, sy * 0.5, sz * 0.5)
    ca, sa = math.cos(rot_z), math.sin(rot_z)
    vs = []
    for dz in (-1, 1):
        for dy in (-1, 1):
            for dx in (-1, 1):
                x, y = dx * hs[0], dy * hs[1]
                vs.append(bm.verts.new((cx + x * ca - y * sa,
                                        cy + x * sa + y * ca,
                                        cz + dz * hs[2])))
    b, t = vs[0:4], vs[4:8]
    bm.faces.new((b[0], b[1], b[3], b[2]))
    bm.faces.new((t[2], t[3], t[1], t[0]))
    bm.faces.new((b[0], b[2], t[2], t[0]))
    bm.faces.new((b[3], b[1], t[1], t[3]))
    bm.faces.new((b[1], b[0], t[0], t[1]))
    bm.faces.new((b[2], b[3], t[3], t[2]))
    return bm


def revolve(bm, profile, seg, a0=0.0, span=TAU, centre=(0.0, 0.0, 0.0)):
    """Revolve a 2D (radius, z) profile about a vertical axis through *centre*."""
    cx, cy, cz = centre
    closed = abs(span - TAU) < 1e-9
    steps = seg if closed else seg + 1
    loops = []
    for s in range(steps):
        t = a0 + span * s / seg
        loops.append([bm.verts.new((cx + r * math.cos(t), cy + r * math.sin(t),
                                    cz + z)) for r, z in profile])
    for s in range(seg):
        a, b = loops[s], loops[(s + 1) % len(loops)]
        for i in range(len(profile) - 1):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    return bm


def tube(bm, path, radius, sides=8, cap=True):
    rings, n = [], len(path)
    for i, p in enumerate(path):
        p = Vector(p)
        fwd = Vector(path[min(i + 1, n - 1)]) - Vector(path[max(i - 1, 0)])
        if fwd.length < 1e-9:
            fwd = Vector((0.0, 0.0, 1.0))
        fwd.normalize()
        up = Vector((0.0, 0.0, 1.0))
        if abs(fwd.dot(up)) > 0.98:
            up = Vector((1.0, 0.0, 0.0))
        side = fwd.cross(up).normalized()
        up2 = side.cross(fwd).normalized()
        rings.append([bm.verts.new(p + side * (radius * math.cos(TAU * k / sides))
                                     + up2 * (radius * math.sin(TAU * k / sides)))
                      for k in range(sides)])
    for i in range(n - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if cap:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    return bm


def quad(bm, p0, p1, p2, p3):
    return bm.faces.new([bm.verts.new(p) for p in (p0, p1, p2, p3)])


def grid_panel(bm, origin, du, dv, nu, nv, uvs=None):
    """A flat subdivided quad. origin + du*u + dv*v, u,v in [0,1]."""
    o, du, dv = Vector(origin), Vector(du), Vector(dv)
    rows = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            v = bm.verts.new(o + du * (i / nu) + dv * (j / nv))
            if uvs is not None:
                uvs[v] = (i / nu, j / nv)
            row.append(v)
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((rows[j][i], rows[j][i + 1],
                          rows[j + 1][i + 1], rows[j + 1][i]))
    return bm


# ------------------------------------------------------ arches and walls -----
def arch_halfwidth(z, w, sill, spring):
    """Half-width of an equilateral pointed-arch opening at height *z*."""
    if z < sill - 1e-9:
        return 0.0
    if z <= spring:
        return w * 0.5
    dz = z - spring
    inner = w * w - dz * dz
    if inner <= 0.0:
        return 0.0
    return max(0.0, math.sqrt(inner) - w * 0.5)


def arch_apex(w, spring):
    return spring + w * SQ3_2


def arch_outline(w, sill, spring, n_arc=12):
    """Open outline: up the left jamb, over the arch, down the right jamb."""
    rise = w * SQ3_2
    pts = [(-w * 0.5, sill), (-w * 0.5, spring)]
    for i in range(1, n_arc + 1):
        z = spring + rise * i / n_arc
        pts.append((-arch_halfwidth(z, w, sill, spring), z))
    for i in range(n_arc - 1, 0, -1):
        z = spring + rise * i / n_arc
        pts.append((arch_halfwidth(z, w, sill, spring), z))
    pts += [(w * 0.5, spring), (w * 0.5, sill)]
    return pts


def wall_rows(h, openings, per_arch=10):
    """Z levels for a wall grid, guaranteeing a row at every sill and apex."""
    zs = {0.0, h}
    for uc, w, sill, spring in openings:
        apex = arch_apex(w, spring)
        zs.update((sill, spring, apex))
        for i in range(1, per_arch):
            zs.add(spring + (apex - spring) * i / per_arch)
        zs.add((sill + spring) * 0.5)
    return sorted(round(z, 5) for z in zs if -1e-6 <= z <= h + 1e-6)


def _spans(z, u0, u1, active):
    """Solid horizontal spans at height *z*, given the openings active here."""
    cuts = []
    for uc, w, sill, spring in active:
        hw = arch_halfwidth(z, w, sill, spring)
        cuts.append((uc - hw, uc + hw))
    cuts.sort()
    out, cur = [], u0
    for lo, hi in cuts:
        if lo > cur:
            out.append((cur, lo))
        cur = max(cur, hi)
    if cur < u1:
        out.append((cur, u1))
    return out


def wall_with_openings(bm, to_world, u0, u1, h, thickness, openings,
                       nu=2, per_arch=10):
    """Build a flat wall panel pierced by pointed-arch openings.

    *to_world(u, z, d)* maps wall-local coords to world space, where d is the
    outward depth (0 = room face, thickness = back face). Openings are
    (u_centre, width, sill, spring). Bands are chosen so every band has the
    same span count top and bottom, which keeps the quads well-formed.
    """
    zs = wall_rows(h, openings, per_arch)
    for i in range(len(zs) - 1):
        zb, zt = zs[i], zs[i + 1]
        active = [o for o in openings
                  if o[2] <= zb + 1e-6 and arch_apex(o[1], o[3]) >= zt - 1e-6]
        sb = _spans(zb, u0, u1, active)
        st = _spans(zt, u0, u1, active)
        if len(sb) != len(st):
            continue
        for (b0, b1), (t0, t1) in zip(sb, st):
            if (b1 - b0) < 1e-5 and (t1 - t0) < 1e-5:
                continue
            fb = [b0 + (b1 - b0) * j / nu for j in range(nu + 1)]
            ft = [t0 + (t1 - t0) * j / nu for j in range(nu + 1)]
            vi_b = [bm.verts.new(to_world(u, zb, 0.0)) for u in fb]
            vi_t = [bm.verts.new(to_world(u, zt, 0.0)) for u in ft]
            vo_b = [bm.verts.new(to_world(u, zb, thickness)) for u in fb]
            vo_t = [bm.verts.new(to_world(u, zt, thickness)) for u in ft]
            for j in range(nu):
                bm.faces.new((vi_b[j], vi_b[j + 1], vi_t[j + 1], vi_t[j]))
                bm.faces.new((vo_t[j], vo_t[j + 1], vo_b[j + 1], vo_b[j]))
            for e, flip in ((0, True), (nu, False)):     # jambs / reveals
                q = (vi_b[e], vo_b[e], vo_t[e], vi_t[e])
                bm.faces.new(q[::-1] if flip else q)
            if i == len(zs) - 2:
                bm.faces.new(vi_t + vo_t[::-1])
            if i == 0:
                bm.faces.new(vo_b + vi_b[::-1])
    return bm


def wall_mapper(kind, fixed, flip=False):
    """Return to_world(u, z, d) for an axis-aligned wall.

    kind 'X': wall lies in the YZ plane at x = fixed, u runs along Y.
    kind 'Y': wall lies in the XZ plane at y = fixed, u runs along X.
    *flip* points the outward depth in the negative axis direction.
    """
    s = -1.0 if flip else 1.0
    if kind == 'X':
        return lambda u, z, d: Vector((fixed + s * d, u, z))
    return lambda u, z, d: Vector((u, fixed + s * d, z))


def tri_count():
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or not ob.visible_get():
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        total += sum(len(p.vertices) - 2 for p in me.polygons)
        ev.to_mesh_clear()
    return total
