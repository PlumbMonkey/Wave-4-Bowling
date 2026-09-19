extends SceneTree

const Rules = preload("res://scripts/eight_ball_rules.gd")
const AI = preload("res://scripts/ai_opponent.gd")
const Cue = preload("res://scripts/cue_controller.gd")

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	_test_group_assignment_and_foul()
	_test_break_rules_and_ball_in_hand()
	_test_eight_on_break_is_respotted()
	_test_legal_eight_ball_win()
	_test_wrong_called_pocket_loses()
	_test_ai_finds_direct_pot()
	_test_spin_produces_torque()
	if failures == 0:
		print("GAMEPLAY TESTS PASSED")
	quit(1 if failures > 0 else 0)


func _test_group_assignment_and_foul() -> void:
	var rules := Rules.new()
	rules.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	rules.is_break_shot = false
	rules.record_first_contact(1)
	rules.record_pocket(1)
	var result := rules.evaluate_shot()
	_assert(not result["foul"], "A legal opening pocket is not a foul")
	_assert(rules.player_groups[1] == Rules.Group.SOLIDS, "First legal pocket assigns solids")
	_assert(rules.current_player == 1, "A legal pocket continues the turn")
	rules.begin_shot()
	rules.record_first_contact(9)
	rules.record_rail_contact(9)
	result = rules.evaluate_shot()
	_assert(result["foul"], "Contacting the opponent group first is a foul")
	_assert(rules.current_player == 2, "A foul passes the turn")


func _test_legal_eight_ball_win() -> void:
	var rules := Rules.new()
	rules.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	rules.is_break_shot = false
	rules.record_first_contact(1)
	rules.record_pocket(1)
	rules.evaluate_shot()
	for number in range(2, 8):
		if number not in rules.pocketed:
			rules.pocketed.append(number)
	rules.begin_shot()
	rules.call_pocket(3)
	rules.record_first_contact(8)
	rules.record_pocket(8, 3)
	var result := rules.evaluate_shot()
	_assert(result["winner"] == 1, "Clearing a group then pocketing the eight ball wins")


func _test_break_rules_and_ball_in_hand() -> void:
	var legal := Rules.new()
	legal.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	legal.record_first_contact(1)
	for number in [1, 2, 3, 4]:
		legal.record_rail_contact(number)
	var result := legal.evaluate_shot()
	_assert(not result["foul"], "A four-rail break contacting the one ball is legal")
	_assert(not legal.is_break_shot, "Break state ends after evaluation")

	var illegal := Rules.new()
	illegal.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	illegal.record_first_contact(2)
	result = illegal.evaluate_shot()
	_assert(result["foul"], "An illegal break is a foul")
	_assert(result["ball_in_hand"], "An illegal break grants ball in hand")
	_assert(illegal.current_player == 2, "An illegal break passes the turn")


func _test_eight_on_break_is_respotted() -> void:
	var rules := Rules.new()
	rules.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	rules.record_first_contact(1)
	rules.record_pocket(8, 2)
	var result := rules.evaluate_shot()
	_assert(result["respot_eight"], "The eight ball is respotted when made on the break")
	_assert(result["winner"] == 0, "The eight ball on the break does not end the match")
	_assert(8 not in rules.pocketed, "Respotted eight ball remains in play")


func _test_wrong_called_pocket_loses() -> void:
	var rules := Rules.new()
	rules.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	rules.is_break_shot = false
	rules.player_groups = {1: Rules.Group.SOLIDS, 2: Rules.Group.STRIPES}
	for number in range(1, 8):
		rules.pocketed.append(number)
	rules.begin_shot()
	rules.call_pocket(1)
	rules.record_first_contact(8)
	rules.record_pocket(8, 4)
	var result := rules.evaluate_shot()
	_assert(result["winner"] == 2, "Pocketing the eight ball in the wrong called pocket loses")


func _test_ai_finds_direct_pot() -> void:
	var computer := AI.new()
	computer.configure(AI.Difficulty.HARD)
	var ball_positions := {1: Vector3(1.0, 1.0, 0.0), 9: Vector3(0.5, 1.0, 1.4)}
	var pockets: Array[Vector3] = [Vector3(4.4, 1.0, 0.0)]
	var plan := computer.plan_shot(Vector3(-2.8, 1.0, 0.0), ball_positions, [1], pockets)
	_assert(plan["target"] == 1, "AI selects a legal target")
	_assert(plan["direction"].x > 0.95, "AI aims along a clear potting line")
	_assert(plan["power"] > 0.2 and plan["power"] <= 1.0, "AI returns playable shot power")


func _test_spin_produces_torque() -> void:
	var cue := Cue.new()
	cue.spin = Vector2(0.7, -0.8)
	var torque := cue.torque_for_shot(Vector3.RIGHT, 0.75)
	_assert(absf(torque.y) > 0.01, "Side English produces vertical-axis torque")
	_assert(absf(torque.z) > 0.01, "Draw produces rolling-axis torque")


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
