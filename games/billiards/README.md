# Spectral Manor Billiards

A cinematic gothic 3D eight-ball game built with Godot, featuring spectral physics, gamepad-first controls, and instant replays.

## First playable

The current vertical slice is generated procedurally at runtime and includes:

- a complete 16-ball rack with six functional pockets;
- built-in Jolt rigid-body physics on Godot 4.7;
- gamepad-first aiming, charging, striking, tactical camera, and replay controls;
- mouse and keyboard fallback controls;
- an eight-second transform ring buffer with manual and automatic slow-motion replays;
- velocity-scaled procedural ball and cushion impact audio;
- a gothic lounge whitebox based on the supplied visual references;
- Practice Alone, Versus Computer, and Local Two Player modes;
- eight-ball group assignment, legal-target checking, fouls, scratches, turn continuation, and win/loss evaluation;
- an AI shot planner with Easy, Medium, and Hard accuracy profiles;
- interactive human and strategic computer ball-in-hand placement;
- right-stick/arrow-key top, draw, and side English with physical torque;
- legal-break validation with distinct rail-contact counting;
- called-pocket eight-ball play and eight-on-break respotting;
- pocket tracking and re-racking.

## Run

Open `project.godot` in Godot 4.7.2 and press **F6/F5**, or run:

```text
Godot_v4.7.2-stable_win64.exe --path <project-folder>
```

![First playable preview](docs/first-playable.png)

![Gameplay Core mode selection](docs/gameplay-core.png)

![Ball Control v0.3](docs/ball-control.png)

### Smoke test

```text
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/smoke_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/gameplay_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/ai_flow_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/ball_control_test.gd
```

## Controls

| Action | Xbox controller | Keyboard / mouse |
| --- | --- | --- |
| Aim around table | Left stick | A/D or move mouse |
| Apply English | Right stick | Arrow keys |
| Build power | Right trigger | Hold Space or right mouse |
| Strike | Right bumper | Enter or left mouse |
| Place cue ball | Left stick, then right bumper | WASD, then Enter or left mouse |
| Call eight-ball pocket | B | C |
| Tactical view | Y | T |
| Replay last shot | X | R |
| Re-rack | Back | Escape |

## Art references

The supplied concept images are preserved under `docs/reference/`. They are visual references only; the project does not parse them as requirements or instructions.

## Next production passes

1. Replace the procedural room and table with optimized Blender assets.
2. Expand Hard AI with bank shots, safeties, and deeper cue-ball position planning.
3. Tune spin decay, cushion transfer, table friction, and shot strength from playtesting.
4. Record and layer production resin, rubber, roll, ambience, and reverb audio.
5. Add accessibility settings, save data, export presets, and optional GIF highlights.

See `THIRD_PARTY.md` for open-source evaluation and license boundaries.
