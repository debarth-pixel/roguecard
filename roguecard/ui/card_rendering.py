from __future__ import annotations

import math
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from ui.card_style import (
    CARD_COMPACT_LAYOUT_SPEC,
    CARD_PRIMARY_EFFECT_CUES,
    CARD_MINI_LAYOUT_SPEC,
    CARD_PORTRAIT_LAYOUT_SPEC,
    CARD_TYPE_BADGES,
    CARD_TYPOGRAPHY,
    resolve_card_theme,
)
from ui.sprite_sheet_assets import sprite_sheet_assets

_CARD_FONT_CACHE: dict[tuple[int, bool], Any] = {}

_PRIMARY_EFFECT_TYPES = {
    "DMG": {"damage", "multi_damage", "lifesteal_damage", "modify_next_attack_damage"},
    "BLK": {"block"},
    "HEAL": {"heal", "cleanse_status", "remove_nullified"},
    "FLOW": {"draw", "energy", "modify_next_card_cost"},
    "BUFF": {"gain_strength"},
    "DEBUFF": {"apply_bleed", "apply_infect", "apply_vulnerable", "apply_weak", "add_status_card"},
    "RISK": {"self_damage"},
}


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


def renderable_card_rule_entries(card: dict[str, Any]) -> list[dict[str, str]]:
    entries = [{"text": line, "tone": "base"} for line in inspect_card_rules(card)]
    corruption_display = card.get("corruption_display", [])
    if isinstance(corruption_display, list):
        for rider in corruption_display:
            text = str(rider.get("text", "")).strip()
            if not text:
                continue
            entries.append(
                {
                    "text": text,
                    "tone": "corruption_active" if rider.get("active") else "corruption_inactive",
                }
            )
    return entries


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


def _type_badge(card_theme: dict[str, Any]) -> dict[str, Any]:
    type_key = str(card_theme.get("type_key", "status")).strip().lower() or "status"
    return CARD_TYPE_BADGES.get(type_key, CARD_TYPE_BADGES["status"])


def _primary_effect_cue(card: dict[str, Any]) -> dict[str, Any]:
    cue_key = _first_primary_effect_key(card)
    cue = CARD_PRIMARY_EFFECT_CUES.get(cue_key, CARD_PRIMARY_EFFECT_CUES["UTIL"])
    return {**cue, "label": cue_key}


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
    if rect.width <= 0 or rect.height <= 0:
        return

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
    if variant == "mini":
        return _resolve_mini_layout(rect)
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
    if layout.get("show_art", False):
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
    body_rect = layout["body_rect"]
    type_theme = card_theme["type_theme"]
    outline = _frame_border_color(type_theme, interaction)

    shadow_pad = max(10, int(card_rect.width * 0.06))
    shadow_surface = pygame.Surface((card_rect.width + (shadow_pad * 2), card_rect.height + (shadow_pad * 2)), pygame.SRCALPHA)
    shadow_rect = shadow_surface.get_rect()
    _draw_beveled_panel(
        shadow_surface,
        shadow_rect.inflate(-shadow_pad, -shadow_pad).move(0, max(4, shadow_pad // 3)),
        (*type_theme["outer_shadow"], 152),
        kind="card",
    )
    surface.blit(shadow_surface, (card_rect.x - shadow_pad, card_rect.y - shadow_pad))

    _draw_glow(surface, card_rect, type_theme, interaction)
    _draw_beveled_panel(surface, card_rect.inflate(-1, -1), type_theme["outer_fill"], kind="card")
    _draw_beveled_panel(surface, card_rect.inflate(-4, -4), type_theme["outer_shadow"], kind="card")
    _draw_beveled_panel(surface, body_rect, type_theme["body_fill"], kind="card")
    _draw_beveled_outline(surface, body_rect, type_theme["keyline"], 1, kind="card")
    _draw_accent_rails(surface, body_rect, type_theme, layout["variant"])

    title_top, title_bottom = _interaction_title_colors(type_theme, interaction)
    _blit_gradient_panel(surface, layout["header"], title_top, title_bottom, kind="header")
    _draw_beveled_outline(surface, layout["header"], outline, 1, kind="header")
    _draw_header_motif(surface, layout["header"], card_theme)

    _blit_gradient_panel(
        surface,
        layout["rules_panel"],
        _blend_color(type_theme["description_fill"], type_theme["title_top"], 0.18),
        type_theme["description_fill"],
        kind="rules",
    )
    _draw_beveled_outline(surface, layout["rules_panel"], type_theme["description_border"], 1, kind="rules")
    _draw_rules_shell_details(surface, layout, type_theme)

    _draw_cost_badge_shell(surface, layout["cost_badge"], type_theme, interaction)

    if layout.get("show_art", False):
        _draw_beveled_panel(
            surface,
            layout["art_panel"],
            _blend_color(type_theme["body_fill"], (8, 12, 20), 0.35),
            kind="art",
        )


def render_card_art_panel(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
) -> None:
    if pygame is None or not layout.get("show_art", False):
        return

    art_rect = layout["art_panel"]
    art_surface = _build_atlas_art_surface(art_rect, card_theme, card, variant=layout["variant"])
    if art_surface is None:
        return

    masked = _mask_surface_to_panel(art_surface, "art")
    surface.blit(masked, art_rect.topleft)
    _draw_beveled_outline(surface, art_rect, card_theme["type_theme"]["art_border"], 1, kind="art")
    _draw_art_frame_accents(surface, art_rect, card_theme["type_theme"], layout["variant"])


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
    if pygame is None:
        return

    type_theme = card_theme["type_theme"]
    variant = layout["variant"]

    _draw_cost_text(surface, layout["cost_badge"], str(card.get("cost", 0)), fonts["cost"], type_theme, interaction)

    title_font = fonts["title"] if variant == "full" else fonts["compact_title"]
    title_fallback = fonts["title_small"] if variant == "full" else fonts["compact_title_small"]
    if variant == "mini":
        title_font = fonts["mini_title"]
        title_fallback = fonts["mini_title"]
    _draw_title_text(surface, layout["title"], str(card.get("name", "Card")), title_font, title_fallback, type_theme)

    if variant in {"full", "compact"} and layout.get("faction_chip") is not None:
        _draw_type_chip(surface, layout["faction_chip"], card_theme, fonts["meta"])

    if variant == "full":
        _draw_full_rules(
            surface,
            layout,
            card,
            card_theme,
            fonts,
            shortcut_label=shortcut_label,
            footer_label=footer_label,
            note_label=note_label,
        )
    elif variant == "compact":
        _draw_compact_rules(
            surface,
            layout,
            card,
            card_theme,
            fonts,
            shortcut_label=shortcut_label,
            footer_label=footer_label,
            note_label=note_label,
        )
    else:
        _draw_mini_face(
            surface,
            layout,
            card,
            card_theme,
            fonts,
            shortcut_label=shortcut_label,
            footer_label=footer_label,
            note_label=note_label,
        )

    _draw_serial_lane(surface, layout["serial_lane"], card, card_theme, fonts, variant)


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
    ring_width = max(1, int(card_rect.width * 0.012))

    _draw_beveled_outline(surface, card_rect.inflate(-1, -1), ring_color, ring_width, kind="card")

    if interaction["selected"]:
        ring_rect = card_rect.inflate(max(8, int(card_rect.width * 0.04)), max(10, int(card_rect.width * 0.05)))
        ring_surface = pygame.Surface(ring_rect.size, pygame.SRCALPHA)
        _draw_beveled_outline(
            ring_surface,
            ring_surface.get_rect(),
            (*type_theme["accent_soft"], 176),
            max(1, ring_width),
            kind="card",
        )
        surface.blit(ring_surface, ring_rect.topleft)

    if interaction["pressed"]:
        press_surface = pygame.Surface(card_rect.size, pygame.SRCALPHA)
        _draw_beveled_panel(press_surface, press_surface.get_rect(), (255, 245, 220, 20), kind="card")
        surface.blit(press_surface, card_rect.topleft)

    if interaction["disabled"]:
        dimmer = pygame.Surface(card_rect.size, pygame.SRCALPHA)
        _draw_beveled_panel(dimmer, dimmer.get_rect(), (6, 10, 18, 128), kind="card")
        surface.blit(dimmer, card_rect.topleft)


def _resolve_full_layout(rect: Any) -> dict[str, Any]:
    safe_rect = _inset_rect(
        rect,
        max(6, int(rect.width * CARD_PORTRAIT_LAYOUT_SPEC["safe_margin_x"])),
        max(6, int(rect.height * CARD_PORTRAIT_LAYOUT_SPEC["safe_margin_y"])),
    )
    header_rect = _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["header"])
    cost_badge = _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["cost_badge"])
    title_rect = _title_safe_rect(
        header_rect.inflate(-max(8, rect.width // 22), -max(4, rect.height // 120)),
        cost_badge,
        gap=max(6, rect.width // 40),
    )
    rules_panel = _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["rules_panel"])
    label_height = max(12, int(rect.height * CARD_PORTRAIT_LAYOUT_SPEC["rules_label_height"]))
    footer_height = max(16, int(rect.height * CARD_PORTRAIT_LAYOUT_SPEC["rules_footer_height"]))
    effect_label, rules_text, rules_footer = _resolve_rules_regions(rules_panel, label_height, footer_height)
    return {
        "variant": "full",
        "card_rect": rect,
        "safe_rect": safe_rect,
        "body_rect": safe_rect.inflate(-2, -2),
        "header": header_rect,
        "title": title_rect,
        "cost_badge": cost_badge,
        "art_panel": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["art_panel"]),
        "faction_chip": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["faction_chip"]),
        "rules_panel": rules_panel,
        "effect_label": effect_label,
        "rules_text": rules_text,
        "rules_footer": rules_footer,
        "serial_lane": _scale_region(rect, CARD_PORTRAIT_LAYOUT_SPEC["serial_lane"]),
        "show_art": True,
    }


