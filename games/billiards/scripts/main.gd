extends Node3D

const ReplayBufferClass = preload("res://scripts/replay_buffer.gd")
const SpectralBallClass = preload("res://scripts/spectral_ball.gd")
const AimGuideClass = preload("res://scripts/aim_guide.gd")

const TABLE_LENGTH := 8.8
const TABLE_WIDTH := 4.4
const BED_Y := 0.92
const BALL_RADIUS := 0.145
const BALL_Y := BED_Y + BALL_RADIUS + 0.012
const STOP_SPEED := 0.035
const MAX_SHOT_IMPULSE := 4.2

enum GameState { AIMING, ROLLING, REPLAY }

var state := GameState.AIMING
var balls: Array[RigidBody3D] = []
var cue_ball: SpectralBall
var replay_buffer := ReplayBufferClass.new()
var aim_guide: AimGuide
var cue_visual: MeshInstance3D
var camera: Camera3D
var camera_yaw := 0.0
var cue_elevation := 0.0
var top_down := false
var charge := 0.0
var was_charging := false
var settling_frames := 0
var current_player := 1
var shot_pocketed := false
var potted_numbers: Array[int] = []

var replay_frames: Array[Dictionary] = []
var replay_cursor := 0.0
var replay_restore := {}
var replay_auto := false

var status_label: Label
var player_label: Label
var power_bar: ProgressBar
var replay_badge: Label
var tip_label: Label
var resin_stream: AudioStreamWAV
var cushion_stream: AudioStreamWAV


func _ready() -> void:
	_ensure_input_map()
	_build_world()
	_build_room()
	_build_table()
	_build_balls()
	_build_camera_and_aiming()
	_build_ui()
	_build_audio()
	_update_ui("Table open — Player 1 to break")
	get_viewport().get_window().title = "Spectral Manor Billiards — First Playable"


func _physics_process(delta: float) -> void:
	if state == GameState.REPLAY:
		_update_replay(delta)
		return

	replay_buffer.capture(balls)
	if state == GameState.AIMING:
		_update_aiming(delta)
	else:
		_update_rolling()
	_update_camera(delta)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and state == GameState.AIMING and not top_down:
		camera_yaw -= event.relative.x * 0.0025
	if event.is_action_pressed("toggle_view"):
		top_down = not top_down
		_update_ui("Tactical view" if top_down else "Player view")
	if event.is_action_pressed("replay") and state == GameState.AIMING:
		var last_shot := replay_buffer.get_last_shot()
		if last_shot.size() > 2:
			_start_replay(last_shot, false)
		else:
			_update_ui("Take a shot before requesting a replay")
	if event.is_action_pressed("reset_rack"):
		_reset_rack()


func _update_aiming(delta: float) -> void:
	var turn_axis := Input.get_axis("aim_left", "aim_right")
	camera_yaw -= turn_axis * delta * 1.55
	var elevation_axis := Input.get_axis("aim_down", "aim_up")
	cue_elevation = clampf(cue_elevation + elevation_axis * delta * 0.7, -0.18, 0.32)

	var charging := Input.is_action_pressed("charge_shot")
	if charging:
		charge = minf(1.0, charge + delta * 0.55)
		was_charging = true
	if Input.is_action_just_pressed("strike"):
		_strike(maxf(charge, 0.28))
	elif was_charging and not charging and charge > 0.08 and Input.get_connected_joypads().is_empty():
		_strike(charge)
	was_charging = charging
	power_bar.value = charge * 100.0

	var direction := _shot_direction()
	var guide_distance := _aim_distance(direction)
	aim_guide.visible = cue_ball != null and not cue_ball.pocketed
	if aim_guide.visible:
		aim_guide.update_guide(cue_ball.global_position, direction, guide_distance, delta)
		_update_cue_visual(direction)


