from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from ui.card_style import (
    CARD_COMPACT_LAYOUT_SPEC,
    CARD_PORTRAIT_LAYOUT_SPEC,
    CARD_TYPOGRAPHY,
    resolve_card_theme,
)
from ui.render_utils import draw_wrapped_text

_CARD_FONT_CACHE: dict[tuple[int, bool], Any] = {}


def card_type_label(card: dict[str, Any]) -> str:
    return str(card.get("type", "card")).title()


def get_card_theme(card: dict[str, Any]) -> dict[str, Any]:
    return resolve_card_theme(card)


def concise_card_rules(card: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for effect in card.get("effects", []):
        line = _effect_line(effect)
        if line:
            lines.append(line)
    for trigger in card.get("triggers", []):
        line = _trigger_line(trigger)
        if line:
            lines.append(line)
    for effect in card.get("resource_effects", []):
        line = _resource_effect_line(effect)
        if line:
            lines.append(line)
    for keyword in _keyword_face_lines(card):
        if keyword:
            lines.append(keyword)
    if not lines:
        return ["No effect."]
    return lines[:2]


def inspect_card_rules(card: dict[str, Any]) -> list[str]:
    lines = list(concise_card_rules(card))
    extra_trigger_lines = [
        line
        for line in (_trigger_line(trigger) for trigger in card.get("triggers", []))
        if line and line not in lines
    ]
    lines.extend(extra_trigger_lines)
    for cost in card.get("resource_costs", []):
        line = _resource_cost_line(cost)
        if line:
            lines.append(line)
    for keyword in _keyword_face_lines(card):
        if keyword and keyword not in lines:
            lines.append(keyword)
    return lines


def primary_effect_text(card: dict[str, Any]) -> str:
    lines = concise_card_rules(card)
    return lines[0] if lines else card_type_label(card)


def secondary_effect_lines(card: dict[str, Any]) -> list[str]:
    lines = concise_card_rules(card)
    return lines[1:]


def card_summary_lines(card: dict[str, Any], max_lines: int = 3) -> list[str]:
    return inspect_card_rules(card)[:max_lines]


def compact_card_summary(card: dict[str, Any]) -> str:
    return " ".join(concise_card_rules(card)[:2]).strip() or card_type_label(card)


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
    card_theme = get_card_theme(card)
    layout = resolve_card_layout(rect, variant)
    typography = _card_fonts(rect.height, fonts)
    interaction = {
        "selected": selected,
        "hovered": hovered,
        "pressed": pressed,
        "disabled": disabled,
        "high_contrast": high_contrast,
    }
    render_card_base(
        surface,
        layout,
        card,
        card_theme,
        typography,
        interaction,
        shortcut_label=shortcut_label,
        footer_label=footer_label,
        note_label=note_label,
    )


def resolve_card_layout(rect: Any, variant: str) -> dict[str, Any]:
    if variant == "compact":
        return _resolve_compact_layout(rect)
    return _resolve_full_layout(rect)


def render_card_base(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
    fonts: dict[str, Any],
    interaction: dict[str, bool],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
) -> None:
    render_card_frame(surface, layout, card_theme, interaction)
    render_card_art_panel(surface, layout, card, card_theme)
    render_card_text_regions(
        surface,
        layout,
        card,
        card_theme,
        fonts,
        interaction,
        shortcut_label=shortcut_label,
        footer_label=footer_label,
        note_label=note_label,
    )
    render_card_interaction_state(surface, layout, card_theme, interaction)


def render_card_frame(
    surface: Any,
    layout: dict[str, Any],
    card_theme: dict[str, Any],
    interaction: dict[str, bool],
) -> None:
    if pygame is None:
        return

    card_rect = layout["card_rect"]
    type_theme = card_theme["type_theme"]
    outer_border = max(2, int(card_rect.width * 0.016))
    inner_border = max(1, int(card_rect.width * 0.009))
    body_inset = max(8, int(card_rect.width * 0.042))

    shadow_surface = pygame.Surface((card_rect.width + 18, card_rect.height + 18), pygame.SRCALPHA)
    shadow_rect = shadow_surface.get_rect()
    _draw_theme_shape(
        shadow_surface,
        shadow_rect.move(0, 6),
        type_theme,
        (*type_theme["outer_shadow"], 144),
    )
    surface.blit(shadow_surface, (card_rect.x - 9, card_rect.y - 9))

    _draw_glow(surface, card_rect, type_theme, interaction)
    _draw_theme_shape(surface, card_rect, type_theme, type_theme["outer_fill"])
    _draw_theme_shape(surface, card_rect.inflate(-outer_border * 2, -outer_border * 2), type_theme, type_theme["outer_shadow"])
    _draw_theme_shape(surface, card_rect.inflate(-body_inset, -body_inset), type_theme, type_theme["body_fill"])

    title_top, title_bottom = _interaction_title_colors(type_theme, interaction)
    _blit_gradient_shape(surface, layout["title_strip"], card_theme, title_top, title_bottom, shape_key="title_shape")
    _draw_theme_outline(surface, layout["title_strip"], card_theme, type_theme["accent_soft"], max(1, inner_border), shape_key="title_shape")
    _draw_title_motif(surface, layout["title_strip"], card_theme)

    _draw_panel_box(
        surface,
        layout["mid_band"],
        type_theme["mid_band_fill"],
        type_theme["mid_band_border"],
        compact=layout["variant"] == "compact",
    )
    _draw_panel_box(surface, layout["description_box"], type_theme["description_fill"], type_theme["description_border"])
    _draw_panel_box(surface, layout["metadata_band"], type_theme["metadata_fill"], type_theme["description_border"], subtle=True)
    _draw_cost_orb(surface, layout["cost_orb"], type_theme, interaction)


def render_card_art_panel(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
) -> None:
    if pygame is None:
        return

    art_rect = layout["art_panel"]
    type_theme = card_theme["type_theme"]
    art_palette = card_theme["art_palette"]

    _blit_gradient_shape(
        surface,
        art_rect,
        card_theme,
        art_palette["art_top"],
        art_palette["art_bottom"],
        shape_key="art_shape",
    )
    _draw_art_style_overlay(surface, art_rect, card_theme, card)
    _draw_theme_outline(
        surface,
        art_rect,
        card_theme,
        type_theme["art_border"],
        max(1, int(layout["card_rect"].width * 0.009)),
        shape_key="art_shape",
    )


def render_card_text_regions(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
    fonts: dict[str, Any],
    interaction: dict[str, bool],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
) -> None:
    type_theme = card_theme["type_theme"]
    cost_surface = fonts["cost"].render(str(card.get("cost", 0)), True, type_theme["cost_text"])
    surface.blit(cost_surface, cost_surface.get_rect(center=layout["cost_orb"].center))

    title_rect = layout["title_strip"]
    title_text_rect = title_rect.inflate(-max(10, int(title_rect.width * 0.08)), 0)
    title_text_rect.width -= layout.get("title_pip_width", 0)
    title_text = _fit_text_ellipsis(str(card.get("name", "Card")), fonts["title"], title_text_rect.width)
    title_surface = fonts["title"].render(title_text, True, type_theme["title_text"])
    surface.blit(
        title_surface,
        (title_text_rect.x, title_text_rect.y + max(2, (title_text_rect.height - title_surface.get_height()) // 2)),
    )

    if layout["variant"] == "full":
        _draw_type_pip(surface, layout["title_pip_rect"], card_theme, interaction)

    if layout["variant"] == "full":
        _draw_primary_effect_block(surface, layout, card, fonts, type_theme)
    else:
        _draw_compact_rules(surface, layout, card, fonts, type_theme)

    metadata_text = note_label or footer_label
    metadata_color = type_theme["accent_soft"] if note_label else type_theme["muted"]
    metadata_text_x = layout["metadata_band"].x + 8
    if shortcut_label is not None:
        badge_size = min(layout["metadata_band"].height - 4, max(16, int(layout["card_rect"].height * 0.05)))
        badge_rect = pygame.Rect(layout["metadata_band"].x + 4, layout["metadata_band"].y + 2, badge_size, badge_size)
        _draw_chip(
            surface,
            badge_rect,
            shortcut_label,
            fill=(18, 24, 36),
            text_color=type_theme["accent"],
            font=fonts["meta"],
            outline=type_theme["accent"],
        )
        metadata_text_x = badge_rect.right + 8

    if metadata_text:
        draw_wrapped_text(
            surface,
            metadata_text,
            (metadata_text_x, layout["metadata_band"].y + 2),
            fonts["meta"],
            color=metadata_color,
            width=max(8, layout["metadata_band"].right - metadata_text_x - 8),
        )


def render_card_interaction_state(
    surface: Any,
    layout: dict[str, Any],
    card_theme: dict[str, Any],
    interaction: dict[str, bool],
) -> None:
    if pygame is None:
        return

    card_rect = layout["card_rect"]
    type_theme = card_theme["type_theme"]
    ring_color = _frame_border_color(type_theme, interaction)
    ring_width = max(2, int(card_rect.width * 0.016))

    _draw_theme_outline(surface, card_rect, card_theme, ring_color, ring_width)

    if interaction["selected"]:
        ring_rect = card_rect.inflate(max(8, int(card_rect.width * 0.03)), max(10, int(card_rect.width * 0.04)))
        ring_surface = pygame.Surface((ring_rect.width, ring_rect.height), pygame.SRCALPHA)
        _draw_theme_outline(
            ring_surface,
            ring_surface.get_rect(),
            card_theme,
            (*type_theme["accent_soft"], 188),
            max(2, ring_width - 1),
        )
        surface.blit(ring_surface, ring_rect.topleft)

    if interaction["pressed"]:
        press_surface = pygame.Surface(card_rect.size, pygame.SRCALPHA)
        _draw_theme_shape(press_surface, press_surface.get_rect(), type_theme, (255, 245, 220, 24))
        surface.blit(press_surface, card_rect.topleft)

    if interaction["disabled"]:
        dimmer = pygame.Surface(card_rect.size, pygame.SRCALPHA)
        dimmer.fill((8, 12, 18, 132))
        surface.blit(dimmer, card_rect.topleft)


def _resolve_full_layout(rect: Any) -> dict[str, Any]:
    title_rect = _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["title_strip"])
    pip_width = max(16, int(title_rect.width * CARD_PORTRAIT_LAYOUT_SPEC["title_pip_ratio"]))
    return {
        "variant": "full",
        "card_rect": rect,
        "cost_orb": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["cost_orb"]),
        "title_strip": title_rect,
        "title_pip_rect": pygame.Rect(
            title_rect.right - pip_width - 4,
            title_rect.y + 4,
            pip_width,
            max(12, title_rect.height - 8),
        ),
        "title_pip_width": pip_width,
        "art_panel": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["art_panel"]),
        "mid_band": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["mid_band"]),
        "primary_effect": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["primary_effect"]),
        "description_box": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["description_box"]),
        "metadata_band": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["metadata_band"]),
    }


