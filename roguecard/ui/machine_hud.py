from __future__ import annotations

import math
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None


GLASS_DARK = (7, 16, 24)
GLASS_MID = (11, 22, 34)
GUNMETAL_DARK = (22, 26, 31)
GUNMETAL_MID = (42, 48, 55)
EDGE = (94, 107, 117)
CYAN = (39, 200, 255)
DIM_CYAN = (11, 110, 145)
HEALTH_RED = (232, 75, 85)
WARNING_ORANGE = (255, 154, 36)
YELLOW = (255, 209, 90)
PURPLE = (139, 77, 255)
ENEMY_RED = (255, 74, 95)
TEXT = (236, 244, 255)
MUTED = (132, 158, 184)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _lerp(start: float, end: float, progress: float) -> float:
    return start + ((end - start) * progress)


def _mix(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    progress: float,
) -> tuple[int, int, int]:
    progress = _clamp(progress, 0.0, 1.0)
    return tuple(int(_lerp(start[index], end[index], progress)) for index in range(3))


def _rect(value: Any) -> Any:
    return pygame.Rect(value)


def clipped_points(rect: Any, cut: int = 12) -> list[tuple[int, int]]:
    rect = _rect(rect)
    cut = max(0, min(cut, rect.width // 2, rect.height // 2))
    return [
        (rect.x + cut, rect.y),
        (rect.right - cut, rect.y),
        (rect.right, rect.y + cut),
        (rect.right, rect.bottom - cut),
        (rect.right - cut, rect.bottom),
        (rect.x + cut, rect.bottom),
        (rect.x, rect.bottom - cut),
        (rect.x, rect.y + cut),
    ]


def draw_clipped_panel(
    surface: Any,
    rect_value: Any,
    *,
    fill: tuple[int, int, int] | tuple[int, int, int, int] = (*GLASS_DARK, 232),
    border: tuple[int, int, int] = CYAN,
    cut: int = 12,
    border_width: int = 2,
    shadow: bool = True,
    glow: int = 0,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    if rect.width <= 0 or rect.height <= 0:
        return

    if glow > 0:
        glow_rect = rect.inflate(glow * 2, glow * 2)
        glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(
            glow_surface,
            (*border, min(72, 14 + glow * 3)),
            clipped_points(pygame.Rect(glow, glow, rect.width, rect.height), cut + glow // 2),
        )
        surface.blit(glow_surface, glow_rect.topleft)

    if shadow:
        shadow_rect = rect.move(0, 5).inflate(8, 8)
        shadow_surface = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(
            shadow_surface,
            (0, 0, 0, 84),
            clipped_points(pygame.Rect(4, 4, rect.width, rect.height), cut),
        )
        surface.blit(shadow_surface, shadow_rect.topleft)

    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    local_rect = panel.get_rect()
    points = clipped_points(local_rect, cut)
    pygame.draw.polygon(panel, fill, points)
    pygame.draw.polygon(panel, (*border, 218), points, border_width)

    bevel = clipped_points(local_rect.inflate(-6, -6), max(2, cut - 4))
    pygame.draw.lines(panel, (255, 255, 255, 28), False, bevel[:3], 1)
    pygame.draw.lines(panel, (0, 0, 0, 92), False, bevel[3:], 1)
    surface.blit(panel, rect.topleft)


def draw_scanlines(
    surface: Any,
    rect_value: Any,
    *,
    color: tuple[int, int, int] = CYAN,
    alpha: int = 14,
    step: int = 4,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    if rect.width <= 0 or rect.height <= 0:
        return
    lines = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y_pos in range(1, rect.height, max(2, step)):
        pygame.draw.line(lines, (*color, alpha), (0, y_pos), (rect.width, y_pos), 1)
    surface.blit(lines, rect.topleft)


def draw_bolts(surface: Any, rect_value: Any, *, color: tuple[int, int, int] = EDGE, radius: int = 3) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    inset = max(7, radius + 5)
    points = [
        (rect.x + inset, rect.y + inset),
        (rect.right - inset, rect.y + inset),
        (rect.x + inset, rect.bottom - inset),
        (rect.right - inset, rect.bottom - inset),
    ]
    for point in points:
        pygame.draw.circle(surface, (5, 7, 10), point, radius + 2)
        pygame.draw.circle(surface, color, point, radius)
        pygame.draw.line(surface, (12, 16, 20), (point[0] - radius, point[1]), (point[0] + radius, point[1]), 1)


def draw_micro_vents(surface: Any, rect_value: Any, *, accent: tuple[int, int, int] = WARNING_ORANGE) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    for index in range(5):
        x_pos = rect.x + 8 + (index * 7)
        pygame.draw.line(surface, (4, 6, 8), (x_pos, rect.y + 4), (x_pos + 4, rect.y + 4), 2)
        if index % 2 == 0:
            pygame.draw.line(surface, (*accent, 150), (x_pos, rect.y + 8), (x_pos + 4, rect.y + 8), 1)


def draw_data_capsule(
    surface: Any,
    rect_value: Any,
    *,
    label: str,
    font: Any,
    sublabel: str | None = None,
    subfont: Any | None = None,
    accent: tuple[int, int, int] = CYAN,
    active: bool = False,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    draw_clipped_panel(
        surface,
        rect,
        fill=(*GLASS_DARK, 230),
        border=_mix(DIM_CYAN, accent, 0.55 if active else 0.25),
        cut=10,
        border_width=1,
        shadow=False,
        glow=6 if active else 0,
    )
    inner = rect.inflate(-10, -8)
    pygame.draw.polygon(surface, (*GLASS_MID, 116), clipped_points(inner, 8))
    pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 10, rect.y + 13, 4, rect.height - 26), border_radius=2)
    draw_scanlines(surface, inner, alpha=10, step=3)
    text_x = rect.x + 24
    label_surface = font.render(label.upper(), True, TEXT)
    if sublabel and subfont is not None:
        surface.blit(label_surface, (text_x, rect.y + 8))
        sub_surface = subfont.render(sublabel.upper(), True, _mix(MUTED, accent, 0.55))
        surface.blit(sub_surface, (text_x, rect.y + 29))
    else:
        surface.blit(label_surface, label_surface.get_rect(midleft=(text_x, rect.centery)))


def draw_machine_button(
    surface: Any,
    rect_value: Any,
    *,
    label: str,
    font: Any,
    sublabel: str | None = None,
    subfont: Any | None = None,
    hovered: bool = False,
    pressed: bool = False,
    accent: tuple[int, int, int] = CYAN,
    warning: tuple[int, int, int] = ENEMY_RED,
    important: bool = False,
    enabled: bool = True,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    draw_rect = rect.move(0, 2 if pressed else 0)
    base_accent = accent if enabled else (72, 84, 98)
    glow = 12 if hovered and enabled else (6 if important and enabled else 0)
    face_fill = (7, 15, 24, 238) if not pressed else (5, 10, 16, 242)
    shell_fill = (24, 27, 31, 242) if enabled else (18, 21, 25, 232)
    draw_clipped_panel(surface, draw_rect, fill=shell_fill, border=EDGE, cut=13, border_width=2, glow=glow)

    face = draw_rect.inflate(-18 if important else -14, -14)
    draw_clipped_panel(
        surface,
        face,
        fill=face_fill,
        border=_mix(DIM_CYAN, base_accent, 0.85 if hovered else 0.62),
        cut=10,
        border_width=2,
        shadow=False,
    )
    draw_scanlines(surface, face.inflate(-4, -4), color=base_accent, alpha=13 if enabled else 7, step=3)

    side_width = 6 if important else 4
    pygame.draw.rect(surface, (*warning, 180), pygame.Rect(draw_rect.x + 11, draw_rect.centery - 10, side_width, 20), border_radius=2)
    pygame.draw.rect(surface, (*warning, 180), pygame.Rect(draw_rect.right - 11 - side_width, draw_rect.centery - 10, side_width, 20), border_radius=2)
    pygame.draw.circle(surface, YELLOW if enabled else (86, 78, 48), (draw_rect.centerx, draw_rect.bottom - 6), 3)
    draw_bolts(surface, draw_rect, radius=2)

    label_color = TEXT if enabled else (116, 128, 144)
    if pressed:
        label_color = _mix(label_color, base_accent, 0.22)
    label_surface = font.render(label.upper(), True, label_color)
    y_offset = -7 if sublabel and subfont is not None else 0
    surface.blit(label_surface, label_surface.get_rect(center=(draw_rect.centerx, draw_rect.centery + y_offset)))
    if sublabel and subfont is not None:
        sub_surface = subfont.render(sublabel.upper(), True, _mix(MUTED, base_accent, 0.72))
        surface.blit(sub_surface, sub_surface.get_rect(center=(draw_rect.centerx, draw_rect.centery + 13)))


def draw_relic_rail(surface: Any, rect_value: Any, *, slot_count: int, accent: tuple[int, int, int] = CYAN) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    draw_clipped_panel(surface, rect, fill=(*GUNMETAL_DARK, 238), border=EDGE, cut=15, border_width=2, glow=4)
    inner = rect.inflate(-18, -12)
    pygame.draw.rect(surface, (5, 10, 16), inner, border_radius=4)
    draw_scanlines(surface, inner, color=accent, alpha=8, step=4)
    pygame.draw.line(surface, (*accent, 155), (inner.x + 4, inner.y + 2), (inner.right - 4, inner.y + 2), 1)
    pygame.draw.line(surface, (*DIM_CYAN, 120), (inner.x + 4, inner.bottom - 2), (inner.right - 4, inner.bottom - 2), 1)
    draw_micro_vents(surface, pygame.Rect(rect.x + 10, rect.y + 8, 48, 18))
    draw_micro_vents(surface, pygame.Rect(rect.right - 58, rect.y + 8, 48, 18))
    pygame.draw.circle(surface, YELLOW, (rect.x + 22, rect.centery), 3)
    pygame.draw.circle(surface, YELLOW, (rect.right - 22, rect.centery), 3)
    del slot_count


def draw_relic_socket(
    surface: Any,
    rect_value: Any,
    *,
    filled: bool,
    hovered: bool = False,
    flash: float = 0.0,
    accent: tuple[int, int, int] = CYAN,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    flash = _clamp(flash, 0.0, 1.0)
    socket_border = _mix(DIM_CYAN, (255, 255, 255), flash * 0.75)
    if hovered:
        socket_border = YELLOW
    fill = (*((10, 16, 22) if filled else (7, 11, 16)), 232)
    draw_clipped_panel(
        surface,
        rect,
        fill=fill,
        border=socket_border,
        cut=9,
        border_width=2 if filled or hovered else 1,
        shadow=False,
        glow=8 if flash > 0.0 or hovered else 0,
    )
    inner = rect.inflate(-10, -10)
    pygame.draw.polygon(surface, (0, 0, 0, 72), clipped_points(inner, 7))
    draw_scanlines(surface, inner, color=accent, alpha=9 if filled else 5, step=3)
    if not filled:
        pygame.draw.line(surface, (*DIM_CYAN, 84), (inner.x + 6, inner.bottom - 5), (inner.right - 6, inner.bottom - 5), 1)


def draw_foreground_card_platform(surface: Any, rect_value: Any, *, accent: tuple[int, int, int] = CYAN) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    draw_clipped_panel(surface, rect, fill=(9, 13, 18, 218), border=EDGE, cut=22, border_width=2, shadow=False, glow=3)
    inner = rect.inflate(-34, -26)
    pygame.draw.polygon(surface, (4, 9, 14, 190), clipped_points(inner, 17))
    draw_scanlines(surface, inner, color=accent, alpha=8, step=3)
    pygame.draw.line(surface, (*accent, 130), (inner.x + 18, inner.y + 6), (inner.right - 18, inner.y + 6), 2)
    pygame.draw.line(surface, (*DIM_CYAN, 110), (inner.x + 18, inner.bottom - 6), (inner.right - 18, inner.bottom - 6), 1)

    for index in range(7):
        x_pos = rect.x + 92 + (index * 168)
        plate = pygame.Rect(x_pos, rect.y + 8, 108, 13)
        pygame.draw.rect(surface, GUNMETAL_MID, plate, border_radius=2)
        pygame.draw.line(surface, (128, 138, 146), plate.topleft, (plate.right, plate.y), 1)
        if index % 3 == 1:
            pygame.draw.line(surface, WARNING_ORANGE, (plate.x + 30, plate.y + 6), (plate.x + 54, plate.y + 6), 2)

    for x_pos in (rect.x + 32, rect.right - 88):
        pygame.draw.arc(surface, (72, 22, 20), pygame.Rect(x_pos, rect.y + 26, 74, 108), math.radians(96), math.radians(258), 5)
        pygame.draw.arc(surface, (8, 8, 10), pygame.Rect(x_pos + 9, rect.y + 30, 64, 102), math.radians(96), math.radians(258), 4)


def draw_ground_strip(surface: Any, rect_value: Any, *, accent: tuple[int, int, int] = DIM_CYAN) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    ground = pygame.Surface(rect.size, pygame.SRCALPHA)
    base = pygame.Rect(0, 0, rect.width, rect.height)
    pygame.draw.rect(ground, (28, 28, 29, 166), base)
    for row in range(rect.height):
        alpha = int(_lerp(20, 120, row / max(1, rect.height - 1)))
        pygame.draw.line(ground, (0, 0, 0, alpha), (0, row), (rect.width, row))

    for index in range(15):
        x_pos = int((index * 91 + 28) % rect.width)
        y_pos = int(20 + ((index * 37) % max(1, rect.height - 48)))
        w = 78 + ((index * 13) % 54)
        h = 18 + ((index * 7) % 24)
        color = (42 + (index % 3) * 8, 43 + (index % 2) * 8, 45 + (index % 4) * 5, 132)
        pygame.draw.polygon(
            ground,
            color,
            [
                (x_pos + 8, y_pos),
                (x_pos + w - 10, y_pos + 2),
                (x_pos + w, y_pos + h - 7),
                (x_pos + 12, y_pos + h),
                (x_pos, y_pos + 8),
            ],
        )

    for index in range(18):
        start = (int((index * 73 + 41) % rect.width), int((index * 29 + 18) % rect.height))
        mid = (start[0] + 22 + (index % 4) * 13, start[1] + ((-1) ** index) * (8 + index % 9))
        end = (mid[0] + 18 + (index % 5) * 11, mid[1] + 12)
        crack_color = (*accent, 82 if index % 4 == 0 else 42)
        pygame.draw.line(ground, (8, 9, 10, 145), start, mid, 2)
        pygame.draw.line(ground, (8, 9, 10, 145), mid, end, 2)
        if index % 4 == 0:
            pygame.draw.line(ground, crack_color, start, mid, 1)
            pygame.draw.line(ground, crack_color, mid, end, 1)

    for index in range(5):
        x_pos = 52 + index * 245
        plate = pygame.Rect(x_pos, rect.height - 28, 126, 20)
        pygame.draw.rect(ground, (30, 34, 38, 192), plate, border_radius=2)
        pygame.draw.rect(ground, (76, 86, 96, 150), plate, 1, border_radius=2)
        pygame.draw.line(ground, (*accent, 122), (plate.x + 10, plate.bottom - 4), (plate.right - 10, plate.bottom - 4), 1)

    fade = pygame.Surface(rect.size, pygame.SRCALPHA)
    for row in range(rect.height):
        edge_progress = min(row / 18.0, (rect.height - 1 - row) / 24.0, 1.0)
        alpha = int(_lerp(0, 255, _clamp(edge_progress, 0.0, 1.0)))
        pygame.draw.line(fade, (255, 255, 255, alpha), (0, row), (rect.width, row))
    ground.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(ground, rect.topleft)


def draw_card_pile_holder(
    surface: Any,
    rect_value: Any,
    *,
    label: str,
    value: int,
    font: Any,
    tiny_font: Any,
    accent: tuple[int, int, int] = CYAN,
    discard: bool = False,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    draw_clipped_panel(surface, rect, fill=(*GUNMETAL_DARK, 238), border=EDGE, cut=12, border_width=2, glow=4 if not discard else 2)
    inner = rect.inflate(-14, -14)
    draw_clipped_panel(surface, inner, fill=(*GLASS_DARK, 230), border=accent, cut=9, border_width=1, shadow=False)
    draw_scanlines(surface, inner.inflate(-4, -4), color=accent, alpha=9, step=3)

    stack_center = (inner.centerx, inner.y + 25)
    for offset in range(3):
        card = pygame.Rect(stack_center[0] - 13 + (offset * 3), stack_center[1] - 12 + (offset * 3), 24, 30)
        pygame.draw.rect(surface, (13, 20, 28), card, border_radius=2)
        pygame.draw.rect(surface, (*accent, 80 + offset * 35), card, 1, border_radius=2)
    pygame.draw.circle(surface, YELLOW if not discard else PURPLE, (rect.right - 12, rect.y + 18), 3)

    value_surface = font.render(str(value), True, TEXT)
    surface.blit(value_surface, value_surface.get_rect(center=(inner.centerx, inner.centery + 14)))
    label_surface = tiny_font.render(label.upper(), True, _mix(MUTED, accent, 0.75))
    surface.blit(label_surface, label_surface.get_rect(center=(inner.centerx, inner.bottom - 11)))


def drift_color(amount: float) -> tuple[int, int, int]:
    amount = _clamp(amount, 0.0, 1.0)
    if amount < 0.5:
        return _mix(CYAN, WARNING_ORANGE, amount / 0.5)
    return _mix(WARNING_ORANGE, HEALTH_RED, (amount - 0.5) / 0.5)


def draw_drift_gauge(surface: Any, rect_value: Any, *, amount: float, high_contrast: bool = False) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    amount = _clamp(amount, 0.0, 1.0)
    fill_color = drift_color(amount)
    dangerous = amount >= 0.72
    pulse = 0.5 + (0.5 * math.sin(pygame.time.get_ticks() / 120.0)) if dangerous else 0.0
    border = (244, 248, 255) if high_contrast else (_mix(DIM_CYAN, fill_color, 0.55 + (pulse * 0.35)))
    draw_clipped_panel(surface, rect, fill=(*GUNMETAL_DARK, 238), border=EDGE, cut=10, border_width=2, glow=8 if dangerous else 2)
    tube = rect.inflate(-12, -14)
    draw_clipped_panel(surface, tube, fill=(3, 9, 14, 234), border=border, cut=7, border_width=1, shadow=False)
    draw_scanlines(surface, tube.inflate(-4, -4), color=fill_color, alpha=12, step=5)

    if amount > 0.0:
        inner = tube.inflate(-7, -7)
        fill_height = max(2, int(inner.height * amount))
        fill_rect = pygame.Rect(inner.x, inner.bottom - fill_height, inner.width, fill_height)
        glow_alpha = 100 + int(80 * pulse)
        fill_surface = pygame.Surface(inner.size, pygame.SRCALPHA)
        local_fill = pygame.Rect(0, inner.height - fill_height, inner.width, fill_height)
        pygame.draw.rect(fill_surface, (*fill_color, 215), local_fill, border_radius=3)
        pygame.draw.rect(fill_surface, (*fill_color, glow_alpha), local_fill.inflate(4, 2), border_radius=4)
        surface.blit(fill_surface, inner.topleft)
        pygame.draw.line(surface, (255, 255, 255, 96), fill_rect.topleft, (fill_rect.right, fill_rect.y), 1)

    indicator = WARNING_ORANGE if amount >= 0.5 else YELLOW
    pygame.draw.polygon(
        surface,
        indicator,
        [(rect.centerx, rect.bottom - 7), (rect.centerx - 5, rect.bottom - 16), (rect.centerx + 5, rect.bottom - 16)],
    )


def draw_visor_overlay(surface: Any, *, alpha: int = 30, accent: tuple[int, int, int] = CYAN) -> None:
    if pygame is None or alpha <= 0:
        return
    width, height = surface.get_size()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    line_alpha = max(4, min(34, alpha))
    for y_pos in range(0, height, 4):
        pygame.draw.line(overlay, (*accent, line_alpha // 2), (0, y_pos), (width, y_pos), 1)

    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    for inset in range(0, 72, 8):
        shade = int(_lerp(alpha + 18, 0, inset / 72.0))
        pygame.draw.rect(vignette, (0, 0, 0, shade), pygame.Rect(inset, inset, width - inset * 2, height - inset * 2), 8)
    overlay.blit(vignette, (0, 0))

    arc_rect = pygame.Rect(int(width * 0.08), int(height * 0.08), int(width * 0.84), int(height * 0.76))
    pygame.draw.arc(overlay, (*accent, alpha + 12), arc_rect, math.radians(194), math.radians(346), 1)
    pygame.draw.arc(overlay, (*accent, alpha + 12), arc_rect, math.radians(14), math.radians(166), 1)
    center = (width // 2, int(height * 0.43))
    pygame.draw.line(overlay, (*accent, alpha + 28), (center[0] - 8, center[1]), (center[0] + 8, center[1]), 1)
    pygame.draw.line(overlay, (*accent, alpha + 28), (center[0], center[1] - 8), (center[0], center[1] + 8), 1)

    corner_len = 44
    for x_sign, y_sign in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x0 = 24 if x_sign > 0 else width - 24
        y0 = 24 if y_sign > 0 else height - 24
        pygame.draw.line(overlay, (*accent, alpha + 24), (x0, y0), (x0 + x_sign * corner_len, y0), 1)
        pygame.draw.line(overlay, (*accent, alpha + 24), (x0, y0), (x0, y0 + y_sign * corner_len), 1)

    for index in range(12):
        x_pos = int((index + 1) * width / 13)
        tick_h = 4 if index % 3 else 7
        pygame.draw.line(overlay, (*accent, alpha + 10), (x_pos, height - 18), (x_pos, height - 18 - tick_h), 1)

    surface.blit(overlay, (0, 0))


def draw_intent_frame(
    surface: Any,
    rect_value: Any,
    *,
    accent: tuple[int, int, int] = ENEMY_RED,
    high_contrast: bool = False,
) -> None:
    if pygame is None:
        return
    rect = _rect(rect_value)
    border = (245, 248, 255) if high_contrast else _mix(ENEMY_RED, accent, 0.35)
    draw_clipped_panel(surface, rect, fill=(6, 10, 18, 238), border=border, cut=10, border_width=2, shadow=True, glow=3)
    inner = rect.inflate(-8, -8)
    draw_scanlines(surface, inner, color=ENEMY_RED, alpha=12, step=3)
    icon_compartment = pygame.Rect(rect.x + 7, rect.y + 6, 30, rect.height - 12)
    draw_clipped_panel(surface, icon_compartment, fill=(34, 9, 15, 216), border=ENEMY_RED, cut=7, border_width=1, shadow=False)
    pygame.draw.line(surface, (*ENEMY_RED, 168), (rect.right - 18, rect.y + 9), (rect.right - 10, rect.y + 9), 1)
    pygame.draw.line(surface, (*ENEMY_RED, 168), (rect.right - 18, rect.bottom - 9), (rect.right - 10, rect.bottom - 9), 1)