func _update_rolling() -> void:
	var moving := false
	for ball in balls:
		if not ball.pocketed and (ball.linear_velocity.length() > STOP_SPEED or ball.angular_velocity.length() > 0.12):
			moving = true
			break
	if moving:
		settling_frames = 0
		return
	settling_frames += 1
	if settling_frames < 18:
		return
	for ball in balls:
		if not ball.pocketed:
			ball.linear_velocity = Vector3.ZERO
			ball.angular_velocity = Vector3.ZERO
	if cue_ball.pocketed:
		_respawn_cue_ball()
		shot_pocketed = false
		current_player = 2 if current_player == 1 else 1
	elif not shot_pocketed:
		current_player = 2 if current_player == 1 else 1
	state = GameState.AIMING
	charge = 0.0
	settling_frames = 0
	_update_ui("Player %d — line up your shot" % current_player)


func _strike(power: float) -> void:
	if state != GameState.AIMING or cue_ball == null or cue_ball.pocketed:
		return
	state = GameState.ROLLING
	shot_pocketed = false
	settling_frames = 0
	replay_buffer.mark_shot_start()
	var direction := _shot_direction()
	var impulse := direction * lerpf(0.65, MAX_SHOT_IMPULSE, power)
	impulse.y = clampf(cue_elevation, -0.05, 0.2) * power
	cue_ball.apply_central_impulse(impulse)
	# A small torque term previews the English system while preserving stable breaks.
	cue_ball.apply_torque_impulse(Vector3(direction.z, 0.0, -direction.x) * cue_elevation * power * 0.12)
	charge = 0.0
	aim_guide.visible = false
	cue_visual.visible = false
	_update_ui("Shot in motion")


func _shot_direction() -> Vector3:
	return Vector3(cos(camera_yaw), 0.0, sin(camera_yaw)).normalized()


