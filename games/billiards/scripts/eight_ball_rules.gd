class_name EightBallRules
extends RefCounted

enum Mode { PRACTICE, VS_CPU, LOCAL_TWO_PLAYER }
enum Group { OPEN, SOLIDS, STRIPES }

var mode := Mode.PRACTICE
var current_player := 1
var winner := 0
var player_groups := {1: Group.OPEN, 2: Group.OPEN}
var pocketed: Array[int] = []
var is_break_shot := true
var ball_in_hand := false

var shot_pockets: Array[int] = []
var shot_pocket_indices := {}
var first_contact := -1
var rail_balls: Array[int] = []
var called_pocket := -1


func start_match(selected_mode: Mode) -> void:
	mode = selected_mode
	current_player = 1
	winner = 0
	player_groups = {1: Group.OPEN, 2: Group.OPEN}
	pocketed.clear()
	is_break_shot = true
	ball_in_hand = false
	begin_shot()


func begin_shot() -> void:
	shot_pockets.clear()
	shot_pocket_indices.clear()
	first_contact = -1
	rail_balls.clear()
	called_pocket = -1


func call_pocket(pocket_index: int) -> void:
	called_pocket = pocket_index


func record_first_contact(number: int) -> void:
	if first_contact < 0 and number > 0:
		first_contact = number


func record_rail_contact(number: int) -> void:
	if number > 0 and number not in rail_balls:
		rail_balls.append(number)


func record_pocket(number: int, pocket_index: int = -1) -> void:
	if number not in shot_pockets:
		shot_pockets.append(number)
	shot_pocket_indices[number] = pocket_index
	if number > 0 and number not in pocketed:
		pocketed.append(number)


func evaluate_shot() -> Dictionary:
	if mode == Mode.PRACTICE:
		var practice_scratch := 0 in shot_pockets
		ball_in_hand = practice_scratch
		is_break_shot = false
		return _result(practice_scratch, false, 0, false, "Scratch — place the cue ball" if practice_scratch else "Practice table ready")

	var shooter := current_player
	var opponent := 2 if shooter == 1 else 1
	var scratch := 0 in shot_pockets
	var object_pocketed := _object_ball_was_pocketed()

	if is_break_shot:
		var legal_break := first_contact == 1 and (object_pocketed or rail_balls.size() >= 4)
		var break_foul := scratch or not legal_break
		var eight_on_break := 8 in shot_pockets
		if eight_on_break:
			pocketed.erase(8)
		is_break_shot = false
		ball_in_hand = break_foul
		var switch_break_turn := break_foul or not object_pocketed
		if switch_break_turn:
			current_player = opponent
		var break_message := "Eight ball spotted — breaker continues" if eight_on_break and not break_foul else ("Illegal break — opponent has ball in hand" if break_foul else ("Breaker continues" if object_pocketed else "Turn passes to Player %d" % current_player))
		return _result(break_foul, switch_break_turn, 0, eight_on_break, break_message)

	var foul := scratch or not _is_legal_first_contact(shooter, first_contact)
	if first_contact > 0 and not object_pocketed and rail_balls.is_empty():
		foul = true

	if 8 in shot_pockets:
		var group_cleared: bool = player_groups[shooter] != Group.OPEN and remaining_for_player(shooter) == 0
		var correct_pocket: bool = called_pocket >= 0 and int(shot_pocket_indices.get(8, -2)) == called_pocket
		winner = shooter if group_cleared and correct_pocket and not foul else opponent
		ball_in_hand = false
		return _result(foul, false, winner, false, "Player %d wins the manor table" % winner)

	if player_groups[shooter] == Group.OPEN and not foul:
		_assign_group_from_shot(shooter)

	var own_ball_pocketed := false
	var shooter_group: Group = player_groups[shooter]
	for number in shot_pockets:
		if _number_group(number) == shooter_group:
			own_ball_pocketed = true
	var switch_turn := foul or not own_ball_pocketed
	ball_in_hand = foul
	if switch_turn:
		current_player = opponent
	return _result(foul, switch_turn, 0, false, _result_message(shooter, foul, own_ball_pocketed))


func legal_targets(player: int) -> Array[int]:
	var result: Array[int] = []
	var group: Group = player_groups[player]
	if is_break_shot:
		return [1]
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


func _object_ball_was_pocketed() -> bool:
	for number in shot_pockets:
		if number > 0:
			return true
	return false


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


func _result(foul: bool, switch_turn: bool, winning_player: int, respot_eight: bool, message: String) -> Dictionary:
	return {
		"foul": foul,
		"switch_turn": switch_turn,
		"winner": winning_player,
		"respot_eight": respot_eight,
		"ball_in_hand": ball_in_hand,
		"message": message,
	}


func _result_message(shooter: int, foul: bool, own_ball_pocketed: bool) -> String:
	if foul:
		return "Foul by Player %d — opponent has ball in hand" % shooter
	if own_ball_pocketed:
		return "Player %d continues" % shooter
	return "Turn passes to Player %d" % current_player
