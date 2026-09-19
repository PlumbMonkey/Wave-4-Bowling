"""The pinsetter, after a Brunswick A-2 / GS: the parts you see move between balls.

    PS_Sweep  - the rake: a board with a rubber lip in a steel channel frame,
                side arms rising to pivot bosses. Origin: the centre of the board.
    PS_Table  - the setting table: a ribbed steel deck, ten spotting cups with
                their tongs, and the two lift rods. Origin: the underside of the
                deck, centred over the pin deck; a pin hangs with its base
                PIN_HANG below it (pinsetter.gd).
    PS_Frame  - the side frames standing on the kickbacks, with the guide rails
                the sweep and table run in. Placed where it stands.

Exported to games/bowling/art/pinsetter/pinsetter.glb; pinsetter.gd drives the
sweep and table (Blender +Y = down the lane = Godot -Z).
"""
import bmesh, math
from bowl_common import (new_obj, shade_auto, box, revolve, tube, mat, pbr, load_png, pin_spots,
                         LANE_HALF, LANE_LEN, DECK_END, TAU)
import bowl_alley

LOGO_ASPECT = 1189 / 446         # textures/PS_Logo.png - the Plumbmonkey logo, cut out

TABLE_Y = 18.68                  # over the middle of the pin deck
CUP_DEPTH = 0.10
PIN_HANG = 0.381 - 0.085         # the pin's head sits 85 mm up inside its cup
FRAME_X = 0.80


def materials():
    return {
        "steel": mat("PS_Steel", (0.085, 0.09, 0.095), metallic=0.75, rough=0.42),
        "paint": mat("PS_Paint", (0.10, 0.12, 0.11), metallic=0.3, rough=0.55),
        "alu": mat("PS_Alu", (0.62, 0.62, 0.64), metallic=1.0, rough=0.3),
        "rubber": mat("PS_Rubber", (0.015, 0.015, 0.017), rough=0.9),
        "cup": mat("PS_Cup", (0.03, 0.03, 0.035), rough=0.45),
        "brass": mat("PS_Brass", (0.55, 0.38, 0.15), metallic=1.0, rough=0.35),
        "board": mat("PS_Board", (0.05, 0.035, 0.03), rough=0.6),
        "logo": pbr("PS_LogoMat", base_img=load_png("PS_Logo"), emit_img=load_png("PS_Logo"),
                    emit_str=1.0, rough=0.4, alpha_from_base=True),
    }


def logo(bm, uvs, centre, h, right, up):
    """A logo decal of height *h*, reading left-to-right along *right*."""
    w = h * LOGO_ASPECT
    cx, cy, cz = centre
    corners = []
    for su, sv in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
        corners.append((cx + right[0] * su * w + up[0] * sv * h,
                        cy + right[1] * su * w + up[1] * sv * h,
                        cz + right[2] * su * w + up[2] * sv * h))
    bowl_alley.uv_quad(bm, corners, uvs)


def build_sweep(M, c):
    steel, rubber, board, brass = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    w = 2 * LANE_HALF + 0.06
    box(board, 0, 0, 0.0, w - 0.04, 0.025, 0.2)                     # the rake board
    box(rubber, 0, -0.005, -0.115, w - 0.02, 0.03, 0.035)           # its rubber lip
    for z in (0.105, -0.095):                                       # channel frame top and bottom
        box(steel, 0, 0, z, w, 0.045, 0.022)
    for s in (-1, 1):
        box(steel, s * w / 2, 0, 0.0, 0.03, 0.05, 0.24)            # end plates
        # side arm up to the pivot, and a brace
        tube(steel, [(s * (w / 2 + 0.02), 0.0, 0.1), (s * (w / 2 + 0.02), 0.0, 0.55),
                     (s * (w / 2 + 0.02), 0.28, 0.74)], 0.018, sides=6)
        tube(steel, [(s * (w / 2 + 0.02), 0.0, 0.3), (s * (w / 2 + 0.02), 0.2, 0.62)], 0.011, sides=6)
        box(steel, s * (w / 2 + 0.02), 0.28, 0.74, 0.05, 0.07, 0.07)   # pivot boss
    for k in range(-4, 5):                                          # bolts along the frame
        for z in (0.105, -0.095):
            revolve(brass, [(0.0, 0.0), (0.007, 0.0), (0.005, 0.004), (0.0, 0.005)], 6,
                    centre=(k * 0.12, -0.023, z))
    decal, duv = bmesh.new(), {}
    logo(decal, duv, (0.0, -0.0145, 0.0), 0.16, (1, 0, 0), (0, 0, 1))
    bowl_alley.set_uvs(decal, duv)
    obs = [shade_auto(new_obj("PS_Sweep", steel, c, [M["paint"]]), math.radians(40))]
    parts = [new_obj("PS_SweepBoard", board, c, [M["board"]]),
             new_obj("PS_SweepRubber", rubber, c, [M["rubber"]]),
             shade_auto(new_obj("PS_SweepBolts", brass, c, [M["brass"]])),
             new_obj("PS_SweepLogo", decal, c, [M["logo"]])]
    for p in parts:
        p.parent = obs[0]
    return obs[0]


