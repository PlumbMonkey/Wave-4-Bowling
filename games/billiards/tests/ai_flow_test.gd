extends SceneTree

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene: PackedScene = load("res://scenes/main.tscn")
	var game := packed_scene.instantiate()
	root.add_child(game)
	await process_frame
	game._start_match(EightBallRules.Mode.VS_CPU)
	game.rules.current_player = 2
	game.current_player = 2
	game.state = game.GameState.AIMING
	for frame in 95:
		await physics_frame
	_assert(game.ai_plan.has("direction"), "Computer creates a shot plan")
	_assert(int(game.ai_plan.get("target", -1)) > 0, "Computer selects a legal object ball")
	_assert(game.state == game.GameState.ROLLING, "Computer completes its aiming animation and strikes")
	_assert(game.replay_buffer.shot_start_index > 0, "Computer shots use the replay pipeline")
	game.queue_free()
	await process_frame
	if failures == 0:
		print("AI FLOW TEST PASSED")
	quit(1 if failures > 0 else 0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
