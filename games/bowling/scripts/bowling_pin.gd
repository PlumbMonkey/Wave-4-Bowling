class_name BowlingPin
extends RigidBody3D
## A regulation pin: 15" tall, 1.58 kg, centre of mass low in the belly.
## The grey-box mesh is a lathe of the USBC profile; the collider is its convex
## hull (the neck concavity is filled, which is fine - pins meet at the belly).

## (radius, height) up the pin, in metres
const PROFILE := [
	Vector2(0.0, 0.0), Vector2(0.0258, 0.0), Vector2(0.0365, 0.019), Vector2(0.0500, 0.057),
	Vector2(0.0605, 0.114), Vector2(0.0565, 0.165), Vector2(0.0435, 0.210), Vector2(0.0327, 0.234),
	Vector2(0.03045, 0.239), Vector2(0.0277, 0.247), Vector2(0.0254, 0.254), Vector2(0.0228, 0.262),
	Vector2(0.0240, 0.292), Vector2(0.0300, 0.330), Vector2(0.0318, 0.346),
	Vector2(0.0280, 0.365), Vector2(0.0160, 0.378), Vector2(0.0, 0.381),
]
const SIDES := 16
## the two red stripes sit on the narrow neck
const STRIPES := [Vector2(0.239, 0.247), Vector2(0.254, 0.262)]
const FALLEN_TILT := deg_to_rad(40.0)

static var _mesh: ArrayMesh
static var _shape: ConvexPolygonShape3D
static var _material: PhysicsMaterial

var spot: Vector3          ## where this pin was set
var _mi: MeshInstance3D

## Pin sets. Every set shares the regulation collider and mass, so the choice is
## purely visual - the bone set plays exactly like the classic one.
const STYLES := {
	"classic": {"name": "Classic", "glb": ""},
	"bone": {"name": "Bone", "glb": "res://art/pins/bone.glb"},
	"reliquary": {"name": "Reliquary", "glb": "res://art/pins/reliquary.glb"},
}
## the order D-pad up / P cycles through
const STYLE_ORDER := ["classic", "bone", "reliquary"]
static var style := "classic"
static var _style_meshes := {}


func _init() -> void:
	_build_shared()
	mass = BowlingSpec.PIN_MASS
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0.0, BowlingSpec.PIN_COM, 0.0)
	physics_material_override = _material
	continuous_cd = true
	_mi = MeshInstance3D.new()
	_mi.mesh = style_mesh(style)
	add_child(_mi)
	var cs := CollisionShape3D.new()
	cs.shape = _shape
	add_child(cs)


static func _build_shared() -> void:
	if _mesh:
		return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var hull := PackedVector3Array()
	for i in PROFILE.size() - 1:
		var a: Vector2 = PROFILE[i]
		var b: Vector2 = PROFILE[i + 1]
		# the red neck stripes, painted by height
		var red := false
		for sb in STRIPES:
			if a.y >= sb.x - 0.0001 and b.y <= sb.y + 0.0001:
				red = true
		var col := Color(0.75, 0.05, 0.06) if red else Color(0.93, 0.92, 0.88)
		st.set_color(col)
		# the flat foot shades on its own; everything else is smooth
		st.set_smooth_group(0xFFFFFFFF if i == 0 else 0)
		for s in SIDES:
			var t0 := TAU * s / SIDES
			var t1 := TAU * (s + 1) / SIDES
			var p00 := Vector3(a.x * cos(t0), a.y, a.x * sin(t0))
			var p01 := Vector3(a.x * cos(t1), a.y, a.x * sin(t1))
			var p10 := Vector3(b.x * cos(t0), b.y, b.x * sin(t0))
			var p11 := Vector3(b.x * cos(t1), b.y, b.x * sin(t1))
			st.add_vertex(p00); st.add_vertex(p10); st.add_vertex(p11)
			st.add_vertex(p00); st.add_vertex(p11); st.add_vertex(p01)
	for p in PROFILE:
		for s in 12:
			var t := TAU * s / 12
			hull.append(Vector3(p.x * cos(t), p.y, p.x * sin(t)))
	st.generate_normals()
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.25
	st.set_material(mat)
	_mesh = st.commit()
	_shape = ConvexPolygonShape3D.new()
	_shape.points = hull
	_material = PhysicsMaterial.new()
	_material.friction = 0.35
	_material.bounce = 0.45


## Every mesh in a pin set. A set can have several designs (the Reliquary has
## four); pins take them in turn across the rack. Falls back to classic.
static func style_meshes(s: String) -> Array:
	_build_shared()
	if s == "classic" or not STYLES.has(s):
		return [_mesh]
	if not _style_meshes.has(s):
		var list := []
		var path: String = STYLES[s].glb
		if ResourceLoader.exists(path):
			var scene: Node = (load(path) as PackedScene).instantiate()
			var found := scene.find_children("*", "MeshInstance3D", true, false)
			found.sort_custom(func(a, b): return String(a.name) < String(b.name))
			for mi in found:
				list.append((mi as MeshInstance3D).mesh)
			scene.free()
		_style_meshes[s] = list if not list.is_empty() else [_mesh]
	return _style_meshes[s]


## The mesh for the index-th pin of the rack.
static func style_mesh(s: String, index := 0) -> Mesh:
	var list := style_meshes(s)
	return list[index % list.size()]


## Switch every pin to a set.
static func set_style(s: String, pins: Array) -> void:
	style = s if STYLES.has(s) else "classic"
	for i in pins.size():
		(pins[i] as BowlingPin)._mi.mesh = style_mesh(style, i)


func is_down() -> bool:
	var up := global_transform.basis.y.normalized()
	if up.dot(Vector3.UP) < cos(FALLEN_TILT):
		return true
	var p := global_position
	# off the deck: in the pit, the gutter or knocked sideways onto the kickbacks
	return p.y < -0.03 or p.z < BowlingSpec.DECK_END or absf(p.x) > BowlingSpec.LANE_HALF


func is_settled() -> bool:
	return sleeping or (linear_velocity.length() < 0.03 and angular_velocity.length() < 0.25)


## Stand the pin back up at *pos* (the pinsetter respot).
func set_at(pos: Vector3) -> void:
	process_mode = Node.PROCESS_MODE_INHERIT
	freeze = true
	global_transform = Transform3D(Basis.IDENTITY, pos)
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	freeze = false
	visible = true


## Sweep the pin away (deadwood) until the next full rack.
func sweep() -> void:
	freeze = true
	visible = false
	global_position = Vector3(0.0, -5.0, BowlingSpec.PIT_END - 2.0)
	process_mode = Node.PROCESS_MODE_DISABLED


func in_play() -> bool:
	return visible
