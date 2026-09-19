extends Node3D
## Phantom Bowling - the game loop.
##
##   AIM (pull back to set speed) ──release──▶ process_throw() ──▶ ROLL (full speed)
##    ▲                                                              │
##    │        REPLAY (optional, slow motion) ◀── RESULT ◀── SETTLE ◀┘
##    └────────────── pinsetter resets ◀─────────────┘
##
## Every throw, local or remote, goes through process_throw(params). The
## network layer will call the same function with the other player's throw.
##
## Command-line (after `--`):  --autoplay   bowl a whole game by itself
##                             --shots=DIR  save screenshots, quit at game end

signal throw_made(params: Dictionary)
signal roll_scored(pins: int, card: ScoreCard)
## Network groundwork: everything needed to reproduce a throw elsewhere.
## { v, params: {x, aim, power, spin}, inputs: [spin, steer] per physics tick, pins, ball_end }
signal throw_completed(record: Dictionary)

enum State { AIM, ROLL, SETTLE, RESULT, REPLAY, GAME_OVER }

const SETTLE_TIMEOUT := 5.0
const RESULT_HOLD := 2.6         ## how long the replay offer stays up
const MIN_DRAW := 0.06           ## pull back at least this far before releasing
const MOUSE_DRAW_PX := 380.0     ## mouse travel for a full draw
const HINT_AIM := "Aim R-stick / J L / mouse   Pull back L-stick / S / mouse → release RT / click / Space   " + \
	"Move D-pad / A D   Spin LB RB / Q E   Ball Y / B   Pins D-pad up / P   Mute View / M"

var alley: Alley
var setter: Pinsetter
var ball: BowlingBall
var cam: Camera3D
var hud: BowlingHud
var guide: AimGuide
var audio: BowlingAudio
var theme: AlleyTheme
var env: Environment
var replay := ThrowReplay.new()
var alley_id := "lounge"
var ball_kinds := ["spectre", "p", "skull"]
var ball_index := 0
var pin_style := "classic"
var card := ScoreCard.new()

var state := State.AIM
var stance_x := BowlingSpec.board_x(12)
var aim := 0.0
var release_spin := -0.5         ## right-hander's hook by default
var draw := 0.0                  ## how far the ball is pulled back, 0..1 = the power
var _mouse_draw := 0.0
var _key_draw := 0.0
var _stick_draw := 0.0
var _guide_key := Vector4.INF
var _settle_t := 0.0
var _result_t := 0.0
var _standing_before := 10
var _cam_look := Vector3(0, 0.2, -18)
var _roll_t := 0.0

var autoplay := false
var shots_dir := ""
var _shot_n := 0
var _rng := RandomNumberGenerator.new()
var _auto_wait := 0.0
var _auto_replays := 0
var _auto_next := {}
var _replay_shot := false
var _lane_rng := RandomNumberGenerator.new()
var profile := GraphicsProfile.DESKTOP
var _inputs := PackedFloat32Array()
var _tick := 0
var _last_params := {}
var _remote := {}                 ## a received throw being played through


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--autoplay":
			autoplay = true
		elif a.begins_with("--shots="):
			shots_dir = a.trim_prefix("--shots=")
			autoplay = true
			DirAccess.make_dir_recursive_absolute(shots_dir)
	_rng.seed = 7
	profile = GraphicsProfile.detect()
	var saved := BowlingSettings.load_all()
	ball_index = clampi(int(saved.ball), 0, 2)
	pin_style = String(saved.pins)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--pins="):
			pin_style = a.trim_prefix("--pins=")

	_build_environment()
	alley = Alley.new()
	add_child(alley)
	theme = AlleyTheme.create(self, alley_id, env, profile)
	if theme:
		alley.show_greybox(false)
	else:
		_build_greybox_lights()
	setter = Pinsetter.new()
	add_child(setter)
	ball = BowlingBall.new()
	add_child(ball)
	audio = BowlingAudio.new()
	add_child(audio)
	audio.setup(ball, setter.pins)
	if bool(saved.muted) and not autoplay:
		audio.set_muted(true)
	cam = Camera3D.new()
	cam.fov = 58.0
	cam.near = 0.05
	add_child(cam)
	cam.current = true
	GraphicsProfile.apply(profile, env, get_viewport())
	guide = AimGuide.new()
	add_child(guide)
	hud = BowlingHud.new()
	add_child(hud)
	_apply_pins(false)
	new_game()


