class_name BilliardsAI
extends RefCounted

enum Difficulty { EASY, MEDIUM, HARD }

const BALL_DIAMETER := 0.225
const TABLE_MIN_X := -4.18
const TABLE_MAX_X := 4.18
const TABLE_MIN_Z := -1.98
const TABLE_MAX_Z := 1.98

var difficulty := Difficulty.MEDIUM
var rng := RandomNumberGenerator.new()


func _init() -> void:
	rng.seed = 0x5EC7A1


func configure(level: Difficulty) -> void:
	difficulty = level


func plan_shot(cue_position: Vector3, ball_positions: Dictionary, legal_numbers: Array[int], pocket_positions: Array[Vector3]) -> Dictionary:
	var direct := _best_direct_shot(cue_position, ball_positions, legal_numbers, pocket_positions)
	var selected := direct
	if difficulty == Difficulty.HARD:
		var bank := plan_bank_shot(cue_position, ball_positions, legal_numbers, pocket_positions)
		if direct.is_empty() or float(direct.get("confidence", 0.0)) < 0.31:
			selected = bank if not bank.is_empty() else plan_safety_shot(cue_position, ball_positions, legal_numbers)
		elif not bank.is_empty() and float(bank.get("score", -INF)) > float(direct.get("score", -INF)) + 0.3:
			selected = bank
	if selected.is_empty():
		selected = _fallback_shot(cue_position, ball_positions, legal_numbers)
	return _apply_difficulty(selected)


func _best_direct_shot(cue_position: Vector3, ball_positions: Dictionary, legal_numbers: Array[int], pocket_positions: Array[Vector3]) -> Dictionary:
	var best := {}
	var best_score := -INF
	for number in legal_numbers:
		if not ball_positions.has(number):
			continue
		var target: Vector3 = ball_positions[number]
		for pocket_index in pocket_positions.size():
			var pocket: Vector3 = pocket_positions[pocket_index]
			var target_to_pocket := _flat(pocket - target)
			if target_to_pocket.length() < 0.01:
				continue
			var pocket_direction := target_to_pocket.normalized()
			var ghost := target - pocket_direction * BALL_DIAMETER
			var cue_path := _flat(ghost - cue_position)
			if cue_path.length() < 0.05:
				continue
			var cue_direction := cue_path.normalized()
			var alignment := cue_direction.dot(pocket_direction)
			if alignment < 0.18:
				continue
			if not _corridor_clear(cue_position, ghost, ball_positions, [number]):
				continue
			if not _corridor_clear(target, pocket, ball_positions, [number]):
				continue
			var distance := cue_path.length() + target_to_pocket.length()
			var position_quality := _position_quality(ghost, cue_direction, ball_positions, legal_numbers, number)
			var score := alignment * 4.0 - distance * 0.22
			if difficulty == Difficulty.HARD:
				score += position_quality * 0.9
			if number == 8:
				score += 2.0
			if score > best_score:
				best_score = score
				best = {
					"shot_type": "DIRECT",
					"direction": cue_direction,
					"power": clampf(0.28 + distance * 0.065, 0.34, 0.92),
					"target": number,
					"pocket": pocket,
					"pocket_index": pocket_index,
					"confidence": clampf((alignment + 1.0) * 0.5 - distance * 0.025, 0.0, 1.0),
					"position_score": position_quality,
					"score": score,
					"spin": _position_spin(ghost, cue_direction, ball_positions, legal_numbers, number),
				}
	return best


