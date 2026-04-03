from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


class ModifierDraftUI:
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
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
        ):
            self._load_image(path)

    def handle_event(self, event: Any, draft_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(draft_state)

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

        if pygame.K_1 <= event.key <= pygame.K_3:
            offer_index = event.key - pygame.K_1
            if offer_index >= len(layout["offers"]):
                return {"type": "notice", "message": "That modifier slot is empty.", "level": "error"}
            return {"type": "select_run_modifier_offer", "modifier_id": layout["offers"][offer_index]["id"]}

        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if not layout["can_confirm"]:
                return {"type": "notice", "message": "Select a modifier before confirming it.", "level": "error"}
            return {"type": "confirm_run_modifier_selection"}

        return None

    def build_layout(self, draft_state: dict[str, Any]) -> dict[str, Any]:
        draft = draft_state["modifier_draft"]
        offers = []
        for index, offer in enumerate(draft["offers"]):
            offers.append(
                {
                    **offer,
                    "rect": (70 + (index * 392), 220, 356, 340),
                    "shortcut": index + 1,
                }
            )

        return {
            "offers": offers,
            "selected_offer_id": draft["selected_offer_id"],
            "can_confirm": draft["can_confirm"],
            "confirm_rect": (1036, 622, 188, 48),
            "status_message": draft_state.get("status_message", ""),
        }

    def render(self, surface: Any, draft_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(draft_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = draft_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(draft_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        top_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (1232, 96))
        offer_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (356, 340))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=188)
        surface.blit(top_panel, (24, 96))

        self._draw_text(surface, "Choose Your Run Modifier", (44, 118), self._title_font)
        self._draw_text(surface, layout["status_message"], (44, 156), self._small_font, width=880)
        self._draw_text(surface, "Pick 1 of 3. Tradeoffs are shown explicitly.", (844, 122), self._tiny_font, width=340)
        self._draw_text(surface, "Controls: click or 1-3 to select, Enter / Space to confirm.", (844, 150), self._tiny_font, width=340)

        for offer in layout["offers"]:
            rect = pygame.Rect(*offer["rect"])
            surface.blit(offer_panel, rect.topleft)
            selected = layout["selected_offer_id"] == offer["id"]
            hovered = self._hovered_action == f"offer:{offer['id']}"
            pressed = self._pressed_action == f"offer:{offer['id']}"
            border = (
                (255, 214, 110)
                if selected
                else (255, 255, 255)
                if hovered
                else (190, 205, 230)
                if high_contrast
                else (104, 118, 146)
            )
            if pressed:
                border = (255, 236, 140)
            pygame.draw.rect(surface, border, rect, 3, border_radius=16)

            self._draw_kind_chip(surface, offer["kind"], (rect.x + 18, rect.y + 16), high_contrast)
            badge_rect = pygame.Rect(rect.x + rect.width - 40, rect.y + 16, 24, 24)
            pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=12)
            pygame.draw.rect(surface, (255, 214, 110), badge_rect, 2, border_radius=12)
            badge = self._tiny_font.render(str(offer["shortcut"]), True, (255, 214, 110))
            surface.blit(badge, badge.get_rect(center=badge_rect.center))

            self._draw_text(surface, offer["name"], (rect.x + 18, rect.y + 62), self._font, width=316)
            self._draw_text(surface, offer["description"], (rect.x + 18, rect.y + 108), self._small_font, width=316)
            self._draw_text(surface, "Upside", (rect.x + 18, rect.y + 198), self._tiny_font)
            self._draw_text(surface, offer["description"], (rect.x + 18, rect.y + 220), self._tiny_font, width=316)

            downside = offer.get("downside")
            if downside:
                self._draw_text(surface, "Tradeoff", (rect.x + 18, rect.y + 272), self._tiny_font)
                self._draw_text(surface, downside, (rect.x + 18, rect.y + 292), self._tiny_font, width=316)

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
                return {"type": "notice", "message": "Select a modifier before confirming it.", "level": "error"}
            return {"type": "confirm_run_modifier_selection"}
        if action_id.startswith("offer:"):
            return {"type": "select_run_modifier_offer", "modifier_id": action_id.removeprefix("offer:")}
        return {"type": "notice", "message": "Unknown modifier draft action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for offer in layout["offers"]:
            if point_in_rect(position, offer["rect"]):
                return f"offer:{offer['id']}"
        if point_in_rect(position, layout["confirm_rect"]):
            return "confirm"
        return None

    def _draw_kind_chip(
        self,
        surface: Any,
        kind: str,
        position: tuple[int, int],
        high_contrast: bool,
    ) -> None:
        colors = {
            "relic": (90, 180, 240),
            "blessing": (100, 210, 150),
            "curse": (220, 110, 110),
        }
        accent = colors.get(kind, (140, 150, 170))
        if high_contrast:
            accent = tuple(min(255, channel + 20) for channel in accent)
        rect = pygame.Rect(position[0], position[1], 108, 28)
        pygame.draw.rect(surface, (18, 28, 42), rect, border_radius=12)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=12)
        label = self._tiny_font.render(kind.title(), True, accent)
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
        fill = (40, 78, 138) if enabled else (26, 34, 48)
        border = (230, 240, 255) if enabled else (110, 118, 136)
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
        self._title_font = pygame.font.SysFont("consolas", max(26, int(34 * scale)))
        self._font = pygame.font.SysFont("consolas", max(20, int(26 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(16, int(19 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load modifier draft UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((120, 90, 220, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_modifier_draft_ui() -> dict[str, Any]:
    ui = ModifierDraftUI()
    layout = ui.build_layout(
        {
            "current_state": "modifier_draft",
            "status_message": "Choose a run modifier before entering the city.",
            "modifier_draft": {
                "offers": [
                    {
                        "id": "carbon_weave",
                        "name": "Carbon Weave",
                        "kind": "relic",
                        "description": "Start each combat with 5 Block.",
                        "downside": None,
                        "selected": True,
                    },
                    {
                        "id": "market_key",
                        "name": "Market Key",
                        "kind": "relic",
                        "description": "Shop card prices cost 15% less.",
                        "downside": None,
                        "selected": False,
                    },
                    {
                        "id": "glass_engine",
                        "name": "Glass Engine",
                        "kind": "curse",
                        "description": "Gain 1 extra Energy on turn 1.",
                        "downside": "Lose 12 max HP.",
                        "selected": False,
                    },
                ],
                "selected_offer_id": "carbon_weave",
                "can_confirm": True,
            },
            "presentation": {"ui_scale": 1.0},
        }
    )
    return {
        "offer_count": len(layout["offers"]),
        "can_confirm": layout["can_confirm"],
    }