def _resolve_compact_layout(rect: Any) -> dict[str, Any]:
    safe_rect = _inset_rect(
        rect,
        max(4, int(rect.width * CARD_COMPACT_LAYOUT_SPEC["safe_margin_x"])),
        max(4, int(rect.height * CARD_COMPACT_LAYOUT_SPEC["safe_margin_y"])),
    )
    header_rect = _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["header"])
    cost_badge = _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["cost_badge"])
    title_rect = _title_safe_rect(
        header_rect.inflate(-max(4, rect.width // 24), -max(2, rect.height // 28)),
        cost_badge,
        gap=max(4, rect.width // 36),
    )
    rules_panel = _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["rules_panel"])
    label_height = max(10, int(rect.height * CARD_COMPACT_LAYOUT_SPEC["rules_label_height"]))
    footer_height = max(10, int(rect.height * CARD_COMPACT_LAYOUT_SPEC["rules_footer_height"]))
    effect_label, rules_text, rules_footer = _resolve_rules_regions(rules_panel, label_height, footer_height)
    return {
        "variant": "compact",
        "card_rect": rect,
        "safe_rect": safe_rect,
        "body_rect": safe_rect.inflate(-2, -2),
        "header": header_rect,
        "title": title_rect,
        "cost_badge": cost_badge,
        "art_panel": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["art_panel"]),
        "faction_chip": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["faction_chip"]),
        "rules_panel": rules_panel,
        "effect_label": effect_label,
        "rules_text": rules_text,
        "rules_footer": rules_footer,
        "serial_lane": _scale_region(rect, CARD_COMPACT_LAYOUT_SPEC["serial_lane"]),
        "show_art": True,
    }