func plan_bank_shot(cue_position: Vector3, ball_positions: Dictionary, legal_numbers: Array[int], pocket_positions: Array[Vector3]) -> Dictionary:
	var best := {}
	var best_score := -INF
	var rails := [
		{"axis": "x", "value": TABLE_MIN_X}, {"axis": "x", "value": TABLE_MAX_X},
		{"axis": "z", "value": TABLE_MIN_Z}, {"axis": "z", "value": TABLE_MAX_Z},
	]
	for number in legal_numbers:
		if not ball_positions.has(number):
			continue
		var target: Vector3 = ball_positions[number]
		for pocket_index in pocket_positions.size():
			var pocket: Vector3 = pocket_positions[pocket_index]
			for rail in rails:
				var bank_point := _bank_point(target, pocket, rail)
				if bank_point == Vector3.INF:
					continue
				var incoming := _flat(bank_point - target).normalized()
				var ghost := target - incoming * BALL_DIAMETER
				var cue_path := _flat(ghost - cue_position)
				if cue_path.length() < 0.05:
					continue
				var cue_direction := cue_path.normalized()
				var alignment := cue_direction.dot(incoming)
				if alignment < 0.16:
					continue
				if not _corridor_clear(cue_position, ghost, ball_positions, [number]):
					continue
				if not _corridor_clear(target, bank_point, ball_positions, [number]):
					continue
				if not _corridor_clear(bank_point, pocket, ball_positions, [number]):
					continue
				var distance := cue_path.length() + target.distance_to(bank_point) + bank_point.distance_to(pocket)
				var position_quality := _position_quality(ghost, cue_direction, ball_positions, legal_numbers, number)
				var confidence := clampf(alignment * 0.62 - distance * 0.018, 0.05, 0.68)
				var score := alignment * 3.0 - distance * 0.18 - 0.75 + position_quality * 0.55
				if score > best_score:
					best_score = score
					best = {
						"shot_type": "BANK",
						"direction": cue_direction,
						"power": clampf(0.48 + distance * 0.052, 0.56, 1.0),
						"target": number,
						"pocket": pocket,
						"pocket_index": pocket_index,
						"bank_point": bank_point,
						"confidence": confidence,
						"position_score": position_quality,
						"score": score,
						"spin": Vector2(0.0, 0.18),
					}
	return best


func plan_safety_shot(cue_position: Vector3, ball_positions: Dictionary, legal_numbers: Array[int]) -> Dictionary:
	var best := {}
	var best_score := -INF
	for number in legal_numbers:
		if not ball_positions.has(number):
			continue
		var target: Vector3 = ball_positions[number]
		var base_direction := _flat(target - cue_position).normalized()
		for side_value in [-1.0, 1.0]:
			var side: float = side_value
			var contact_offset: Vector3 = Vector3(-base_direction.z, 0.0, base_direction.x) * BALL_DIAMETER * 0.42 * side
			var ghost: Vector3 = target - base_direction * BALL_DIAMETER + contact_offset
			if not _corridor_clear(cue_position, ghost, ball_positions, [number]):
				continue
			var direction := _flat(ghost - cue_position).normalized()
			var predicted_cue: Vector3 = ghost + direction * 0.28
			var rail_cover := 1.0 - clampf(_distance_to_nearest_rail(predicted_cue) / 1.2, 0.0, 1.0)
			var blockers := _blocker_count(predicted_cue, target, ball_positions, [number])
			var separation: float = predicted_cue.distance_to(target)
			var score: float = rail_cover * 1.5 + blockers * 0.8 + separation * 0.08
			if score > best_score:
				best_score = score
				best = {
					"shot_type": "SAFETY",
					"direction": direction,
					"power": 0.29,
					"target": number,
					"confidence": 0.24,
					"position_score": clampf(score / 4.0, 0.0, 1.0),
					"score": score,
					"spin": Vector2(0.0, -0.62),
				}
	if best.is_empty():
		best = _fallback_shot(cue_position, ball_positions, legal_numbers)
		best["shot_type"] = "SAFETY"
	return best


