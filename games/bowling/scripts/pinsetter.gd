class_name Pinsetter
extends Node3D
## Sets the rack, decides when the pins have settled, counts what fell, sweeps
## deadwood and respots the pins still standing for the second ball.

const SETTLE_TIMEOUT := 4.0     ## seconds after the ball reaches the pins
const SETTLE_QUIET := 0.6       ## pins must stay still this long

## The machine you watch between balls: the sweep bar drops in front of the
## pins and rakes the deadwood into the pit, and the setting table comes down
## to lift the pins still standing (second ball) or to set a fresh rack.
const BAR_FRONT := -17.62       ## the sweep bar's z when it drops (in front of the head pin)
const BAR_BACK := -20.1         ## ...and when it has raked everything into the pit
const BAR_UP := 1.25            ## hidden behind the masking
const BAR_DOWN := 0.13
const TABLE_Z := -18.68         ## over the middle of the pin deck
const TABLE_UP := 1.35
const PACE := 1.25              ## every move of the cycle takes this much longer (20% slower)
const MODEL := "res://art/pinsetter/pinsetter.glb"   ## the Blender machine (bowl_pinsetter.py)

signal cycle_done

var pins: Array[BowlingPin] = []
var busy := false               ## an animated cycle is running
var _quiet := 0.0
var _bar: Node3D
var _table: Node3D
var _frame: Node3D
var PIN_HANG := 0.406           ## table height minus the base of a pin hanging from it
var _cur: Tween
var _speed := 1.0
var _cycle := 0                 ## bumps on cancel, so an old cycle stops touching the pins


func _ready() -> void:
	for spot in BowlingSpec.pin_spots():
		var p := BowlingPin.new()
		p.name = "Pin%d" % (pins.size() + 1)
		p.spot = spot
		add_child(p)
		pins.append(p)
	_build_machine()
	full_rack()


func _build_machine() -> void:
	if ResourceLoader.exists(MODEL):
		# the modelled machine: sweep, setting table and side frames
		var inst: Node = (load(MODEL) as PackedScene).instantiate()
		for n in ["PS_Sweep", "PS_Table", "PS_Frame"]:
			var part := inst.find_child(n, true, false) as Node3D
			var xf := part.global_transform if part.is_inside_tree() else part.transform
			part.get_parent().remove_child(part)
			add_child(part)
			part.transform = xf
			match n:
				"PS_Sweep": _bar = part
				"PS_Table": _table = part
				"PS_Frame": _frame = part
		inst.free()
		PIN_HANG = 0.296               # a pin's head sits 85 mm up inside its spotting cup
		_park()
		return
	var iron := StandardMaterial3D.new()
	iron.albedo_color = Color(0.07, 0.065, 0.08)
	iron.metallic = 0.75
	iron.roughness = 0.35
	var bar := BoxMesh.new()
	bar.size = Vector3(2.0 * BowlingSpec.LANE_HALF + 0.06, 0.2, 0.05)
	bar.material = iron
	_bar = MeshInstance3D.new()
	_bar.mesh = bar
	_bar.visible = false
	add_child(_bar)
	var table := BoxMesh.new()
	table.size = Vector3(2.0 * BowlingSpec.LANE_HALF - 0.02, 0.05, 1.05)
	table.material = iron
	_table = MeshInstance3D.new()
	_table.mesh = table
	_table.visible = false
	add_child(_table)
	_park()


func _park() -> void:
	_bar.position = Vector3(0.0, BAR_UP, BAR_FRONT)
	_table.position = Vector3(0.0, TABLE_UP, TABLE_Z)
	_bar.visible = false
	_table.visible = false


func full_rack() -> void:
	cancel()
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
	cancel()
	for p in pins:
		if not p.in_play():
			continue
		if p.is_down():
			p.sweep()
		else:
			var at := p.global_position
			p.set_at(Vector3(at.x, 0.0, at.z))


