from __future__ import annotations

from typing import Any

from ui.render_utils import DEFAULT_TEXT_COLOR


CARD_PORTRAIT_HEIGHT_RATIO = 320 / 220

CARD_PORTRAIT_LAYOUT_SPEC = {
    "safe_margin_x": 8 / 220,
    "safe_margin_y": 8 / 320,
    "header": {"x": 12 / 220, "y": 10 / 320, "w": 180 / 220, "h": 26 / 320},
    "title": {"x": 18 / 220, "y": 12 / 320, "w": 164 / 220, "h": 22 / 320},
    "cost_badge": {"x": 190 / 220, "y": 8 / 320, "w": 30 / 220, "h": 38 / 320},
    "art_panel": {"x": 10 / 220, "y": 44 / 320, "w": 200 / 220, "h": 144 / 320},
    "faction_chip": {"x": 16 / 220, "y": 170 / 320, "w": 82 / 220, "h": 20 / 320},
    "rules_panel": {"x": 10 / 220, "y": 198 / 320, "w": 200 / 220, "h": 78 / 320},
    "rules_label_height": 14 / 320,
    "rules_footer_height": 20 / 320,
    "serial_lane": {"x": 14 / 220, "y": 286 / 320, "w": 192 / 220, "h": 18 / 320},
}

CARD_COMPACT_LAYOUT_SPEC = {
    "safe_margin_x": 0.05,
    "safe_margin_y": 0.08,
    "header": {"x": 0.06, "y": 0.08, "w": 0.58, "h": 0.16},
    "title": {"x": 0.10, "y": 0.10, "w": 0.50, "h": 0.12},
    "cost_badge": {"x": 0.78, "y": 0.06, "w": 0.14, "h": 0.22},
    "art_panel": {"x": 0.64, "y": 0.18, "w": 0.28, "h": 0.48},
    "faction_chip": {"x": 0.66, "y": 0.60, "w": 0.22, "h": 0.11},
    "rules_panel": {"x": 0.06, "y": 0.52, "w": 0.56, "h": 0.28},
    "rules_label_height": 0.08,
    "rules_footer_height": 0.10,
    "serial_lane": {"x": 0.08, "y": 0.84, "w": 0.84, "h": 0.08},
}

CARD_MINI_LAYOUT_SPEC = {
    "safe_margin_x": 0.06,
    "safe_margin_y": 0.10,
    "header": {"x": 0.10, "y": 0.10, "w": 0.54, "h": 0.18},
    "title": {"x": 0.12, "y": 0.13, "w": 0.50, "h": 0.11},
    "cost_badge": {"x": 0.78, "y": 0.08, "w": 0.14, "h": 0.26},
    "art_panel": {"x": 0.72, "y": 0.18, "w": 0.18, "h": 0.48},
    "rules_panel": {"x": 0.10, "y": 0.50, "w": 0.56, "h": 0.20},
    "rules_label_height": 0.08,
    "rules_footer_height": 0.0,
    "serial_lane": {"x": 0.10, "y": 0.78, "w": 0.80, "h": 0.10},
}

CARD_TYPOGRAPHY = {
    "cost": 0.092,
    "header": 0.028,
    "title": 0.086,
    "effect_label": 0.034,
    "description": 0.056,
    "description_line_height": 1.14,
    "metadata": 0.036,
    "serial": 0.032,
    "compact_title": 0.17,
    "compact_description": 0.112,
    "compact_metadata": 0.094,
    "mini_title": 0.16,
    "mini_description": 0.105,
    "mini_metadata": 0.09,
}

CARD_ART_PALETTES = {
    "starter_neutral": {
        "art_top": (88, 208, 220),
        "art_bottom": (28, 42, 74),
        "art_highlight": (240, 196, 96),
        "art_grid": (255, 255, 255, 54),
    },
    "netrunner": {
        "art_top": (86, 242, 222),
        "art_bottom": (18, 60, 92),
        "art_highlight": (110, 244, 222),
        "art_grid": (255, 255, 255, 70),
    },
    "enforcer_crimson": {
        "art_top": (214, 78, 66),
        "art_bottom": (62, 22, 30),
        "art_highlight": (255, 204, 124),
        "art_grid": (255, 244, 232, 64),
    },
    "operator_teal": {
        "art_top": (84, 226, 214),
        "art_bottom": (18, 58, 88),
        "art_highlight": (168, 250, 238),
        "art_grid": (232, 255, 255, 68),
    },
    "bio_hacker_verdant": {
        "art_top": (114, 214, 138),
        "art_bottom": (24, 64, 44),
        "art_highlight": (218, 250, 170),
        "art_grid": (238, 255, 236, 62),
    },
}

