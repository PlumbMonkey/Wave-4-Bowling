class_name AimGuide
extends Node3D
## A faint dotted path showing where the throw will go - curved by the spin,
## predicted with the ball's own lane model - with a pulse that travels along
## it at the speed the ball will actually roll.

const SPACING := 0.30          ## metres between dots
const MAX_DOTS := 72
const BASE_ALPHA := 0.30
const PULSE_WIDTH := 0.14      ## seconds
const COLOR := Color("2bf7a3")
## Only the front of the lane is shown - the back end is the bowler's to read.
const SHOW_DIST := 11.0
const FADE_DIST := 4.0

var nominal := OilPattern.house()

var _mm: MultiMesh
var _times := PackedFloat32Array()
var _count := 0
var _pulse := 0.0
var _duration := 1.0
var _strength := 1.0           ## the pulse brightens with power


func _ready() -> void:
	var quad := QuadMesh.new()
	quad.size = Vector2(0.055, 0.055)
	quad.orientation = PlaneMesh.FACE_Y
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.vertex_color_use_as_albedo = true
	m.albedo_texture = _dot_texture()
	m.no_depth_test = false
	quad.material = m
	_mm = MultiMesh.new()
	_mm.transform_format = MultiMesh.TRANSFORM_3D
	_mm.use_colors = true
	_mm.mesh = quad
	_mm.instance_count = MAX_DOTS
	_mm.visible_instance_count = 0
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = _mm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)


static func _dot_texture() -> ImageTexture:
	var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	for y in 32:
		for x in 32:
			var d := Vector2(x - 15.5, y - 15.5).length() / 15.5
			var a := clampf(1.0 - d, 0.0, 1.0)
			img.set_pixel(x, y, Color(1, 1, 1, a * a))
	return ImageTexture.create_from_image(img)


## Re-plot the path for a throw. power 0..1 only sets how bright the pulse is.
func show_throw(x: float, aim: float, speed: float, spin: float, power: float) -> void:
	var pred := BowlingBall.predict(x, aim, speed, spin, nominal, SHOW_DIST)
	var pts: PackedVector3Array = pred[0]
	var tms: PackedFloat32Array = pred[1]
	_times.clear()
	var n := 0
	var carried := 0.0
	for i in range(1, pts.size()):
		var a := pts[i - 1]
		var b := pts[i]
		var seg := a.distance_to(b)
		var d := SPACING - carried
		while d <= seg and n < MAX_DOTS:
			var f := d / seg
			var p := a.lerp(b, f)
			_mm.set_instance_transform(n, Transform3D(Basis.IDENTITY, Vector3(p.x, 0.004, p.z)))
			_times.append(lerpf(tms[i - 1], tms[i], f))
			n += 1
			d += SPACING
		carried = seg - (d - SPACING)
	_count = n
	_mm.visible_instance_count = n
	_duration = (_times[n - 1] if n > 0 else 1.0) + 0.35
	_strength = 0.45 + 0.55 * power


func _process(delta: float) -> void:
	if not visible or _count == 0:
		return
	_pulse = fmod(_pulse + delta, _duration)
	for i in _count:
		var dt := (_times[i] - _pulse) / PULSE_WIDTH
		var glow := exp(-dt * dt) * _strength
		# dots fade out toward the pins so the guide stays out of the way
		var fade := clampf(float(_count - 1 - i) * SPACING / FADE_DIST, 0.0, 1.0)
		_mm.set_instance_color(i, Color(COLOR, (BASE_ALPHA + 1.2 * glow) * fade))
