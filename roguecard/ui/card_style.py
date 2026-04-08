from __future__ import annotations

from typing import Any

from ui.render_utils import DEFAULT_TEXT_COLOR


CARD_PORTRAIT_HEIGHT_RATIO = 1.36

CARD_PORTRAIT_LAYOUT_SPEC = {
    "safe_padding_lr": 0.055,
    "safe_padding_top": 0.045,
    "safe_padding_bottom": 0.055,
    "cost_orb": {"x": 0.025, "y": 0.022, "w": 0.15, "h": 0.15},
    "title_strip": {"x": 0.175, "y": 0.035, "w": 0.66, "h": 0.11},
    "title_pip_ratio": 0.10,
    "art_panel": {"x": 0.10, "y": 0.17, "w": 0.80, "h": 0.31},
    "mid_band": {"x": 0.095, "y": 0.495, "w": 0.81, "h": 0.045},
    "primary_effect": {"x": 0.10, "y": 0.55, "w": 0.80, "h": 0.11},
    "description_box": {"x": 0.09, "y": 0.67, "w": 0.82, "h": 0.20},
    "metadata_band": {"x": 0.085, "y": 0.895, "w": 0.83, "h": 0.05},
}

CARD_TYPOGRAPHY = {
    "cost": 0.095,
    "title": 0.07,
    "type_label": 0.042,
    "primary_value": 0.08,
    "primary_support": 0.052,
    "description": 0.045,
    "description_line_height": 1.18,
    "metadata": 0.038,
    "compact_title": 0.17,
    "compact_body": 0.12,
    "compact_meta": 0.105,
}

