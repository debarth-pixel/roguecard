from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, PROJECT_ROOT, SCREEN_SIZE
from ui.render_utils import clamp_scale, draw_wrapped_text, point_in_rect

ARTS_ROOT = PROJECT_ROOT / "arts"
CHARACTER_CUTOUTS_ROOT = PROJECT_ROOT / "assets" / "ui" / "character_select"
TILE_RADIUS = 18
CARD_TYPE_COLORS: dict[str, tuple[int, int, int]] = {
    "attack": (196, 92, 74),
    "skill": (86, 164, 198),
    "power": (188, 156, 82),
    "status": (140, 108, 162),
}

CHARACTER_VISUALS: dict[str, dict[str, Any]] = {
    "enforcer": {
        "background_path": ARTS_ROOT / "enforcer_background.png",
        "unselected_path": ARTS_ROOT / "enforcer_unselected.png",
        "selected_path": CHARACTER_CUTOUTS_ROOT / "enforcer_selected_cutout.png",
        "selected_fallback_path": ARTS_ROOT / "enforcer_selected.png",
        "accent_color": (208, 104, 70),
        "effect_type": "embers",
        "effect_anchor_rect": (0.40, 0.66, 0.18, 0.20),
        "character_bounds": (0.05, 0.11, 0.9, 0.72),
        "character_anchor": {
            "unselected": (0.76, 0.98),
            "selected": (0.72, 1.0),
        },
        "character_scale": {
            "unselected": 0.88,
            "selected": 1.0,
        },
    },
    "operator": {
        "background_path": ARTS_ROOT / "controller_background.png",
        "unselected_path": ARTS_ROOT / "controller_unselected.png",
        "selected_path": CHARACTER_CUTOUTS_ROOT / "controller_selected_cutout.png",
        "selected_fallback_path": ARTS_ROOT / "controller_selected.png",
        "accent_color": (82, 146, 222),
        "effect_type": "crackle",
        "effect_anchor_rect": (0.10, 0.08, 0.50, 0.28),
        "character_bounds": (0.05, 0.11, 0.9, 0.72),
        "character_anchor": {
            "unselected": (0.77, 0.98),
            "selected": (0.73, 1.0),
        },
        "character_scale": {
            "unselected": 0.9,
            "selected": 0.98,
        },
    },
    "bio_hacker": {
        "background_path": ARTS_ROOT / "biohacker_background.png",
        "unselected_path": ARTS_ROOT / "biohacker_unselected.png",
        "selected_path": ARTS_ROOT / "biohacker_selected.png",
        "accent_color": (92, 196, 96),
        "effect_type": "drips",
        "effect_anchor_rect": (0.60, 0.04, 0.24, 0.42),
        "character_bounds": (0.05, 0.11, 0.9, 0.72),
        "character_anchor": {
            "unselected": (0.75, 0.98),
            "selected": (0.72, 1.0),
        },
        "character_scale": {
            "unselected": 0.87,
            "selected": 0.98,
        },
    },
}


class CharacterSelectUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None
        self._keyboard_index = 0

    def preload_assets(self) -> None:
        if pygame is None:
            return
        for visual in CHARACTER_VISUALS.values():
            self._load_image(visual["background_path"])
            self._load_image(visual["unselected_path"])
            self._load_image(self._image_path_for_state(visual, selected=True))

    def handle_event(self, event: Any, character_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(character_state)
        panels = layout["panels"]
        if panels:
            self._keyboard_index = max(0, min(self._keyboard_index, len(panels) - 1))

        if event.type == pygame.MOUSEMOTION:
            self._hovered_action = self._action_at_position(layout, event.pos)
            hovered_index = next(
                (index for index, panel in enumerate(panels) if self._hovered_action == f"character:{panel['id']}"),
                None,
            )
            if hovered_index is not None:
                self._keyboard_index = hovered_index
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed_action = self._action_at_position(layout, event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            action_id = self._action_at_position(layout, event.pos)
            pressed_action = self._pressed_action
            self._pressed_action = None
            if action_id is None or action_id != pressed_action:
                return None
            return self._event_for_action(action_id, layout)

        if event.type != pygame.KEYDOWN:
            return None

        if pygame.K_1 <= event.key <= pygame.K_3:
            panel_index = event.key - pygame.K_1
            if panel_index < len(panels):
                return {"type": "select_character", "character_id": panels[panel_index]["id"]}

        if event.key in {pygame.K_LEFT, pygame.K_UP} and panels:
            self._keyboard_index = (self._keyboard_index - 1) % len(panels)
            return None
        if event.key in {pygame.K_RIGHT, pygame.K_DOWN} and panels:
            self._keyboard_index = (self._keyboard_index + 1) % len(panels)
            return None
        if event.key == pygame.K_TAB and panels:
            self._keyboard_index = (self._keyboard_index + 1) % len(panels)
            return {"type": "select_character", "character_id": panels[self._keyboard_index]["id"]}
        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if layout["selected_character_id"] is None and panels:
                return {"type": "select_character", "character_id": panels[self._keyboard_index]["id"]}
            if layout["can_confirm"]:
                return {"type": "confirm_character_selection"}
            return {"type": "notice", "message": "Select a character before confirming.", "level": "error"}

        return None

    def build_layout(
        self,
        character_state: dict[str, Any],
        screen_size: tuple[int, int] = SCREEN_SIZE,
    ) -> dict[str, Any]:
        character_select = character_state["character_select"]
        width, height = screen_size
        outer_margin = max(36, int(width * 0.04))
        gap = max(18, int(width * 0.018))
        tile_width = int((width - (outer_margin * 2) - (gap * 2)) / 3)
        tile_height = height - 150
        tile_y = 70

        panels: list[dict[str, Any]] = []
        for index, character in enumerate(character_select["characters"]):
            panels.append(
                {
                    **character,
                    "shortcut": index + 1,
                    "rect": (outer_margin + (index * (tile_width + gap)), tile_y, tile_width, tile_height),
                }
            )

        return {
            "panels": panels,
            "selected_character_id": character_select.get("selected_character_id"),
            "can_confirm": character_select.get("can_confirm", False),
            "confirm_rect": (width - 210, height - 54, 170, 34),
            "status_message": character_state.get("status_message", ""),
            "screen_size": screen_size,
        }

    def render(self, surface: Any, character_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(character_state.get("presentation", {}).get("ui_scale", 1.0))
        layout = self.build_layout(character_state, surface.get_size())
        self._draw_stage_background(surface)
        self._draw_stage_header(surface, layout["status_message"])

        for index, panel_data in enumerate(layout["panels"]):
            selected = panel_data["id"] == layout["selected_character_id"]
            hovered = self._hovered_action == f"character:{panel_data['id']}"
            pressed = self._pressed_action == f"character:{panel_data['id']}"
            keyboard_selected = index == self._keyboard_index
            self._draw_character_tile(
                surface,
                panel_data,
                selected=selected,
                hovered=hovered,
                pressed=pressed,
                keyboard_selected=keyboard_selected,
            )

        self._draw_button(
            surface,
            layout["confirm_rect"],
            "Confirm",
            hovered=self._hovered_action == "confirm",
            pressed=self._pressed_action == "confirm",
            enabled=layout["can_confirm"],
        )

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "confirm":
            if not layout["can_confirm"]:
                return {"type": "notice", "message": "Select a character before confirming.", "level": "error"}
            return {"type": "confirm_character_selection"}
        if action_id.startswith("character:"):
            return {"type": "select_character", "character_id": action_id.removeprefix("character:")}
        return {"type": "notice", "message": "Unknown character selection action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for panel in layout["panels"]:
            if point_in_rect(position, panel["rect"]):
                return f"character:{panel['id']}"
        if point_in_rect(position, layout["confirm_rect"]):
            return "confirm"
        return None

    def _draw_stage_background(self, surface: Any) -> None:
        width, height = surface.get_size()
        surface.fill((6, 10, 16))

        for x in range(-height, width + height, 72):
            pygame.draw.line(surface, (16, 24, 34), (x, 0), (x + height, height), 1)
        for y in range(0, height, 52):
            pygame.draw.line(surface, (10, 16, 24), (0, y), (width, y), 1)

        left_shadow = pygame.Surface((int(width * 0.25), height), pygame.SRCALPHA)
        left_shadow.fill((4, 8, 12, 72))
        surface.blit(left_shadow, (0, 0))

        bottom_fade = pygame.Surface((width, 150), pygame.SRCALPHA)
        for row in range(bottom_fade.get_height()):
            alpha = min(150, int(30 + (row * 0.8)))
            pygame.draw.line(bottom_fade, (4, 8, 12, alpha), (0, row), (width, row))
        surface.blit(bottom_fade, (0, height - bottom_fade.get_height()))

    def _draw_stage_header(self, surface: Any, status_message: str) -> None:
        if not status_message:
            return
        self._draw_text(
            surface,
            status_message,
            (surface.get_width() - 420, 28),
            self._tiny_font,
            width=360,
            color=(132, 140, 154),
        )

    def _draw_character_tile(
        self,
        surface: Any,
        panel_data: dict[str, Any],
        *,
        selected: bool,
        hovered: bool,
        pressed: bool,
        keyboard_selected: bool,
    ) -> None:
        visual = CHARACTER_VISUALS[panel_data["id"]]
        accent = tuple(visual["accent_color"])
        base_rect = pygame.Rect(*panel_data["rect"])
        lift = -8 if selected else -3 if hovered or keyboard_selected else 0
        render_rect = base_rect.move(0, lift)

        shadow_surface = pygame.Surface((render_rect.width + 24, render_rect.height + 30), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, (0, 0, 0, 52 if selected else 34), shadow_surface.get_rect(), border_radius=TILE_RADIUS + 6)
        surface.blit(shadow_surface, (render_rect.x - 12, render_rect.y + 8))

        tile_surface = pygame.Surface(render_rect.size, pygame.SRCALPHA)
        self._blit_cover_image(tile_surface, visual["background_path"])
        self._draw_scene_overlays(tile_surface, accent, selected=selected, hovered=hovered or keyboard_selected)
        if selected:
            self._draw_selected_ambient(tile_surface, visual)
        self._draw_character_art(tile_surface, visual, selected=selected)

        self._draw_text(
            tile_surface,
            panel_data["name"],
            (20, 18),
            self._font,
            width=render_rect.width - 40,
            color=(236, 242, 248),
        )

        preview_rect = pygame.Rect(14, render_rect.height - 64, render_rect.width - 28, 50)
        self._draw_preview_strip(
            tile_surface,
            preview_rect,
            panel_data.get("preview_cards", [])[:3],
            accent=accent,
            selected=selected,
        )

        self._draw_tile_finish(tile_surface, accent, selected=selected, hovered=hovered or keyboard_selected)
        tile_surface = self._apply_round_mask(tile_surface, TILE_RADIUS)
        surface.blit(tile_surface, render_rect.topleft)

        border_color = (255, 214, 110) if pressed else accent if selected else (104, 112, 126) if hovered or keyboard_selected else (74, 82, 94)
        border_width = 2 if selected or hovered or keyboard_selected or pressed else 1
        pygame.draw.rect(surface, border_color, render_rect, border_width, border_radius=TILE_RADIUS)

    def _draw_scene_overlays(
        self,
        surface: Any,
        accent: tuple[int, int, int],
        *,
        selected: bool,
        hovered: bool,
    ) -> None:
        width, height = surface.get_size()
        top_gradient = pygame.Surface((width, int(height * 0.28)), pygame.SRCALPHA)
        for row in range(top_gradient.get_height()):
            alpha = max(0, 180 - int(row * 1.6))
            pygame.draw.line(top_gradient, (6, 10, 14, alpha), (0, row), (width, row))
        surface.blit(top_gradient, (0, 0))

        bottom_gradient = pygame.Surface((width, int(height * 0.34)), pygame.SRCALPHA)
        for row in range(bottom_gradient.get_height()):
            alpha = min(190, int(28 + (row * 1.45)))
            pygame.draw.line(bottom_gradient, (5, 8, 12, alpha), (0, row), (width, row))
        surface.blit(bottom_gradient, (0, height - bottom_gradient.get_height()))

        neutral_dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        neutral_dim.fill((8, 12, 18, 76 if selected else 128))
        surface.blit(neutral_dim, (0, 0))

        if hovered and not selected:
            hover_lift = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            hover_lift.fill((255, 255, 255, 10))
            surface.blit(hover_lift, (0, 0))

        if selected:
            backlight = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            backlight_rect = pygame.Rect(int(width * 0.18), int(height * 0.22), int(width * 0.64), int(height * 0.46))
            pygame.draw.ellipse(backlight, (*accent, 22), backlight_rect)
            surface.blit(backlight, (0, 0))

            lower_lift = pygame.Surface((width, int(height * 0.24)), pygame.SRCALPHA)
            for row in range(lower_lift.get_height()):
                alpha = max(0, 18 - int(abs((row / max(1, lower_lift.get_height())) - 0.5) * 36))
                pygame.draw.line(lower_lift, (*accent, alpha), (0, row), (width, row))
            surface.blit(lower_lift, (0, height - lower_lift.get_height()))

    def _draw_character_art(
        self,
        surface: Any,
        visual: dict[str, Any],
        *,
        selected: bool,
    ) -> None:
        image = self._load_image(self._image_path_for_state(visual, selected=selected))
        bounds = self._resolve_relative_rect(surface.get_rect(), visual["character_bounds"])
        state_key = "selected" if selected else "unselected"
        anchor = visual["character_anchor"][state_key]
        scale = visual["character_scale"][state_key]
        alpha = 255 if selected else 212

        backlight = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        halo_center = (
            bounds.x + int(bounds.width * anchor[0]),
            bounds.y + int(bounds.height * min(0.86, anchor[1])),
        )
        halo_rect = pygame.Rect(0, 0, int(bounds.width * 0.5), int(bounds.height * 0.34))
        halo_rect.center = halo_center
        pygame.draw.ellipse(backlight, (*visual["accent_color"], 28 if selected else 12), halo_rect)
        surface.blit(backlight, (0, 0))

        self._blit_contain_anchored_image(
            surface,
            image,
            bounds,
            anchor=anchor,
            scale=scale,
            alpha=alpha,
        )

    def _draw_selected_ambient(self, surface: Any, visual: dict[str, Any]) -> None:
        if pygame is None:
            return
        tick = pygame.time.get_ticks()
        effect_type = visual["effect_type"]
        region = self._resolve_relative_rect(surface.get_rect(), visual["effect_anchor_rect"])
        if effect_type == "embers":
            self._draw_ember_effect(surface, region, tick)
        elif effect_type == "drips":
            self._draw_bio_drip_effect(surface, region, tick)
        elif effect_type == "crackle":
            self._draw_operator_crackle(surface, region, tick)

    def _draw_ember_effect(self, surface: Any, region: pygame.Rect, tick_ms: int) -> None:
        effect_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        time_value = tick_ms / 1000.0
        ember_colors = ((252, 166, 96), (238, 118, 70), (214, 156, 120))
        for index in range(14):
            phase = (time_value * 0.16 + index * 0.083) % 1.0
            x_ratio = 0.14 + ((index * 0.11 + 0.12 * math.sin(time_value * 0.9 + (index * 0.8))) % 0.72)
            x = region.x + int(region.width * x_ratio)
            y = region.bottom - int(region.height * phase) + int(math.sin((time_value * 2.2) + index) * 4)
            radius = 2 if index % 3 else 3
            alpha = 48 + int((1.0 - phase) * 54)
            color = ember_colors[index % len(ember_colors)]
            pygame.draw.circle(effect_surface, (*color, alpha), (x, y), radius)
            if index % 4 == 0:
                pygame.draw.line(
                    effect_surface,
                    (*color, max(18, alpha - 22)),
                    (x, y + 2),
                    (x, y + 6),
                    1,
                )
        surface.blit(effect_surface, (0, 0))

    def _draw_bio_drip_effect(self, surface: Any, region: pygame.Rect, tick_ms: int) -> None:
        effect_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        time_value = tick_ms / 1000.0
        for index in range(7):
            base_x = region.x + int(region.width * ((0.10 + (index * 0.13)) % 0.94))
            drift = (time_value * 0.05 + index * 0.14) % 1.0
            top_y = region.y + int(region.height * ((index * 0.09) % 0.48))
            drop_length = 14 + (index % 3) * 5
            wobble = int(math.sin(time_value * 1.1 + index * 0.8) * 2.0)
            alpha = 42 + int(28 * abs(math.sin(time_value * 0.55 + index)))
            glow_alpha = min(94, alpha + 16)
            for step in range(drop_length // 3):
                block_x = base_x + wobble + (1 if step % 2 else 0)
                block_y = top_y + int(drift * 24) + (step * 3)
                pygame.draw.rect(effect_surface, (92, 218, 106, alpha), (block_x, block_y, 3, 3))
            if drift > 0.64:
                pygame.draw.rect(
                    effect_surface,
                    (116, 246, 126, glow_alpha),
                    (base_x + wobble - 1, top_y + int(drift * 24) + drop_length, 5, 4),
                )
            pygame.draw.rect(
                effect_surface,
                (74, 188, 94, max(18, alpha - 18)),
                (base_x + wobble - 1, top_y + int(drift * 18), 5, max(4, drop_length - 4)),
                1,
            )
        surface.blit(effect_surface, (0, 0))

    def _draw_operator_crackle(self, surface: Any, region: pygame.Rect, tick_ms: int) -> None:
        effect_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        time_value = tick_ms / 1000.0
        for index in range(5):
            flicker = math.sin((time_value * 2.6) + (index * 1.9))
            if flicker < 0.54:
                continue

            start_x = region.x + int(region.width * (0.10 + index * 0.16))
            start_y = region.y + int(region.height * (0.20 + (index % 3) * 0.18))
            alpha = 42 + int((flicker - 0.54) * 76)
            points = [(start_x, start_y)]
            for step in range(1, 6):
                points.append(
                    (
                        start_x + (step * 14),
                        start_y + int(math.sin((time_value * 5.0) + index + step) * 5),
                    )
                )
            pygame.draw.lines(effect_surface, (92, 166, 248, min(58, alpha)), False, points, 3)
            pygame.draw.lines(effect_surface, (148, 214, 255, min(110, alpha + 28)), False, points, 1)

            if index in {0, 3} and flicker > 0.82:
                scan_x = region.x + int(region.width * (0.68 + (index * 0.06)))
                pygame.draw.line(
                    effect_surface,
                    (124, 198, 255, 34),
                    (scan_x, region.y),
                    (scan_x, region.bottom),
                    1,
                )
            node_center = (start_x + 10, start_y + 2)
            pygame.draw.circle(effect_surface, (138, 212, 255, min(88, alpha + 12)), node_center, 2)
        surface.blit(effect_surface, (0, 0))

    def _draw_preview_strip(
        self,
        surface: Any,
        rect: pygame.Rect,
        preview_cards: list[dict[str, Any]],
        *,
        accent: tuple[int, int, int],
        selected: bool,
    ) -> None:
        strip_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(strip_surface, (6, 10, 16, 146), strip_surface.get_rect(), border_radius=12)
        pygame.draw.rect(strip_surface, (*accent, 54 if selected else 34), strip_surface.get_rect(), 1, border_radius=12)

        chip_gap = 8
        chip_width = int((rect.width - (chip_gap * 2)) / 3)
        for index, card in enumerate(preview_cards):
            chip_rect = pygame.Rect(index * (chip_width + chip_gap), 0, chip_width, rect.height)
            self._draw_card_chip(strip_surface, chip_rect, card, accent)

        strip_surface = self._apply_round_mask(strip_surface, 12)
        surface.blit(strip_surface, rect.topleft)

    def _draw_card_chip(
        self,
        surface: Any,
        rect: pygame.Rect,
        card: dict[str, Any],
        accent: tuple[int, int, int],
    ) -> None:
        card_type = str(card.get("type", "skill")).lower()
        chip_color = CARD_TYPE_COLORS.get(card_type, accent)
        chip_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(chip_surface, (10, 16, 24, 176), chip_surface.get_rect(), border_radius=10)
        pygame.draw.rect(chip_surface, (*chip_color, 136), chip_surface.get_rect(), 1, border_radius=10)

        cost = card.get("cost")
        cost_box = pygame.Rect(6, 6, 18, 18)
        pygame.draw.rect(chip_surface, (*chip_color, 214), cost_box, border_radius=4)
        cost_text = self._tiny_font.render(str(cost if isinstance(cost, int) else "-"), True, (12, 16, 22))
        chip_surface.blit(cost_text, cost_text.get_rect(center=cost_box.center))

        type_label = self._tiny_font.render(card_type[:1].upper(), True, chip_color)
        chip_surface.blit(type_label, (rect.width - 16, 8))

        self._draw_text(
            chip_surface,
            str(card.get("name", "Card")),
            (8, 26),
            self._tiny_font,
            width=rect.width - 16,
            color=(228, 234, 242),
        )
        surface.blit(chip_surface, rect.topleft)

    def _draw_tile_finish(
        self,
        surface: Any,
        accent: tuple[int, int, int],
        *,
        selected: bool,
        hovered: bool,
    ) -> None:
        width, height = surface.get_size()
        if selected:
            inner_glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for inset, alpha in ((8, 22), (18, 12)):
                pygame.draw.rect(
                    inner_glow,
                    (*accent, alpha),
                    pygame.Rect(inset, inset, width - (inset * 2), height - (inset * 2)),
                    1,
                    border_radius=max(8, TILE_RADIUS - (inset // 3)),
                )
            pygame.draw.rect(inner_glow, (*accent, 28), pygame.Rect(2, 2, width - 4, height - 4), 2, border_radius=TILE_RADIUS)
            surface.blit(inner_glow, (0, 0))
        elif hovered:
            hover_highlight = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.rect(hover_highlight, (236, 242, 248, 12), pygame.Rect(2, 2, width - 4, height - 4), 1, border_radius=TILE_RADIUS)
            surface.blit(hover_highlight, (0, 0))

    def _draw_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        *,
        hovered: bool,
        pressed: bool,
        enabled: bool,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        button_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        fill = (10, 16, 22, 214 if enabled else 118)
        border = (118, 128, 142) if enabled else (72, 80, 94)
        if hovered and enabled:
            fill = (14, 20, 28, 232)
        if pressed and enabled:
            border = (255, 214, 110)
        pygame.draw.rect(button_surface, fill, button_surface.get_rect(), border_radius=10)
        pygame.draw.rect(button_surface, (*border, 255), button_surface.get_rect(), 1, border_radius=10)
        label_surface = self._small_font.render(
            label,
            True,
            (236, 242, 248) if enabled else (124, 132, 144),
        )
        button_surface.blit(label_surface, label_surface.get_rect(center=button_surface.get_rect().center))
        surface.blit(button_surface, rect.topleft)

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
        color: tuple[int, int, int] = (236, 242, 248),
    ) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._title_font is not None:
            return

        self._font_scale = scale
        self._title_font = pygame.font.SysFont("consolas", max(26, int(30 * scale)))
        self._font = pygame.font.SysFont("consolas", max(20, int(24 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(14, int(17 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(11, int(13 * scale)))

    def _blit_cover_image(self, surface: Any, path: Path) -> None:
        image = self._load_image(path)
        image_rect = image.get_rect()
        destination = surface.get_rect()
        scale = max(destination.width / image_rect.width, destination.height / image_rect.height)
        scaled_size = (
            max(1, int(round(image_rect.width * scale))),
            max(1, int(round(image_rect.height * scale))),
        )
        scaled = pygame.transform.smoothscale(image, scaled_size)
        scaled_rect = scaled.get_rect(center=destination.center)
        surface.blit(scaled, destination.topleft, area=destination.move(-scaled_rect.x, -scaled_rect.y))

    def _blit_contain_anchored_image(
        self,
        surface: Any,
        image: Any,
        bounds: pygame.Rect,
        *,
        anchor: tuple[float, float],
        scale: float,
        alpha: int,
    ) -> None:
        image_rect = image.get_rect()
        base_scale = min(bounds.width / image_rect.width, bounds.height / image_rect.height) * scale
        scaled_size = (
            max(1, int(round(image_rect.width * base_scale))),
            max(1, int(round(image_rect.height * base_scale))),
        )
        scaled = pygame.transform.smoothscale(image, scaled_size)
        if alpha < 255:
            scaled.set_alpha(alpha)
        anchor_point = (
            bounds.x + int(bounds.width * anchor[0]),
            bounds.y + int(bounds.height * anchor[1]),
        )
        blit_rect = scaled.get_rect(midbottom=anchor_point)
        surface.blit(scaled, blit_rect)

    def _resolve_relative_rect(
        self,
        base_rect: pygame.Rect,
        normalized: tuple[float, float, float, float],
    ) -> pygame.Rect:
        return pygame.Rect(
            base_rect.x + int(base_rect.width * normalized[0]),
            base_rect.y + int(base_rect.height * normalized[1]),
            int(base_rect.width * normalized[2]),
            int(base_rect.height * normalized[3]),
        )

    def _apply_round_mask(self, surface: Any, radius: int) -> Any:
        masked = surface.copy()
        mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        masked.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return masked

    def _load_image(self, path: Path) -> Any:
        if pygame is None:
            return None
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        try:
            image = pygame.image.load(path.as_posix()).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((16, 16), pygame.SRCALPHA)
            image.fill((12, 18, 28, 255))
        self._image_cache[cache_key] = image
        return image

    def _image_path_for_state(self, visual: dict[str, Any], *, selected: bool) -> Path:
        if not selected:
            return visual["unselected_path"]
        selected_path = visual["selected_path"]
        if selected_path.exists():
            return selected_path
        return visual.get("selected_fallback_path", selected_path)


def simulate_character_select_ui() -> dict[str, Any]:
    ui = CharacterSelectUI()
    layout = ui.build_layout(
        {
            "current_state": "character_select",
            "status_message": "Choose a runner before drafting a modifier.",
            "character_select": {
                "selected_character_id": "operator",
                "can_confirm": True,
                "characters": [
                    {
                        "id": "enforcer",
                        "name": "The Enforcer",
                        "accent_color": [232, 88, 72],
                        "preview_cards": [
                            {"name": "Bash Protocol", "cost": 1, "type": "attack"},
                            {"name": "Battle Roar", "cost": 1, "type": "skill"},
                            {"name": "War Engine", "cost": 1, "type": "power"},
                        ],
                    },
                    {
                        "id": "operator",
                        "name": "The Operator",
                        "accent_color": [72, 214, 226],
                        "preview_cards": [
                            {"name": "Needle Ping", "cost": 1, "type": "attack"},
                            {"name": "Priority Queue", "cost": 1, "type": "skill"},
                            {"name": "Auto-Tuner", "cost": 1, "type": "power"},
                        ],
                    },
                    {
                        "id": "bio_hacker",
                        "name": "The Bio-Hacker",
                        "accent_color": [110, 220, 126],
                        "preview_cards": [
                            {"name": "Leech Jab", "cost": 1, "type": "attack"},
                            {"name": "Triage Loop", "cost": 1, "type": "skill"},
                            {"name": "Symbiote Mesh", "cost": 1, "type": "power"},
                        ],
                    },
                ],
            },
            "presentation": {"ui_scale": 1.0},
        }
    )
    return {
        "panel_count": len(layout["panels"]),
        "confirm_enabled": layout["can_confirm"],
        "confirm_rect": layout["confirm_rect"],
        "config_ids": sorted(CHARACTER_VISUALS.keys()),
    }
