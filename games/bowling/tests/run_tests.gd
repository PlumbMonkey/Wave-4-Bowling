extends SceneTree
## Headless tests:  godot --headless --path . --script res://tests/run_tests.gd
## Scoring rules first, then real Jolt throws down the grey-box alley.

var failures := 0


func _initialize() -> void:
	# a script error kills the coroutine silently - never hang the shell
	create_timer(150.0).timeout.connect(func():
		print("TIMEOUT - a test coroutine died (see script errors above)")
		quit(2))
	_run.call_deferred()


func check(cond: bool, what: String) -> void:
	if cond:
		print("  ok   ", what)
	else:
		failures += 1
		print("  FAIL ", what)


func card(rolls: Array) -> ScoreCard:
	var c := ScoreCard.new()
	for r in rolls:
		c.roll(r)
	return c


func _run() -> void:
	print("== scoring")
	check(card([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]).total() == 0, "gutter game = 0")
	var perfect := card([10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10])
	check(perfect.total() == 300 and perfect.is_complete(), "perfect game = 300")
	var spares := []
	for i in 21:
		spares.append(5)
	check(card(spares).total() == 150, "all 5-spares = 150")
	var nines := []
	for i in 10:
		nines += [9, 0]
	check(card(nines).total() == 90 and card(nines).is_complete(), "nine-and-miss x10 = 90")
	var mixed := card([10, 7, 3, 9, 0, 10, 0, 8, 8, 2, 0, 6, 10, 10, 10, 8, 1])
	check(mixed.total() == 167, "sample game = 167 (got %d)" % mixed.total())
	var f := mixed.frames()
	check(f[0].marks == ["X"] and f[1].marks == ["7", "/"] and f[2].marks == ["9", "-"], "marks X, 7/, 9-")
	check(f[9].marks == ["X", "8", "1"], "10th frame marks X 8 1")
	var partial := card([10, 3])
	check(partial.total() == 0 and partial.frames()[0].score == null, "strike waits for two more balls")
	check(partial.pins_standing() == 7, "7 standing after a 3 on the second frame")
	check(not partial.can_roll(8), "can't knock 8 when 7 are up")
	var tenth := card([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 4])
	check(tenth.pins_standing() == 6 and not tenth.is_complete(), "10th: X then 4 leaves 6 for the fill ball")
	check(tenth.frames()[9].marks == ["X", "4"], "10th marks X 4")
	var t2 := card([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 3, 10])
	check(t2.total() == 20 and t2.frames()[9].marks == ["7", "/", "X"], "10th spare + strike = 20, 7 / X")
	check(card([3, 4]).needs_full_rack() and card([3]).pins_standing() == 7, "rack rules in frames 1-9")

	print("== physics (Jolt: %s)" % ProjectSettings.get_setting("physics/3d/physics_engine"))
	var straight := await throw({"x": BowlingSpec.board_x(17.5), "aim": deg_to_rad(-0.6), "power": 0.72, "spin": 0.0})
	# right-hander: stand right of centre, aim slightly out, hook back left into the 1-3 pocket
	var hook := await throw({"x": BowlingSpec.board_x(12), "aim": deg_to_rad(0.3), "power": 0.72, "spin": -0.8})
	check(hook.max_x - hook.end_x > 0.15, "hook ball breaks left by %.2f m" % (hook.max_x - hook.end_x))
	check(straight.time < 3.2 and straight.time > 1.6, "reaches the pins in %.2f s" % straight.time)
	check(hook.down >= 7, "a pocket hook knocks down most pins (%d)" % hook.down)
	var gutter := await throw({"x": BowlingSpec.board_x(2), "aim": deg_to_rad(1.0), "power": 0.7, "spin": 0.0})
	check(gutter.gutter and gutter.down == 0, "a gutter ball stays in the gutter (%d down)" % gutter.down)

	# the aim guide predicts the real throw
	var pred: Array = BowlingBall.predict(BowlingSpec.board_x(12), deg_to_rad(0.3),
		lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, 0.72), -0.8)
	var pts: PackedVector3Array = pred[0]
	var px := 99.0
	for p in pts:
		if p.z <= -15.0:
			px = p.x
			break
	check(absf(px - hook.x15) < 0.05, "aim guide predicts the hook: x %+.3f vs real %+.3f at 15 m" % [px, hook.x15])

	# the oil changes from game to game and breaks down as you bowl
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	var pa := OilPattern.random(rng)
	var pb := OilPattern.random(rng)
	check(absf(pa.length - pb.length) > 0.05 or absf(pa.mu_dry - pb.mu_dry) > 0.005, "each game gets its own oil pattern")
	var worn := OilPattern.house()
	var sp := lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, 0.72)
	var fresh_line: PackedVector3Array = BowlingBall.predict(BowlingSpec.board_x(12), deg_to_rad(0.3), sp, -0.8, worn)[0]
	for k in 8:
		worn.wear_path(fresh_line)
	var worn_line: PackedVector3Array = BowlingBall.predict(BowlingSpec.board_x(12), deg_to_rad(0.3), sp, -0.8, worn)[0]
	var dx := absf(fresh_line[fresh_line.size() - 1].x - worn_line[worn_line.size() - 1].x)
	check(dx > 0.04, "after 8 balls the same throw finishes %.2f m off its fresh line" % dx)

	var steer := await throw({"x": 0.0, "aim": 0.0, "power": 0.72, "spin": 0.0, "steer": 1.0})
	check(steer.end_x > 0.15 and steer.end_x < 0.6, "full stick nudges the ball right %.2f m, subtly" % steer.end_x)

	print("== network groundwork")
	var game: Node = (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	for i in 60:
		await physics_frame
	BowlingBall.pattern = OilPattern.house()
	var inputs := PackedFloat32Array()
	for k in 400:
		inputs.append(-0.6 if k > 90 and k < 200 else 0.0)     # hook partway down
		inputs.append(0.8 if k < 120 else 0.0)                  # and a nudge right
	var sent := {"params": {"x": BowlingSpec.board_x(12), "aim": deg_to_rad(0.3), "power": 0.72,
		"spin": -0.8, "jitter": 1.0}, "inputs": inputs}
	check(game.play_remote_throw(sent), "a remote throw is accepted while aiming")
	var rec_a: Dictionary = await game.throw_completed
	check(game.audio.events.any(func(e): return e[1] == "crash"), "a full-rack hit plays the rack crash")
	var heard := {}
	for e in game.audio.events:
		heard[e[1]] = int(heard.get(e[1], 0)) + 1
	print("  sounds during the throw: ", heard)
	check(heard.has("ball_pin") and heard.has("release") and not heard.has("whoosh"),
		"a throw sounds the ball landing and hitting pins, with no swish")
	check(heard.has("pin_pin"), "pins clatter against each other")
	game.new_game()
	BowlingBall.pattern = OilPattern.house()
	for i in 60:
		await physics_frame
	game.play_remote_throw(rec_a)
	var rec_b: Dictionary = await game.throw_completed
	var drift: float = (rec_a.ball_end as Vector3).distance_to(rec_b.ball_end)
	print("  record: %d input ticks, %d pins; replayed: %d pins, ball ends %.3f m apart" % [
		rec_a.inputs.size() / 2, rec_a.pins, rec_b.pins, drift])
	check(rec_a.inputs.size() > 300 and rec_a.inputs == rec_b.inputs, "the record carries every tick of steer and hook")
	check(rec_a.pins == rec_b.pins and drift < 0.05, "playing a record back reproduces the throw")
	# the bone set: a different mesh on the same collider
	var classic_mesh: Mesh = BowlingPin.style_mesh("classic")
	BowlingPin.set_style("bone", game.setter.pins)
	var pin0: BowlingPin = game.setter.pins[0]
	check(pin0._mi.mesh != classic_mesh and pin0._mi.mesh != null, "bone pins swap in their own mesh")
	var shape := (pin0.get_child(1) as CollisionShape3D).shape
	check(shape is ConvexPolygonShape3D and is_equal_approx(pin0.mass, BowlingSpec.PIN_MASS), "bone pins keep the regulation collider and mass")
	BowlingPin.set_style("reliquary", game.setter.pins)
	var designs := {}
	for pn in game.setter.pins:
		designs[(pn as BowlingPin)._mi.mesh] = true
	check(designs.size() == 4, "the Reliquary rack shows its four designs (%d)" % designs.size())
	BowlingPin.set_style("classic", game.setter.pins)
	game.queue_free()

	print("\n%s (%d failure%s)" % ["PASS" if failures == 0 else "FAILED", failures, "" if failures == 1 else "s"])
	quit(1 if failures else 0)


## Throw one ball down a fresh alley and report what happened.
func throw(t: Dictionary) -> Dictionary:
	var world := Node3D.new()
	root.add_child(world)
	var alley := Alley.new()
	world.add_child(alley)
	var setter := Pinsetter.new()
	world.add_child(setter)
	var ball := BowlingBall.new()
	world.add_child(ball)
	for i in 30:                      # let the rack settle on the deck
		await physics_frame
	var speed := lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, t.power)
	ball.launch(t.x, t.aim, speed, t.spin)
	ball.steer_input = t.get("steer", 0.0)
	var dt := 1.0 / Engine.physics_ticks_per_second
	var time := 0.0
	var arrive := -1.0
	var max_x := -9.0
	var track := []
	var x15 := 99.0
	setter.reset_settle()
	while time < 12.0:
		await physics_frame
		time += dt
		var p := ball.global_position
		if x15 > 90.0 and p.z <= -15.0:
			x15 = p.x
		max_x = maxf(max_x, p.x) if p.z > -17.0 else max_x
		if track.size() < int(-p.z / 3.0) and p.z < 0.0:
			track.append("z%.0f x%+.2f" % [p.z, p.x])
		if arrive < 0.0 and p.z < -BowlingSpec.LANE_LEN + 0.3:
			arrive = time
		if arrive > 0.0 and time - arrive > 1.0 and setter.tick_settle(dt):
			break
		if arrive < 0.0 and time > 6.0:
			break
	var down := 10 - setter.standing().size()
	print("  throw x%+.2f aim %+.1f° power %.2f spin %+.1f -> %d down, arrive %.2fs, entry x%+.2f %s  [%s]" % [
		t.x, rad_to_deg(t.aim), t.power, t.spin, down, arrive, ball.global_position.x,
		"(gutter)" if ball.in_gutter else "", ", ".join(track)])
	var result := {"down": down, "time": arrive, "max_x": max_x, "end_x": _x_at(track, ball),
		"gutter": ball.in_gutter, "x15": x15}
	world.queue_free()
	await process_frame
	return result


func _x_at(track: Array, ball: BowlingBall) -> float:
	return ball.global_position.x if track.is_empty() else float(str(track[-1]).split("x")[1])
