"""Generate the Spectral Manor v0.7B billiards table and cue with Blender 5.2.

Outputs are deterministic so the editable .blend and runtime GLBs can be rebuilt.
Run with: blender --background --python tools/build_v07b_assets.py
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets" / "source"
MODEL_DIR = ROOT / "assets" / "models"
TEXTURE_DIR = ROOT / "assets" / "textures"
PREVIEW_DIR = ROOT / "docs"
BLEND_PATH = SOURCE_DIR / "spectral_billiards_v07b.blend"
TABLE_GLB = MODEL_DIR / "spectral_billiards_table.glb"
CUE_GLB = MODEL_DIR / "spectral_billiards_cue.glb"
PREVIEW_PATH = PREVIEW_DIR / "blender-art-pass-v07b.png"

TABLE_LENGTH = 8.8
TABLE_WIDTH = 4.4
FELT_Z = 0.92


def make_surface_texture(name: str, kind: str, size=256):
    path = TEXTURE_DIR / f"{name}.png"
    image = bpy.data.images.new(name, width=size, height=size, alpha=True)
    pixels = []
    for y in range(size):
        for x in range(size):
            u = x / size
            v = y / size
            if kind == "mahogany":
                grain = 0.56 + 0.22 * math.sin(u * 72.0 + math.sin(v * 15.0) * 2.8) + 0.08 * math.sin(u * 211.0)
                pore = 0.90 if math.sin(u * 463.0 + v * 71.0) > -0.88 else 0.48
                pixels.extend((0.25 * grain * pore, 0.045 * grain * pore, 0.025 * grain * pore, 1.0))
            elif kind == "walnut":
                grain = 0.52 + 0.20 * math.sin(u * 58.0 + math.sin(v * 19.0) * 2.0) + 0.07 * math.sin(u * 173.0)
                pixels.extend((0.075 * grain, 0.021 * grain, 0.018 * grain, 1.0))
            elif kind == "felt":
                fiber = 0.92 + 0.06 * math.sin(x * 1.73 + y * 2.31) + 0.025 * math.sin(x * 5.17 - y * 3.11)
                pixels.extend((0.018 * fiber, 0.24 * fiber, 0.13 * fiber, 1.0))
            else:
                pebble = 0.72 + 0.12 * math.sin(x * 2.9 + y * 1.7) * math.sin(x * 0.8 - y * 2.4)
                pixels.extend((0.018 * pebble, 0.012 * pebble, 0.016 * pebble, 1.0))
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return image


def material(name: str, color: tuple[float, float, float, float], metallic=0.0, roughness=0.4, texture=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if texture is not None:
        image_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        image_node.image = texture
        image_node.interpolation = "Linear"
        mat.node_tree.links.new(image_node.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def collection(name: str):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj, target):
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


def bevel_cube(name, location, dimensions, mat, target, bevel=0.06, rotation=None):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation or (0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel_mod = obj.modifiers.new("Soft carved edges", "BEVEL")
    bevel_mod.width = bevel
    bevel_mod.segments = 3
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    return obj


def cylinder(name, location, radius, depth, mat, target, vertices=32, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation or (0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    bevel_mod = obj.modifiers.new("Rounded edge", "BEVEL")
    bevel_mod.width = min(radius * 0.12, depth * 0.16)
    bevel_mod.segments = 2
    move_to_collection(obj, target)
    return obj


def uv_sphere(name, location, scale, mat, target):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    return obj


def torus(name, location, major, minor, mat, target, rotation=None, scale=None):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major,
        minor_radius=minor,
        major_segments=48,
        minor_segments=12,
        location=location,
        rotation=rotation or (0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    if scale:
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to_collection(obj, target)
    return obj


def curve_strand(name, points, bevel_depth, mat, target):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    obj.data.materials.append(mat)
    target.objects.link(obj)
    return obj


def arc_tube(name, center, radius, start_angle, end_angle, bevel_depth, mat, target, z):
    points = []
    segments = 32
    for index in range(segments + 1):
        angle = start_angle + (end_angle - start_angle) * index / segments
        points.append(Vector((center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius, z)))
    return curve_strand(name, points, bevel_depth, mat, target)


def add_cut_felt_slate(felt, target):
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.855))
    slate = bpy.context.object
    slate.name = "Table_Slate"
    slate.dimensions = (8.8, 4.4, 0.13)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    slate.data.materials.append(felt)
    move_to_collection(slate, target)
    pocket_centers = [(-4.4, -2.2), (0, -2.2), (4.4, -2.2), (-4.4, 2.2), (0, 2.2), (4.4, 2.2)]
    for index, (x, y) in enumerate(pocket_centers):
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.29, depth=0.40, location=(x, y, 0.88))
        cutter = bpy.context.object
        cutter.name = f"PocketCut_{index}"
        modifier = slate.modifiers.new(f"Pocket opening {index}", "BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        bpy.context.view_layer.objects.active = slate
        slate.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    bevel_mod = slate.modifiers.new("Slate edge softness", "BEVEL")
    bevel_mod.width = 0.018
    bevel_mod.segments = 2
    return slate


def add_pocket_surrounds(wood, brass, target):
    pockets = [(-4.4, -2.2), (0, -2.2), (4.4, -2.2), (-4.4, 2.2), (0, 2.2), (4.4, 2.2)]
    for index, (x, y) in enumerate(pockets):
        if x == 0:
            exterior = math.pi / 2.0 if y > 0 else -math.pi / 2.0
            start = exterior - math.pi / 2.0
            end = exterior + math.pi / 2.0
        else:
            interior = math.atan2(-math.copysign(1.0, y), -math.copysign(1.0, x))
            start = interior + math.pi / 4.0
            end = interior + math.tau - math.pi / 4.0
        arc_tube(f"Pocket{index}_WoodSurround", (x, y), 0.31, start, end, 0.09, wood, target, 0.965)
        arc_tube(f"Pocket{index}_BrassSurround", (x, y), 0.31, start, end, 0.016, brass, target, 1.045)


def add_leg(index, x, y, wood, brass, target):
    bevel_cube(f"Leg{index}_Capital", (x, y, 0.73), (0.66, 0.66, 0.18), wood, target, 0.10)
    cylinder(f"Leg{index}_Column", (x, y, 0.43), 0.24, 0.60, wood, target, 48)
    cylinder(f"Leg{index}_CollarTop", (x, y, 0.66), 0.35, 0.09, brass, target, 48)
    cylinder(f"Leg{index}_CollarMid", (x, y, 0.43), 0.29, 0.055, brass, target, 48)
    cylinder(f"Leg{index}_CollarLow", (x, y, 0.20), 0.31, 0.09, brass, target, 48)
    uv_sphere(f"Leg{index}_Bulb", (x, y, 0.42), (0.35, 0.35, 0.26), wood, target)
    torus(f"Leg{index}_Filigree", (x, y, 0.43), 0.245, 0.018, brass, target, scale=(1.0, 1.0, 0.65))
    for claw in range(4):
        angle = claw * math.tau / 4.0 + math.pi / 4.0
        cx = x + math.cos(angle) * 0.28
        cy = y + math.sin(angle) * 0.28
        foot = uv_sphere(f"Leg{index}_Claw{claw}", (cx, cy, 0.085), (0.25, 0.17, 0.105), wood, target)
        foot.rotation_euler.z = angle
        torus(f"Leg{index}_ClawBand{claw}", (cx, cy, 0.10), 0.105, 0.014, brass, target, scale=(1.3, 0.78, 0.45))


def add_pocket(index, x, y, brass, leather, target):
    cylinder(f"Pocket{index}_Void", (x, y, FELT_Z - 0.025), 0.18, 0.05, leather, target, 40)
    torus(f"Pocket{index}_Rim", (x, y, FELT_Z - 0.012), 0.195, 0.027, brass, target, scale=(1.0, 1.0, 0.42))
    top_z = FELT_Z - 0.055
    bottom_z = FELT_Z - 0.43
    for strand in range(12):
        angle = strand * math.tau / 12.0
        lower = angle + 0.24
        points = [
            Vector((x + math.cos(angle) * 0.17, y + math.sin(angle) * 0.17, top_z)),
            Vector((x + math.cos(angle + 0.12) * 0.15, y + math.sin(angle + 0.12) * 0.15, (top_z + bottom_z) * 0.5)),
            Vector((x + math.cos(lower) * 0.105, y + math.sin(lower) * 0.105, bottom_z)),
        ]
        curve_strand(f"Pocket{index}_NetV{strand}", points, 0.006, leather, target)
    for ring in range(3):
        z = top_z - (ring + 1) * 0.09
        radius = 0.17 - (ring + 1) * 0.018
        torus(f"Pocket{index}_NetRing{ring}", (x, y, z), radius, 0.0055, leather, target)


def add_apron_ornament(side, wood_y, brass, target):
    for x in (-3.0, -1.5, 0.0, 1.5, 3.0):
        torus(
            f"ApronMedallion_{side}_{x:+.1f}",
            (x, wood_y, 0.57),
            0.17,
            0.022,
            brass,
            target,
            rotation=(math.pi / 2.0, 0.0, 0.0),
            scale=(1.0, 1.35, 1.0),
        )


def add_long_apron_panels(side, y, dark_wood, brass, target):
    outward = -1.0 if y < 0 else 1.0
    face_y = y + outward * 0.13
    for index, x in enumerate((-3.55, -1.78, 0.0, 1.78, 3.55)):
        bevel_cube(f"LongApronInset_{side}_{index}", (x, face_y, 0.56), (1.42, 0.035, 0.285), dark_wood, target, 0.035)
        torus(
            f"LongApronRose_{side}_{index}",
            (x, face_y + outward * 0.025, 0.56),
            0.13,
            0.016,
            brass,
            target,
            rotation=(math.pi / 2.0, 0.0, 0.0),
            scale=(1.0, 1.28, 1.0),
        )
        for wing in (-1.0, 1.0):
            bevel_cube(
                f"LongApronVine_{side}_{index}_{wing:+.0f}",
                (x + wing * 0.23, face_y + outward * 0.027, 0.56),
                (0.29, 0.018, 0.018),
                brass,
                target,
                0.008,
                rotation=(0.0, wing * math.radians(18), 0.0),
            )


def add_sights(brass, ivory, target):
    for y in (-2.34, 2.34):
        for index, x in enumerate((-3.30, -2.20, -1.10, 1.10, 2.20, 3.30)):
            sight_mat = ivory if index % 2 == 0 else brass
            bevel_cube(
                f"LongRailSight_{x:+.2f}_{y:+.2f}",
                (x, y, 1.137),
                (0.085, 0.085, 0.018),
                sight_mat,
                target,
                0.014,
                rotation=(0.0, 0.0, math.pi / 4.0),
            )
    for x in (-4.56, 4.56):
        for index, y in enumerate((-1.30, -0.43, 0.43, 1.30)):
            sight_mat = brass if index % 2 == 0 else ivory
            bevel_cube(
                f"EndRailSight_{x:+.2f}_{y:+.2f}",
                (x, y, 1.137),
                (0.085, 0.085, 0.018),
                sight_mat,
                target,
                0.014,
                rotation=(0.0, 0.0, math.pi / 4.0),
            )


def build_table(target, mats):
    wood, dark_wood, brass, felt, leather, ivory = mats
    bevel_cube("Table_LongApron_Front", (0, -2.55, 0.57), (9.54, 0.30, 0.52), wood, target, 0.09)
    bevel_cube("Table_LongApron_Back", (0, 2.55, 0.57), (9.54, 0.30, 0.52), wood, target, 0.09)
    bevel_cube("Table_EndApron_Left", (-4.62, 0, 0.57), (0.30, 4.82, 0.52), wood, target, 0.09)
    bevel_cube("Table_EndApron_Right", (4.62, 0, 0.57), (0.30, 4.82, 0.52), wood, target, 0.09)
    add_cut_felt_slate(felt, target)
    bevel_cube("Table_UnderRail", (0, 0, 0.74), (9.52, 5.12, 0.20), wood, target, 0.09)
    for y in (-2.34, 2.34):
        for x in (-2.25, 2.25):
            bevel_cube(f"LongRail_{x:+.2f}_{y:+.2f}", (x, y, 1.01), (3.72, 0.42, 0.24), wood, target, 0.075)
            bevel_cube(f"Cushion_{x:+.2f}_{y:+.2f}", (x, y - math.copysign(0.17, y), 1.00), (3.64, 0.12, 0.16), felt, target, 0.035)
            bevel_cube(f"LongRailBrass_{x:+.2f}_{y:+.2f}", (x, y + math.copysign(0.205, y), 0.975), (3.54, 0.026, 0.075), brass, target, 0.012)
    for x in (-4.56, 4.56):
        bevel_cube(f"EndRail_{x:+.2f}", (x, 0, 1.01), (0.42, 3.60, 0.24), wood, target, 0.075)
        bevel_cube(f"EndCushion_{x:+.2f}", (x - math.copysign(0.17, x), 0, 1.00), (0.12, 3.48, 0.16), felt, target, 0.035)
        bevel_cube(f"EndRailBrass_{x:+.2f}", (x + math.copysign(0.205, x), 0, 0.975), (0.026, 3.32, 0.075), brass, target, 0.012)
    for idx, (x, y) in enumerate(((-3.75, -1.72), (-3.75, 1.72), (3.75, -1.72), (3.75, 1.72))):
        add_leg(idx, x, y, wood, brass, target)
    pockets = [(-4.4, -2.2), (0, -2.2), (4.4, -2.2), (-4.4, 2.2), (0, 2.2), (4.4, 2.2)]
    for idx, (x, y) in enumerate(pockets):
        add_pocket(idx, x, y, brass, leather, target)
    add_pocket_surrounds(wood, brass, target)
    for x, y in ((-4.70, -2.46), (-4.70, 2.46), (4.70, -2.46), (4.70, 2.46)):
        bevel_cube(f"CornerCap_{x:+.1f}_{y:+.1f}", (x, y, 0.93), (0.30, 0.30, 0.105), brass, target, 0.07, rotation=(0, 0, math.pi / 4.0))
        torus(f"CornerCrown_{x:+.1f}_{y:+.1f}", (x, y, 0.99), 0.13, 0.018, dark_wood, target, scale=(1.0, 1.0, 0.45))
    add_long_apron_panels("Front", -2.55, dark_wood, brass, target)
    add_long_apron_panels("Back", 2.55, dark_wood, brass, target)
    add_sights(brass, ivory, target)


def cue_segment(name, center_x, length, r_left, r_right, mat, target):
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r_left, radius2=r_right, depth=length, location=(center_x, 0, 0), rotation=(0, math.pi / 2.0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    bevel_mod = obj.modifiers.new("Cue edge", "BEVEL")
    bevel_mod.width = 0.006
    bevel_mod.segments = 2
    move_to_collection(obj, target)
    return obj


def build_cue(target, mats):
    ebony, burgundy, leather, maple, ivory, tip_blue, brass = mats
    cue_segment("Cue_Butt", -0.78, 0.94, 0.057, 0.047, ebony, target)
    cue_segment("Cue_Inlay", -0.20, 0.22, 0.048, 0.044, burgundy, target)
    cue_segment("Cue_LeatherWrap", 0.14, 0.46, 0.044, 0.039, leather, target)
    cue_segment("Cue_MapleShaft", 0.83, 0.92, 0.038, 0.022, maple, target)
    cue_segment("Cue_Ferrule", 1.34, 0.10, 0.023, 0.022, ivory, target)
    cue_segment("Cue_ChalkedTip", 1.4125, 0.045, 0.022, 0.020, tip_blue, target)
    cylinder("Cue_ButtCap", (-1.256, 0, 0), 0.058, 0.012, brass, target, 32, rotation=(0, math.pi / 2.0, 0))
    for offset in (-0.43, -0.35):
        torus("Cue_BrassRing", (offset, 0, 0), 0.045, 0.007, brass, target, rotation=(0, math.pi / 2.0, 0))


def select_collection(col):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in col.all_objects:
        obj.select_set(True)


def export_collection(col, path):
    select_collection(col)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True, export_yup=True, export_materials="EXPORT")


def add_preview_scene(cue_collection, dark_wood):
    bevel_cube("PreviewFloor", (0, 0, -0.08), (14, 10, 0.16), dark_wood, preview_collection, 0.03)
    cue_root = bpy.data.objects.new("CuePreviewRoot", None)
    preview_collection.objects.link(cue_root)
    for obj in cue_collection.objects:
        obj.parent = cue_root
    cue_root.location = (-0.6, -3.05, 1.18)
    cue_root.rotation_euler.z = math.radians(8)
    bpy.ops.object.light_add(type="AREA", location=(0, 0, 6.8))
    key = bpy.context.object
    key.name = "ChandelierGlow"
    key.data.energy = 1350
    key.data.shape = "DISK"
    key.data.size = 5.0
    key.data.color = (1.0, 0.55, 0.24)
    move_to_collection(key, preview_collection)
    bpy.ops.object.light_add(type="AREA", location=(-4.8, -4.0, 3.2), rotation=(math.radians(58), 0, math.radians(-42)))
    fill = bpy.context.object
    fill.name = "MoonFill"
    fill.data.energy = 900
    fill.data.size = 4.0
    fill.data.color = (0.32, 0.56, 1.0)
    move_to_collection(fill, preview_collection)
    bpy.ops.object.camera_add(location=(10.8, -11.8, 8.1))
    camera = bpy.context.object
    camera.name = "ArtPassCamera"
    move_to_collection(camera, preview_collection)
    direction = Vector((0, 0, 0.65)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 52
    bpy.context.scene.camera = camera


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW_PATH)
    scene.world.color = (0.004, 0.006, 0.012)
    scene.view_settings.look = "AgX - Medium High Contrast"


if __name__ == "__main__":
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    table_collection = collection("TABLE_ASSET")
    cue_collection = collection("CUE_ASSET")
    preview_collection = collection("PREVIEW_ONLY")
    mahogany_texture = make_surface_texture("spectral_mahogany", "mahogany")
    walnut_texture = make_surface_texture("spectral_walnut", "walnut")
    felt_texture = make_surface_texture("spectral_felt", "felt")
    leather_texture = make_surface_texture("spectral_leather", "leather", 128)
    wood = material("Mahogany", (0.12, 0.018, 0.012, 1), metallic=0.12, roughness=0.27, texture=mahogany_texture)
    dark_wood = material("Carved Dark Walnut", (0.025, 0.009, 0.008, 1), metallic=0.04, roughness=0.36, texture=walnut_texture)
    brass = material("Antique Brass", (0.42, 0.19, 0.045, 1), metallic=0.88, roughness=0.19)
    felt = material("Ectoplasm Green Felt", (0.012, 0.19, 0.105, 1), metallic=0.0, roughness=0.88, texture=felt_texture)
    leather = material("Black Leather", (0.008, 0.006, 0.009, 1), metallic=0.0, roughness=0.78, texture=leather_texture)
    burgundy = material("Bloodstone Inlay", (0.28, 0.008, 0.018, 1), metallic=0.22, roughness=0.18)
    maple = material("Maple Shaft", (0.69, 0.48, 0.24, 1), metallic=0.02, roughness=0.31)
    ivory = material("Ferrule Ivory", (0.86, 0.78, 0.62, 1), metallic=0.0, roughness=0.22)
    tip_blue = material("Chalked Tip", (0.025, 0.22, 0.35, 1), metallic=0.0, roughness=0.66)
    build_table(table_collection, (wood, dark_wood, brass, felt, leather, ivory))
    build_cue(cue_collection, (dark_wood, burgundy, leather, maple, ivory, tip_blue, brass))
    export_collection(table_collection, TABLE_GLB)
    export_collection(cue_collection, CUE_GLB)
    add_preview_scene(cue_collection, dark_wood)
    setup_render()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    bpy.ops.render.render(write_still=True)
    print(f"BLEND={BLEND_PATH}")
    print(f"TABLE_GLB={TABLE_GLB}")
    print(f"CUE_GLB={CUE_GLB}")
    print(f"PREVIEW={PREVIEW_PATH}")
