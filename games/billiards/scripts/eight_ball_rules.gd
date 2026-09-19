class_name EightBallRules
extends RefCounted

enum Mode { PRACTICE, VS_CPU, LOCAL_TWO_PLAYER }
enum Group { OPEN, SOLIDS, STRIPES }

var mode := Mode.PRACTICE
var current_player := 1
var winner := 0
var player_groups := {1: Group.OPEN, 2: Group.OPEN}
var pocketed: Array[int] = []

var shot_pockets: Array[int] = []
var first_contact := -1
var rail_contact := false


func start_match(selected_mode: Mode) -> void:
	mode = selected_mode
	current_player = 1
	winner = 0
	player_groups = {1: Group.OPEN, 2: Group.OPEN}
	pocketed.clear()
	begin_shot()


func begin_shot() -> void:
	shot_pockets.clear()
	first_contact = -1
	rail_contact = false


func record_first_contact(number: int) -> void:
	if first_contact < 0 and number > 0:
		first_contact = number


func record_rail_contact() -> void:
	rail_contact = true


func record_pocket(number: int) -> void:
	if number not in shot_pockets:
		shot_pockets.append(number)
	if number > 0 and number not in pocketed:
		pocketed.append(number)


func evaluate_shot() -> Dictionary:
	if mode == Mode.PRACTICE:
		var scratch := 0 in shot_pockets
		return {
			"foul": scratch,
			"switch_turn": false,
			"winner": 0,
			"message": "Scratch — cue ball returned" if scratch else "Practice table ready",
		}

	var shooter := current_player
	var opponent := 2 if shooter == 1 else 1
	var foul := 0 in shot_pockets
	var legal_target := _is_legal_first_contact(shooter, first_contact)
	if not legal_target:
		foul = true
	var object_pocketed := false
	for number in shot_pockets:
		if number > 0:
			object_pocketed = true
	if first_contact > 0 and not object_pocketed and not rail_contact:
		foul = true

	if 8 in shot_pockets:
		var legal_eight: bool = player_groups[shooter] != Group.OPEN and remaining_for_player(shooter) == 0
		winner = shooter if legal_eight and not foul else opponent
		return {
			"foul": foul,
			"switch_turn": false,
			"winner": winner,
			"message": "Player %d wins the manor table" % winner,
		}

	if player_groups[shooter] == Group.OPEN and not foul:
		_assign_group_from_shot(shooter)

	var own_ball_pocketed := false
	var shooter_group: Group = player_groups[shooter]
	for number in shot_pockets:
		if _number_group(number) == shooter_group:
			own_ball_pocketed = true
	var switch_turn := foul or not own_ball_pocketed
	if switch_turn:
		current_player = opponent
	return {
		"foul": foul,
		"switch_turn": switch_turn,
		"winner": 0,
		"message": _result_message(shooter, foul, own_ball_pocketed),
	}


func legal_targets(player: int) -> Array[int]:
	var result: Array[int] = []
	var group: Group = player_groups[player]
	if group == Group.OPEN:
		for number in range(1, 16):
			if number != 8 and number not in pocketed:
				result.append(number)
		return result
	if remaining_for_player(player) == 0:
		if 8 not in pocketed:
			result.append(8)
		return result
	for number in range(1, 16):
		if _number_group(number) == group and number not in pocketed:
			result.append(number)
	return result


func remaining_for_player(player: int) -> int:
	var group: Group = player_groups[player]
	if group == Group.OPEN:
		return 7
	var remaining := 0
	for number in range(1, 16):
		if _number_group(number) == group and number not in pocketed:
			remaining += 1
	return remaining


func group_name(player: int) -> String:
	match player_groups[player]:
		Group.SOLIDS:
			return "Solids"
		Group.STRIPES:
			return "Stripes"
		_:
			return "Open Table"


func _is_legal_first_contact(player: int, number: int) -> bool:
	if number <= 0:
		return false
	var group: Group = player_groups[player]
	if group == Group.OPEN:
		return number != 8
	if remaining_for_player(player) == 0:
		return number == 8
	return _number_group(number) == group


func _assign_group_from_shot(shooter: int) -> void:
	for number in shot_pockets:
		var group := _number_group(number)
		if group == Group.OPEN:
			continue
		player_groups[shooter] = group
		var opponent := 2 if shooter == 1 else 1
		player_groups[opponent] = Group.STRIPES if group == Group.SOLIDS else Group.SOLIDS
		return


func _number_group(number: int) -> Group:
	if number >= 1 and number <= 7:
		return Group.SOLIDS
	if number >= 9 and number <= 15:
		return Group.STRIPES
	return Group.OPEN


func _result_message(shooter: int, foul: bool, own_ball_pocketed: bool) -> String:
	if foul:
		return "Foul by Player %d — opponent has ball in hand" % shooter
	if own_ball_pocketed:
		return "Player %d continues" % shooter
	return "Turn passes to Player %d" % current_player