func new_game() -> void:
	card = ScoreCard.new()
	if autoplay:
		_lane_rng.seed = 11
	else:
		_lane_rng.randomize()
	BowlingBall.pattern = OilPattern.random(_lane_rng)
	setter.full_rack()
	_standing_before = 10
	hud.update_card(card)
	hud.set_replay(false)
	_enter_aim()


func _enter_aim() -> void:
	state = State.AIM
	draw = 0.0
	_mouse_draw = 0.0
	_key_draw = 0.0
	_auto_wait = 1.4
	_guide_key = Vector4.INF
	if autoplay:
		_auto_next = _auto_params()
		stance_x = _auto_next.x
		aim = _auto_next.aim
		release_spin = _auto_next.spin
	hud.set_power(0.0, false)
	hud.set_hint(HINT_AIM)
	_show_lane()
	guide.visible = true
	if autoplay and card.current_frame() < 10:
		ball_index = card.current_frame() % ball_kinds.size()      # show off every ball
		_apply_ball()
	_snap_camera()


static func speed_for(power: float) -> float:
	return lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, power)


## The one entry point for a throw. params: {x, aim, power, spin}
func process_throw(params: Dictionary) -> void:
	var x := clampf(float(params.get("x", 0.0)), -BowlingSpec.X_MAX, BowlingSpec.X_MAX)
	var a := clampf(float(params.get("aim", 0.0)), -BowlingSpec.AIM_MAX, BowlingSpec.AIM_MAX)
	var p := clampf(float(params.get("power", 0.7)), 0.0, 1.0)
	var s := clampf(float(params.get("spin", 0.0)), -1.0, 1.0)
	# no two throws alike: the lane surface varies a little (part of the record,
	# so a remote copy of this throw rolls on the same lane)
	var j := float(params.get("jitter", _lane_rng.randf_range(0.96, 1.04)))
	BowlingBall.pattern.jitter = j
	_standing_before = setter.standing().size()
	ball.launch(x, a, speed_for(p), s)
	_inputs.clear()
	_tick = 0
	_last_params = {"x": x, "aim": a, "power": p, "spin": s, "jitter": j}
	replay.begin(ball, setter.pins)
	audio.start_throw()
	guide.visible = false
	state = State.ROLL
	_roll_t = 0.0
	hud.set_hint("Steer L-stick / A D   Hook LB RB / Q E")
	throw_made.emit({"x": x, "aim": a, "power": p, "spin": s})
	_shot("roll", 0.5)


func _physics_process(delta: float) -> void:
	match state:
		State.AIM:
			_update_aim(delta)
			if autoplay:
				# pull back like a player would, then let go
				_auto_wait -= delta
				_key_draw = move_toward(_key_draw, _auto_next.power, delta * 0.9)
				if _auto_wait <= 0.0:
					process_throw(_auto_next)
				elif absf(_auto_wait - 0.25) < 0.005:
					_shot("aim")
			elif Input.is_action_just_pressed("next_ball"):
				ball_index = (ball_index + 1) % ball_kinds.size()
				_apply_ball()
				audio.play("select", null, -10.0)
				BowlingSettings.save_value("ball", ball_index)
			elif Input.is_action_just_pressed("pin_style"):
				var order: Array = BowlingPin.STYLE_ORDER
				pin_style = order[(order.find(pin_style) + 1) % order.size()]
				_apply_pins(true)
				BowlingSettings.save_value("pins", pin_style)
			elif Input.is_action_just_pressed("release"):
				_try_release()
		State.ROLL:
			_roll_t += delta
			replay.capture()
			var si := 0.0
			var st := 0.0
			if not _remote.is_empty():
				var inp: PackedFloat32Array = _remote.inputs
				if _tick * 2 + 1 < inp.size():
					si = inp[_tick * 2]
					st = inp[_tick * 2 + 1]
			elif not autoplay:
				si = Input.get_axis("spin_left", "spin_right")
				st = Input.get_axis("steer_left", "steer_right")
			ball.spin_input = si
			ball.steer_input = st
			_inputs.append(si)
			_inputs.append(st)
			_tick += 1
			var z := ball.global_position.z
			if z < -BowlingSpec.LANE_LEN + 0.2 or ball.global_position.y < -0.5 \
					or (ball.linear_velocity.length() < 0.15 and z < -1.0):
				state = State.SETTLE
				_settle_t = 0.0
				setter.reset_settle()
				_shot("impact", 0.25)
		State.SETTLE:
			_settle_t += delta
			replay.capture()
			if (_settle_t > 1.2 and setter.tick_settle(delta)) or _settle_t > SETTLE_TIMEOUT:
				_finish_roll()
		State.RESULT:
			_result_t += delta
			var auto_replay := autoplay and _auto_replays < 1 and _result_t > 0.8 \
				and _standing_before == 10 and setter.standing().is_empty()
			if (Input.is_action_just_pressed("replay") or auto_replay) and replay.can_play():
				_start_replay()
			elif Input.is_action_just_pressed("confirm") or Input.is_action_just_pressed("release") \
					or _result_t > RESULT_HOLD:
				_advance()
		State.REPLAY:
			var going := replay.step(delta)
			audio.replay_to(replay.time(), ThrowReplay.RATE)
			hud.set_replay(true, replay.progress())
			if autoplay and not _replay_shot and replay.progress() > 0.45:
				_replay_shot = true
				_shot("replay")
			if not going or Input.is_action_just_pressed("confirm") \
					or Input.is_action_just_pressed("replay"):
				replay.finish()
				hud.set_replay(false)
				_advance()
	_update_camera(delta)


