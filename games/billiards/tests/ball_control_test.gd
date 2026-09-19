extends SceneTree

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/main.tscn")
	var game := packed_scene.instantiate()
	root.add_child(game)
	await process_frame
	game._start_match(EightBallRules.Mode.LOCAL_TWO_PLAYER)
	game._begin_ball_in_hand(false)
	_assert(game.state == game.GameState.BALL_IN_HAND, "Human foul enters ball-in-hand placement")
	_assert(game.cue_ball.freeze, "Cue ball is frozen while being positioned")
	game.cue_ball.global_position = Vector3(-3.2, game.BALL_Y, 1.5)
	game._confirm_ball_in_hand()
	_assert(game.state == game.GameState.AIMING, "A valid placement returns to aiming")
	_assert(not game.cue_ball.freeze, "Placed cue ball returns to physics")

	game.selected_mode = EightBallRules.Mode.VS_CPU
	game.rules.mode = EightBallRules.Mode.VS_CPU
	game.rules.current_player = 2
	game.current_player = 2
	game._begin_ball_in_hand(false)
	_assert(game.state == game.GameState.AIMING, "Computer chooses and confirms ball placement")
	_assert(game._is_valid_cue_placement(game.cue_ball.global_position), "Computer placement does not overlap another ball")
	game.queue_free()
	await process_frame
	if failures == 0:
		print("BALL CONTROL TEST PASSED")
	quit(1 if failures > 0 else 0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
