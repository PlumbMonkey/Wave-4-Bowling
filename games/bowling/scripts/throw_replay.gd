class_name ThrowReplay
extends RefCounted
## Records the ball and the pins every physics frame of a throw, and plays the
## recording back in slow motion. Playback only moves frozen bodies, so it can't
## change the result. The same stream could later be sent to a network opponent.

const RATE := 0.30             ## playback speed
const LEAD := 0.9              ## seconds before the ball reaches the pins
const TAIL := 2.6              ## seconds after

var frames: Array = []         # [ [ball_xform, pin_xform...], ... ] at the physics rate
var impact := -1               # frame the ball reached the head pin
var hz := 120.0

var _bodies: Array[Node3D] = []
var _t := 0.0
var _start := 0.0
var _end := 0.0


func begin(ball: Node3D, pins: Array) -> void:
	frames.clear()
	impact = -1
	hz = float(Engine.physics_ticks_per_second)
	_bodies.clear()
	_bodies.append(ball)
	for p in pins:
		_bodies.append(p)


func capture() -> void:
	var f: Array[Transform3D] = []
	for b in _bodies:
		f.append(b.global_transform)
	frames.append(f)
	if impact < 0 and f[0].origin.z < -BowlingSpec.LANE_LEN + 0.25:
		impact = frames.size() - 1


func can_play() -> bool:
	return impact >= 0 and frames.size() > impact


## Freeze everything and rewind to just before the impact.
func start_playback() -> void:
	for b in _bodies:
		if b is RigidBody3D:
			(b as RigidBody3D).freeze = true
	_start = maxf(0.0, impact / hz - LEAD)
	_end = minf((frames.size() - 1) / hz, impact / hz + TAIL)
	_t = _start
	_apply(_t)


## Advance; returns false once the replay has finished.
func step(delta: float) -> bool:
	_t += delta * RATE
	_apply(minf(_t, _end))
	return _t < _end


func time() -> float:
	return _t


func start_time() -> float:
	return _start


func progress() -> float:
	return clampf((_t - _start) / maxf(_end - _start, 0.001), 0.0, 1.0)


## Put everything back where the throw left it and let physics resume.
func finish() -> void:
	_apply((frames.size() - 1) / hz)
	for b in _bodies:
		if b is BowlingPin and (b as BowlingPin).in_play():
			(b as RigidBody3D).freeze = false


func ball_position(at_t := -1.0) -> Vector3:
	var t := _t if at_t < 0.0 else at_t
	var i := clampi(int(t * hz), 0, frames.size() - 1)
	return frames[i][0].origin


func _apply(t: float) -> void:
	var fi := t * hz
	var i := clampi(int(fi), 0, frames.size() - 1)
	var j := mini(i + 1, frames.size() - 1)
	var w := fi - float(i)
	var a: Array = frames[i]
	var b: Array = frames[j]
	for k in _bodies.size():
		var ta: Transform3D = a[k]
		_bodies[k].global_transform = ta.interpolate_with(b[k], clampf(w, 0.0, 1.0))
