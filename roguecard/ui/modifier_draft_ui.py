from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.relic_assets import relic_assets
from ui.render_utils import clamp_scale, design_frame_scale, draw_screen_scrim, draw_wrapped_text, fit_design_frame, point_in_rect, scale_design_rect

DRAFT_OFFER_WIDTH = 240
DRAFT_OFFER_HEIGHT = 296
DRAFT_OFFER_Y = 214
DRAFT_OFFER_SPACING = 360
DRAFT_TOOLTIP_WIDTH = 300
DESIGN_SIZE = (1280, 720)
RARITY_OUTLINE_COLORS = {
    "common": (154, 162, 176),
    "uncommon": (94, 208, 124),
    "rare": (154, 108, 255),
    "boss": (244, 208, 132),
    "special": (208, 160, 255),
}


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
        self._last_surface_size: tuple[int, int] = DESIGN_SIZE

    def preload_assets(self) -> None:
        if pygame is None:
            return
        relic_assets.preload()
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
        ):
            self._load_image(path)

    def handle_event(
        self,
        event: Any,
        draft_state: dict[str, Any],
        screen_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(draft_state, self._last_surface_size if screen_size is None else screen_size)

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
                return {"type": "notice", "message": "That relic slot is empty.", "level": "error"}
            return {"type": "select_run_modifier_offer", "modifier_id": layout["offers"][offer_index]["id"]}

        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if not layout["can_confirm"]:
                return {"type": "notice", "message": "Select a relic before confirming it.", "level": "error"}
            return {"type": "confirm_run_modifier_selection"}

        return None

    def build_layout(
        self,
        draft_state: dict[str, Any],
        screen_size: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        draft = draft_state["modifier_draft"]
        resolved_surface_size = self._resolve_surface_size(screen_size)
        layout_frame = fit_design_frame(resolved_surface_size, DESIGN_SIZE)
        layout_scale = design_frame_scale(layout_frame, DESIGN_SIZE)
        offers = []
        total_width = ((len(draft["offers"]) - 1) * DRAFT_OFFER_SPACING) + DRAFT_OFFER_WIDTH
        start_x = (DESIGN_SIZE[0] - total_width) // 2
        for index, offer in enumerate(draft["offers"]):
            offer_rect = scale_design_rect(
                (
                    start_x + (index * DRAFT_OFFER_SPACING),
                    DRAFT_OFFER_Y,
                    DRAFT_OFFER_WIDTH,
                    DRAFT_OFFER_HEIGHT,
                ),
                layout_frame,
                DESIGN_SIZE,
            )
            offers.append(
                {
                    **offer,
                    "rect": offer_rect,
                }
            )

        return {
            "offers": offers,
            "selected_offer_id": draft["selected_offer_id"],
            "can_confirm": draft["can_confirm"],
            "confirm_rect": scale_design_rect((540, 614, 200, 50), layout_frame, DESIGN_SIZE),
            "top_panel_rect": scale_design_rect((24, 86, 1232, 96), layout_frame, DESIGN_SIZE),
            "status_message": draft_state.get("status_message", ""),
            "character_name": (draft_state.get("character") or {}).get("name", "Runner"),
            "layout_frame": layout_frame,
            "layout_scale": layout_scale,
        }

    def render(self, surface: Any, draft_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._last_surface_size = surface.get_size()
        layout = self.build_layout(draft_state, self._last_surface_size)
        ui_scale = float(draft_state.get("presentation", {}).get("ui_scale", 1.0))
        self._ensure_fonts(ui_scale * max(0.78, min(1.12, layout["layout_scale"])))
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        top_panel_rect = pygame.Rect(*layout["top_panel_rect"])
        top_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), top_panel_rect.size)

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=190)
        surface.blit(top_panel, top_panel_rect.topleft)

        title_x = top_panel_rect.x + max(18, int(round(top_panel_rect.width * 0.016)))
        title_y = top_panel_rect.y + max(18, int(round(top_panel_rect.height * 0.23)))
        status_y = top_panel_rect.y + max(52, int(round(top_panel_rect.height * 0.64)))
        character_x = top_panel_rect.right - max(250, int(round(top_panel_rect.width * 0.23)))
        self._draw_text(surface, "Choose Your Starter Relic", (title_x, title_y), self._title_font, width=max(280, top_panel_rect.width - 320))
        self._draw_text(surface, layout["status_message"], (title_x, status_y), self._small_font, width=max(260, int(round(top_panel_rect.width * 0.68))))
        self._draw_text(surface, layout["character_name"], (character_x, title_y + 10), self._small_font, width=max(160, int(round(top_panel_rect.width * 0.2))))

        hovered_offer = None
        for offer in layout["offers"]:
            hovered = self._hovered_action == f"offer:{offer['id']}"
            selected = layout["selected_offer_id"] == offer["id"]
            pressed = self._pressed_action == f"offer:{offer['id']}"
            if hovered:
                hovered_offer = offer
            self._draw_offer_sprite(surface, offer, hovered=hovered, selected=selected, pressed=pressed)

        if hovered_offer is not None:
            self._draw_hover_tooltip(surface, hovered_offer)

        self._draw_button(
            surface,
            layout["confirm_rect"],
            "Confirm",
            hovered=self._hovered_action == "confirm",
            pressed=self._pressed_action == "confirm",
            enabled=layout["can_confirm"],
        )

    def _draw_offer_sprite(
        self,
        surface: Any,
        offer: dict[str, Any],
        *,
        hovered: bool,
        selected: bool,
        pressed: bool,
    ) -> None:
        rect = pygame.Rect(*offer["rect"])
        rarity = str(offer.get("rarity", "common")).lower()
        outline_color = RARITY_OUTLINE_COLORS.get(rarity, RARITY_OUTLINE_COLORS["common"])
        target_size = 192 + (16 if hovered else 0) + (12 if selected else 0) - (6 if pressed else 0)
        relic_art = relic_assets.get_relic_art(offer["id"], (target_size, target_size))
        if relic_art is None:
            fallback = self._small_font.render(offer["name"], True, (232, 240, 255))
            fallback_rect = fallback.get_rect(center=(rect.centerx, rect.centery))
            surface.blit(fallback, fallback_rect)
            return

        vertical_lift = 14 if hovered else 8 if selected else 0
        art_rect = relic_art.get_rect(center=(rect.centerx, rect.centery - vertical_lift))

        shadow = relic_art.copy()
        shadow.fill((0, 0, 0, 105), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(shadow, (art_rect.x + 4, art_rect.y + 10))

        pulse_strength = 1.0
        if rarity in {"rare", "boss", "special"}:
            pulse_strength = 0.9 + (0.1 * math.sin(pygame.time.get_ticks() * 0.0032))

        self._draw_outline(
            surface,
            relic_art,
            art_rect,
            color=self._scaled_color(outline_color, pulse_strength),
            thickness=4 if selected else 3 if hovered else 2,
            glow_alpha=84 if selected else 44 if hovered else 22,
            animated=rarity in {"rare", "boss", "special"},
        )
        if selected:
            self._draw_outline(
                surface,
                relic_art,
                art_rect,
                color=(255, 244, 196),
                thickness=2,
                glow_alpha=36,
                animated=False,
            )

        surface.blit(relic_art, art_rect)

    def _draw_outline(
        self,
        surface: Any,
        relic_art: Any,
        art_rect: Any,
        *,
        color: tuple[int, int, int],
        thickness: int,
        glow_alpha: int,
        animated: bool,
    ) -> None:
        mask = pygame.mask.from_surface(relic_art)
        outline_points = mask.outline()
        if len(outline_points) < 2:
            return

        drift_x = 0
        drift_y = 0
        if animated:
            ticks = pygame.time.get_ticks()
            drift_x = int(round(math.sin(ticks * 0.0018) * 1.2))
            drift_y = int(round(math.cos(ticks * 0.0015) * 1.2))

        padding = thickness + 8
        outline_surface = pygame.Surface(
            (art_rect.width + (padding * 2), art_rect.height + (padding * 2)),
            pygame.SRCALPHA,
        )
        shifted_points = [
            (point[0] + padding + drift_x, point[1] + padding + drift_y)
            for point in outline_points
        ]
        if glow_alpha > 0:
            pygame.draw.lines(
                outline_surface,
                (*color, glow_alpha),
                True,
                shifted_points,
                thickness + 5,
            )
        pygame.draw.lines(
            outline_surface,
            (*color, 255),
            True,
            shifted_points,
            thickness,
        )
        surface.blit(outline_surface, (art_rect.x - padding, art_rect.y - padding))

    def _draw_hover_tooltip(self, surface: Any, offer: dict[str, Any]) -> None:
        rect = pygame.Rect(*offer["rect"])
        tooltip_height = 102
        tooltip_x = rect.centerx + 56
        if tooltip_x + DRAFT_TOOLTIP_WIDTH > 1248:
            tooltip_x = rect.centerx - DRAFT_TOOLTIP_WIDTH - 56
        tooltip_x = max(32, tooltip_x)
        tooltip_y = max(164, rect.y + 20)
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, DRAFT_TOOLTIP_WIDTH, tooltip_height)
        pygame.draw.rect(surface, (8, 14, 24), tooltip_rect, border_radius=16)
        pygame.draw.rect(surface, (230, 236, 248), tooltip_rect, 2, border_radius=16)
        self._draw_text(surface, offer["name"], (tooltip_rect.x + 16, tooltip_rect.y + 14), self._small_font, width=tooltip_rect.width - 32)
        self._draw_text(surface, offer["description"], (tooltip_rect.x + 16, tooltip_rect.y + 46), self._tiny_font, width=tooltip_rect.width - 32)

    def _scaled_color(
        self,
        color: tuple[int, int, int],
        multiplier: float,
    ) -> tuple[int, int, int]:
        return tuple(max(0, min(255, int(channel * multiplier))) for channel in color)

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "confirm":
            if not layout["can_confirm"]:
                return {"type": "notice", "message": "Select a relic before confirming it.", "level": "error"}
            return {"type": "confirm_run_modifier_selection"}
        if action_id.startswith("offer:"):
            return {"type": "select_run_modifier_offer", "modifier_id": action_id.removeprefix("offer:")}
        return {"type": "notice", "message": "Unknown relic draft action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for offer in layout["offers"]:
            if point_in_rect(position, offer["rect"]):
                return f"offer:{offer['id']}"
        if point_in_rect(position, layout["confirm_rect"]):
            return "confirm"
        return None

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
        fill = (36, 72, 122) if enabled else (26, 34, 48)
        border = (230, 240, 255) if enabled else (110, 118, 136)
        if hovered and enabled:
            fill = (54, 96, 158)
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
        scale = clamp_scale(scale, 0.78, MAX_UI_SCALE)
        if self._font_scale == scale and self._title_font is not None:
            return

        self._font_scale = scale
        self._title_font = pygame.font.SysFont("consolas", max(28, int(36 * scale)))
        self._font = pygame.font.SysFont("consolas", max(20, int(26 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(18, int(20 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(13, int(15 * scale)))

    def _resolve_surface_size(self, screen_size: tuple[int, int] | None) -> tuple[int, int]:
        if screen_size is None:
            return self._last_surface_size
        self._last_surface_size = (max(1, int(screen_size[0])), max(1, int(screen_size[1])))
        return self._last_surface_size

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
            "status_message": "The Enforcer ready. Choose a starter relic.",
            "modifier_draft": {
                "offers": [
                    {
                        "id": "plated_grip",
                        "name": "Plated Grip",
                        "kind": "relic",
                        "type": "relic",
                        "rarity": "common",
                        "description": "Add Firewall to the starting deck.",
                        "selected": True,
                    },
                    {
                        "id": "market_key",
                        "name": "Market Key",
                        "kind": "relic",
                        "type": "relic",
                        "rarity": "uncommon",
                        "description": "Shop card prices cost 15% less.",
                        "selected": False,
                    },
                    {
                        "id": "signal_router",
                        "name": "Signal Router",
                        "kind": "relic",
                        "type": "relic",
                        "rarity": "rare",
                        "description": "Card rewards show 1 extra choice.",
                        "selected": False,
                    },
                ],
                "selected_offer_id": "plated_grip",
                "can_confirm": True,
            },
            "character": {"name": "The Enforcer"},
            "presentation": {"ui_scale": 1.0},
        }
    )
    return {
        "offer_count": len(layout["offers"]),
        "can_confirm": layout["can_confirm"],
        "first_offer_x": layout["offers"][0]["rect"][0],
    }
