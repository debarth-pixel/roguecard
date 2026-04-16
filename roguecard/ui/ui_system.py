from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

SPACE_1 = 8
SPACE_2 = 12
SPACE_3 = 16
SPACE_4 = 24
SPACE_5 = 32

RADIUS_SM = 10
RADIUS_MD = 16
RADIUS_LG = 24

BORDER_LIGHT = 1
BORDER_ACTIVE = 2

COLOR_TEXT = (240, 245, 255)
COLOR_MUTED = (156, 172, 196)
COLOR_MUTED_SOFT = (118, 132, 156)
COLOR_PANEL = (11, 17, 27)
COLOR_PANEL_ELEVATED = (16, 24, 38)
COLOR_PANEL_SOFT = (20, 28, 42)
COLOR_LINE = (70, 88, 116)
COLOR_LINE_SOFT = (44, 56, 78)
COLOR_GOLD = (255, 214, 110)
COLOR_CYAN = (104, 214, 246)
COLOR_GREEN = (122, 226, 182)
COLOR_RED = (236, 108, 124)


def fill_vertical_gradient(
    surface: Any,
    rect_value: Any,
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
) -> None:
    if pygame is None:
        return
    rect = pygame.Rect(rect_value)
    if rect.width <= 0 or rect.height <= 0:
        return
    for offset in range(rect.height):
        progress = offset / max(1, rect.height - 1)
        color = tuple(
            int(top_color[index] + ((bottom_color[index] - top_color[index]) * progress))
            for index in range(3)
        )
        pygame.draw.line(surface, color, (rect.x, rect.y + offset), (rect.right - 1, rect.y + offset))


def draw_background_stage(
    surface: Any,
    background: Any | None,
    *,
    veil_alpha: int = 164,
    left_veil_width: int = 0,
    top_band_height: int = 74,
    bottom_band_height: int = 112,
    line_step: int = 0,
    line_alpha: int = 12,
    accent: tuple[int, int, int] = COLOR_CYAN,
) -> None:
    if pygame is None or surface is None:
        return

    if background is not None:
        surface.blit(background, (0, 0))
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((5, 9, 16, veil_alpha))
    surface.blit(overlay, (0, 0))

    width, height = surface.get_size()
    if left_veil_width > 0:
        left_rect = pygame.Rect(0, 0, min(width, left_veil_width), height)
        left_surface = pygame.Surface(left_rect.size, pygame.SRCALPHA)
        fill_vertical_gradient(left_surface, left_surface.get_rect(), (10, 16, 28), (4, 8, 14))
        left_surface.set_alpha(208)
        surface.blit(left_surface, left_rect.topleft)

    if top_band_height > 0:
        band = pygame.Surface((width, top_band_height), pygame.SRCALPHA)
        fill_vertical_gradient(band, band.get_rect(), (8, 12, 20), (8, 12, 20))
        band.set_alpha(94)
        surface.blit(band, (0, 0))

    if bottom_band_height > 0:
        band = pygame.Surface((width, bottom_band_height), pygame.SRCALPHA)
        fill_vertical_gradient(band, band.get_rect(), (4, 8, 14), (10, 14, 20))
        band.set_alpha(164)
        surface.blit(band, (0, height - bottom_band_height))

    if line_step > 0:
        line_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for y in range(0, height, line_step):
            pygame.draw.line(line_surface, (*accent, line_alpha), (0, y), (width, y), 1)
        surface.blit(line_surface, (0, 0))


def draw_panel(
    surface: Any,
    rect_value: Any,
    *,
    accent: tuple[int, int, int] = COLOR_LINE,
    fill: tuple[int, int, int] = COLOR_PANEL,
    radius: int = RADIUS_LG,
    border_width: int = BORDER_LIGHT,
    shadow_alpha: int = 56,
    shadow_offset: int = 10,
) -> None:
    if pygame is None:
        return
    rect = pygame.Rect(rect_value)
    if shadow_alpha > 0:
        shadow_surface = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surface,
            (0, 0, 0, shadow_alpha),
            pygame.Rect(10, 10 + shadow_offset, rect.width, rect.height),
            border_radius=radius + 2,
        )
        surface.blit(shadow_surface, (rect.x - 10, rect.y - 10))
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, accent, rect, border_width, border_radius=radius)


