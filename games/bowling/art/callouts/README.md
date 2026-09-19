# Call-out art (Gregg's graffiti)

Drop a painted PNG here and it replaces the text call-out for that result:

| file | shown when |
|---|---|
| `strike.png` | all ten down on the first ball |
| `spare.png` | the rest cleared on the second ball |
| `miss.png` | the ball touched nothing (on the lane) |
| `gutter.png` | the ball went in the gutter |

- **Transparent background** (PNG with alpha) - it's laid over the alley.
- **About 2:1**, e.g. 2000 x 1000 or 2400 x 1200. Any size works; it's fitted into
  1100 x 560 on a 1920 x 1080 screen, slightly above centre.
- It slams on (1.6x -> 1x with a bounce), sits at a small random tilt for ~1.2 s,
  then fades. Paint it level; the game adds the tilt.
- Bright colours with a dark outline read best over both the warm Lounge and the neon Crypt.
- Missing files just fall back to the text, so they can arrive one at a time.

After adding one, open the project in Godot once (or run
`godot --headless --path . --import`) and re-export the builds.
