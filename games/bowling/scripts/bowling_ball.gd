class_name BowlingBall
extends RigidBody3D
## The ball, with its own lane-friction model.
##
## The lane surface has zero friction for Jolt; this script applies sliding
## friction at the contact patch instead, with the coefficient taken from the
## oil pattern. That gives the real three phases for free: the ball skids
## through the oil, hooks when it reaches the dry back end, then rolls out.
##
##   contact velocity  vc = v + w x (0, -R, 0)
##   friction          F  = -mu(z) * m * g * vc / |vc|   (while vc > SLIP_EPS)
##   torque            T  = (0, -R, 0) x F

const R := BowlingSpec.BALL_R
const SLIP_EPS := 0.05

var released := false
var in_gutter := false
## -1..1 from the bumpers while rolling: positive hooks right (+x)
var spin_input := 0.0
## -1..1 from the left stick while rolling: a gentle sideways nudge (+x = right)
var steer_input := 0.0

static var _material: PhysicsMaterial
## The lane's oil pattern - the game swaps in a fresh one each game.
static var pattern := OilPattern.house()

const SKINS := {
	"spectre": {"name": "The Spectre", "glb": "res://art/balls/spectre.glb"},
	"p": {"name": "The P", "glb": "res://art/balls/p.glb"},
	"skull": {"name": "The Skull", "glb": "res://art/balls/skull.glb"},
}

var skin := ""
var _greybox: Array[Node] = []


func _init() -> void:
	if not _material:
		_material = PhysicsMaterial.new()
		_material.friction = 0.0          # the lane model below owns friction
		_material.bounce = 0.05
	mass = BowlingSpec.BALL_MASS
	physics_material_override = _material
	continuous_cd = true
	can_sleep = false
	# no engine damping - the lane model owns every loss of speed and spin
	# (Godot's default 0.1 damping cost ~25% of the speed by the pins)
	linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	linear_damp = 0.0
	angular_damp = 0.0
	var sphere := SphereShape3D.new()
	sphere.radius = R
	var cs := CollisionShape3D.new()
	cs.shape = sphere
	add_child(cs)

	var mesh := SphereMesh.new()
	mesh.radius = R
	mesh.height = R * 2.0
	mesh.radial_segments = 48
	mesh.rings = 24
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.22, 0.08, 0.38)
	mat.roughness = 0.12
	mat.metallic = 0.2
	mat.emission_enabled = true
	mat.emission = Color(0.35, 0.12, 0.6)
	mat.emission_energy_multiplier = 0.35
	mesh.material = mat
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	add_child(mi)
	_greybox.append(mi)
	# finger holes so the rotation reads
	var hole := SphereMesh.new()
	hole.radius = 0.014
	hole.height = 0.028
	var hm := StandardMaterial3D.new()
	hm.albedo_color = Color(0.02, 0.02, 0.02)
	hole.material = hm
	for p in [Vector3(-0.025, 0.1, 0.03), Vector3(0.025, 0.1, 0.03), Vector3(0.0, 0.098, -0.045)]:
		var h := MeshInstance3D.new()
		h.mesh = hole
		h.position = p
		add_child(h)
		_greybox.append(h)


## Swap the look of the ball (physics is unchanged). Returns the display name.
func set_skin(kind: String) -> String:
	var old := get_node_or_null("Skin")
	if old:
		old.queue_free()
		remove_child(old)
	if not SKINS.has(kind) or not ResourceLoader.exists(SKINS[kind].glb):
		for g in _greybox:
			(g as Node3D).visible = true
		skin = ""
		return "House ball"
	var s: Node3D = (load(SKINS[kind].glb) as PackedScene).instantiate()
	s.name = "Skin"
	add_child(s)
	for g in _greybox:
		(g as Node3D).visible = false
	skin = kind
	return SKINS[kind].name


## Launch the ball from the foul line.
func launch(x: float, aim: float, speed: float, spin: float) -> void:
	freeze = false
	released = true
	in_gutter = false
	spin_input = 0.0
	steer_input = 0.0
	var st := launch_state(x, aim, speed, spin)
	global_transform = Transform3D(Basis.IDENTITY, st[0] + Vector3(0.0, 0.002, 0.0))
	linear_velocity = st[1]
	angular_velocity = st[2]


