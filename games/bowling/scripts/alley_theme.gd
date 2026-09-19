class_name AlleyTheme
extends Node3D
## Dresses the grey-box alley with a Blender-built alley (res://art/alleys/<id>.glb).
##
## The GLB carries the visuals plus LGT_* marker nodes; this turns each marker
## into a light by its prefix, sets the Desktop-profile environment, and makes
## the candles flicker. Physics stays on the grey-box colliders in alley.gd.

const ALLEYS := {
	"lounge": {"name": "The Spectral Lounge", "glb": "res://art/alleys/lounge.glb"},
}

## prefix -> [type, colour, energy, range, shadow, volumetric]
const LIGHTS := {
	"Chandelier": ["omni", Color(1.0, 0.66, 0.36), 2.6, 9.0, true, 0.6],
	"Candle": ["omni", Color(1.0, 0.58, 0.28), 0.9, 3.2, false, 0.0],
	"Lantern": ["omni", Color(1.0, 0.6, 0.3), 0.6, 2.0, false, 0.0],
	"Mask": ["omni", Color(0.62, 0.36, 1.0), 1.4, 2.8, false, 0.4],
	"Pit": ["omni", Color(0.58, 0.30, 1.0), 1.0, 1.6, false, 0.0],
	"PinSpot": ["spot", Color(0.92, 0.88, 1.0), 4.0, 5.0, false, 1.0],
	"Window": ["omni", Color(0.45, 0.42, 1.0), 2.2, 7.0, false, 0.8],
	"Orb": ["omni", Color(0.6, 0.25, 1.0), 1.2, 2.2, false, 0.0],
	"Approach": ["omni", Color(1.0, 0.70, 0.45), 1.8, 7.0, true, 0.3],
}

var id := ""
var profile := GraphicsProfile.DESKTOP
var _flicker: Array = []        # [light, base_energy, phase]
var _t := 0.0


static func exists(alley_id: String) -> bool:
	return ALLEYS.has(alley_id) and ResourceLoader.exists(ALLEYS[alley_id].glb)


## Build the themed alley under *parent*. Returns null when the art is missing,
## so the game falls back to the grey box.
static func create(parent: Node, alley_id: String, env: Environment,
		profile := GraphicsProfile.DESKTOP) -> AlleyTheme:
	if not exists(alley_id):
		return null
	var t := AlleyTheme.new()
	t.name = "AlleyTheme"
	t.id = alley_id
	t.profile = profile
	parent.add_child(t)
	var art: Node3D = (load(ALLEYS[alley_id].glb) as PackedScene).instantiate()
	art.name = "Art"
	t.add_child(art)
	t._spawn_lights(art)
	t._environment(env)
	return t


## Swap the set pins standing on the other four lanes to match.
func set_pin_style(s: String) -> void:
	var art := get_node_or_null("Art")
	if art == null:
		return
	for n in ["BWL_SetPins", "BWL_SetPinStripes"]:
		var node := art.find_child(n, true, false)
		if node:
			(node as Node3D).visible = s == "classic"
	for old in get_children():
		if String(old.name).begins_with("StyledSetPins"):
			old.queue_free()
	if s == "classic":
		return
	# one MultiMesh per design; pins take the designs in turn, as on your lane
	var meshes := BowlingPin.style_meshes(s)
	var spots := BowlingSpec.pin_spots()
	var pitch := 2.0 * (BowlingSpec.LANE_HALF + BowlingSpec.GUTTER_W + 0.12)
	for v in meshes.size():
		var xforms: Array[Transform3D] = []
		for lane in [-2, -1, 1, 2]:
			for i in spots.size():
				if i % meshes.size() == v:
					xforms.append(Transform3D(Basis.IDENTITY, spots[i] + Vector3(lane * pitch, 0, 0)))
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = meshes[v]
		mm.instance_count = xforms.size()
		for k in xforms.size():
			mm.set_instance_transform(k, xforms[k])
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "StyledSetPins%d" % v
		mmi.multimesh = mm
		add_child(mmi)


func display_name() -> String:
	return ALLEYS[id].name


func _spawn_lights(art: Node) -> void:
	var markers: Array[Node] = art.find_children("LGT_*", "", true, false)
	for m in markers:
		var kind := String(m.name).split("_")[1]
		if not LIGHTS.has(kind) or not GraphicsProfile.wants_light(profile, kind):
			continue
		var cfg: Array = LIGHTS[kind]
		var light: Light3D
		if cfg[0] == "spot":
			var s := SpotLight3D.new()
			s.spot_range = cfg[3]
			s.spot_angle = 28.0
			s.spot_angle_attenuation = 0.6
			light = s
		else:
			var o := OmniLight3D.new()
			o.omni_range = cfg[3]
			o.omni_attenuation = 1.4
			light = o
		light.name = "L_" + String(m.name)
		light.light_color = cfg[1]
		light.light_energy = cfg[2]
		light.shadow_enabled = cfg[4]
		light.light_volumetric_fog_energy = cfg[5]
		light.light_specular = 0.35 if kind == "Candle" else 0.8
		add_child(light)
		light.global_position = (m as Node3D).global_position
		if kind == "PinSpot":
			var p := light.global_position
			light.look_at(Vector3(p.x, 0.1, -18.75))
			# the playable lane gets the brightest, shadowed spot
			if absf(p.x) < 0.1:
				light.light_energy = 6.0
				light.shadow_enabled = true
		light.shadow_enabled = GraphicsProfile.wants_shadow(profile, kind,
			kind == "PinSpot" and absf(light.global_position.x) < 0.1, light.shadow_enabled)
		if kind == "Candle" or kind == "Lantern":
			_flicker.append([light, light.light_energy, randf() * 100.0])


func _environment(env: Environment) -> void:
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.01, 0.006, 0.02)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.38, 0.30, 0.52)
	env.ambient_light_energy = 0.22
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.1
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 0.9
	# Desktop profile (PRD phase 4): SSR for the lane, SSAO/SSIL, volumetric fog
	env.ssr_enabled = true
	env.ssr_max_steps = 96
	env.ssr_fade_in = 0.1
	env.ssr_fade_out = 2.5
	env.ssao_enabled = true
	env.ssil_enabled = true
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.010
	env.volumetric_fog_albedo = Color(0.72, 0.62, 0.92)
	env.volumetric_fog_anisotropy = 0.45
	env.volumetric_fog_length = 40.0


func _process(delta: float) -> void:
	_t += delta
	for f in _flicker:
		var ph: float = f[2]
		var n := sin(_t * 9.1 + ph) * 0.5 + sin(_t * 23.7 + ph * 1.7) * 0.3 + sin(_t * 3.3 + ph) * 0.2
		(f[0] as Light3D).light_energy = f[1] * (0.86 + 0.14 * n)
