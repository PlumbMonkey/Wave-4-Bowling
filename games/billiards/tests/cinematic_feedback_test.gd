extends SceneTree

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/main.tscn")
	var game := packed_scene.instantiate()
	root.add_child(game)
	await process_frame

	_assert(game.soundscape != null, "Dynamic table soundscape is created")
	_assert(game.soundscape.impact_players.size() == 12, "Impact audio uses a reusable player pool")
	_assert(game.soundscape.impact_volume_db(3.0, false) > game.soundscape.impact_volume_db(0.2, false), "Hard impacts are louder than soft impacts")
	_assert(game.soundscape.impact_pitch(3.0, false) > game.soundscape.impact_pitch(0.2, false), "Hard impacts are sharper than soft impacts")
	_assert(game.soundscape.impact_pitch(2.0, true) < game.soundscape.impact_pitch(2.0, false), "Cushion impacts remain lower than resin impacts")
	_assert(game.soundscape.roll_level(8.0) > game.soundscape.roll_level(0.2), "Cloth roll grows with combined ball speed")

	game._start_match(0)
	game._confirm_ball_in_hand()
	var cue_id: int = game.cue_ball.get_instance_id()
	var saved_transform: Transform3D = game.cue_ball.global_transform
	game.cue_ball.linear_velocity = Vector3(0.4, 0.0, 0.1)
	var saved_velocity: Vector3 = game.cue_ball.linear_velocity
	var replay_transform := saved_transform
	replay_transform.origin += Vector3(1.0, 0.0, 0.0)
	var frames: Array[Dictionary] = [
		{cue_id: {"transform": replay_transform, "visible": true}},
		{cue_id: {"transform": saved_transform, "visible": true}},
	]
	game._start_replay(frames, false, cue_id, Vector3.ZERO)
	_assert(game.state == game.GameState.REPLAY, "Replay enters its isolated playback state")
	_assert(game.soundscape.replay_mix_active, "Replay enables the cinematic audio mix")
	_assert(game._find_replay_focus(frames[0]).is_equal_approx(replay_transform.origin), "Replay follows the explicitly pocketed ball")
	game._apply_replay_frame(frames[0])
	_assert(game.cue_ball.global_position.is_equal_approx(replay_transform.origin), "Replay can present a recorded transform")
	game._finish_replay()
	_assert(game.state == game.GameState.AIMING, "Manual replay returns to its exact prior state")
	_assert(game.cue_ball.global_transform.is_equal_approx(saved_transform), "Replay restores the live ball transform")
	_assert(game.cue_ball.linear_velocity.is_equal_approx(saved_velocity), "Replay restores live velocity")
	_assert(not game.soundscape.replay_mix_active, "Replay restores the live audio mix")
	_assert(is_equal_approx(game.camera.fov, 48.0), "Replay restores the gameplay field of view")

	game.queue_free()
	await process_frame
	if failures == 0:
		print("CINEMATIC FEEDBACK TEST PASSED")
	quit(1 if failures > 0 else 0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
