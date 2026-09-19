# Master PRD — Spectral Manor Arcade Suite (Wave 4)

- **Host:** plumbmonkey.online — a **new, adults-only site**, separate from the
  existing Plumbmonkey site. The current site stays as it is, with no chat, to
  protect children who explore it. This site is built around social play and
  **selling products** (not services).
- **Deployment:** static web app, $0/month recurring.
- **Multiplayer:** serverless WebRTC peer-to-peer + live text chat (Trystero).
- **Hero:** Luno the Spaceman, adapted for the gothic lounge and sports settings.
- **Hub:** the Spectral Manor Lounge — a 3D gothic hall whose four archways lead
  to the games (bowling, billiards, golf, cards). Blender source in `blender/`.

## 1. Open-source base matrix

| Title / module | Base repo | Stack | Role |
|---|---|---|---|
| 8-Ball Billiards | Teddymops/3d-pool-game | Three.js, Cannon.js | 3D table, cue rotation, shot meter, ball impacts |
| Ten-Pin Bowling | iliagrigorevdev/bowling | Three.js, Ammo.js | rigid-body pin scatter, lane friction, swipe curve |
| Golf A: Mini-Golf | jasanbornn/golfgame | Three.js, cannon-es | 9-hole loop, bank bounces, slopes, cup triggers |
| Golf B: 18 Links | jcole/golf-shot-simulation + js13kGames/coding-golf-broken-links | Three.js, WebGL | ballistic lift/drag + 18-hole scorecard |
| Texas Hold'em | bocaletto-luca/Texas-Holdem | Vanilla JS, CSS3 | poker state machine, betting, bot AI |
| Hand evaluation | thx/poker-evaluator | JS / npm | 5–7 card rank comparison |
| P2P + chat | dmotz/trystero | WebRTC DataChannel | serverless signalling |

> **Before forking any of these:** check each repo's licence. This site sells
> products, so code with no licence (all rights reserved) or a copyleft licence
> (GPL/AGPL) can't be used as-is. Checked per game as each one starts.

## 2. Aesthetic

Victorian gothic lounge meets cosmic traveller.

| token | hex |
|---|---|
| ectoplasm green | `#2bf7a3` |
| spirit violet | `#8a2be2` |
| tarnished brass | `#b59449` |
| worn mahogany | `#1a0f0d` |
| charcoal void | `#0a0a0c` |

Luno's role per game:

- **Pool** — antique cue in glowing astronaut gauntlets; cue ball trails spectral vapour.
- **Bowling** — a heavy ball holding a swirling miniature galaxy, down candle-lit parquet lanes.
- **Crypt Putt** — foggy graveyard greens, swinging pendulum blades, gargoyle teleporters.
- **Phantom Links 18** — full drives over moonlit cliffs, haunted bunkers, misty fairways.
- **Poker** — velvet table opposite skeletal and phantom specters; visor shows the HUD.

## 3. Games

### Game 1 — Spectral Billiards (8-ball)
Orbital table camera + top-down toggle · aim line, pull-back power, English spin
offset · pocket detection with spectral drop chimes.
Modes: Solo Practice, Manor Ghost Bot, 2-Player P2P.

### Game 2 — Phantom Bowling  ← **building first**
Lane alignment slide → power meter → hook/spin flick · Ammo.js pin chain
reactions · 10-frame ledger (strikes, spares, opens).
Modes: Solo 10-Frame Challenge, 2-Player turn-by-turn P2P.

### Game 3 — Crypt Putt (mini-golf)
Contoured greens, stone banks, elevation drops · swinging crypt axes, rising
tombstones, gargoyle shortcut pipes · opponent shown as an ethereal ghost ball.
Modes: 9 or 18 holes, Solo Stroke Play, 2-Player Ghost Race.

### Game 4 — Phantom Links 18
Full bag (Driver, 3W, 3I–9I, PW, SW, Putter) · 3-click swing gauge (start →
power → accuracy snap) · launch angle, backspin, drag, Magnus lift, crosswind ·
animated green-contour grid.
Modes: Solo Practice, 18-Hole Stroke Play, 2-Player Match Play P2P.

### Game 5 — Crypt Hold'em
No-Limit Hold'em (pre-flop → river) · Fold/Check/Call/Raise slider/All-In ·
tarot-styled cards, cursed-gold chips, automatic hand evaluation.
Modes: Solo vs 3 Ghost Bots, 2-Player Heads-Up P2P.

## 4. P2P networking and chat

One shared bridge (`shared/net/`) that every game uses:

```
 Active game ──(gameAction)──┐        ┌──(chatMessage)── Chat drawer
                             ▼        ▼
                        [ ManorNet  (Trystero) ]
                                  │  signalling over public Nostr relays /
                                  │  BitTorrent trackers
                                  ▼
                       direct, encrypted WebRTC ─── opponent's browser
```

- Room links: `plumbmonkey.online/manor?game=pool&room=DARK-404`.
- `gameAction` — impulses (cue hits, swings, throws) or betting events.
- `chatMessage` — sanitised text, sender alias, timestamp.

### Known limits of the $0 model (decide before launch)

1. **Some players won't connect.** Without a TURN relay, peers behind strict
   NATs (some mobile carriers, corporate networks) can't reach each other.
   Cloudflare's TURN free tier (1,000 GB/month) is the cheap fix; ManorNet
   already accepts a `turn` option.
2. **Peers see each other's IP address.** That's inherent to WebRTC. Mention it
   in the site's privacy notice.
3. **No central moderation.** Nothing passes through a server, so there's no log
   and no way to ban anyone site-wide. The chat drawer has per-user mute and a
   rate limit. A public lobby with strangers would need more than that.
4. **Public relays can be slow or down.** ManorNet uses Nostr by default and can
   switch to BitTorrent trackers.

## 5. Roadmap (build order as agreed 2026-09-18)

0. **Spectral Manor Lounge** — Blender hub scene (in progress).
1. **Network + chat shell** — `shared/net/` (first cut written).
2. **Phantom Bowling** — the first game.
3. Crypt Putt · 4. Spectral Billiards · 5. Crypt Hold'em · 6. Phantom Links 18.
7. Deployment — audio mastering, mobile touch checks, static publish.
