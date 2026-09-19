class_name GraphicsProfile
extends RefCounted
## PRD Phase 4: one game, two looks.
##
##   DESKTOP - Forward+: MSAA 4x, SSR on the lanes, SSAO + SSIL, volumetric fog,
##             every candle is a light, shadows on the chandeliers and pin spots.
##   WEB     - Compatibility (WebGL 2): MSAA 2x, glow only, no screen-space
##             effects or fog, candles glow by emission alone, one shadowed
##             light (your lane's pin spot), brighter ambient to make up for it.
##
## Picked automatically (web export or the Compatibility renderer means WEB),
## or forced with  -- --profile=web / --profile=desktop.

enum { DESKTOP, WEB }

## light kinds that only exist on desktop
const DESKTOP_ONLY_LIGHTS := ["Candle", "Lantern", "Pit", "Orb", "Neon", "Moon", "Torch"]


static func detect() -> int:
	for a in OS.get_cmdline_user_args():
		if a == "--profile=web":
			return WEB
		if a == "--profile=desktop":
			return DESKTOP
	if OS.has_feature("web") or RenderingServer.get_current_rendering_method() == "gl_compatibility":
		return WEB
	return DESKTOP


static func label(p: int) -> String:
	return "Web" if p == WEB else "Desktop"


static func wants_light(p: int, kind: String) -> bool:
	return p == DESKTOP or not DESKTOP_ONLY_LIGHTS.has(kind)


static func wants_shadow(p: int, kind: String, player_lane: bool, default: bool) -> bool:
	if p == DESKTOP:
		return default
	return kind == "PinSpot" and player_lane


static func apply(p: int, env: Environment, viewport: Viewport) -> void:
	if p == DESKTOP:
		viewport.msaa_3d = Viewport.MSAA_4X
		return
	viewport.msaa_3d = Viewport.MSAA_2X
	env.ssr_enabled = false
	env.ssao_enabled = false
	env.ssil_enabled = false
	env.sdfgi_enabled = false
	env.volumetric_fog_enabled = false
	env.ambient_light_energy *= 1.8
	env.glow_enabled = true