func _update_aim(delta: float) -> void:
	stance_x = clampf(stance_x + Input.get_axis("move_left", "move_right") * 0.9 * delta,
		-BowlingSpec.X_MAX, BowlingSpec.X_MAX)
	aim = clampf(aim + Input.get_axis("aim_left", "aim_right") * deg_to_rad(2.5) * delta,
		-BowlingSpec.AIM_MAX, BowlingSpec.AIM_MAX)
	if Input.is_action_just_pressed("spin_left"):
		release_spin = clampf(release_spin - 0.25, -1.0, 1.0)
	if Input.is_action_just_pressed("spin_right"):
		release_spin = clampf(release_spin + 0.25, -1.0, 1.0)
	# the draw: left stick pulled toward you, mouse dragged toward you, or S / W
	var sy := 0.0
	for pad in Input.get_connected_joypads():
		sy = maxf(sy, Input.get_joy_axis(pad, JOY_AXIS_LEFT_Y))
	var target := clampf((sy - 0.15) / 0.8, 0.0, 1.0)
	_stick_draw = move_toward(_stick_draw, target, delta * 4.0)
	if Input.is_action_pressed("draw_more"):
		_key_draw = minf(1.0, _key_draw + delta * 0.9)
	if Input.is_action_pressed("draw_less"):
		_key_draw = maxf(0.0, _key_draw - delta * 0.9)
	draw = maxf(maxf(_stick_draw, _mouse_draw), _key_draw)
	# the ball swings back and down as it's drawn
	ball.hold(Vector3(stance_x + 0.22, 0.75 - draw * 0.42, 0.55 + draw * 0.7))
	var shown := draw if draw > 0.0 else 0.35
	var key := Vector4(snappedf(stance_x, 0.002), snappedf(aim, 0.0002), snappedf(shown, 0.01),
		release_spin)
	if key != _guide_key:
		_guide_key = key
		guide.show_throw(stance_x, aim, speed_for(shown), release_spin, draw)
	hud.set_speed(draw, speed_for(draw))


func _try_release() -> void:
	if state != State.AIM:
		return
	if draw < MIN_DRAW:
		hud.flash("PULL BACK", BowlingHud.VIOLET, 0.5)
		return
	process_throw({"x": stance_x, "aim": aim, "power": draw, "spin": release_spin})


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED   # first click grabs the mouse
		elif state == State.AIM:
			_try_release()
		elif state == State.RESULT or state == State.REPLAY:
			_result_t = RESULT_HOLD
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED \
			and state == State.AIM:
		aim = clampf(aim + event.relative.x * 0.0002, -BowlingSpec.AIM_MAX, BowlingSpec.AIM_MAX)
		_mouse_draw = clampf(_mouse_draw + event.relative.y / MOUSE_DRAW_PX, 0.0, 1.0)
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event.is_action_pressed("mute"):
		audio.set_muted(not audio.muted)
		BowlingSettings.save_value("muted", audio.muted)
		hud.flash("SOUND OFF" if audio.muted else "SOUND ON", BowlingHud.INK, 0.4)
	elif event.is_action_pressed("restart"):
		new_game()
	elif event.is_action_pressed("confirm") and state == State.GAME_OVER:
		new_game()