func _aim_distance(direction: Vector3) -> float:
	if cue_ball == null:
		return 1.0
	var from := cue_ball.global_position + direction * (BALL_RADIUS + 0.02)
	var to := from + direction * 9.0
	var query := PhysicsRayQueryParameters3D.create(from, to, 3, [cue_ball.get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return 5.5
	return clampf(from.distance_to(hit.position), 0.3, 5.5)


func _update_cue_visual(direction: Vector3) -> void:
	if cue_ball == null:
		return
	cue_visual.visible = true
	var pullback := 0.36 + charge * 0.75
	var center := cue_ball.global_position - direction * (1.45 + pullback)
	center.y += 0.09 + cue_elevation * 0.7
	cue_visual.global_position = center
	cue_visual.look_at(center + direction, Vector3.UP)
	cue_visual.rotate_object_local(Vector3.RIGHT, PI * 0.5)


func _update_camera(delta: float) -> void:
	if cue_ball == null:
		return
	var target := cue_ball.global_position if not cue_ball.pocketed else Vector3(0.0, BALL_Y, 0.0)
	var desired: Vector3
	if top_down:
		desired = Vector3(0.0, 10.8, 0.01)
	else:
		var direction := _shot_direction()
		desired = target - direction * 4.1 + Vector3.UP * 2.35
	camera.global_position = camera.global_position.lerp(desired, 1.0 - exp(-delta * 5.2))
	camera.look_at(target + Vector3.UP * (0.05 if top_down else 0.2), Vector3.FORWARD if top_down else Vector3.UP)


func _start_replay(frames: Array[Dictionary], automatic: bool) -> void:
	if frames.size() < 2:
		return
	replay_frames = frames
	replay_cursor = 0.0
	replay_auto = automatic
	replay_restore.clear()
	for ball in balls:
		replay_restore[ball.get_instance_id()] = {
			"transform": ball.global_transform,
			"linear": ball.linear_velocity,
			"angular": ball.angular_velocity,
			"visible": ball.visible,
			"pocketed": ball.pocketed,
		}
		ball.freeze = true
	state = GameState.REPLAY
	aim_guide.visible = false
	cue_visual.visible = false
	replay_badge.visible = true
	replay_badge.text = "SPECTRAL REPLAY  •  0.25×" if automatic else "LAST SHOT REPLAY"
	_update_ui("A memory caught in the manor")


func _update_replay(delta: float) -> void:
	var speed := 15.0 if replay_auto else 60.0
	replay_cursor += delta * speed
	var frame_index := int(replay_cursor)
	if frame_index >= replay_frames.size():
		_finish_replay()
		return
	_apply_replay_frame(replay_frames[frame_index])
	var orbit := replay_cursor * 0.006
	var focus := cue_ball.global_position if cue_ball != null else Vector3(0.0, BALL_Y, 0.0)
	if replay_auto:
		focus = _find_replay_focus(replay_frames[frame_index])
	camera.global_position = focus + Vector3(cos(orbit) * 2.7, 1.45, sin(orbit) * 2.7)
	camera.look_at(focus, Vector3.UP)


func _apply_replay_frame(frame: Dictionary) -> void:
	for ball in balls:
		var id := ball.get_instance_id()
		if frame.has(id):
			ball.global_transform = frame[id]["transform"]
			ball.visible = frame[id]["visible"]


func _find_replay_focus(frame: Dictionary) -> Vector3:
	for ball in balls:
		var id := ball.get_instance_id()
		if frame.has(id) and ball.number in potted_numbers:
			return frame[id]["transform"].origin
	return Vector3(0.0, BALL_Y, 0.0)


func _finish_replay() -> void:
	for ball in balls:
		var id := ball.get_instance_id()
		if replay_restore.has(id):
			var saved: Dictionary = replay_restore[id]
			ball.global_transform = saved["transform"]
			ball.linear_velocity = saved["linear"]
			ball.angular_velocity = saved["angular"]
			ball.visible = saved["visible"]
			ball.pocketed = saved["pocketed"]
			ball.freeze = ball.pocketed
	replay_badge.visible = false
	state = GameState.ROLLING if replay_auto else GameState.AIMING
	replay_frames.clear()
	_update_ui("The table returns to the present")


func _on_pocket_body_entered(body: Node, pocket_position: Vector3) -> void:
	if state == GameState.REPLAY or not body is SpectralBall:
		return
	var ball := body as SpectralBall
	if ball.pocketed:
		return
	ball.pocketed = true
	ball.linear_velocity = Vector3.ZERO
	ball.angular_velocity = Vector3.ZERO
	ball.freeze = true
	ball.visible = false
	if ball.number > 0:
		shot_pocketed = true
		potted_numbers.append(ball.number)
		_update_ui("Ball %d claimed by the manor" % ball.number)
	else:
		_update_ui("Scratch — cue ball returns after the shot")
	var recent := replay_buffer.get_recent(1.5)
	if recent.size() > 12:
		_start_replay(recent, true)


func _respawn_cue_ball() -> void:
	cue_ball.pocketed = false
	cue_ball.freeze = true
	cue_ball.visible = true
	cue_ball.global_position = Vector3(-2.8, BALL_Y, 0.0)
	cue_ball.linear_velocity = Vector3.ZERO
	cue_ball.angular_velocity = Vector3.ZERO
	await get_tree().physics_frame
	cue_ball.freeze = false


func _reset_rack() -> void:
	if state == GameState.REPLAY:
		_finish_replay()
	for ball in balls:
		ball.queue_free()
	balls.clear()
	potted_numbers.clear()
	replay_buffer.clear()
	current_player = 1
	state = GameState.AIMING
	charge = 0.0
	_build_balls()
	_update_ui("Fresh rack — Player 1 to break")


func _build_world() -> void:
	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("071015")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("29404a")
	environment.ambient_light_energy = 0.34
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.adjustment_enabled = true
	environment.adjustment_contrast = 1.14
	environment.adjustment_saturation = 0.9
	world_environment.environment = environment
	add_child(world_environment)

	var moon := DirectionalLight3D.new()
	moon.light_color = Color("9bbce8")
	moon.light_energy = 0.55
	moon.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
	moon.shadow_enabled = true
	add_child(moon)


func _build_room() -> void:
	var wood := _material(Color("1b0c0a"), 0.42, 0.08)
	var black_wood := _material(Color("090607"), 0.5, 0.0)
	var brass := _material(Color("8d5b22"), 0.24, 0.78)
	var burgundy := _material(Color("390711"), 0.86, 0.0)
	_create_static_box("Parquet", Vector3(15.0, 0.24, 11.0), Vector3(0.0, -0.12, 0.0), wood, 2)
	_create_static_box("BackWall", Vector3(15.0, 7.5, 0.25), Vector3(0.0, 3.5, -5.3), black_wood, 2)
	_create_static_box("LeftWall", Vector3(0.25, 7.5, 11.0), Vector3(-7.3, 3.5, 0.0), black_wood, 2)
	_create_static_box("RightWall", Vector3(0.25, 7.5, 11.0), Vector3(7.3, 3.5, 0.0), black_wood, 2)

	for side in [-1.0, 1.0]:
		for index in 3:
			var curtain := MeshInstance3D.new()
			var mesh := CylinderMesh.new()
			mesh.top_radius = 0.16
			mesh.bottom_radius = 0.34
			mesh.height = 5.4
			mesh.radial_segments = 16
			curtain.mesh = mesh
			curtain.material_override = burgundy
			curtain.position = Vector3(side * (5.8 + index * 0.32), 3.0, -4.95)
			add_child(curtain)

	for x in [-3.0, 0.0, 3.0]:
		var lamp := OmniLight3D.new()
		lamp.light_color = Color("ffad62")
		lamp.light_energy = 5.0
		lamp.omni_range = 6.0
		lamp.shadow_enabled = true
		lamp.position = Vector3(x, 4.4, 0.0)
		add_child(lamp)
		_create_mesh_box(Vector3(0.07, 0.85, 0.07), lamp.position + Vector3(0.0, 0.5, 0.0), brass)

	for x in [-5.8, 5.8]:
		for z in [-3.8, 3.8]:
			var sconce := OmniLight3D.new()
			sconce.light_color = Color("ff7e3b")
			sconce.light_energy = 2.2
			sconce.omni_range = 4.0
			sconce.position = Vector3(x, 2.8, z)
			add_child(sconce)


func _build_table() -> void:
	var mahogany := _material(Color("2b0d08"), 0.3, 0.05)
	var brass := _material(Color("9f6b28"), 0.2, 0.82)
	var felt := _material(Color("073d35"), 0.88, 0.0)
	var rubber := PhysicsMaterial.new()
	rubber.friction = 0.25
	rubber.bounce = 0.78

	_create_static_box("SlateBed", Vector3(TABLE_LENGTH, 0.22, TABLE_WIDTH), Vector3(0.0, BED_Y - 0.11, 0.0), felt, 2)
	_create_mesh_box(Vector3(TABLE_LENGTH + 1.15, 0.38, TABLE_WIDTH + 1.15), Vector3(0.0, BED_Y - 0.36, 0.0), mahogany)

	# Cushions are split around corner and side-pocket openings.
	for z in [-TABLE_WIDTH * 0.5 - 0.12, TABLE_WIDTH * 0.5 + 0.12]:
		for x in [-2.25, 2.25]:
			var rail := _create_static_box("LongCushion", Vector3(3.72, 0.34, 0.30), Vector3(x, BED_Y + 0.08, z), mahogany, 2)
			rail.physics_material_override = rubber
	for x in [-TABLE_LENGTH * 0.5 - 0.12, TABLE_LENGTH * 0.5 + 0.12]:
		var rail := _create_static_box("EndCushion", Vector3(0.30, 0.34, 3.55), Vector3(x, BED_Y + 0.08, 0.0), mahogany, 2)
		rail.physics_material_override = rubber

	for x in [-3.8, 3.8]:
		for z in [-1.75, 1.75]:
			_create_mesh_box(Vector3(0.52, 0.92, 0.52), Vector3(x, 0.46, z), mahogany)
			var foot := MeshInstance3D.new()
			var foot_mesh := SphereMesh.new()
			foot_mesh.radius = 0.34
			foot_mesh.height = 0.68
			foot.mesh = foot_mesh
			foot.material_override = brass
			foot.position = Vector3(x, 0.12, z)
			add_child(foot)

	var pocket_positions := [
		Vector3(-TABLE_LENGTH * 0.5, BALL_Y, -TABLE_WIDTH * 0.5),
		Vector3(0.0, BALL_Y, -TABLE_WIDTH * 0.5),
		Vector3(TABLE_LENGTH * 0.5, BALL_Y, -TABLE_WIDTH * 0.5),
		Vector3(-TABLE_LENGTH * 0.5, BALL_Y, TABLE_WIDTH * 0.5),
		Vector3(0.0, BALL_Y, TABLE_WIDTH * 0.5),
		Vector3(TABLE_LENGTH * 0.5, BALL_Y, TABLE_WIDTH * 0.5),
	]
	for pocket_position in pocket_positions:
		_build_pocket(pocket_position, brass)


func _build_pocket(pocket_position: Vector3, brass: Material) -> void:
	var rim := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.22
	torus.outer_radius = 0.34
	torus.rings = 24
	torus.ring_segments = 12
	rim.mesh = torus
	rim.material_override = brass
	rim.position = pocket_position - Vector3.UP * 0.05
	add_child(rim)
	var darkness := MeshInstance3D.new()
	var dark_mesh := CylinderMesh.new()
	dark_mesh.top_radius = 0.235
	dark_mesh.bottom_radius = 0.18
	dark_mesh.height = 0.11
	darkness.mesh = dark_mesh
	darkness.material_override = _material(Color("010203"), 1.0, 0.0)
	darkness.position = pocket_position - Vector3.UP * 0.09
	add_child(darkness)

	var area := Area3D.new()
	area.name = "Pocket"
	area.collision_layer = 4
	area.collision_mask = 1
	area.position = pocket_position
	var collision := CollisionShape3D.new()
	var shape := SphereShape3D.new()
	shape.radius = 0.28
	collision.shape = shape
	area.add_child(collision)
	add_child(area)
	area.body_entered.connect(_on_pocket_body_entered.bind(pocket_position))


func _build_balls() -> void:
	var ball_colors := [
		Color("f0e8cf"), Color("d6a329"), Color("28488e"), Color("8a2730"),
		Color("512d7c"), Color("d46c24"), Color("245e42"), Color("76252a"),
		Color("11131a"), Color("d6a329"), Color("28488e"), Color("8a2730"),
		Color("512d7c"), Color("d46c24"), Color("245e42"), Color("76252a"),
	]
	cue_ball = _create_ball(0, Vector3(-2.8, BALL_Y, 0.0), ball_colors[0])
	var rack_order := [1, 10, 2, 3, 8, 11, 6, 14, 4, 5, 13, 15, 7, 12, 9]
	var index := 0
	var row_spacing := BALL_RADIUS * 1.78
	for row in 5:
		var x := 1.55 + row * row_spacing
		for column in row + 1:
			var z := (float(column) - float(row) * 0.5) * BALL_RADIUS * 2.04
			var number: int = rack_order[index]
			_create_ball(number, Vector3(x, BALL_Y, z), ball_colors[number])
			index += 1


func _create_ball(number: int, spawn_position: Vector3, color: Color) -> SpectralBall:
	var ball := SpectralBallClass.new() as SpectralBall
	ball.name = "CueBall" if number == 0 else "Ball%02d" % number
	ball.configure(number)
	ball.position = spawn_position
	ball.physics_material_override = PhysicsMaterial.new()
	ball.physics_material_override.friction = 0.16
	ball.physics_material_override.bounce = 0.94

	var mesh_instance := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = BALL_RADIUS
	sphere.height = BALL_RADIUS * 2.0
	sphere.radial_segments = 32
	sphere.rings = 16
	mesh_instance.mesh = sphere
	var material := _material(color, 0.12, 0.32)
	material.clearcoat_enabled = true
	material.clearcoat = 0.9
	material.clearcoat_roughness = 0.08
	material.emission_enabled = number != 0
	material.emission = color * 0.28
	material.emission_energy_multiplier = 0.55
	mesh_instance.material_override = material
	ball.add_child(mesh_instance)

	var collision := CollisionShape3D.new()
	var shape := SphereShape3D.new()
	shape.radius = BALL_RADIUS
	collision.shape = shape
	ball.add_child(collision)

	var number_label := Label3D.new()
	number_label.text = "☾" if number == 0 else str(number)
	number_label.font_size = 48
	number_label.outline_size = 9
	number_label.modulate = Color("f9e6bd")
	number_label.outline_modulate = Color("160a0d")
	number_label.position = Vector3(0.0, BALL_RADIUS + 0.014, 0.0)
	number_label.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	number_label.pixel_size = 0.0032
	ball.add_child(number_label)

	add_child(ball)
	balls.append(ball)
	ball.impact.connect(_on_ball_impact)
	return ball


func _build_camera_and_aiming() -> void:
	camera = Camera3D.new()
	camera.current = true
	camera.fov = 48.0
	camera.position = Vector3(-5.5, 3.2, 4.2)
	add_child(camera)

	aim_guide = AimGuideClass.new() as AimGuide
	add_child(aim_guide)

	cue_visual = MeshInstance3D.new()
	var cue_mesh := CylinderMesh.new()
	cue_mesh.top_radius = 0.025
	cue_mesh.bottom_radius = 0.055
	cue_mesh.height = 2.65
	cue_mesh.radial_segments = 16
	cue_visual.mesh = cue_mesh
	cue_visual.material_override = _material(Color("5b1a13"), 0.25, 0.32)
	add_child(cue_visual)


func _build_ui() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 34)
	margin.add_theme_constant_override("margin_top", 26)
	margin.add_theme_constant_override("margin_right", 34)
	margin.add_theme_constant_override("margin_bottom", 26)
	canvas.add_child(margin)
	var layout := VBoxContainer.new()
	layout.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(layout)

	var title := Label.new()
	title.text = "SPECTRAL MANOR"
	title.add_theme_font_size_override("font_size", 28)
	title.add_theme_color_override("font_color", Color("d6b875"))
	layout.add_child(title)
	var subtitle := Label.new()
	subtitle.text = "B I L L I A R D S"
	subtitle.add_theme_font_size_override("font_size", 15)
	subtitle.add_theme_color_override("font_color", Color("91c9ba"))
	layout.add_child(subtitle)

	player_label = Label.new()
	player_label.add_theme_font_size_override("font_size", 21)
	player_label.add_theme_color_override("font_color", Color("f5e7c8"))
	layout.add_child(player_label)
	status_label = Label.new()
	status_label.add_theme_font_size_override("font_size", 17)
	status_label.add_theme_color_override("font_color", Color("a8c9bf"))
	layout.add_child(status_label)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0.0, 14.0)
	layout.add_child(spacer)
	var power_caption := Label.new()
	power_caption.text = "SHOT POWER"
	power_caption.add_theme_font_size_override("font_size", 12)
	layout.add_child(power_caption)
	power_bar = ProgressBar.new()
	power_bar.custom_minimum_size = Vector2(280.0, 12.0)
	power_bar.show_percentage = false
	layout.add_child(power_bar)

	tip_label = Label.new()
	tip_label.text = "Aim: Left stick / A D / mouse     Charge: RT / hold Space or RMB     Strike: RB / Enter or LMB\nTactical: Y / T     Replay: X / R     Re-rack: Back / Esc"
	tip_label.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	tip_label.position = Vector2(34.0, -72.0)
	tip_label.add_theme_font_size_override("font_size", 14)
	tip_label.add_theme_color_override("font_color", Color("c6beb0"))
	canvas.add_child(tip_label)

	replay_badge = Label.new()
	replay_badge.visible = false
	replay_badge.set_anchors_preset(Control.PRESET_CENTER_TOP)
	replay_badge.position = Vector2(-130.0, 34.0)
	replay_badge.add_theme_font_size_override("font_size", 22)
	replay_badge.add_theme_color_override("font_color", Color("8fffe3"))
	canvas.add_child(replay_badge)


