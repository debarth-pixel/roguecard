from __future__ import annotations

from typing import Any


DEFAULT_TEXT_COLOR = (240, 245, 255)


def clamp_scale(value: Any, minimum: float, maximum: float, fallback: float = 1.0) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = fallback
    return max(minimum, min(maximum, numeric_value))


def draw_wrapped_text(
    surface: Any,
    text: str | None,
    position: tuple[int, int],
    font: Any,
    color: tuple[int, int, int] = DEFAULT_TEXT_COLOR,
    width: int | None = None,
) -> None:
    if text is None:
        return

    if width is None:
        rendered = font.render(text, True, color)
        surface.blit(rendered, position)
        return

    words = text.split()
    line = ""
    x, y = position
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if font.size(candidate)[0] <= width:
            line = candidate
            continue
        if not line:
            rendered = font.render(word, True, color)
            surface.blit(rendered, (x, y))
            y += font.get_linesize()
            continue
        rendered = font.render(line, True, color)
        surface.blit(rendered, (x, y))
        y += font.get_linesize()
        line = word

    if line:
        rendered = font.render(line, True, color)
        surface.blit(rendered, (x, y))


def point_in_rect(point: tuple[int, int], rect: tuple[int, int, int, int]) -> bool:
    x, y, width, height = rect
    return x <= point[0] <= x + width and y <= point[1] <= y + height


def draw_screen_scrim(surface: Any, alpha: int = 120, color: tuple[int, int, int] = (6, 10, 18)) -> None:
    overlay = surface.copy()
    overlay.fill(color)
    overlay.set_alpha(alpha)
    surface.blit(overlay, (0, 0))