func _finish_roll() -> void:
	state = State.RESULT
	_result_t = 0.0
	var standing_now := setter.standing().size()
	var pins := clampi(_standing_before - standing_now, 0, _standing_before)
	card.roll(pins)
	hud.update_card(card)
	BowlingBall.pattern.wear_path(_ball_path())
	throw_completed.emit({"v": 1, "params": _last_params.duplicate(), "inputs": _inputs.duplicate(),
		"pins": pins, "ball_end": ball.global_position})
	_remote = {}
	roll_scored.emit(pins, card)
	audio.stop_recording()
	_announce(pins, standing_now)
	hud.set_hint("X  Instant replay        A / click  Continue")
	_shot("result", 0.4)


## Play a throw recorded elsewhere (another player's, over ManorNet) through the
## same path a local throw takes. Returns false if we're not ready for a ball.
func play_remote_throw(record: Dictionary) -> bool:
	if state != State.AIM or not record.has("params"):
		return false
	_remote = record
	process_throw(record.params)
	return true


func _ball_path() -> PackedVector3Array:
	var out := PackedVector3Array()
	for k in range(0, replay.frames.size(), 6):
		out.append((replay.frames[k][0] as Transform3D).origin)
	return out


func _show_lane() -> void:
	var p := BowlingBall.pattern
	hud.set_lane("OIL  %d ft house shot  ·  %s" % [p.feet(), p.condition()])


func _start_replay() -> void:
	state = State.REPLAY
	_auto_replays += 1
	replay.start_playback()
	audio.begin_replay(replay.start_time())
	hud.set_replay(true, 0.0)
	hud.set_hint("X / A  Skip replay")
	cam.global_position = Vector3(0.42, 0.24, -16.9)
	_cam_look = replay.ball_position()


## After the result (and any replay): next ball, next frame, or game over.
func _advance() -> void:
	if card.is_complete():
		state = State.GAME_OVER
		hud.flash("FINAL  %d" % card.total(), BowlingHud.BRASS, 60.0)
		audio.play("final", null, -18.0)
		hud.set_hint("Press A / Enter to bowl again")
		if autoplay:
			await get_tree().create_timer(1.0).timeout
			_shot("final")
			if shots_dir != "":
				get_tree().quit()
			else:
				new_game()
		return
	audio.play("pinsetter", Vector3(0.0, 0.9, -19.0), -7.0)
	if card.needs_full_rack():
		setter.full_rack()
	else:
		setter.clear_deadwood()
	_enter_aim()


func _announce(pins: int, standing_now: int) -> void:
	if ball.in_gutter and pins == 0:
		hud.flash("GUTTER", BowlingHud.VIOLET)
		audio.play("gutter", null, -23.0)
	elif pins == 10 and _standing_before == 10:
		hud.flash("STRIKE!")
		audio.play("strike", null, -20.0)
	elif standing_now == 0:
		hud.flash("SPARE!")
		audio.play("spare", null, -21.0)
	elif pins == 0:
		hud.flash("MISS", BowlingHud.VIOLET)
	else:
		hud.flash(str(pins), BowlingHud.INK, 0.6)


# ------------------------------------------------------------------ camera --
func _snap_camera() -> void:
	var t := _aim_cam()
	cam.global_position = t[0]
	_cam_look = t[1]
	cam.look_at(_cam_look)


func _aim_cam() -> Array:
	var pos := Vector3(stance_x * 0.5, 1.45 + draw * 0.1, 2.7 + draw * 0.25)
	var look := Vector3(stance_x * 0.2 + sin(aim) * 14.0, 0.15, -15.0)
	return [pos, look]


const PIN_CAM := Vector3(0.5, 0.8, -15.9)
const PIN_LOOK := Vector3(0.0, 0.15, -18.7)


