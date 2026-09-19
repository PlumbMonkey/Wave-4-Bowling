# Spectral Manor Billiards

A cinematic gothic 3D eight-ball game built with Godot, featuring spectral physics, gamepad-first controls, and instant replays.

## First playable

The current vertical slice is generated procedurally at runtime and includes:

- a complete 16-ball rack with six functional pockets;
- built-in Jolt rigid-body physics on Godot 4.7;
- gamepad-first camera, cue-ball placement, pull/push striking, tactical view, and replay controls;
- mouse and keyboard fallback controls;
- an eight-second transform ring buffer with manual and automatic slow-motion replays;
- pocket-focused cinematic replay cameras with isolated, exact live-state restoration;
- pooled, velocity-scaled resin and cushion impact audio;
- continuous cloth-roll sound driven by the combined speed and position of moving balls;
- gothic hall reverb plus a muffled replay mix and spectral bass rumble;
- strike, collision, and pocket controller vibration;
- saved table-volume, vibration, automatic-replay, and shot-guide settings;
- a gothic lounge whitebox based on the supplied visual references;
- Practice Alone, Versus Computer, and Local Two Player modes;
- eight-ball group assignment, legal-target checking, fouls, scratches, turn continuation, and win/loss evaluation;
- an AI shot planner with Easy, Medium, and Hard accuracy profiles;
- Hard AI one-cushion banks, defensive safeties, and next-shot position scoring;
- visible computer tactical intent and a spectral bank-path guide;
- interactive human and strategic computer ball-in-hand placement;
- camera-relative, velocity-smoothed cue-ball placement with the left stick;
- right-stick orbit and elevation camera control;
- hold-RT pull-back/push-forward analog cue strokes with motion-based power;
- optional solid light-blue cue/object-ball trajectory guidance;
- D-pad/arrow-key top, draw, and side English with physical torque;
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

![Tactical AI v0.4](docs/tactical-ai.png)

![Controller and trajectory guidance v0.5](docs/controller-guidance.png)

![Cinematic pocket replay v0.6](docs/cinematic-replay.png)

### Smoke test

```text
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/smoke_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/gameplay_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/ai_flow_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/ball_control_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/menu_input_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/control_scheme_test.gd
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/cinematic_feedback_test.gd
```

## Controls

| Action | Xbox controller | Keyboard / mouse |
| --- | --- | --- |
| Orbit / tilt camera | Right stick | A/D or move mouse |
| Apply English | D-pad | Arrow keys |
| Analog cue stroke | Hold RT, pull right stick back, then push forward | Hold Space/right mouse, release to strike |
| Quick strike / place | Right bumper | Enter or left mouse |
| Place cue ball | Left stick, then right bumper | WASD, then Enter or left mouse |
| Toggle shot guide | Left bumper | G |
| Call eight-ball pocket | B | C |
| Tactical view | Y | T |
| Replay last shot | X | R |
| Re-rack | Back | Escape |

## Art references

The supplied concept images are preserved under `docs/reference/`. They are visual references only; the project does not parse them as requirements or instructions.

## Next production passes

1. Replace the procedural room and table with optimized Blender assets.
2. Add multi-rail/combinations only after one-cushion bank accuracy is playtested.
3. Tune spin decay, cushion transfer, table friction, and shot strength from controller playtesting.
4. Replace the procedural audio sources with recorded production resin, rubber, cloth, and ambience layers.
5. Add accessibility settings, save data, export presets, and optional GIF highlights.

See `THIRD_PARTY.md` for open-source evaluation and license boundaries.
