extends SceneTree

const Rules = preload("res://scripts/eight_ball_rules.gd")
const AI = preload("res://scripts/ai_opponent.gd")

var failures := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	_test_group_assignment_and_foul()
	_test_legal_eight_ball_win()
	_test_ai_finds_direct_pot()
	if failures == 0:
		print("GAMEPLAY TESTS PASSED")
	quit(1 if failures > 0 else 0)


func _test_group_assignment_and_foul() -> void:
	var rules := Rules.new()
	rules.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	rules.record_first_contact(1)
	rules.record_pocket(1)
	var result := rules.evaluate_shot()
	_assert(not result["foul"], "A legal opening pocket is not a foul")
	_assert(rules.player_groups[1] == Rules.Group.SOLIDS, "First legal pocket assigns solids")
	_assert(rules.current_player == 1, "A legal pocket continues the turn")
	rules.begin_shot()
	rules.record_first_contact(9)
	rules.record_rail_contact()
	result = rules.evaluate_shot()
	_assert(result["foul"], "Contacting the opponent group first is a foul")
	_assert(rules.current_player == 2, "A foul passes the turn")


func _test_legal_eight_ball_win() -> void:
	var rules := Rules.new()
	rules.start_match(Rules.Mode.LOCAL_TWO_PLAYER)
	rules.record_first_contact(1)
	rules.record_pocket(1)
	rules.evaluate_shot()
	for number in range(2, 8):
		if number not in rules.pocketed:
			rules.pocketed.append(number)
	rules.begin_shot()
	rules.record_first_contact(8)
	rules.record_pocket(8)
	var result := rules.evaluate_shot()
	_assert(result["winner"] == 1, "Clearing a group then pocketing the eight ball wins")


func _test_ai_finds_direct_pot() -> void:
	var computer := AI.new()
	computer.configure(AI.Difficulty.HARD)
	var ball_positions := {1: Vector3(1.0, 1.0, 0.0), 9: Vector3(0.5, 1.0, 1.4)}
	var pockets: Array[Vector3] = [Vector3(4.4, 1.0, 0.0)]
	var plan := computer.plan_shot(Vector3(-2.8, 1.0, 0.0), ball_positions, [1], pockets)
	_assert(plan["target"] == 1, "AI selects a legal target")
	_assert(plan["direction"].x > 0.95, "AI aims along a clear potting line")
	_assert(plan["power"] > 0.2 and plan["power"] <= 1.0, "AI returns playable shot power")


func _assert(condition: bool, message: String) -> void:
	if condition:
		print("PASS: ", message)
		return
	push_error("FAIL: " + message)
	failures += 1