func _update_ui(message: String) -> void:
	if status_label == null:
		return
	player_label.text = "PLAYER %d" % current_player
	status_label.text = message


func _build_audio() -> void:
	resin_stream = _make_impact_stream(0.072, 1650.0, 0.34)
	cushion_stream = _make_impact_stream(0.11, 230.0, 0.52)


func _on_ball_impact(hit_position: Vector3, intensity: float, cushion: bool) -> void:
	if DisplayServer.get_name() == "headless" or intensity < 0.08 or state == GameState.REPLAY:
		return
	var player := AudioStreamPlayer3D.new()
	player.stream = cushion_stream if cushion else resin_stream
	player.position = hit_position
	player.volume_db = clampf(linear_to_db(clampf(intensity / 4.0, 0.015, 1.0)), -28.0, 0.0)
	player.pitch_scale = clampf(0.84 + intensity * 0.08, 0.78, 1.28)
	player.max_distance = 18.0
	add_child(player)
	player.finished.connect(player.queue_free)
	player.play()


func _make_impact_stream(duration: float, frequency: float, decay: float) -> AudioStreamWAV:
	var rate := 22050
	var sample_count := int(duration * rate)
	var data := PackedByteArray()
	data.resize(sample_count * 2)
	for sample in sample_count:
		var t := float(sample) / float(rate)
		var envelope := exp(-t / maxf(0.01, duration * decay))
		var overtone := sin(TAU * frequency * t) + sin(TAU * frequency * 1.91 * t) * 0.32
		var value := int(clampf(overtone * envelope * 0.52, -1.0, 1.0) * 32767.0)
		data.encode_s16(sample * 2, value)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.stereo = false
	stream.data = data
	return stream


