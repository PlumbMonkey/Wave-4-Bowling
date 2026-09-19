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
