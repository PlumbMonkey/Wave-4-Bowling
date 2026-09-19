class_name BowlingAudio
extends Node
## Every sound in the game, driven by the physics.
##
##   roll      - a loop riding on the ball; louder and higher as it speeds up,
##               swapped for a hollow rattle in the gutter, silent in the air
##   contacts  - ball/pin, pin/pin and pin/deck hits from Jolt contact reports,
##               loudness from the closing speed, a little pitch variety
##   events    - release thump, pit thud, pinsetter, strike/spare/gutter
##               stingers, the ambience drone, UI blips
##
## Contacts during a throw are recorded with their times, so the instant
## replay can play them back in slow motion (pitched down) in step with the
## pictures - the frozen bodies of a replay make no contacts of their own.
##
## Sounds come from tools/make_sounds.py (synthesised, no samples).

const DIR := "res://audio/"
## stingers play on their own bus, so the settings menu can turn them down
const CALLOUTS := ["strike", "spare", "gutter", "final"]
const VOICES := 28
const PAIR_GAP := 0.05
const CRASH_DELAY := 0.09        ## after the ball arrives, count the pins in flight
const CRASH_MIN_PINS := 4           ## seconds before the same pair may sound again

var ball: BowlingBall
var muted := false
## pin sounds are pitched by the pin set (bone is higher and drier)
var pin_pitch := 1.0
## The pin-contact sound family in use: "" is the deep default, "bone_" the
## original, lighter set (kept for the bone pins).
var sound_set := ""
const PIN_FAMILIES := ["ball_pin", "pin_pin", "pin_lane", "pin_kick", "pin_pit", "crash"]
## The authentic set (Settings > Pin sounds > Authentic): real recordings for
## every contact - ball on pin, pin on pin, on the deck, on the kickbacks - a
## whole recorded strike when the ball meets a full rack (the single hits stand
## aside while it plays), and a real pinsetter between balls.
var recorded := false
const HUSH := 1.6                  ## seconds the synth contacts stay quiet under a recorded strike
var _hush := 0.0
var _rack_full := false
var _rec_played := false
var events: Array = []           ## [t, name, position, volume_db, pitch] for the current throw

var _streams := {}               ## name -> Array[AudioStream]
var _pool: Array[AudioStreamPlayer3D] = []
var _next := 0
var _roll: AudioStreamPlayer3D
var _gutter: AudioStreamPlayer3D
var _amb: AudioStreamPlayer
var _ui: AudioStreamPlayer
var _call: AudioStreamPlayer      ## strike / spare / gutter / final stingers
var _recording := false
var _rec_t := 0.0
var _replay_from := 0.0
var _last_pair := {}
var _sfx_bus := 0
var _pit_done := false
var _pins: Array = []
var _crash_t := -1.0          ## counts down once the ball first touches a pin


