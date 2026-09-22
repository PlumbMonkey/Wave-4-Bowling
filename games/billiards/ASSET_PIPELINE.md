# Blender Asset Pipeline

Spectral Manor Billiards v0.7B uses Blender-authored visuals over separate, deterministic Godot collision geometry. This keeps the table attractive without letting ornamental details disturb ball physics.

## Files

- `assets/source/spectral_billiards_v07b.blend` — editable Blender 5.2 source scene
- `assets/models/spectral_billiards_table.glb` — table visual imported by Godot
- `assets/models/spectral_billiards_cue.glb` — cue visual imported by Godot
- `assets/textures/` — original generated mahogany, walnut, felt, and leather textures
- `tools/build_v07b_assets.py` — deterministic source, texture, export, and preview generator
- `docs/blender-art-pass-v07b.png` — Blender presentation render
- `docs/production-assets-v07b.png` — verified in-game render

## Rebuild

Close the source scene in Blender before rebuilding it, then run this from the project folder:

```text
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python tools\build_v07b_assets.py
```

The script recreates the `.blend`, both `.glb` exports, and the Blender preview. Open the regenerated `.blend` normally for hand-authored refinement.

## Godot integration

Godot loads the exported table and cue automatically when the `.glb` files are present. The hidden procedural slate, cushions, and pocket areas remain authoritative for collision and rules. If either model is absent, the corresponding procedural visual is used as a safe fallback.

Do not add collision meshes to the exported visual scenes without also reviewing the procedural physics geometry. Duplicate colliders will cause erratic rebounds and pocket detection.
