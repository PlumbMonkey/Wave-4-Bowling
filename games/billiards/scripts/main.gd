extends Node3D

const ReplayBufferClass = preload("res://scripts/replay_buffer.gd")
const SpectralBallClass = preload("res://scripts/spectral_ball.gd")
const AimGuideClass = preload("res://scripts/aim_guide.gd")
const EightBallRulesClass = preload("res://scripts/eight_ball_rules.gd")
const BilliardsAIClass = preload("res://scripts/ai_opponent.gd")
const CueControllerClass = preload("res://scripts/cue_controller.gd")
const TrajectoryGuideClass = preload("res://scripts/trajectory_guide.gd")

const TABLE_LENGTH := 8.8
const TABLE_WIDTH := 4.4
const BED_Y := 0.92
const BALL_RADIUS := 0.145
const BALL_Y := BED_Y + BALL_RADIUS + 0.012
const STOP_SPEED := 0.035
const MAX_SHOT_IMPULSE := 4.2

enum GameState { MENU, BALL_IN_HAND, AIMING, AI_THINKING, ROLLING, REPLAY, MATCH_OVER }

var state := GameState.MENU
var balls: Array[RigidBody3D] = []
var cue_ball: SpectralBall
var replay_buffer := ReplayBufferClass.new()
var rules := EightBallRulesClass.new()
var computer := BilliardsAIClass.new()
var cue_controls := CueControllerClass.new()
var aim_guide: AimGuide
var tactical_guide: AimGuide
var trajectory_guide: TrajectoryGuide
var cue_visual: MeshInstance3D
var camera: Camera3D
var camera_yaw := 0.0
var camera_pitch := 0.38
var top_down := false
var charge := 0.0
var was_charging := false
var stroke_armed := false
var stroke_pull := 0.0
var previous_stroke_axis := 0.0
var placement_velocity := Vector3.ZERO
var shot_guide_enabled := true
var settling_frames := 0
var current_player := 1
var shot_pocketed := false
var potted_numbers: Array[int] = []
var pocket_positions: Array[Vector3] = []
var pocket_markers: Array[MeshInstance3D] = []
var called_pocket_index := 0
var ball_in_hand_kitchen_only := false
var selected_mode := EightBallRules.Mode.PRACTICE
var selected_difficulty := BilliardsAI.Difficulty.MEDIUM
var ai_plan := {}
var ai_aim_time := 0.0
var ai_start_yaw := 0.0
var ai_target_yaw := 0.0

var replay_frames: Array[Dictionary] = []
var replay_cursor := 0.0
var replay_restore := {}
var replay_auto := false

var status_label: Label
var player_label: Label
var power_bar: ProgressBar
var replay_badge: Label
var tip_label: Label
var menu_panel: PanelContainer
var difficulty_picker: OptionButton
var guide_checkbox: CheckButton
var match_over_panel: PanelContainer
var match_over_label: Label
var spin_dot: ColorRect
var spin_label: Label
var called_pocket_label: Label
var ai_tactic_label: Label
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
	_show_mode_menu()
	get_viewport().get_window().title = "Spectral Manor Billiards — Controller & Guidance v0.5"


func _physics_process(delta: float) -> void:
	if state == GameState.MENU or state == GameState.MATCH_OVER:
		return
	if state == GameState.REPLAY:
		_update_replay(delta)
		return

	replay_buffer.capture(balls)
	if state == GameState.AIMING:
		_update_aiming(delta)
	elif state == GameState.BALL_IN_HAND:
		_update_ball_in_hand(delta)
	elif state == GameState.AI_THINKING:
		_update_ai_thinking(delta)
	else:
		_update_rolling()
	_update_camera(delta)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and state == GameState.AIMING and not top_down and not _is_computer_turn():
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
		if state == GameState.MENU:
			return
		_reset_rack()
	if event.is_action_pressed("call_pocket") and state == GameState.AIMING and not _is_computer_turn():
		_cycle_called_pocket()
	if event.is_action_pressed("toggle_guide") and state != GameState.MENU:
		shot_guide_enabled = not shot_guide_enabled
		if guide_checkbox != null:
			guide_checkbox.button_pressed = shot_guide_enabled
		if not shot_guide_enabled:
			trajectory_guide.hide_guide()
		_update_ui("Shot guide %s" % ("enabled" if shot_guide_enabled else "disabled"))


