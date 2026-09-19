extends SceneTree
## Screenshots of every menu (run windowed, not headless):
##   godot --path . --script res://tests/menu_shots.gd -- --out=DIR [--alley=crypt]

var out := "user://menu_shots"


func _initialize() -> void:
	# a scratch settings file, so the player's own (best score, bowlers...) are never touched
	BowlingSettings.path = "user://test_settings.cfg"
	DirAccess.remove_absolute(BowlingSettings.path)
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
	var saved := BowlingSettings.load_all()
	BowlingSettings.save_value("players", 2)
	BowlingSettings.save_value("names", ["WRAITH", "BANSHEE", "", ""])
	var game: Node = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await _snap("1_title", 90)
	game.menus._open_settings("title")
	await _snap("2_settings")
	game.menus._open_sub("bowlers", "title")
	await _snap("2b_bowlers")
	game.start_from_title()
	await _snap("3_aim", 40)
	game.menus.open("pause")
	await _snap("4_pause")
	game.menus.close()
	for k in [["strike", "STRIKE!"], ["spare", "SPARE!"], ["gutter", "GUTTER"], ["miss", "MISS"]]:
		game.hud.callout(k[0], k[1])
		await _snap("5_callout_" + k[0], 40)
		for i in 120:
			await process_frame
	for r in [10, 7, 3, 9, 0, 10, 0, 8, 8, 2, 0, 6, 10, 10, 10, 8, 1]:
		game.players[0].card.roll(r)
	for r in [9, 1, 10, 7, 2, 10, 10, 6, 3, 8, 1, 9, 0, 7, 3, 10, 9, 0]:
		game.players[1].card.roll(r)
	game.cur_player = 1
	game._update_board()
	await _snap("5b_board", 20)
	game.menus.show_over(game.players, 150)
	await _snap("6_over")
	for k in ["players", "names"]:
		BowlingSettings.save_value(k, saved[k])
	quit()