def draw_rule(surface: Any, start: tuple[int, int], end: tuple[int, int], *, color: tuple[int, int, int] = COLOR_LINE_SOFT) -> None:
    if pygame is None:
        return
    pygame.draw.line(surface, color, start, end, 1)


def draw_focus_glow(
    surface: Any,
    rect_value: Any,
    *,
    accent: tuple[int, int, int] = COLOR_CYAN,
    alpha: int = 42,
    inflate_x: int = 18,
    inflate_y: int = 18,
    radius: int = RADIUS_LG,
) -> None:
    if pygame is None:
        return
    rect = pygame.Rect(rect_value).inflate(inflate_x, inflate_y)
    glow = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(glow, (*accent, alpha), glow.get_rect(), border_radius=radius)
    surface.blit(glow, rect.topleft)


def draw_accent_label(
    surface: Any,
    font: Any,
    label: str,
    position: tuple[int, int],
    *,
    accent: tuple[int, int, int] = COLOR_GOLD,
) -> None:
    if pygame is None:
        return
    rendered = font.render(label, True, accent)
    surface.blit(rendered, position)


def draw_hint_row(
    surface: Any,
    rect_value: Any,
    *,
    left_text: str,
    right_text: str | None = None,
    font: Any,
    accent: tuple[int, int, int] = COLOR_LINE,
    fill: tuple[int, int, int] = COLOR_PANEL,
    text_color: tuple[int, int, int] = COLOR_MUTED,
) -> None:
    if pygame is None:
        return
    rect = pygame.Rect(rect_value)
    draw_panel(surface, rect, accent=accent, fill=fill, radius=RADIUS_MD, border_width=BORDER_LIGHT, shadow_alpha=0)
    left = font.render(left_text, True, text_color)
    surface.blit(left, (rect.x + SPACE_3, rect.y + max(4, (rect.height - left.get_height()) // 2)))
    if right_text:
        right = font.render(right_text, True, COLOR_MUTED_SOFT)
        surface.blit(right, right.get_rect(midright=(rect.right - SPACE_3, rect.y + (rect.height // 2))))


def draw_chip(
    surface: Any,
    rect_value: Any,
    *,
    label: str,
    font: Any,
    accent: tuple[int, int, int],
    fill: tuple[int, int, int] = COLOR_PANEL_SOFT,
    text_color: tuple[int, int, int] | None = None,
    active: bool = False,
) -> None:
    if pygame is None:
        return
    rect = pygame.Rect(rect_value)
    border_width = BORDER_ACTIVE if active else BORDER_LIGHT
    draw_panel(surface, rect, accent=accent, fill=fill, radius=RADIUS_MD, border_width=border_width, shadow_alpha=0)
    rendered = font.render(label, True, text_color or COLOR_TEXT)
    surface.blit(rendered, rendered.get_rect(center=rect.center))


def draw_metric_tile(
    surface: Any,
    rect_value: Any,
    *,
    label: str,
    value: str,
    title_font: Any,
    body_font: Any,
    accent: tuple[int, int, int],
    active: bool = False,
) -> None:
    if pygame is None:
        return
    rect = pygame.Rect(rect_value)
    draw_panel(
        surface,
        rect,
        accent=accent if active else COLOR_LINE,
        fill=COLOR_PANEL_ELEVATED,
        radius=RADIUS_MD,
        border_width=BORDER_ACTIVE if active else BORDER_LIGHT,
        shadow_alpha=0,
    )
    pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 10, rect.y + 12, 4, rect.height - 24), border_radius=2)
    label_surface = body_font.render(label, True, COLOR_MUTED)
    value_surface = title_font.render(value, True, COLOR_TEXT)
    surface.blit(label_surface, (rect.x + 22, rect.y + 10))
    surface.blit(value_surface, (rect.x + 22, rect.y + 30))


def draw_modal_scrim(surface: Any, *, alpha: int = 196) -> None:
    if pygame is None:
        return
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((4, 8, 14, alpha))
    surface.blit(overlay, (0, 0))
