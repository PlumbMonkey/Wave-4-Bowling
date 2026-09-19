extends SceneTree

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var game := (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame

	var solid := game.find_child("Ball01", true, false)
	var stripe := game.find_child("Ball09", true, false)
	var eight := game.find_child("Ball08", true, false)
	_assert(solid != null and solid.find_child("StripeBand", false, false) == null, "Balls 1–7 use solid shells")
	_assert(stripe != null and stripe.find_child("StripeBand", false, false) != null, "Balls 9–15 have a distinct equatorial stripe")
	_assert(eight != null and eight.find_child("StripeBand", false, false) == null, "The eight ball remains a solid shell")
	var number_label := solid.find_child("SurfaceNumber", false, false) as Label3D
	var medallion := solid.find_child("NumberMedallion", false, false) as MeshInstance3D
	_assert(number_label != null and medallion != null, "Ball number is mounted on a surface medallion")
	_assert(number_label.position.y - game.BALL_RADIUS < 0.002, "Ball number sits flush with the sphere")

	var expected_cue_parts := ["Butt", "Inlay", "LeatherWrap", "MapleShaft", "Ferrule", "ChalkedTip"]
	for part in expected_cue_parts:
		_assert(game.cue_visual.find_child(part, false, false) != null, "Cue includes %s" % part)

	var rim := game.find_child("RecessedPocketRim", true, false) as MeshInstance3D
	var drop := game.find_child("PocketDrop", true, false) as MeshInstance3D
	_assert(rim != null and rim.global_position.y <= game.BED_Y, "Pocket rim is recessed to felt level")
	_assert(drop != null and drop.global_position.y < game.BED_Y, "Pocket drop sits below the playing surface")
	_assert(is_equal_approx(game.TABLE_LENGTH / game.TABLE_WIDTH, 2.0), "Playing surface keeps regulation 2:1 proportions")
	_assert(is_equal_approx(game.BALL_RADIUS * 2.0, 0.225), "Ball scale matches the table proportions")

	game.queue_free()
	await process_frame
	if failures == 0:
		print("VISUAL ASSETS TEST PASSED")
	quit(1 if failures > 0 else 0)


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
