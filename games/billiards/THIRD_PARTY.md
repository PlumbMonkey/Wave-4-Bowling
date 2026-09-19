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
