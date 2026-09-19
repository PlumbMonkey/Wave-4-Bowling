class_name BowlingMenus
extends CanvasLayer
## Title, pause, settings and game-over screens. Built in code like the HUD,
## driven by pad (D-pad / left stick, A select, B back, Start pause) or mouse.
##
## Runs while the tree is paused; talks to the game through a handful of
## methods on game.gd (start_from_title, cycle_alley, set_quality, ...).

const BRASS := BowlingHud.BRASS
const ECTO := BowlingHud.ECTO
const VIOLET := BowlingHud.VIOLET
const INK := BowlingHud.INK

signal closed

var game: Node
var _screens := {}              ## name -> Control
var _first := {}                ## name -> the control that takes focus on open
var _open := ""
var _settings_back := ""        ## where Back goes from settings
var _refresh: Array[Callable] = []   ## option rows re-read their values on open
var _theme := Theme.new()
var _best: Label
var _over_score: Label
var _over_best: Label
var _over_stats: Label
var _sliders := {}


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_theme()
	_build_title()
	_build_pause()
	_build_settings()
	_build_over()
	for s in _screens.values():
		(s as Control).visible = false


func is_open() -> bool:
	return _open != ""


func current() -> String:
	return _open


func open(screen: String) -> void:
	for n in _screens:
		(_screens[n] as Control).visible = n == screen
	_open = screen
	# the game stops under the pause menu (and settings opened from it); the
	# title and game-over screens let the alley carry on behind them
	get_tree().paused = screen == "pause" or (screen == "settings" and _settings_back == "pause")
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if game and game.hud:
		game.hud.clear_message()
	for r in _refresh:
		r.call()
	if _best:
		var b := int(BowlingSettings.load_all().best)
		_best.text = "BEST GAME  %d" % b if b > 0 else ""
	var f: Control = _first.get(screen)
	if f:
		f.grab_focus.call_deferred()


func close() -> void:
	for s in _screens.values():
		(s as Control).visible = false
	_open = ""
	_settings_back = ""
	get_tree().paused = false
	closed.emit()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		match _open:
			"":
				if game and game.can_pause():
					open("pause")
			"pause":
				close()
			"settings":
				_back_from_settings()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("ui_cancel") and _open != "":
		match _open:
			"pause":
				close()
			"settings":
				_back_from_settings()
		get_viewport().set_input_as_handled()


# ----------------------------------------------------------------- screens --
func _build_title() -> void:
	var s := _screen("title", Color(0, 0, 0, 0.0))
	var shade := ColorRect.new()          # darken the left third so the text reads
	shade.color = Color(0.02, 0.0, 0.05, 0.62)
	shade.position = Vector2.ZERO
	shade.size = Vector2(820, 1080)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	s.add_child(shade)
	var col := _column(s, Vector2(120, 150))
	var t1 := _label("PHANTOM", 118, ECTO)
	t1.add_theme_color_override("font_outline_color", Color(0.18, 0.02, 0.32))
	t1.add_theme_constant_override("outline_size", 22)
	col.add_child(t1)
	var t2 := _label("BOWLING", 118, INK)
	t2.add_theme_color_override("font_outline_color", Color(0.18, 0.02, 0.32))
	t2.add_theme_constant_override("outline_size", 22)
	col.add_child(t2)
	col.add_child(_label("SPECTRAL MANOR  ·  WAVE IV", 26, BRASS))
	col.add_child(_gap(40))
	var play := _button(col, "BOWL", func(): game.start_from_title())
	_first["title"] = play
	_option(col, "ALLEY", func(): return AlleyTheme.display_name_of(game.alley_id),
		func(d: int): game.cycle_alley(d))
	_option(col, "PINS", func(): return String(BowlingPin.STYLES[game.pin_style].name),
		func(d: int): game.cycle_pins(d))
	_option(col, "BALL", func(): return game.ball_name(), func(d: int): game.cycle_ball(d))
	_button(col, "SETTINGS", func(): _open_settings("title"))
	if not OS.has_feature("web"):
		_button(col, "QUIT", func(): get_tree().quit())
	col.add_child(_gap(24))
	_best = _label("", 26, ECTO)
	col.add_child(_best)
	var hint := _label("A / Enter  select      ◀ ▶  change      B / Esc  back", 18, Color(INK, 0.6))
	hint.position = Vector2(120, 1020)
	s.add_child(hint)


