# Open-source evaluation

No third-party source code is currently copied into the runtime. The following projects informed the architecture or remain candidates for later integration.

## Godot Jolt

- Source: https://github.com/godot-jolt/godot-jolt
- License: MIT
- Decision: use the Jolt module already built into Godot 4.7.2. The standalone extension documents support through Godot 4.6 and is in maintenance mode, so it is not vendored.

## BreakoutShot

- Source: https://github.com/danielKlmr/BreakoutShot
- License: MIT, Copyright (c) 2023 Daniel Kulmer
- Decision: its animated dotted `Path2D` guide inspired the original 3D dotted-guide implementation in this project. No source was copied; the source project targets Godot 4.1 and is 2D.

## GIF Replay Recorder

- Source: https://github.com/thepolypusher/GodotGIFReplayRecorder
- License: MIT, Copyright (c) 2026 Punch Up Games
- Decision: candidate for optional shareable GIF export. It captures compressed viewport frames and does not replace the transform-state buffer required for cinematic camera replay and physics resumption.

## Purgatory Pool

- Source: https://github.com/twstewart42/purgatory-pool
- License: GPL-3.0
- Decision: architecture reference only. Code and assets are not copied into this private project because doing so would impose GPL obligations on the combined work.

## 3D Pool Game

- Source: https://github.com/Teddymops/3d-pool-game
- License: not clearly declared in the repository
- Decision: conceptual reference only. No code or assets may be copied without a verified license or direct permission.

## Pool-table model research

- [OpenGameArt low-poly pool table](https://opengameart.org/content/pool-table-low-poly) — CC0; suitable as a proportion reference, but below the project's visual-detail target.
- [OpenGameArt billiards pack](https://opengameart.org/content/billiards-pack) — CC0; useful as a compatibility/reference pack, but its style does not match Spectral Manor.
- [Sketchfab Pool Table](https://sketchfab.com/3d-models/pool-table-fdacab7310cc4ad7811cb7eff95f486b) — CC BY-NC; rejected because the noncommercial restriction is unnecessarily limiting.
- [3D CAD Browser billiard table](https://www.3dcadbrowser.com/3d-model/billiard-table) — royalty-free use but no source redistribution; rejected for a repository that retains editable production sources.
- Decision: no third-party table model was imported. The v0.7B table, geometry, materials, and texture maps are original project assets built by the deterministic Blender generator.
