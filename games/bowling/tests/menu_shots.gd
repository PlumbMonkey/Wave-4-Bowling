extends SceneTree
## Screenshots of every menu (run windowed, not headless):
##   godot --path . --script res://tests/menu_shots.gd -- --out=DIR [--alley=crypt]

var out := "user://menu_shots"


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	DirAccess.make_dir_recursive_absolute(out)
	_run.call_deferred()


func _snap(tag: String, frames := 30) -> void:
	for i in frames:
		await process_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(out.path_join(tag + ".png"))
	print("shot ", tag)


func _run() -> void:
	var game: Node = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await _snap("1_title", 90)
	game.menus._open_settings("title")
	await _snap("2_settings")
	game.start_from_title()
	await _snap("3_aim", 40)
	game.menus.open("pause")
	await _snap("4_pause")
	game.menus.close()
	game.hud.callout("strike", "STRIKE!")
	await _snap("5_callout", 12)
	var c := ScoreCard.new()
	for r in [10, 7, 3, 9, 0, 10, 0, 8, 8, 2, 0, 6, 10, 10, 10, 8, 1]:
		c.roll(r)
	game.menus.show_over(c, 150)
	await _snap("6_over")
	quit()