func choose_cue_position(ball_positions: Dictionary, legal_numbers: Array[int], pocket_positions: Array[Vector3], kitchen_only: bool = false) -> Vector3:
	var best_position := Vector3(-2.8, 1.077, 0.0)
	var best_score := -INF
	var maximum_x := -2.15 if kitchen_only else 3.7
	for x_step in 9:
		var x := lerpf(-3.75, maximum_x, float(x_step) / 8.0)
		for z_step in 7:
			var z := lerpf(-1.65, 1.65, float(z_step) / 6.0)
			var candidate := Vector3(x, 1.077, z)
			if not _position_clear(candidate, ball_positions):
				continue
			var plan := plan_shot(candidate, ball_positions, legal_numbers, pocket_positions)
			var score := float(plan.get("confidence", 0.0)) + float(plan.get("position_score", 0.0)) * 0.35
			if score > best_score:
				best_score = score
				best_position = candidate
	return best_position


func _bank_point(target: Vector3, pocket: Vector3, rail: Dictionary) -> Vector3:
	var mirrored := pocket
	var axis: String = rail["axis"]
	var rail_value: float = rail["value"]
	if axis == "x":
		mirrored.x = rail_value * 2.0 - pocket.x
		var denominator_x := mirrored.x - target.x
		if absf(denominator_x) < 0.001:
			return Vector3.INF
		var t_x := (rail_value - target.x) / denominator_x
		if t_x <= 0.03 or t_x >= 0.97:
			return Vector3.INF
		var point_x := target.lerp(mirrored, t_x)
		if point_x.z < TABLE_MIN_Z + 0.24 or point_x.z > TABLE_MAX_Z - 0.24:
			return Vector3.INF
		point_x.y = target.y
		return point_x
	mirrored.z = rail_value * 2.0 - pocket.z
	var denominator_z := mirrored.z - target.z
	if absf(denominator_z) < 0.001:
		return Vector3.INF
	var t_z := (rail_value - target.z) / denominator_z
	if t_z <= 0.03 or t_z >= 0.97:
		return Vector3.INF
	var point_z := target.lerp(mirrored, t_z)
	if point_z.x < TABLE_MIN_X + 0.3 or point_z.x > TABLE_MAX_X - 0.3:
		return Vector3.INF
	point_z.y = target.y
	return point_z


func _position_quality(ghost: Vector3, direction: Vector3, ball_positions: Dictionary, legal_numbers: Array[int], current_target: int) -> float:
	var predicted := ghost + direction * 0.55
	var nearest_next := INF
	for number in legal_numbers:
		if number == current_target or not ball_positions.has(number):
			continue
		nearest_next = minf(nearest_next, predicted.distance_to(ball_positions[number]))
	var next_ball_score := 0.45 if nearest_next == INF else 1.0 - clampf(nearest_next / 6.0, 0.0, 1.0)
	var rail_clearance := clampf(_distance_to_nearest_rail(predicted) / 0.75, 0.0, 1.0)
	return next_ball_score * 0.72 + rail_clearance * 0.28


func _position_spin(ghost: Vector3, direction: Vector3, ball_positions: Dictionary, legal_numbers: Array[int], current_target: int) -> Vector2:
	if difficulty != Difficulty.HARD:
		return Vector2.ZERO
	var best_next := Vector3.INF
	var nearest := INF
	for number in legal_numbers:
		if number == current_target or not ball_positions.has(number):
			continue
		var distance: float = ghost.distance_to(ball_positions[number])
		if distance < nearest:
			nearest = distance
			best_next = ball_positions[number]
	if best_next == Vector3.INF:
		return Vector2(0.0, 0.12)
	var to_next := _flat(best_next - ghost).normalized()
	var forward_value := clampf(direction.dot(to_next), -1.0, 1.0)
	var side_value := clampf(direction.cross(to_next).y, -0.45, 0.45)
	return Vector2(side_value, forward_value * 0.55)


func _position_clear(candidate: Vector3, ball_positions: Dictionary) -> bool:
	for number in ball_positions:
		if candidate.distance_to(ball_positions[number]) < BALL_DIAMETER * 1.18:
			return false
	return true


