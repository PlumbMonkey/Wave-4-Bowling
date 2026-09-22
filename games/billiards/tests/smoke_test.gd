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
	game._confirm_ball_in_hand()
	await physics_frame
	_assert(game.replay_buffer.frames.size() > 0, "Replay buffer captures physics state")
	game._strike(0.5)
	await physics_frame
	_assert(game.cue_ball.linear_velocity.length() > 0.05, "Cue strike applies a physical impulse")
	var simulated_speed: float = game.MAX_SHOT_IMPULSE / game.cue_ball.mass
	for frame in 480:
		simulated_speed = game.cue_ball.rolling_speed_after_step(simulated_speed, 1.0 / 60.0)
		simulated_speed *= exp(-game.cue_ball.linear_damp / 60.0)
	_assert(simulated_speed < game.STOP_SPEED, "A maximum-power ball settles within eight simulated seconds")
	for ball in game.balls:
		if ball != game.cue_ball:
			ball.pocketed = true
			ball.freeze = true
			ball.visible = false
	game.cue_ball.global_position = Vector3(-2.8, game.BALL_Y, 0.0)
	game.cue_ball.linear_velocity = Vector3.ZERO
	game.cue_ball.angular_velocity = Vector3.ZERO
	game.state = game.GameState.AIMING
	game._strike(1.0)
	var settling_frame_count := 0
	while settling_frame_count < 480 and (game.cue_ball.linear_velocity.length() > game.STOP_SPEED or game.cue_ball.angular_velocity.length() > 0.12):
		await physics_frame
		settling_frame_count += 1
	_assert(settling_frame_count < 480, "An actual maximum-power shot settles within eight seconds")
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
