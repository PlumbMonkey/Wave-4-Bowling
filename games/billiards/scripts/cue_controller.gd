class_name CueController
extends RefCounted

var spin := Vector2.ZERO


func reset() -> void:
	spin = Vector2.ZERO


func update_spin(input_vector: Vector2, delta: float) -> void:
	if input_vector.length() < 0.08:
		return
	spin += input_vector * delta * 1.15
	if spin.length() > 1.0:
		spin = spin.normalized()


func torque_for_shot(direction: Vector3, power: float) -> Vector3:
	var rolling_axis := Vector3(direction.z, 0.0, -direction.x).normalized()
	var top_or_back := rolling_axis * spin.y * power * 0.085
	var side_english := Vector3.UP * -spin.x * power * 0.072
	return top_or_back + side_english


func strike_label() -> String:
	if spin.length() < 0.12:
		return "CENTER"
	var vertical := "TOP" if spin.y > 0.2 else ("DRAW" if spin.y < -0.2 else "")
	var horizontal := "RIGHT" if spin.x > 0.2 else ("LEFT" if spin.x < -0.2 else "")
	return (vertical + " " + horizontal).strip_edges()