func _build_pause() -> void:
	var s := _screen("pause", Color(0.01, 0.0, 0.03, 0.72))
	var col := _column(s, Vector2(760, 330))
	col.add_child(_label("PAUSED", 72, ECTO))
	col.add_child(_gap(20))
	_first["pause"] = _button(col, "RESUME", close)
	_button(col, "RESTART GAME", func(): close(); game.restart_game())
	_button(col, "SETTINGS", func(): _open_settings("pause"))
	_button(col, "QUIT TO TITLE", func(): close(); game.show_title())


func _build_settings() -> void:
	var s := _screen("settings", Color(0.01, 0.0, 0.03, 0.80))
	var col := _column(s, Vector2(640, 170))
	col.add_child(_label("SETTINGS", 64, ECTO))
	col.add_child(_gap(16))
	var first: Control = null
	for row in [["vol_master", "MASTER VOLUME"], ["vol_sfx", "EFFECTS"], ["vol_amb", "AMBIENCE"],
			["vol_callouts", "CALL-OUTS"]]:
		var sl := _slider(col, row[1], row[0])
		if first == null:
			first = sl
	_first["settings"] = first
	col.add_child(_gap(10))
	if not GraphicsProfile.web_only():
		_option(col, "GRAPHICS", func(): return String(game.quality_label()),
			func(d: int): game.cycle_quality(d))
	if not OS.has_feature("web"):
		_option(col, "FULLSCREEN", func(): return "ON" if _fullscreen() else "OFF",
			func(_d: int): _toggle_fullscreen())
	_option(col, "AIM GUIDE", func(): return "ON" if game.guide_enabled else "OFF",
		func(_d: int): game.toggle_guide())
	col.add_child(_gap(10))
	_button(col, "BACK", _back_from_settings)


func _build_over() -> void:
	var s := _screen("over", Color(0.01, 0.0, 0.03, 0.66))
	var col := _column(s, Vector2(680, 110))
	col.add_child(_label("FINAL SCORE", 34, BRASS))
	_over_score = _label("0", 160, ECTO)
	_over_score.add_theme_color_override("font_outline_color", Color(0.18, 0.02, 0.32))
	_over_score.add_theme_constant_override("outline_size", 24)
	col.add_child(_over_score)
	_over_best = _label("", 34, VIOLET.lerp(INK, 0.3))
	col.add_child(_over_best)
	_over_stats = _label("", 26, INK)
	col.add_child(_over_stats)
	col.add_child(_gap(30))
	_first["over"] = _button(col, "BOWL AGAIN", func(): close(); game.restart_game())
	# try something different for the next game without going back to the title
	_option(col, "ALLEY", func(): return AlleyTheme.display_name_of(game.alley_id),
		func(d: int): game.cycle_alley(d))
	_option(col, "PINS", func(): return String(BowlingPin.STYLES[game.pin_style].name),
		func(d: int): game.cycle_pins(d))
	_option(col, "BALL", func(): return game.ball_name(), func(d: int): game.cycle_ball(d))
	_button(col, "TITLE", func(): close(); game.show_title())


## Fill in and show the game-over screen.
func show_over(card: ScoreCard, best_before: int) -> void:
	var total := card.total()
	_over_score.text = str(total)
	if total > best_before:
		_over_best.text = "NEW BEST GAME!" if best_before > 0 else "FIRST GAME ON THE BOOKS"
	else:
		_over_best.text = "BEST  %d" % best_before
	var strikes := 0
	var spares := 0
	for f in card.frames():
		for m in f.marks:
			if m == "X":
				strikes += 1
			elif m == "/":
				spares += 1
	_over_stats.text = "STRIKES  %d      SPARES  %d" % [strikes, spares]
	open("over")


# ---------------------------------------------------------------- settings --
func _open_settings(from: String) -> void:
	_settings_back = from
	open("settings")


func _back_from_settings() -> void:
	var to := _settings_back
	_settings_back = ""
	open(to if to != "" else "pause")


func _fullscreen() -> bool:
	return DisplayServer.window_get_mode() in [DisplayServer.WINDOW_MODE_FULLSCREEN,
		DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN]


func _toggle_fullscreen() -> void:
	var on := not _fullscreen()
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if on
		else DisplayServer.WINDOW_MODE_WINDOWED)
	BowlingSettings.save_value("fullscreen", on)


# ----------------------------------------------------------------- widgets --
func _screen(id: String, dim: Color) -> Control:
	var s := Control.new()
	s.name = id
	s.theme = _theme
	s.set_anchors_preset(Control.PRESET_FULL_RECT)
	s.mouse_filter = Control.MOUSE_FILTER_STOP
	var bg := ColorRect.new()
	bg.color = dim
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	s.add_child(bg)
	add_child(s)
	_screens[id] = s
	return s


