class_name ScoreCard
extends RefCounted
## Ten-pin scoring: strikes, spares, opens and the 10th-frame fill balls.
## Pure logic, no nodes - tested in tests/run_tests.gd.

var rolls: Array[int] = []


## Pins still standing before the next ball (so the pinsetter knows what to set).
func pins_standing() -> int:
	var f := _frames()
	for i in 10:
		var fr: Dictionary = f[i]
		if fr.complete:
			continue
		var r: Array = fr.rolls
		if i < 9:
			return 10 - (r[0] if r.size() == 1 else 0)
		# 10th frame
		match r.size():
			0:
				return 10
			1:
				return 10 if r[0] == 10 else 10 - r[0]
			2:
				if r[0] == 10:
					return 10 if r[1] == 10 else 10 - r[1]
				return 10          # spare earns a fresh rack
	return 0


## True when the next ball needs all ten pins reset.
func needs_full_rack() -> bool:
	return pins_standing() == 10


func can_roll(pins: int) -> bool:
	return not is_complete() and pins >= 0 and pins <= pins_standing()


func roll(pins: int) -> bool:
	if not can_roll(pins):
		push_warning("ScoreCard: illegal roll %d (standing %d)" % [pins, pins_standing()])
		return false
	rolls.append(pins)
	return true


func is_complete() -> bool:
	return _frames()[9].complete


## Index of the frame being bowled (0-9), or 10 when the game is over.
func current_frame() -> int:
	var f := _frames()
	for i in 10:
		if not f[i].complete:
			return i
	return 10


## Running total up to the last frame that can be scored.
func total() -> int:
	var t := 0
	for fr in _frames():
		if fr.score == null:
			break
		t = fr.cumulative
	return t


## Per-frame view for the scoreboard:
## { rolls: [int], marks: ["X", "/", "-", "7"], complete: bool, score: int|null, cumulative: int|null }
func frames() -> Array:
	return _frames()


func _frames() -> Array:
	var out := []
	var i := 0
	var running := 0
	var scoring := true
	for f in 10:
		var r: Array = []
		var fr := {"rolls": r, "marks": [], "complete": false, "score": null, "cumulative": null}
		if f < 9:
			if i < rolls.size():
				r.append(rolls[i])
				if rolls[i] == 10:
					fr.complete = true
					fr.score = _sum(i, 3) if i + 2 < rolls.size() else null
					i += 1
				else:
					if i + 1 < rolls.size():
						r.append(rolls[i + 1])
						fr.complete = true
						if rolls[i] + rolls[i + 1] == 10:
							fr.score = _sum(i, 3) if i + 2 < rolls.size() else null
						else:
							fr.score = rolls[i] + rolls[i + 1]
					i += 2
		else:
			r.assign(rolls.slice(i, i + 3))
			var bonus: bool = r.size() >= 2 and (r[0] == 10 or r[0] + r[1] == 10)
			fr.complete = r.size() == 3 or (r.size() == 2 and not bonus)
			if fr.complete:
				fr.score = _sum(i, r.size())
		fr.marks = _marks(r, f == 9)
		if scoring and fr.score != null:
			running += fr.score
			fr.cumulative = running
		else:
			scoring = false          # later frames can't show a running total yet
		out.append(fr)
	return out


func _sum(from: int, n: int) -> int:
	var s := 0
	for k in n:
		s += rolls[from + k]
	return s


static func _mark(pins: int) -> String:
	return "-" if pins == 0 else str(pins)


func _marks(r: Array, tenth: bool) -> Array:
	var m := []
	if r.is_empty():
		return m
	if not tenth:
		if r[0] == 10:
			return ["X"]
		m.append(_mark(r[0]))
		if r.size() > 1:
			m.append("/" if r[0] + r[1] == 10 else _mark(r[1]))
		return m
	# 10th frame: each ball is judged against a fresh or partial rack
	var fresh := true
	var standing := 10
	for k in r.size():
		var p: int = r[k]
		if fresh and p == 10:
			m.append("X")
		elif not fresh and p == standing:
			m.append("/")
		else:
			m.append(_mark(p))
		if fresh and p < 10:
			fresh = false
			standing = 10 - p
		elif not fresh:
			fresh = true           # after a spare or an open second ball
			standing = 10
	return m
