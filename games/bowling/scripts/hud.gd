class_name BowlingHud
extends CanvasLayer
## Grey-box HUD: the 10-frame scoreboard, power meter, spin gauge, and the
## big "STRIKE!" message.

const BRASS := Color("b59449")
const ECTO := Color("2bf7a3")
const VIOLET := Color("8a2be2")
const INK := Color("e8e0d0")

var _board: VBoxContainer      ## one scoreboard row per bowler
var _rows: Array = []          # [{frames: [{marks, total, panel}], grand: Label, name: Label, name_sb}]
var _power: ProgressBar
var _power_box: Control
var _lane: Label
var _msg: Label
var _hint: Label
var _ball: Label
var _bowler: Label              ## whose turn it is (two or more bowlers)
var _speed: Label
var _bars: Array[ColorRect] = []
var _replay_label: Label
var _replay_bar: ColorRect
var _msg_tween: Tween
var _art: TextureRect           ## a painted call-out, when there is one
var _art_tween: Tween
var _art_cache := {}
var _call: Label                ## the text call-out, until the painted art arrives
var _call_haze: Label           ## a purple haze behind it
var _call_tween: Tween

## Creepy glowing baby blue with a hint of purple. Comic Sans comes from the
## player's own system (it can't be shipped in the game), so the web build and
## other systems fall back to the next font on the list.
const CALL_BLUE := Color(0.62, 0.88, 1.0)
const CALL_EDGE := Color(0.34, 0.12, 0.62)
const CALL_FONTS := ["Comic Sans MS", "Comic Neue", "Chalkboard SE", "Chalkboard"]

## Painted call-outs: drop art/callouts/<kind>.png into the project (transparent
## PNG, roughly 2:1) and it replaces the text for that result.
const CALLOUT_DIR := "res://art/callouts/"
const CALLOUT_MAX := Vector2(1100, 560)


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	_board = VBoxContainer.new()
	_board.position = Vector2(40, 28)
	_board.add_theme_constant_override("separation", 4)
	root.add_child(_board)
	set_players(["PLAYER 1"])

	_power_box = VBoxContainer.new()
	_power_box.position = Vector2(760, 960)
	_power_box.custom_minimum_size = Vector2(400, 0)
	root.add_child(_power_box)
	var pl := _label("POWER", 18, BRASS)
	_power_box.add_child(pl)
	_power = ProgressBar.new()
	_power.custom_minimum_size = Vector2(400, 26)
	_power.max_value = 1.0
	_power.show_percentage = false
	var fill := StyleBoxFlat.new()
	fill.bg_color = ECTO
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.6)
	bg.border_color = BRASS
	bg.set_border_width_all(2)
	_power.add_theme_stylebox_override("fill", fill)
	_power.add_theme_stylebox_override("background", bg)
	_power_box.add_child(_power)

	_lane = _label("", 20, Color(INK, 0.7))
	_lane.position = Vector2(1240, 980)
	root.add_child(_lane)

	_msg = _label("", 110, ECTO)
	root.add_child(_msg)
	_msg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_msg.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_msg.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_msg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_msg.add_theme_color_override("font_outline_color", Color(0.1, 0.0, 0.2))
	_msg.add_theme_constant_override("outline_size", 16)
	_msg.modulate.a = 0.0

	var font := SystemFont.new()
	font.font_names = PackedStringArray(CALL_FONTS)
	font.font_weight = 700
	var haze := LabelSettings.new()
	haze.font = font
	haze.font_size = 150
	haze.font_color = Color(0.55, 0.30, 1.0, 0.0)
	haze.outline_size = 44
	haze.outline_color = Color(0.58, 0.34, 1.0, 0.13)
	haze.shadow_size = 0
	haze.shadow_color = Color(0, 0, 0, 0)
	haze.shadow_offset = Vector2.ZERO
	var main := LabelSettings.new()
	main.font = font
	main.font_size = 150
	main.font_color = CALL_BLUE
	main.outline_size = 16
	main.outline_color = CALL_EDGE
	main.shadow_size = 26
	main.shadow_color = Color(0.45, 0.80, 1.0, 0.30)
	main.shadow_offset = Vector2.ZERO
	for pair in [["haze", haze], ["main", main]]:
		var l := Label.new()
		l.label_settings = pair[1]
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(l)
		l.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		l.pivot_offset = Vector2(960, 480)
		l.modulate.a = 0.0
		if pair[0] == "haze":
			_call_haze = l
		else:
			_call = l

	_art = TextureRect.new()
	_art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_art.visible = false
	root.add_child(_art)

	_speed = _label("", 22, INK)
	_speed.position = Vector2(1240, 900)
	root.add_child(_speed)

	# instant-replay letterbox
	for top in [true, false]:
		var bar := ColorRect.new()
		bar.color = Color(0, 0, 0, 0.92)
		bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(bar)
		bar.position = Vector2(0, 0 if top else 970)
		bar.size = Vector2(1920, 110)
		bar.visible = false
		_bars.append(bar)
	_replay_label = _label("INSTANT REPLAY", 34, VIOLET)
	_replay_label.position = Vector2(1500, 996)
	_replay_label.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	_replay_label.add_theme_constant_override("outline_size", 6)
	_replay_label.visible = false
	root.add_child(_replay_label)
	_replay_bar = ColorRect.new()
	_replay_bar.color = VIOLET
	_replay_bar.position = Vector2(0, 1076)
	_replay_bar.size = Vector2(0, 4)
	_replay_bar.visible = false
	root.add_child(_replay_bar)

	_ball = _label("", 22, BRASS)
	_ball.position = Vector2(1240, 940)
	root.add_child(_ball)

	_bowler = _label("", 34, ECTO)
	_bowler.position = Vector2(1240, 846)
	_bowler.add_theme_color_override("font_outline_color", Color(0.1, 0.0, 0.2))
	_bowler.add_theme_constant_override("outline_size", 8)
	root.add_child(_bowler)

	_hint = _label("", 18, Color(INK, 0.75))
	_hint.position = Vector2(40, 1010)
	root.add_child(_hint)


