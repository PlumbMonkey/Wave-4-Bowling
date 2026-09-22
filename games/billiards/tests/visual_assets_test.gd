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
	var number_label := solid.find_child("SurfaceNumber", true, false) as Label
	var medallion := solid.find_child("NumberMedallion", false, false) as MeshInstance3D
	var opposite_medallion := solid.find_child("NumberMedallionOpposite", false, false) as MeshInstance3D
	_assert(number_label != null and medallion != null, "Ball number is rendered into a surface medallion")
	_assert(opposite_medallion != null, "Ball number is marked on both opposing faces")
	var medallion_faces := medallion.mesh.get_faces()
	_assert(medallion.mesh.get_aabb().size.y > 0.004, "Ball number medallion follows the sphere curvature")
	_assert(absf(medallion_faces[0].length() - game.BALL_RADIUS) < 0.001, "Ball number marking sits on the sphere surface")

	var production_table: Node = game.find_child("ProductionTable", true, false)
	_assert(production_table != null, "Blender production table is active")
	for detail in ["LongRailSight*", "LongApronInset_Front_0", "Leg0_Filigree", "Pocket0_NetV0", "Pocket0_WoodSurround", "Pocket0_BrassSurround"]:
		_assert(production_table.find_child(detail, true, false) != null, "Production table includes %s" % detail)
	var production_slate := production_table.find_child("Table_Slate", true, false) as MeshInstance3D
	var slate_material := production_slate.get_active_material(0) as StandardMaterial3D
	_assert(slate_material.albedo_texture != null, "Production cloth uses its original felt texture")
	_assert(production_slate.mesh.get_faces().size() > 36, "Production cloth mesh includes cut pocket openings")
	var production_cue: Node = game.cue_visual.find_child("ProductionCue", false, false)
	_assert(production_cue != null, "Blender production cue is active")
	var expected_cue_parts := ["Cue_Butt", "Cue_Inlay", "Cue_LeatherWrap", "Cue_MapleShaft", "Cue_Ferrule", "Cue_ChalkedTip"]
	for part in expected_cue_parts:
		_assert(game.cue_visual.find_child(part, true, false) != null, "Cue includes %s" % part)

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