def _resolve_compact_layout(rect: Any) -> dict[str, Any]:
    cost_size = max(18, int(min(rect.width * CARD_COMPACT_LAYOUT_SPEC["cost_orb"]["size"], rect.height * 0.46)))
    title_strip = _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["title_strip"])
    return {
        "variant": "compact",
        "card_rect": rect,
        "cost_orb": pygame.Rect(
            rect.x + int(rect.width * CARD_COMPACT_LAYOUT_SPEC["cost_orb"]["x"]),
            rect.y + int(rect.height * CARD_COMPACT_LAYOUT_SPEC["cost_orb"]["y"]),
            cost_size,
            cost_size,
        ),
        "title_strip": title_strip,
        "title_pip_rect": pygame.Rect(
            title_strip.right - max(12, int(title_strip.width * 0.14)),
            title_strip.y + 2,
            max(12, int(title_strip.width * 0.12)),
            max(10, title_strip.height - 4),
        ),
        "title_pip_width": 0,
        "art_panel": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["art_panel"]),
        "mid_band": pygame.Rect(
            title_strip.x,
            title_strip.bottom + 6,
            max(36, title_strip.width),
            max(14, int(rect.height * 0.10)),
        ),
        "primary_effect": pygame.Rect(
            title_strip.x,
            title_strip.bottom + 6,
            max(18, title_strip.width),
            max(18, int(rect.height * 0.14)),
        ),
        "type_label": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["type_label"]),
        "description_box": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["summary_box"]),
        "metadata_band": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["metadata"]),
    }


