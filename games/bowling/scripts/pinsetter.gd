class_name Pinsetter
extends Node3D
## Sets the rack, decides when the pins have settled, counts what fell, sweeps
## deadwood and respots the pins still standing for the second ball.

const SETTLE_TIMEOUT := 4.0     ## seconds after the ball reaches the pins
const SETTLE_QUIET := 0.6       ## pins must stay still this long

var pins: Array[BowlingPin] = []
var _quiet := 0.0


func _ready() -> void:
	for spot in BowlingSpec.pin_spots():
		var p := BowlingPin.new()
		p.name = "Pin%d" % (pins.size() + 1)
		p.spot = spot
		add_child(p)
		pins.append(p)
	full_rack()


func full_rack() -> void:
	for p in pins:
		p.set_at(p.spot)


func standing() -> Array[BowlingPin]:
	var out: Array[BowlingPin] = []
	for p in pins:
		if p.in_play() and not p.is_down():
			out.append(p)
	return out


## Call every physics frame after the ball is thrown. Returns true once the
## deck has been quiet for SETTLE_QUIET seconds.
func tick_settle(delta: float) -> bool:
	for p in pins:
		if p.in_play() and not p.is_settled() and p.global_position.y > -0.5:
			_quiet = 0.0
			return false
	_quiet += delta
	return _quiet >= SETTLE_QUIET


func reset_settle() -> void:
	_quiet = 0.0


## After the first ball: sweep the fallen pins, stand the others back up where
## they are (the real machine lifts them and puts them down in place).
func clear_deadwood() -> void:
	for p in pins:
		if not p.in_play():
			continue
		if p.is_down():
			p.sweep()
		else:
			var at := p.global_position
			p.set_at(Vector3(at.x, 0.0, at.z))
