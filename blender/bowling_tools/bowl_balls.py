"""The three house balls. Each is regulation size (r = 0.1085 m) and built at
*loc*, so the same builders dress the ball returns in the alley.

    The Spectre - a hooded reaper in obsidian with lava cracks
    The P       - black marble, violet lightning, raised silver monogram
    The Skull   - clear smoky resin with a real skull suspended inside (CC0 model
                  by CDmir, blender/assets_src/skull_cc0), eyes glowing violet
"""
import bpy, bmesh, math, os
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


SKULL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets_src", "skull_cc0", "skull-obj")
SKULL_FIT = 0.080                 # the skull's bounding sphere, inside the 0.1085 shell
SKULL_EYES = ((-0.26, -0.40, 0.04), (0.26, -0.40, 0.04))   # deep in the sockets, in units of SKULL_FIT


def skull_mesh():
    """The CC0 skull, imported once: turned Z-up, facing -Y, centred and scaled
    to sit inside the ball. Its textures are halved to 1K for the game."""
    me = bpy.data.meshes.get("BWL_SkullReal")
    if me:
        return me
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(SKULL_DIR, "skull-Low4K.obj"))
    ob = [o for o in bpy.data.objects if o not in before][0]
    me = ob.data
    me.transform(ob.matrix_world)                    # bake the importer's Y-up turn
    lo = Vector((min(v.co[i] for v in me.vertices) for i in range(3)))
    hi = Vector((max(v.co[i] for v in me.vertices) for i in range(3)))
    centre = (lo + hi) * 0.5
    rad = max((v.co - centre).length for v in me.vertices)
    k = SKULL_FIT / rad
    for v in me.vertices:
        v.co = (v.co - centre) * k
    me.name = "BWL_SkullReal"
    for p in me.polygons:
        p.use_smooth = True
    bpy.data.objects.remove(ob)
    for img in bpy.data.images:
        if img.name.startswith("Skull-") and img.size[0] > 1024:
            img.scale(1024, 1024)
    return me


def _skull_image(name):
    path = os.path.join(SKULL_DIR, name)
    img = bpy.data.images.get(name) or bpy.data.images.load(path)
    if img.size[0] > 1024:
        img.scale(1024, 1024)
    return img


def skull_material():
    m = pbr("BWL_SkullRealMat", base_img=_skull_image("Skull-Low.png"), rough=0.55)
    nt = m.node_tree
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _skull_image("Skull-Low-normal.png")
    t.image.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(t.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


def _smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def materials(tex):
    sp_b, sp_e = tex["spectre"]
    p_b, p_e, p_o = tex["p"][:3]
    p_n = tex["p"][3] if len(tex["p"]) > 3 else None
    sk_b, sk_e = tex["skull"]
    pm = pbr("BWL_BallPMat", base_img=p_b, emit_img=p_e, orm_img=p_o, emit_str=2.2)
    if p_n is not None:                      # the raised, bevelled steel letter
        nt = pm.node_tree
        for n in [n for n in nt.nodes if n.name in ("BWL_PNormal", "BWL_PNormalMap")]:
            nt.nodes.remove(n)
        t = nt.nodes.new("ShaderNodeTexImage")
        t.name = t.label = "BWL_PNormal"
        t.image = p_n
        p_n.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.name = "BWL_PNormalMap"
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    return {
        "spectre": pbr("BWL_BallSpectreMat", base_img=sp_b, emit_img=sp_e, emit_str=2.5,
                       rough=0.10, metallic=0.1),
        "p": pm,
        "shell": pbr("BWL_ResinShell", base=(0.14, 0.09, 0.24), rough=0.02, alpha=0.36),
        "bone": pbr("BWL_BoneMat", base_img=sk_b, emit_img=sk_e, emit_str=2.0, rough=0.55),
        "bone_flat": mat("BWL_BoneFlat", (0.52, 0.45, 0.33), rough=0.55),
        "skull_real": skull_material(),
        "eye_glow": mat("BWL_EyeGlow", (0.5, 0.2, 1.0), rough=0.3, emit=(0.62, 0.25, 1.0), emit_str=3.5),
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
        sk = bpy.data.objects.new(name + "_Skull", skull_mesh())
        sk.data.materials.clear()
        sk.data.materials.append(M["skull_real"])
        c.objects.link(sk)
        parts.append(sk)
        bm = bmesh.new()                             # a violet glow in each eye socket
        for ex, ey, ez in SKULL_EYES:
            sphere(bm, 0.0062, centre=(ex * SKULL_FIT, ey * SKULL_FIT, ez * SKULL_FIT),
                   nlon=12, nlat=6)
        parts.append(_smooth(new_obj(name + "_Eyes", bm, c, [M["eye_glow"]])))
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
