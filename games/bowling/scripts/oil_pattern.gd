class_name OilPattern
extends RefCounted
## The lane's conditioning - where the oil is, and how it changes.
##
## Every game gets its own house shot (oil length, how slick the oil and the dry
## back end are, how much drier the outside boards are). Then it breaks down:
## each ball dries the track it rolled through and carries a little oil further
## down the lane. So a line that strikes in frame 1 starts hooking early by
## frame 5, and the bowler has to move.

const CELL := 0.5                      ## metres per lengthwise cell of the wear map
const CELLS := 40                      ## 20 m of lane
const BOARDS := 39
const WEAR_PER_BALL := 0.006           ## friction added to each cell a ball rolls through
const WEAR_MAX := 0.05
const CARRY_PER_BALL := 0.08           ## metres of oil pushed past the pattern each ball

var length := BowlingSpec.OIL_LEN      ## where the oil ends (before carrydown)
var mu_oil := BowlingSpec.MU_OIL
var mu_dry := BowlingSpec.MU_DRY
var crown := 0.0                       ## 0 = flat; 0.5 = outside boards half again drier
var carry := 0.0
var jitter := 1.0                      ## per-throw lane-surface variation, set by the game
var balls := 0
var wear := PackedFloat32Array()


func _init() -> void:
	wear.resize(CELLS * BOARDS)


## The published house shot - what the aim guide assumes.
static func house() -> OilPattern:
	return OilPattern.new()


## A fresh, slightly different shot for a new game.
static func random(rng: RandomNumberGenerator) -> OilPattern:
	var p := OilPattern.new()
	p.length = rng.randf_range(10.8, 13.8)
	p.mu_oil = rng.randf_range(0.030, 0.052)
	p.mu_dry = rng.randf_range(0.16, 0.25)
	p.crown = rng.randf_range(0.10, 0.55)
	return p


func feet() -> int:
	return roundi((length + carry) / 0.3048)


## How worn the shot is, for the HUD.
func condition() -> String:
	if balls < 4:
		return "fresh"
	if balls < 12:
		return "transitioning"
	return "broken down"


static func _board(x: float) -> int:
	return clampi(int((x + BowlingSpec.LANE_HALF) / (2.0 * BowlingSpec.LANE_HALF) * BOARDS), 0, BOARDS - 1)


func _cell(p: Vector3) -> int:
	var c := clampi(int(-p.z / CELL), 0, CELLS - 1)
	return c * BOARDS + _board(p.x)


func mu(p: Vector3) -> float:
	var dist := -p.z
	var edge := absf(p.x) / BowlingSpec.LANE_HALF
	var oil := mu_oil * (1.0 + crown * edge * edge * 2.0)
	var end := length + carry
	var m := oil if dist < end else lerpf(oil, mu_dry, clampf(dist - end, 0.0, 1.0))
	if dist < end + 1.0:
		m += wear[_cell(p)]
	return m * jitter


## Called after every ball with the path it rolled.
func wear_path(points: PackedVector3Array) -> void:
	balls += 1
	carry += CARRY_PER_BALL
	var touched := {}
	for p in points:
		if -p.z > length + carry or absf(p.x) > BowlingSpec.LANE_HALF:
			continue
		var i := _cell(p)
		if touched.has(i):
			continue
		touched[i] = true
		wear[i] = minf(WEAR_MAX, wear[i] + WEAR_PER_BALL)
		# the ball is ~8 boards wide; dry the neighbours a little too
		for d: int in [-2, -1, 1, 2]:
			var b: int = _board(p.x) + d
			if b >= 0 and b < BOARDS:
				var j: int = i - _board(p.x) + b
				wear[j] = minf(WEAR_MAX, wear[j] + WEAR_PER_BALL * (0.6 if absi(d) == 1 else 0.3))
