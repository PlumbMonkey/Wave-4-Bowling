extends SceneTree
## How often a good pocket throw strikes across random oil (a tuning tool):
##   godot --headless --path . --script res://tests/strike_rate.gd

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var rng := RandomNumberGenerator.new()
	var err := RandomNumberGenerator.new()
	err.seed = 5
	var strikes := 0
	var n := 0
	var line := []
	for g in 8:
		rng.seed = 100 + g
		BowlingBall.pattern = OilPattern.random(rng)
		var row := ""
		for b in 4:
			BowlingBall.pattern.jitter = rng.randf_range(0.93, 1.07)
			var x := BowlingSpec.board_x(10) + err.randf_range(-0.03, 0.03)
			var aim := deg_to_rad(0.3 + err.randf_range(-0.25, 0.25))
			var power := 0.72 + err.randf_range(-0.05, 0.05)
			var spin := -0.8 + err.randf_range(-0.15, 0.15)
			var down := await _throw(x, aim, power, spin)
			n += 1
			strikes += int(down == 10)
			row += "%2d " % down
			var sp := lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, power)
			BowlingBall.pattern.wear_path(BowlingBall.predict(x, aim, sp, spin)[0])
		line.append("game %d  oil %2d ft  skew %+.2f : %s" % [g + 1, BowlingBall.pattern.feet(), BowlingBall.pattern.skew, row])
	for l in line:
		print(l)
	print("STRIKES %d / %d = %d%%" % [strikes, n, roundi(100.0 * strikes / n)])
	quit()

func _throw(x: float, aim: float, power: float, spin: float) -> int:
	var world := Node3D.new()
	root.add_child(world)
	world.add_child(Alley.new())
	var setter := Pinsetter.new()
	world.add_child(setter)
	var ball := BowlingBall.new()
	world.add_child(ball)
	for i in 30:
		await physics_frame
	ball.launch(x, aim, lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, power), spin)
	var t := 0.0
	var arrive := -1.0
	while t < 10.0:
		await physics_frame
		t += 1.0 / 120.0
		if arrive < 0.0 and ball.global_position.z < -BowlingSpec.LANE_LEN + 0.3:
			arrive = t
		if arrive > 0.0 and t - arrive > 1.0 and setter.tick_settle(1.0 / 120.0):
			break
		if arrive < 0.0 and t > 6.0:
			break
	var down := 10 - setter.standing().size()
	world.queue_free()
	await process_frame
	return down
