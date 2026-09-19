class_name TrajectoryGuide
extends Node3D

const MAX_SEGMENTS := 4

var beams: Array[MeshInstance3D] = []


func _ready() -> void:
	for index in MAX_SEGMENTS:
		var beam := MeshInstance3D.new()
		var mesh := CylinderMesh.new()
		mesh.top_radius = 0.013
		mesh.bottom_radius = 0.013
		mesh.height = 1.0
		mesh.radial_segments = 8
		beam.mesh = mesh
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.albedo_color = Color(0.38, 0.91, 1.0, 0.92)
		material.emission_enabled = true
		material.emission = Color(0.22, 0.82, 1.0)
		material.emission_energy_multiplier = 2.8
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		beam.material_override = material
		beam.visible = false
		add_child(beam)
		beams.append(beam)


func show_segments(segments: Array) -> void:
	visible = true
	for index in beams.size():
		if index >= segments.size():
			beams[index].visible = false
			continue
		var segment: PackedVector3Array = segments[index]
		if segment.size() < 2:
			beams[index].visible = false
			continue
		_set_beam(beams[index], segment[0], segment[1])


func hide_guide() -> void:
	visible = false
	for beam in beams:
		beam.visible = false


func _set_beam(beam: MeshInstance3D, start: Vector3, finish: Vector3) -> void:
	var delta := finish - start
	var length := delta.length()
	if length < 0.02:
		beam.visible = false
		return
	beam.visible = true
	var y_axis := delta / length
	var x_axis := y_axis.cross(Vector3.UP)
	if x_axis.length_squared() < 0.001:
		x_axis = Vector3.RIGHT
	else:
		x_axis = x_axis.normalized()
	var z_axis := x_axis.cross(y_axis).normalized()
	beam.global_transform = Transform3D(Basis(x_axis, y_axis, z_axis), start.lerp(finish, 0.5))
	beam.scale = Vector3(1.0, length, 1.0)
