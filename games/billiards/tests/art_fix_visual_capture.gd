extends SceneTree


func _init() -> void:
	call_deferred("_capture")


func _capture() -> void:
	var game := (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	game._start_match(0)
	game._confirm_ball_in_hand()
	game.camera_yaw = 0.08
	game.camera_pitch = 0.62
	for frame in 5:
		await process_frame
	var output := "user://spectral_manor_art_fix.png"
	var error := root.get_texture().get_image().save_png(output)
	print("VISUAL_CAPTURE=", ProjectSettings.globalize_path(output), " ERROR=", error)
	game.queue_free()
	await process_frame
	quit(0 if error == OK else 1)