def _resolve_mini_layout(rect: Any) -> dict[str, Any]:
    safe_rect = _inset_rect(
        rect,
        max(4, int(rect.width * CARD_MINI_LAYOUT_SPEC["safe_margin_x"])),
        max(4, int(rect.height * CARD_MINI_LAYOUT_SPEC["safe_margin_y"])),
    )
    header_rect = _scale_region(rect, CARD_MINI_LAYOUT_SPEC["header"])
    cost_badge = _scale_region(rect, CARD_MINI_LAYOUT_SPEC["cost_badge"])
    title_rect = _title_safe_rect(
        header_rect.inflate(-max(4, rect.width // 18), -max(1, rect.height // 30)),
        cost_badge,
        gap=max(4, rect.width // 34),
    )
    rules_panel = _scale_region(rect, CARD_MINI_LAYOUT_SPEC["rules_panel"])
    label_height = max(8, int(rect.height * CARD_MINI_LAYOUT_SPEC["rules_label_height"]))
    effect_label, rules_text, _ = _resolve_rules_regions(rules_panel, label_height, 0)
    return {
        "variant": "mini",
        "card_rect": rect,
        "safe_rect": safe_rect,
        "body_rect": safe_rect.inflate(-1, -1),
        "header": header_rect,
        "title": title_rect,
        "cost_badge": cost_badge,
        "art_panel": _scale_region(rect, CARD_MINI_LAYOUT_SPEC["art_panel"]),
        "faction_chip": None,
        "rules_panel": rules_panel,
        "effect_label": effect_label,
        "rules_text": rules_text,
        "rules_footer": None,
        "serial_lane": _scale_region(rect, CARD_MINI_LAYOUT_SPEC["serial_lane"]),
        "show_art": True,
    }


def _resolve_rules_regions(rules_panel: Any, label_height: int, footer_height: int) -> tuple[Any, Any, Any | None]:
    padding_x = max(8, int(rules_panel.width * 0.05))
    top_padding = max(6, int(rules_panel.height * 0.08))
    bottom_padding = max(6, int(rules_panel.height * 0.08))
    effect_label = pygame.Rect(
        rules_panel.x + padding_x,
        rules_panel.y + top_padding,
        max(16, rules_panel.width - (padding_x * 2)),
        label_height,
    )
    if footer_height > 0:
        rules_footer = pygame.Rect(
            rules_panel.x + padding_x,
            rules_panel.bottom - footer_height - bottom_padding,
            max(16, rules_panel.width - (padding_x * 2)),
            footer_height,
        )
        rules_text = pygame.Rect(
            rules_panel.x + padding_x,
            effect_label.bottom + 6,
            max(20, rules_panel.width - (padding_x * 2)),
            max(18, rules_footer.y - effect_label.bottom - 12),
        )
        return effect_label, rules_text, rules_footer

    rules_text = pygame.Rect(
        rules_panel.x + padding_x,
        effect_label.bottom + 4,
        max(20, rules_panel.width - (padding_x * 2)),
        max(16, rules_panel.bottom - effect_label.bottom - bottom_padding),
    )
    return effect_label, rules_text, None


def _card_fonts(card_height: int, fallback_fonts: dict[str, Any]) -> dict[str, Any]:
    if pygame is None:
        return fallback_fonts
    return {
        "cost": _cached_font(int(card_height * CARD_TYPOGRAPHY["cost"]), bold=True),
        "header": _cached_font(int(card_height * CARD_TYPOGRAPHY["header"]), bold=False),
        "title": _cached_font(int(card_height * CARD_TYPOGRAPHY["title"]), bold=True),
        "title_small": _cached_font(int(card_height * CARD_TYPOGRAPHY["title"] * 0.74), bold=True),
        "effect_label": _cached_font(int(card_height * CARD_TYPOGRAPHY["effect_label"]), bold=True),
        "rules": _cached_font(int(card_height * CARD_TYPOGRAPHY["description"]), bold=False),
        "meta": _cached_font(int(card_height * CARD_TYPOGRAPHY["metadata"]), bold=True),
        "serial": _cached_font(int(card_height * CARD_TYPOGRAPHY["serial"]), bold=False),
        "compact_title": _cached_font(int(card_height * CARD_TYPOGRAPHY["compact_title"]), bold=True),
        "compact_title_small": _cached_font(int(card_height * CARD_TYPOGRAPHY["compact_title"] * 0.80), bold=True),
        "compact_rules": _cached_font(int(card_height * CARD_TYPOGRAPHY["compact_description"]), bold=False),
        "compact_meta": _cached_font(int(card_height * CARD_TYPOGRAPHY["compact_metadata"]), bold=True),
        "mini_title": _cached_font(int(card_height * CARD_TYPOGRAPHY["mini_title"]), bold=True),
        "mini_rules": _cached_font(int(card_height * CARD_TYPOGRAPHY["mini_description"]), bold=False),
        "mini_meta": _cached_font(int(card_height * CARD_TYPOGRAPHY["mini_metadata"]), bold=True),
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


def _inset_rect(rect: Any, inset_x: int, inset_y: int) -> Any:
    return pygame.Rect(
        rect.x + inset_x,
        rect.y + inset_y,
        max(1, rect.width - (inset_x * 2)),
        max(1, rect.height - (inset_y * 2)),
    )


def _title_safe_rect(title_rect: Any, cost_badge: Any, *, gap: int) -> Any:
    if title_rect.right <= cost_badge.x - gap:
        return title_rect
    safe_width = max(18, cost_badge.x - gap - title_rect.x)
    return pygame.Rect(title_rect.x, title_rect.y, safe_width, title_rect.height)


def _draw_glow(surface: Any, rect: Any, type_theme: dict[str, Any], interaction: dict[str, bool]) -> None:
    if pygame is None:
        return
    glow_pad = max(12, int(rect.width * 0.08))
    glow_alpha = type_theme["accent_glow"][3]
    if interaction["hovered"]:
        glow_alpha = min(164, glow_alpha + 32)
    if interaction["selected"]:
        glow_alpha = min(210, glow_alpha + 56)
    if interaction["disabled"]:
        glow_alpha = max(18, glow_alpha // 3)

    glow_surface = pygame.Surface((rect.width + (glow_pad * 2), rect.height + (glow_pad * 2)), pygame.SRCALPHA)
    glow_rect = glow_surface.get_rect().inflate(-glow_pad, -glow_pad)
    _draw_beveled_panel(glow_surface, glow_rect, (*type_theme["accent"], glow_alpha), kind="card")
    surface.blit(glow_surface, (rect.x - glow_pad, rect.y - glow_pad))


def _draw_beveled_panel(surface: Any, rect: Any, fill: tuple[int, ...], *, kind: str) -> None:
    if rect.width <= 0 or rect.height <= 0:
        return
    pygame.draw.polygon(surface, fill, _panel_points(rect, kind))


def _draw_beveled_outline(surface: Any, rect: Any, color: tuple[int, ...], width: int, *, kind: str) -> None:
    if rect.width <= 0 or rect.height <= 0:
        return
    pygame.draw.polygon(surface, color, _panel_points(rect, kind), width)


def _blit_gradient_panel(
    surface: Any,
    rect: Any,
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
    *,
    kind: str,
) -> None:
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    _fill_vertical_gradient(layer, layer.get_rect(), top_color, bottom_color)
    masked = _mask_surface_to_panel(layer, kind)
    surface.blit(masked, rect.topleft)


def _fill_vertical_gradient(surface: Any, rect: Any, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> None:
    height = max(1, rect.height)
    for index in range(height):
        blend = index / max(1, height - 1)
        color = _blend_color(top_color, bottom_color, blend)
        pygame.draw.line(surface, color, (rect.x, rect.y + index), (rect.right - 1, rect.y + index))


def _draw_accent_rails(surface: Any, body_rect: Any, type_theme: dict[str, Any], variant: str) -> None:
    rail_width = max(2, int(body_rect.width * 0.018))
    inset = max(4, int(body_rect.width * 0.018))
    left_rail = pygame.Rect(body_rect.x + inset, body_rect.y + inset, rail_width, body_rect.height - (inset * 2))
    right_rail = pygame.Rect(body_rect.right - inset - rail_width, body_rect.y + inset + max(4, body_rect.height // 16), rail_width, body_rect.height - (inset * 2) - max(8, body_rect.height // 10))
    top_rail = pygame.Rect(body_rect.x + max(16, body_rect.width // 10), body_rect.y + inset, max(32, body_rect.width - max(28, body_rect.width // 5)), rail_width)
    rail_color = (*type_theme["shell_rail"], 112)
    edge_color = (*type_theme["accent"], 84)
    pygame.draw.rect(surface, rail_color, left_rail)
    if variant != "mini":
        pygame.draw.rect(surface, edge_color, right_rail)
    pygame.draw.rect(surface, (*type_theme["accent_soft"], 46), top_rail)


def _draw_rules_shell_details(surface: Any, layout: dict[str, Any], type_theme: dict[str, Any]) -> None:
    panel = layout["rules_panel"]
    effect_label = layout["effect_label"]
    footer = layout.get("rules_footer")

    header_plate = pygame.Rect(effect_label.x, effect_label.y - 3, max(16, int(panel.width * 0.72)), max(8, effect_label.height))
    _draw_beveled_panel(surface, header_plate, (*type_theme["accent_soft"], 26), kind="header_tab")

    if footer is not None:
        footer_plate = footer.inflate(0, 4)
        _draw_beveled_panel(surface, footer_plate, type_theme["metadata_fill"], kind="footer")
        pygame.draw.line(
            surface,
            (*type_theme["keyline"], 36),
            (footer_plate.x + 2, footer_plate.y - 4),
            (footer_plate.right - 2, footer_plate.y - 4),
            1,
        )


def _draw_cost_badge_shell(surface: Any, rect: Any, type_theme: dict[str, Any], interaction: dict[str, bool]) -> None:
    fill = type_theme["cost_fill"] if not interaction["disabled"] else _blend_color(type_theme["cost_fill"], (92, 98, 110), 0.48)
    border = type_theme["cost_ring"] if not interaction["disabled"] else _blend_color(type_theme["cost_ring"], (132, 138, 148), 0.42)
    pygame.draw.polygon(surface, fill, _hex_points(rect))
    pygame.draw.polygon(surface, border, _hex_points(rect), max(1, rect.width // 10))

    highlight = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.polygon(
        highlight,
        (255, 255, 255, 34),
        [
            (rect.width // 2, 2),
            (rect.width - max(6, rect.width // 5), rect.height // 4),
            (rect.width // 2, rect.height // 2),
            (max(6, rect.width // 5), rect.height // 4),
        ],
    )
    surface.blit(highlight, rect.topleft)


def _draw_art_frame_accents(surface: Any, rect: Any, type_theme: dict[str, Any], variant: str) -> None:
    accent = (*type_theme["accent"], 150 if variant == "full" else 110)
    rail_len = max(12, int(rect.width * 0.12))
    rail_depth = max(2, int(rect.width * 0.012))
    top_left = [
        (rect.x + 8, rect.y + 14),
        (rect.x + 8, rect.y + 14 + rail_len),
        (rect.x + 8 + rail_depth, rect.y + 14 + rail_len),
        (rect.x + 8 + rail_depth, rect.y + 14),
    ]
    bottom_right = [
        (rect.right - 14 - rail_len, rect.bottom - 10),
        (rect.right - 14, rect.bottom - 10),
        (rect.right - 14, rect.bottom - 10 - rail_depth),
        (rect.right - 14 - rail_len, rect.bottom - 10 - rail_depth),
    ]
    pygame.draw.polygon(surface, accent, top_left)
    if variant != "mini":
        pygame.draw.polygon(surface, (*type_theme["accent_soft"], 126), bottom_right)


def _draw_header_motif(surface: Any, rect: Any, card_theme: dict[str, Any]) -> None:
    type_theme = card_theme["type_theme"]
    motif_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    motif_kind = type_theme["title_motif"]

    if motif_kind == "slashes":
        for index in range(3):
            start_x = int(rect.width * (0.18 + (index * 0.16)))
            pygame.draw.line(
                motif_surface,
                (255, 255, 255, 24),
                (start_x, rect.height - 4),
                (start_x + max(10, rect.width // 7), 4),
                1,
            )
    elif motif_kind == "circuit":
        mid_y = rect.height // 2
        pygame.draw.line(motif_surface, (255, 255, 255, 22), (8, mid_y), (rect.width - 8, mid_y), 1)
        for node_x in (rect.width // 4, rect.width // 2, (rect.width * 3) // 4):
            pygame.draw.circle(motif_surface, (255, 255, 255, 30), (node_x, mid_y), 2)
    elif motif_kind == "sigil":
        pygame.draw.circle(motif_surface, (255, 255, 255, 24), (rect.width - 22, rect.height // 2), max(5, rect.height // 4), 1)
    else:
        for offset in range(10, rect.width - 8, max(12, rect.width // 5)):
            pygame.draw.line(motif_surface, (255, 255, 255, 20), (offset, 5), (offset, rect.height - 5), 1)

    surface.blit(_mask_surface_to_panel(motif_surface, "header"), rect.topleft)


def _draw_cost_text(
    surface: Any,
    rect: Any,
    cost_text: str,
    font: Any,
    type_theme: dict[str, Any],
    interaction: dict[str, bool],
) -> None:
    color = type_theme["cost_text"] if not interaction["disabled"] else _blend_color(type_theme["cost_text"], (150, 154, 164), 0.45)
    rendered = font.render(cost_text, True, color)
    surface.blit(rendered, rendered.get_rect(center=(rect.centerx, rect.centery + max(0, rect.height // 22))))


def _draw_header_text(
    surface: Any,
    rect: Any,
    text: str,
    font: Any,
    type_theme: dict[str, Any],
    interaction: dict[str, bool],
) -> None:
    color = type_theme["accent"] if not interaction["disabled"] else _blend_color(type_theme["accent"], (120, 126, 136), 0.5)
    inner = rect.inflate(-max(10, rect.width // 14), -max(4, rect.height // 5))
    fitted = _fit_text_ellipsis(text, font, inner.width)
    rendered = font.render(fitted, True, color)
    surface.blit(rendered, (inner.x, inner.y + max(0, (inner.height - rendered.get_height()) // 2)))


def _draw_title_text(
    surface: Any,
    rect: Any,
    text: str,
    primary_font: Any,
    fallback_font: Any,
    type_theme: dict[str, Any],
) -> None:
    font = primary_font if primary_font.size(text)[0] <= rect.width else fallback_font
    fitted = _fit_text_ellipsis(text, font, rect.width)
    rendered = font.render(fitted, True, type_theme["title_text"])
    y = rect.y + max(0, (rect.height - rendered.get_height()) // 2)
    shadow = font.render(fitted, True, (0, 0, 0))
    shadow.set_alpha(90)
    surface.blit(shadow, (rect.x + 2, y + 2))
    surface.blit(rendered, (rect.x, y))


def _draw_type_chip(surface: Any, rect: Any, card_theme: dict[str, Any], font: Any) -> None:
    badge = _type_badge(card_theme)
    fill = _blend_color((10, 14, 24), badge["color"], 0.26)
    _draw_beveled_panel(surface, rect, fill, kind="chip")
    _draw_beveled_outline(surface, rect, badge["color"], 1, kind="chip")
    fitted = _fit_text_ellipsis(badge["label"], font, rect.width - 10)
    rendered = font.render(fitted, True, badge["soft"])
    surface.blit(rendered, rendered.get_rect(center=(rect.centerx, rect.centery + 1)))


def _draw_full_rules(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
    fonts: dict[str, Any],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
) -> None:
    type_theme = card_theme["type_theme"]
    label_rect = layout["effect_label"]
    _draw_rules_header_row(surface, label_rect, fonts["effect_label"], type_theme, _primary_effect_cue(card))

    rules_font = fonts["rules"]
    line_step = max(rules_font.get_linesize(), int(rules_font.get_linesize() * CARD_TYPOGRAPHY["description_line_height"]))
    max_lines = max(2, layout["rules_text"].height // max(1, line_step))
    wrapped = _wrap_rule_entries(
        renderable_card_rule_entries(card),
        rules_font,
        layout["rules_text"].width,
        max_lines=max_lines,
    )
    y = layout["rules_text"].y
    for entry in wrapped:
        rendered = rules_font.render(entry["text"], True, _rule_line_color(type_theme, entry["tone"]))
        surface.blit(rendered, (layout["rules_text"].x, y))
        y += line_step

    _draw_footer_metadata(
        surface,
        layout["rules_footer"],
        _metadata_summary(card, card_theme),
        fonts["meta"],
        type_theme,
        shortcut_label=shortcut_label,
        footer_label=footer_label,
        note_label=note_label,
    )


def _draw_compact_rules(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
    fonts: dict[str, Any],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
) -> None:
    type_theme = card_theme["type_theme"]
    label_rect = layout["effect_label"]
    _draw_rules_header_row(surface, label_rect, fonts["compact_meta"], type_theme, _primary_effect_cue(card))

    rules_font = fonts["compact_rules"]
    max_lines = max(2, layout["rules_text"].height // max(1, rules_font.get_linesize()))
    wrapped = _wrap_rule_entries(
        renderable_card_rule_entries(card),
        rules_font,
        layout["rules_text"].width,
        max_lines=max_lines,
    )
    y = layout["rules_text"].y
    for entry in wrapped:
        rendered = rules_font.render(entry["text"], True, _rule_line_color(type_theme, entry["tone"]))
        surface.blit(rendered, (layout["rules_text"].x, y))
        y += rules_font.get_linesize()

    if layout.get("rules_footer") is not None:
        _draw_footer_metadata(
            surface,
            layout["rules_footer"],
            _metadata_summary(card, card_theme),
            fonts["compact_meta"],
            type_theme,
            shortcut_label=shortcut_label,
            footer_label=footer_label,
            note_label=note_label,
        )


def _draw_mini_face(
    surface: Any,
    layout: dict[str, Any],
    card: dict[str, Any],
    card_theme: dict[str, Any],
    fonts: dict[str, Any],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
) -> None:
    del shortcut_label
    type_theme = card_theme["type_theme"]
    _draw_mini_cue_row(surface, layout["effect_label"], fonts["mini_meta"], card_theme, _primary_effect_cue(card))

    summary = compact_card_summary(card)
    fitted_lines = _wrap_lines_clamped([summary], fonts["mini_rules"], layout["rules_text"].width, max_lines=2)
    y = layout["rules_text"].y
    for line in fitted_lines:
        rendered = fonts["mini_rules"].render(line, True, type_theme["primary_support"])
        surface.blit(rendered, (layout["rules_text"].x, y))
        y += fonts["mini_rules"].get_linesize()

    footer_text = note_label or footer_label or _metadata_summary(card, card_theme)
    fitted = _fit_text_ellipsis(footer_text, fonts["mini_meta"], layout["rules_panel"].width - 16)
    rendered = fonts["mini_meta"].render(fitted, True, type_theme["footer_text"])
    surface.blit(rendered, (layout["rules_panel"].x + 8, layout["rules_panel"].bottom - rendered.get_height() - 6))


def _draw_footer_metadata(
    surface: Any,
    rect: Any,
    left_text: str,
    font: Any,
    type_theme: dict[str, Any],
    *,
    shortcut_label: str | None,
    footer_label: str | None,
    note_label: str | None,
) -> None:
    x = rect.x
    right = rect.right
    pill_label = note_label or footer_label
    pill_fill = type_theme["chip_fill"]
    pill_outline = type_theme["accent"]
    pill_text_color = type_theme["chip_text"]

    if pill_label:
        if note_label:
            pill_fill = _blend_color(type_theme["chip_fill"], (98, 34, 26), 0.42)
            pill_outline = (248, 156, 112)
            pill_text_color = (255, 224, 204)
        pill_width = min(max(54, font.size(pill_label)[0] + 16), max(54, rect.width // 2))
        pill_rect = pygame.Rect(right - pill_width, rect.y, pill_width, rect.height)
        _draw_footer_pill(surface, pill_rect, pill_label, font, pill_fill, pill_outline, pill_text_color)
        right = pill_rect.x - 6

    if shortcut_label is not None:
        badge_width = max(rect.height, font.size(shortcut_label)[0] + 12)
        badge_rect = pygame.Rect(right - badge_width, rect.y, badge_width, rect.height)
        _draw_footer_pill(surface, badge_rect, shortcut_label, font, (12, 16, 28), type_theme["accent"], type_theme["accent"])
        right = badge_rect.x - 6

    available_width = max(10, right - x)
    fitted = _fit_text_ellipsis(left_text, font, available_width)
    rendered = font.render(fitted, True, type_theme["primary_support"])
    surface.blit(rendered, (x, rect.y + max(0, (rect.height - rendered.get_height()) // 2)))


def _draw_footer_pill(
    surface: Any,
    rect: Any,
    label: str,
    font: Any,
    fill: tuple[int, ...],
    outline: tuple[int, ...],
    text_color: tuple[int, int, int],
) -> None:
    _draw_beveled_panel(surface, rect, fill, kind="footer_pill")
    _draw_beveled_outline(surface, rect, outline, 1, kind="footer_pill")
    fitted = _fit_text_ellipsis(label, font, rect.width - 10)
    rendered = font.render(fitted, True, text_color)
    surface.blit(rendered, rendered.get_rect(center=(rect.centerx, rect.centery + 1)))


def _draw_rules_header_row(
    surface: Any,
    rect: Any,
    font: Any,
    type_theme: dict[str, Any],
    effect_cue: dict[str, Any],
) -> None:
    label = font.render("EFFECT", True, type_theme["muted"])
    label_y = rect.y + max(0, (rect.height - label.get_height()) // 2)
    surface.blit(label, (rect.x, label_y))

    cue_label = str(effect_cue["label"])
    cue_width = min(max(48, font.size(cue_label)[0] + rect.height + 10), max(48, rect.width // 2))
    cue_rect = pygame.Rect(rect.right - cue_width, rect.y, cue_width, rect.height)
    _draw_cue_pill(surface, cue_rect, cue_label, font, effect_cue)


def _draw_mini_cue_row(
    surface: Any,
    rect: Any,
    font: Any,
    card_theme: dict[str, Any],
    effect_cue: dict[str, Any],
) -> None:
    type_badge = _type_badge(card_theme)
    type_width = min(max(28, font.size(type_badge["label"])[0] + 10), max(28, rect.width // 2 - 4))
    effect_width = min(
        max(34, font.size(str(effect_cue["label"]))[0] + rect.height + 10),
        max(34, rect.width - type_width - 6),
    )
    type_rect = pygame.Rect(rect.x, rect.y, type_width, rect.height)
    effect_rect = pygame.Rect(rect.right - effect_width, rect.y, effect_width, rect.height)

    _draw_beveled_panel(surface, type_rect, _blend_color((10, 14, 24), type_badge["color"], 0.26), kind="chip")
    _draw_beveled_outline(surface, type_rect, type_badge["color"], 1, kind="chip")
    type_text = _fit_text_ellipsis(type_badge["label"], font, type_rect.width - 8)
    type_rendered = font.render(type_text, True, type_badge["soft"])
    surface.blit(type_rendered, type_rendered.get_rect(center=(type_rect.centerx, type_rect.centery + 1)))

    _draw_cue_pill(surface, effect_rect, str(effect_cue["label"]), font, effect_cue)


def _draw_cue_pill(
    surface: Any,
    rect: Any,
    label: str,
    font: Any,
    cue: dict[str, Any],
) -> None:
    fill = _blend_color((10, 14, 24), cue["color"], 0.22)
    _draw_beveled_panel(surface, rect, fill, kind="footer_pill")
    _draw_beveled_outline(surface, rect, cue["color"], 1, kind="footer_pill")

    icon_size = max(7, min(rect.height - 6, rect.width // 4))
    icon_rect = pygame.Rect(rect.x + 5, rect.centery - (icon_size // 2), icon_size, icon_size)
    _draw_cue_glyph(surface, icon_rect, str(cue.get("glyph", "dot")), cue["soft"])

    text_x = icon_rect.right + 4
    available_width = max(8, rect.right - text_x - 4)
    fitted = _fit_text_ellipsis(label, font, available_width)
    rendered = font.render(fitted, True, cue["soft"])
    surface.blit(rendered, (text_x, rect.y + max(0, (rect.height - rendered.get_height()) // 2)))


def _draw_cue_glyph(surface: Any, rect: Any, glyph: str, color: tuple[int, int, int]) -> None:
    if glyph == "slash":
        pygame.draw.line(surface, color, (rect.x + 1, rect.bottom - 1), (rect.right - 1, rect.y + 1), 2)
        return
    if glyph == "shield":
        points = [
            (rect.centerx, rect.y + 1),
            (rect.right - 2, rect.y + max(2, rect.height // 4)),
            (rect.right - 3, rect.bottom - 3),
            (rect.centerx, rect.bottom - 1),
            (rect.x + 3, rect.bottom - 3),
            (rect.x + 2, rect.y + max(2, rect.height // 4)),
        ]
        pygame.draw.polygon(surface, color, points, 1)
        return
    if glyph == "cross":
        pygame.draw.line(surface, color, (rect.centerx, rect.y + 1), (rect.centerx, rect.bottom - 1), 2)
        pygame.draw.line(surface, color, (rect.x + 1, rect.centery), (rect.right - 1, rect.centery), 2)
        return
    if glyph == "flow":
        points = [
            (rect.x + 1, rect.centery),
            (rect.centerx - 1, rect.y + 2),
            (rect.centerx, rect.centery),
            (rect.right - 2, rect.bottom - 2),
        ]
        pygame.draw.lines(surface, color, False, points, 2)
        return
    if glyph == "up":
        pygame.draw.line(surface, color, (rect.centerx, rect.bottom - 1), (rect.centerx, rect.y + 2), 2)
        pygame.draw.line(surface, color, (rect.centerx, rect.y + 2), (rect.x + 2, rect.y + 5), 2)
        pygame.draw.line(surface, color, (rect.centerx, rect.y + 2), (rect.right - 2, rect.y + 5), 2)
        return
    if glyph == "spark":
        pygame.draw.line(surface, color, (rect.centerx, rect.y + 1), (rect.centerx, rect.bottom - 1), 1)
        pygame.draw.line(surface, color, (rect.x + 1, rect.centery), (rect.right - 1, rect.centery), 1)
        pygame.draw.line(surface, color, (rect.x + 2, rect.y + 2), (rect.right - 2, rect.bottom - 2), 1)
        pygame.draw.line(surface, color, (rect.right - 2, rect.y + 2), (rect.x + 2, rect.bottom - 2), 1)
        return
    if glyph == "hazard":
        points = [(rect.centerx, rect.y + 1), (rect.right - 1, rect.bottom - 1), (rect.x + 1, rect.bottom - 1)]
        pygame.draw.polygon(surface, color, points, 1)
        pygame.draw.line(surface, color, (rect.centerx, rect.y + 4), (rect.centerx, rect.bottom - 4), 1)
        return
    pygame.draw.circle(surface, color, rect.center, max(2, rect.width // 4))


def _draw_serial_lane(
    surface: Any,
    rect: Any,
    card: dict[str, Any],
    card_theme: dict[str, Any],
    fonts: dict[str, Any],
    variant: str,
) -> None:
    del variant
    type_theme = card_theme["type_theme"]
    serial_font = fonts["serial"]
    serial_text = _fit_text_ellipsis(_serial_code(card), serial_font, max(20, rect.width - 18))
    serial_surface = serial_font.render(serial_text, True, type_theme["footer_text"])
    surface.blit(serial_surface, (rect.x, rect.y))


def _build_atlas_art_surface(
    art_rect: Any,
    card_theme: dict[str, Any],
    card: dict[str, Any],
    *,
    variant: str,
) -> Any | None:
    if pygame is None:
        return None

    art_surface = pygame.Surface(art_rect.size, pygame.SRCALPHA)
    art_palette = card_theme["art_palette"]
    type_theme = card_theme["type_theme"]
    top_color = _blend_color(art_palette["art_top"], (18, 24, 32), 0.26)
    bottom_color = _blend_color(art_palette["art_bottom"], (8, 12, 18), 0.42)
    _fill_vertical_gradient(art_surface, art_surface.get_rect(), top_color, bottom_color)

    art_crop = sprite_sheet_assets.get_card_art_crop(str(card.get("name", "")))
    if art_crop is not None:
        art_surface.blit(_cover_scaled_surface(art_crop, art_rect.size), (0, 0))
    else:
        _draw_procedural_art_panel(art_surface, art_surface.get_rect(), card_theme, art_palette, card)

    shade = pygame.Surface(art_rect.size, pygame.SRCALPHA)
    shade.fill((6, 10, 18, 28 if variant == "mini" else 22))
    art_surface.blit(shade, (0, 0))

    overlay_alpha = 0.38 if art_crop is not None else 0.72
    _draw_art_style_overlay(art_surface, art_surface.get_rect(), card_theme, overlay_alpha=overlay_alpha)
    if variant != "mini":
        _draw_scan_texture(art_surface, art_surface.get_rect(), type_theme, spacing=max(3, art_rect.height // 40))
        _draw_glass_glare(art_surface, art_surface.get_rect(), type_theme)
    _draw_bottom_readability_gradient(art_surface, art_surface.get_rect(), alpha=74 if variant == "full" else 54)
    return art_surface


def _cover_scaled_surface(source: Any, target_size: tuple[int, int]) -> Any:
    target_width = max(1, int(target_size[0]))
    target_height = max(1, int(target_size[1]))
    src_width, src_height = source.get_size()
    if src_width <= 0 or src_height <= 0:
        return source.copy()

    scale = max(target_width / src_width, target_height / src_height)
    scaled_width = max(1, int(math.ceil(src_width * scale)))
    scaled_height = max(1, int(math.ceil(src_height * scale)))
    scaled = pygame.transform.smoothscale(source, (scaled_width, scaled_height))
    output = pygame.Surface((target_width, target_height), pygame.SRCALPHA)
    dest = scaled.get_rect(center=(target_width // 2, target_height // 2))
    output.blit(scaled, dest)
    return output


def _draw_procedural_art_panel(
    surface: Any,
    rect: Any,
    card_theme: dict[str, Any],
    art_palette: dict[str, Any],
    card: dict[str, Any],
) -> None:
    highlight_color = (*art_palette["art_highlight"], 84)
    pygame.draw.circle(surface, highlight_color, (int(rect.width * 0.68), int(rect.height * 0.34)), max(18, rect.height // 5))
    pygame.draw.circle(surface, (*art_palette["art_highlight"], 42), (int(rect.width * 0.32), int(rect.height * 0.58)), max(22, rect.height // 4))
    _draw_art_style_overlay(surface, rect, card_theme, overlay_alpha=0.88)

    motif = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.line(
        motif,
        (*card_theme["type_theme"]["accent_soft"], 86),
        (int(rect.width * 0.16), int(rect.height * 0.74)),
        (int(rect.width * 0.80), int(rect.height * 0.24)),
        3,
    )
    pygame.draw.circle(
        motif,
        (*art_palette["art_highlight"], 112),
        (int(rect.width * 0.56), int(rect.height * 0.42)),
        max(14, rect.height // 6),
        2,
    )
    surface.blit(motif, (0, 0))
    del card


def _draw_art_style_overlay(surface: Any, rect: Any, card_theme: dict[str, Any], *, overlay_alpha: float) -> None:
    art_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    art_palette = card_theme["art_palette"]
    type_theme = card_theme["type_theme"]
    art_style = card_theme["art_style"]
    grid_alpha = max(10, int(art_palette["art_grid"][3] * overlay_alpha))

    if art_style == "circuit_burst":
        for index in range(4):
            start_x = 10 + (index * max(10, rect.width // 6))
            pygame.draw.line(
                art_surface,
                (*art_palette["art_highlight"], min(120, grid_alpha + 24)),
                (start_x, rect.height - 12),
                (start_x + max(14, rect.width // 8), 10 + (index * 6)),
                2,
            )
    elif art_style == "signal_mesh":
        for index in range(5):
            offset_y = 10 + (index * max(8, rect.height // 7))
            pygame.draw.line(
                art_surface,
                (*type_theme["accent_soft"], grid_alpha),
                (8, offset_y),
                (rect.width - 8, offset_y + (4 if index % 2 == 0 else -4)),
                1,
            )
    elif art_style == "patch_grid":
        cell = max(12, min(rect.width, rect.height) // 5)
        for cell_x in range(0, rect.width, cell):
            for cell_y in range(0, rect.height, cell):
                alpha = max(10, int(grid_alpha * (0.8 if (cell_x + cell_y) // cell % 2 == 0 else 0.45)))
                pygame.draw.rect(
                    art_surface,
                    (255, 255, 255, alpha),
                    pygame.Rect(cell_x + 2, cell_y + 2, max(4, cell - 4), max(4, cell - 4)),
                    1,
                    border_radius=3,
                )

    if type_theme["art_motif"] == "slashes":
        for offset in (0.18, 0.42, 0.66):
            start_x = int(rect.width * offset)
            pygame.draw.line(
                art_surface,
                (*type_theme["accent_soft"], min(110, grid_alpha + 24)),
                (start_x, rect.height - 10),
                (min(rect.width - 6, start_x + max(12, rect.width // 7)), 6),
                1,
            )
    else:
        base_y = int(rect.height * 0.30)
        pygame.draw.line(art_surface, (*type_theme["accent_soft"], grid_alpha), (12, base_y), (rect.width - 12, base_y), 1)
        pygame.draw.line(art_surface, (*type_theme["accent_soft"], grid_alpha), (rect.width // 2, 12), (rect.width // 2, rect.height - 12), 1)
        for node in ((rect.width // 3, base_y), (rect.width // 2, rect.height // 2), ((rect.width * 2) // 3, rect.height - base_y)):
            pygame.draw.circle(art_surface, (*type_theme["accent_soft"], min(112, grid_alpha + 24)), node, 2)

    surface.blit(art_surface, (0, 0))


def _draw_scan_texture(surface: Any, rect: Any, type_theme: dict[str, Any], *, spacing: int) -> None:
    texture = pygame.Surface(rect.size, pygame.SRCALPHA)
    color = type_theme["scanline"]
    for y in range(0, rect.height, max(2, spacing)):
        pygame.draw.line(texture, color, (0, y), (rect.width, y), 1)
    surface.blit(texture, (0, 0))


def _draw_glass_glare(surface: Any, rect: Any, type_theme: dict[str, Any]) -> None:
    glare = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.polygon(
        glare,
        type_theme["glare"],
        [
            (0, int(rect.height * 0.14)),
            (int(rect.width * 0.18), 0),
            (int(rect.width * 0.32), 0),
            (int(rect.width * 0.10), int(rect.height * 0.46)),
        ],
    )
    surface.blit(glare, (0, 0))


def _draw_bottom_readability_gradient(surface: Any, rect: Any, *, alpha: int) -> None:
    gradient = pygame.Surface(rect.size, pygame.SRCALPHA)
    band_height = max(16, rect.height // 3)
    start_y = rect.height - band_height
    for index in range(band_height):
        blend = index / max(1, band_height - 1)
        row_alpha = int(alpha * blend)
        pygame.draw.line(
            gradient,
            (6, 10, 18, row_alpha),
            (0, start_y + index),
            (rect.width, start_y + index),
        )
    surface.blit(gradient, (0, 0))


def _wrap_lines_clamped(lines: list[str], font: Any, width: int, *, max_lines: int) -> list[str]:
    wrapped: list[str] = []
    overflowed = False
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
                    overflowed = True
                    break
            current = word
        if overflowed:
            break
        if current:
            wrapped.append(current)
            if len(wrapped) >= max_lines:
                overflowed = True
                break
    if overflowed and wrapped:
        wrapped[-1] = _fit_text_ellipsis(f"{wrapped[-1]}...", font, width)
    return wrapped[:max_lines]


def _wrap_rule_entries(
    entries: list[dict[str, str]],
    font: Any,
    width: int,
    *,
    max_lines: int,
) -> list[dict[str, str]]:
    wrapped: list[dict[str, str]] = []
    overflowed = False
    for entry in entries:
        raw_line = str(entry.get("text", ""))
        tone = str(entry.get("tone", "base"))
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
                wrapped.append({"text": current, "tone": tone})
                if len(wrapped) >= max_lines:
                    overflowed = True
                    break
            current = word
        if overflowed:
            break
        if current:
            wrapped.append({"text": current, "tone": tone})
            if len(wrapped) >= max_lines:
                overflowed = True
                break
    if overflowed and wrapped:
        wrapped[-1] = {
            **wrapped[-1],
            "text": _fit_text_ellipsis(f"{wrapped[-1]['text']}...", font, width),
        }
    return wrapped[:max_lines]


def _rule_line_color(type_theme: dict[str, Any], tone: str) -> tuple[int, int, int]:
    if tone == "corruption_active":
        return (255, 214, 110)
    if tone == "corruption_inactive":
        return type_theme["footer_text"]
    return type_theme["primary_value"]


def _fit_text_ellipsis(text: str, font: Any, width: int) -> str:
    if font.size(text)[0] <= width:
        return text
    ellipsis = "..."
    if width <= font.size(ellipsis)[0]:
        return ellipsis
    trimmed = text
    while trimmed:
        trimmed = trimmed[:-1]
        candidate = f"{trimmed.rstrip()}{ellipsis}"
        if font.size(candidate)[0] <= width:
            return candidate
    return ellipsis


def _metadata_summary(card: dict[str, Any], card_theme: dict[str, Any]) -> str:
    del card_theme
    tokens = [card_type_label(card).upper()]
    keywords = card.get("keywords", [])
    if isinstance(keywords, list):
        for keyword in keywords:
            token = str(keyword).replace("_", " ").upper()
            if token and token not in tokens:
                tokens.append(token)
            if len(tokens) >= 3:
                break
    return " • ".join(tokens[:3])


def _serial_code(card: dict[str, Any]) -> str:
    raw = str(card.get("id", card.get("name", "card"))).strip().upper().replace("_", "-")
    return raw[:18] if raw else "CARD"


def _first_primary_effect_key(card: dict[str, Any]) -> str:
    for effect in card.get("effects", []):
        cue_key = _effect_cue_key(effect)
        if cue_key is not None:
            return cue_key

    for trigger in card.get("triggers", []):
        if not isinstance(trigger, dict):
            continue
        for effect in trigger.get("effects", []):
            cue_key = _effect_cue_key(effect)
            if cue_key is not None:
                return cue_key

    for effect in card.get("resource_effects", []):
        cue_key = _effect_cue_key(effect)
        if cue_key is not None:
            return cue_key

    return "UTIL"


def _effect_cue_key(effect: Any) -> str | None:
    if not isinstance(effect, dict):
        return None

    effect_type = effect.get("type")
    if isinstance(effect_type, str):
        normalized = effect_type.strip().lower()
        for cue_key, supported_types in _PRIMARY_EFFECT_TYPES.items():
            if normalized in supported_types:
                return cue_key
        return "UTIL"

    resource = effect.get("resource")
    if isinstance(resource, str) and resource.strip().lower() == "energy":
        return "FLOW"

    if "resource" in effect or "delta" in effect:
        return "UTIL"

    return None


def _mask_surface_to_panel(layer: Any, kind: str) -> Any:
    mask = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
    _draw_beveled_panel(mask, mask.get_rect(), (255, 255, 255, 255), kind=kind)
    masked = layer.copy()
    masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return masked


def _panel_points(rect: Any, kind: str) -> list[tuple[int, int]]:
    minimum = min(rect.width, rect.height)
    base = max(4, int(minimum * 0.12))
    cuts = {
        "card": {"tl": base, "tr": base, "br": base + 2, "bl": base},
        "header": {"tl": max(4, base // 2), "tr": max(6, base // 2), "br": max(8, int(base * 1.8)), "bl": max(3, base // 3)},
        "art": {"tl": max(6, base // 2), "tr": max(10, int(base * 1.4)), "br": max(5, base // 3), "bl": max(10, int(base * 1.3))},
        "rules": {"tl": max(6, base // 2), "tr": max(4, base // 3), "br": max(6, base // 2), "bl": max(4, base // 3)},
        "chip": {"tl": max(5, base // 2), "tr": max(4, base // 3), "br": max(5, base // 2), "bl": max(4, base // 3)},
        "footer": {"tl": max(4, base // 3), "tr": max(4, base // 3), "br": max(4, base // 3), "bl": max(4, base // 3)},
        "footer_pill": {"tl": max(4, base // 3), "tr": max(6, base // 2), "br": max(4, base // 3), "bl": max(6, base // 2)},
        "header_tab": {"tl": max(4, base // 3), "tr": max(4, base // 3), "br": max(6, base // 2), "bl": max(4, base // 3)},
    }[kind]
    return _bevel_points(rect, cuts)


def _bevel_points(rect: Any, cuts: dict[str, int]) -> list[tuple[int, int]]:
    tl = min(rect.width // 3, rect.height // 3, cuts["tl"])
    tr = min(rect.width // 3, rect.height // 3, cuts["tr"])
    br = min(rect.width // 3, rect.height // 3, cuts["br"])
    bl = min(rect.width // 3, rect.height // 3, cuts["bl"])
    return [
        (rect.x + tl, rect.y),
        (rect.right - tr, rect.y),
        (rect.right, rect.y + tr),
        (rect.right, rect.bottom - br),
        (rect.right - br, rect.bottom),
        (rect.x + bl, rect.bottom),
        (rect.x, rect.bottom - bl),
        (rect.x, rect.y + tl),
    ]


def _hex_points(rect: Any) -> list[tuple[int, int]]:
    inset = max(4, rect.width // 5)
    return [
        (rect.centerx, rect.y),
        (rect.right - inset, rect.y + max(3, rect.height // 6)),
        (rect.right - inset, rect.bottom - max(3, rect.height // 6)),
        (rect.centerx, rect.bottom),
        (rect.x + inset, rect.bottom - max(3, rect.height // 6)),
        (rect.x + inset, rect.y + max(3, rect.height // 6)),
    ]


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
        brighten = 0.08
    if interaction["selected"]:
        brighten = 0.16
    if interaction["disabled"]:
        brighten = -0.14
    return _shift_brightness(type_theme["title_top"], brighten), _shift_brightness(type_theme["title_bottom"], brighten)


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
    if effect_type == "apply_bleed" and isinstance(value, int):
        return f"Apply {value} Bleed."
    if effect_type == "apply_infect" and isinstance(value, int):
        return f"Apply {value} Infect."
    if effect_type == "apply_nullified" and isinstance(value, int):
        return "Apply Nullified."
    if effect_type == "cleanse_status" and isinstance(value, int):
        status_id = str(effect.get("status_id", "status")).replace("_", " ").title()
        return f"Cleanse {value} {status_id}."
    if effect_type == "remove_nullified":
        return "Remove Nullified."
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
