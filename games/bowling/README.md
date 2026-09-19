# Phantom Bowling (Godot 4.7, Forward+, Jolt)

PRD: `../../docs/PRD_PhantomBowling.md`. Reference art in `art/reference/`.

## Run

Open this folder in Godot 4.7 and press F5, or:

```
godot --path .                                  # play
godot --path . -- --autoplay                    # watch it bowl itself
godot --path . -- --shots=C:/tmp/shots          # autoplay one game, save screenshots, quit
godot --headless --path . --script res://tests/run_tests.gd   # 14 scoring + 4 physics tests
```

After adding a new `class_name` script, run `godot --headless --path . --import`
once, or Godot won't find the class.

## Controls

| | Xbox | keyboard / mouse |
|---|---|---|
| move on the approach | D-pad left/right | A / D |
| aim | right stick | J / L, or move the mouse sideways |
| **draw back (sets the speed)** | pull the **left** stick toward you | move the mouse toward you, or hold S (W eases off) |
| **release** | squeeze **RT** (a firm squeeze - a resting finger won't let go) | left click, or Space |
| instant replay (after the result) | X | X |
| release spin (while aiming) | LB / RB, in steps | Q / E |
| hook (while the ball rolls) | hold LB / RB | hold Q / E |
| steer (while the ball rolls) | left stick left/right — a subtle nudge, off in the last metre | A / D |
| change ball (while aiming) | Y | B |
| restart / play again | Start / A | R / Enter |
| mute | View (Back) | M |
| pin set: Classic → Bone → Reliquary (while aiming) | D-pad up | P |
| alley: Spectral Lounge → The Void → The Crypt (while aiming) | D-pad down | V |

Click once in the window to capture the mouse; Esc frees it.

The input map is registered in code (`autoload/input_setup.gd`), so it doesn't
appear in the editor's Input Map tab.

## How it works

| file | role |
|---|---|
| `scripts/bowling_spec.gd` | regulation dimensions, oil pattern, throw limits |
| `scripts/bowling_ball.gd` | the ball's **own lane-friction model**: the lane has zero Jolt friction; the script applies sliding friction at the contact patch with μ from the oil pattern (0.04 for 40 ft, then 0.20 dry). The ball skids, hooks and rolls out on its own. |
| `scripts/bowling_pin.gd` | USBC-profile pin, 1.58 kg, centre of mass 14.5 cm up, convex-hull collider. Down = tilted > 40° or off the deck |
| `scripts/pinsetter.gd` | racks, waits for the deck to go quiet, sweeps deadwood, respots the pins still standing |
| `scripts/score_card.gd` | 10-frame scoring, 10th-frame fill balls, marks (X / - digits) |
| `scripts/game.gd` | state machine AIM → CHARGE → ROLL → SETTLE → RESULT; cameras (behind the bowler → chase → slow-mo pin cam); **`process_throw({x, aim, power, spin})` is the single entry point for every throw**, ready for networked play |
| `scripts/alley.gd` | grey-box colliders + visuals at regulation size |
| `scripts/hud.gd` | scoreboard, speed readout, spin gauge, STRIKE/SPARE banner, replay letterbox |
| `scripts/aim_guide.gd` | faint dotted path predicted by `BowlingBall.predict()` (the ball's own lane model), curving with spin, with a pulse running along it at the throw speed |
| `scripts/throw_replay.gd` | records ball + pins every physics frame; slow-motion playback on frozen bodies, so it can't change the result |

Sign conventions: +x is the bowler's right; positive spin hooks right. A
right-hander stands right of centre with negative spin.

## Art (Phase 2)

Built by script in Blender (`../../blender/bowling_tools/`), exported straight into `art/`:

| asset | source | notes |
|---|---|---|
| `art/alleys/lounge.glb` | `Phantom Bowling - Spectral Lounge.blend` | 5 lanes, 122k tris, 12 MB. Lane 0 lines up with the grey-box colliders exactly |
| `art/alleys/void.glb` | `Phantom Bowling - The Void.blend` | 140k tris, 14 MB. The back wall is one great arch onto a nebula (unshaded in Godot); the masking is an open gothic screen with spires and a gold crescent; telescopes, armillaries, compass-star floor |
| `art/alleys/crypt.glb` | `Phantom Bowling - The Crypt.blend` | 115k tris, 13 MB. Black stone lanes with UV-glow markings, cyan neon gutters, blacklight murals, sigil banners, torches, lasers, the ghost bride between two gargoyles over the masking |
| `art/balls/{spectre,p,skull}.glb` | `Phantom Bowling - Balls.blend` | regulation size; The Spectre = hooded reaper in lava, The P = silver monogram on violet marble, The Skull = smoky resin with a skull inside |

Rebuild: `blender -b --factory-startup --python blender/bowling_tools/bowl_headless.py -- --balls --alley --void --crypt [--bake] [--bake2] [--render aim,hall,pins,balls]`
(`--bake` re-bakes the Lounge/ball textures, `--bake2` the Void/Crypt ones in `bowl_textures2.py`),
then `godot --headless --path . --import`.

`scripts/alley_theme.gd` loads the alley GLB, hides the grey-box meshes (colliders stay), turns the `LGT_*`
marker nodes into lights (chandeliers, flickering candles, the violet masking glow, a pin spot per lane,
the windows) and sets the Desktop profile: SSR, SSAO, SSIL, glow, volumetric fog. If the GLB is missing,
the game falls back to the grey box.

Each alley in `AlleyTheme.ALLEYS` can override the light colours per marker kind and the environment
(the Void is cool starlight, the Crypt violet blacklight + orange torches). D-pad down / V switches alley
while aiming (`game.set_alley`); only scenery, lights and environment change - the lane, pins, ball and
colliders are the same everywhere. The choice is saved; `-- --alley=void|crypt|lounge` forces one.

## The oil (why the same line stops working)

`scripts/oil_pattern.gd`. Every game rolls its own house shot: oil length 10.8–13.8 m (the HUD shows it
in feet), slickness of the oil and of the dry back end, and a crown (outside boards drier than the
middle). Each ball then dries the cells it rolled through and carries oil ~8 cm further, and every throw
gets a ±4% surface variation. After 8 balls down the same line, that line finishes ~0.18 m (6–7 boards)
away from where it did on the fresh shot, so you have to move. The aim guide only shows the first 11 m,
computed on the *published* house shot, so the back end is yours to read.

## Graphics profiles and builds (Phase 4)

`scripts/graphics_profile.gd` - picked automatically (a web export or the Compatibility renderer means Web),
or forced with `-- --profile=web`.

| | Desktop (Forward+) | Web (Compatibility / WebGL 2) |
|---|---|---|
| anti-aliasing | MSAA 4x | MSAA 2x |
| SSR, SSAO, SSIL, volumetric fog | on | off |
| candle / lantern / pit / orb lights | real lights, flickering | emission only |
| shadows | chandeliers + pin spots | your lane's pin spot only |

Exports (`export_presets.cfg`, templates for 4.7 are installed):

```
godot --headless --path . --export-release "Windows Desktop" ../../builds/bowling/windows/PhantomBowling.exe
godot --headless --path . --export-release "Web" ../../builds/bowling/web/index.html
```

Windows: one 122 MB exe. Web: single-threaded (no COOP/COEP headers needed on the host), 12.6 MB pck +
39.5 MB wasm (~9 MB gzipped). Preview the web look on desktop with
`godot --path . --rendering-method gl_compatibility -- --profile=web`.

## Networking groundwork (Phase 4)

Every throw emits `throw_completed(record)`: `{v, params: {x, aim, power, spin, jitter}, inputs: [hook, steer]
per physics tick, pins, ball_end}` - small enough to send over ManorNet. `play_remote_throw(record)` feeds a
received throw through the same `process_throw` path, replaying the opponent's steer and hook tick by tick.
Tested: a record played back lands 0.000 m from the original with the same pin count (same build, same
lane state). For real matches the thrower's result should stay authoritative, because physics isn't
guaranteed identical across different machines. The replay recorder's frames can be streamed if the
other screen needs to show the exact pin action.

## Pin sets

`BowlingPin.STYLES`:
- **Classic** - procedural, red neck stripes.
- **Bone** (`art/pins/bone.glb`, `blender/bowling_tools/bowl_pins.py`) - knuckled femur base, vertebra
  rings instead of stripes, a small skull head facing the bowler with faintly glowing eyes.
- **Reliquary** (`art/pins/reliquary.glb`, `bowl_reliquary.py`, reference `art/reference/pins_reliquary.webp`)
  - polished, cracked bone carved with gothic reliefs (skull and rib-wings, ribcage and spine, cathedral
  window, skull under a heart of ribs) that glow blue from the hollows; aged-bronze crown collar, rings and
  foot as real geometry; a spine up every pin's back. The carvings live in one 2x2 texture atlas (colour,
  normal, emission, ORM), so the silhouette stays regulation. The four designs alternate across the rack.
 Every set shares the regulation collider
and mass, so it's purely a look. The neighbouring lanes switch too (`AlleyTheme.set_pin_style`), bone
pins sound a touch higher and drier, and the choice is saved with the ball and mute in
`user://phantom_bowling.cfg` (`scripts/settings.gd`). `-- --pins=bone` forces it from the command line.

## Sound

All synthesised - no samples, no licences. `python tools/make_sounds.py` regenerates `audio/*.wav`
(22 files) with numpy/scipy: shaped noise plus pin resonance modes for the clatter, additive organ and
bell partials through a synthetic hall for the stingers, perfectly-looping roll / gutter / ambience beds.

`scripts/bowling_audio.gd` plays them from the physics:
- the roll loop rides on the ball - louder and higher with speed, a hollow rattle in the gutter, silent in the air;
- **pin acoustics** (rebuilt after playtest 4): every hit = a half-sine contact pulse exciting a real pin's
  modes (free-bar overtones 1 : 2.76 : 5.40 : 8.93 above a 640–860 Hz fundamental) + the ~2 kHz ring of the
  plastic shell + a bright click; harder contacts are shorter pulses, so brighter. Separate families for
  ball→pin (with the ball's low thock), pin→pin (the bright TOCK), pin→lane (a slap plus one or two
  bounces), pin→kickback and pin→pit, 3–8 variations each, centred around 2 kHz like real clatter;
- **the rack crash**: 90 ms after the ball arrives, the pins in flight are counted; 4+ fires a layered
  crash (a storm of clacks that thins over a second, pins sliding and dropping into the pit), louder the
  more pins are moving. The individual contacts still play on top of it;
- release thump, pit thud, pinsetter between balls, quiet strike / spare / gutter stingers, a final chord, a
  low organ-and-wind ambience;
- the instant replay re-plays the throw's recorded hits in slow motion, pitched down;
- buses: `SFX` (a small, dry room - reverb wet 0.05, high-passed so the low end stays punchy - plus a
  limiter), `Ambience`, and a limiter on Master.
- Playtest 5 mix: no swish on release (just the ball landing, then the roll); strike / spare / gutter
  stingers ~17 dB quieter; the ball hit, the pin clack and the crash all carry a low thock / sub thump,
  and the crash tail is ~0.3 s instead of over a second.

Listen: `builds/bowling/clips/phantom_bowling_sound.mp4` (40 s of autoplay, recorded with Godot's
movie maker: room ≈ −30 dB, rolls ≈ −14 dB, pin hits up to −10 dB, peak −0.6 dBFS).

## Phase status

- **Phase 1 (grey box) — done.** Measured: a 7.6 m/s ball reaches the pins in 2.7 s;
  a pocket hook skids straight for ~9 m and breaks ~0.4 m on the back end.
- Phase 3 is partly done: scoring, the state machine, cameras and a basic scoreboard.
- Post-release steering added after the first playtest (`STEER_ACCEL`, 0.12 m/s² — ~0.34 m at full stick).
- **Sound — done (2026-09-18).**
- **Phase 4 — done (2026-09-18):** desktop/web profiles, Windows + Web exports verified (the web build
  boots in a browser), throw records for networking. Also: oil variance, left-stick draw + RT release,
  spin HUD removed, pin stripes moved onto the neck.
- **Phase 3 — done (2026-09-18):** pull-back throw, full-speed roll (no live slow-mo; engine damping on the
  ball switched off — it had been costing ~25% of the speed), swoop → chase → pin-deck cameras, instant
  replay (X) from a low deck camera, and the predictive aim guide (matches the real throw to ~1 cm at 15 m).
- **Phase 2 — done (2026-09-18):** all three alleys (The Spectral Lounge, The Void, The Crypt), the alley
  picker, the three balls and three pin sets. The web pck is now ~41 MB (three 12-14 MB alleys) - a lighter
  web GLB per alley is the next web-polish job.
