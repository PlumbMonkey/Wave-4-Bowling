class_name SpectralBall
extends RigidBody3D

signal impact(position: Vector3, intensity: float, cushion: bool)
signal contacted_ball(other_number: int)

var number := 0
var pocketed := false


func configure(ball_number: int) -> void:
	number = ball_number
	mass = 0.17
	gravity_scale = 1.0
	linear_damp = 0.34
	angular_damp = 0.42
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 8
	collision_layer = 1
	collision_mask = 3
	body_entered.connect(_on_body_entered)


func _on_body_entered(other: Node) -> void:
	if pocketed:
		return
	var speed := linear_velocity.length()
	if other is SpectralBall:
		if number == 0:
			emit_signal("contacted_ball", other.number)
		if get_instance_id() > other.get_instance_id():
			return
		speed = (linear_velocity - other.linear_velocity).length()
		emit_signal("impact", global_position, speed, false)
	elif "Cushion" in other.name:
		emit_signal("impact", global_position, speed, true)