func _corridor_clear(start: Vector3, finish: Vector3, ball_positions: Dictionary, ignored: Array[int]) -> bool:
	var segment := _flat(finish - start)
	var length_squared := segment.length_squared()
	if length_squared < 0.0001:
		return true
	for number in ball_positions:
		if number in ignored:
			continue
		var point: Vector3 = ball_positions[number]
		var along := clampf(_flat(point - start).dot(segment) / length_squared, 0.0, 1.0)
		var nearest := start + segment * along
		if _flat(point - nearest).length() < BALL_DIAMETER * 1.08 and along > 0.04 and along < 0.96:
			return false
	return true


func _blocker_count(start: Vector3, finish: Vector3, ball_positions: Dictionary, ignored: Array[int]) -> int:
	var count := 0
	var segment := _flat(finish - start)
	var length_squared := segment.length_squared()
	if length_squared < 0.001:
		return 0
	for number in ball_positions:
		if number in ignored:
			continue
		var point: Vector3 = ball_positions[number]
		var along := clampf(_flat(point - start).dot(segment) / length_squared, 0.0, 1.0)
		var nearest := start + segment * along
		if _flat(point - nearest).length() < BALL_DIAMETER * 1.35 and along > 0.08 and along < 0.92:
			count += 1
	return count


func _distance_to_nearest_rail(point: Vector3) -> float:
	return minf(minf(point.x - TABLE_MIN_X, TABLE_MAX_X - point.x), minf(point.z - TABLE_MIN_Z, TABLE_MAX_Z - point.z))


func _fallback_shot(cue_position: Vector3, ball_positions: Dictionary, legal_numbers: Array[int]) -> Dictionary:
	var closest_number := -1
	var closest_distance := INF
	for number in legal_numbers:
		if not ball_positions.has(number):
			continue
		var distance: float = cue_position.distance_to(ball_positions[number])
		if distance < closest_distance:
			closest_distance = distance
			closest_number = number
	if closest_number < 0:
		return {"shot_type": "CLEARANCE", "direction": Vector3.RIGHT, "power": 0.35, "target": -1, "confidence": 0.0, "position_score": 0.0}
	var direction := _flat(ball_positions[closest_number] - cue_position).normalized()
	return {
		"shot_type": "CLEARANCE",
		"direction": direction,
		"power": clampf(0.35 + closest_distance * 0.045, 0.38, 0.72),
		"target": closest_number,
		"confidence": 0.18,
		"position_score": 0.0,
		"spin": Vector2.ZERO,
	}


func _apply_difficulty(plan: Dictionary) -> Dictionary:
	var angle_error := 0.0
	var power_error := 0.0
	match difficulty:
		Difficulty.EASY:
			angle_error = deg_to_rad(rng.randf_range(-4.2, 4.2))
			power_error = rng.randf_range(-0.13, 0.12)
		Difficulty.MEDIUM:
			angle_error = deg_to_rad(rng.randf_range(-1.7, 1.7))
			power_error = rng.randf_range(-0.055, 0.05)
		Difficulty.HARD:
			angle_error = deg_to_rad(rng.randf_range(-0.45, 0.45))
			power_error = rng.randf_range(-0.018, 0.018)
	var direction: Vector3 = plan["direction"]
	plan["direction"] = direction.rotated(Vector3.UP, angle_error).normalized()
	plan["power"] = clampf(float(plan["power"]) + power_error, 0.22, 1.0)
	if difficulty == Difficulty.EASY:
		plan["spin"] = Vector2.ZERO
	elif difficulty == Difficulty.MEDIUM:
		plan["spin"] = Vector2(rng.randf_range(-0.12, 0.12), rng.randf_range(-0.06, 0.22))
	elif not plan.has("spin"):
		plan["spin"] = Vector2.ZERO
	return plan


func _flat(vector: Vector3) -> Vector3:
	vector.y = 0.0
	return vector
