class_name SpectralBall
extends RigidBody3D

signal impact(position: Vector3, intensity: float, cushion: bool)
signal contacted_ball(other_number: int)

var number := 0
var pocketed := false

const BASE_ROLLING_RESISTANCE := 0.34
const SPEED_ROLLING_RESISTANCE := 0.10
const LOW_SPEED_SPIN_DRAG := 2.8


func configure(ball_number: int) -> void:
	number = ball_number
	mass = 0.17
	gravity_scale = 1.0
	linear_damp = 0.48
	angular_damp = 0.82
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 8
	collision_layer = 1
	collision_mask = 3
	body_entered.connect(_on_body_entered)


func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	if pocketed or state.get_contact_count() == 0:
		return
	var velocity := state.linear_velocity
	var horizontal := Vector3(velocity.x, 0.0, velocity.z)
	var speed := horizontal.length()
	if speed > 0.0:
		var next_speed := rolling_speed_after_step(speed, state.step)
		horizontal *= next_speed / speed
		state.linear_velocity = Vector3(horizontal.x, velocity.y, horizontal.z)
	var spin_drag := LOW_SPEED_SPIN_DRAG if speed < 0.22 else 0.75
	state.angular_velocity = state.angular_velocity.move_toward(Vector3.ZERO, spin_drag * state.step)
	if speed < 0.045 and state.angular_velocity.length() < 0.22:
		state.linear_velocity = Vector3(0.0, velocity.y, 0.0)
		state.angular_velocity = Vector3.ZERO


func rolling_speed_after_step(speed: float, delta: float) -> float:
	var resistance := BASE_ROLLING_RESISTANCE + minf(speed * SPEED_ROLLING_RESISTANCE, 0.72)
	return maxf(speed - resistance * delta, 0.0)


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