def _card_fonts(card_height: int, fallback_fonts: dict[str, Any]) -> dict[str, Any]:
    if pygame is None:
        return fallback_fonts
    return {
        "cost": _cached_font(int(card_height * CARD_TYPOGRAPHY["cost"]), bold=True),
        "title": _cached_font(int(card_height * CARD_TYPOGRAPHY["title"]), bold=True),
        "type": _cached_font(int(card_height * CARD_TYPOGRAPHY["type_label"]), bold=True),
        "primary_value": _cached_font(int(card_height * CARD_TYPOGRAPHY["primary_value"]), bold=True),
        "primary_support": _cached_font(int(card_height * CARD_TYPOGRAPHY["primary_support"]), bold=True),
        "description": _cached_font(int(card_height * CARD_TYPOGRAPHY["description"])),
        "meta": _cached_font(int(card_height * CARD_TYPOGRAPHY["metadata"]), bold=True),
    }


def _cached_font(size: int, bold: bool = False) -> Any:
    if pygame is None:
        return None
    size = max(10, size)
    cache_key = (size, bold)
    if cache_key not in _CARD_FONT_CACHE:
        _CARD_FONT_CACHE[cache_key] = pygame.font.SysFont("consolas", size, bold=bold)
    return _CARD_FONT_CACHE[cache_key]