func setup(b: BowlingBall, pins: Array) -> void:
	ball = b
	_make_buses()
	for n in ["roll_loop", "gutter_loop", "release", "pit", "pinsetter", "strike", "spare",
			"gutter", "final", "ambience_loop", "whoosh", "replay", "select"]:
		_load(n, [n])
	_load("ball_pin", _variants("ball_pin", 6))
	_load("pin_pin", _variants("pin_pin", 8))
	_load("pin_lane", _variants("pin_lane", 6))
	_load("pin_kick", _variants("pin_kick", 4))
	_load("pin_pit", _variants("pin_pit", 3))
	_load("crash", _variants("crash", 3))
	for fam in PIN_FAMILIES:
		_load("bone_" + fam, _variants("bone_" + fam, _streams[fam].size()))
	_load("rec_crash", _variants("rec_crash", 2))
	# single hits cut from the same recordings (tools/cut_recordings.py)
	for fam in [["ball_pin", 3], ["pin_pin", 8], ["pin_lane", 6], ["pin_kick", 4]]:
		_load("rec_" + fam[0], _variants("rec_" + fam[0], fam[1]))
	_load("rec_pinsetter", _variants("rec_pinsetter", 3))
	for n in ["roll_loop", "gutter_loop", "ambience_loop"]:
		_loop(n)

	for i in VOICES:
		var p := _player3d()
		add_child(p)
		_pool.append(p)
	_roll = _player3d(_first("roll_loop"))
	_gutter = _player3d(_first("gutter_loop"))
	for p in [_roll, _gutter]:
		p.volume_db = -80.0
		ball.add_child(p)
		p.play()
	_amb = AudioStreamPlayer.new()
	_amb.stream = _first("ambience_loop")
	_amb.bus = "Ambience"
	_amb.volume_db = -15.0
	add_child(_amb)
	_amb.play()
	_ui = AudioStreamPlayer.new()
	_ui.bus = "SFX"
	add_child(_ui)
	_call = AudioStreamPlayer.new()
	_call.bus = "Callouts"
	add_child(_call)

	ball.contact_monitor = true
	ball.max_contacts_reported = 6
	ball.body_entered.connect(_on_ball_contact)
	_pins = pins
	for pin in pins:
		(pin as RigidBody3D).contact_monitor = true
		(pin as RigidBody3D).max_contacts_reported = 4
		(pin as RigidBody3D).body_entered.connect(_on_pin_contact.bind(pin))


func _make_buses() -> void:
	if AudioServer.get_bus_index("SFX") >= 0:
		_sfx_bus = AudioServer.get_bus_index("SFX")
		return
	AudioServer.add_bus()
	_sfx_bus = AudioServer.bus_count - 1
	AudioServer.set_bus_name(_sfx_bus, "SFX")
	AudioServer.set_bus_send(_sfx_bus, "Master")
	# the hall: a long, dark reverb, mostly dry so hits stay crisp
	var rev := AudioEffectReverb.new()
	rev.room_size = 0.40
	rev.damping = 0.85
	rev.spread = 0.6
	rev.wet = 0.05
	rev.dry = 1.0
	rev.predelay_msec = 20.0
	rev.hipass = 0.25              # keep the reverb off the low end so hits stay punchy
	AudioServer.add_bus_effect(_sfx_bus, rev)
	var lim := AudioEffectLimiter.new()
	lim.ceiling_db = -0.5
	AudioServer.add_bus_effect(_sfx_bus, lim)
	# a gentle safety limiter on the master too (stingers + clatter can stack)
	var master_lim := AudioEffectLimiter.new()
	master_lim.ceiling_db = -1.0
	master_lim.threshold_db = -3.0
	AudioServer.add_bus_effect(0, master_lim)
	AudioServer.add_bus()
	var amb := AudioServer.bus_count - 1
	AudioServer.set_bus_name(amb, "Ambience")
	AudioServer.set_bus_send(amb, "Master")
	AudioServer.add_bus()
	var calls := AudioServer.bus_count - 1
	AudioServer.set_bus_name(calls, "Callouts")
	AudioServer.set_bus_send(calls, "Master")


func _load(key: String, files: Array) -> void:
	var list: Array[AudioStream] = []
	for f in files:
		var path: String = DIR + f + ".wav"
		if ResourceLoader.exists(path):
			list.append(load(path))
	_streams[key] = list


static func _variants(base: String, n: int) -> Array:
	var out := []
	for i in n:
		out.append("%s_%d" % [base, i + 1])
	return out


func _first(key: String) -> AudioStream:
	var l: Array = _streams.get(key, [])
	return l[0] if not l.is_empty() else null


func _loop(key: String) -> void:
	var s := _first(key) as AudioStreamWAV
	if s:
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = int(s.get_length() * s.mix_rate)


func _player3d(stream: AudioStream = null) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.stream = stream
	p.bus = "SFX"
	p.unit_size = 5.0
	p.max_distance = 45.0
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.panning_strength = 0.8
	return p


