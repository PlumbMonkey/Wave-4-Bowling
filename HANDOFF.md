# Wave 4 handoff

**Started 2026-09-18.** Adults-only social arcade for plumbmonkey.online — a new
site, kept separate from the existing (child-safe, chat-free) Plumbmonkey site.
The PRD is in `docs/PRD.md`.

## Status

| piece | state |
|---|---|
| Project folder + PRD | done |
| Spectral Manor Lounge (Blender hub) | **first pass done** — see below |
| ManorNet (P2P + chat) | **first cut working** — tested live between two tabs over Nostr |
| Phantom Bowling | Phases 1, 3, 4 done; Phase 2 half done (Spectral Lounge + 3 balls). Windows + Web builds in `builds/bowling/`. Sound done (synthesised, `tools/make_sounds.py`; pin acoustics + rack crash rebuilt after playtest 4). Pin sets: Classic, Bone, Reliquary (D-pad up / P).
**Sound decision (2026-09-18):** Gregg picked the current synthesised mix (the `phantom_bowling_mix2`
version: dry room, heavy low end, quiet stingers, no swish) as the one to live with. Revisit with real
recordings - Freesound CC0 / CC-BY only, never non-commercial - only if it stops feeling right in play. Open: The Crypt + The Void, a lighter web GLB — see `games/bowling/README.md`, PRD in `docs/PRD_PhantomBowling.md` |
| Crypt Putt, Billiards, Hold'em, Links 18 | not started |
| `site/` shell | not started |

Bowling moved from the web (Three.js) plan to **Godot 4.7 + built-in Jolt, desktop
first** per the bowling PRD. Tests: `godot --headless --path games/bowling --script
res://tests/run_tests.gd`. Next: tune the feel with a controller, then the
Blender alleys and balls (the art decisions are open, see the PRD notes).
**Playtest backlog** (no live slow-mo → replay, sound, spin-arc aim guide with speed pulse,
pull-back throw) is in `docs/PRD_PhantomBowling.md`.

## Spectral Manor Lounge — `blender/`

- `Spectral Manor Lounge.blend` is **generated**; edit the scripts in
  `blender/lounge_tools/`, not the file. Each phase wipes its own `LNG_*` objects
  before rebuilding.
- Rebuild headless (never while another EEVEE render is running):

  ```
  "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python "blender\lounge_tools\headless.py" -- --render hero,fireplace,bowling,poker --pct 50
  ```

  `--bake` re-bakes all textures (~35 s, mostly the floor); `--export` writes
  `export/spectral_manor_lounge.glb`; `--samples N` sets EEVEE samples.
  Renders go to `blender/renders/`.
- Numbers: ~99k tris, 159 objects, GLB 13.9 MB (floor PNG is 5 MB of that).
- Layout (`lounge_common.py`): +Y is the fireplace wall. Back wall x = ±8.5 at
  y = 8, angled walls to (±12.5, 4), side walls to the front at y = −9. Gallery
  floor at z = 8, ceiling at 16. The four doors are listed in `DOORS`: billiards
  and golf on the back wall at x = ∓5.6, bowling and poker centred on the
  angled walls.
- Each emblem tympanum and every game-room object carries a `game` custom
  property (`bowling` / `billiards` / `golf` / `poker`) that exports as glTF
  extras, for click-to-enter in the three.js hub.
- Cameras: `LNGCAM_Hero` (matches the reference framing), `Fireplace`,
  `Bowling`, `Poker`, `Gallery`.

### Lounge — known gaps, next pass

1. The chandelier still reads as a wire globe rather than the reference's dense
   tiered candle cluster.
2. The mirror's pointed crest shows a pale reflection; the reference mirror has
   a ghostly figure in it (could be a faint texture in the glass).
3. Floor blooms: the glossy floor still catches soft reflections of the lamps in
   the game rooms. Specular is already turned down (`NO_SPEC` in `lounge_scene.py`).
4. Web weight: convert the floor and rug PNGs to JPG/WebP and downscale the
   floor before shipping.
5. glTF has no area lights — the window washes, fire spill and top fill are
   dropped on export and need three.js `RectAreaLight`s.
6. Traps hit here: piping Blender through `Select-Object -First N` kills it
   mid-render; shadowless lights leak through walls (the game-room lights keep
   their shadows for that reason); >~40 shadowed lights overflow EEVEE's shadow
   pool.

## ManorNet — `shared/net/`

- `manor-net.js` — `joinManor({ game, alias, room?, key?, private?, strategy?, turn?, importer? })`
  → `sendAction / onAction` (the PRD's gameAction), `sendChat / onChat`
  (chatMessage), `peers()`, `isHost()` (lowest peer id; every peer agrees),
  `mute()`, `inviteLink()`, `leave()`.
- `chat-drawer.js` + `.css` — `mountChatDrawer(net)`: slide-out drawer, peer list
  with mute, invite copy, unread badge. All peer text is written with
  `textContent`.
- `manor-util.js` — the pure helpers (room codes, invite parsing, sanitising,
  rate limits). `npm test` runs `manor-util.test.mjs` (8 tests).
- `demo.html` — two-tab test page. Serve the project root (`manor-wave4` in
  `~/.claude/launch.json`, port 5190) and open
  `/shared/net/demo.html?room=DARK-404` in two windows.
- Trystero is pinned to **0.25.4** and loaded from `esm.run`. Its API has moved
  on since the PRD was written: `makeAction()` now returns an object
  (`.send`, `.onMessage`), and BitTorrent lives in `@trystero-p2p/torrent`.
  The default is Nostr. Pass `importer` to load a vendored copy instead of the CDN.
- Room id is `game:CODE`, so a bowling room and a pool room with the same code
  never meet. Private rooms put `#key=` in the link (it stays in the browser,
  never reaches a server) and use it as Trystero's password.
- Inbound limits: chat ≤ 280 chars, 5 messages / 5 s per peer; actions need a
  string `type`, ≤ 4 KB, ≤ 60/s per peer.

## Open decisions before launch

- **TURN relay.** Without one, some players (strict mobile/corporate NATs) can't
  connect. Cloudflare's free tier covers it; pass it as `turn: [...]`.
- **Moderation.** P2P means no server log and no site-wide ban. The current
  tools are per-user mute, a rate limit and invite-only rooms. Public lobbies
  with strangers would need more than that.
- **Age gate + terms + privacy notice** (peers can see each other's IP, which is
  inherent to WebRTC).
- **Licences** of the base game repos — check each before forking into a site
  that sells things.
