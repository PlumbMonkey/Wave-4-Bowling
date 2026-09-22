extends SceneTree

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/main.tscn")
	var game := packed_scene.instantiate()
	root.add_child(game)
	await process_frame

	_assert(InputMap.has_action("camera_right"), "Right-stick camera action is registered")
	_assert(InputMap.has_action("toggle_guide"), "Shot-guide toggle action is registered")
	_assert(_has_joy_axis("camera_right", JOY_AXIS_RIGHT_X), "Right stick controls camera orbit")
	_assert(_has_joy_axis("place_right", JOY_AXIS_LEFT_X), "Left stick controls cue-ball placement")
	_assert(_has_joy_button("toggle_guide", JOY_BUTTON_LEFT_SHOULDER), "Left bumper toggles the shot guide")

	game._start_match(0)
	var starting_position: Vector3 = game.cue_ball.global_position
	Input.action_press("place_right", 0.65)
	game._update_ball_in_hand(0.1)
	Input.action_release("place_right")
	_assert(game.cue_ball.global_position.distance_to(starting_position) > 0.001, "Cue ball moves smoothly from left-stick input")
	_assert(game.placement_velocity.length() > 0.0, "Cue-ball placement uses smoothed velocity")

	var starting_yaw: float = game.camera_yaw
	Input.action_press("camera_right", 0.8)
	game._update_camera_controls(0.1)
	Input.action_release("camera_right")
	_assert(not is_equal_approx(game.camera_yaw, starting_yaw), "Right stick rotates the camera")

	game.state = game.GameState.ROLLING
	starting_yaw = game.camera_yaw
	Input.action_press("camera_right", 0.8)
	game._physics_process(0.1)
	Input.action_release("camera_right")
	_assert(not is_equal_approx(game.camera_yaw, starting_yaw), "Camera remains controllable while balls are rolling")

	game.state = game.GameState.AIMING
	game._process_controller_stroke(1.0, 0.72, 0.016)
	_assert(game.stroke_armed and game.charge > 0.65, "Right trigger arms a pull-back stroke")
	game._process_controller_stroke(1.0, -0.78, 0.016)
	_assert(game.state == game.GameState.ROLLING, "Forward stick motion releases the cue stroke")
	_assert(game.stroke_needs_trigger_release, "A completed stroke requires a fresh trigger press")
	game._process_controller_stroke(0.0, 0.0, 0.016)
	_assert(not game.stroke_needs_trigger_release, "Releasing the trigger rearms the stroke control")

	game.state = game.GameState.AIMING
	game._update_human_trajectory(game._shot_direction())
	var guide_beam: MeshInstance3D = game.trajectory_guide.beams[0]
	var guide_mesh := guide_beam.mesh as CylinderMesh
	var guide_material := guide_beam.material_override as StandardMaterial3D
	_assert(is_equal_approx(guide_beam.global_position.y, game.BED_Y + 0.012), "Trajectory guide rests on the cloth surface")
	_assert(guide_mesh.top_radius >= 0.024, "Trajectory guide is wide enough to read clearly")
	_assert(guide_material.albedo_color.a <= 0.5, "Trajectory guide is translucent")

	var target_ball = game._ball_by_number(1)
	for ball in game.balls:
		if ball != game.cue_ball and ball != target_ball:
			ball.pocketed = true
	game.cue_ball.global_position = Vector3(-2.0, game.BALL_Y, 0.0)
	target_ball.global_position = Vector3(0.0, game.BALL_Y, 0.0)
	var trajectory_exclusions: Array[RID] = [game.cue_ball.get_rid()]
	var trajectory_hit: Dictionary = game._trajectory_hit(game.cue_ball.global_position, Vector3.RIGHT, trajectory_exclusions, 6.0)
	var expected_travel: float = 2.0 - game.BALL_RADIUS * 2.0
	var actual_travel: float = game.cue_ball.global_position.distance_to(Vector3(trajectory_hit["endpoint"].x, game.BALL_Y, trajectory_hit["endpoint"].z))
	_assert(trajectory_hit["collider"] == target_ball, "Trajectory guide identifies the first physical ball contact")
	_assert(absf(actual_travel - expected_travel) < 0.002, "Trajectory guide accounts for both ball radii")

	game.guide_checkbox.button_pressed = false
	_assert(not game.shot_guide_enabled, "Menu option disables the solid trajectory guide")
	game.guide_checkbox.button_pressed = true
	_assert(game.shot_guide_enabled, "Menu option enables the solid trajectory guide")

	game.queue_free()
	await process_frame
	if failures == 0:
		print("CONTROL SCHEME TEST PASSED")
	quit(1 if failures > 0 else 0)


func _has_joy_axis(action: StringName, axis: JoyAxis) -> bool:
	for event in InputMap.action_get_events(action):
		if event is InputEventJoypadMotion and event.axis == axis:
			return true
	return false


func _has_joy_button(action: StringName, button: JoyButton) -> bool:
	for event in InputMap.action_get_events(action):
		if event is InputEventJoypadButton and event.button_index == button:
			return true
	return false


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
