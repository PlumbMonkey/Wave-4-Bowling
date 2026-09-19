class_name BowlingHud
extends CanvasLayer
## Grey-box HUD: the 10-frame scoreboard, power meter, spin gauge, and the
## big "STRIKE!" message.

const BRASS := Color("b59449")
const ECTO := Color("2bf7a3")
const VIOLET := Color("8a2be2")
const INK := Color("e8e0d0")

var _frames: Array = []        # [{marks: Label, total: Label}]
var _grand: Label
var _power: ProgressBar
var _power_box: Control
var _lane: Label
var _msg: Label
var _hint: Label
var _ball: Label
var _speed: Label
var _bars: Array[ColorRect] = []
var _replay_label: Label
var _replay_bar: ColorRect
var _msg_tween: Tween


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	var board := HBoxContainer.new()
	board.position = Vector2(40, 28)
	board.add_theme_constant_override("separation", 4)
	root.add_child(board)
	for i in 10:
		var cell := _cell(board, 120 if i == 9 else 86, str(i + 1))
		_frames.append(cell)
	var t := _cell(board, 110, "TOTAL")
	_grand = t.total

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
	v.add_child(head)
	var marks := _label("", 24, INK)
	marks.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	v.add_child(marks)
	var total := _label("", 30, ECTO)
	total.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(total)
	return {"marks": marks, "total": total, "panel": sb}


func update_card(card: ScoreCard) -> void:
	var fr := card.frames()
	var cur := card.current_frame()
	for i in 10:
		var f: Dictionary = fr[i]
		_frames[i].marks.text = "  ".join(PackedStringArray(f.marks))
		_frames[i].total.text = "" if f.cumulative == null else str(f.cumulative)
		_frames[i].panel.border_color = ECTO if i == cur else Color(BRASS, 0.8)
	_grand.text = str(card.total())


func set_power(p: float, shown: bool) -> void:
	_power_box.visible = shown
	_power.value = p


func set_lane(text: String) -> void:
	_lane.text = text


func set_ball(text: String) -> void:
	_ball.text = text


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
