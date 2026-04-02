from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, SHOP_PURGE_OFFER_ID, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


class ShopUI:
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

    def handle_event(self, event: Any, shop_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(shop_state)

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

        if pygame.K_1 <= event.key <= pygame.K_9:
            option_index = event.key - pygame.K_1
            if option_index < len(layout["offers"]):
                return {"type": "select_shop_offer", "offer_id": layout["offers"][option_index]["offer_id"]}
            if layout["selected_offer_id"] == SHOP_PURGE_OFFER_ID and option_index < len(layout["purge_targets"]):
                return {"type": "select_shop_offer", "offer_id": layout["purge_targets"][option_index]["option_id"]}
            return {"type": "notice", "message": "That shop slot is empty.", "level": "error"}

        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if layout["can_purchase"]:
                return {"type": "confirm_shop_purchase"}
            return {"type": "notice", "message": layout["purchase_disabled_reason"], "level": "error"}

        if event.key == pygame.K_r:
            if layout["can_reroll"]:
                return {"type": "reroll_shop_inventory"}
            return {"type": "notice", "message": layout["reroll_disabled_reason"], "level": "error"}

        if event.key == pygame.K_l:
            return {"type": "leave_shop"}

        return None

    def build_layout(self, shop_state: dict[str, Any]) -> dict[str, Any]:
        offers = []
        for index, offer in enumerate(shop_state["shop"]["inventory"]):
            offers.append(
                {
                    **offer,
                    "rect": (42, 190 + (index * 92), 418, 78),
                    "shortcut": index + 1 if index < 9 else None,
                }
            )

        purge_targets = []
        for index, target in enumerate(shop_state["shop"]["purge_targets"]):
            purge_targets.append(
                {
                    **target,
                    "rect": (520 + ((index % 4) * 170), 514 + ((index // 4) * 38), 156, 30),
                    "shortcut": index + 1 if index < 9 else None,
                }
            )

        selected_offer = next(
            (offer for offer in offers if offer["offer_id"] == shop_state["shop"]["selected_offer_id"]),
            None,
        )
        show_purge_targets = (
            selected_offer is not None
            and selected_offer["type"] == "purge"
            and not selected_offer.get("sold_out")
        )
        if selected_offer is None:
            purchase_disabled_reason = "Select a shop offer before purchasing it."
            can_purchase = False
        elif selected_offer.get("sold_out"):
            purchase_disabled_reason = "That shop offer has already been purchased."
            can_purchase = False
        elif selected_offer["type"] == "purge" and shop_state["shop"]["selected_purge_index"] is None:
            purchase_disabled_reason = "Choose a deck card to purge before purchasing the service."
            can_purchase = False
        else:
            purchase_disabled_reason = "Purchase ready."
            can_purchase = True
        return {
            "player_credits": shop_state["player"]["credits"],
            "offers": offers,
            "selected_offer": selected_offer,
            "selected_offer_id": shop_state["shop"]["selected_offer_id"],
            "selected_purge_index": shop_state["shop"]["selected_purge_index"],
            "purge_targets": purge_targets,
            "show_purge_targets": show_purge_targets,
            "purchase_rect": (1056, 636, 168, 48),
            "reroll_rect": (868, 636, 168, 48),
            "leave_rect": (680, 636, 168, 48),
            "can_purchase": can_purchase,
            "purchase_disabled_reason": purchase_disabled_reason,
            "reroll_count": shop_state["shop"].get("reroll_count", 0),
            "reroll_price": shop_state["shop"].get("reroll_price", 0),
            "can_reroll": shop_state["shop"].get("can_reroll", False),
            "reroll_disabled_reason": shop_state["shop"].get("reroll_disabled_reason") or "Reroll unavailable.",
        }

    def render(self, surface: Any, shop_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(shop_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = shop_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(shop_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (1232, 96))
        left_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (438, 430))
        right_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (762, 238))
        lower_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (762, 190))
        card_panel = self._scaled_image(resolve_asset_path("cards", "card_placeholder.png"), (220, 132))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176)
        surface.blit(panel, (24, 96))
        surface.blit(left_panel, (24, 174))
        surface.blit(right_panel, (486, 174))
        surface.blit(lower_panel, (486, 430))

        self._draw_text(surface, "Black Market", (44, 118), self._font)
        self._draw_text(surface, f"Credits: {layout['player_credits']}", (44, 150), self._small_font)
        reroll_label = f"Reroll {layout['reroll_price']} cr"
        self._draw_text(surface, reroll_label, (270, 150), self._small_font, width=240)
        self._draw_text(surface, shop_state["status_message"], (560, 118), self._tiny_font, width=646)
        self._draw_text(surface, "Inventory", (44, 188), self._small_font)

        for offer in layout["offers"]:
            rect = pygame.Rect(*offer["rect"])
            hovered = self._hovered_action == f"offer:{offer['offer_id']}"
            pressed = self._pressed_action == f"offer:{offer['offer_id']}"
            selected = layout["selected_offer_id"] == offer["offer_id"]
            fill = (24, 34, 50)
            if hovered:
                fill = (34, 48, 68)
            if pressed:
                fill = (255, 214, 110)
            border = (255, 214, 110) if selected else (255, 255, 255) if hovered else (190, 205, 230) if high_contrast else (104, 118, 146)
            if offer.get("sold_out"):
                fill = (26, 24, 32)
                border = (120, 88, 100)
            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, border, rect, 2, border_radius=14)
            self._draw_text(surface, offer["label"], (rect.x + 16, rect.y + 12), self._small_font, width=220)
            subtitle = offer.get("description", self._card_summary(offer["card"]) if offer["type"] == "card" else "Remove one card from the deck.")
            self._draw_text(surface, subtitle, (rect.x + 16, rect.y + 40), self._tiny_font, width=260)
            price_label = "Sold Out" if offer.get("sold_out") else f"{offer['price']} cr"
            self._draw_text(surface, price_label, (rect.x + 316, rect.y + 24), self._small_font, width=86)
            if offer["shortcut"] is not None:
                badge_rect = pygame.Rect(rect.x + rect.width - 30, rect.y + 10, 22, 22)
                pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=11)
                pygame.draw.rect(surface, (255, 214, 110), badge_rect, 2, border_radius=11)
                badge = self._tiny_font.render(str(offer["shortcut"]), True, (255, 214, 110))
                surface.blit(badge, badge.get_rect(center=badge_rect.center))

        self._draw_text(surface, "Offer Details", (506, 188), self._small_font)
        selected_offer = layout["selected_offer"]
        if selected_offer is None:
            self._draw_text(surface, "Choose an offer from the list to inspect and buy it.", (506, 226), self._small_font, width=720)
            self._draw_text(surface, "Tip: reroll refreshes only unsold card offers in this shop.", (506, 258), self._tiny_font, width=720)
        elif selected_offer["type"] == "card":
            surface.blit(card_panel, (520, 230))
            self._draw_text(surface, selected_offer["card"]["name"], (536, 246), self._small_font, width=188)
            self._draw_text(surface, self._card_summary(selected_offer["card"]), (536, 278), self._tiny_font, width=188)
            self._draw_text(surface, f"Price: {selected_offer['price']} credits", (766, 236), self._small_font)
            self._draw_text(surface, "Adds this card to the run deck immediately.", (766, 268), self._tiny_font, width=428)
            if selected_offer.get("sold_out"):
                self._draw_text(surface, "Already purchased in this shop.", (766, 300), self._tiny_font, width=428)
            else:
                self._draw_text(surface, "Select Purchase to claim it.", (766, 300), self._tiny_font, width=428)
        else:
            self._draw_text(surface, "Purge Service", (520, 236), self._small_font)
            self._draw_text(surface, f"Price: {selected_offer['price']} credits", (520, 268), self._tiny_font)
            if selected_offer.get("sold_out"):
                self._draw_text(surface, "Already used in this shop.", (520, 300), self._tiny_font, width=660)
            elif layout["selected_purge_index"] is None:
                self._draw_text(surface, "Choose one deck card below, then purchase the service.", (520, 300), self._tiny_font, width=660)
            else:
                self._draw_text(surface, "Target locked in. Purchase to remove that card from the run.", (520, 300), self._tiny_font, width=660)

        self._draw_text(surface, "Shop State", (506, 446), self._small_font)
        self._draw_text(surface, f"Rerolls used here: {layout['reroll_count']}", (520, 480), self._tiny_font)
        if layout["show_purge_targets"]:
            self._draw_text(surface, "Purge Targets", (760, 446), self._small_font)
            for target in layout["purge_targets"]:
                rect = pygame.Rect(*target["rect"])
                hovered = self._hovered_action == f"purge:{target['deck_index']}"
                pressed = self._pressed_action == f"purge:{target['deck_index']}"
                selected = target["selected"]
                fill = (24, 34, 50)
                if hovered:
                    fill = (34, 48, 68)
                if pressed:
                    fill = (255, 214, 110)
                border = (255, 214, 110) if selected else (255, 255, 255) if hovered else (104, 118, 146)
                pygame.draw.rect(surface, fill, rect, border_radius=12)
                pygame.draw.rect(surface, border, rect, 2, border_radius=12)
                self._draw_text(surface, target["card"]["name"], (rect.x + 10, rect.y + 7), self._tiny_font, width=138)
        else:
            reroll_status = "Reroll ready: refresh unsold card offers." if layout["can_reroll"] else layout["reroll_disabled_reason"]
            self._draw_text(surface, reroll_status, (520, 512), self._small_font, width=690)

        self._draw_button(surface, layout["leave_rect"], "Leave", self._hovered_action == "leave", self._pressed_action == "leave", enabled=True)
        self._draw_button(surface, layout["reroll_rect"], f"Reroll {layout['reroll_price']}", self._hovered_action == "reroll", self._pressed_action == "reroll", enabled=layout["can_reroll"])
        self._draw_button(surface, layout["purchase_rect"], "Purchase", self._hovered_action == "purchase", self._pressed_action == "purchase", enabled=layout["can_purchase"])

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "purchase":
            if not layout["can_purchase"]:
                return {"type": "notice", "message": layout["purchase_disabled_reason"], "level": "error"}
            return {"type": "confirm_shop_purchase"}
        if action_id == "reroll":
            if not layout["can_reroll"]:
                return {"type": "notice", "message": layout["reroll_disabled_reason"], "level": "error"}
            return {"type": "reroll_shop_inventory"}
        if action_id == "leave":
            return {"type": "leave_shop"}
        if action_id.startswith("offer:"):
            return {"type": "select_shop_offer", "offer_id": action_id.removeprefix("offer:")}
        if action_id.startswith("purge:"):
            return {"type": "select_shop_offer", "offer_id": f"purge_target:{action_id.removeprefix('purge:')}"}
        return {"type": "notice", "message": "Unknown shop action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for offer in layout["offers"]:
            if point_in_rect(position, offer["rect"]):
                return f"offer:{offer['offer_id']}"
        if layout["show_purge_targets"]:
            for target in layout["purge_targets"]:
                if point_in_rect(position, target["rect"]):
                    return f"purge:{target['deck_index']}"
        if layout["can_purchase"] and point_in_rect(position, layout["purchase_rect"]):
            return "purchase"
        if layout["can_reroll"] and point_in_rect(position, layout["reroll_rect"]):
            return "reroll"
        if point_in_rect(position, layout["leave_rect"]):
            return "leave"
        return None

    def _card_summary(self, card: dict[str, Any]) -> str:
        effect_text = ", ".join(f"{effect['type']} {effect['value']}" for effect in card["effects"])
        return f"Cost {card['cost']} | {effect_text}"

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
            raise RuntimeError("Pygame is required to load shop UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((90, 180, 140, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_shop_ui() -> dict[str, Any]:
    ui = ShopUI()
    return ui.build_layout(
        {
            "shop": {
                "inventory": [
                    {
                        "offer_id": "card:surge_strike_01",
                        "type": "card",
                        "card": {
                            "id": "surge_strike_01",
                            "name": "Surge Strike",
                            "cost": 2,
                            "effects": [{"type": "damage", "value": 12}],
                        },
                        "label": "Surge Strike",
                        "price": 55,
                        "sold_out": False,
                    },
                    {
                        "offer_id": "purge_service",
                        "type": "purge",
                        "label": "Purge Service",
                        "description": "Remove one card from the deck.",
                        "price": 45,
                        "sold_out": False,
                    },
                ],
                "selected_offer_id": "purge_service",
                "selected_purge_index": 0,
                "purge_targets": [
                    {
                        "option_id": "purge_target:0",
                        "deck_index": 0,
                        "card": {"id": "strike_01", "name": "Strike"},
                        "selected": True,
                    }
                ],
            },
            "player": {"credits": 80},
            "presentation": {"ui_scale": 1.0},
        }
    )
