"""glTF export of the Lounge collection for the three.js hub.

Materials are plain Principled BSDF with baked PNGs, so nothing needs baking.
glTF has no area lights: the window washes, fire spill and top fill are dropped
and must be recreated in three.js (RectAreaLight) or left to the emissives.
Objects carry a `game` custom property (emblems + game rooms) that survives as
glTF extras - the hub uses it for click-to-enter.
"""
import bpy, os
from lounge_common import ROOT


def gltf(path=None, lights=True, cameras=True):
    path = path or os.path.join(ROOT, "export", "spectral_manor_lounge.glb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    root = bpy.data.collections.get("Lounge")
    if root is None:
        raise RuntimeError("no Lounge collection - run lounge_build first")
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    n = 0
    for ob in root.all_objects:
        if (ob.type == 'LIGHT' and not lights) or (ob.type == 'CAMERA' and not cameras):
            continue
        ob.select_set(True)
        n += 1
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_lights=lights, export_cameras=cameras,
        export_extras=True, export_materials='EXPORT', export_image_format='AUTO',
        export_normals=True)
    return {"path": path, "objects": n,
            "bytes": os.path.getsize(path) if os.path.exists(path) else None}