func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


func _cell(parent: Container, w: int, title: String) -> Dictionary:
	var panel := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.04, 0.02, 0.06, 0.8)
	sb.border_color = Color(BRASS, 0.8)
	sb.set_border_width_all(2)
	sb.set_content_margin_all(6)
	panel.add_theme_stylebox_override("panel", sb)
	panel.custom_minimum_size = Vector2(w, 0)
	parent.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	panel.add_child(v)
	var head := _label(title, 14, Color(BRASS, 0.9))
	head.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	head.visible = title != ""          # frame numbers only on the top row
	v.add_child(head)
	var marks := _label("", 24, INK)
	marks.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	v.add_child(marks)
	var total := _label("", 30, ECTO)
	total.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(total)
	return {"marks": marks, "total": total, "panel": sb}


## One scoreboard row per bowler; with more than one, each row starts with a
## name cell. Three or four bowlers shrink the board to fit.
func set_players(names: Array) -> void:
	for c in _board.get_children():
		_board.remove_child(c)
		c.queue_free()
	_rows.clear()
	var multi := names.size() > 1
	_board.scale = Vector2.ONE * (0.8 if names.size() > 2 else 1.0)
	for p in names.size():
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 4)
		_board.add_child(row)
		var r := {"frames": [], "name": null, "name_sb": null}
		if multi:
			var nc := _cell(row, 190, "BOWLER" if p == 0 else "")
			nc.marks.text = String(names[p])
			nc.marks.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
			nc.marks.clip_text = true
			nc.marks.add_theme_font_size_override("font_size", 26)
			r.name = nc.marks
			r.name_sb = nc.panel
		for i in 10:
			r.frames.append(_cell(row, 120 if i == 9 else 86, str(i + 1) if p == 0 else ""))
		r.grand = _cell(row, 110, "TOTAL" if p == 0 else "").total
		_rows.append(r)


func update_card(card: ScoreCard) -> void:
	update_cards([card], 0)


## Fill every bowler's row; the bowler up now gets the lit name and frame.
func update_cards(cards: Array, current: int) -> void:
	for p in mini(cards.size(), _rows.size()):
		var c: ScoreCard = cards[p]
		var row: Dictionary = _rows[p]
		var fr := c.frames()
		var cur := c.current_frame()
		for i in 10:
			var f: Dictionary = fr[i]
			var cell: Dictionary = row.frames[i]
			cell.marks.text = "  ".join(PackedStringArray(f.marks))
			cell.total.text = "" if f.cumulative == null else str(f.cumulative)
			cell.panel.border_color = ECTO if (p == current and i == cur) else Color(BRASS, 0.8)
		row.grand.text = str(c.total())
		if row.name:
			row.name_sb.border_color = ECTO if p == current else Color(BRASS, 0.8)
			row.name.add_theme_color_override("font_color", ECTO if p == current else Color(INK, 0.7))


func set_power(p: float, shown: bool) -> void:
	_power_box.visible = shown
	_power.value = p


func set_lane(text: String) -> void:
	_lane.text = text


func set_ball(text: String) -> void:
	_ball.text = text


func set_bowler(text: String) -> void:
	_bowler.text = text


## The draw readout under the ball name: speed in mph, or a nudge to pull back.
func set_speed(draw: float, metres_per_s: float) -> void:
	if draw <= 0.0:
		_speed.text = "PULL BACK TO SET SPEED"
		_speed.add_theme_color_override("font_color", Color(INK, 0.55))
	else:
		_speed.text = "SPEED  %d mph" % roundi(metres_per_s * 2.237)
		_speed.add_theme_color_override("font_color", ECTO.lerp(INK, 0.35))