def build_table(M, c):
    steel, cups, alu, brass = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    w, d = 2 * LANE_HALF - 0.02, 1.02
    box(steel, 0, 0, 0.015, w, d, 0.03)                             # the deck plate
    for x in (-0.42, 0.0, 0.42):                                    # ribs on top
        box(steel, x, 0, 0.065, 0.04, d, 0.07)
    for y in (-0.42, 0.0, 0.42):
        box(steel, 0, y, 0.055, w, 0.035, 0.05)
    for s in (-1, 1):                                               # lift rods and their collars
        tube(alu, [(s * 0.46, 0.0, 0.03), (s * 0.46, 0.0, 1.6)], 0.018, sides=10)
        revolve(steel, [(0.035, 0.03), (0.035, 0.12), (0.0, 0.12)], 10, centre=(s * 0.46, 0, 0))
    spots = [(x, y - LANE_LEN - (TABLE_Y - LANE_LEN)) for x, y in pin_spots(0.0)]
    for x, y in spots:
        # a spotting cup: a black shell, flared at the mouth
        revolve(cups, [(0.050, 0.0), (0.050, -CUP_DEPTH + 0.01), (0.062, -CUP_DEPTH),
                       (0.066, -CUP_DEPTH + 0.004), (0.058, -0.01), (0.060, 0.0)], 14,
                centre=(x, y, 0.0))
        # the tongs that grip a standing pin by the neck
        for a in (0.0, math.pi):
            ca, sa = math.cos(a), math.sin(a)
            tube(alu, [(x + ca * 0.058, y + sa * 0.058, -0.01), (x + ca * 0.064, y + sa * 0.064, -0.07),
                       (x + ca * 0.045, y + sa * 0.045, -0.105)], 0.005, sides=5)
        revolve(brass, [(0.0, 0.0), (0.012, 0.0), (0.009, 0.008), (0.0, 0.01)], 6, centre=(x, y, 0.03))
    table = shade_auto(new_obj("PS_Table", steel, c, [M["paint"]]), math.radians(40))
    for name, bm, m in (("PS_TableCups", cups, M["cup"]), ("PS_TableRods", alu, M["alu"]),
                        ("PS_TableBolts", brass, M["brass"])):
        p = shade_auto(new_obj(name, bm, c, [m]), math.radians(40))
        p.parent = table
    return table


def build_frame(M, c):
    """Low side frames on the kickbacks around the deck - the guide rails the
    sweep runs in. Kept below the masking so they never hide the arches."""
    steel, alu = bmesh.new(), bmesh.new()
    decal, duv = bmesh.new(), {}
    y0, y1 = 18.05, DECK_END + 0.15
    for s in (-1, 1):
        x = s * FRAME_X
        box(steel, x, (y0 + y1) / 2, 1.07, 0.025, y1 - y0, 0.24)    # side plate on the kickback
        box(steel, x - s * 0.02, (y0 + y1) / 2, 1.2, 0.06, y1 - y0, 0.03)
        for y in (y0 + 0.04, TABLE_Y, y1 - 0.06):                  # uprights
            box(steel, x - s * 0.02, y, 1.07, 0.05, 0.05, 0.24)
        tube(alu, [(x - s * 0.05, y0 + 0.02, 1.17), (x - s * 0.05, y1, 1.17)], 0.012, sides=8)
        logo(decal, duv, (x - s * 0.0135, (y0 + 0.04 + TABLE_Y) / 2, 1.055), 0.15,
             (0, -s, 0), (0, 0, 1))
        for y in (y0 + 0.04, TABLE_Y, y1 - 0.06):
            revolve(alu, [(0.0, 0.0), (0.014, 0.0), (0.01, 0.006), (0.0, 0.008)], 6,
                    centre=(x - s * 0.047, y, 1.0))
    fr = shade_auto(new_obj("PS_Frame", steel, c, [M["paint"]]), math.radians(40))
    rails = shade_auto(new_obj("PS_FrameRails", alu, c, [M["alu"]]), math.radians(40))
    rails.parent = fr
    bowl_alley.set_uvs(decal, duv)
    new_obj("PS_FrameLogo", decal, c, [M["logo"]]).parent = fr
    return fr


def build(c):
    M = materials()
    return build_sweep(M, c), build_table(M, c), build_frame(M, c)
