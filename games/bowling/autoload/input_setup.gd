extends Node
## Registers the input map in code so it's readable and diffable.
## Gamepad first (Xbox layout), keyboard + mouse as the fallback.

const DEADZONE := 0.2


func _enter_tree() -> void:
	# the approach: D-pad or A / D. (The left stick is the draw on the pad.)
	_action("move_left", [_key(KEY_A), _key(KEY_LEFT), _button(JOY_BUTTON_DPAD_LEFT)])
	_action("move_right", [_key(KEY_D), _key(KEY_RIGHT), _button(JOY_BUTTON_DPAD_RIGHT)])
	# after release the left stick steers
	_action("steer_left", [_key(KEY_A), _key(KEY_LEFT), _axis(JOY_AXIS_LEFT_X, -1.0)])
	_action("steer_right", [_key(KEY_D), _key(KEY_RIGHT), _axis(JOY_AXIS_LEFT_X, 1.0)])
	_action("aim_left", [_key(KEY_J), _axis(JOY_AXIS_RIGHT_X, -1.0)])
	_action("aim_right", [_key(KEY_L), _axis(JOY_AXIS_RIGHT_X, 1.0)])
	# pull back with the LEFT stick (read raw in game.gd), the mouse, or S / W;
	# release with the right trigger, a left click (handled in game.gd), or Space.
	# The trigger needs a firm squeeze so a resting finger can't let go early.
	_action("release", [_axis(JOY_AXIS_TRIGGER_RIGHT, 1.0), _key(KEY_SPACE)], 0.55)
	_action("draw_more", [_key(KEY_S)])
	_action("draw_less", [_key(KEY_W)])
	_action("replay", [_button(JOY_BUTTON_X), _key(KEY_X)])
	_action("spin_left", [_button(JOY_BUTTON_LEFT_SHOULDER), _key(KEY_Q)])
	_action("spin_right", [_button(JOY_BUTTON_RIGHT_SHOULDER), _key(KEY_E)])
	_action("confirm", [_button(JOY_BUTTON_A), _key(KEY_ENTER)])
	_action("next_ball", [_button(JOY_BUTTON_Y), _key(KEY_B)])
	_action("restart", [_button(JOY_BUTTON_START), _key(KEY_R)])
	_action("mute", [_button(JOY_BUTTON_BACK), _key(KEY_M)])
	_action("pin_style", [_button(JOY_BUTTON_DPAD_UP), _key(KEY_P)])
	_action("alley", [_button(JOY_BUTTON_DPAD_DOWN), _key(KEY_V)])


func _action(name: StringName, events: Array, deadzone := DEADZONE) -> void:
	if not InputMap.has_action(name):
		InputMap.add_action(name, deadzone)
	for e in events:
		InputMap.action_add_event(name, e)


func _key(code: Key) -> InputEventKey:
	var e := InputEventKey.new()
	e.physical_keycode = code
	return e


func _axis(axis: JoyAxis, value: float) -> InputEventJoypadMotion:
	var e := InputEventJoypadMotion.new()
	e.axis = axis
	e.axis_value = value
	return e


func _button(b: JoyButton) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new()
	e.button_index = b
	return e


func _mouse(b: MouseButton) -> InputEventMouseButton:
	var e := InputEventMouseButton.new()
	e.button_index = b
	return e