func set_replay(on: bool, progress := 0.0) -> void:
	for b in _bars:
		b.visible = on
	_replay_label.visible = on
	_replay_bar.visible = on
	_replay_bar.size.x = 1920.0 * progress
	_speed.visible = not on
	_ball.visible = not on
	_bowler.visible = not on
	_lane.visible = not on


func set_hint(text: String) -> void:
	_hint.text = text


func flash(text: String, color := ECTO, hold := 1.2) -> void:
	_msg.text = text
	_msg.add_theme_color_override("font_color", color)
	if _msg_tween:
		_msg_tween.kill()
	_msg.modulate.a = 1.0
	_msg_tween = create_tween()
	_msg_tween.tween_interval(hold)
	_msg_tween.tween_property(_msg, "modulate:a", 0.0, 0.5)


## The texture for a call-out (strike, spare, miss, gutter), or null.
func callout_art(kind: String) -> Texture2D:
	if not _art_cache.has(kind):
		var path := CALLOUT_DIR + kind + ".png"
		_art_cache[kind] = load(path) if ResourceLoader.exists(path) else null
	return _art_cache[kind]


## Show a result: the painted art if it exists (slammed on with a bounce and a
## tilt, like a sticker), otherwise the text.
func callout(kind: String, text: String, color := ECTO, hold := 1.2) -> void:
	var tex := callout_art(kind)
	if tex == null:
		_text_callout(text, hold)
		return
	if _art_tween:
		_art_tween.kill()
	_msg.modulate.a = 0.0
	var k := minf(CALLOUT_MAX.x / tex.get_width(), CALLOUT_MAX.y / tex.get_height())
	var sz := Vector2(tex.get_width(), tex.get_height()) * k
	_art.texture = tex
	_art.size = sz
	_art.position = (Vector2(1920, 1080) - sz) * 0.5 + Vector2(0, -60)
	_art.pivot_offset = sz * 0.5
	_art.visible = true
	_art.modulate.a = 1.0
	_art.scale = Vector2.ONE * 1.6
	_art.rotation = deg_to_rad(randf_range(-7.0, 3.0))
	_art_tween = create_tween()
	_art_tween.tween_property(_art, "scale", Vector2.ONE * 0.94, 0.14).set_trans(Tween.TRANS_QUAD) 		.set_ease(Tween.EASE_IN)
	_art_tween.tween_property(_art, "scale", Vector2.ONE, 0.10).set_trans(Tween.TRANS_BACK) 		.set_ease(Tween.EASE_OUT)
	_art_tween.tween_interval(hold)
	_art_tween.tween_property(_art, "modulate:a", 0.0, 0.4)
	_art_tween.tween_callback(func(): _art.visible = false)


## Clear any call-out or message (a menu is opening over the HUD).
func clear_message() -> void:
	if _msg_tween:
		_msg_tween.kill()
	if _art_tween:
		_art_tween.kill()
	_msg.modulate.a = 0.0
	_art.visible = false
	if _call_tween:
		_call_tween.kill()
	_call.modulate.a = 0.0
	_call_haze.modulate.a = 0.0


## The text call-out: it flickers on like a failing tube, breathes and drifts
## up a little, then fades.
func _text_callout(text: String, hold: float) -> void:
	if _call_tween:
		_call_tween.kill()
	_msg.modulate.a = 0.0
	for l in [_call, _call_haze]:
		l.text = text
		l.modulate.a = 0.0
		l.position.y = 0.0
		l.scale = Vector2.ONE * 1.08
		l.rotation = deg_to_rad(randf_range(-2.5, 2.5))
	var tw := create_tween().set_parallel(true)
	_call_tween = tw
	var flick := [1.0, 0.15, 0.9, 0.35, 1.0]
	for i in flick.size():
		for l in [_call, _call_haze]:
			tw.tween_property(l, "modulate:a", flick[i], 0.05).set_delay(i * 0.05)
	for l in [_call, _call_haze]:
		tw.tween_property(l, "scale", Vector2.ONE, 0.35).set_trans(Tween.TRANS_BACK) 			.set_ease(Tween.EASE_OUT)
		tw.tween_property(l, "position:y", -26.0, hold + 0.6).set_delay(0.25) 			.set_trans(Tween.TRANS_SINE)
	# the haze breathes while it hangs there
	var breaths := int(hold / 0.25) - 1
	for b in breaths:
		tw.tween_property(_call_haze, "modulate:a", 0.45 if b % 2 == 0 else 1.0, 0.25) 			.set_delay(0.3 + b * 0.25)
	for l in [_call, _call_haze]:
		tw.tween_property(l, "modulate:a", 0.0, 0.45).set_delay(0.3 + hold)
