class_name ManorAudio
extends Node3D

const IMPACT_POOL_SIZE := 12
const BUS_NAME := "Manor Table"

var impact_players: Array[AudioStreamPlayer3D] = []
var impact_cursor := 0
var roll_player: AudioStreamPlayer3D
var replay_player: AudioStreamPlayer
var resin_stream: AudioStreamWAV
var cushion_stream: AudioStreamWAV
var roll_stream: AudioStreamWAV
var replay_stream: AudioStreamWAV
var bus_index := -1
var master_level := 0.85
var replay_mix_active := false


func configure(level: float) -> void:
	master_level = clampf(level, 0.0, 1.0)
	_ensure_audio_bus()
	resin_stream = _make_impact_stream(0.075, 1680.0, 0.31, 0.48)
	cushion_stream = _make_impact_stream(0.13, 215.0, 0.58, 0.56)
	roll_stream = _make_roll_stream()
	replay_stream = _make_replay_stream()
	for index in IMPACT_POOL_SIZE:
		var player := AudioStreamPlayer3D.new()
		player.name = "Impact%02d" % index
		player.bus = BUS_NAME
		player.max_distance = 18.0
		player.unit_size = 2.2
		add_child(player)
		impact_players.append(player)
	roll_player = AudioStreamPlayer3D.new()
	roll_player.name = "ClothRoll"
	roll_player.bus = BUS_NAME
	roll_player.stream = roll_stream
	roll_player.max_distance = 16.0
	roll_player.unit_size = 3.0
	roll_player.volume_db = -60.0
	add_child(roll_player)
	replay_player = AudioStreamPlayer.new()
	replay_player.name = "ReplayRumble"
	replay_player.stream = replay_stream
	replay_player.bus = BUS_NAME
	replay_player.volume_db = -15.0
	add_child(replay_player)
	set_master_level(master_level)
	if DisplayServer.get_name() != "headless":
		roll_player.play()


func set_master_level(level: float) -> void:
	master_level = clampf(level, 0.0, 1.0)
	if bus_index >= 0:
		AudioServer.set_bus_mute(bus_index, master_level <= 0.001)
		AudioServer.set_bus_volume_db(bus_index, linear_to_db(maxf(master_level, 0.001)))


func play_impact(hit_position: Vector3, intensity: float, cushion: bool) -> void:
	if DisplayServer.get_name() == "headless" or intensity < 0.08 or replay_mix_active or impact_players.is_empty():
		return
	var player := impact_players[impact_cursor]
	impact_cursor = (impact_cursor + 1) % impact_players.size()
	player.stop()
	player.stream = cushion_stream if cushion else resin_stream
	player.global_position = hit_position
	player.volume_db = impact_volume_db(intensity, cushion)
	player.pitch_scale = impact_pitch(intensity, cushion)
	player.play()


func update_roll(balls: Array[RigidBody3D], active: bool) -> void:
	if roll_player == null:
		return
	if not active or replay_mix_active:
		roll_player.volume_db = move_toward(roll_player.volume_db, -60.0, 3.0)
		return
	var speed_sum := 0.0
	var weighted_position := Vector3.ZERO
	for ball in balls:
		if not is_instance_valid(ball) or bool(ball.get("pocketed")):
			continue
		var speed := ball.linear_velocity.length()
		if speed < 0.025:
			continue
		speed_sum += speed
		weighted_position += ball.global_position * speed
	if speed_sum <= 0.025:
		roll_player.volume_db = move_toward(roll_player.volume_db, -60.0, 2.2)
		return
	roll_player.global_position = weighted_position / speed_sum
	var target_db := linear_to_db(roll_level(speed_sum))
	roll_player.volume_db = move_toward(roll_player.volume_db, target_db, 2.6)
	roll_player.pitch_scale = clampf(0.72 + speed_sum * 0.055, 0.72, 1.18)


func begin_replay_mix() -> void:
	replay_mix_active = true
	roll_player.volume_db = -60.0
	if bus_index >= 0:
		AudioServer.set_bus_effect_enabled(bus_index, 1, true)
	if DisplayServer.get_name() != "headless":
		replay_player.play()


