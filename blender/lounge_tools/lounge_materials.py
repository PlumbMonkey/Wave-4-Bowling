"""The Lounge palette. Principled BSDF only, at most one image per material."""
import bpy
from lounge_common import mat, textured


def _alpha_from_tex(m, method='DITHERED'):
    nt = m.node_tree
    tex = nt.nodes.get("LNG_Tex")
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    m.surface_render_method = method
    return m


def build(tex):
    M = {}
    M["floor"] = textured("LNG_Floor", tex["floor"], rough=0.10)
    M["stone"] = textured("LNG_Stone", tex["stone"], rough=0.78)
    M["trim"] = mat("LNG_StoneTrim", (0.085, 0.078, 0.080), rough=0.55)
    M["trim_lt"] = mat("LNG_StoneTrimLight", (0.16, 0.15, 0.15), rough=0.5)
    M["wood"] = textured("LNG_Mahogany", tex["wood"], rough=0.32)
    M["brass"] = mat("LNG_Brass", (0.50, 0.32, 0.12), metallic=1.0, rough=0.34)
    M["gilt"] = mat("LNG_Gilt", (0.80, 0.58, 0.24), metallic=1.0, rough=0.20)
    M["iron"] = mat("LNG_Iron", (0.018, 0.017, 0.017), metallic=0.8, rough=0.45)
    M["soot"] = mat("LNG_Soot", (0.008, 0.007, 0.007), rough=0.95)
    M["velvet"] = textured("LNG_Velvet", tex["velvet"], rough=0.72)
    M["velvet_dk"] = mat("LNG_VelvetDark", (0.10, 0.008, 0.015), rough=0.8)
    M["rug"] = textured("LNG_RugRound", tex["rug_round"], rough=0.95)
    M["rug_rect"] = textured("LNG_RugRect", tex["rug_rect"], rough=0.95)
    M["marble"] = mat("LNG_MarbleTop", (0.32, 0.32, 0.34), rough=0.12)
    M["hearth"] = mat("LNG_Hearth", (0.13, 0.12, 0.12), rough=0.25)
    M["candle"] = mat("LNG_Candle", (0.80, 0.74, 0.60), rough=0.45,
                      emit=(1.0, 0.70, 0.40), emit_str=0.6)
    M["flame"] = _alpha_from_tex(textured("LNG_FlameMat", tex["flame"], 'BOTH',
                                          emit_str=14.0))
    M["glass_blue"] = textured("LNG_GlassBlueMat", tex["glass_blue"], 'BOTH',
                               rough=0.2, emit_str=2.2)
    M["glass_storm"] = textured("LNG_GlassStormMat", tex["glass_storm"], 'BOTH',
                                rough=0.2, emit_str=1.8)
    M["glass_jar"] = mat("LNG_JarGlass", (0.55, 0.28, 0.12), rough=0.1,
                         emit=(1.0, 0.55, 0.22), emit_str=1.2, alpha=0.55)
    M["mirror"] = mat("LNG_Mirror", (0.16, 0.16, 0.19), metallic=1.0, rough=0.05)
    for key, name in (("emb_bowling", "LNG_EmbBowlingMat"),
                      ("emb_billiards", "LNG_EmbBilliardsMat"),
                      ("emb_golf", "LNG_EmbGolfMat"),
                      ("emb_poker", "LNG_EmbPokerMat")):
        M[key] = textured(name, tex[key], 'BOTH', metallic=0.25, rough=0.42,
                          emit_str=0.55)
    M["banner"] = textured("LNG_BannerMat", tex["banner"], rough=0.8)
    M["portrait_a"] = textured("LNG_PortraitAMat", tex["portrait_a"], rough=0.55)
    M["portrait_b"] = textured("LNG_PortraitBMat", tex["portrait_b"], rough=0.55)
    M["ghost"] = mat("LNG_Ghost", (0.50, 0.56, 0.66), rough=0.22,
                     emit=(0.45, 0.62, 1.0), emit_str=0.85, alpha=0.75)
    M["ghost_wisp"] = mat("LNG_GhostWisp", (0.6, 0.75, 1.0), rough=0.3,
                          emit=(0.55, 0.75, 1.0), emit_str=2.2, alpha=0.45)
    M["spirit"] = mat("LNG_SpiritFlame", (0.3, 0.5, 1.0),
                      emit=(0.35, 0.55, 1.0), emit_str=12.0)
    M["spirit_ball"] = mat("LNG_GalaxyBall", (0.10, 0.03, 0.25), rough=0.08,
                           emit=(0.54, 0.17, 0.89), emit_str=3.0)
    M["statue"] = mat("LNG_Bronze", (0.075, 0.068, 0.070), metallic=0.55, rough=0.42)
    M["ceiling"] = mat("LNG_Ceiling", (0.030, 0.024, 0.028), rough=0.9)
    M["felt"] = mat("LNG_Felt", (0.015, 0.20, 0.075), rough=0.92)
    M["wall_red"] = mat("LNG_WallRed", (0.16, 0.014, 0.020), rough=0.8)
    M["wall_green"] = mat("LNG_WallGreen", (0.018, 0.075, 0.042), rough=0.8)
    M["lane"] = textured("LNG_LaneMat", tex["lane"], rough=0.12)
    M["pin"] = mat("LNG_Pin", (0.90, 0.88, 0.84), rough=0.22)
    M["pin_red"] = mat("LNG_PinStripe", (0.55, 0.02, 0.03), rough=0.3)
    M["screen"] = textured("LNG_ScreenMat", tex["golf_screen"], 'BOTH', emit_str=2.5)
    M["turf"] = mat("LNG_Turf", (0.025, 0.14, 0.045), rough=0.95)
    M["shade"] = mat("LNG_Lampshade", (0.55, 0.30, 0.12), rough=0.7,
                     emit=(1.0, 0.50, 0.20), emit_str=0.7)
    M["shade_green"] = mat("LNG_ShadeGreen", (0.02, 0.22, 0.09), rough=0.35,
                           emit=(0.4, 1.0, 0.55), emit_str=0.8)
    M["embers"] = mat("LNG_Embers", (0.08, 0.02, 0.01), rough=0.9,
                      emit=(1.0, 0.28, 0.04), emit_str=4.0)
    M["cushion_gold"] = mat("LNG_CushionGold", (0.40, 0.25, 0.08), rough=0.6)
    M["book"] = mat("LNG_Books", (0.12, 0.04, 0.03), rough=0.7)
    M["chip"] = mat("LNG_Chips", (0.55, 0.40, 0.12), metallic=0.6, rough=0.3)
    return M
