from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from ui.render_utils import DEFAULT_TEXT_COLOR, draw_wrapped_text


CARD_PALETTES = {
    "starter_neutral": {
        "frame": (122, 74, 88),
        "frame_inner": (76, 48, 58),
        "panel": (34, 24, 32),
        "panel_alt": (54, 38, 48),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (196, 202, 218),
        "art_top": (88, 208, 220),
        "art_bottom": (28, 42, 74),
        "accent": (240, 196, 96),
        "glow": (170, 110, 132, 96),
    },
    "netrunner": {
        "frame": (68, 118, 124),
        "frame_inner": (30, 56, 60),
        "panel": (16, 24, 34),
        "panel_alt": (24, 40, 54),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (180, 236, 232),
        "art_top": (86, 242, 222),
        "art_bottom": (18, 60, 92),
        "accent": (110, 244, 222),
        "glow": (82, 224, 208, 96),
    },
}

CARD_TYPE_COLORS = {
    "attack": (226, 108, 108),
    "skill": (92, 198, 240),
    "power": (248, 192, 84),
}

CARD_EFFECT_COLORS = {
    "damage": (248, 112, 112),
    "block": (106, 216, 252),
    "heal": (120, 228, 152),
    "draw": (236, 188, 82),
    "energy": (248, 214, 114),
}


def card_type_label(card: dict[str, Any]) -> str:
    return str(card.get("type", "card")).title()


def resolve_card_theme(card: dict[str, Any]) -> dict[str, str]:
    raw_theme = card.get("theme") if isinstance(card.get("theme"), dict) else {}
    faction = raw_theme.get("faction", "starter")
    palette_key = raw_theme.get("palette")
    if not isinstance(palette_key, str) or not palette_key:
        palette_key = "netrunner" if faction == "netrunner" else "starter_neutral"
    art_style = raw_theme.get("art_style", "circuit_burst")
    return {
        "faction": faction,
        "palette": palette_key,
        "art_style": art_style,
    }


def resolve_card_palette(card: dict[str, Any]) -> dict[str, tuple[int, ...]]:
    theme = resolve_card_theme(card)
    return CARD_PALETTES.get(theme["palette"], CARD_PALETTES["starter_neutral"])


