from __future__ import annotations

from typing import Any


DEFAULT_TEXT_COLOR = (240, 245, 255)


def clamp_scale(value: Any, minimum: float, maximum: float, fallback: float = 1.0) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        numeric_value = fallback
    return max(minimum, min(maximum, numeric_value))


def fit_design_frame(
    screen_size: tuple[int, int],
    design_size: tuple[int, int] = (1280, 720),
    *,
    min_padding: int = 18,
    padding_ratio: float = 0.04,
) -> tuple[int, int, int, int]:
    screen_width = max(1, int(screen_size[0]))
    screen_height = max(1, int(screen_size[1]))
    design_width = max(1, int(design_size[0]))
    design_height = max(1, int(design_size[1]))

    padding_x = min(screen_width // 4, max(min_padding, int(round(screen_width * padding_ratio))))
    padding_y = min(screen_height // 4, max(min_padding, int(round(screen_height * padding_ratio))))
    available_width = max(1, screen_width - (padding_x * 2))
    available_height = max(1, screen_height - (padding_y * 2))
    scale = min(available_width / design_width, available_height / design_height)
    frame_width = max(1, int(round(design_width * scale)))
    frame_height = max(1, int(round(design_height * scale)))
    frame_x = (screen_width - frame_width) // 2
    frame_y = (screen_height - frame_height) // 2
    return (frame_x, frame_y, frame_width, frame_height)


def scale_design_rect(
    rect: tuple[int, int, int, int],
    frame: tuple[int, int, int, int],
    design_size: tuple[int, int] = (1280, 720),
) -> tuple[int, int, int, int]:
    design_width = max(1, int(design_size[0]))
    design_height = max(1, int(design_size[1]))
    frame_x, frame_y, frame_width, frame_height = frame
    x, y, width, height = rect
    scaled_x = frame_x + int(round((x / design_width) * frame_width))
    scaled_y = frame_y + int(round((y / design_height) * frame_height))
    scaled_width = max(1, int(round((width / design_width) * frame_width)))
    scaled_height = max(1, int(round((height / design_height) * frame_height)))
    return (scaled_x, scaled_y, scaled_width, scaled_height)


def design_frame_scale(
    frame: tuple[int, int, int, int],
    design_size: tuple[int, int] = (1280, 720),
) -> float:
    design_width = max(1, int(design_size[0]))
    design_height = max(1, int(design_size[1]))
    return min(frame[2] / design_width, frame[3] / design_height)


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