## Hold the ball in the bowler's hand before the throw.
func hold(pos: Vector3) -> void:
	freeze = true
	released = false
	global_transform = Transform3D(Basis.IDENTITY, pos)
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO




static func on_lane_at(p: Vector3) -> bool:
	return absf(p.x) < BowlingSpec.LANE_HALF and p.y < R + 0.015 		and p.z > BowlingSpec.DECK_END and p.z < 0.5


func on_lane() -> bool:
	return on_lane_at(global_position)


## The lane model, shared by the real ball and the aim guide's prediction.
## Returns [force, torque] for a ball at p with velocity v and spin w.
static func lane_forces(p: Vector3, v: Vector3, w: Vector3, m: float,
		spin_in := 0.0, steer_in := 0.0, pat: OilPattern = null) -> Array:
	if pat == null:
		pat = pattern
	var force := Vector3.ZERO
	var torque := Vector3.ZERO
	var n := m * 9.81
	var rc := Vector3(0.0, -R, 0.0)
	var vc := v + w.cross(rc)
	vc.y = 0.0
	var slip := vc.length()
	if slip > SLIP_EPS:
		var f := -vc / slip * pat.mu(p) * n
		force += f
		torque += rc.cross(f)
	elif v.length() > 0.05:
		force += -v.normalized() * BowlingSpec.MU_ROLL * n
	if spin_in != 0.0:
		torque += Vector3(0.0, 0.0, -spin_in * BowlingSpec.SPIN_TORQUE)
	# "body English": a subtle nudge, fading out before the pins
	if steer_in != 0.0 and p.z > -BowlingSpec.LANE_LEN + BowlingSpec.STEER_STOP:
		force += Vector3(steer_in * BowlingSpec.STEER_ACCEL * m, 0.0, 0.0)
	return [force, torque]


static func launch_state(x: float, aim: float, speed: float, spin: float) -> Array:
	var dir := Vector3(sin(aim), 0.0, -cos(aim))
	var v := dir * speed
	# some forward roll, plus side rotation for the hook (positive spin hooks right)
	var w := Vector3(dir.z * speed / R * 0.25, 0.0, -spin * BowlingSpec.REV_SIDE)
	return [Vector3(x, R, -0.05), v, w]


## Where a throw will go with no further input: [points, times] down to the
## head pin (or the gutter). Same equations as the real ball.
static func predict(x: float, aim: float, speed: float, spin: float,
		pat: OilPattern = null, max_dist := 99.0) -> Array:
	var st := launch_state(x, aim, speed, spin)
	var p: Vector3 = st[0]
	var v: Vector3 = st[1]
	var w: Vector3 = st[2]
	var m := BowlingSpec.BALL_MASS
	var inv_i := 1.0 / (0.4 * m * R * R)
	var dt := 1.0 / 120.0
	var pts := PackedVector3Array([p])
	var times := PackedFloat32Array([0.0])
	var t := 0.0
	while t < 6.0 and p.z > -minf(BowlingSpec.LANE_LEN, max_dist) and absf(p.x) < BowlingSpec.LANE_HALF:
		var ft: Array = lane_forces(p, v, w, m, 0.0, 0.0, pat)
		v += ft[0] / m * dt
		w += ft[1] * inv_i * dt
		p += v * dt
		p.y = R
		t += dt
		if int(t * 120.0) % 6 == 0:
			pts.append(p)
			times.append(t)
	pts.append(p)
	times.append(t)
	return [pts, times]


func _integrate_forces(s: PhysicsDirectBodyState3D) -> void:
	if not released:
		return
	var p := s.transform.origin
	# only a gutter ball if it leaves the lane before reaching the pins
	if absf(p.x) > BowlingSpec.LANE_HALF + R * 0.25 and p.z > -BowlingSpec.LANE_LEN + 0.3:
		in_gutter = true
	if in_gutter or not on_lane_at(p):
		return
	var ft: Array = lane_forces(p, s.linear_velocity, s.angular_velocity, mass, spin_input, steer_input)
	s.apply_central_force(ft[0])
	s.apply_torque(ft[1])
