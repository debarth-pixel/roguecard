from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


class EventUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None

    def preload_assets(self) -> None:
        if pygame is None:
            return
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("cards", "card_placeholder.png"),
        ):
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
                return {
                    "type": "notice",
                    "message": layout["selected_choice"]["disabled_reason"],
                    "level": "error",
                }
            if not layout["can_confirm"]:
                return {
                    "type": "notice",
                    "message": "Select a deck card target before confirming this choice.",
                    "level": "error",
                }
            return {"type": "confirm_event_choice"}

        return None

    def build_layout(self, event_state: dict[str, Any]) -> dict[str, Any]:
        event = event_state["event"]
        choices = []
        for index, choice in enumerate(event["choices"]):
            choices.append(
                {
                    **choice,
                    "rect": (44, 244 + (index * 58), 720, 48),
                    "shortcut": index + 1 if index < 9 else None,
                }
            )

        selected_choice = next(
            (choice for choice in choices if choice["id"] == event["selected_choice_id"]),
            None,
        )

        purge_targets = []
        for index, target in enumerate(event["purge_targets"]):
            purge_targets.append(
                {
                    **target,
                    "rect": (44 + ((index % 6) * 198), 566 + ((index // 6) * 40), 182, 30),
                }
            )

        can_confirm = (
            not event["resolved"]
            and selected_choice is not None
            and selected_choice["available"]
            and (
                selected_choice["choice_type"] != "purge"
                or event["selected_target_id"] is not None
            )
        )

        return {
            "title": event["title"],
            "body": event["body"],
            "player_hp": event_state["player"]["current_hp"],
            "player_max_hp": event_state["player"]["max_hp"],
            "player_credits": event_state["player"]["credits"],
            "deck_size": event["deck_size"],
            "choices": choices,
            "selected_choice": selected_choice,
            "selected_choice_id": event["selected_choice_id"],
            "selected_choice_type": event["selected_choice_type"],
            "purge_targets": purge_targets,
            "resolved": event["resolved"],
            "resolution_summary": event["resolution_summary"],
            "resolution_details": event["resolution_details"],
            "can_continue": event["can_continue"],
            "can_confirm": can_confirm,
            "confirm_rect": (1056, 480, 168, 48),
            "continue_rect": (1056, 636, 168, 48),
            "controls": [
                "Click or 1-9: choose option",
                "Click target card for purge choices",
                "Enter / Space: confirm",
                "C: continue",
                "S: settings",
            ],
        }

    def render(self, surface: Any, event_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(event_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = event_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(event_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        header_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (1232, 88))
        story_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (760, 434))
        side_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (438, 434))
        lower_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (1232, 150))
        card_panel = self._scaled_image(resolve_asset_path("cards", "card_placeholder.png"), (182, 94))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176)
        surface.blit(header_panel, (24, 96))
        surface.blit(story_panel, (24, 174))
        surface.blit(side_panel, (818, 174))
        show_purge_panel = layout["selected_choice_type"] == "purge" and not layout["resolved"]
        if show_purge_panel:
            surface.blit(lower_panel, (24, 540))

        self._draw_text(surface, "City Event", (44, 118), self._font)
        self._draw_text(surface, layout["title"], (44, 152), self._small_font, width=720)

        self._draw_chip(surface, f"HP {layout['player_hp']}/{layout['player_max_hp']}", (846, 190), 118)
        self._draw_chip(surface, f"Credits {layout['player_credits']}", (974, 190), 132)
        self._draw_chip(surface, f"Deck {layout['deck_size']}", (1116, 190), 112)

        self._draw_text(surface, layout["body"], (44, 194), self._tiny_font, width=704)

        for choice in layout["choices"]:
            rect = pygame.Rect(*choice["rect"])
            selected = layout["selected_choice_id"] == choice["id"]
            hovered = self._hovered_action == f"choice:{choice['id']}"
            pressed = self._pressed_action == f"choice:{choice['id']}"
            available = choice["available"] and not layout["resolved"]
            fill = (24, 34, 50) if available else (22, 24, 34)
            if hovered and available:
                fill = (34, 48, 68)
            if pressed and available:
                fill = (255, 214, 110)
            border = (
                (255, 214, 110)
                if selected
                else (255, 255, 255)
                if hovered and available
                else (190, 205, 230)
                if high_contrast
                else (104, 118, 146)
            )
            if not available:
                border = (120, 88, 100)
            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, border, rect, 2, border_radius=14)
            self._draw_text(surface, choice["label"], (rect.x + 14, rect.y + 8), self._small_font, width=240)
            detail_text = choice["description"] if available else choice["disabled_reason"] or choice["description"]
            self._draw_text(surface, detail_text, (rect.x + 14, rect.y + 28), self._tiny_font, width=560)
            if choice["shortcut"] is not None:
                badge_rect = pygame.Rect(rect.x + rect.width - 30, rect.y + 10, 22, 22)
                pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=11)
                pygame.draw.rect(surface, (255, 214, 110), badge_rect, 2, border_radius=11)
                badge = self._tiny_font.render(str(choice["shortcut"]), True, (255, 214, 110))
                surface.blit(badge, badge.get_rect(center=badge_rect.center))

        selected_choice = layout["selected_choice"]
        self._draw_text(surface, "Selected Choice", (838, 234), self._small_font)
        if layout["resolved"]:
            self._draw_text(surface, layout["resolution_summary"] or "Outcome resolved.", (838, 270), self._small_font, width=364)
            details_y = 324
            for detail in layout["resolution_details"]:
                self._draw_text(surface, detail, (838, details_y), self._tiny_font, width=360)
                details_y += 24
        elif selected_choice is None:
            self._draw_text(surface, "Select one option to see what it will resolve.", (838, 270), self._small_font, width=364)
        else:
            if selected_choice["choice_type"] == "purge":
                surface.blit(card_panel, (838, 270))
            self._draw_text(surface, selected_choice["label"], (850, 282), self._small_font, width=332)
            self._draw_text(surface, selected_choice["description"], (838, 324), self._tiny_font, width=364)
            if not selected_choice["available"]:
                self._draw_text(surface, selected_choice["disabled_reason"], (838, 386), self._tiny_font, width=364)
            elif selected_choice["choice_type"] == "purge":
                target_text = "Target selected." if event_state["event"]["selected_target_id"] else "Choose a deck card below."
                self._draw_text(surface, target_text, (838, 386), self._tiny_font, width=364)
            elif selected_choice["choice_type"] == "risk":
                self._draw_text(surface, "Outcome will lock in once you confirm.", (838, 386), self._tiny_font, width=364)
            else:
                self._draw_text(surface, "Confirm to resolve this event choice.", (838, 386), self._tiny_font, width=364)

        self._draw_button(
            surface,
            layout["confirm_rect"],
            "Confirm",
            self._hovered_action == "confirm",
            self._pressed_action == "confirm",
            enabled=layout["can_confirm"],
        )

        if show_purge_panel:
            self._draw_text(surface, "Deck Targets", (44, 556), self._small_font)
            for target in layout["purge_targets"]:
                rect = pygame.Rect(*target["rect"])
                hovered = self._hovered_action == f"target:{target['option_id']}"
                pressed = self._pressed_action == f"target:{target['option_id']}"
                fill = (24, 34, 50)
                if hovered:
                    fill = (34, 48, 68)
                if pressed:
                    fill = (255, 214, 110)
                border = (255, 214, 110) if target["selected"] else (255, 255, 255) if hovered else (104, 118, 146)
                pygame.draw.rect(surface, fill, rect, border_radius=12)
                pygame.draw.rect(surface, border, rect, 2, border_radius=12)
                self._draw_text(surface, target["card"]["name"], (rect.x + 10, rect.y + 7), self._tiny_font, width=150)

        if layout["can_continue"]:
            self._draw_button(
                surface,
                layout["continue_rect"],
                "Continue",
                self._hovered_action == "continue",
                self._pressed_action == "continue",
                enabled=True,
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
        if layout["selected_choice_type"] == "purge" and not layout["resolved"]:
            for target in layout["purge_targets"]:
                if point_in_rect(position, target["rect"]):
                    return f"target:{target['option_id']}"
        if point_in_rect(position, layout["confirm_rect"]):
            return "confirm"
        if layout["can_continue"] and point_in_rect(position, layout["continue_rect"]):
            return "continue"
        return None

    def _draw_chip(self, surface: Any, text: str, position: tuple[int, int], width: int) -> None:
        rect = pygame.Rect(position[0], position[1], width, 26)
        pygame.draw.rect(surface, (18, 28, 42), rect, border_radius=10)
        pygame.draw.rect(surface, (126, 140, 168), rect, 1, border_radius=10)
        label = self._tiny_font.render(text, True, (232, 240, 255))
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        hovered: bool,
        pressed: bool,
        enabled: bool,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        fill = (36, 78, 138) if enabled else (26, 34, 48)
        border = (230, 240, 255) if enabled else (110, 118, 136)
        if hovered and enabled:
            fill = (52, 104, 184)
        if pressed and enabled:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        pygame.draw.rect(surface, fill, rect, border_radius=12)
        pygame.draw.rect(surface, border, rect, 2, border_radius=12)
        text_color = (240, 245, 255) if enabled and not pressed else (18, 24, 36) if pressed else (160, 170, 190)
        label_surface = self._tiny_font.render(label, True, text_color)
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
        if self._font_scale == scale and self._font is not None:
            return

        self._font_scale = scale
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
                "body": "A blinking courier cache hums beneath a busted tram bench.",
                "choices": [
                    {
                        "id": "crack_cache",
                        "label": "Crack the cache",
                        "description": "Pull a clean stack of credits.",
                        "choice_type": "effect",
                        "available": True,
                        "disabled_reason": None,
                        "selected": False,
                    },
                    {
                        "id": "walk_away",
                        "label": "Walk away",
                        "description": "Leave the drop untouched.",
                        "choice_type": "effect",
                        "available": True,
                        "disabled_reason": None,
                        "selected": False,
                    },
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
