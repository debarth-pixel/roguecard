from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, PROJECT_ROOT, SCREEN_SIZE
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.ui_system import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_LINE,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PANEL_ELEVATED,
    RADIUS_LG,
    RADIUS_MD,
    draw_panel,
)

ARTS_ROOT = PROJECT_ROOT / "arts"
TITLE_BACKGROUND_PATH = ARTS_ROOT / "title_background.png"
TITLE_BUTTON_SIZE = (264, 54)
TITLE_BUTTON_GAP = 62
TITLE_BUTTON_ENTRY_OFFSET = 18
TITLE_BUTTON_STAGGER_MS = 70
TITLE_BUTTON_ANIMATION_MS = 300

ACTION_ACCENTS: dict[str, tuple[int, int, int]] = {
    "title_new_run": (255, 193, 88),
    "title_continue": (100, 170, 255),
    "toggle_settings": (82, 224, 214),
    "title_quit": (255, 118, 132),
    "title_confirm_new_run": (255, 193, 88),
    "title_cancel_new_run": (130, 150, 188),
}

STATE_LABELS = {
    "character_select": "Character Select",
    "modifier_draft": "Relic Draft",
    "map": "Map",
    "combat": "Combat",
    "reward": "Reward",
    "shop": "Shop",
    "event": "Event",
}


class TitleUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._title_font = None
        self._title_support_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None
        self._keyboard_index = 0
        self._intro_started_ms: int | None = None
        self._last_surface_size: tuple[int, int] = SCREEN_SIZE

    def preload_assets(self) -> None:
        if pygame is None:
            return
        self._load_image(TITLE_BACKGROUND_PATH)

    def handle_event(
        self,
        event: Any,
        title_state: dict[str, Any],
        screen_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(title_state, self._last_surface_size if screen_size is None else screen_size)
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

    def build_layout(
        self,
        title_state: dict[str, Any],
        screen_size: tuple[int, int] = SCREEN_SIZE,
    ) -> dict[str, Any]:
        title = title_state["title"]
        confirm_overwrite = bool(title.get("confirm_overwrite", False))
        continue_summary = title.get("continue_summary")
        width, height = screen_size

        button_width, button_height = TITLE_BUTTON_SIZE
        menu_x = max(84, int(width * 0.09))
        menu_y = max(252, int(height * 0.42))

        buttons = [
            {
                "action": "title_new_run",
                "label": "New Run",
                "rect": (menu_x, menu_y + (TITLE_BUTTON_GAP * 0), button_width, button_height),
                "enabled": True,
            },
            {
                "action": "title_continue",
                "label": "Continue",
                "rect": (menu_x, menu_y + (TITLE_BUTTON_GAP * 1), button_width, button_height),
                "enabled": bool(title.get("continue_enabled", False)),
                "disabled_reason": "No resumable run is available.",
            },
            {
                "action": "toggle_settings",
                "label": "Settings",
                "rect": (menu_x, menu_y + (TITLE_BUTTON_GAP * 2), button_width, button_height),
                "enabled": True,
            },
            {
                "action": "title_quit",
                "label": "Quit",
                "rect": (menu_x, menu_y + (TITLE_BUTTON_GAP * 3), button_width, button_height),
                "enabled": True,
            },
        ]

        confirm_panel_width = 430
        confirm_panel_height = 204
        confirm_panel_rect = (
            (width - confirm_panel_width) // 2,
            (height - confirm_panel_height) // 2,
            confirm_panel_width,
            confirm_panel_height,
        )

        confirm_buttons = [
            {
                "action": "title_confirm_new_run",
                "label": "Overwrite Run",
                "rect": (confirm_panel_rect[0] + 26, confirm_panel_rect[1] + confirm_panel_rect[3] - 62, 210, 42),
                "enabled": True,
            },
            {
                "action": "title_cancel_new_run",
                "label": "Cancel",
                "rect": (
                    confirm_panel_rect[0] + confirm_panel_rect[2] - 170,
                    confirm_panel_rect[1] + confirm_panel_rect[3] - 62,
                    144,
                    42,
                ),
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
            "screen_size": screen_size,
            "title_anchor": (menu_x, max(70, int(height * 0.1))),
            "confirm_panel_rect": confirm_panel_rect,
        }

    def render(self, surface: Any, title_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._last_surface_size = surface.get_size()
        self._ensure_fonts(title_state.get("presentation", {}).get("ui_scale", 1.0))
        layout = self.build_layout(title_state, self._last_surface_size)
        if layout["active_buttons"]:
            self._keyboard_index = max(0, min(self._keyboard_index, len(layout["active_buttons"]) - 1))
        if self._intro_started_ms is None:
            self._intro_started_ms = pygame.time.get_ticks()

        self._draw_cover_image(surface, TITLE_BACKGROUND_PATH, surface.get_rect())
        self._draw_scene_overlays(surface)
        self._draw_title_lockup(surface, layout["title_anchor"])

        for index, button in enumerate(layout["buttons"]):
            selected = (not layout["confirm_overwrite"]) and index == self._keyboard_index
            animated_rect, alpha = self._animated_button_rect(button["rect"], index, layout["confirm_overwrite"])
            self._draw_button(
                surface,
                animated_rect,
                button["label"],
                button["action"],
                hovered=self._hovered_action == button["action"] and button["enabled"],
                pressed=self._pressed_action == button["action"],
                enabled=button["enabled"],
                selected=selected,
                alpha=alpha,
            )

        if (
            not layout["confirm_overwrite"]
            and layout["continue_enabled"]
            and layout["continue_summary"] is not None
            and self._hovered_action == "title_continue"
        ):
            continue_button = next(button for button in layout["buttons"] if button["action"] == "title_continue")
            self._draw_continue_preview(surface, continue_button["rect"], layout["continue_summary"])

        if layout["confirm_overwrite"]:
            self._draw_confirm_dialog(surface, layout)

    def _action_event(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "title_continue" and not layout["continue_enabled"]:
            return {"type": "notice", "message": "No resumable run is available.", "level": "error"}
        return {"type": action_id}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for button in layout["active_buttons"]:
            if point_in_rect(position, button["rect"]):
                return button["action"]
        return None

    def _draw_scene_overlays(self, surface: Any) -> None:
        width, height = surface.get_size()
        draw_screen_scrim(surface, alpha=22, color=(4, 8, 14))

        left_scrim = pygame.Surface((max(360, int(width * 0.38)), height), pygame.SRCALPHA)
        left_scrim.fill((6, 10, 18, 152))
        surface.blit(left_scrim, (0, 0))

        top_fade = pygame.Surface((width, 100), pygame.SRCALPHA)
        top_fade.fill((5, 9, 16, 64))
        surface.blit(top_fade, (0, 0))

        floor_fade = pygame.Surface((width, max(180, int(height * 0.30))), pygame.SRCALPHA)
        floor_fade.fill((4, 8, 14, 138))
        surface.blit(floor_fade, (0, height - floor_fade.get_height()))

        rail_rect = pygame.Rect(max(42, int(width * 0.06)), max(58, int(height * 0.09)), max(252, int(width * 0.23)), height - 176)
        rail_surface = pygame.Surface(rail_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(rail_surface, (10, 16, 26, 74), rail_surface.get_rect(), border_radius=28)
        pygame.draw.rect(rail_surface, (86, 104, 134, 60), rail_surface.get_rect(), 1, border_radius=28)
        surface.blit(rail_surface, rail_rect.topleft)

        for offset in range(0, height, 54):
            pygame.draw.line(surface, (34, 58, 76, 10), (0, offset), (width, offset), 1)

    def _draw_title_lockup(self, surface: Any, anchor: tuple[int, int]) -> None:
        x, y = anchor
        tag_surface = pygame.Surface((236, 28), pygame.SRCALPHA)
        pygame.draw.rect(tag_surface, (10, 18, 30, 174), tag_surface.get_rect(), border_radius=14)
        pygame.draw.rect(tag_surface, (86, 104, 134, 140), tag_surface.get_rect(), 1, border_radius=14)
        surface.blit(tag_surface, (x - 2, y - 38))
        tag_text = self._tiny_font.render("TACTICAL DECKBUILDING RUN", True, COLOR_MUTED)
        surface.blit(tag_text, (x + 12, y - 31))
        self._blit_glow_text(surface, "ROGUE", self._title_font, (90, 218, 198), (x, y), glow_alpha=86, shadow=(8, 10, 16))
        self._blit_glow_text(
            surface,
            "CARD",
            self._title_font,
            (244, 247, 255),
            (x + 6, y + self._title_font.get_height() - 10),
            glow_alpha=56,
            shadow=(8, 10, 16),
        )
        pygame.draw.line(
            surface,
            (100, 170, 255, 90),
            (x + 4, y + (self._title_font.get_height() * 2) - 12),
            (x + 230, y + (self._title_font.get_height() * 2) - 12),
            2,
        )

    def _blit_glow_text(
        self,
        surface: Any,
        text: str,
        font: Any,
        color: tuple[int, int, int],
        position: tuple[int, int],
        *,
        glow_alpha: int,
        shadow: tuple[int, int, int],
    ) -> None:
        if pygame is None:
            return
        shadow_surface = font.render(text, True, shadow)
        shadow_surface.set_alpha(170)
        glow_surface = font.render(text, True, color)
        glow_surface.set_alpha(glow_alpha)
        text_surface = font.render(text, True, color)
        x, y = position
        surface.blit(glow_surface, (x - 4, y - 1))
        surface.blit(glow_surface, (x + 3, y))
        surface.blit(shadow_surface, (x + 4, y + 4))
        surface.blit(text_surface, position)

    def _animated_button_rect(
        self,
        rect_tuple: tuple[int, int, int, int],
        index: int,
        confirm_overwrite: bool,
    ) -> tuple[pygame.Rect, int]:
        rect = pygame.Rect(*rect_tuple)
        if pygame is None or confirm_overwrite or self._intro_started_ms is None:
            return rect, 255

        elapsed = pygame.time.get_ticks() - self._intro_started_ms - (index * TITLE_BUTTON_STAGGER_MS)
        if elapsed <= 0:
            return rect.move(0, -TITLE_BUTTON_ENTRY_OFFSET), 0

        progress = min(1.0, elapsed / TITLE_BUTTON_ANIMATION_MS)
        eased = 1.0 - pow(1.0 - progress, 3)
        offset = int(round((1.0 - eased) * TITLE_BUTTON_ENTRY_OFFSET))
        return rect.move(0, -offset), int(255 * eased)

    def _draw_button(
        self,
        surface: Any,
        rect_value: tuple[int, int, int, int] | pygame.Rect,
        label: str,
        action_id: str,
        *,
        hovered: bool,
        pressed: bool,
        enabled: bool,
        selected: bool,
        alpha: int = 255,
    ) -> None:
        rect = pygame.Rect(rect_value)
        accent = ACTION_ACCENTS.get(action_id, (100, 170, 255))
        fill = (10, 18, 32, 172 if enabled else 112)
        border = accent if hovered or selected else COLOR_LINE
        if not enabled:
            border = (70, 78, 96)
        if pressed and enabled:
            fill = (34, 46, 66, 224)
            border = COLOR_GOLD

        button_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(button_surface, fill, button_surface.get_rect(), border_radius=18)
        pygame.draw.rect(button_surface, (*border, 255), button_surface.get_rect(), 2 if hovered or selected or pressed else 1, border_radius=18)
        pygame.draw.rect(button_surface, (*accent, 210 if enabled else 90), pygame.Rect(12, (rect.height // 2) - 8, 3, 16), border_radius=2)

        if hovered and enabled:
            highlight = pygame.Surface(rect.size, pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 8))
            button_surface.blit(highlight, (0, 0))

        text_color = (236, 244, 255) if enabled else (126, 134, 154)
        label_surface = self._small_font.render(label, True, text_color)
        button_surface.blit(label_surface, label_surface.get_rect(midleft=(28, button_surface.get_rect().centery)))
        if alpha < 255:
            button_surface.set_alpha(alpha)
        surface.blit(button_surface, rect.topleft)

    def _draw_continue_preview(
        self,
        surface: Any,
        continue_rect_tuple: tuple[int, int, int, int],
        summary: dict[str, Any],
    ) -> None:
        continue_rect = pygame.Rect(*continue_rect_tuple)
        bubble_width = 292
        bubble_height = 122
        surface_rect = surface.get_rect()

        bubble_x = min(surface_rect.right - bubble_width - 28, continue_rect.right + 22)
        bubble_y = max(46, continue_rect.centery - (bubble_height // 2))
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)

        bubble_surface = pygame.Surface(bubble_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bubble_surface, (8, 14, 24, 228), bubble_surface.get_rect(), border_radius=18)
        pygame.draw.rect(bubble_surface, (96, 170, 255, 180), bubble_surface.get_rect(), 2, border_radius=18)
        pygame.draw.rect(bubble_surface, (96, 170, 255, 62), pygame.Rect(0, 0, bubble_rect.width, 10), border_radius=10)
        surface.blit(bubble_surface, bubble_rect.topleft)

        pointer_points = [
            (bubble_rect.left, continue_rect.centery - 9),
            (bubble_rect.left - 12, continue_rect.centery),
            (bubble_rect.left, continue_rect.centery + 9),
        ]
        pygame.draw.polygon(surface, (8, 14, 24), pointer_points)
        pygame.draw.lines(surface, (96, 170, 255), False, pointer_points, 2)

        map_label = self._format_route_label(summary.get("map_index"), summary.get("map_name"))
        status_label = self._display_state_name(summary.get("current_state"))
        hp_label = self._format_hp_label(summary.get("current_hp"), summary.get("max_hp"))
        rows = [
            ("Route", map_label),
            ("Status", status_label),
            ("Character", summary.get("character_name") or "Unknown"),
            ("HP", hp_label),
        ]
        for index, (label, value) in enumerate(rows):
            row_y = bubble_rect.y + 20 + (index * 24)
            label_surface = self._tiny_font.render(f"{label}:", True, (112, 146, 176))
            value_surface = self._tiny_font.render(str(value), True, (236, 244, 255))
            surface.blit(label_surface, (bubble_rect.x + 16, row_y))
            surface.blit(value_surface, (bubble_rect.x + 84, row_y))

    def _draw_confirm_dialog(self, surface: Any, layout: dict[str, Any]) -> None:
        scrim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        scrim.fill((5, 9, 16, 190))
        surface.blit(scrim, (0, 0))

        panel_rect = pygame.Rect(*layout["confirm_panel_rect"])
        panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (10, 18, 32, 236), panel_surface.get_rect(), border_radius=24)
        pygame.draw.rect(panel_surface, (255, 193, 88, 190), panel_surface.get_rect(), 2, border_radius=24)
        surface.blit(panel_surface, panel_rect.topleft)

        self._draw_text(surface, "Overwrite saved run?", (panel_rect.x + 24, panel_rect.y + 24), self._font)
        self._draw_text(
            surface,
            "Starting a new run will replace the current resumable save after you choose a character.",
            (panel_rect.x + 24, panel_rect.y + 66),
            self._small_font,
            width=panel_rect.width - 48,
        )

        for index, button in enumerate(layout["confirm_buttons"]):
            selected = index == self._keyboard_index
            self._draw_button(
                surface,
                button["rect"],
                button["label"],
                button["action"],
                hovered=self._hovered_action == button["action"],
                pressed=self._pressed_action == button["action"],
                enabled=button["enabled"],
                selected=selected,
            )

    def _format_route_label(self, map_index: Any, map_name: Any) -> str:
        if isinstance(map_name, str) and map_name:
            return map_name if not map_index else f"Map {map_index}: {map_name}"
        if map_index:
            return f"Map {map_index}"
        return "Unavailable"

    def _display_state_name(self, current_state: Any) -> str:
        if not isinstance(current_state, str) or not current_state:
            return "Unknown"
        return STATE_LABELS.get(current_state, current_state.replace("_", " ").title())

    def _format_hp_label(self, current_hp: Any, max_hp: Any) -> str:
        if isinstance(current_hp, int) and isinstance(max_hp, int):
            return f"{current_hp}/{max_hp}"
        return "Unknown"

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
        color: tuple[int, int, int] = (236, 244, 255),
    ) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._title_font is not None:
            return

        self._font_scale = scale
        self._title_font = pygame.font.SysFont("arialblack", max(54, int(72 * scale)))
        self._title_support_font = pygame.font.SysFont("consolas", max(30, int(38 * scale)))
        self._font = pygame.font.SysFont("consolas", max(22, int(28 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(17, int(21 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(13, int(15 * scale)))

    def _draw_cover_image(self, surface: Any, path: Path, destination: pygame.Rect) -> None:
        image = self._load_image(path)
        image_rect = image.get_rect()
        scale = max(destination.width / image_rect.width, destination.height / image_rect.height)
        scaled_size = (
            max(1, int(round(image_rect.width * scale))),
            max(1, int(round(image_rect.height * scale))),
        )
        scaled_image = pygame.transform.smoothscale(image, scaled_size)
        blit_rect = scaled_image.get_rect(center=destination.center)
        surface.blit(scaled_image, destination.topleft, area=destination.move(-blit_rect.x, -blit_rect.y))

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
            image.fill((16, 28, 42, 255))

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
                    "character_name": "The Enforcer",
                    "map_name": "Outskirts",
                    "map_index": 1,
                    "current_hp": 58,
                    "max_hp": 70,
                },
                "confirm_overwrite": False,
            },
            "presentation": {"ui_scale": 1.0},
        }
    )
    return {
        "button_count": len(layout["buttons"]),
        "continue_enabled": layout["continue_enabled"],
        "route_label": ui._format_route_label(1, "Outskirts"),
        "status_label": ui._display_state_name("shop"),
    }
