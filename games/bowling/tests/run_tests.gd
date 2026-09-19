extends SceneTree
## Headless tests:  godot --headless --path . --script res://tests/run_tests.gd
## Scoring rules first, then real Jolt throws down the grey-box alley.

var failures := 0


func _initialize() -> void:
	# a scratch settings file, so the player's own (best score, bowlers...) are never touched
	BowlingSettings.path = "user://test_settings.cfg"
	DirAccess.remove_absolute(BowlingSettings.path)
	# a script error kills the coroutine silently - never hang the shell
	create_timer(240.0).timeout.connect(func():
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
	check(game.state == game.State.TITLE and game.menus.current() == "title", "the game opens on the title screen")
	game.start_from_title()
	check(game.state == game.State.AIM and not game.menus.is_open() and game.hud.visible, "BOWL starts a game")
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

	print("== alleys")
	var own_light := {"lounge": "L_LGT_Chandelier_0", "void": "L_LGT_Nebula_0", "crypt": "L_LGT_Torch_0"}
	for id in AlleyTheme.ALLEY_ORDER:
		game.set_alley(id)
		await process_frame
		var t: AlleyTheme = game.theme
		var lights := t.find_children("L_LGT_*", "Light3D", false, false)
		check(t != null and t.id == id and t.get_node_or_null("Art") != null,
			"%s loads its art" % AlleyTheme.display_name_of(id))
		check(lights.size() > 10 and t.get_node_or_null(own_light[id]) != null,
			"%s lights itself (%d lights, incl. %s)" % [id, lights.size(), own_light[id]])
		check(game.get_children().filter(func(n): return n is AlleyTheme and not n.is_queued_for_deletion()).size() == 1,
			"%s replaces the last alley rather than stacking" % id)
	game.set_alley("lounge")

	print("== menus")
	game.menus.open("pause")
	check(paused and game.menus.current() == "pause", "Start / Esc pauses the game under the menu")
	game.menus.close()
	check(not paused, "resume unpauses")
	BowlingSettings.save_value("vol_callouts", 0.5)
	game.apply_volumes()
	var cb := AudioServer.get_bus_index("Callouts")
	check(cb >= 0 and absf(AudioServer.get_bus_volume_db(cb) - linear_to_db(0.5)) < 0.01,
		"the call-out volume slider drives its own bus")
	BowlingSettings.save_value("vol_callouts", 0.7)
	game.apply_volumes()
	check(game.hud.callout_art("no_such_kind") == null, "a call-out with no painting falls back to text")
	game.hud.callout("strike", "STRIKE!")
	var mixed_card := card([10, 7, 3, 9, 0, 10, 0, 8, 8, 2, 0, 6, 10, 10, 10, 8, 1])
	game.menus.show_over(mixed_card, 150)
	check(game.menus.current() == "over" and game.menus._over_score.text == "167"
		and game.menus._over_stats.text.contains("STRIKES  5") and game.menus._over_best.text == "NEW BEST GAME!",
		"game over shows the score, strikes and a new best")
	var pad_a := false
	for e in InputMap.action_get_events("ui_accept"):
		pad_a = pad_a or (e is InputEventJoypadButton and e.button_index == JOY_BUTTON_A)
	check(pad_a, "the pad's A button presses menu buttons")
	check(game.menus._first["over"] is Button and game.menus._screens["over"].find_children("*", "Button", true, false).size() >= 5,
		"game over offers bowl again, alley, pins, ball and title")
	game.menus.close()
	game.state = game.State.GAME_OVER
	check(not game.can_pause(), "Start can't bury the game-over screen under the pause menu")

	# placing the ball: it eases up to speed and eases to a stop
	game.state = game.State.AIM
	game.stance_x = 0.0
	game._stance_v = 0.0
	Input.action_press("move_right")
	game._update_stance(1.0 / 120.0)
	var first_step: float = game._stance_v
	for i in 60:
		game._update_stance(1.0 / 120.0)
	var cruising: float = game._stance_v
	Input.action_release("move_right")
	for i in 60:
		game._update_stance(1.0 / 120.0)
	check(first_step > 0.0 and first_step < cruising * 0.2 and cruising > 0.8 and absf(game._stance_v) < 0.01
		and game.stance_x > 0.2, "the ball eases across the approach and eases to a stop (%.2f m)" % game.stance_x)

	print("== two players")
	var saved := BowlingSettings.load_all()
	BowlingSettings.save_value("players", 2)
	BowlingSettings.save_value("names", ["WRAITH", "", "", ""])
	BowlingSettings.save_value("balls", [2, 0, 1, 0])
	game.new_game()
	check(game.players.size() == 2 and game.players[0].name == "WRAITH" and game.players[1].name == "PLAYER 2",
		"two bowlers, named or defaulted")
	check(game.ball.skin == "skull", "bowler 1 steps up with their own ball")
	var order := []
	var step := func(pins: int):
		order.append(game.cur_player)
		game.card.roll(pins)
		game._advance()
	step.call(10)                 # WRAITH strikes: frame over, P2 is up
	check(game.cur_player == 1 and game.ball.skin == "spectre", "after a strike the other bowler is up, with their ball")
	step.call(3)                  # P2 leaves 7 standing: still their frame
	check(game.cur_player == 1, "a second ball stays with the same bowler")
	step.call(4)
	check(game.cur_player == 0, "an open frame hands the lane back")
	# play the rest out: gutter balls, until the game ends
	var guard := 0
	while game.state != game.State.GAME_OVER and guard < 60:
		step.call(0)
		guard += 1
	check(game.state == game.State.GAME_OVER and game.players.all(func(p): return p.card.is_complete()),
		"the game ends when both cards are complete (%d balls)" % order.size())
	check(order.slice(0, 7) == [0, 1, 1, 0, 0, 1, 1], "frames alternate between the bowlers")
	game.menus.show_over(game.players, 999)
	check(game.menus._over_best.text == "WRAITH WINS!" and game.menus._over_stats.text.begins_with("1.  WRAITH"),
		"game over names the winner and ranks the bowlers")
	game.menus.close()
	for k in ["players", "names", "balls", "best"]:
		BowlingSettings.save_value(k, saved[k])

	game.cycle_pins(0)
	game.pin_style = "bone"
	game._apply_pins(false)
	check(game.audio.sound_set == "bone_" and game.audio._streams["bone_pin_pin"].size() == 8,
		"bone pins play the original pin sounds; the others the deep set")
	game.pin_style = "classic"
	game._apply_pins(false)
	check(game.audio.sound_set == "", "classic pins play the deep set")

	print("== computer bowler")
	BowlingBall.pattern = OilPattern.house()
	var spd := lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, 0.74)
	var pk := BowlerAI.plan(3, BowlingSpec.pin_spots())
	var at_head := BowlerAI.x_at(pk.x, pk.aim, spd, pk.spin, -BowlingSpec.LANE_LEN)
	check(absf(at_head - BowlerAI.POCKET_X) < 0.01, "the computer finds the 1-3 pocket (x %+.3f at the head pin)" % at_head)
	var ten: Vector3 = BowlingSpec.pin_spots()[6]          # a corner pin alone
	var sp2 := BowlerAI.plan(3, [ten])
	var at_pin := BowlerAI.x_at(sp2.x, sp2.aim, lerpf(BowlingSpec.SPEED_MIN, BowlingSpec.SPEED_MAX, sp2.power), sp2.spin, ten.z)
	check(absf(at_pin - ten.x) < 0.03, "...and lines up a corner-pin spare (x %+.3f vs pin %+.3f)" % [at_pin, ten.x])
	var perfect_throw := await throw({"x": pk.x, "aim": pk.aim, "power": pk.power, "spin": pk.spin})
	check(perfect_throw.down >= 9, "its pocket line carries (%d down)" % perfect_throw.down)
	BowlingSettings.save_value("players", 1)
	BowlingSettings.save_value("opponent", 2)
	game.new_game()
	check(game.players.size() == 2 and game.players[1].ai == 2 and game.players[1].name == "POLTERGEIST",
		"VS CPU adds a computer bowler after the humans")
	game.card.roll(10)
	game._advance()
	await game.setter.cycle_done
	check(game.cur_player == 1 and game.is_cpu_turn() and game.state == game.State.AIM, "after your frame the computer is up")
	var waited := 0
	while game.state == game.State.AIM and waited < 600:
		await physics_frame
		waited += 1
	check(game.state == game.State.ROLL, "it lines up and throws by itself (%.1f s)" % (waited / 120.0))
	BowlingSettings.save_value("opponent", 0)
	game.show_title()
	game.menus.close()

	# the recorded set: a real strike into a full rack, the synth standing aside
	BowlingSettings.save_value("pin_sounds", "recorded")
	game._apply_pins(false)
	check(game.audio.recorded and game.audio._streams["rec_crash"].size() == 2
		and game.audio._streams["rec_pinsetter"].size() == 3, "the recorded set loads (2 strikes, 3 pinsetter cycles)")
	game.new_game()
	for i in 60:
		await physics_frame
	BowlingBall.pattern = OilPattern.house()
	game.play_remote_throw(rec_a)
	await game.throw_completed
	var rec_heard := {}
	for e in game.audio.events:
		rec_heard[e[1]] = int(rec_heard.get(e[1], 0)) + 1
	check(rec_heard.has("rec_crash") and not rec_heard.has("crash"),
		"with Authentic pin sounds a full-rack hit plays the real strike (%s)" % str(rec_heard))
	check(game.audio.sound_set == "rec_" and game.audio._streams["rec_pin_pin"].size() == 8
		and game.audio._streams["rec_ball_pin"].size() == 3, "...and every single contact has a recorded hit")
	# a spare: no recorded strike, the single recorded hits instead
	game.setter.pins[0].sweep()
	game.setter.pins[1].sweep()
	game.new_game()
	game.card.roll(2)
	game.setter.clear_deadwood()
	for i in [0, 1]:
		game.setter.pins[i].sweep()
	for i in 30:
		await physics_frame
	game.play_remote_throw(rec_a)
	await game.throw_completed
	var sp_heard := {}
	for e in game.audio.events:
		sp_heard[e[1]] = int(sp_heard.get(e[1], 0)) + 1
	check(not sp_heard.has("rec_crash") and (sp_heard.has("rec_ball_pin") or sp_heard.has("rec_pin_pin")),
		"on a spare the ball and pins play recorded single hits (%s)" % str(sp_heard))
	BowlingSettings.save_value("pin_sounds", "auto")
	game._apply_pins(false)

	print("== pinsetter")
	game.show_title()
	game.menus.close()
	var ps: Pinsetter = game.setter
	for i in 6:                                    # knock six over
		var pin: BowlingPin = ps.pins[i]
		pin.freeze = true
		pin.global_transform = Transform3D(Basis(Vector3.RIGHT, PI / 2), pin.spot + Vector3(0, 0.06, 0.1))
	ps.animate("deadwood")
	var t0 := Time.get_ticks_msec()
	await ps.cycle_done
	var took := (Time.get_ticks_msec() - t0) / 1000.0
	var upright := ps.standing()
	check(upright.size() == 4 and ps.pins.slice(0, 6).all(func(p): return not p.in_play())
		and upright.all(func(p): return absf(p.global_position.y) < 0.01 and not p.freeze),
		"second ball: the table lifts the 4 standing, the bar sweeps the 6 down, the 4 go back (%.1f s)" % took)
	ps.animate("full")
	await ps.cycle_done
	check(ps.standing().size() == 10 and ps.pins.all(func(p): return p.global_position.distance_to(p.spot) < 0.01)
		and not ps.busy and not ps._bar.visible, "a full cycle sets ten fresh pins on their spots and parks the machine")
	ps.animate("full")
	ps.full_rack()                                 # e.g. a new game mid-cycle
	for i in 90:
		await physics_frame
	check(ps.standing().size() == 10 and not ps.busy, "cancelling mid-cycle leaves a clean rack")
	game.show_title()
	check(game.state == game.State.TITLE and not game.ball.visible, "quit to title hides the ball and opens the title")
	game.menus.close()
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