func _update_aiming(delta: float) -> void:
	if _is_computer_turn():
		_begin_ai_turn()
		return
	var controller_stroking := _update_controller_stroke(delta)
	if not controller_stroking:
		_update_camera_controls(delta)
	var spin_input := Input.get_vector("spin_left", "spin_right", "spin_down", "spin_up")
	cue_controls.update_spin(spin_input, delta)
	_update_spin_reticle()

	var keyboard_charging := Input.is_key_pressed(KEY_SPACE) or Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)
	if keyboard_charging and not controller_stroking:
		charge = minf(1.0, charge + delta * 0.55)
		was_charging = true
	if Input.is_action_just_pressed("strike"):
		_strike(maxf(charge, 0.28))
	elif was_charging and not keyboard_charging and charge > 0.08 and not controller_stroking:
		_strike(charge)
	was_charging = keyboard_charging
	power_bar.value = charge * 100.0

	var direction := _shot_direction()
	aim_guide.visible = false
	if cue_ball != null and not cue_ball.pocketed:
		_update_human_trajectory(direction)
		_update_cue_visual(direction)


func _update_controller_stroke(delta: float) -> bool:
	var joypads := Input.get_connected_joypads()
	if joypads.is_empty():
		stroke_armed = false
		return false
	var device: int = joypads[0]
	var trigger := Input.get_joy_axis(device, JOY_AXIS_TRIGGER_RIGHT)
	if trigger < 0.16:
		if stroke_armed:
			stroke_armed = false
			stroke_pull = 0.0
			charge = 0.0
		return false
	var axis := Input.get_joy_axis(device, JOY_AXIS_RIGHT_Y)
	if not stroke_armed:
		stroke_armed = true
		stroke_pull = 0.0
		previous_stroke_axis = axis
		_update_ui("Stroke armed — pull the right stick back, then push forward")
	stroke_pull = maxf(stroke_pull, maxf(axis, 0.0))
	charge = stroke_pull
	var forward_speed := maxf((previous_stroke_axis - axis) / maxf(delta, 0.001), 0.0)
	if stroke_pull > 0.16 and axis < -0.28:
		var power := clampf(maxf(-axis, forward_speed * 0.075) * 0.82 + stroke_pull * 0.18, 0.22, 1.0)
		stroke_armed = false
		stroke_pull = 0.0
		_strike(power)
		return true
	previous_stroke_axis = axis
	return true


func _update_camera_controls(delta: float) -> void:
	var yaw_input := Input.get_axis("aim_left", "aim_right") + Input.get_axis("camera_left", "camera_right")
	var pitch_input := Input.get_axis("camera_up", "camera_down")
	camera_yaw -= clampf(yaw_input, -1.0, 1.0) * delta * 1.65
	camera_pitch = clampf(camera_pitch + pitch_input * delta * 0.72, 0.12, 0.82)