CARD_FACTION_THEMES = {
    "shared": {
        "display_name": "COMMON",
        "accent": (98, 192, 236),
        "accent_soft": (198, 236, 255),
        "cost_fill": (246, 198, 84),
        "cost_ring": (255, 224, 136),
    },
    "starter": {
        "display_name": "COMMON",
        "accent": (98, 192, 236),
        "accent_soft": (198, 236, 255),
        "cost_fill": (246, 198, 84),
        "cost_ring": (255, 224, 136),
    },
    "netrunner": {
        "display_name": "NETRUNNER",
        "accent": (92, 228, 218),
        "accent_soft": (190, 250, 242),
        "cost_fill": (246, 198, 84),
        "cost_ring": (255, 224, 136),
    },
    "enforcer": {
        "display_name": "ENFORCER",
        "accent": (246, 140, 82),
        "accent_soft": (255, 214, 178),
        "cost_fill": (250, 166, 86),
        "cost_ring": (255, 224, 150),
    },
    "operator": {
        "display_name": "OPERATOR",
        "accent": (88, 224, 214),
        "accent_soft": (192, 252, 244),
        "cost_fill": (244, 198, 84),
        "cost_ring": (255, 224, 136),
    },
    "bio_hacker": {
        "display_name": "BIO-HACKER",
        "accent": (118, 220, 136),
        "accent_soft": (214, 250, 192),
        "cost_fill": (230, 184, 72),
        "cost_ring": (248, 222, 134),
    },
}

CARD_TYPE_THEMES = {
    "attack": {
        "title_pip": "attack",
        "title_motif": "slashes",
        "art_motif": "slashes",
        "keywords": ("impact", "aggressive"),
    },
    "skill": {
        "title_pip": "skill",
        "title_motif": "circuit",
        "art_motif": "circuit",
        "keywords": ("utility", "control"),
    },
    "power": {
        "title_pip": "power",
        "title_motif": "sigil",
        "art_motif": "circuit",
        "keywords": ("engine", "persistent"),
    },
    "curse": {
        "title_pip": "curse",
        "title_motif": "sigil",
        "art_motif": "slashes",
        "keywords": ("unstable", "hostile"),
    },
    "status": {
        "title_pip": "status",
        "title_motif": "grid",
        "art_motif": "circuit",
        "keywords": ("status", "temporary"),
    },
}

CARD_EFFECT_COLORS = {
    "damage": (248, 112, 112),
    "block": (106, 216, 252),
    "heal": (120, 228, 152),
    "draw": (236, 188, 82),
    "energy": (248, 214, 114),
}

CARD_TYPE_BADGES = {
    "attack": {"label": "ATK", "color": (244, 132, 84), "soft": (255, 222, 198)},
    "skill": {"label": "SKL", "color": (104, 214, 244), "soft": (210, 246, 255)},
    "power": {"label": "PWR", "color": (244, 196, 90), "soft": (255, 234, 180)},
    "status": {"label": "STS", "color": (176, 192, 214), "soft": (234, 240, 248)},
    "curse": {"label": "CUR", "color": (214, 126, 214), "soft": (248, 214, 255)},
}

CARD_PRIMARY_EFFECT_CUES = {
    "DMG": {"color": (246, 126, 82), "soft": (255, 220, 194), "glyph": "slash"},
    "BLK": {"color": (104, 214, 246), "soft": (210, 246, 255), "glyph": "shield"},
    "HEAL": {"color": (114, 224, 148), "soft": (214, 250, 224), "glyph": "cross"},
    "FLOW": {"color": (110, 222, 214), "soft": (214, 250, 246), "glyph": "flow"},
    "BUFF": {"color": (244, 192, 88), "soft": (255, 234, 182), "glyph": "up"},
    "DEBUFF": {"color": (224, 110, 196), "soft": (246, 214, 255), "glyph": "spark"},
    "RISK": {"color": (212, 84, 102), "soft": (255, 210, 220), "glyph": "hazard"},
    "UTIL": {"color": (156, 170, 194), "soft": (226, 232, 244), "glyph": "dot"},
}

_FRAME_COLORS = {
    "shell_outer": (4, 9, 18),
    "shell_inner": (10, 16, 28),
    "body_fill": (14, 21, 36),
    "panel_top": (22, 34, 54),
    "panel_fill": (16, 20, 34),
    "panel_fill_soft": (20, 28, 44),
    "panel_footer": (10, 14, 24),
    "text_muted": (170, 184, 206),
    "footer_text": (116, 130, 154),
    "white_keyline": (242, 247, 252),
    "title_text": (246, 249, 255),
}


