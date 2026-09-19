# PRD — Phantom Bowling (Spectral Manor Arcade Suite)

Received 2026-09-18. It supersedes the web-first bowling plan in `PRD.md`
(Three.js / Ammo.js fork): bowling is now a **Godot 4 game first**, with a
lighter web build and VR later.

## Summary
A premium haunted 3D bowling game in Godot 4. Desktop first (full gamepad
support), then a lightweight web build for plumbmonkey.online, then VR.

## Platforms
- Engine: Godot 4.x (GDScript) + Blender for models.
- Physics: Jolt.
- Tier 1 (now): desktop, Forward+ renderer — volumetric fog, SSR, SSAO, MSAA, high-res textures.
- Tier 2 (later): web / mobile, Compatibility renderer, baked lighting, low poly, compressed textures.
- Tier 3 (later): OpenXR.

## Controls (gamepad first)
- L-stick: move on the approach. R-stick: aim. RT: hold for power, release to throw.
  LB/RB: spin/hook while the ball rolls.
- Fallback: A/D move, mouse drag aim, left click hold/release power, Q/E spin.

## Art
Gothic, candle-lit, haunted, ethereal.
- **Three alleys** (PRD names: The Crypt, The Void, The Spectral Lounge). Reference
  images in `games/bowling/art/reference/`: `alley_lounge` (mahogany, velvet,
  gargoyle columns), `alley_void` (open cosmic backdrop, astronomical
  instruments), `alley_neon` (blacklight / laser version with glowing balls).
- **Three balls** (PRD names: The Skull, The Pentagram, The Spectre with the
  Plumbmonkey logo). Reference image `balls_reaper_owl_logo`: a hooded reaper
  in molten lava, an owl, and a gothic "P" monogram.

## Decisions (2026-09-18)
- Alleys keep the PRD names: **The Spectral Lounge** (`alley_lounge`), **The Void**
  (`alley_void`), **The Crypt** (`alley_neon`, the blacklight/gargoyle room).
- Balls: **The Spectre** is the hooded reaper in lava; **the P** (gothic monogram)
  replaces the Pentagram; **The Skull** stays.
- After the first playtest: the left stick steers the ball subtly after release.

## Playtest backlog (2026-09-18, second playtest) — all done (sound added 2026-09-18)
1. **No live slow-motion.** The drop in speed near the pins is `SLOWMO` in `game.gd`
   (time scale 0.35 for about a second), not friction. The ball should reach the
   pins at full speed.
2. **Replay instead.** Record the ball and pin transforms every physics frame
   during the roll; after the result, offer "Replay" (X / R-click) that plays it
   back in slow motion from the pin camera. The replay only reads the recording,
   so it can't change the score, and a recorded throw could be streamed to a
   networked opponent later.
3. **Sound (there is none yet).** Ball roll rumble scaled by speed (lane and
   gutter differ), ball-pin and pin-pin hits scaled by impulse, the pit and
   pinsetter, strike/spare stingers, room ambience (candles, low organ drone),
   UI ticks. Use CC0 sources or synthesise; check licences.
4. **Subtler aim guide.** Replace the bright straight line with a faint dotted
   path that **curves with the spin**: it's predicted with the same oil-pattern
   friction model the ball uses, minus the pins. A **pulse travels along it at
   the throw speed**, so power is shown on the path itself rather than by a
   separate meter.
5. **Pull-back throw.** Replace the hold-and-sweep power meter. Pull back with
   the mouse (drag toward you) or the stick (pull down) to draw the ball back;
   how far you pull sets the power. Release with a click (mouse) or a button
   (A / RT) on the controller.

## Third playtest (2026-09-18) — done
- Oil pattern varies per game and breaks down during it; the aim guide shows only the front 11 m.
- Controller: right stick aims, left stick draws back, RT releases. D-pad moves on the approach.
- Spin graphic removed; pin stripes moved down onto the neck.

## Build plan
1. **Grey box** — Jolt, lane, weighted pins, ball impulse + spin, fallen-pin
   detection and respot. **Done 2026-09-18.**
2. **Blender art** — modular alleys, lighting baked for the web build, the three
   balls (Skull: clear-coat shell with a skull inside), glTF into Godot, fog and spots.
3. **Game loop** — scoreboard UI, state machine Aiming → Throwing → Rolling →
   Scoring → Reset, a camera that follows the ball and cuts to slow-mo on the pins.
   **Mostly done in Phase 1.**
4. **Desktop vs web profiles** — separate Environments; `process_throw(...)` is the
   single input path so a remote WebRTC player can drive the same function.

## Notes from building Phase 1
- **Jolt is built into Godot since 4.4** — `physics/3d/physics_engine = "Jolt Physics"`.
  The godot-jolt plugin repo is the old extension, so there's nothing to download.
- **maincomputer/bowlinggame** wasn't needed. The scoring is written from the
  rules and covered by tests, which also avoids a licence question.
- **Open art decisions:** the alley images don't match the PRD names one-for-one
  (the neon room isn't obviously "The Crypt"), and the ball images show a reaper,
  an owl and a "P" monogram where the PRD says skull, pentagram and spectre.