# ------------------------------------------------------------ playback ------
## Play a one-shot at a position (or at the listener when pos is null).
func play(key: String, pos = null, volume_db := 0.0, pitch := 1.0) -> void:
	if recorded and _hush > 0.0 and PIN_FAMILIES.has(key):
		return                                   # the recorded strike is carrying the sound
	if recorded and key == "pinsetter" and not _streams.get("rec_pinsetter", []).is_empty():
		key = "rec_pinsetter"
	if sound_set != "" and PIN_FAMILIES.has(key) and not _streams.get(sound_set + key, []).is_empty():
		key = sound_set + key
	var list: Array = _streams.get(key, [])
	if list.is_empty() or muted:
		return
	var stream: AudioStream = list[randi() % list.size()]
	if _recording:
		events.append([_rec_t, key, pos, volume_db, pitch])
	if pos == null:
		var ui := _call if CALLOUTS.has(key) else _ui
		ui.stream = stream
		ui.volume_db = volume_db
		ui.pitch_scale = pitch
		ui.play()
		return
	var p := _pool[_next]
	_next = (_next + 1) % _pool.size()
	p.stream = stream
	p.global_position = pos
	p.volume_db = volume_db
	p.pitch_scale = pitch
	p.play()


static func _vol(speed: float, lo: float, hi: float) -> float:
	return linear_to_db(clampf((speed - lo) / (hi - lo), 0.06, 1.0))


func _pair_ok(a: Object, b: Object, gap := PAIR_GAP) -> bool:
	var key := "%d:%d" % [mini(a.get_instance_id(), b.get_instance_id()),
		maxi(a.get_instance_id(), b.get_instance_id())]
	var now := Time.get_ticks_msec() / 1000.0
	if now - float(_last_pair.get(key, -9.0)) < gap:
		return false
	_last_pair[key] = now
	return true


func _on_ball_contact(body: Node) -> void:
	if not ball.released:
		return
	if body is BowlingPin:
		var pin := body as BowlingPin
		var closing := (ball.linear_velocity - pin.linear_velocity).length()
		if recorded and _rack_full and not _rec_played and closing > 1.5:
			# into a full rack: the real thing
			_rec_played = true
			play("rec_crash", Vector3(0.0, 0.3, -18.7), _vol(closing, 1.5, 8.0) + 2.0, randf_range(0.97, 1.03))
			_hush = HUSH
			return
		if closing > 0.4 and _pair_ok(ball, pin):
			play("ball_pin", ball.global_position, _vol(closing, 0.4, 7.0) + 1.0, randf_range(0.94, 1.06) * pin_pitch)
			if _crash_t < 0.0 and closing > 2.0:
				_crash_t = CRASH_DELAY
	elif body is StaticBody3D and body.name.begins_with("Lane") and ball.global_position.z > -1.5:
		if _pair_ok(ball, body):
			play("release", ball.global_position, -2.0, randf_range(0.95, 1.05))


func _on_pin_contact(body: Node, pin: BowlingPin) -> void:
	if body is BowlingBall:
		return                                  # the ball's side plays that one
	var speed := pin.linear_velocity.length()
	if body is BowlingPin:
		var closing := (pin.linear_velocity - (body as BowlingPin).linear_velocity).length()
		if closing > 0.35 and _pair_ok(pin, body):
			play("pin_pin", pin.global_position, _vol(closing, 0.35, 5.0), randf_range(0.9, 1.12) * pin_pitch)
	elif body is StaticBody3D:
		# what did it hit? the maple, the kickback panels, or the pit
		var what := String(body.name)
		# pins sliding around the pit keep re-touching it; give the pit a long gap
		var pit := what.begins_with("Pit") or what.begins_with("Cushion")
		if not _pair_ok(pin, body, 0.6 if pit else PAIR_GAP):
			return
		if what.begins_with("Kickback") or what.begins_with("Capping"):
			if speed > 0.6:
				play("pin_kick", pin.global_position, _vol(speed, 0.6, 5.0) - 1.0, randf_range(0.92, 1.08) * pin_pitch)
		elif what.begins_with("Pit") or what.begins_with("Cushion"):
			if speed > 1.2:
				play("pin_pit", pin.global_position, _vol(speed, 0.5, 5.0) - 3.0, randf_range(0.9, 1.1))
		elif speed > 0.7:
			play("pin_lane", pin.global_position, _vol(speed, 0.7, 5.0) - 1.0, randf_range(0.92, 1.08) * pin_pitch)


