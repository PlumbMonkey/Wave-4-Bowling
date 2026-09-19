class_name AimGuide
extends Node3D

var dots: Array[MeshInstance3D] = []
var phase := 0.0


func _ready() -> void:
	for index in 18:
		var dot := MeshInstance3D.new()
		var mesh := SphereMesh.new()
		mesh.radius = 0.027
		mesh.height = 0.054
		mesh.radial_segments = 8
		mesh.rings = 4
		dot.mesh = mesh
		var material := StandardMaterial3D.new()
		material.albedo_color = Color(0.55, 1.0, 0.86, 0.9)
		material.emission_enabled = true
		material.emission = Color(0.15, 0.9, 0.65)
		material.emission_energy_multiplier = 1.8
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		dot.material_override = material
		add_child(dot)
		dots.append(dot)


func update_guide(origin: Vector3, direction: Vector3, max_distance: float, delta: float) -> void:
	global_position = Vector3.ZERO
	phase = fmod(phase + delta * 0.75, 0.25)
	for index in dots.size():
		var distance := phase + 0.24 + index * 0.25
		dots[index].visible = distance <= max_distance
		dots[index].global_position = origin + direction * distance + Vector3.UP * 0.012