func _column(parent: Control, at: Vector2) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.position = at
	v.add_theme_constant_override("separation", 12)
	parent.add_child(v)
	return v


func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _gap(h: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, h)
	return c


func _button(parent: Container, text: String, action: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(560, 58)
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.pressed.connect(func(): _click(); action.call())
	b.mouse_entered.connect(func(): b.grab_focus())
	parent.add_child(b)
	return b


## A row that cycles a value: A / click / right steps forward, left steps back.
func _option(parent: Container, title: String, value: Callable, step: Callable) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(560, 58)
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	var redraw := func(): b.text = "%s      ◀  %s  ▶" % [title, str(value.call())]
	redraw.call()
	_refresh.append(redraw)
	b.pressed.connect(func(): _click(); step.call(1); redraw.call())
	b.gui_input.connect(func(e: InputEvent):
		for d in [[-1, "ui_left"], [1, "ui_right"]]:
			if e.is_action_pressed(d[1]):
				_click()
				step.call(d[0])
				redraw.call()
				b.accept_event())
	b.mouse_entered.connect(func(): b.grab_focus())
	parent.add_child(b)
	return b


func _slider(parent: Container, title: String, key: String) -> HSlider:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 20)
	parent.add_child(row)
	var l := _label(title, 26, INK)
	l.custom_minimum_size = Vector2(280, 0)
	row.add_child(l)
	var sl := HSlider.new()
	sl.min_value = 0.0
	sl.max_value = 1.0
	sl.step = 0.05
	sl.custom_minimum_size = Vector2(360, 40)
	sl.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var pct := _label("", 24, ECTO)
	pct.custom_minimum_size = Vector2(80, 0)
	var read := func():
		sl.set_value_no_signal(float(BowlingSettings.load_all()[key]))
		pct.text = "%d%%" % roundi(sl.value * 100.0)
	read.call()
	_refresh.append(read)
	sl.value_changed.connect(func(v: float):
		pct.text = "%d%%" % roundi(v * 100.0)
		BowlingSettings.save_value(key, v)
		game.apply_volumes())
	sl.mouse_entered.connect(func(): sl.grab_focus())
	row.add_child(sl)
	row.add_child(pct)
	_sliders[key] = sl
	return sl


func _click() -> void:
	if game and game.audio:
		game.audio.play("select", null, -12.0, 0.9)


func _build_theme() -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color(0.03, 0.015, 0.05, 0.86)
	normal.border_color = Color(BRASS, 0.75)
	normal.set_border_width_all(2)
	normal.set_corner_radius_all(3)
	normal.content_margin_left = 22
	normal.content_margin_right = 22
	var focus := normal.duplicate() as StyleBoxFlat
	focus.bg_color = Color(0.08, 0.03, 0.12, 0.95)
	focus.border_color = ECTO
	focus.set_border_width_all(3)
	focus.shadow_color = Color(ECTO, 0.25)
	focus.shadow_size = 10
	var pressed := focus.duplicate() as StyleBoxFlat
	pressed.bg_color = Color(VIOLET, 0.5)
	_theme.set_stylebox("normal", "Button", normal)
	_theme.set_stylebox("hover", "Button", focus)
	_theme.set_stylebox("focus", "Button", focus)
	_theme.set_stylebox("pressed", "Button", pressed)
	_theme.set_font_size("font_size", "Button", 30)
	_theme.set_color("font_color", "Button", INK)
	_theme.set_color("font_hover_color", "Button", ECTO)
	_theme.set_color("font_focus_color", "Button", ECTO)
	_theme.set_color("font_pressed_color", "Button", INK)
	var track := StyleBoxFlat.new()
	track.bg_color = Color(0.0, 0.0, 0.0, 0.6)
	track.border_color = Color(BRASS, 0.7)
	track.set_border_width_all(1)
	track.content_margin_top = 4
	track.content_margin_bottom = 4
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color(ECTO, 0.75)
	fill.content_margin_top = 4
	fill.content_margin_bottom = 4
	var sfocus := StyleBoxFlat.new()
	sfocus.draw_center = false
	sfocus.border_color = ECTO
	sfocus.set_border_width_all(2)
	sfocus.set_expand_margin_all(6)
	_theme.set_stylebox("slider", "HSlider", track)
	_theme.set_stylebox("grabber_area", "HSlider", fill)
	_theme.set_stylebox("grabber_area_highlight", "HSlider", fill)
	_theme.set_stylebox("focus", "HSlider", sfocus)
