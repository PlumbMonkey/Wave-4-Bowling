class_name Alley
extends Node3D
## Grey-box alley: approach, lane, gutters, pin deck, kickbacks, pit and
## masking unit, at regulation size. Phase 2 swaps the visuals for the Blender
## alleys but keeps these colliders.

var lane_material: PhysicsMaterial
var gutter_material: PhysicsMaterial


func _ready() -> void:
	lane_material = PhysicsMaterial.new()
	lane_material.friction = 0.4          # for the pins; the ball's own friction is 0
	lane_material.bounce = 0.1
	gutter_material = PhysicsMaterial.new()
	gutter_material.friction = 0.6
	gutter_material.bounce = 0.05

	var lane_len := -BowlingSpec.DECK_END
	var gx := BowlingSpec.LANE_HALF + BowlingSpec.GUTTER_W
	var wood := Color(0.62, 0.52, 0.40)
	var dark := Color(0.12, 0.11, 0.12)

	# lane + pin deck (one slab, top at y = 0)
	_slab("Lane", Vector3(BowlingSpec.LANE_HALF * 2.0, 0.1, lane_len), Vector3(0, -0.05, -lane_len * 0.5),
		wood, lane_material, 0.15)
	_slab("Approach", Vector3(gx * 2.0 + 0.4, 0.1, BowlingSpec.APPROACH), Vector3(0, -0.05, BowlingSpec.APPROACH * 0.5),
		Color(0.5, 0.42, 0.33), lane_material, 0.3)
	for side in [-1.0, 1.0]:
		var cx: float = side * (BowlingSpec.LANE_HALF + BowlingSpec.GUTTER_W * 0.5)
		_slab("Gutter", Vector3(BowlingSpec.GUTTER_W, 0.1, lane_len), Vector3(cx, -BowlingSpec.GUTTER_DROP - 0.05, -lane_len * 0.5),
			dark, gutter_material, 0.6)
		# capping between this lane and the next
		_slab("Capping", Vector3(0.12, 0.2, lane_len), Vector3(side * (gx + 0.06), 0.0, -lane_len * 0.5),
			Color(0.2, 0.12, 0.1), gutter_material, 0.4)
		# kickback plates either side of the deck
		_slab("Kickback", Vector3(0.05, 0.9, 3.2), Vector3(side * (gx + 0.025), 0.3, -BowlingSpec.LANE_LEN - 0.5),
			Color(0.08, 0.07, 0.08), gutter_material, 0.5)
	# the pit, its back cushion, and the masking unit over the deck
	_slab("PitFloor", Vector3(gx * 2.0, 0.1, BowlingSpec.DECK_END - BowlingSpec.PIT_END), Vector3(0, -0.35, (BowlingSpec.DECK_END + BowlingSpec.PIT_END) * 0.5),
		dark, gutter_material, 0.8)
	var cushion := PhysicsMaterial.new()
	cushion.friction = 0.8
	cushion.bounce = 0.0
	_slab("Cushion", Vector3(gx * 2.0, 1.2, 0.2), Vector3(0, 0.2, BowlingSpec.PIT_END), Color(0.05, 0.04, 0.05), cushion, 0.9)
	_visual("Masking", Vector3(gx * 2.0 + 0.3, 0.7, 0.3), Vector3(0, 1.25, BowlingSpec.DECK_END + 0.1), Color(0.18, 0.05, 0.25))

	# lane markings: foul line, approach dots, target arrows, the oil line
	_visual("FoulLine", Vector3(BowlingSpec.LANE_HALF * 2.0, 0.002, 0.02), Vector3(0, 0.001, 0), Color(0.05, 0.05, 0.05))
	for b in [5, 10, 15, 20, 25, 30, 35]:
		var x := BowlingSpec.board_x(b)
		var z := -4.6 - absf(20.0 - b) / 5.0 * 0.3            # the arrows form a V
		var arrow := _visual("Arrow", Vector3(0.02, 0.002, 0.14), Vector3(x, 0.001, z), Color(0.15, 0.05, 0.05))
		arrow.rotation.y = 0.0
	for b in [3, 5, 8, 11, 14, 20, 26, 29, 32, 35, 37]:
		_visual("Dot", Vector3(0.02, 0.002, 0.02), Vector3(BowlingSpec.board_x(b), 0.001, 0.9), Color(0.1, 0.1, 0.1))

	# grey-box room so the camera has something around it
	_visual("Floor", Vector3(8.0, 0.1, 30.0), Vector3(0, -0.45, -8.0), Color(0.07, 0.06, 0.08))
	for side in [-1.0, 1.0]:
		_visual("Wall", Vector3(0.2, 5.0, 30.0), Vector3(side * 3.2, 2.0, -8.0), Color(0.16, 0.13, 0.18))
	_visual("BackWall", Vector3(8.0, 5.0, 0.2), Vector3(0, 2.0, BowlingSpec.PIT_END - 0.3), Color(0.1, 0.06, 0.14))


## Hide (or show) the grey-box meshes. The colliders always stay.
func show_greybox(on: bool) -> void:
	for mi in find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).visible = on


func _material(color: Color, roughness: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = roughness
	return m


func _visual(n: String, size: Vector3, pos: Vector3, color: Color, roughness := 0.6) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = n
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _material(color, roughness)
	mi.mesh = bm
	mi.position = pos
	add_child(mi, true)
	return mi


func _slab(n: String, size: Vector3, pos: Vector3, color: Color, pm: PhysicsMaterial, roughness: float) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = n
	body.physics_material_override = pm
	body.position = pos
	var shape := BoxShape3D.new()
	shape.size = size
	var cs := CollisionShape3D.new()
	cs.shape = shape
	body.add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _material(color, roughness)
	mi.mesh = bm
	body.add_child(mi)
	add_child(body, true)
	return body
