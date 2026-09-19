extends SceneTree

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/main.tscn")
	var game := packed_scene.instantiate()
	root.add_child(game)
	await process_frame
	var practice_button := game.find_child("PracticeButton", true, false) as Button
	_assert(practice_button != null, "Practice menu button is available")
	practice_button.grab_focus()
	var press := InputEventJoypadButton.new()
	press.button_index = JOY_BUTTON_A
	press.pressed = true
	Input.parse_input_event(press)
	await process_frame
	var release := InputEventJoypadButton.new()
	release.button_index = JOY_BUTTON_A
	release.pressed = false
	Input.parse_input_event(release)
	await process_frame
	_assert(not game.menu_panel.visible, "Controller A activates the focused menu option")
	_assert(game.state == game.GameState.BALL_IN_HAND, "Practice mode starts in cue-ball placement")
	game.queue_free()
	await process_frame
	if failures == 0:
		print("MENU INPUT TEST PASSED")
	quit(1 if failures > 0 else 0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