func _create_static_box(node_name: String, size: Vector3, position: Vector3, material: Material, layer: int) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = node_name
	body.collision_layer = layer
	body.collision_mask = 1
	body.position = position
	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh_instance.mesh = mesh
	mesh_instance.material_override = material
	body.add_child(mesh_instance)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)
	add_child(body)
	return body


func _create_mesh_box(size: Vector3, position: Vector3, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	instance.mesh = mesh
	instance.material_override = material
	instance.position = position
	add_child(instance)
	return instance


func _material(color: Color, roughness: float, metallic: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material


func _ensure_input_map() -> void:
	_add_key_action("aim_left", KEY_A)
	_add_key_action("aim_right", KEY_D)
	_add_key_action("aim_up", KEY_W)
	_add_key_action("aim_down", KEY_S)
	_add_key_action("charge_shot", KEY_SPACE)
	_add_key_action("strike", KEY_ENTER)
	_add_key_action("toggle_view", KEY_T)
	_add_key_action("replay", KEY_R)
	_add_key_action("reset_rack", KEY_ESCAPE)
	_add_mouse_action("charge_shot", MOUSE_BUTTON_RIGHT)
	_add_mouse_action("strike", MOUSE_BUTTON_LEFT)
	_add_joy_axis_action("aim_left", JOY_AXIS_LEFT_X, -1.0)
	_add_joy_axis_action("aim_right", JOY_AXIS_LEFT_X, 1.0)
	_add_joy_axis_action("aim_up", JOY_AXIS_RIGHT_Y, -1.0)
	_add_joy_axis_action("aim_down", JOY_AXIS_RIGHT_Y, 1.0)
	_add_joy_axis_action("charge_shot", JOY_AXIS_TRIGGER_RIGHT, 1.0)
	_add_joy_button_action("strike", JOY_BUTTON_RIGHT_SHOULDER)
	_add_joy_button_action("toggle_view", JOY_BUTTON_Y)
	_add_joy_button_action("replay", JOY_BUTTON_X)
	_add_joy_button_action("reset_rack", JOY_BUTTON_BACK)


func _add_key_action(action: StringName, key: Key) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.18)
	var event := InputEventKey.new()
	event.physical_keycode = key
	InputMap.action_add_event(action, event)


func _add_mouse_action(action: StringName, button: MouseButton) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = button
	InputMap.action_add_event(action, event)


func _add_joy_axis_action(action: StringName, axis: JoyAxis, value: float) -> void:
	var event := InputEventJoypadMotion.new()
	event.axis = axis
	event.axis_value = value
	InputMap.action_add_event(action, event)


func _add_joy_button_action(action: StringName, button: JoyButton) -> void:
	var event := InputEventJoypadButton.new()
	event.button_index = button
	InputMap.action_add_event(action, event)