def effect_chip_entries(card: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for effect in card.get("effects", []):
        effect_type = effect.get("type")
        value = effect.get("value")
        if not isinstance(effect_type, str) or not isinstance(value, int):
            continue
        entries.append(
            {
                "label": _effect_label(effect_type, value),
                "fill": CARD_EFFECT_COLORS.get(effect_type, (168, 176, 200)),
            }
        )
    for effect in card.get("resource_effects", []):
        resource = effect.get("resource")
        delta = effect.get("delta")
        if not isinstance(resource, str) or not isinstance(delta, int):
            continue
        sign = "+" if delta >= 0 else "-"
        entries.append(
            {
                "label": f"{sign}{abs(delta)} {resource.title()}",
                "fill": (184, 134, 255),
            }
        )
    return entries


def resource_cost_entries(card: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for cost in card.get("resource_costs", []):
        resource = cost.get("resource")
        amount = cost.get("amount")
        if not isinstance(resource, str) or not isinstance(amount, int):
            continue
        entries.append(
            {
                "label": f"{amount} {resource.title()}",
                "fill": (112, 138, 220),
            }
        )
    return entries


def card_summary_lines(card: dict[str, Any], max_lines: int = 3) -> list[str]:
    lines = [_effect_line(effect) for effect in card.get("effects", [])]
    for effect in card.get("resource_effects", []):
        resource = effect.get("resource")
        delta = effect.get("delta")
        if isinstance(resource, str) and isinstance(delta, int):
            sign = "+" if delta >= 0 else "-"
            lines.append(f"{sign}{abs(delta)} {resource.title()}")
    return lines[:max_lines]


def compact_card_summary(card: dict[str, Any]) -> str:
    pieces = card_summary_lines(card, max_lines=2)
    if not pieces:
        return f"Cost {card.get('cost', 0)}"
    return f"Cost {card.get('cost', 0)} | {' | '.join(pieces)}"


def draw_card(
    surface: Any,
    rect_tuple: tuple[int, int, int, int],
    card: dict[str, Any],
    fonts: dict[str, Any],
    *,
    variant: str,
    shortcut_label: str | None = None,
    footer_label: str | None = None,
    note_label: str | None = None,
    selected: bool = False,
    hovered: bool = False,
    pressed: bool = False,
    disabled: bool = False,
    high_contrast: bool = False,
) -> None:
    if pygame is None or surface is None:
        return

    rect = pygame.Rect(*rect_tuple)
    palette = resolve_card_palette(card)
    if variant == "compact":
        _draw_compact_card(
            surface,
            rect,
            card,
            fonts,
            palette,
            shortcut_label=shortcut_label,
            footer_label=footer_label,
            note_label=note_label,
            selected=selected,
            hovered=hovered,
            pressed=pressed,
            disabled=disabled,
            high_contrast=high_contrast,
        )
        return

    _draw_full_card(
        surface,
        rect,
        card,
        fonts,
        palette,
        shortcut_label=shortcut_label,
        footer_label=footer_label,
        note_label=note_label,
        selected=selected,
        hovered=hovered,
        pressed=pressed,
        disabled=disabled,
        high_contrast=high_contrast,
    )


def _draw_full_card(
    surface: Any,
    rect: Any,
    card: dict[str, Any],
    fonts: dict[str, Any],
    palette: dict[str, tuple[int, ...]],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
    selected: bool,
    hovered: bool,
    pressed: bool,
    disabled: bool,
    high_contrast: bool,
) -> None:
    title_font = fonts["title"]
    body_font = fonts["body"]
    tiny_font = fonts["tiny"]
    type_color = CARD_TYPE_COLORS.get(str(card.get("type", "card")).lower(), palette["accent"])
    border_color = _border_color(
        palette=palette,
        selected=selected,
        hovered=hovered,
        pressed=pressed,
        disabled=disabled,
        high_contrast=high_contrast,
    )

    glow = pygame.Surface((rect.width + 24, rect.height + 24), pygame.SRCALPHA)
    pygame.draw.rect(glow, palette["glow"], glow.get_rect(), border_radius=24)
    surface.blit(glow, (rect.x - 12, rect.y - 12))

    pygame.draw.rect(surface, palette["frame"], rect, border_radius=18)
    pygame.draw.rect(surface, palette["frame_inner"], rect.inflate(-10, -10), border_radius=16)
    inner_rect = rect.inflate(-18, -18)
    pygame.draw.rect(surface, palette["panel"], inner_rect, border_radius=14)
    pygame.draw.rect(surface, border_color, rect, 3, border_radius=18)

    art_rect = pygame.Rect(inner_rect.x + 8, inner_rect.y + 28, inner_rect.width - 16, int(inner_rect.height * 0.38))
    _draw_art_panel(surface, art_rect, card, palette)

    ribbon_rect = pygame.Rect(inner_rect.x + 18, inner_rect.y + 6, inner_rect.width - 36, 28)
    pygame.draw.polygon(
        surface,
        type_color,
        [
            (ribbon_rect.x, ribbon_rect.centery),
            (ribbon_rect.x + 20, ribbon_rect.y),
            (ribbon_rect.right - 20, ribbon_rect.y),
            (ribbon_rect.right, ribbon_rect.centery),
            (ribbon_rect.right - 20, ribbon_rect.bottom),
            (ribbon_rect.x + 20, ribbon_rect.bottom),
        ],
    )
    draw_wrapped_text(
        surface,
        str(card.get("name", "Card")),
        (ribbon_rect.x + 22, ribbon_rect.y + 4),
        title_font,
        color=(22, 24, 34),
        width=ribbon_rect.width - 44,
    )

    medallion_center = (rect.x + 22, rect.y + 22)
    pygame.draw.circle(surface, (76, 40, 44), medallion_center, 18)
    pygame.draw.circle(surface, palette["accent"], medallion_center, 18, 4)
    cost_text = tiny_font.render(str(card.get("cost", 0)), True, palette["accent"])
    surface.blit(cost_text, cost_text.get_rect(center=medallion_center))

    type_chip_rect = pygame.Rect(art_rect.x + 10, art_rect.bottom - 18, 74, 20)
    _draw_chip(
        surface,
        type_chip_rect,
        card_type_label(card),
        fill=type_color,
        text_color=(20, 20, 28),
        font=tiny_font,
    )

    resource_costs = resource_cost_entries(card)
    chip_x = art_rect.right - 10
    for entry in reversed(resource_costs[:2]):
        width = max(52, tiny_font.size(entry["label"])[0] + 16)
        chip_rect = pygame.Rect(chip_x - width, art_rect.y + 8, width, 18)
        _draw_chip(surface, chip_rect, entry["label"], fill=entry["fill"], text_color=(18, 22, 34), font=tiny_font)
        chip_x -= width + 6

    box_rect = pygame.Rect(inner_rect.x + 8, art_rect.bottom + 8, inner_rect.width - 16, inner_rect.bottom - art_rect.bottom - 16)
    pygame.draw.rect(surface, palette["panel_alt"], box_rect, border_radius=12)
    pygame.draw.rect(surface, (86, 90, 110), box_rect, 1, border_radius=12)

    effect_entries = effect_chip_entries(card)
    _draw_wrapped_chip_list(surface, effect_entries, tiny_font, box_rect.x + 10, box_rect.y + 10, box_rect.width - 20, 18)

    summary_lines = card_summary_lines(card, max_lines=3)
    text_y = box_rect.y + 58
    for line in summary_lines:
        draw_wrapped_text(
            surface,
            line,
            (box_rect.x + 12, text_y),
            tiny_font,
            color=palette["text"],
            width=box_rect.width - 24,
        )
        text_y += tiny_font.get_linesize()

    if footer_label:
        draw_wrapped_text(
            surface,
            footer_label,
            (box_rect.x + 12, box_rect.bottom - 34),
            tiny_font,
            color=palette["muted"],
            width=box_rect.width - 24,
        )
    if note_label:
        draw_wrapped_text(
            surface,
            note_label,
            (box_rect.x + 12, box_rect.bottom - 18),
            tiny_font,
            color=(246, 128, 134) if disabled else palette["accent"],
            width=box_rect.width - 24,
        )

    if shortcut_label is not None:
        badge_rect = pygame.Rect(rect.x + 10, rect.bottom - 30, 22, 22)
        _draw_chip(surface, badge_rect, shortcut_label, fill=(18, 24, 36), text_color=palette["accent"], font=tiny_font, outline=palette["accent"])

    if disabled:
        dimmer = pygame.Surface(rect.size, pygame.SRCALPHA)
        dimmer.fill((8, 12, 18, 148))
        surface.blit(dimmer, rect.topleft)
        pygame.draw.rect(surface, (184, 94, 112), rect, 3, border_radius=18)


def _draw_compact_card(
    surface: Any,
    rect: Any,
    card: dict[str, Any],
    fonts: dict[str, Any],
    palette: dict[str, tuple[int, ...]],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
    selected: bool,
    hovered: bool,
    pressed: bool,
    disabled: bool,
    high_contrast: bool,
) -> None:
    title_font = fonts["title"]
    body_font = fonts["body"]
    tiny_font = fonts["tiny"]
    type_color = CARD_TYPE_COLORS.get(str(card.get("type", "card")).lower(), palette["accent"])
    border_color = _border_color(
        palette=palette,
        selected=selected,
        hovered=hovered,
        pressed=pressed,
        disabled=disabled,
        high_contrast=high_contrast,
    )

    pygame.draw.rect(surface, palette["frame"], rect, border_radius=16)
    pygame.draw.rect(surface, palette["frame_inner"], rect.inflate(-8, -8), border_radius=14)
    inner_rect = rect.inflate(-14, -14)
    pygame.draw.rect(surface, palette["panel"], inner_rect, border_radius=12)
    pygame.draw.rect(surface, border_color, rect, 3, border_radius=16)

    art_rect = pygame.Rect(inner_rect.right - max(54, inner_rect.width // 3), inner_rect.y + 6, max(48, inner_rect.width // 3) - 6, inner_rect.height - 12)
    _draw_art_panel(surface, art_rect, card, palette)

    medallion_center = (rect.x + 20, rect.y + 20)
    pygame.draw.circle(surface, (76, 40, 44), medallion_center, 16)
    pygame.draw.circle(surface, palette["accent"], medallion_center, 16, 3)
    cost_text = tiny_font.render(str(card.get("cost", 0)), True, palette["accent"])
    surface.blit(cost_text, cost_text.get_rect(center=medallion_center))

    title_x = rect.x + 42
    draw_wrapped_text(
        surface,
        str(card.get("name", "Card")),
        (title_x, rect.y + 8),
        title_font,
        color=palette["text"],
        width=art_rect.x - title_x - 10,
    )

    chip_width = max(54, tiny_font.size(card_type_label(card))[0] + 16)
    _draw_chip(
        surface,
        pygame.Rect(title_x, rect.y + 30, chip_width, 18),
        card_type_label(card),
        fill=type_color,
        text_color=(20, 22, 30),
        font=tiny_font,
    )

    cost_entries = resource_cost_entries(card)
    chip_x = title_x + chip_width + 8
    for entry in cost_entries[:2]:
        width = max(52, tiny_font.size(entry["label"])[0] + 16)
        _draw_chip(
            surface,
            pygame.Rect(chip_x, rect.y + 30, width, 18),
            entry["label"],
            fill=entry["fill"],
            text_color=(20, 22, 30),
            font=tiny_font,
        )
        chip_x += width + 6

    effect_entries = effect_chip_entries(card)
    _draw_wrapped_chip_list(
        surface,
        effect_entries[:3],
        tiny_font,
        title_x,
        rect.y + 54,
        art_rect.x - title_x - 10,
        18,
    )

    summary = compact_card_summary(card)
    draw_wrapped_text(
        surface,
        summary,
        (title_x, rect.bottom - 24),
        tiny_font,
        color=palette["muted"],
        width=art_rect.x - title_x - 10,
    )

    if shortcut_label is not None:
        badge_rect = pygame.Rect(rect.right - 28, rect.y + 8, 20, 20)
        _draw_chip(surface, badge_rect, shortcut_label, fill=(18, 24, 36), text_color=palette["accent"], font=tiny_font, outline=palette["accent"])

    if footer_label:
        draw_wrapped_text(surface, footer_label, (title_x, rect.bottom - 40), tiny_font, color=palette["muted"], width=art_rect.x - title_x - 10)
    if note_label:
        draw_wrapped_text(surface, note_label, (title_x, rect.bottom - 56), tiny_font, color=(246, 128, 134), width=art_rect.x - title_x - 10)

    if disabled:
        dimmer = pygame.Surface(rect.size, pygame.SRCALPHA)
        dimmer.fill((8, 12, 18, 120))
        surface.blit(dimmer, rect.topleft)
        pygame.draw.rect(surface, (184, 94, 112), rect, 3, border_radius=16)


def _draw_art_panel(
    surface: Any,
    rect: Any,
    card: dict[str, Any],
    palette: dict[str, tuple[int, ...]],
) -> None:
    art_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    art_surface.fill(palette["art_bottom"])
    pygame.draw.polygon(
        art_surface,
        (*palette["art_top"], 164),
        [
            (0, rect.height * 0.72),
            (rect.width * 0.2, rect.height * 0.14),
            (rect.width * 0.54, rect.height * 0.36),
            (rect.width * 0.82, 0),
            (rect.width, rect.height * 0.22),
            (rect.width, rect.height),
            (0, rect.height),
        ],
    )
    pygame.draw.circle(
        art_surface,
        (*palette["accent"], 108),
        (int(rect.width * 0.76), int(rect.height * 0.22)),
        max(12, rect.height // 5),
    )
    art_style = resolve_card_theme(card)["art_style"]
    if art_style == "circuit_burst":
        for index in range(4):
            start_x = 12 + (index * max(10, rect.width // 6))
            pygame.draw.line(
                art_surface,
                (255, 255, 255, 86),
                (start_x, rect.height - 10),
                (start_x + max(14, rect.width // 8), 10 + (index * 6)),
                2,
            )
    elif art_style == "signal_mesh":
        for index in range(5):
            offset_y = 12 + (index * max(8, rect.height // 7))
            pygame.draw.line(
                art_surface,
                (255, 255, 255, 70),
                (8, offset_y),
                (rect.width - 8, offset_y + (4 if index % 2 == 0 else -4)),
                1,
            )
    elif art_style == "patch_grid":
        cell_size = max(12, min(rect.width, rect.height) // 4)
        for cell_x in range(0, rect.width, cell_size):
            for cell_y in range(0, rect.height, cell_size):
                pygame.draw.rect(
                    art_surface,
                    (255, 255, 255, 36 if (cell_x + cell_y) // cell_size % 2 == 0 else 18),
                    pygame.Rect(cell_x + 2, cell_y + 2, cell_size - 4, cell_size - 4),
                    border_radius=4,
                )
    surface.blit(art_surface, rect.topleft)
    pygame.draw.rect(surface, (230, 236, 248), rect, 1, border_radius=12)


def _draw_wrapped_chip_list(
    surface: Any,
    entries: list[dict[str, Any]],
    font: Any,
    x: int,
    y: int,
    width: int,
    chip_height: int,
) -> None:
    cursor_x = x
    cursor_y = y
    row_bottom = y
    for entry in entries:
        label = entry["label"]
        chip_width = max(42, font.size(label)[0] + 16)
        if cursor_x + chip_width > x + width:
            cursor_x = x
            cursor_y = row_bottom + 6
        chip_rect = pygame.Rect(cursor_x, cursor_y, chip_width, chip_height)
        _draw_chip(surface, chip_rect, label, fill=entry["fill"], text_color=(16, 18, 28), font=font)
        cursor_x += chip_width + 6
        row_bottom = max(row_bottom, chip_rect.bottom)


def _draw_chip(
    surface: Any,
    rect: Any,
    label: str,
    *,
    fill: tuple[int, ...],
    text_color: tuple[int, int, int],
    font: Any,
    outline: tuple[int, ...] | None = None,
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=min(rect.height // 2, 10))
    if outline is not None:
        pygame.draw.rect(surface, outline, rect, 2, border_radius=min(rect.height // 2, 10))
    text_surface = font.render(label, True, text_color)
    surface.blit(text_surface, text_surface.get_rect(center=rect.center))


def _border_color(
    *,
    palette: dict[str, tuple[int, ...]],
    selected: bool,
    hovered: bool,
    pressed: bool,
    disabled: bool,
    high_contrast: bool,
) -> tuple[int, int, int]:
    if disabled:
        return (184, 94, 112)
    if pressed:
        return (255, 220, 122)
    if selected:
        return palette["accent"]
    if hovered:
        return (255, 255, 255)
    if high_contrast:
        return (214, 228, 248)
    return (126, 136, 164)


def _effect_label(effect_type: str, value: int) -> str:
    if effect_type == "damage":
        return f"{value} Dmg"
    if effect_type == "block":
        return f"{value} Block"
    if effect_type == "heal":
        return f"{value} Heal"
    if effect_type == "draw":
        return f"Draw {value}"
    if effect_type == "energy":
        return f"+{value} Energy"
    return f"{effect_type.title()} {value}"


def _effect_line(effect: dict[str, Any]) -> str:
    effect_type = effect.get("type")
    value = effect.get("value")
    if not isinstance(effect_type, str) or not isinstance(value, int):
        return ""
    if effect_type == "damage":
        return f"Deal {value} damage"
    if effect_type == "block":
        return f"Gain {value} block"
    if effect_type == "heal":
        return f"Heal {value}"
    if effect_type == "draw":
        return f"Draw {value}"
    if effect_type == "energy":
        return f"Gain {value} energy"
    return f"{effect_type.title()} {value}"