CARD_COMPACT_LAYOUT_SPEC = {
    "cost_orb": {"x": 0.028, "y": 0.10, "size": 0.17},
    "title_strip": {"x": 0.20, "y": 0.08, "w": 0.43, "h": 0.22},
    "art_panel": {"x": 0.68, "y": 0.10, "w": 0.25, "h": 0.74},
    "type_label": {"x": 0.20, "y": 0.34, "w": 0.22, "h": 0.12},
    "summary_box": {"x": 0.20, "y": 0.50, "w": 0.43, "h": 0.26},
    "metadata": {"x": 0.20, "y": 0.80, "w": 0.43, "h": 0.12},
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

CARD_TYPE_THEMES = {
    "attack": {
        "shape": "attack",
        "title_shape": "attack",
        "art_shape": "attack",
        "outer_fill": (116, 24, 34),
        "outer_shadow": (70, 12, 20),
        "body_fill": (34, 18, 24),
        "title_top": (154, 34, 42),
        "title_bottom": (98, 18, 26),
        "title_text": (255, 242, 238),
        "description_fill": (32, 18, 28),
        "description_border": (106, 54, 68),
        "mid_band_fill": (78, 22, 28),
        "mid_band_border": (214, 112, 92),
        "metadata_fill": (26, 16, 22),
        "cost_fill": (54, 16, 20),
        "cost_ring": (246, 118, 82),
        "cost_text": (255, 242, 232),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (222, 202, 210),
        "accent": (246, 118, 82),
        "accent_soft": (255, 196, 148),
        "accent_glow": (255, 112, 84, 86),
        "type_fill": (152, 42, 52),
        "type_text": (255, 242, 238),
        "primary_value": (255, 246, 242),
        "primary_support": (255, 214, 202),
        "art_border": (255, 170, 130),
        "title_pip": "attack",
        "title_motif": "slashes",
        "art_motif": "slashes",
        "outer_radius_ratio": 0.02,
        "inner_radius_ratio": 0.018,
        "art_radius_ratio": 0.018,
        "top_cut_ratio": 0.11,
        "shoulder_depth_ratio": 0.09,
    },
    "skill": {
        "shape": "skill",
        "title_shape": "skill",
        "art_shape": "skill",
        "outer_fill": (24, 66, 104),
        "outer_shadow": (14, 36, 60),
        "body_fill": (18, 26, 38),
        "title_top": (42, 110, 178),
        "title_bottom": (22, 74, 132),
        "title_text": (242, 248, 255),
        "description_fill": (20, 30, 48),
        "description_border": (58, 94, 136),
        "mid_band_fill": (28, 72, 112),
        "mid_band_border": (110, 214, 246),
        "metadata_fill": (16, 24, 38),
        "cost_fill": (18, 46, 74),
        "cost_ring": (108, 214, 246),
        "cost_text": (242, 248, 255),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (192, 218, 236),
        "accent": (104, 214, 246),
        "accent_soft": (190, 244, 255),
        "accent_glow": (84, 208, 244, 86),
        "type_fill": (40, 102, 164),
        "type_text": (240, 248, 255),
        "primary_value": (246, 251, 255),
        "primary_support": (198, 232, 244),
        "art_border": (152, 226, 244),
        "title_pip": "skill",
        "title_motif": "circuit",
        "art_motif": "circuit",
        "outer_radius_ratio": 0.05,
        "inner_radius_ratio": 0.042,
        "art_radius_ratio": 0.04,
        "top_cut_ratio": 0.0,
        "shoulder_depth_ratio": 0.0,
    },
    "power": {
        "shape": "power",
        "title_shape": "skill",
        "art_shape": "skill",
        "outer_fill": (94, 70, 22),
        "outer_shadow": (54, 40, 10),
        "body_fill": (32, 26, 18),
        "title_top": (170, 138, 54),
        "title_bottom": (114, 92, 28),
        "title_text": (255, 246, 228),
        "description_fill": (34, 28, 22),
        "description_border": (120, 100, 54),
        "mid_band_fill": (110, 94, 34),
        "mid_band_border": (248, 202, 92),
        "metadata_fill": (24, 20, 16),
        "cost_fill": (72, 58, 20),
        "cost_ring": (244, 192, 82),
        "cost_text": (255, 246, 228),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (224, 214, 192),
        "accent": (244, 192, 82),
        "accent_soft": (255, 226, 152),
        "accent_glow": (244, 192, 82, 82),
        "type_fill": (148, 118, 42),
        "type_text": (255, 248, 234),
        "primary_value": (255, 250, 236),
        "primary_support": (244, 226, 182),
        "art_border": (244, 214, 152),
        "title_pip": "power",
        "title_motif": "sigil",
        "art_motif": "circuit",
        "outer_radius_ratio": 0.05,
        "inner_radius_ratio": 0.042,
        "art_radius_ratio": 0.04,
        "top_cut_ratio": 0.0,
        "shoulder_depth_ratio": 0.0,
    },
    "curse": {
        "shape": "attack",
        "title_shape": "attack",
        "art_shape": "attack",
        "outer_fill": (70, 34, 88),
        "outer_shadow": (40, 18, 54),
        "body_fill": (28, 20, 34),
        "title_top": (116, 64, 154),
        "title_bottom": (68, 34, 96),
        "title_text": (248, 240, 255),
        "description_fill": (30, 22, 38),
        "description_border": (90, 58, 122),
        "mid_band_fill": (82, 44, 110),
        "mid_band_border": (196, 140, 246),
        "metadata_fill": (24, 18, 28),
        "cost_fill": (46, 24, 60),
        "cost_ring": (184, 124, 238),
        "cost_text": (246, 236, 255),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (220, 204, 234),
        "accent": (192, 132, 244),
        "accent_soft": (226, 188, 255),
        "accent_glow": (188, 128, 240, 82),
        "type_fill": (104, 62, 138),
        "type_text": (250, 240, 255),
        "primary_value": (248, 244, 255),
        "primary_support": (224, 202, 246),
        "art_border": (214, 174, 255),
        "title_pip": "curse",
        "title_motif": "sigil",
        "art_motif": "slashes",
        "outer_radius_ratio": 0.02,
        "inner_radius_ratio": 0.018,
        "art_radius_ratio": 0.018,
        "top_cut_ratio": 0.11,
        "shoulder_depth_ratio": 0.09,
    },
    "status": {
        "shape": "skill",
        "title_shape": "skill",
        "art_shape": "skill",
        "outer_fill": (76, 84, 102),
        "outer_shadow": (42, 48, 60),
        "body_fill": (26, 30, 40),
        "title_top": (118, 130, 148),
        "title_bottom": (78, 88, 108),
        "title_text": (244, 248, 255),
        "description_fill": (28, 32, 44),
        "description_border": (92, 106, 128),
        "mid_band_fill": (70, 78, 94),
        "mid_band_border": (170, 182, 204),
        "metadata_fill": (22, 26, 34),
        "cost_fill": (42, 50, 62),
        "cost_ring": (188, 202, 224),
        "cost_text": (248, 250, 255),
        "text": DEFAULT_TEXT_COLOR,
        "muted": (206, 216, 232),
        "accent": (188, 202, 224),
        "accent_soft": (224, 232, 244),
        "accent_glow": (184, 198, 220, 72),
        "type_fill": (96, 108, 124),
        "type_text": (248, 250, 255),
        "primary_value": (248, 250, 255),
        "primary_support": (214, 224, 236),
        "art_border": (214, 224, 238),
        "title_pip": "status",
        "title_motif": "grid",
        "art_motif": "circuit",
        "outer_radius_ratio": 0.05,
        "inner_radius_ratio": 0.042,
        "art_radius_ratio": 0.04,
        "top_cut_ratio": 0.0,
        "shoulder_depth_ratio": 0.0,
    },
}

CARD_EFFECT_COLORS = {
    "damage": (248, 112, 112),
    "block": (106, 216, 252),
    "heal": (120, 228, 152),
    "draw": (236, 188, 82),
    "energy": (248, 214, 114),
}


def card_type_key(card: dict[str, Any]) -> str:
    return str(card.get("type", "status")).strip().lower()


def resolve_card_theme(card: dict[str, Any]) -> dict[str, Any]:
    raw_theme = card.get("theme") if isinstance(card.get("theme"), dict) else {}
    faction = raw_theme.get("faction", "starter")
    palette_key = raw_theme.get("palette")
    if not isinstance(palette_key, str) or not palette_key:
        palette_key = "netrunner" if faction == "netrunner" else "starter_neutral"
    art_style = raw_theme.get("art_style", "circuit_burst")
    type_key = card_type_key(card)
    type_theme = CARD_TYPE_THEMES.get(type_key, CARD_TYPE_THEMES["status"])
    art_palette = CARD_ART_PALETTES.get(palette_key, CARD_ART_PALETTES["starter_neutral"])
    return {
        "type_key": type_key,
        "faction": faction,
        "palette_key": palette_key,
        "art_style": art_style,
        "type_theme": type_theme,
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
