class_name BowlerAI
extends RefCounted
## A computer bowler. It works out a line with BowlingBall.predict - the 1-3
## pocket for a full rack, the middle of what's left for a spare - then misses
## it by a human amount. How well it reads the lane is what makes the levels:
##   EASY    assumes the standard house shot (no idea what this lane is doing)
##   MEDIUM  reads this game's pattern but not how it has worn
##   HARD    reads the lane as it is now, wear and all

const LEVELS := ["OFF", "EASY", "MEDIUM", "HARD"]
const NAMES := ["", "LOST SOUL", "POLTERGEIST", "THE REAPER"]
const BALLS := [0, 2, 1, 0]                  ## skull, the P, the Spectre
## one standard deviation of error: stance (m), aim (deg), power, spin
const ERROR := [
	{},
	{"x": 0.05, "aim": 0.45, "power": 0.08, "spin": 0.22},
	{"x": 0.025, "aim": 0.22, "power": 0.04, "spin": 0.11},
	{"x": 0.010, "aim": 0.085, "power": 0.018, "spin": 0.05},
]
const POCKET_X := 0.064                      ## between the 1 and 3 pins, for a right-hander
const STANCES := [6.0, 9.0, 12.0, 15.0, 18.0, 21.0, 24.0, 27.0, 30.0, 33.0]


## The throw to make: {x, aim, power, spin}. *standing* is where the standing
## pins are; *rng* null means no error (a perfect bowler, for tests).
static func plan(level: int, standing: Array, rng: RandomNumberGenerator = null) -> Dictionary:
	var full := standing.size() >= 10
	var target := Vector2(POCKET_X, -BowlingSpec.LANE_LEN)
	var spin := -0.8
	var power := 0.74
	var prefer := 12.0                                    # a right-hander's usual stance board
	if not full and not standing.is_empty():
		# a spare: at the middle of what's left, as seen from the front pin, with less hook
		var sx := 0.0
		var front := -99.0
		for p: Vector3 in standing:
			sx += p.x
			front = maxf(front, p.z)
		target = Vector2(sx / standing.size(), front)
		spin = -0.3
		power = 0.8
		prefer = 20.0 - target.x / BowlingSpec.BOARD * 1.5   # cross the lane for corner pins
	var speed := lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, power)
	var pat := read_lane(level)
	var best := {}
	var best_cost := INF
	for b: float in STANCES:
		var x := BowlingSpec.board_x(b)
		if absf(x) > BowlingSpec.X_MAX:
			continue
		var aim := _solve_aim(x, speed, spin, target, pat)
		if is_nan(aim):
			continue
		var cost := absf(b - prefer) + absf(rad_to_deg(aim)) * 3.0
		if cost < best_cost:
			best_cost = cost
			best = {"x": x, "aim": aim, "power": power, "spin": spin}
	if best.is_empty():
		best = {"x": 0.0, "aim": 0.0, "power": power, "spin": 0.0}      # can't find one: go straight
	if rng != null and level > 0:
		var e: Dictionary = ERROR[level]
		best.x = clampf(best.x + rng.randfn(0.0, e.x), -BowlingSpec.X_MAX, BowlingSpec.X_MAX)
		best.aim = clampf(best.aim + deg_to_rad(rng.randfn(0.0, e.aim)), -BowlingSpec.AIM_MAX, BowlingSpec.AIM_MAX)
		best.power = clampf(best.power + rng.randfn(0.0, e.power), 0.3, 1.0)
		best.spin = clampf(best.spin + rng.randfn(0.0, e.spin), -1.0, 1.0)
	return best


## The aim that takes a ball from stance x through *target* (x at depth z), or
## NAN if none does. Further right aim = further right at the pins, so bisect.
static func _solve_aim(x: float, speed: float, spin: float, target: Vector2, pat: OilPattern) -> float:
	var lo := -BowlingSpec.AIM_MAX
	var hi := BowlingSpec.AIM_MAX
	var f_lo := x_at(x, lo, speed, spin, target.y, pat) - target.x
	var f_hi := x_at(x, hi, speed, spin, target.y, pat) - target.x
	if signf(f_lo) == signf(f_hi):
		return NAN
	for i in 14:
		var mid := (lo + hi) * 0.5
		var f := x_at(x, mid, speed, spin, target.y, pat) - target.x
		if signf(f) == signf(f_lo):
			lo = mid
			f_lo = f
		else:
			hi = mid
	return (lo + hi) * 0.5


## Where the predicted ball is across the lane when it reaches depth z
## (extrapolating past the head pin, where the prediction stops).
static func x_at(x: float, aim: float, speed: float, spin: float, z: float,
		pat: OilPattern = null) -> float:
	var pts: PackedVector3Array = BowlingBall.predict(x, aim, speed, spin, pat)[0]
	for i in range(1, pts.size()):
		if pts[i].z <= z:
			var a := pts[i - 1]
			var b := pts[i]
			return lerpf(a.x, b.x, (z - a.z) / (b.z - a.z)) if b.z != a.z else b.x
	if pts.size() < 2:
		return x
	var a2 := pts[pts.size() - 2]
	var b2 := pts[pts.size() - 1]
	if absf(b2.x) >= BowlingSpec.LANE_HALF or b2.z == a2.z:
		return b2.x * 3.0                                  # in the gutter: well off target
	return b2.x + (b2.x - a2.x) / (b2.z - a2.z) * (z - b2.z)


## The lane as this level of bowler understands it.
static func read_lane(level: int) -> OilPattern:
	var real := BowlingBall.pattern
	if level >= 3 or real == null:
		return real
	if level <= 1:
		return OilPattern.house()
	var fresh := OilPattern.new()                  # this game's shot, but as if new
	fresh.length = real.length
	fresh.mu_oil = real.mu_oil
	fresh.mu_dry = real.mu_dry
	fresh.crown = real.crown
	fresh.skew = real.skew
	return fresh
