class_name BowlingSettings
extends RefCounted
## The player's choices, remembered between sessions (user://phantom_bowling.cfg).

const PATH := "user://phantom_bowling.cfg"


static func load_all() -> Dictionary:
	var cfg := ConfigFile.new()
	cfg.load(PATH)          # a missing file just leaves the defaults
	return {
		"ball": cfg.get_value("play", "ball", 0),
		"pins": cfg.get_value("play", "pins", "classic"),
		"muted": cfg.get_value("play", "muted", false),
	}


static func save_value(key: String, value: Variant) -> void:
	var cfg := ConfigFile.new()
	cfg.load(PATH)
	cfg.set_value("play", key, value)
	cfg.save(PATH)
