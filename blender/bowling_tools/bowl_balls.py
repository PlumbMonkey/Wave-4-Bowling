"""The three house balls. Each is regulation size (r = 0.1085 m) and built at
*loc*, so the same builders dress the ball returns in the alley.

    The Spectre - a hooded reaper in obsidian with lava cracks
    The P       - black marble, violet lightning, raised silver monogram
    The Skull   - clear smoky resin with a bone skull suspended inside
"""
import bpy, bmesh, math
from mathutils import Vector
from bowl_common import BALL_R, new_obj, pbr, mat, tube, TAU

BALLS = ("spectre", "p", "skull")
NAMES = {"spectre": "The Spectre", "p": "The P", "skull": "The Skull"}
HOLES = [((0.16, 0.35, 1.0), 0.10), ((-0.16, 0.35, 1.0), 0.10), ((0.0, 1.3, 1.0), 0.12)]


def sphere(bm, r, centre=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0), nlon=64, nlat=32, uvs=None):
    """UV sphere whose UVs are exactly the equirect layout the textures use."""
    cx, cy, cz = centre
    sx, sy, sz = scale
    rows = []
    for j in range(nlat + 1):
        lat = math.pi * (j / nlat - 0.5)
        row = []
        for i in range(nlon + 1):
            lon = TAU * i / nlon
            d = (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
            v = bm.verts.new((cx + r * sx * d[0], cy + r * sy * d[1], cz + r * sz * d[2]))
            if uvs is not None:
                uvs[v] = (i / nlon, j / nlat)
            row.append(v)
        rows.append(row)
    for j in range(nlat):
        for i in range(nlon):
            a, b = rows[j][i], rows[j][i + 1]
            c, d = rows[j + 1][i + 1], rows[j + 1][i]
            if j == 0:
                bm.faces.new((a, c, d))
            elif j == nlat - 1:
                bm.faces.new((a, b, d))
            else:
                bm.faces.new((a, b, c, d))
    return bm


def _uv(bm, uvs):
    layer = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for loop in f.loops:
            if loop.vert in uvs:
                loop[layer].uv = uvs[loop.vert]


def _smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def materials(tex):
    sp_b, sp_e = tex["spectre"]
    p_b, p_e, p_o = tex["p"]
    sk_b, sk_e = tex["skull"]
    return {
        "spectre": pbr("BWL_BallSpectreMat", base_img=sp_b, emit_img=sp_e, emit_str=2.5,
                       rough=0.10, metallic=0.1),
        "p": pbr("BWL_BallPMat", base_img=p_b, emit_img=p_e, orm_img=p_o, emit_str=2.2),
        "shell": pbr("BWL_ResinShell", base=(0.14, 0.09, 0.24), rough=0.02, alpha=0.36),
        "bone": pbr("BWL_BoneMat", base_img=sk_b, emit_img=sk_e, emit_str=2.0, rough=0.55),
        "bone_flat": mat("BWL_BoneFlat", (0.52, 0.45, 0.33), rough=0.55),
        "hole": mat("BWL_HoleMat", (0.01, 0.01, 0.012), rough=0.6),
        "plain": {c: mat("BWL_BallPlain_" + c, rgb, rough=0.08, metallic=0.2)
                  for c, rgb in (("violet", (0.22, 0.06, 0.40)), ("emerald", (0.02, 0.28, 0.14)),
                                 ("crimson", (0.35, 0.02, 0.05)), ("midnight", (0.03, 0.05, 0.22)))},
    }


def _holes_geo(bm, loc, depth=0.045):
    """Actual finger holes - needed where the shell is see-through."""
    c = Vector(loc)
    for (hx, hy, hz), ang in HOLES:
        h = Vector((hx, hy, hz)).normalized()
        rad = BALL_R * math.sin(ang)
        top = c + h * (BALL_R * math.cos(ang) + 0.002)
        tube(bm, [top, top - h * depth], rad, sides=12)



def build(kind, loc, c, M, name=None):
    """Build one ball at *loc* in collection *c*. Returns its root empty."""
    name = name or "BALL_" + kind
    root = bpy.data.objects.new(name, None)
    root.location = loc
    root.empty_display_size = 0.15
    c.objects.link(root)
    parts = []
    if kind in ("spectre", "p"):
        bm, uvs = bmesh.new(), {}
        sphere(bm, BALL_R, uvs=uvs)
        _uv(bm, uvs)
        parts.append(_smooth(new_obj(name + "_Shell", bm, c, [M[kind]])))
    elif kind == "skull":
        bm = bmesh.new()
        sphere(bm, BALL_R, nlon=48, nlat=24)
        parts.append(_smooth(new_obj(name + "_Shell", bm, c, [M["shell"]])))
        bm, uvs = bmesh.new(), {}
        sphere(bm, 0.058, centre=(0.0, 0.0, 0.012), scale=(0.90, 1.05, 1.0), uvs=uvs,
               nlon=48, nlat=24)
        _uv(bm, uvs)
        parts.append(_smooth(new_obj(name + "_Skull", bm, c, [M["bone"]])))
        bm = bmesh.new()
        sphere(bm, 0.036, centre=(0.0, -0.012, -0.042), scale=(1.1, 1.0, 0.62), nlon=24, nlat=12)
        parts.append(_smooth(new_obj(name + "_Jaw", bm, c, [M["bone_flat"]])))
        bm = bmesh.new()
        _holes_geo(bm, (0.0, 0.0, 0.0))
        parts.append(new_obj(name + "_Holes", bm, c, [M["hole"]]))
    else:                                           # plain house ball
        bm = bmesh.new()
        sphere(bm, BALL_R, nlon=40, nlat=20)
        parts.append(_smooth(new_obj(name + "_Shell", bm, c, [M["plain"][kind]])))
    for p in parts:
        p.parent = root
    root["ball"] = kind
    return root
