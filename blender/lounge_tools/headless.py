"""Headless entry point. Never run this while another EEVEE job is going.

    blender -b --factory-startup --python headless.py -- [--bake] [--render hero,bowling] [--pct 50] [--export]

Builds the Lounge from scratch, saves `Spectral Manor Lounge.blend`, then
renders the listed cameras into ../renders/.
"""
import bpy, sys, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lounge_build  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else True
    return default


t0 = time.time()
lounge_build.wipe_scene()
stats = lounge_build.run(bake=bool(opt("--bake", False)))
import lounge_common  # noqa: E402
bpy.ops.wm.save_as_mainfile(filepath=lounge_common.BLEND_PATH)
print("LOUNGE built", stats, "in %.1fs" % (time.time() - t0))

cams = opt("--render")
if cams:
    pct = int(opt("--pct", 50))
    samples = int(opt("--samples", 48))
    out_dir = os.path.join(lounge_common.ROOT, "renders")
    os.makedirs(out_dir, exist_ok=True)
    for name in str(cams).split(","):
        cam = "LNGCAM_" + name.strip().capitalize()
        path = os.path.join(out_dir, "lounge_%s.png" % name.strip().lower())
        t1 = time.time()
        lounge_build.render(path, percent=pct, camera=cam, samples=samples)
        print("LOUNGE rendered", path, "%.1fs" % (time.time() - t1))

if opt("--export"):
    import lounge_export  # noqa: E402
    print("LOUNGE exported", lounge_export.gltf())
