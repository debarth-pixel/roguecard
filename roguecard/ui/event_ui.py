from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.card_renderer import draw_card
from ui.ui_system import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_LINE,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PANEL_ELEVATED,
    RADIUS_LG,
    RADIUS_MD,
    draw_background_stage,
    draw_chip,
    draw_hint_row,
    draw_panel,
)


EVENT_LAYOUT = {
    "main_rect": (72, 110, 760, 560),
    "art_rect": (96, 152, 712, 90),
    "description_rect": (96, 264, 712, 68),
    "choice_start_y": 356,
    "choice_height": 58,
    "choice_gap": 12,
    "side_rect": (856, 164, 360, 392),
    "confirm_rect": (1010, 620, 206, 44),
    "continue_rect": (1010, 620, 206, 44),
    "purge_columns": 2,
    "purge_gap_x": 12,
    "purge_gap_y": 10,
    "purge_height": 82,
}


class EventUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None

    def preload_assets(self) -> None:
        if pygame is None:
            return
        for path in (resolve_asset_path("ui", "bg_map.png"), resolve_asset_path("ui", "panel.png")):
            self._load_image(path)

    def handle_event(self, event: Any, event_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self.build_layout(event_state)

        if event.type == pygame.MOUSEMOTION:
            self._hovered_action = self._action_at_position(layout, event.pos)
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
        if event.key == pygame.K_c and layout["can_continue"]:
            return {"type": "continue_from_event"}
        if pygame.K_1 <= event.key <= pygame.K_9:
            choice_index = event.key - pygame.K_1
            if choice_index >= len(layout["choices"]):
                return {"type": "notice", "message": "That event option is empty.", "level": "error"}
            choice = layout["choices"][choice_index]
            if not choice["available"]:
                return {"type": "notice", "message": choice["disabled_reason"], "level": "error"}
            return {"type": "select_event_choice", "choice_id": choice["id"]}
        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if layout["can_continue"]:
                return {"type": "continue_from_event"}
            if layout["selected_choice"] is None:
                return {"type": "notice", "message": "Select an event choice before confirming it.", "level": "error"}
            if not layout["selected_choice"]["available"]:
                return {"type": "notice", "message": layout["selected_choice"]["disabled_reason"], "level": "error"}
            if not layout["can_confirm"]:
                return {"type": "notice", "message": "Choose a deck card target before confirming this choice.", "level": "error"}
            return {"type": "confirm_event_choice"}
        return None

    def build_layout(self, event_state: dict[str, Any]) -> dict[str, Any]:
        event = event_state["event"]
        choices = []
        for index, choice in enumerate(event["choices"]):
            choices.append(
                {
                    **choice,
                    "rect": (96, EVENT_LAYOUT["choice_start_y"] + (index * (EVENT_LAYOUT["choice_height"] + EVENT_LAYOUT["choice_gap"])), 712, EVENT_LAYOUT["choice_height"]),
                    "shortcut": index + 1 if index < 9 else None,
                }
            )
        selected_choice = next((choice for choice in choices if choice["id"] == event["selected_choice_id"]), None)
        choice_bottom = choices[-1]["rect"][1] + choices[-1]["rect"][3] if choices else EVENT_LAYOUT["choice_start_y"]
        purge_targets: list[dict[str, Any]] = []
        purge_title_y = choice_bottom + 16
        if selected_choice is not None and selected_choice["choice_type"] == "purge" and not event["resolved"]:
            chip_width = (328 - (EVENT_LAYOUT["purge_gap_x"] * (EVENT_LAYOUT["purge_columns"] - 1))) // EVENT_LAYOUT["purge_columns"]
            for index, target in enumerate(event["purge_targets"]):
                row = index // EVENT_LAYOUT["purge_columns"]
                col = index % EVENT_LAYOUT["purge_columns"]
                purge_targets.append(
                    {
                        **target,
                        "rect": (
                            EVENT_LAYOUT["side_rect"][0] + 16 + (col * (chip_width + EVENT_LAYOUT["purge_gap_x"])),
                            EVENT_LAYOUT["side_rect"][1] + 120 + (row * (EVENT_LAYOUT["purge_height"] + EVENT_LAYOUT["purge_gap_y"])),
                            chip_width,
                            EVENT_LAYOUT["purge_height"],
                        ),
                    }
                )

        can_confirm = not event["resolved"] and selected_choice is not None and selected_choice["available"] and (selected_choice["choice_type"] != "purge" or event["selected_target_id"] is not None)
        return {
            "event_id": event["event_id"],
            "title": event["title"],
            "body": event["body"],
            "player_hp": event_state["player"]["current_hp"],
            "player_max_hp": event_state["player"]["max_hp"],
            "player_credits": event_state["player"]["credits"],
            "deck_size": event["deck_size"],
            "choices": choices,
            "selected_choice": selected_choice,
            "selected_choice_id": event["selected_choice_id"],
            "purge_targets": purge_targets,
            "purge_title_y": purge_title_y,
            "resolved": event["resolved"],
            "resolution_summary": event["resolution_summary"],
            "resolution_details": event["resolution_details"],
            "can_continue": event["can_continue"],
            "can_confirm": can_confirm,
            "main_rect": EVENT_LAYOUT["main_rect"],
            "art_rect": EVENT_LAYOUT["art_rect"],
            "description_rect": EVENT_LAYOUT["description_rect"],
            "side_rect": EVENT_LAYOUT["side_rect"],
            "confirm_rect": EVENT_LAYOUT["confirm_rect"],
            "continue_rect": EVENT_LAYOUT["continue_rect"],
        }

    def render(self, surface: Any, event_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        self._ensure_fonts(event_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = event_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(event_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        draw_background_stage(surface, background, veil_alpha=170, top_band_height=72, bottom_band_height=92, line_step=54, line_alpha=6)
        draw_panel(surface, pygame.Rect(*layout["main_rect"]), accent=COLOR_LINE, fill=COLOR_PANEL, radius=RADIUS_LG, border_width=1, shadow_alpha=0)
        draw_panel(surface, pygame.Rect(*layout["side_rect"]), accent=COLOR_LINE, fill=COLOR_PANEL, radius=RADIUS_LG, border_width=1, shadow_alpha=0)
        self._draw_text(surface, layout["title"], (96, 120), self._title_font, width=712)
        self._draw_event_art_panel(surface, layout)
        self._draw_text(surface, layout["body"], (layout["description_rect"][0], layout["description_rect"][1]), self._small_font, width=layout["description_rect"][2], color=(220, 232, 246))

        for choice in layout["choices"]:
            self._draw_choice(surface, choice, layout, high_contrast=high_contrast)

        if layout["purge_targets"]:
            self._draw_text(surface, "Deck Cards", (layout["side_rect"][0] + 16, layout["side_rect"][1] + 18), self._tiny_font, color=(210, 222, 238))
            for target in layout["purge_targets"]:
                self._draw_purge_target(surface, target)

        self._draw_outcome_rail(surface, layout)

        if layout["can_continue"]:
            self._draw_button(surface, layout["continue_rect"], "Continue", self._hovered_action == "continue", self._pressed_action == "continue", enabled=True)
        else:
            self._draw_button(surface, layout["confirm_rect"], "Confirm", self._hovered_action == "confirm", self._pressed_action == "confirm", enabled=layout["can_confirm"])
        draw_hint_row(
            surface,
            pygame.Rect(72, 620, 912, 44),
            left_text="1-9 choose  |  Enter confirm  |  C continue",
            font=self._tiny_font,
            accent=COLOR_LINE,
            fill=COLOR_PANEL_ELEVATED,
        )

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "confirm":
            if not layout["can_confirm"]:
                if layout["selected_choice"] is None:
                    return {"type": "notice", "message": "Select an event choice before confirming it.", "level": "error"}
                if layout["selected_choice"]["choice_type"] == "purge":
                    return {"type": "notice", "message": "Choose a deck card target before confirming this choice.", "level": "error"}
                return {"type": "notice", "message": "That event choice is unavailable right now.", "level": "error"}
            return {"type": "confirm_event_choice"}
        if action_id == "continue":
            if not layout["can_continue"]:
                return {"type": "notice", "message": "Resolve the event before continuing.", "level": "error"}
            return {"type": "continue_from_event"}
        if action_id.startswith("choice:"):
            choice_id = action_id.removeprefix("choice:")
            choice = next(choice for choice in layout["choices"] if choice["id"] == choice_id)
            if not choice["available"]:
                return {"type": "notice", "message": choice["disabled_reason"], "level": "error"}
            return {"type": "select_event_choice", "choice_id": choice_id}
        if action_id.startswith("target:"):
            return {"type": "select_event_target", "target_id": action_id.removeprefix("target:")}
        return {"type": "notice", "message": "Unknown event action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for choice in layout["choices"]:
            if point_in_rect(position, choice["rect"]):
                return f"choice:{choice['id']}"
        for target in layout["purge_targets"]:
            if point_in_rect(position, target["rect"]):
                return f"target:{target['option_id']}"
        if layout["can_continue"] and point_in_rect(position, layout["continue_rect"]):
            return "continue"
        if point_in_rect(position, layout["confirm_rect"]):
            return "confirm"
        return None

    def _draw_left_panel(self, surface: Any, panel_image: Any, rect: pygame.Rect) -> None:
        panel = pygame.transform.smoothscale(panel_image, rect.size).copy()
        panel.set_alpha(226)
        surface.blit(panel, rect.topleft)
        pygame.draw.rect(surface, (84, 114, 164), rect, 2, border_radius=22)

    def _draw_event_art_panel(self, surface: Any, layout: dict[str, Any]) -> None:
        rect = pygame.Rect(*layout["art_rect"])
        accent, shadow = self._event_palette(layout["event_id"])
        draw_panel(surface, rect, accent=accent, fill=shadow, radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        for index in range(5):
            stripe_width = 92 + (index * 16)
            stripe_rect = pygame.Rect(rect.x + 18 + (index * 128), rect.y + 16, stripe_width, rect.height - 32)
            stripe_surface = pygame.Surface((stripe_rect.width, stripe_rect.height), pygame.SRCALPHA)
            stripe_surface.fill((*accent, 28 if index % 2 == 0 else 14))
            stripe_surface = pygame.transform.rotate(stripe_surface, -12)
            surface.blit(stripe_surface, stripe_surface.get_rect(center=stripe_rect.center))
        glow_rect = pygame.Rect(rect.x + 24, rect.y + 24, 180, 10)
        pygame.draw.rect(surface, (255, 214, 110), glow_rect, border_radius=6)
        pygame.draw.rect(surface, (190, 234, 248), pygame.Rect(rect.x + 24, rect.y + 44, 132, 6), border_radius=3)

    def _draw_choice(self, surface: Any, choice: dict[str, Any], layout: dict[str, Any], *, high_contrast: bool) -> None:
        rect = pygame.Rect(*choice["rect"])
        draw_rect = rect.move(0, -4 if self._hovered_action == f"choice:{choice['id']}" and choice["available"] and not layout["resolved"] else 0)
        selected = layout["selected_choice_id"] == choice["id"]
        hovered = self._hovered_action == f"choice:{choice['id']}"
        pressed = self._pressed_action == f"choice:{choice['id']}"
        available = choice["available"] and not layout["resolved"]
        fill = (18, 28, 42) if available else (22, 24, 32)
        border = (92, 118, 150)
        if hovered and available:
            fill = (28, 42, 62)
            border = (232, 240, 255)
        if selected:
            fill = (42, 62, 98)
            border = (255, 214, 110)
        if pressed and available:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        if high_contrast and available and not selected:
            border = (220, 232, 248)
        draw_panel(surface, draw_rect, accent=border, fill=fill, radius=RADIUS_MD, border_width=2 if selected or hovered else 1, shadow_alpha=0)
        title_color = (18, 24, 36) if pressed and available else (246, 250, 255) if available else (176, 184, 198)
        detail_color = (24, 32, 42) if pressed and available else (204, 216, 236) if available else (136, 144, 156)
        self._draw_text(surface, choice["label"], (draw_rect.x + 18, draw_rect.y + 8), self._small_font, width=620, color=title_color)
        detail_text = choice["description"] if available else choice["disabled_reason"] or choice["description"]
        self._draw_text(surface, detail_text, (draw_rect.x + 18, draw_rect.y + 30), self._tiny_font, width=640, color=detail_color)
        if choice["shortcut"] is not None:
            draw_chip(surface, pygame.Rect(draw_rect.right - 36, draw_rect.y + 18, 22, 22), label=str(choice["shortcut"]), font=self._tiny_font, accent=border, fill=COLOR_PANEL_ELEVATED)

    def _draw_purge_target(self, surface: Any, target: dict[str, Any]) -> None:
        rect = pygame.Rect(*target["rect"])
        hovered = self._hovered_action == f"target:{target['option_id']}"
        pressed = self._pressed_action == f"target:{target['option_id']}"
        fill = (34, 48, 72) if hovered else (22, 32, 50)
        border = (224, 238, 255) if hovered else (102, 120, 152)
        if target["selected"]:
            fill = (54, 82, 126)
            border = (255, 214, 110)
        if pressed:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        draw_card(
            surface,
            rect,
            target["card"],
            {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._tiny_font},
            variant="mini",
            selected=target["selected"],
            hovered=hovered,
            pressed=pressed,
            high_contrast=False,
        )

    def _draw_outcome_rail(self, surface: Any, layout: dict[str, Any]) -> None:
        rect = pygame.Rect(*layout["side_rect"])
        visible = layout["resolved"] or layout["selected_choice"] is not None
        if not visible:
            return
        if layout["purge_targets"] and not layout["resolved"]:
            header_rect = pygame.Rect(rect.x + 16, rect.y + 16, rect.width - 32, 86)
            draw_panel(surface, header_rect, accent=COLOR_LINE, fill=COLOR_PANEL_ELEVATED, radius=RADIUS_MD, border_width=1, shadow_alpha=0)
            draw_chip(surface, pygame.Rect(header_rect.x + 14, header_rect.y + 14, 94, 24), label="Selected", font=self._tiny_font, accent=(118, 182, 244), fill=COLOR_PANEL)
            self._draw_text(surface, layout["selected_choice"]["label"], (header_rect.x + 14, header_rect.y + 44), self._tiny_font, width=header_rect.width - 28)
            return
        inner_rect = rect.inflate(-16, -16)
        draw_panel(surface, inner_rect, accent=COLOR_LINE, fill=COLOR_PANEL_ELEVATED, radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        if layout["resolved"]:
            draw_chip(surface, pygame.Rect(inner_rect.x + 16, inner_rect.y + 16, 94, 24), label="Resolved", font=self._tiny_font, accent=(110, 216, 186), fill=COLOR_PANEL)
            self._draw_text(surface, layout["resolution_summary"] or "Event resolved.", (inner_rect.x + 16, inner_rect.y + 54), self._small_font, width=inner_rect.width - 32)
            detail_y = inner_rect.y + 108
            for detail in layout["resolution_details"][:4]:
                self._draw_text(surface, detail, (inner_rect.x + 16, detail_y), self._tiny_font, width=inner_rect.width - 32, color=(210, 222, 238))
                detail_y += 24
        else:
            draw_chip(surface, pygame.Rect(inner_rect.x + 16, inner_rect.y + 16, 94, 24), label="Selected", font=self._tiny_font, accent=(118, 182, 244), fill=COLOR_PANEL)
            self._draw_text(surface, layout["selected_choice"]["label"], (inner_rect.x + 16, inner_rect.y + 54), self._small_font, width=inner_rect.width - 32)
            self._draw_text(surface, layout["selected_choice"]["description"], (inner_rect.x + 16, inner_rect.y + 94), self._tiny_font, width=inner_rect.width - 32, color=(210, 222, 238))

    def _event_palette(self, event_id: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        seed = sum(ord(char) for char in event_id)
        accents = [
            ((104, 202, 242), (16, 34, 56)),
            ((244, 118, 104), (46, 24, 30)),
            ((120, 224, 172), (18, 42, 38)),
            ((196, 134, 242), (32, 26, 52)),
            ((255, 214, 110), (56, 38, 22)),
        ]
        return accents[seed % len(accents)]

    def _draw_badge(self, surface: Any, text: str, position: tuple[int, int], accent: tuple[int, int, int], text_color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(position[0], position[1], 26, 26)
        pygame.draw.rect(surface, (18, 24, 36), rect, border_radius=13)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=13)
        badge = self._tiny_font.render(text, True, text_color if text_color != (246, 250, 255) else accent)
        surface.blit(badge, badge.get_rect(center=rect.center))

    def _draw_stat_pill(self, surface: Any, text: str, position: tuple[int, int], width: int, accent: tuple[int, int, int]) -> None:
        rect = pygame.Rect(position[0], position[1], width, 28)
        pygame.draw.rect(surface, (16, 24, 38), rect, border_radius=12)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=12)
        label = self._tiny_font.render(text, True, (236, 244, 255))
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_chip(self, surface: Any, text: str, position: tuple[int, int], width: int, accent: tuple[int, int, int]) -> None:
        rect = pygame.Rect(position[0], position[1], width, 28)
        pygame.draw.rect(surface, (18, 28, 42), rect, border_radius=12)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=12)
        label = self._tiny_font.render(text, True, accent)
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_button(self, surface: Any, rect_tuple: tuple[int, int, int, int], label: str, hovered: bool, pressed: bool, enabled: bool) -> None:
        rect = pygame.Rect(*rect_tuple)
        fill = (36, 86, 152) if enabled else (28, 34, 46)
        border = (238, 244, 255) if enabled else (106, 116, 134)
        if hovered and enabled:
            fill = (54, 110, 186)
        if pressed and enabled:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, border, rect, 2, border_radius=14)
        text_color = (240, 246, 255) if enabled and not pressed else (18, 24, 36) if pressed else (160, 172, 188)
        label_surface = self._small_font.render(label, True, text_color)
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_text(self, surface: Any, text: str, position: tuple[int, int], font: Any, width: int | None = None, color: tuple[int, int, int] = (238, 244, 255)) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return
        self._font_scale = scale
        self._font = pygame.font.SysFont("consolas", max(24, int(30 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(17, int(20 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))
        self._title_font = pygame.font.SysFont("consolas", max(28, int(36 * scale)), bold=True)

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        if pygame is None:
            raise RuntimeError("Pygame is required to load event UI assets.")
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((80, 120, 200, 180))
        self._image_cache[cache_key] = image
        return image


def simulate_event_ui() -> dict[str, Any]:
    ui = EventUI()
    return ui.build_layout(
        {
            "event": {
                "event_id": "dead_drop_01",
                "title": "Dead Drop",
                "body": "A courier cache blinks beneath a tram bench.",
                "choices": [
                    {"id": "crack_cache", "label": "Crack the cache", "description": "Gain 25 credits.", "choice_type": "effect", "available": True, "disabled_reason": None, "selected": False},
                    {"id": "walk_away", "label": "Walk away", "description": "Move on.", "choice_type": "effect", "available": True, "disabled_reason": None, "selected": False},
                ],
                "selected_choice_id": "crack_cache",
                "selected_choice_type": "effect",
                "selected_target_id": None,
                "purge_targets": [],
                "resolved": False,
                "resolution_summary": None,
                "resolution_details": [],
                "deck_size": 10,
                "can_continue": False,
            },
            "player": {"current_hp": 64, "max_hp": 70, "credits": 20},
            "presentation": {"ui_scale": 1.0},
        }
    )
