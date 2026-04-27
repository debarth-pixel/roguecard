from __future__ import annotations

from dataclasses import dataclass

from config import SCREEN_HEIGHT, SCREEN_WIDTH

RectTuple = tuple[int, int, int, int]


@dataclass(frozen=True)
class CombatLayout:
    surface_size: tuple[int, int]
    safe_rect: RectTuple
    top_hud_rect: RectTuple
    top_resource_bar_rect: RectTuple
    turn_label_rect: RectTuple
    arena_rect: RectTuple
    player_status_rect: RectTuple
    deck_discard_rect: RectTuple
    hand_rect: RectTuple
    exhaust_rect: RectTuple
    end_turn_rect: RectTuple
    enemy_status_area_rect: RectTuple
    bottom_ui_rect: RectTuple
    card_platform_rect: RectTuple
    top_pause_rect: RectTuple
    top_intel_rect: RectTuple | None

    def debug_rects(self) -> dict[str, RectTuple]:
        return {
            "safe_rect": self.safe_rect,
            "top_hud_rect": self.top_hud_rect,
            "top_resource_bar_rect": self.top_resource_bar_rect,
            "turn_label_rect": self.turn_label_rect,
            "arena_rect": self.arena_rect,
            "player_status_rect": self.player_status_rect,
            "deck_discard_rect": self.deck_discard_rect,
            "hand_rect": self.hand_rect,
            "exhaust_rect": self.exhaust_rect,
            "end_turn_rect": self.end_turn_rect,
            "enemy_status_area_rect": self.enemy_status_area_rect,
        }