def _scale_region(rect: Any, spec: dict[str, float]) -> Any:
    return pygame.Rect(
        rect.x + int(rect.width * spec["x"]),
        rect.y + int(rect.height * spec["y"]),
        max(1, int(rect.width * spec["w"])),
        max(1, int(rect.height * spec["h"])),
    )


def _draw_glow(surface: Any, rect: Any, type_theme: dict[str, Any], interaction: dict[str, bool]) -> None:
    if pygame is None:
        return
    glow_pad = max(10, int(rect.width * 0.08))
    glow_alpha = type_theme["accent_glow"][3]
    if interaction["hovered"]:
        glow_alpha = min(180, glow_alpha + 42)
    if interaction["selected"]:
        glow_alpha = min(220, glow_alpha + 62)
    if interaction["disabled"]:
        glow_alpha = max(24, glow_alpha // 3)

    glow_surface = pygame.Surface((rect.width + (glow_pad * 2), rect.height + (glow_pad * 2)), pygame.SRCALPHA)
    glow_rect = glow_surface.get_rect()
    _draw_theme_shape(
        glow_surface,
        glow_rect.inflate(-max(0, glow_pad // 2), -max(0, glow_pad // 2)),
        type_theme,
        (*type_theme["accent"], glow_alpha),
    )
    surface.blit(glow_surface, (rect.x - glow_pad, rect.y - glow_pad))


def _draw_panel_box(
    surface: Any,
    rect: Any,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    *,
    compact: bool = False,
    subtle: bool = False,
) -> None:
    radius = max(8, int(rect.width * (0.032 if compact else 0.04)))
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    outline = border if not subtle else _blend_color(border, (18, 22, 30), 0.35)
    pygame.draw.rect(surface, outline, rect, 2 if not subtle else 1, border_radius=radius)


def _draw_cost_orb(surface: Any, rect: Any, type_theme: dict[str, Any], interaction: dict[str, bool]) -> None:
    center = rect.center
    radius = min(rect.width, rect.height) // 2
    ring_width = max(2, int(rect.width * 0.12))
    ring_color = type_theme["cost_ring"] if not interaction["disabled"] else _blend_color(type_theme["cost_ring"], (80, 92, 104), 0.6)
    pygame.draw.circle(surface, type_theme["cost_fill"], center, radius)
    pygame.draw.circle(surface, ring_color, center, radius, ring_width)


def _draw_primary_effect_block(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    fonts: dict[str, Any],
    type_theme: dict[str, Any],
) -> None:
    primary_rect = layout["primary_effect"]
    description_rect = layout["description_box"]
    primary_line = primary_effect_text(card)
    if not primary_line:
        return

    secondary_lines = secondary_effect_lines(card)
    display_lines = _merge_rule_lines(primary_line, secondary_lines, fonts["primary_support"], primary_rect.width - 12)
    main_line = display_lines[0]
    main_font = fonts["primary_support"]
    draw_wrapped_text(
        surface,
        main_line,
        (primary_rect.x + 8, primary_rect.y + 8),
        main_font,
        color=type_theme["primary_value"],
        width=primary_rect.width - 16,
    )
    if len(display_lines) > 1:
        _draw_description_lines(
            surface,
            description_rect,
            display_lines[1:2],
            fonts["description"],
            type_theme["text"],
            max_lines=1,
        )


def _draw_description_lines(
    surface: Any,
    rect: Any,
    lines: list[str],
    font: Any,
    color: tuple[int, int, int],
    *,
    max_lines: int = 3,
) -> None:
    wrapped = _wrap_lines(lines, font, rect.width - 16, max_lines=max_lines)
    y = rect.y + 8
    line_step = max(font.get_linesize(), int(font.get_linesize() * CARD_TYPOGRAPHY["description_line_height"]))
    for line in wrapped:
        draw_wrapped_text(surface, line, (rect.x + 8, y), font, color=color, width=rect.width - 16)
        y += line_step


def _draw_compact_rules(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    fonts: dict[str, Any],
    type_theme: dict[str, Any],
) -> None:
    summary_rect = layout["description_box"]
    summary_text = compact_card_summary(card)
    if not summary_text:
        return
    draw_wrapped_text(
        surface,
        summary_text,
        (summary_rect.x + 8, summary_rect.y + 8),
        fonts["description"],
        color=type_theme["text"],
        width=summary_rect.width - 16,
    )


def _draw_title_motif(surface: Any, rect: Any, card_theme: dict[str, Any]) -> None:
    motif_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    motif_kind = card_theme["type_theme"]["title_motif"]
    if motif_kind == "slashes":
        for index in range(3):
            start_x = int(rect.width * (0.18 + (index * 0.18)))
            pygame.draw.line(
                motif_surface,
                (255, 236, 220, 52),
                (start_x, rect.height - 4),
                (start_x + max(12, rect.width // 8), 4),
                2,
            )
    elif motif_kind == "circuit":
        mid_y = rect.height // 2
        pygame.draw.line(motif_surface, (220, 248, 255, 40), (10, mid_y), (rect.width - 10, mid_y), 1)
        for node_x in (rect.width // 4, rect.width // 2, (rect.width * 3) // 4):
            pygame.draw.line(motif_surface, (220, 248, 255, 46), (node_x, 6), (node_x, rect.height - 6), 1)
            pygame.draw.circle(motif_surface, (220, 248, 255, 62), (node_x, mid_y), 2)
    elif motif_kind == "sigil":
        pygame.draw.circle(motif_surface, (255, 234, 204, 34), (rect.width - 18, rect.height // 2), max(6, rect.height // 4), 1)
        pygame.draw.line(motif_surface, (255, 234, 204, 42), (rect.width - 26, rect.height // 2), (rect.width - 10, rect.height // 2), 1)
    else:
        for offset in range(8, rect.width - 8, max(10, rect.width // 5)):
            pygame.draw.line(motif_surface, (240, 246, 255, 22), (offset, 6), (offset, rect.height - 6), 1)

    masked = _mask_surface_to_shape(motif_surface, card_theme, "title_shape")
    surface.blit(masked, rect.topleft)


def _draw_art_style_overlay(surface: Any, rect: Any, card_theme: dict[str, Any], card: dict[str, Any]) -> None:
    art_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    art_palette = card_theme["art_palette"]
    type_theme = card_theme["type_theme"]
    art_style = card_theme["art_style"]

    if art_style == "circuit_burst":
        for index in range(4):
            start_x = 10 + (index * max(10, rect.width // 6))
            pygame.draw.line(
                art_surface,
                (*art_palette["art_grid"][:3], min(art_palette["art_grid"][3] + 18, 120)),
                (start_x, rect.height - 10),
                (start_x + max(14, rect.width // 8), 10 + (index * 6)),
                2,
            )
    elif art_style == "signal_mesh":
        for index in range(5):
            offset_y = 10 + (index * max(8, rect.height // 7))
            pygame.draw.line(
                art_surface,
                art_palette["art_grid"],
                (8, offset_y),
                (rect.width - 8, offset_y + (4 if index % 2 == 0 else -4)),
                1,
            )
    elif art_style == "patch_grid":
        cell = max(12, min(rect.width, rect.height) // 4)
        for cell_x in range(0, rect.width, cell):
            for cell_y in range(0, rect.height, cell):
                alpha = 38 if (cell_x + cell_y) // cell % 2 == 0 else 20
                pygame.draw.rect(
                    art_surface,
                    (255, 255, 255, alpha),
                    pygame.Rect(cell_x + 2, cell_y + 2, max(4, cell - 4), max(4, cell - 4)),
                    border_radius=4,
                )

    if type_theme["art_motif"] == "slashes":
        for offset in (0.18, 0.42, 0.66):
            start_x = int(rect.width * offset)
            pygame.draw.line(
                art_surface,
                (*type_theme["accent_soft"], 70),
                (start_x, rect.height - 8),
                (min(rect.width - 6, start_x + max(12, rect.width // 7)), 6),
                2,
            )
    else:
        base_y = int(rect.height * 0.28)
        pygame.draw.line(art_surface, (*type_theme["accent_soft"], 56), (12, base_y), (rect.width - 12, base_y), 1)
        pygame.draw.line(art_surface, (*type_theme["accent_soft"], 56), (rect.width // 2, 12), (rect.width // 2, rect.height - 12), 1)
        for node in ((rect.width // 3, base_y), (rect.width // 2, rect.height // 2), ((rect.width * 2) // 3, rect.height - base_y)):
            pygame.draw.circle(art_surface, (*type_theme["accent_soft"], 72), node, 2)

    pygame.draw.circle(
        art_surface,
        (*art_palette["art_highlight"], 112),
        (int(rect.width * 0.76), int(rect.height * 0.22)),
        max(12, rect.height // 5),
    )
    masked = _mask_surface_to_shape(art_surface, card_theme, "art_shape")
    surface.blit(masked, rect.topleft)


def _draw_type_pip(surface: Any, rect: Any, card_theme: dict[str, Any], interaction: dict[str, bool]) -> None:
    type_theme = card_theme["type_theme"]
    pip_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    color = type_theme["accent_soft"] if not interaction["disabled"] else _blend_color(type_theme["accent_soft"], (120, 128, 140), 0.55)
    pip = type_theme["title_pip"]

    if pip == "attack":
        pygame.draw.line(pip_surface, color, (4, rect.height - 6), (rect.width - 6, 6), 2)
        pygame.draw.line(pip_surface, color, (6, rect.height - 6), (rect.width - 8, 8), 1)
        pygame.draw.line(pip_surface, color, (rect.width // 2 - 3, rect.height - 8), (rect.width // 2 + 3, rect.height - 2), 2)
    elif pip == "skill":
        pygame.draw.polygon(
            pip_surface,
            color,
            [
                (rect.width // 2, 4),
                (rect.width - 5, 8),
                (rect.width - 7, rect.height - 6),
                (rect.width // 2, rect.height - 2),
                (5, rect.height - 6),
                (3, 8),
            ],
            2,
        )
    elif pip == "power":
        pygame.draw.circle(pip_surface, color, (rect.width // 2, rect.height // 2), max(4, rect.height // 3), 2)
    elif pip == "curse":
        pygame.draw.line(pip_surface, color, (4, 4), (rect.width - 4, rect.height - 4), 2)
        pygame.draw.line(pip_surface, color, (rect.width - 4, 4), (4, rect.height - 4), 2)
    else:
        for x_pos in (4, rect.width // 2, rect.width - 4):
            pygame.draw.line(pip_surface, color, (x_pos, 5), (x_pos, rect.height - 5), 1)
        for y_pos in (5, rect.height // 2, rect.height - 5):
            pygame.draw.line(pip_surface, color, (4, y_pos), (rect.width - 4, y_pos), 1)

    surface.blit(pip_surface, rect.topleft)


def _mask_surface_to_shape(layer: Any, card_theme: dict[str, Any], shape_key: str) -> Any:
    mask = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
    _draw_theme_shape(mask, mask.get_rect(), card_theme["type_theme"], (255, 255, 255, 255), shape_key=shape_key)
    masked = layer.copy()
    masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return masked


def _blit_gradient_shape(
    surface: Any,
    rect: Any,
    card_theme: dict[str, Any],
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
    *,
    shape_key: str,
) -> None:
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    _fill_vertical_gradient(layer, layer.get_rect(), top_color, bottom_color)
    masked = _mask_surface_to_shape(layer, card_theme, shape_key)
    surface.blit(masked, rect.topleft)


def _fill_vertical_gradient(surface: Any, rect: Any, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> None:
    height = max(1, rect.height)
    for index in range(height):
        blend = index / max(1, height - 1)
        color = _blend_color(top_color, bottom_color, blend)
        pygame.draw.line(surface, color, (rect.x, rect.y + index), (rect.right - 1, rect.y + index))


def _draw_theme_shape(
    surface: Any,
    rect: Any,
    type_theme: dict[str, Any],
    fill: tuple[int, ...],
    *,
    width: int = 0,
    shape_key: str = "shape",
) -> None:
    shape = type_theme.get(shape_key, type_theme.get("shape", "skill"))
    if shape == "attack":
        pygame.draw.polygon(surface, fill, _attack_shape_points(rect, type_theme, shape_key), width)
        return
    if shape == "power":
        pygame.draw.ellipse(surface, fill, rect, width)
        return
    pygame.draw.rect(surface, fill, rect, width, border_radius=_shape_radius(rect, type_theme, shape_key))


def _draw_theme_outline(
    surface: Any,
    rect: Any,
    card_theme: dict[str, Any],
    color: tuple[int, ...],
    width: int,
    *,
    shape_key: str = "shape",
) -> None:
    _draw_theme_shape(surface, rect, card_theme["type_theme"], color, width=width, shape_key=shape_key)


def _attack_shape_points(rect: Any, type_theme: dict[str, Any], shape_key: str) -> list[tuple[int, int]]:
    multiplier = 1.0
    if shape_key == "title_shape":
        multiplier = 0.72
    elif shape_key == "art_shape":
        multiplier = 0.62

    cut = max(6, int(rect.width * type_theme["top_cut_ratio"] * multiplier))
    shoulder = max(6, int(rect.height * max(0.06, type_theme["shoulder_depth_ratio"] * multiplier)))
    lower = max(4, int(rect.width * 0.025))
    return [
        (rect.x + cut, rect.y),
        (rect.right - cut, rect.y),
        (rect.right, rect.y + shoulder),
        (rect.right, rect.bottom - lower),
        (rect.right - lower, rect.bottom),
        (rect.x + lower, rect.bottom),
        (rect.x, rect.bottom - lower),
        (rect.x, rect.y + shoulder),
    ]


def _shape_radius(rect: Any, type_theme: dict[str, Any], shape_key: str) -> int:
    if shape_key == "art_shape":
        ratio = type_theme.get("art_radius_ratio", type_theme["outer_radius_ratio"])
    else:
        ratio = type_theme.get("outer_radius_ratio", 0.05)
    return max(6, int(rect.width * ratio))


def _frame_border_color(type_theme: dict[str, Any], interaction: dict[str, bool]) -> tuple[int, int, int]:
    if interaction["disabled"]:
        return _blend_color(type_theme["description_border"], (110, 120, 134), 0.45)
    if interaction["pressed"]:
        return (255, 232, 176)
    if interaction["selected"]:
        return type_theme["accent_soft"]
    if interaction["hovered"]:
        return type_theme["accent"]
    if interaction["high_contrast"]:
        return (236, 242, 255)
    return _blend_color(type_theme["description_border"], type_theme["accent"], 0.35)


def _interaction_title_colors(type_theme: dict[str, Any], interaction: dict[str, bool]) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    brighten = 0.0
    if interaction["hovered"]:
        brighten = 0.16
    if interaction["selected"]:
        brighten = 0.24
    if interaction["disabled"]:
        brighten = -0.18
    return _shift_brightness(type_theme["title_top"], brighten), _shift_brightness(type_theme["title_bottom"], brighten)


def _merge_rule_lines(primary_line: str, extra_lines: list[str], font: Any, width: int) -> list[str]:
    if not primary_line:
        return []
    merged = [primary_line]
    if extra_lines:
        combined = f"{primary_line} {extra_lines[0]}"
        if font.size(combined)[0] <= width:
            return [combined]
        merged.extend(extra_lines[:1])
    return merged


def _wrap_lines(lines: list[str], font: Any, width: int, max_lines: int) -> list[str]:
    wrapped: list[str] = []
    for raw_line in lines:
        if not raw_line:
            continue
        words = raw_line.split()
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= width:
                current = candidate
                continue
            if current:
                wrapped.append(current)
                if len(wrapped) >= max_lines:
                    return wrapped[:max_lines]
            current = word
        if current:
            wrapped.append(current)
            if len(wrapped) >= max_lines:
                return wrapped[:max_lines]
    return wrapped[:max_lines]


def _fit_text_ellipsis(text: str, font: Any, width: int) -> str:
    if font.size(text)[0] <= width:
        return text
    if width <= font.size("...")[0]:
        return "..."
    trimmed = text
    while trimmed:
        trimmed = trimmed[:-1]
        candidate = f"{trimmed.rstrip()}..."
        if font.size(candidate)[0] <= width:
            return candidate
    return "..."


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


def _blend_color(color_a: tuple[int, ...], color_b: tuple[int, ...], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(int(color_a[index] + ((color_b[index] - color_a[index]) * amount)) for index in range(3))


def _shift_brightness(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    if amount >= 0:
        return _blend_color(color, (255, 255, 255), amount)
    return _blend_color(color, (10, 12, 18), abs(amount))


def _effect_line(effect: dict[str, Any]) -> str:
    effect_type = effect.get("type")
    if not isinstance(effect_type, str):
        return ""
    value = effect.get("value")
    if effect_type == "damage" and isinstance(value, int):
        return f"Deal {value} damage."
    if effect_type == "multi_damage" and isinstance(value, int) and isinstance(effect.get("count"), int):
        return f"Deal {value} damage {effect['count']} times."
    if effect_type == "lifesteal_damage" and isinstance(value, int):
        return f"Deal {value} damage. Heal for damage dealt."
    if effect_type == "block" and isinstance(value, int):
        return f"Gain {value} Block."
    if effect_type == "heal" and isinstance(value, int):
        return f"Heal {value}."
    if effect_type == "draw" and isinstance(value, int):
        return f"Draw {value}."
    if effect_type == "energy" and isinstance(value, int):
        if value >= 0:
            return f"Gain {value} Energy."
        return f"Lose {abs(value)} Energy."
    if effect_type == "self_damage" and isinstance(value, int):
        return f"Lose {value} HP."
    if effect_type == "gain_strength" and isinstance(value, int):
        return f"Gain {value} Strength."
    if effect_type == "apply_weak" and isinstance(value, int):
        return f"Apply {value} Weak."
    if effect_type == "apply_vulnerable" and isinstance(value, int):
        return f"Apply {value} Vulnerable."
    if effect_type == "modify_next_card_cost" and isinstance(value, int):
        if value < 0:
            return f"Next card costs {abs(value)} less."
        if value > 0:
            return f"Next card costs {value} more."
        return "Next card cost unchanged."
    if effect_type == "modify_next_attack_damage" and isinstance(value, int):
        if value >= 0:
            return f"Next Attack deals {value} more damage."
        return f"Next Attack deals {abs(value)} less damage."
    if effect_type == "add_status_card":
        card_name = _status_name_from_card_id(effect.get("card_id"))
        count = effect.get("count", 1)
        if isinstance(count, int) and count > 1:
            return f"Add {count} {card_name}."
        return f"Add {card_name}."
    if effect_type == "random_one_of":
        return "Random effect."
    if effect_type == "exhaust_drawn_card":
        return "Exhaust it."
    if effect_type == "noop":
        return "No effect."
    return ""


def _trigger_line(trigger: dict[str, Any]) -> str:
    if not isinstance(trigger, dict):
        return ""
    hook = trigger.get("hook")
    if not isinstance(hook, str):
        return ""
    effect_lines = [
        line
        for line in (_effect_line(effect) for effect in trigger.get("effects", []))
        if line
    ]
    if not effect_lines:
        return ""
    prefix = _trigger_prefix(hook, trigger.get("conditions", {}))
    return f"{prefix} {' '.join(effect_lines)}".strip()


def _trigger_prefix(hook: str, conditions: dict[str, Any]) -> str:
    if not isinstance(conditions, dict):
        conditions = {}
    if hook == "turn_start":
        if "below_hp_ratio" in conditions:
            return "Turn start: If below half HP,"
        return "Turn start:"
    if hook == "turn_end":
        return "Turn end:"
    if hook == "on_draw":
        return "On draw:"
    if hook == "on_self_damage":
        return "On self-damage:"
    if hook == "on_status_drawn":
        return "Status draw:"
    if hook == "after_attack_played":
        return "After Attack:"
    if hook == "after_card_played":
        played_type = conditions.get("played_card_type")
        if conditions.get("first_card_this_turn"):
            return "First card:"
        if isinstance(played_type, str):
            return f"After {played_type.title()}:"
        return "After play:"
    return f"{hook.replace('_', ' ').title()}:"


def _keyword_face_lines(card: dict[str, Any]) -> list[str]:
    keywords = card.get("keywords", [])
    if not isinstance(keywords, list):
        return []
    lines: list[str] = []
    if "retain" in keywords:
        lines.append("Retain.")
    if "exhaust" in keywords:
        lines.append("Exhaust.")
    return lines


def _status_name_from_card_id(card_id: Any) -> str:
    if not isinstance(card_id, str) or not card_id:
        return "Status"
    raw_name = card_id
    if raw_name.startswith("status_"):
        raw_name = raw_name.removeprefix("status_")
    raw_name = raw_name.rsplit("_", 1)[0]
    return raw_name.replace("_", " ").title()


def _resource_effect_line(effect: Any) -> str:
    if not isinstance(effect, dict):
        return ""
    resource = effect.get("resource")
    delta = effect.get("delta")
    if not isinstance(resource, str) or not isinstance(delta, int):
        return ""
    if delta >= 0:
        return f"Gain {delta} {resource.title()}."
    return f"Lose {abs(delta)} {resource.title()}."


def _resource_cost_line(cost: Any) -> str:
    if not isinstance(cost, dict):
        return ""
    resource = cost.get("resource")
    amount = cost.get("amount")
    if not isinstance(resource, str) or not isinstance(amount, int):
        return ""
    return f"Spend {amount} {resource.title()}."
