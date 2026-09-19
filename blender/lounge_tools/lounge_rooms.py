"""The four game rooms seen through the archways. They're stage sets - only as
deep and detailed as the view from the hall needs - but each one says at a
glance which game is behind the door."""
import bpy, bmesh, math
from mathutils import Vector
from lounge_common import (col, wipe, new_obj, shade_auto, box, revolve, tube,
                           DOORS, WALL_T, wall_frame, door_u, TAU)
from lounge_fittings import candle, apply_uvs

PFX = "LNG_Room_"
ROOM_HW, ROOM_D, ROOM_H = 2.8, 8.0, 4.4


class Frame:
    """Local coords for a room: a across the door, b away from the hall."""

    def __init__(self, entry):
        wname = entry[0]
        p0, d, n, L = wall_frame(wname)
        self.p = p0 + d * door_u(entry)
        self.d, self.n = d, n
        self.yaw_d = math.atan2(d.y, d.x)
        self.slug = entry[2]

    def __call__(self, a, b, z=0.0):
        return tuple(self.p + self.d * a + self.n * (WALL_T + b) + Vector((0, 0, z)))

    def box(self, bm, a, b, z, sa, sb, sz, extra_yaw=0.0):
        x, y, zz = self(a, b, z)
        box(bm, x, y, zz, sa, sb, sz, rot_z=self.yaw_d + extra_yaw)

    def revolve(self, bm, prof, seg, a, b, z=0.0):
        revolve(bm, prof, seg, centre=self(a, b, z))