func end_replay_mix() -> void:
	replay_mix_active = false
	if replay_player != null:
		replay_player.stop()
	if bus_index >= 0:
		AudioServer.set_bus_effect_enabled(bus_index, 1, false)


func impact_volume_db(intensity: float, cushion: bool) -> float:
	var divisor := 4.8 if cushion else 4.0
	return clampf(linear_to_db(clampf(intensity / divisor, 0.012, 1.0)), -32.0, 0.0)


func impact_pitch(intensity: float, cushion: bool) -> float:
	var base := 0.72 if cushion else 0.88
	return clampf(base + intensity * (0.055 if cushion else 0.075), 0.68, 1.3)


func roll_level(combined_speed: float) -> float:
	return clampf(pow(clampf(combined_speed / 12.0, 0.0, 1.0), 0.72) * 0.32, 0.001, 0.32)


func _ensure_audio_bus() -> void:
	bus_index = AudioServer.get_bus_index(BUS_NAME)
	if bus_index < 0:
		AudioServer.add_bus()
		bus_index = AudioServer.bus_count - 1
		AudioServer.set_bus_name(bus_index, BUS_NAME)
	if AudioServer.get_bus_effect_count(bus_index) < 1:
		var reverb := AudioEffectReverb.new()
		reverb.room_size = 0.86
		reverb.damping = 0.42
		reverb.wet = 0.27
		reverb.dry = 0.88
		AudioServer.add_bus_effect(bus_index, reverb, 0)
	if AudioServer.get_bus_effect_count(bus_index) < 2:
		var low_pass := AudioEffectLowPassFilter.new()
		low_pass.cutoff_hz = 720.0
		low_pass.resonance = 0.22
		AudioServer.add_bus_effect(bus_index, low_pass, 1)
	AudioServer.set_bus_effect_enabled(bus_index, 1, false)


func _make_impact_stream(duration: float, frequency: float, decay: float, gain: float) -> AudioStreamWAV:
	var rate := 22050
	var sample_count := int(duration * rate)
	var data := PackedByteArray()
	data.resize(sample_count * 2)
	for sample in sample_count:
		var t := float(sample) / float(rate)
		var envelope := exp(-t / maxf(0.01, duration * decay))
		var transient := sin(TAU * frequency * t) + sin(TAU * frequency * 1.93 * t) * 0.3
		var value := int(clampf(transient * envelope * gain, -1.0, 1.0) * 32767.0)
		data.encode_s16(sample * 2, value)
	return _wav(data, rate)


func _make_roll_stream() -> AudioStreamWAV:
	var rate := 22050
	var seconds := 1.2
	var sample_count := int(seconds * rate)
	var data := PackedByteArray()
	data.resize(sample_count * 2)
	var noise := 0.0
	var random := RandomNumberGenerator.new()
	random.seed = 51703
	for sample in sample_count:
		var raw := random.randf_range(-1.0, 1.0)
		noise = lerpf(noise, raw, 0.075)
		var t := float(sample) / float(rate)
		var rumble := sin(TAU * 58.0 * t) * 0.15 + sin(TAU * 93.0 * t) * 0.08
		data.encode_s16(sample * 2, int(clampf((noise * 0.32 + rumble) * 0.42, -1.0, 1.0) * 32767.0))
	var stream := _wav(data, rate)
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_begin = 0
	stream.loop_end = sample_count
	return stream


func _make_replay_stream() -> AudioStreamWAV:
	var rate := 22050
	var seconds := 2.0
	var sample_count := int(seconds * rate)
	var data := PackedByteArray()
	data.resize(sample_count * 2)
	for sample in sample_count:
		var t := float(sample) / float(rate)
		var envelope := sin(PI * clampf(t / seconds, 0.0, 1.0))
		var value := sin(TAU * 42.0 * t) * 0.42 + sin(TAU * 63.0 * t) * 0.18
		data.encode_s16(sample * 2, int(clampf(value * envelope, -1.0, 1.0) * 32767.0))
	return _wav(data, rate)


func _wav(data: PackedByteArray, rate: int) -> AudioStreamWAV:
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.stereo = false
	stream.data = data
	return stream
