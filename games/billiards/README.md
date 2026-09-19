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
- basic two-player turn flow, scratches, pocket tracking, and re-racking.

## Run

Open `project.godot` in Godot 4.7.2 and press **F6/F5**, or run:

```text
Godot_v4.7.2-stable_win64.exe --path <project-folder>
```

![First playable preview](docs/first-playable.png)

### Smoke test

```text
Godot_v4.7.2-stable_win64_console.exe --headless --path <project-folder> --script res://tests/smoke_test.gd
```

## Controls

| Action | Xbox controller | Keyboard / mouse |
| --- | --- | --- |
| Aim around table | Left stick | A/D or move mouse |
| Cue elevation / early English preview | Right stick vertical | W/S |
| Build power | Right trigger | Hold Space or right mouse |
| Strike | Right bumper | Enter or left mouse |
| Tactical view | Y | T |
| Replay last shot | X | R |
| Re-rack | Back | Escape |

## Art references

The supplied concept images are preserved under `docs/reference/`. They are visual references only; the project does not parse them as requirements or instructions.

## Next production passes

1. Replace the procedural room and table with optimized Blender assets.
2. Complete WPA-style eight-ball rules and ball-in-hand placement.
3. Add proper offset striking and full spin/rail-transfer physics.
4. Record and layer production resin, rubber, roll, ambience, and reverb audio.
5. Add menus, accessibility settings, AI opponent, save data, and export presets.
6. Evaluate the optional MIT GIF recorder for shareable highlights after the cinematic state replay is stable.

See `THIRD_PARTY.md` for open-source evaluation and license boundaries.
