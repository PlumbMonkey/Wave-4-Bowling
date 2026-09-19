class_name ReplayBuffer
extends RefCounted

const PHYSICS_FPS := 60
const MAX_SECONDS := 8.0
const MAX_FRAMES := int(PHYSICS_FPS * MAX_SECONDS)

var frames: Array[Dictionary] = []
var shot_start_index := 0


func clear() -> void:
	frames.clear()
	shot_start_index = 0


func mark_shot_start() -> void:
	shot_start_index = frames.size()


func capture(balls: Array[RigidBody3D]) -> void:
	var frame := {}
	for ball in balls:
		if is_instance_valid(ball):
			frame[ball.get_instance_id()] = {
				"transform": ball.global_transform,
				"visible": ball.visible,
			}
	frames.append(frame)
	if frames.size() > MAX_FRAMES:
		frames.pop_front()
		shot_start_index = maxi(0, shot_start_index - 1)


func get_last_shot() -> Array[Dictionary]:
	if frames.is_empty():
		return []
	return frames.slice(clampi(shot_start_index, 0, frames.size() - 1), frames.size())


func get_recent(seconds: float) -> Array[Dictionary]:
	var count := clampi(int(seconds * PHYSICS_FPS), 1, frames.size())
	return frames.slice(frames.size() - count, frames.size())