def card_type_key(card: dict[str, Any]) -> str:
    return str(card.get("type", "status")).strip().lower()


def resolve_card_theme(card: dict[str, Any]) -> dict[str, Any]:
    raw_theme = card.get("theme") if isinstance(card.get("theme"), dict) else {}
    faction = str(raw_theme.get("faction", "shared")).strip().lower() or "shared"
    palette_key = raw_theme.get("palette")
    if not isinstance(palette_key, str) or not palette_key:
        palette_key = "netrunner" if faction == "netrunner" else "starter_neutral"
    art_style = raw_theme.get("art_style", "circuit_burst")
    type_key = card_type_key(card)
    type_template = CARD_TYPE_THEMES.get(type_key, CARD_TYPE_THEMES["status"])
    art_palette = CARD_ART_PALETTES.get(palette_key, CARD_ART_PALETTES["starter_neutral"])
    faction_theme = CARD_FACTION_THEMES.get(faction, CARD_FACTION_THEMES["shared"])
    return {
        "type_key": type_key,
        "faction": faction,
        "palette_key": palette_key,
        "art_style": art_style,
        "type_theme": _compose_frame_theme(type_template, faction_theme),
        "type_template": type_template,
        "faction_theme": faction_theme,
        "art_palette": art_palette,
    }


def fit_portrait_card(bounds: tuple[int, int, int, int], padding: int = 0) -> tuple[int, int, int, int]:
    x, y, width, height = bounds
    x += padding
    y += padding
    width = max(1, width - (padding * 2))
    height = max(1, height - (padding * 2))

    fit_width = min(width, int(height / CARD_PORTRAIT_HEIGHT_RATIO))
    fit_height = int(fit_width * CARD_PORTRAIT_HEIGHT_RATIO)
    if fit_height > height:
        fit_height = height
        fit_width = int(fit_height / CARD_PORTRAIT_HEIGHT_RATIO)

    offset_x = x + ((width - fit_width) // 2)
    offset_y = y + ((height - fit_height) // 2)
    return (offset_x, offset_y, fit_width, fit_height)


def _compose_frame_theme(type_template: dict[str, Any], faction_theme: dict[str, Any]) -> dict[str, Any]:
    accent = faction_theme["accent"]
    accent_soft = faction_theme["accent_soft"]
    return {
        "shape": "bevel",
        "title_shape": "header_bevel",
        "art_shape": "art_bevel",
        "outer_fill": _FRAME_COLORS["shell_outer"],
        "outer_shadow": _FRAME_COLORS["shell_inner"],
        "body_fill": _FRAME_COLORS["body_fill"],
        "title_top": _blend_color(_FRAME_COLORS["panel_top"], accent, 0.14),
        "title_bottom": _blend_color(_FRAME_COLORS["panel_fill_soft"], accent, 0.06),
        "title_text": _FRAME_COLORS["title_text"],
        "description_fill": _FRAME_COLORS["panel_fill"],
        "description_border": _blend_color(accent, _FRAME_COLORS["white_keyline"], 0.45),
        "mid_band_fill": _blend_color(_FRAME_COLORS["panel_fill_soft"], accent, 0.10),
        "mid_band_border": accent,
        "metadata_fill": _FRAME_COLORS["panel_footer"],
        "cost_fill": faction_theme["cost_fill"],
        "cost_ring": faction_theme["cost_ring"],
        "cost_text": (28, 20, 6),
        "text": DEFAULT_TEXT_COLOR,
        "muted": _FRAME_COLORS["text_muted"],
        "accent": accent,
        "accent_soft": accent_soft,
        "accent_glow": (*accent, 74),
        "type_fill": _blend_color(_FRAME_COLORS["panel_fill_soft"], accent, 0.22),
        "type_text": accent_soft,
        "primary_value": _FRAME_COLORS["title_text"],
        "primary_support": _blend_color(DEFAULT_TEXT_COLOR, accent_soft, 0.32),
        "art_border": _FRAME_COLORS["white_keyline"],
        "keyline": _FRAME_COLORS["white_keyline"],
        "chip_fill": _blend_color(_FRAME_COLORS["panel_fill_soft"], accent, 0.20),
        "chip_text": accent_soft,
        "shell_rail": _blend_color(accent, _FRAME_COLORS["white_keyline"], 0.18),
        "scanline": (*accent_soft, 18),
        "glare": (255, 255, 255, 34),
        "footer_text": _FRAME_COLORS["footer_text"],
        **type_template,
    }


def _blend_color(color_a: tuple[int, int, int], color_b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(int(color_a[index] + ((color_b[index] - color_a[index]) * amount)) for index in range(3))
