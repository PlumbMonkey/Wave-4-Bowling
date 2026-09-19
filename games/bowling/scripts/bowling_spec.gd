class_name BowlingSpec
## Regulation dimensions (USBC), in metres and kilograms.
## The lane runs toward -Z. The foul line is z = 0, the approach is +Z, and the
## lane surface is y = 0.

const BOARD := 0.02703                 # 39 boards across the lane
const LANE_HALF := 0.527               # 41.5" wide
const LANE_LEN := 18.288               # foul line to head pin (60 ft)
const DECK_LEN := 0.872                # head pin spot to the pit edge
const DECK_END := -(LANE_LEN + DECK_LEN)
const PIT_END := -20.35
const GUTTER_W := 0.235
const GUTTER_DROP := 0.06
const APPROACH := 4.6

const BALL_R := 0.1085                 # 8.5" diameter
const BALL_MASS := 6.8                 # 15 lb
const PIN_H := 0.381                   # 15"
const PIN_MASS := 1.58                 # 3 lb 8 oz
const PIN_COM := 0.145                 # centre of mass above the base
const PIN_SPACING := 0.3048            # 12" between spot centres
const ROW_SPACING := 0.2640            # 10.392" between rows

# Lane conditioning: a house shot, oil for 40 ft then a dry back end
const OIL_LEN := 12.2
const MU_OIL := 0.04
const MU_DRY := 0.20
const MU_ROLL := 0.01                  # rolling resistance once the ball rolls

# Throw envelope
const SPEED_MIN := 4.0
const SPEED_MAX := 10.0
const AIM_MAX := deg_to_rad(4.0)
const X_MAX := 0.42
const REV_SIDE := 20.0                 # rad/s of side rotation at full release spin
const SPIN_TORQUE := 0.35              # N·m from the bumpers while the ball rolls
const STEER_ACCEL := 0.12              # m/s² sideways from the left stick after release
const STEER_STOP := 1.0                # no steering in the last metre before the head pin


## The ten pin spots. Index 0 is the head pin; the order is 1, 2-3, 4-6, 7-10.
static func pin_spots() -> Array[Vector3]:
	var out: Array[Vector3] = []
	for row in 4:
		for k in row + 1:
			out.append(Vector3((k - row * 0.5) * PIN_SPACING, 0.0, -LANE_LEN - row * ROW_SPACING))
	return out


## Board number (1 = right edge, 39 = left edge, 20 = centre) to x.
static func board_x(board: float) -> float:
	return (20.0 - board) * BOARD