def quad_uv(bm, pts, uvs, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    for v, t in zip(vs, uv):
        uvs[v] = t
    return vs


def shell(F, M, wall_key, floor_key="wood"):
    walls, floor = bmesh.new(), bmesh.new()
    hw, D, H = ROOM_HW, ROOM_D, ROOM_H
    fuv = {}
    quad_uv(floor, [F(-hw, 0), F(hw, 0), F(hw, D), F(-hw, D)], fuv,
            ((0, 0), (1.4, 0), (1.4, 4), (0, 4)))
    apply_uvs(floor, fuv)
    for s in (-1, 1):
        walls.faces.new([walls.verts.new(p) for p in
                         (F(s * hw, 0), F(s * hw, D), F(s * hw, D, H), F(s * hw, 0, H))])
    walls.faces.new([walls.verts.new(p) for p in
                     (F(-hw, D), F(hw, D), F(hw, D, H), F(-hw, D, H))])
    walls.faces.new([walls.verts.new(p) for p in
                     (F(-hw, 0, H), F(hw, 0, H), F(hw, D, H), F(-hw, D, H))])
    new_obj(PFX + F.slug + "_Walls", walls, C, [M[wall_key]])
    new_obj(PFX + F.slug + "_Floor", floor, C, [M[floor_key]])
    # skirting + dado rail in wood
    trim = bmesh.new()
    for s in (-1, 1):
        F.box(trim, s * (hw - 0.03), D / 2, 0.12, 0.06, D, 0.24)
        F.box(trim, s * (hw - 0.03), D / 2, 1.05, 0.05, D, 0.06)
    F.box(trim, 0, D - 0.03, 0.12, hw * 2, 0.06, 0.24)
    new_obj(PFX + F.slug + "_Trim", trim, C, [M["wood"]])


# =============================================================== bowling ===
PIN_PROFILE = [(0.0, 0.0), (0.028, 0.0), (0.045, 0.06), (0.060, 0.13),
               (0.050, 0.20), (0.024, 0.26), (0.020, 0.29), (0.028, 0.33),
               (0.028, 0.36), (0.015, 0.38), (0.0, 0.383)]


def bowling(F, M):
    shell(F, M, "wall_red")
    lane, gut, pins, stripe, ball, brass = (bmesh.new() for _ in range(6))
    uvs = {}
    quad_uv(lane, [F(-0.53, 0.2, 0.02), F(0.53, 0.2, 0.02), F(0.53, 7.6, 0.02),
                   F(-0.53, 7.6, 0.02)], uvs, ((0, 0), (1, 0), (1, 7.4 / 18 * 4),
                                              (0, 7.4 / 18 * 4)))
    apply_uvs(lane, uvs)
    for s in (-1, 1):
        F.box(gut, s * 0.68, 3.9, -0.02, 0.26, 7.4, 0.04)
        F.box(gut, s * 0.84, 3.9, 0.05, 0.06, 7.4, 0.14)
        # the other lanes' capping, dark wood
        F.box(gut, s * 1.8, 3.9, 0.01, 1.9, 7.4, 0.02)
    # 10 pins, head pin nearest
    for row in range(4):
        for k in range(row + 1):
            a = (k - row / 2) * 0.305
            b = 6.55 + row * 0.264
            F.revolve(pins, PIN_PROFILE, 12, a, b, 0.02)
            F.revolve(stripe, [(0.0235, 0.275), (0.0245, 0.285), (0.0215, 0.30)], 12,
                      a, b, 0.02)
    # masking unit over the pin deck
    F.box(gut, 0, 7.45, 1.35, 3.4, 0.25, 0.9)
    F.box(brass, 0, 7.30, 0.92, 3.4, 0.05, 0.05)
    # a galaxy ball waiting on the return
    F.revolve(ball, [(0.0, 0.0)] + [(0.109 * math.sin(math.pi * i / 10),
                                     0.109 - 0.109 * math.cos(math.pi * i / 10))
                                    for i in range(1, 10)] + [(0.0, 0.218)], 16,
              1.45, 0.9, 0.62)
    F.box(gut, 1.45, 1.0, 0.30, 0.45, 1.3, 0.6)
    # two pendant lamps
    for b in (2.5, 5.2):
        x, y, z = F(0, b, ROOM_H)
        tube(brass, [(x, y, z), (x, y, z - 1.1)], 0.01, sides=4)
        revolve(brass, [(0.0, 0.0), (0.22, 0.02), (0.12, 0.2), (0.02, 0.22)][::-1], 16,
                centre=(x, y, z - 1.32))
    new_obj(PFX + "bowling_Lane", lane, C, [M["lane"]])
    new_obj(PFX + "bowling_Gutters", gut, C, [M["wood"]])
    shade_auto(new_obj(PFX + "bowling_Pins", pins, C, [M["pin"]]))
    new_obj(PFX + "bowling_PinStripes", stripe, C, [M["pin_red"]])
    shade_auto(new_obj(PFX + "bowling_Ball", ball, C, [M["spirit_ball"]]))
    shade_auto(new_obj(PFX + "bowling_Brass", brass, C, [M["brass"]]))


# ============================================================= billiards ===
def billiards(F, M):
    shell(F, M, "wall_green")
    wood, felt, balls, shade, brass, books = (bmesh.new() for _ in range(6))
    b0 = 3.9
    F.box(wood, 0, b0, 0.72, 1.62, 2.86, 0.16)              # rail block
    F.box(felt, 0, b0, 0.805, 1.30, 2.56, 0.01)
    for s in (-1, 1):
        for t in (-1, 1):
            F.revolve(wood, [(0.10, 0.0), (0.12, 0.08), (0.07, 0.25), (0.10, 0.45),
                             (0.08, 0.64)], 10, s * 0.68, b0 + t * 1.25)
    F.box(wood, 0, b0, 0.55, 1.4, 2.6, 0.2)
    k = 0
    for row in range(5):
        for i in range(row + 1):
            a = (i - row / 2) * 0.058
            F.revolve(balls, [(0.0, 0.0), (0.02, 0.005), (0.0286, 0.0286),
                              (0.02, 0.052), (0.0, 0.057)], 8, a, b0 + 0.6 + row * 0.05, 0.81)
    F.revolve(balls, [(0.0, 0.0), (0.02, 0.005), (0.0286, 0.0286), (0.02, 0.052),
                      (0.0, 0.057)], 8, 0.0, b0 - 0.75, 0.81)
    for b in (b0 - 0.75, b0 + 0.75):
        x, y, z = F(0, b, ROOM_H)
        tube(brass, [(x, y, z), (x, y, z - 2.3)], 0.01, sides=4)
        revolve(shade, [(0.06, 0.0), (0.12, -0.06), (0.30, -0.26), (0.32, -0.30)], 18,
                centre=(x, y, z - 2.3))
    # a wall of books behind
    for row in range(4):
        for k in range(22):
            h = 0.26 + 0.08 * ((k * 7 + row * 3) % 5) / 4
            F.box(books, -2.1 + k * 0.2, ROOM_D - 0.2, 0.9 + row * 0.62 + h / 2,
                  0.17, 0.26, h)
        F.box(wood, 0, ROOM_D - 0.2, 0.9 + row * 0.62 - 0.02, 4.8, 0.34, 0.04)
    # a cue rack on the side wall
    for i in range(5):
        a0 = -ROOM_HW + 0.05
        x0, y0, z0 = F(a0, 2.2 + i * 0.12, 0.2)
        x1, y1, z1 = F(a0, 2.2 + i * 0.12, 1.65)
        tube(wood, [(x0, y0, z0), (x1, y1, z1)], 0.012, sides=5)
    new_obj(PFX + "billiards_Wood", wood, C, [M["wood"]])
    new_obj(PFX + "billiards_Felt", felt, C, [M["felt"]])
    shade_auto(new_obj(PFX + "billiards_Balls", balls, C, [M["gilt"]]))
    shade_auto(new_obj(PFX + "billiards_Shades", shade, C, [M["shade_green"]]))
    new_obj(PFX + "billiards_Brass", brass, C, [M["brass"]])
    new_obj(PFX + "billiards_Books", books, C, [M["book"]])


# ================================================================== golf ===
def golf(F, M):
    shell(F, M, "wall_green", floor_key="turf")
    scr, mat_, brass, bag = (bmesh.new() for _ in range(4))
    uvs = {}
    quad_uv(scr, [F(-2.3, ROOM_D - 0.08, 0.35), F(2.3, ROOM_D - 0.08, 0.35),
                  F(2.3, ROOM_D - 0.08, 2.94), F(-2.3, ROOM_D - 0.08, 2.94)], uvs)
    apply_uvs(scr, uvs)
    F.box(mat_, 0, 3.0, 0.02, 1.6, 1.6, 0.03)
    F.box(brass, 0, ROOM_D - 0.10, 2.97, 4.7, 0.06, 0.06)
    F.box(brass, 0, ROOM_D - 0.10, 0.32, 4.7, 0.06, 0.06)
    F.revolve(bag, [(0.0, 0.0), (0.14, 0.0), (0.15, 0.4), (0.13, 0.85),
                    (0.0, 0.86)], 12, 1.8, 2.0)
    for i in range(5):
        x0, y0, z0 = F(1.8 + (i - 2) * 0.04, 2.0 + (i % 2) * 0.05, 0.8)
        tube(brass, [(x0, y0, z0), (x0 + 0.02 * (i - 2), y0, z0 + 0.35)], 0.01, sides=4)
    new_obj(PFX + "golf_Screen", scr, C, [M["screen"]])
    new_obj(PFX + "golf_TeeMat", mat_, C, [M["felt"]])
    new_obj(PFX + "golf_Brass", brass, C, [M["brass"]])
    new_obj(PFX + "golf_Bag", bag, C, [M["velvet_dk"]])


# ================================================================= poker ===
def poker(F, M):
    shell(F, M, "wall_red")
    wood, felt, chips, vel, brass, wax, fl = (bmesh.new() for _ in range(7))
    fuv = {}
    b0 = 4.0
    F.revolve(felt, [(0.0, 0.0), (1.02, 0.0), (1.02, 0.01), (0.0, 0.01)][::-1], 32,
              0, b0, 0.78)
    x, y, z = F(0, b0, 0.80)
    ring = [(x + 1.10 * math.cos(TAU * k / 48), y + 1.10 * math.sin(TAU * k / 48), z)
            for k in range(49)]
    tube(wood, ring, 0.09, sides=8, cap=False)
    F.revolve(wood, [(0.45, 0.0), (0.45, 0.05), (0.14, 0.12), (0.10, 0.6),
                     (0.5, 0.74), (0.0, 0.78)], 16, 0, b0)
    for k in range(6):
        ang = TAU * k / 6 + 0.3
        cx, cy = x + 1.55 * math.cos(ang), y + 1.55 * math.sin(ang)
        box(vel, cx, cy, 0.48, 0.52, 0.52, 0.14, rot_z=ang)
        bx, by = x + 1.82 * math.cos(ang), y + 1.82 * math.sin(ang)
        box(vel, bx, by, 0.85, 0.10, 0.52, 0.72, rot_z=ang)
        for lx, ly in ((0.2, 0.2), (-0.2, 0.2), (0.2, -0.2), (-0.2, -0.2)):
            ca, sa = math.cos(ang), math.sin(ang)
            px = cx + lx * ca - ly * sa
            py = cy + lx * sa + ly * ca
            tube(wood, [(px, py, 0.0), (px, py, 0.42)], 0.025, sides=5)
        # a stack of chips in front of each seat
        chx, chy = x + 0.78 * math.cos(ang), y + 0.78 * math.sin(ang)
        revolve(chips, [(0.0, 0.0), (0.02, 0.0), (0.02, 0.018 * (2 + k % 4)),
                        (0.0, 0.018 * (2 + k % 4))], 10, centre=(chx, chy, 0.79))
    # small candle chandelier
    x, y, zc = F(0, b0, ROOM_H)
    tube(brass, [(x, y, zc), (x, y, zc - 1.4)], 0.012, sides=4)
    ring = [(x + 0.6 * math.cos(TAU * k / 32), y + 0.6 * math.sin(TAU * k / 32),
             zc - 1.5) for k in range(33)]
    tube(brass, ring, 0.02, sides=6, cap=False)
    for k in range(8):
        a = TAU * k / 8
        candle(wax, fl, fuv, x + 0.6 * math.cos(a), y + 0.6 * math.sin(a), zc - 1.48)
    # drapes on the back wall
    for s in (-1, 1):
        F.box(vel, s * 1.9, ROOM_D - 0.12, 2.2, 1.0, 0.1, 4.4)
    apply_uvs(fl, fuv)
    new_obj(PFX + "poker_Wood", wood, C, [M["wood"]])
    new_obj(PFX + "poker_Felt", felt, C, [M["felt"]])
    new_obj(PFX + "poker_Chips", chips, C, [M["chip"]])
    new_obj(PFX + "poker_Velvet", vel, C, [M["velvet_dk"]])
    new_obj(PFX + "poker_Brass", brass, C, [M["brass"]])
    new_obj(PFX + "poker_Candles", wax, C, [M["candle"]])
    new_obj(PFX + "poker_Flames", fl, C, [M["flame"]])


C = None


def build(M):
    global C
    C = col("LNG_GameRooms", col("Lounge"))
    wipe(PFX)
    builders = {"bowling": bowling, "billiards": billiards, "golf": golf,
                "poker": poker}
    frames = {}
    for entry in DOORS:
        F = Frame(entry)
        builders[F.slug](F, M)
        frames[F.slug] = F
    for ob in C.objects:
        ob["game"] = ob.name.split("_")[2]
    return frames