def build_combat_layout(
    surface_size: tuple[int, int] | None = None,
    *,
    intel_available: bool = True,
) -> CombatLayout:
    width, height = surface_size or (SCREEN_WIDTH, SCREEN_HEIGHT)
    width = max(640, int(width))
    height = max(360, int(height))

    safe_x = max(20, int(round(width * 0.03)))
    safe_y = max(16, int(round(height * 0.03)))
    safe_rect = (safe_x, safe_y, width - (safe_x * 2), height - (safe_y * 2))
    safe_right = _right(safe_rect)
    safe_bottom = _bottom(safe_rect)

    gap = max(12, int(round(width * 0.014)))
    top_band_h = _clamp(int(round(height * 0.16)), 94, 180)
    bottom_band_h = _clamp(int(round(height * 0.32)), 218, 430)
    if top_band_h + bottom_band_h > safe_rect[3] - 120:
        bottom_band_h = max(170, safe_rect[3] - top_band_h - 120)

    bottom_ui_rect = (safe_x, safe_bottom - bottom_band_h, safe_rect[2], bottom_band_h)
    bottom_top = bottom_ui_rect[1]

    pause_w = _clamp(int(round(width * 0.10)), 126, 210)
    pause_h = _clamp(int(round(height * 0.064)), 44, 72)
    top_pause_rect = (safe_right - pause_w, safe_y, pause_w, pause_h)
    intel_rect = None
    top_right_limit = top_pause_rect[0] - gap
    if intel_available:
        intel_w = _clamp(int(round(width * 0.064)), 78, 118)
        intel_rect = (top_right_limit - intel_w, safe_y, intel_w, pause_h)
        top_right_limit = intel_rect[0] - gap

    top_hud_x = safe_x + _clamp(int(round(width * 0.18)), 194, 360)
    top_hud_h = _clamp(int(round(height * 0.075)), 52, 84)
    top_hud_w = max(520, top_right_limit - top_hud_x)
    top_hud_rect = (top_hud_x, safe_y, top_hud_w, top_hud_h)

    resource_gap = max(8, int(round(height * 0.014)))
    resource_h = _clamp(int(round(height * 0.078)), 50, 86)
    top_resource_bar_rect = (
        top_hud_rect[0],
        _bottom(top_hud_rect) + resource_gap,
        top_hud_rect[2],
        resource_h,
    )

    turn_w = _clamp(int(round(width * 0.15)), 150, 260)
    turn_h = _clamp(int(round(height * 0.088)), 58, 96)
    turn_label_rect = (
        safe_x,
        safe_y + _clamp(int(round(height * 0.075)), 48, 88),
        turn_w,
        turn_h,
    )

    arena_top = max(_bottom(top_resource_bar_rect) + max(10, int(round(height * 0.012))), _bottom(turn_label_rect) + 4)
    arena_bottom = bottom_top - max(10, int(round(height * 0.018)))
    if arena_bottom <= arena_top + 90:
        arena_top = _bottom(top_resource_bar_rect) + 8
        arena_bottom = bottom_top - 6
    arena_rect = (safe_x, arena_top, safe_rect[2], max(90, arena_bottom - arena_top))

    left_w = _clamp(int(round(width * 0.27)), 310, 500)
    right_w = _clamp(int(round(width * 0.22)), 238, 420)
    if safe_rect[2] - left_w - right_w - (gap * 2) < 360:
        overflow = 360 - (safe_rect[2] - left_w - right_w - (gap * 2))
        left_w = max(250, left_w - ((overflow + 1) // 2))
        right_w = max(210, right_w - (overflow // 2))

    panel_gap = max(8, int(round(height * 0.012)))
    player_h = _clamp(int(round(height * 0.104)), 70, 124)
    player_status_rect = (
        safe_x,
        bottom_top + max(4, int(round(bottom_band_h * 0.02))),
        left_w,
        player_h,
    )
    deck_discard_rect = (
        safe_x,
        _bottom(player_status_rect) + panel_gap,
        left_w,
        max(68, safe_bottom - (_bottom(player_status_rect) + panel_gap)),
    )

    end_h = _clamp(int(round(height * 0.078)), 52, 86)
    end_turn_rect = (
        safe_right - right_w,
        safe_bottom - end_h,
        right_w,
        end_h,
    )
    exhaust_h = _clamp(int(round(height * 0.052)), 34, 56)
    exhaust_rect = (
        end_turn_rect[0],
        max(bottom_top, end_turn_rect[1] - exhaust_h - panel_gap),
        right_w,
        exhaust_h,
    )

    hand_x = safe_x + left_w + gap
    hand_right = safe_right - right_w - gap
    hand_rect = (
        hand_x,
        bottom_top + max(4, int(round(bottom_band_h * 0.02))),
        max(320, hand_right - hand_x),
        bottom_band_h - max(10, int(round(bottom_band_h * 0.04))),
    )
    card_platform_rect = _clamp_rect(
        (
            hand_rect[0] - max(14, int(round(width * 0.012))),
            hand_rect[1] + max(2, int(round(height * 0.006))),
            hand_rect[2] + max(28, int(round(width * 0.024))),
            hand_rect[3] - max(4, int(round(height * 0.012))),
        ),
        bottom_ui_rect,
    )

    status_h = _clamp(int(round(height * 0.12)), 62, 128)
    status_y = max(arena_rect[1], min(_bottom(arena_rect) - status_h, hand_rect[1] - status_h - panel_gap))
    enemy_status_area_rect = (
        arena_rect[0] + int(round(arena_rect[2] * 0.40)),
        status_y,
        int(round(arena_rect[2] * 0.58)),
        status_h,
    )

    return CombatLayout(
        surface_size=(width, height),
        safe_rect=safe_rect,
        top_hud_rect=top_hud_rect,
        top_resource_bar_rect=top_resource_bar_rect,
        turn_label_rect=turn_label_rect,
        arena_rect=arena_rect,
        player_status_rect=player_status_rect,
        deck_discard_rect=deck_discard_rect,
        hand_rect=hand_rect,
        exhaust_rect=exhaust_rect,
        end_turn_rect=end_turn_rect,
        enemy_status_area_rect=enemy_status_area_rect,
        bottom_ui_rect=bottom_ui_rect,
        card_platform_rect=card_platform_rect,
        top_pause_rect=top_pause_rect,
        top_intel_rect=intel_rect,
    )


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def _right(rect: RectTuple) -> int:
    return rect[0] + rect[2]


def _bottom(rect: RectTuple) -> int:
    return rect[1] + rect[3]


def _clamp_rect(rect: RectTuple, bounds: RectTuple) -> RectTuple:
    width = min(rect[2], bounds[2])
    height = min(rect[3], bounds[3])
    x = max(bounds[0], min(_right(bounds) - width, rect[0]))
    y = max(bounds[1], min(_bottom(bounds) - height, rect[1]))
    return (x, y, width, height)