# ------------------------------------------------------------ the machine --
## Run the machine: "full" sweeps everything and sets ten fresh pins; "deadwood"
## lifts the standing pins, sweeps the rest and sets them back down.
## Emits cycle_done at the end (not if cancelled).
func animate(kind: String) -> void:
	cancel()
	var me := _cycle
	busy = true
	_speed = 1.0
	_bar.visible = true
	_table.visible = true
	var lifted: Array[BowlingPin] = []
	if kind == "deadwood":
		for p in pins:
			if p.in_play() and not p.is_down():
				var at := p.global_position
				p.freeze = true
				p.global_transform = Transform3D(Basis.IDENTITY, Vector3(at.x, 0.0, at.z))
				lifted.append(p)
		await _table_to(PIN_HANG, [], 0.45)                  # down onto the pin tops
		if me != _cycle: return
		await _table_to(PIN_HANG + 0.34, lifted, 0.35)       # and up with them
		if me != _cycle: return
	await _step(_bar, "position:y", BAR_DOWN, 0.28)
	if me != _cycle: return
	await _rake(lifted, 0.6)
	if me != _cycle: return
	for p in pins:
		if p.in_play() and not lifted.has(p):
			p.sweep()
	await _step(_bar, "position:y", BAR_UP, 0.25)
	if me != _cycle: return
	_bar.position.z = BAR_FRONT
	if kind == "full":
		for p in pins:                                       # ten fresh pins in the table
			p.process_mode = Node.PROCESS_MODE_INHERIT
			p.freeze = true
			p.visible = true
			p.global_transform = Transform3D(Basis.IDENTITY, p.spot + Vector3(0.0, _table.position.y - PIN_HANG, 0.0))
		lifted.assign(pins)
	await _table_to(PIN_HANG, lifted, 0.55 if kind == "full" else 0.35)
	if me != _cycle: return
	for p in lifted:
		var at := p.global_position
		p.set_at(p.spot if kind == "full" else Vector3(at.x, 0.0, at.z))
	await _table_to(TABLE_UP, [], 0.4)
	if me != _cycle: return
	_park()
	busy = false
	cycle_done.emit()


## Speed the rest of the cycle up (the player pressed a button).
func hurry() -> void:
	_speed = 4.0
	if _cur and _cur.is_valid():
		_cur.set_speed_scale(_speed)


## Stop any cycle in progress (a new game, the main menu).
func cancel() -> void:
	_cycle += 1
	if _cur and _cur.is_valid():
		_cur.kill()
	_cur = null
	busy = false
	if _bar:
		_park()


func _step(node: Node3D, prop: String, to: float, dur: float) -> void:
	_cur = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_cur.set_speed_scale(_speed)
	_cur.tween_property(node, prop, to, dur * PACE)
	await _cur.finished


## Move the table, carrying *hung* pins under it.
func _table_to(to_y: float, hung: Array, dur: float) -> void:
	_cur = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_cur.set_speed_scale(_speed)
	_cur.tween_method(func(y: float):
		_table.position.y = y
		for p in hung:
			var at: Vector3 = (p as BowlingPin).global_position
			(p as BowlingPin).global_position = Vector3(at.x, y - PIN_HANG, at.z),
		_table.position.y, to_y, dur * PACE)
	await _cur.finished


## Rake the deck: the bar runs back to the pit, pushing every pin it reaches.
func _rake(skip: Array, dur: float) -> void:
	_cur = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	_cur.set_speed_scale(_speed)
	_cur.tween_method(func(z: float):
		_bar.position.z = z
		for p in pins:
			if not p.in_play() or skip.has(p):
				continue
			var at := p.global_position
			if absf(at.x) < BowlingSpec.LANE_HALF + 0.05 and at.z > z - 0.07 and at.y > -0.3:
				p.freeze = true
				var nz := z - 0.07
				p.global_position = Vector3(at.x, at.y if nz > BowlingSpec.DECK_END else -0.25, nz),
		BAR_FRONT, BAR_BACK, dur * PACE)
	await _cur.finished
