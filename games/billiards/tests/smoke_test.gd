extends SceneTree


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/main.tscn")
	_assert(packed_scene != null, "Main scene loads")
	var game := packed_scene.instantiate()
	root.add_child(game)
	await process_frame
	await physics_frame
	_assert(game.balls.size() == 16, "A regulation rack contains 16 balls")
	_assert(game.cue_ball != null, "Cue ball exists")
	game._start_match(EightBallRules.Mode.PRACTICE)
	await physics_frame
	_assert(game.replay_buffer.frames.size() > 0, "Replay buffer captures physics state")
	game._strike(0.5)
	await physics_frame
	_assert(game.cue_ball.linear_velocity.length() > 0.05, "Cue strike applies a physical impulse")
	game.queue_free()
	await process_frame
	print("SMOKE TEST PASSED")
	quit(0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	quit(1)
