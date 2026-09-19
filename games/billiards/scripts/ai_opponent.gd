class_name BilliardsAI
extends RefCounted

enum Difficulty { EASY, MEDIUM, HARD }

const BALL_DIAMETER := 0.29

var difficulty := Difficulty.MEDIUM
var rng := RandomNumberGenerator.new()


func _init() -> void:
	rng.seed = 0x5EC7A1


func configure(level: Difficulty) -> void:
	difficulty = level


func plan_shot(cue_position: Vector3, ball_positions: Dictionary, legal_numbers: Array[int], pocket_positions: Array[Vector3]) -> Dictionary:
	var best := {}
	var best_score := -INF
	for number in legal_numbers:
		if not ball_positions.has(number):
			continue
		var target: Vector3 = ball_positions[number]
		for pocket in pocket_positions:
			var target_to_pocket := pocket - target
			target_to_pocket.y = 0.0
			if target_to_pocket.length() < 0.01:
				continue
			var pocket_direction := target_to_pocket.normalized()
			var ghost := target - pocket_direction * BALL_DIAMETER
			var cue_path := ghost - cue_position
			cue_path.y = 0.0
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
			var score := alignment * 4.0 - distance * 0.22
			if number == 8:
				score += 2.0
			if score > best_score:
				best_score = score
				best = {
					"direction": cue_direction,
					"power": clampf(0.28 + distance * 0.065, 0.34, 0.92),
					"target": number,
					"pocket": pocket,
					"confidence": clampf((alignment + 1.0) * 0.5 - distance * 0.025, 0.0, 1.0),
				}

	if best.is_empty():
		best = _fallback_shot(cue_position, ball_positions, legal_numbers)
	return _apply_difficulty(best)


func _corridor_clear(start: Vector3, finish: Vector3, ball_positions: Dictionary, ignored: Array[int]) -> bool:
	var segment := finish - start
	segment.y = 0.0
	var length_squared := segment.length_squared()
	if length_squared < 0.0001:
		return true
	for number in ball_positions:
		if number in ignored:
			continue
		var point: Vector3 = ball_positions[number]
		var along := clampf((point - start).dot(segment) / length_squared, 0.0, 1.0)
		var nearest := start + segment * along
		if point.distance_to(nearest) < BALL_DIAMETER * 1.08 and along > 0.04 and along < 0.96:
			return false
	return true


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
		return {"direction": Vector3.RIGHT, "power": 0.35, "target": -1, "confidence": 0.0}
	var direction: Vector3 = ball_positions[closest_number] - cue_position
	direction.y = 0.0
	return {
		"direction": direction.normalized(),
		"power": clampf(0.35 + closest_distance * 0.045, 0.38, 0.72),
		"target": closest_number,
		"confidence": 0.18,
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
	direction = direction.rotated(Vector3.UP, angle_error).normalized()
	plan["direction"] = direction
	plan["power"] = clampf(float(plan["power"]) + power_error, 0.22, 1.0)
	return plan
