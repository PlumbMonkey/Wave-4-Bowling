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
		"alley": cfg.get_value("play", "alley", "lounge"),
		"best": cfg.get_value("play", "best", 0),
		"vol_master": cfg.get_value("play", "vol_master", 0.9),
		"vol_sfx": cfg.get_value("play", "vol_sfx", 1.0),
		"vol_amb": cfg.get_value("play", "vol_amb", 0.8),
		"vol_callouts": cfg.get_value("play", "vol_callouts", 0.7),
		"quality": cfg.get_value("play", "quality", "auto"),
		"fullscreen": cfg.get_value("play", "fullscreen", false),
		"guide": cfg.get_value("play", "guide", true),
		"muted": cfg.get_value("play", "muted", false),
	}


static func save_value(key: String, value: Variant) -> void:
	var cfg := ConfigFile.new()
	cfg.load(PATH)
	cfg.set_value("play", key, value)
	cfg.save(PATH)