func _update_human_trajectory(direction: Vector3) -> void:
	if not shot_guide_enabled:
		trajectory_guide.hide_guide()
		return
	var segments: Array = []
	var origin := cue_ball.global_position + Vector3.UP * 0.025
	var ray_start := origin + direction * (BALL_RADIUS + 0.02)
	var ray_end := ray_start + direction * 9.0
	var query := PhysicsRayQueryParameters3D.create(ray_start, ray_end, 3, [cue_ball.get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	var contact: Vector3 = ray_end if hit.is_empty() else (hit["position"] as Vector3) + Vector3.UP * 0.025
	segments.append(PackedVector3Array([origin, contact]))
	if not hit.is_empty() and hit.collider is SpectralBall:
		var target := hit.collider as SpectralBall
		var object_direction := target.global_position - cue_ball.global_position
		object_direction.y = 0.0
		object_direction = object_direction.normalized()
		var object_start := target.global_position + Vector3.UP * 0.025
		var object_end := _trajectory_ray_end(object_start, object_direction, [cue_ball.get_rid(), target.get_rid()], 4.8)
		segments.append(PackedVector3Array([object_start, object_end]))
		var cue_deflection := direction - object_direction * direction.dot(object_direction)
		cue_deflection.y = 0.0
		if cue_deflection.length() > 0.08:
			cue_deflection = cue_deflection.normalized()
			var deflect_start: Vector3 = contact
			var deflect_end := _trajectory_ray_end(deflect_start, cue_deflection, [cue_ball.get_rid(), target.get_rid()], 2.3)
			segments.append(PackedVector3Array([deflect_start, deflect_end]))
	elif not hit.is_empty() and hit.has("normal"):
		var reflected := direction.bounce(hit.normal).normalized()
		var bounce_end := _trajectory_ray_end(contact, reflected, [cue_ball.get_rid()], 2.8)
		segments.append(PackedVector3Array([contact, bounce_end]))
	trajectory_guide.show_segments(segments)


func _trajectory_ray_end(start: Vector3, direction: Vector3, exclusions: Array[RID], distance: float) -> Vector3:
	var finish := start + direction * distance
	var query := PhysicsRayQueryParameters3D.create(start + direction * 0.03, finish, 3, exclusions)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return finish if hit.is_empty() else hit.position + Vector3.UP * 0.025


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
	var result: Dictionary = rules.evaluate_shot()
	current_player = rules.current_player
	if bool(result.get("respot_eight", false)):
		_respot_ball(8, Vector3(1.55, BALL_Y, 0.0))
	shot_pocketed = false
	charge = 0.0
	settling_frames = 0
	if int(result["winner"]) > 0:
		_show_match_over(int(result["winner"]), str(result["message"]))
		return
	if bool(result.get("ball_in_hand", false)):
		_begin_ball_in_hand(false)
		_update_ui(str(result["message"]))
		return
	state = GameState.AIMING
	cue_controls.reset()
	_update_spin_reticle()
	_update_called_pocket_display()
	_update_ui(str(result["message"]))


func _strike(power: float) -> void:
	if state != GameState.AIMING or cue_ball == null or cue_ball.pocketed:
		return
	_strike_direction(_shot_direction(), power)


func _strike_direction(direction: Vector3, power: float) -> void:
	if cue_ball == null or cue_ball.pocketed:
		return
	state = GameState.ROLLING
	shot_pocketed = false
	settling_frames = 0
	rules.begin_shot()
	if rules.legal_targets(current_player) == [8]:
		rules.call_pocket(called_pocket_index)
	replay_buffer.mark_shot_start()
	var impulse := direction * lerpf(0.65, MAX_SHOT_IMPULSE, power)
	cue_ball.apply_central_impulse(impulse)
	cue_ball.apply_torque_impulse(cue_controls.torque_for_shot(direction, power))
	charge = 0.0
	aim_guide.visible = false
	trajectory_guide.hide_guide()
	cue_visual.visible = false
	called_pocket_label.visible = false
	for marker in pocket_markers:
		marker.visible = false
	tactical_guide.visible = false
	ai_tactic_label.visible = false
	_update_ui("Shot in motion")


func _begin_ai_turn() -> void:
	if not _is_computer_turn() or state != GameState.AIMING:
		return
	var positions := {}
	for ball in balls:
		if not ball.pocketed and ball.number > 0:
			positions[ball.number] = ball.global_position
	ai_plan = computer.plan_shot(cue_ball.global_position, positions, rules.legal_targets(2), pocket_positions)
	trajectory_guide.hide_guide()
	cue_controls.spin = ai_plan.get("spin", Vector2.ZERO)
	_update_spin_reticle()
	if rules.legal_targets(2) == [8]:
		called_pocket_index = int(ai_plan.get("pocket_index", 0))
		_update_called_pocket_display()
	var direction: Vector3 = ai_plan.get("direction", Vector3.RIGHT)
	ai_start_yaw = camera_yaw
	ai_target_yaw = atan2(direction.z, direction.x)
	ai_aim_time = 0.0
	state = GameState.AI_THINKING
	ai_tactic_label.text = "THE MANOR • %s" % str(ai_plan.get("shot_type", "DIRECT"))
	ai_tactic_label.visible = true
	_update_called_pocket_display()
	_update_ui("The manor studies the table…")


func _update_ai_thinking(delta: float) -> void:
	ai_aim_time += delta
	var t := clampf(ai_aim_time / 1.45, 0.0, 1.0)
	camera_yaw = lerp_angle(ai_start_yaw, ai_target_yaw, t * t * (3.0 - 2.0 * t))
	var direction := _shot_direction()
	charge = clampf(float(ai_plan.get("power", 0.45)) * t, 0.0, 1.0)
	power_bar.value = charge * 100.0
	aim_guide.visible = true
	aim_guide.update_guide(cue_ball.global_position, direction, _aim_distance(direction), delta)
	_update_cue_visual(direction)
	_update_tactical_guide(delta)
	if t >= 1.0:
		var planned_direction: Vector3 = ai_plan.get("direction", direction)
		var planned_power := float(ai_plan.get("power", 0.45))
		_strike_direction(planned_direction, planned_power)


func _is_computer_turn() -> bool:
	return selected_mode == EightBallRules.Mode.VS_CPU and current_player == 2


func _update_tactical_guide(delta: float) -> void:
	if str(ai_plan.get("shot_type", "")) != "BANK" or not ai_plan.has("bank_point"):
		tactical_guide.visible = false
		return
	var target_ball := _ball_by_number(int(ai_plan.get("target", -1)))
	if target_ball == null:
		tactical_guide.visible = false
		return
	var bank_point: Vector3 = ai_plan["bank_point"]
	var path := bank_point - target_ball.global_position
	path.y = 0.0
	tactical_guide.visible = true
	tactical_guide.update_guide(target_ball.global_position, path.normalized(), path.length(), delta)


func _ball_by_number(number: int) -> SpectralBall:
	for ball in balls:
		if ball.number == number:
			return ball
	return null


func _begin_ball_in_hand(kitchen_only: bool) -> void:
	ball_in_hand_kitchen_only = kitchen_only
	cue_ball.pocketed = false
	cue_ball.visible = true
	cue_ball.freeze = true
	cue_ball.linear_velocity = Vector3.ZERO
	cue_ball.angular_velocity = Vector3.ZERO
	placement_velocity = Vector3.ZERO
	trajectory_guide.hide_guide()
	cue_visual.visible = false
	var start_x := -2.8 if kitchen_only else clampf(cue_ball.global_position.x, -3.75, 3.75)
	cue_ball.global_position = Vector3(start_x, BALL_Y, clampf(cue_ball.global_position.z, -1.7, 1.7))
	state = GameState.BALL_IN_HAND
	if _is_computer_turn():
		var positions := _active_ball_positions()
		cue_ball.global_position = computer.choose_cue_position(positions, rules.legal_targets(2), pocket_positions, kitchen_only)
		_confirm_ball_in_hand()
	else:
		_update_ui("Ball in hand — move with left stick/WASD, press Strike to place")


func _update_ball_in_hand(delta: float) -> void:
	if _is_computer_turn():
		return
	_update_camera_controls(delta)
	var stick := Vector2(
		Input.get_axis("place_left", "place_right"),
		Input.get_axis("place_up", "place_down")
	)
	if stick.length() > 1.0:
		stick = stick.normalized()
	var forward := _shot_direction()
	var right := Vector3(-forward.z, 0.0, forward.x)
	var desired_velocity := (right * stick.x - forward * stick.y) * 1.75
	placement_velocity = placement_velocity.move_toward(desired_velocity, delta * 7.5)
	var next_position := cue_ball.global_position + placement_velocity * delta
	next_position.x = clampf(next_position.x, -3.88, -2.15 if ball_in_hand_kitchen_only else 3.88)
	next_position.z = clampf(next_position.z, -1.78, 1.78)
	next_position.y = BALL_Y
	if _is_valid_cue_placement(next_position):
		cue_ball.global_position = next_position
	else:
		placement_velocity = Vector3.ZERO
	if Input.is_action_just_pressed("strike"):
		_confirm_ball_in_hand()


func _confirm_ball_in_hand() -> void:
	if not _is_valid_cue_placement(cue_ball.global_position):
		_update_ui("Cue ball overlaps another ball — choose a clear position")
		return
	rules.ball_in_hand = false
	cue_ball.freeze = false
	placement_velocity = Vector3.ZERO
	state = GameState.AIMING
	cue_controls.reset()
	_update_spin_reticle()
	_update_ui("Player %d — ball placed" % current_player)


func _is_valid_cue_placement(candidate: Vector3) -> bool:
	for ball in balls:
		if ball == cue_ball or ball.pocketed:
			continue
		var flat_distance := Vector2(candidate.x, candidate.z).distance_to(Vector2(ball.global_position.x, ball.global_position.z))
		if flat_distance < BALL_RADIUS * 2.15:
			return false
	return true


func _active_ball_positions() -> Dictionary:
	var positions := {}
	for ball in balls:
		if ball.number > 0 and not ball.pocketed:
			positions[ball.number] = ball.global_position
	return positions


func _respot_ball(number: int, spot: Vector3) -> void:
	for ball in balls:
		if ball.number == number:
			ball.pocketed = false
			ball.visible = true
			ball.freeze = true
			ball.global_position = spot
			ball.linear_velocity = Vector3.ZERO
			ball.angular_velocity = Vector3.ZERO
			potted_numbers.erase(number)
			await get_tree().physics_frame
			ball.freeze = false
			return


func _cycle_called_pocket() -> void:
	if rules.legal_targets(current_player) != [8]:
		_update_ui("Called pockets become available after clearing your group")
		return
	called_pocket_index = (called_pocket_index + 1) % pocket_positions.size()
	_update_called_pocket_display()


func _update_called_pocket_display() -> void:
	var calling_eight := state in [GameState.AIMING, GameState.AI_THINKING] and rules.legal_targets(current_player) == [8]
	called_pocket_label.visible = calling_eight
	called_pocket_label.text = "CALLED POCKET: %d  •  B / C TO CHANGE" % (called_pocket_index + 1)
	for index in pocket_markers.size():
		pocket_markers[index].visible = calling_eight and index == called_pocket_index


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
	center.y += 0.11
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
		var distance := lerpf(4.9, 3.55, camera_pitch)
		var height := lerpf(1.35, 4.15, camera_pitch)
		desired = target - direction * distance + Vector3.UP * height
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
	trajectory_guide.hide_guide()
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
	var pocket_index := pocket_positions.find(pocket_position)
	rules.record_pocket(ball.number, pocket_index)
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
	rules.start_match(selected_mode)
	current_player = rules.current_player
	state = GameState.AIMING
	charge = 0.0
	called_pocket_index = 0
	cue_controls.reset()
	_build_balls()
	_update_spin_reticle()
	_update_called_pocket_display()
	_begin_ball_in_hand(true)
	_update_ui("Opening break — place the cue ball behind the head string")


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
			# Keep the leg tops safely below the slate so they cannot z-fight
			# through the felt as square corner artifacts.
			_create_mesh_box(Vector3(0.52, 0.72, 0.52), Vector3(x, 0.36, z), mahogany)
			var foot := MeshInstance3D.new()
			var foot_mesh := SphereMesh.new()
			foot_mesh.radius = 0.34
			foot_mesh.height = 0.68
			foot.mesh = foot_mesh
			foot.material_override = brass
			foot.position = Vector3(x, 0.12, z)
			add_child(foot)

	pocket_positions.assign([
		Vector3(-TABLE_LENGTH * 0.5, BALL_Y, -TABLE_WIDTH * 0.5),
		Vector3(0.0, BALL_Y, -TABLE_WIDTH * 0.5),
		Vector3(TABLE_LENGTH * 0.5, BALL_Y, -TABLE_WIDTH * 0.5),
		Vector3(-TABLE_LENGTH * 0.5, BALL_Y, TABLE_WIDTH * 0.5),
		Vector3(0.0, BALL_Y, TABLE_WIDTH * 0.5),
		Vector3(TABLE_LENGTH * 0.5, BALL_Y, TABLE_WIDTH * 0.5),
	])
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

	var marker := MeshInstance3D.new()
	var marker_mesh := TorusMesh.new()
	marker_mesh.inner_radius = 0.29
	marker_mesh.outer_radius = 0.40
	marker_mesh.rings = 24
	marker_mesh.ring_segments = 10
	marker.mesh = marker_mesh
	var marker_material := _material(Color("64ffe0"), 0.18, 0.45)
	marker_material.emission_enabled = true
	marker_material.emission = Color("3dffd1")
	marker_material.emission_energy_multiplier = 3.0
	marker.material_override = marker_material
	marker.position = pocket_position + Vector3.UP * 0.025
	marker.visible = false
	add_child(marker)
	pocket_markers.append(marker)


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
	ball.impact.connect(_on_ball_impact.bind(number))
	if number == 0:
		ball.contacted_ball.connect(_on_cue_contacted_ball)
	return ball


func _build_camera_and_aiming() -> void:
	camera = Camera3D.new()
	camera.current = true
	camera.fov = 48.0
	camera.position = Vector3(-5.5, 3.2, 4.2)
	add_child(camera)

	aim_guide = AimGuideClass.new() as AimGuide
	add_child(aim_guide)
	tactical_guide = AimGuideClass.new() as AimGuide
	tactical_guide.visible = false
	add_child(tactical_guide)
	trajectory_guide = TrajectoryGuideClass.new() as TrajectoryGuide
	add_child(trajectory_guide)
	trajectory_guide.hide_guide()

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

	var spin_panel := PanelContainer.new()
	spin_panel.custom_minimum_size = Vector2(104.0, 126.0)
	spin_panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	spin_panel.position = Vector2(-138.0, 28.0)
	canvas.add_child(spin_panel)
	var spin_box := Control.new()
	spin_panel.add_child(spin_box)
	var horizontal_line := ColorRect.new()
	horizontal_line.color = Color("526b66")
	horizontal_line.position = Vector2(12.0, 50.0)
	horizontal_line.size = Vector2(80.0, 1.0)
	spin_box.add_child(horizontal_line)
	var vertical_line := ColorRect.new()
	vertical_line.color = Color("526b66")
	vertical_line.position = Vector2(52.0, 10.0)
	vertical_line.size = Vector2(1.0, 80.0)
	spin_box.add_child(vertical_line)
	spin_dot = ColorRect.new()
	spin_dot.color = Color("75ffe1")
	spin_dot.size = Vector2(10.0, 10.0)
	spin_dot.position = Vector2(47.0, 45.0)
	spin_box.add_child(spin_dot)
	spin_label = Label.new()
	spin_label.position = Vector2(8.0, 98.0)
	spin_label.size = Vector2(88.0, 22.0)
	spin_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	spin_label.add_theme_font_size_override("font_size", 11)
	spin_box.add_child(spin_label)

	called_pocket_label = Label.new()
	called_pocket_label.visible = false
	called_pocket_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	called_pocket_label.position = Vector2(-190.0, -112.0)
	called_pocket_label.size = Vector2(380.0, 28.0)
	called_pocket_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	called_pocket_label.add_theme_font_size_override("font_size", 16)
	called_pocket_label.add_theme_color_override("font_color", Color("75ffe1"))
	canvas.add_child(called_pocket_label)

	ai_tactic_label = Label.new()
	ai_tactic_label.visible = false
	ai_tactic_label.set_anchors_preset(Control.PRESET_CENTER_TOP)
	ai_tactic_label.position = Vector2(-150.0, 72.0)
	ai_tactic_label.size = Vector2(300.0, 30.0)
	ai_tactic_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ai_tactic_label.add_theme_font_size_override("font_size", 18)
	ai_tactic_label.add_theme_color_override("font_color", Color("75ffe1"))
	canvas.add_child(ai_tactic_label)

	tip_label = Label.new()
	tip_label.text = "Place: Left stick / WASD     Camera: Right stick / A D / mouse     English: D-pad / arrows\nShoot: Hold RT, pull right stick back, push forward     Guide: LB / G     Tactical: Y / T     Replay: X / R"
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

	menu_panel = PanelContainer.new()
	menu_panel.custom_minimum_size = Vector2(460.0, 452.0)
	menu_panel.set_anchors_preset(Control.PRESET_CENTER)
	menu_panel.position = Vector2(-230.0, -226.0)
	canvas.add_child(menu_panel)
	var menu_margin := MarginContainer.new()
	menu_margin.add_theme_constant_override("margin_left", 34)
	menu_margin.add_theme_constant_override("margin_top", 28)
	menu_margin.add_theme_constant_override("margin_right", 34)
	menu_margin.add_theme_constant_override("margin_bottom", 28)
	menu_panel.add_child(menu_margin)
	var menu_layout := VBoxContainer.new()
	menu_layout.add_theme_constant_override("separation", 12)
	menu_margin.add_child(menu_layout)
	var menu_title := Label.new()
	menu_title.text = "CHOOSE YOUR TABLE"
	menu_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	menu_title.add_theme_font_size_override("font_size", 25)
	menu_title.add_theme_color_override("font_color", Color("d6b875"))
	menu_layout.add_child(menu_title)
	var menu_copy := Label.new()
	menu_copy.text = "The manor is listening. How will you play?"
	menu_copy.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	menu_copy.add_theme_color_override("font_color", Color("a8c9bf"))
	menu_layout.add_child(menu_copy)
	var practice_button := Button.new()
	practice_button.name = "PracticeButton"
	practice_button.text = "PRACTICE ALONE"
	practice_button.pressed.connect(_start_match.bind(EightBallRules.Mode.PRACTICE))
	menu_layout.add_child(practice_button)
	var cpu_button := Button.new()
	cpu_button.name = "ComputerButton"
	cpu_button.text = "VERSUS THE MANOR"
	cpu_button.pressed.connect(_start_match.bind(EightBallRules.Mode.VS_CPU))
	menu_layout.add_child(cpu_button)
	var local_button := Button.new()
	local_button.name = "LocalButton"
	local_button.text = "LOCAL TWO PLAYER"
	local_button.pressed.connect(_start_match.bind(EightBallRules.Mode.LOCAL_TWO_PLAYER))
	menu_layout.add_child(local_button)
	var difficulty_label := Label.new()
	difficulty_label.text = "Computer difficulty"
	difficulty_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	menu_layout.add_child(difficulty_label)
	difficulty_picker = OptionButton.new()
	difficulty_picker.add_item("Easy — wandering spirit", BilliardsAI.Difficulty.EASY)
	difficulty_picker.add_item("Medium — manor resident", BilliardsAI.Difficulty.MEDIUM)
	difficulty_picker.add_item("Hard — table revenant", BilliardsAI.Difficulty.HARD)
	difficulty_picker.select(1)
	menu_layout.add_child(difficulty_picker)
	guide_checkbox = CheckButton.new()
	guide_checkbox.text = "Solid light-blue shot guide"
	guide_checkbox.button_pressed = shot_guide_enabled
	guide_checkbox.toggled.connect(_on_guide_toggled)
	menu_layout.add_child(guide_checkbox)
	practice_button.call_deferred("grab_focus")

	match_over_panel = PanelContainer.new()
	match_over_panel.visible = false
	match_over_panel.custom_minimum_size = Vector2(440.0, 260.0)
	match_over_panel.set_anchors_preset(Control.PRESET_CENTER)
	match_over_panel.position = Vector2(-220.0, -130.0)
	canvas.add_child(match_over_panel)
	var over_layout := VBoxContainer.new()
	over_layout.alignment = BoxContainer.ALIGNMENT_CENTER
	over_layout.add_theme_constant_override("separation", 18)
	match_over_panel.add_child(over_layout)
	match_over_label = Label.new()
	match_over_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	match_over_label.add_theme_font_size_override("font_size", 25)
	match_over_label.add_theme_color_override("font_color", Color("d6b875"))
	over_layout.add_child(match_over_label)
	var rematch_button := Button.new()
	rematch_button.text = "REMATCH"
	rematch_button.pressed.connect(_reset_rack)
	over_layout.add_child(rematch_button)
	var menu_button := Button.new()
	menu_button.text = "CHANGE MODE"
	menu_button.pressed.connect(_show_mode_menu)
	over_layout.add_child(menu_button)


func _update_ui(message: String) -> void:
	if status_label == null:
		return
	var actor := "THE MANOR" if _is_computer_turn() else "PLAYER %d" % current_player
	player_label.text = "%s  •  %s" % [actor, rules.group_name(current_player)]
	status_label.text = message


func _update_spin_reticle() -> void:
	if spin_dot == null:
		return
	spin_dot.position = Vector2(47.0 + cue_controls.spin.x * 36.0, 45.0 - cue_controls.spin.y * 36.0)
	spin_label.text = cue_controls.strike_label()


func _show_mode_menu() -> void:
	state = GameState.MENU
	menu_panel.visible = true
	match_over_panel.visible = false
	aim_guide.visible = false
	trajectory_guide.hide_guide()
	cue_visual.visible = false
	called_pocket_label.visible = false
	ai_tactic_label.visible = false
	tactical_guide.visible = false
	camera.global_position = Vector3(0.0, 7.2, 7.4)
	camera.look_at(Vector3(0.0, BED_Y, 0.0), Vector3.UP)
	_update_ui("Choose a game mode")


func _start_match(mode: EightBallRules.Mode) -> void:
	selected_mode = mode
	selected_difficulty = difficulty_picker.get_selected_id() as BilliardsAI.Difficulty
	computer.configure(selected_difficulty)
	menu_panel.visible = false
	match_over_panel.visible = false
	_reset_rack()
	match mode:
		EightBallRules.Mode.PRACTICE:
			_update_ui("Practice table — place the cue ball for the break")
		EightBallRules.Mode.VS_CPU:
			_update_ui("Place the cue ball, then break against the manor")
		EightBallRules.Mode.LOCAL_TWO_PLAYER:
			_update_ui("Local match — Player 1 places the cue ball to break")


func _show_match_over(winning_player: int, message: String) -> void:
	state = GameState.MATCH_OVER
	aim_guide.visible = false
	trajectory_guide.hide_guide()
	cue_visual.visible = false
	match_over_label.text = message if selected_mode != EightBallRules.Mode.VS_CPU else ("YOU WIN" if winning_player == 1 else "THE MANOR WINS")
	match_over_panel.visible = true
	ai_tactic_label.visible = false
	tactical_guide.visible = false
	_update_ui(message)


func _on_guide_toggled(enabled: bool) -> void:
	shot_guide_enabled = enabled
	if not enabled and trajectory_guide != null:
		trajectory_guide.hide_guide()


func _build_audio() -> void:
	resin_stream = _make_impact_stream(0.072, 1650.0, 0.34)
	cushion_stream = _make_impact_stream(0.11, 230.0, 0.52)


func _on_ball_impact(hit_position: Vector3, intensity: float, cushion: bool, ball_number: int) -> void:
	if cushion and state == GameState.ROLLING:
		rules.record_rail_contact(ball_number)
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


func _on_cue_contacted_ball(number: int) -> void:
	if state == GameState.ROLLING:
		rules.record_first_contact(number)


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
	_add_key_action("ui_accept", KEY_ENTER)
	_add_joy_button_action("ui_accept", JOY_BUTTON_A)
	_add_key_action("aim_left", KEY_A)
	_add_key_action("aim_right", KEY_D)
	_add_key_action("aim_up", KEY_W)
	_add_key_action("aim_down", KEY_S)
	_add_key_action("place_up", KEY_W)
	_add_key_action("place_down", KEY_S)
	_add_key_action("place_left", KEY_A)
	_add_key_action("place_right", KEY_D)
	_add_key_action("spin_left", KEY_LEFT)
	_add_key_action("spin_right", KEY_RIGHT)
	_add_key_action("spin_up", KEY_UP)
	_add_key_action("spin_down", KEY_DOWN)
	_add_key_action("charge_shot", KEY_SPACE)
	_add_key_action("strike", KEY_ENTER)
	_add_key_action("toggle_view", KEY_T)
	_add_key_action("replay", KEY_R)
	_add_key_action("reset_rack", KEY_ESCAPE)
	_add_key_action("call_pocket", KEY_C)
	_add_key_action("toggle_guide", KEY_G)
	_add_mouse_action("charge_shot", MOUSE_BUTTON_RIGHT)
	_add_mouse_action("strike", MOUSE_BUTTON_LEFT)
	_add_joy_axis_action("place_left", JOY_AXIS_LEFT_X, -1.0)
	_add_joy_axis_action("place_right", JOY_AXIS_LEFT_X, 1.0)
	_add_joy_axis_action("place_up", JOY_AXIS_LEFT_Y, -1.0)
	_add_joy_axis_action("place_down", JOY_AXIS_LEFT_Y, 1.0)
	_add_joy_axis_action("camera_left", JOY_AXIS_RIGHT_X, -1.0)
	_add_joy_axis_action("camera_right", JOY_AXIS_RIGHT_X, 1.0)
	_add_joy_axis_action("camera_up", JOY_AXIS_RIGHT_Y, -1.0)
	_add_joy_axis_action("camera_down", JOY_AXIS_RIGHT_Y, 1.0)
	_add_joy_axis_action("charge_shot", JOY_AXIS_TRIGGER_RIGHT, 1.0)
	_add_joy_button_action("spin_left", JOY_BUTTON_DPAD_LEFT)
	_add_joy_button_action("spin_right", JOY_BUTTON_DPAD_RIGHT)
	_add_joy_button_action("spin_up", JOY_BUTTON_DPAD_UP)
	_add_joy_button_action("spin_down", JOY_BUTTON_DPAD_DOWN)
	_add_joy_button_action("strike", JOY_BUTTON_RIGHT_SHOULDER)
	_add_joy_button_action("toggle_guide", JOY_BUTTON_LEFT_SHOULDER)
	_add_joy_button_action("toggle_view", JOY_BUTTON_Y)
	_add_joy_button_action("replay", JOY_BUTTON_X)
	_add_joy_button_action("reset_rack", JOY_BUTTON_BACK)
	_add_joy_button_action("call_pocket", JOY_BUTTON_B)


func _add_key_action(action: StringName, key: Key) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.18)
	var event := InputEventKey.new()
	event.physical_keycode = key
	InputMap.action_add_event(action, event)


func _add_mouse_action(action: StringName, button: MouseButton) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.18)
	var event := InputEventMouseButton.new()
	event.button_index = button
	InputMap.action_add_event(action, event)


func _add_joy_axis_action(action: StringName, axis: JoyAxis, value: float) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.18)
	var event := InputEventJoypadMotion.new()
	event.axis = axis
	event.axis_value = value
	InputMap.action_add_event(action, event)


func _add_joy_button_action(action: StringName, button: JoyButton) -> void:
	var event := InputEventJoypadButton.new()
	event.button_index = button
	InputMap.action_add_event(action, event)
