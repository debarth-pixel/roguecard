from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


class TitleUI:
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

    def handle_event(self, event: Any, title_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(title_state)
        active_buttons = layout["active_buttons"]
        if active_buttons:
            self._keyboard_index = max(0, min(self._keyboard_index, len(active_buttons) - 1))

        if event.type == pygame.MOUSEMOTION:
            self._hovered_action = self._action_at_position(layout, event.pos)
            hovered_index = next(
                (index for index, button in enumerate(active_buttons) if button["action"] == self._hovered_action),
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
            return self._action_event(action_id, layout)

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE and layout["confirm_overwrite"]:
            return {"type": "title_cancel_new_run"}

        if not layout["confirm_overwrite"]:
            if event.key == pygame.K_n:
                return {"type": "title_new_run"}
            if event.key == pygame.K_c:
                if layout["continue_enabled"]:
                    return {"type": "title_continue"}
                return {"type": "notice", "message": "No resumable run is available.", "level": "error"}
            if event.key == pygame.K_s:
                return {"type": "toggle_settings"}
            if event.key == pygame.K_q:
                return {"type": "title_quit"}

        if event.key in {pygame.K_UP, pygame.K_LEFT} and active_buttons:
            self._keyboard_index = (self._keyboard_index - 1) % len(active_buttons)
            return None
        if event.key in {pygame.K_DOWN, pygame.K_RIGHT} and active_buttons:
            self._keyboard_index = (self._keyboard_index + 1) % len(active_buttons)
            return None

        if event.key in {pygame.K_RETURN, pygame.K_SPACE} and active_buttons:
            return self._action_event(active_buttons[self._keyboard_index]["action"], layout)

        return None

    def build_layout(self, title_state: dict[str, Any]) -> dict[str, Any]:
        title = title_state["title"]
        confirm_overwrite = bool(title.get("confirm_overwrite", False))
        continue_summary = title.get("continue_summary")
        buttons = [
            {
                "action": "title_new_run",
                "label": "New Run",
                "rect": (120, 270, 260, 54),
                "enabled": True,
            },
            {
                "action": "title_continue",
                "label": "Continue",
                "rect": (120, 336, 260, 54),
                "enabled": bool(title.get("continue_enabled", False)),
                "disabled_reason": "No resumable run is available.",
            },
            {
                "action": "toggle_settings",
                "label": "Settings",
                "rect": (120, 402, 260, 54),
                "enabled": True,
            },
            {
                "action": "title_quit",
                "label": "Quit",
                "rect": (120, 468, 260, 54),
                "enabled": True,
            },
        ]

        confirm_buttons = [
            {
                "action": "title_confirm_new_run",
                "label": "Overwrite Run",
                "rect": (448, 472, 188, 44),
                "enabled": True,
            },
            {
                "action": "title_cancel_new_run",
                "label": "Cancel",
                "rect": (654, 472, 154, 44),
                "enabled": True,
            },
        ]

        return {
            "confirm_overwrite": confirm_overwrite,
            "buttons": buttons,
            "confirm_buttons": confirm_buttons,
            "active_buttons": confirm_buttons if confirm_overwrite else buttons,
            "continue_enabled": bool(title.get("continue_enabled", False)),
            "continue_summary": continue_summary,
            "status_message": title_state.get("status_message", ""),
        }

    def render(self, surface: Any, title_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(title_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = title_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(title_state)
        if layout["active_buttons"]:
            self._keyboard_index = max(0, min(self._keyboard_index, len(layout["active_buttons"]) - 1))
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        left_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 470))
        right_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (760, 470))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=214)
        surface.blit(left_panel, (84, 180))
        surface.blit(right_panel, (456, 180))

        self._draw_text(surface, "ROGUE CARD", (120, 84), self._title_font)
        self._draw_text(surface, "Neon route-builder deck duels.", (120, 130), self._small_font, width=420)
        self._draw_text(surface, layout["status_message"], (458, 206), self._small_font, width=720)

        for index, button in enumerate(layout["buttons"]):
            selected = (not layout["confirm_overwrite"]) and index == self._keyboard_index
            self._draw_button(
                surface,
                button["rect"],
                button["label"],
                hovered=self._hovered_action == button["action"],
                pressed=self._pressed_action == button["action"],
                enabled=button["enabled"],
                selected=selected,
            )

        self._draw_text(surface, "Resume", (484, 246), self._small_font)
        if layout["continue_summary"] is None:
            self._draw_text(
                surface,
                "No resumable run found. Start a new run to draft a modifier and enter the city.",
                (484, 284),
                self._small_font,
                width=700,
            )
        else:
            summary = layout["continue_summary"]
            summary_lines = [
                f"State: {summary['current_state'].replace('_', ' ').title()}",
                f"Seed: {summary['run_seed']}",
                f"Status: {summary['status_message']}",
            ]
            modifier_label = summary.get("modifier_label")
            if modifier_label:
                summary_lines.append(f"Active modifier: {modifier_label}")
            for index, line in enumerate(summary_lines):
                self._draw_text(surface, line, (484, 284 + (index * 34)), self._small_font, width=700)

        help_lines = [
            "N: new run",
            "C: continue",
            "S: settings",
            "Q: quit",
        ]
        for index, line in enumerate(help_lines):
            self._draw_text(surface, line, (484, 500 + (index * 26)), self._tiny_font, width=280)

        if layout["confirm_overwrite"]:
            scrim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            scrim.fill((8, 12, 18, 176))
            surface.blit(scrim, (0, 0))
            confirm_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (420, 200))
            surface.blit(confirm_panel, (430, 260))
            self._draw_text(surface, "Overwrite saved run?", (456, 286), self._font)
            self._draw_text(
                surface,
                "Starting a new run will replace the current resumable save after you pick a modifier.",
                (456, 328),
                self._small_font,
                width=366,
            )
            for index, button in enumerate(layout["confirm_buttons"]):
                selected = index == self._keyboard_index
                self._draw_button(
                    surface,
                    button["rect"],
                    button["label"],
                    hovered=self._hovered_action == button["action"],
                    pressed=self._pressed_action == button["action"],
                    enabled=button["enabled"],
                    selected=selected,
                )

    def _action_event(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "title_continue" and not layout["continue_enabled"]:
            return {"type": "notice", "message": "No resumable run is available.", "level": "error"}
        return {"type": action_id}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for button in layout["active_buttons"]:
            if point_in_rect(position, button["rect"]):
                return button["action"]
        return None

    def _draw_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        hovered: bool,
        pressed: bool,
        enabled: bool,
        selected: bool,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        fill = (40, 78, 138) if enabled else (26, 34, 48)
        border = (255, 214, 110) if selected else (230, 240, 255) if enabled else (110, 118, 136)
        if hovered and enabled:
            fill = (56, 100, 168)
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
        self._title_font = pygame.font.SysFont("consolas", max(34, int(46 * scale)))
        self._font = pygame.font.SysFont("consolas", max(22, int(28 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(16, int(20 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load title UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((80, 120, 200, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_title_ui() -> dict[str, Any]:
    ui = TitleUI()
    layout = ui.build_layout(
        {
            "current_state": "title",
            "status_message": "Choose how to enter the city.",
            "title": {
                "continue_enabled": True,
                "continue_summary": {
                    "current_state": "shop",
                    "run_seed": 7421,
                    "status_message": "Shop open. Spend, reroll, or leave.",
                    "modifier_label": "Market Key",
                },
                "confirm_overwrite": False,
            },
            "presentation": {"ui_scale": 1.0},
        }
    )
    return {
        "button_count": len(layout["buttons"]),
        "continue_enabled": layout["continue_enabled"],
    }