func _physics_process(delta: float) -> void:
	if _recording:
		_rec_t += delta
	_hush = maxf(0.0, _hush - delta)
	if ball == null:
		return
	# the roll: on the lane, in the gutter, or in the air / the pit
	var v := ball.linear_velocity.length()
	var p := ball.global_position
	var rolling := ball.released and not ball.freeze and p.y < BowlingSpec.BALL_R + 0.02 and v > 0.2
	var on_lane := rolling and not ball.in_gutter
	var in_gutter := rolling and ball.in_gutter and p.y > -0.2
	_fade(_roll, on_lane and not muted, _vol(v, 0.2, 9.0) - 1.0, delta)
	_roll.pitch_scale = clampf(0.72 + v * 0.055, 0.6, 1.4)
	_fade(_gutter, in_gutter and not muted, _vol(v, 0.2, 9.0) - 4.0, delta)
	_gutter.pitch_scale = clampf(0.8 + v * 0.05, 0.6, 1.4)
	# the rack going: once the ball is into the pins, count what's flying
	if _crash_t > 0.0:
		_crash_t -= delta
		if _crash_t <= 0.0:
			var flying := 0
			for pin in _pins:
				if (pin as BowlingPin).in_play() and (pin as RigidBody3D).linear_velocity.length() > 0.6:
					flying += 1
			if flying >= CRASH_MIN_PINS:
				var loud := float(flying - CRASH_MIN_PINS) / float(10 - CRASH_MIN_PINS)
				play("crash", Vector3(0.0, 0.3, -18.7), lerpf(-9.0, 0.0, loud), randf_range(0.95, 1.05) * pin_pitch)
	if ball.released and not _pit_done and p.z < BowlingSpec.DECK_END + 0.1 and p.y < -0.15:
		_pit_done = true
		play("pit", p, _vol(v, 0.5, 8.0) - 2.0)


func _fade(pl: AudioStreamPlayer3D, on: bool, target_db: float, delta: float) -> void:
	var goal := target_db if on else -60.0
	pl.volume_db = move_toward(pl.volume_db, goal, delta * (90.0 if on else 60.0))


# ------------------------------------------------------------ the throw -----
func start_throw() -> void:
	events.clear()
	_recording = true
	_rec_t = 0.0
	_pit_done = false
	_crash_t = -1.0
	_rec_played = false
	_hush = 0.0
	var up := 0
	for pin in _pins:
		if (pin as BowlingPin).in_play() and not (pin as BowlingPin).is_down():
			up += 1
	_rack_full = up == 10


func stop_recording() -> void:
	_recording = false


## Slow-motion replay: play the recorded events as the replay clock passes them.
func begin_replay(from_t: float) -> void:
	_replay_from = from_t
	play("replay", null, -16.0)


func replay_to(t: float, rate: float) -> void:
	for e in events:
		var et: float = e[0]
		if et > _replay_from and et <= t and e[2] != null:
			var was := _recording
			_recording = false
			play(e[1], e[2], float(e[3]) - 2.0, float(e[4]) * lerpf(0.55, 1.0, rate))
			_recording = was
	_replay_from = maxf(_replay_from, t)


## Bus volumes from the settings menu, each 0..1.
static func set_volumes(master: float, sfx: float, amb: float, callouts: float) -> void:
	for pair in [["Master", master], ["SFX", sfx], ["Ambience", amb], ["Callouts", callouts]]:
		var i := AudioServer.get_bus_index(pair[0])
		if i >= 0:
			AudioServer.set_bus_volume_db(i, linear_to_db(maxf(float(pair[1]), 0.0001)))


func set_muted(m: bool) -> void:
	muted = m
	AudioServer.set_bus_mute(0, m)
