class_name BowlingSettings
extends RefCounted
## The player's choices, remembered between sessions (user://phantom_bowling.cfg).

const PATH := "user://phantom_bowling.cfg"
## the file in use; tests point this at a scratch file so they never touch
## the player's own settings
static var path := PATH


static func load_all() -> Dictionary:
	var cfg := ConfigFile.new()
	cfg.load(path)          # a missing file just leaves the defaults
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
		"pin_sounds": cfg.get_value("play", "pin_sounds", "auto"),   # auto / deep / original / recorded
		"players": cfg.get_value("play", "players", 1),
		"opponent": cfg.get_value("play", "opponent", 0),       # 0 off, 1-3 a computer bowler
		"names": cfg.get_value("play", "names", ["", "", "", ""]),
		# each bowler's ball; bowler 1 inherits the single-player choice
		"balls": cfg.get_value("play", "balls", [cfg.get_value("play", "ball", 0), 1, 2, 0]),
		"muted": cfg.get_value("play", "muted", false),
	}


static func save_value(key: String, value: Variant) -> void:
	var cfg := ConfigFile.new()
	cfg.load(path)
	cfg.set_value("play", key, value)
	cfg.save(path)
