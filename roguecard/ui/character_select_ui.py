from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.card_renderer import draw_card
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


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
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
        ):
            self._load_image(path)

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

    def build_layout(self, character_state: dict[str, Any]) -> dict[str, Any]:
        character_select = character_state["character_select"]
        panels: list[dict[str, Any]] = []
        for index, character in enumerate(character_select["characters"]):
            panels.append(
                {
                    **character,
                    "shortcut": index + 1,
                    "rect": (52 + (index * 392), 184, 360, 430),
                }
            )
        return {
            "panels": panels,
            "selected_character_id": character_select.get("selected_character_id"),
            "can_confirm": character_select.get("can_confirm", False),
            "confirm_rect": (1032, 630, 196, 46),
            "status_message": character_state.get("status_message", ""),
        }

    def render(self, surface: Any, character_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(character_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = character_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(character_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        top_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (1232, 96))
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 430))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=190)
        surface.blit(top_panel, (24, 74))

        self._draw_text(surface, "Choose Your Character", (44, 96), self._title_font)
        self._draw_text(surface, layout["status_message"], (44, 134), self._small_font, width=860)
        self._draw_text(surface, "Pick a style, then draft a run modifier.", (886, 104), self._tiny_font, width=300)

        for index, panel_data in enumerate(layout["panels"]):
            rect = pygame.Rect(*panel_data["rect"])
            surface.blit(panel, rect.topleft)
            selected = panel_data["id"] == layout["selected_character_id"]
            hovered = self._hovered_action == f"character:{panel_data['id']}"
            pressed = self._pressed_action == f"character:{panel_data['id']}"
            keyboard_selected = index == self._keyboard_index
            accent = tuple(panel_data.get("accent_color", [120, 150, 190]))
            border = accent if selected or keyboard_selected else (220, 230, 255) if high_contrast else (90, 108, 138)
            if hovered:
                border = tuple(min(255, channel + 24) for channel in accent)
            if pressed:
                border = (255, 214, 110)

            pygame.draw.rect(surface, border, rect, 3, border_radius=18)
            pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 14, rect.y + 16, rect.width - 28, 6), border_radius=3)

            badge_rect = pygame.Rect(rect.right - 40, rect.y + 18, 24, 24)
            pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=12)
            pygame.draw.rect(surface, accent, badge_rect, 2, border_radius=12)
            badge = self._tiny_font.render(str(panel_data["shortcut"]), True, accent)
            surface.blit(badge, badge.get_rect(center=badge_rect.center))

            self._draw_text(surface, panel_data["name"], (rect.x + 18, rect.y + 32), self._font, width=270)
            self._draw_text(surface, panel_data["subtitle"], (rect.x + 18, rect.y + 70), self._tiny_font, width=300)
            self._draw_text(surface, panel_data["description"], (rect.x + 18, rect.y + 102), self._small_font, width=318)
            self._draw_text(surface, "Starter Preview", (rect.x + 18, rect.y + 176), self._tiny_font)

            preview_x = rect.x + 18
            for preview_card in panel_data.get("preview_cards", [])[:3]:
                draw_card(
                    surface,
                    (preview_x, rect.y + 206, 100, 152),
                    preview_card,
                    {},
                    variant="full",
                    selected=selected,
                    hovered=hovered,
                    high_contrast=high_contrast,
                )
                preview_x += 108

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
        fill = (40, 78, 138) if enabled else (28, 34, 46)
        border = (230, 240, 255) if enabled else (110, 118, 136)
        if hovered and enabled:
            fill = (52, 94, 158)
        if pressed and enabled:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, border, rect, 2, border_radius=14)
        text_color = (18, 24, 36) if pressed and enabled else (240, 245, 255) if enabled else (152, 162, 184)
        label_surface = self._small_font.render(label, True, text_color)
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
    ) -> None:
        draw_wrapped_text(surface, text, position, font, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._title_font is not None:
            return

        self._font_scale = scale
        self._title_font = pygame.font.SysFont("consolas", max(26, int(34 * scale)))
        self._font = pygame.font.SysFont("consolas", max(20, int(26 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(16, int(19 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        if image is None or image.get_size() == size:
            return image
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        if pygame is None:
            return None
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        try:
            image = pygame.image.load(path.as_posix()).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((8, 8), pygame.SRCALPHA)
            image.fill((22, 28, 38, 255))
        self._image_cache[cache_key] = image
        return image