func _update_camera(delta: float) -> void:
	var pos: Vector3
	var look: Vector3
	var bp := ball.global_position
	var rate := 5.0
	match state:
		State.AIM:
			var t := _aim_cam()
			pos = t[0]
			look = t[1]
		State.ROLL:
			# swoop down behind the ball, then hand over to the pin camera
			if bp.z > -12.0:
				pos = Vector3(bp.x * 0.6, 0.55, bp.z + 2.0)
				look = Vector3(bp.x * 0.5, 0.1, bp.z - 5.0)
				rate = 3.5 if _roll_t < 0.5 else 7.0
			else:
				pos = PIN_CAM
				look = PIN_LOOK
				rate = 4.0
		State.REPLAY:
			var rb := replay.ball_position()
			pos = Vector3(0.42, 0.24, clampf(rb.z + 1.6, -17.4, -16.6))
			look = Vector3(rb.x * 0.6, 0.18, minf(rb.z, -18.2)) if rb.z > -18.6 else PIN_LOOK
			rate = 3.0
		_:
			pos = PIN_CAM
			look = PIN_LOOK
	var k := 1.0 - exp(-rate * delta)
	cam.global_position = cam.global_position.lerp(pos, k)
	_cam_look = _cam_look.lerp(look, k)
	cam.look_at(_cam_look)


func _apply_pins(announce: bool) -> void:
	BowlingPin.set_style(pin_style, setter.pins)
	pin_style = BowlingPin.style
	if theme:
		theme.set_pin_style(pin_style)
	audio.pin_pitch = {"bone": 1.14, "reliquary": 1.06}.get(pin_style, 1.0)
	if announce:
		audio.play("select", null, -10.0, 0.8)
		hud.flash("%s PINS" % String(BowlingPin.STYLES[pin_style].name).to_upper(), BowlingHud.INK, 0.5)
	_apply_ball()


func _apply_ball() -> void:
	var n := ball.set_skin(ball_kinds[ball_index])
	var where := "   ·   PINS  %s" % BowlingPin.STYLES[pin_style].name
	where += ("   ·   " + theme.display_name()) if theme else ""
	if profile == GraphicsProfile.WEB:
		where += "   ·   web"
	hud.set_ball("BALL  %s%s" % [n, where])


# -------------------------------------------------------------- the world ---
func _build_environment() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.02, 0.012, 0.035)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.40, 0.32, 0.55)
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true
	env.glow_intensity = 0.6
	env.ssr_enabled = true            # the Desktop profile from the PRD
	env.ssao_enabled = true
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


## Lights for the grey box only - a themed alley brings its own.
func _build_greybox_lights() -> void:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, 25, 0)
	sun.light_energy = 0.25
	sun.light_color = Color(0.6, 0.6, 1.0)
	sun.shadow_enabled = true
	add_child(sun)
	# candle-warm pools down the lane
	for z in [1.0, -3.0, -7.0, -11.0, -15.0]:
		var o := OmniLight3D.new()
		o.position = Vector3(0, 2.6, z)
		o.light_color = Color(1.0, 0.7, 0.42)
		o.light_energy = 1.6
		o.omni_range = 6.0
		o.shadow_enabled = z > -8.0
		add_child(o)
	var pins := SpotLight3D.new()
	pins.position = Vector3(0, 2.4, -16.8)
	pins.look_at_from_position(pins.position, Vector3(0, 0.2, -18.7))
	pins.light_color = Color(0.85, 0.8, 1.0)
	pins.light_energy = 5.0
	pins.spot_range = 5.0
	pins.spot_angle = 30.0
	pins.shadow_enabled = true
	add_child(pins)


# ---------------------------------------------------------------- autoplay --
func _auto_params() -> Dictionary:
	# aim for the 1-3 pocket with a little human error
	return {
		"x": BowlingSpec.board_x(10) + _rng.randf_range(-0.03, 0.03),
		"aim": deg_to_rad(0.3 + _rng.randf_range(-0.25, 0.25)),
		"power": 0.72 + _rng.randf_range(-0.05, 0.05),
		"spin": -0.8 + _rng.randf_range(-0.15, 0.15),
	}


func _shot(tag: String, delay := 0.0) -> void:
	if shots_dir == "" or _shot_n >= 60:
		return
	var n := _shot_n
	_shot_n += 1
	if delay > 0.0:
		await get_tree().create_timer(delay, true, false, true).timeout
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(shots_dir.path_join("%02d_f%d_%s.png" % [n, card.current_frame() + 1, tag]))
