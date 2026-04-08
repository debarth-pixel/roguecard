from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.card_renderer import compact_card_summary
from ui.card_style import resolve_card_theme
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


SHOP_LAYOUT = {
    "header_rect": (56, 62, 1168, 84),
    "canvas_rect": (56, 172, 1168, 438),
    "footer_rect": (56, 632, 1168, 56),
    "content_padding": 18,
    "offer_columns": 2,
    "offer_height": 98,
    "offer_gap_x": 18,
    "offer_gap_y": 14,
    "purge_tray_gap": 14,
    "purge_columns": 6,
    "purge_chip_height": 30,
    "purge_chip_gap_x": 10,
    "purge_chip_gap_y": 8,
}

SERVICE_THEMES = {
    "heal": {
        "fill": (20, 52, 66),
        "fill_hover": (28, 70, 88),
        "fill_selected": (34, 82, 102),
        "border": (110, 216, 186),
        "muted": (166, 206, 198),
        "pill": (110, 216, 186),
    },
    "purge": {
        "fill": (54, 26, 34),
        "fill_hover": (70, 34, 42),
        "fill_selected": (86, 42, 54),
        "border": (255, 148, 124),
        "muted": (222, 188, 182),
        "pill": (255, 148, 124),
    },
}


class ShopUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._micro_font = None
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
            if layout["show_purge_targets"] and option_index < len(layout["purge_targets"]):
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
        header_rect = pygame.Rect(*SHOP_LAYOUT["header_rect"]) if pygame is not None else _rect_tuple_to_dict(SHOP_LAYOUT["header_rect"])
        canvas_rect = pygame.Rect(*SHOP_LAYOUT["canvas_rect"]) if pygame is not None else _rect_tuple_to_dict(SHOP_LAYOUT["canvas_rect"])
        footer_rect = pygame.Rect(*SHOP_LAYOUT["footer_rect"]) if pygame is not None else _rect_tuple_to_dict(SHOP_LAYOUT["footer_rect"])

        if pygame is not None:
            content_rect = canvas_rect.inflate(-SHOP_LAYOUT["content_padding"] * 2, -SHOP_LAYOUT["content_padding"] * 2)
            offer_width = (content_rect.width - SHOP_LAYOUT["offer_gap_x"]) // SHOP_LAYOUT["offer_columns"]
            offer_rects = []
            for index in range(len(shop_state["shop"]["inventory"])):
                row = index // SHOP_LAYOUT["offer_columns"]
                col = index % SHOP_LAYOUT["offer_columns"]
                offer_rects.append(
                    pygame.Rect(
                        content_rect.x + (col * (offer_width + SHOP_LAYOUT["offer_gap_x"])),
                        content_rect.y + (row * (SHOP_LAYOUT["offer_height"] + SHOP_LAYOUT["offer_gap_y"])),
                        offer_width,
                        SHOP_LAYOUT["offer_height"],
                    )
                )
        else:
            content_rect = _inflate_rect_tuple(SHOP_LAYOUT["canvas_rect"], -SHOP_LAYOUT["content_padding"] * 2, -SHOP_LAYOUT["content_padding"] * 2)
            offer_width = (content_rect["width"] - SHOP_LAYOUT["offer_gap_x"]) // SHOP_LAYOUT["offer_columns"]
            offer_rects = []
            for index in range(len(shop_state["shop"]["inventory"])):
                row = index // SHOP_LAYOUT["offer_columns"]
                col = index % SHOP_LAYOUT["offer_columns"]
                offer_rects.append(
                    (
                        content_rect["x"] + (col * (offer_width + SHOP_LAYOUT["offer_gap_x"])),
                        content_rect["y"] + (row * (SHOP_LAYOUT["offer_height"] + SHOP_LAYOUT["offer_gap_y"])),
                        offer_width,
                        SHOP_LAYOUT["offer_height"],
                    )
                )

        offers = []
        for index, offer in enumerate(shop_state["shop"]["inventory"]):
            offers.append(
                {
                    **offer,
                    "rect": tuple(offer_rects[index]) if pygame is not None else offer_rects[index],
                    "shortcut": index + 1 if index < 9 else None,
                    "summary": self._offer_summary(offer),
                    "theme": self._offer_theme(offer),
                }
            )

        selected_offer = next((offer for offer in offers if offer["offer_id"] == shop_state["shop"]["selected_offer_id"]), None)
        show_purge_targets = bool(
            selected_offer is not None and selected_offer["type"] == "purge" and not selected_offer.get("sold_out")
        )
        player_credits = shop_state["player"]["credits"]
        player_current_hp = shop_state["player"]["current_hp"]
        player_max_hp = shop_state["player"]["max_hp"]

        if selected_offer is None:
            purchase_disabled_reason = "Select a shop offer before purchasing it."
            can_purchase = False
        elif selected_offer.get("sold_out"):
            purchase_disabled_reason = "That shop offer has already been purchased."
            can_purchase = False
        elif selected_offer["price"] > player_credits:
            purchase_disabled_reason = f"Requires {selected_offer['price']} credits."
            can_purchase = False
        elif selected_offer["type"] == "purge" and shop_state["shop"]["selected_purge_index"] is None:
            purchase_disabled_reason = "Choose a deck card to purge before purchasing the service."
            can_purchase = False
        elif selected_offer["type"] == "heal" and player_current_hp >= player_max_hp:
            purchase_disabled_reason = "Heal service is only available below max HP."
            can_purchase = False
        else:
            purchase_disabled_reason = "Purchase ready."
            can_purchase = True

        if pygame is not None:
            content_rect = canvas_rect.inflate(-SHOP_LAYOUT["content_padding"] * 2, -SHOP_LAYOUT["content_padding"] * 2)
            last_offer_rect = pygame.Rect(*offers[-1]["rect"]) if offers else pygame.Rect(content_rect.x, content_rect.y, 0, 0)
            purge_tray_y = last_offer_rect.bottom + SHOP_LAYOUT["purge_tray_gap"]
            purge_tray_height = max(
                88,
                32
                + (
                    ((len(shop_state["shop"]["purge_targets"]) - 1) // SHOP_LAYOUT["purge_columns"] + 1)
                    * (SHOP_LAYOUT["purge_chip_height"] + SHOP_LAYOUT["purge_chip_gap_y"])
                ),
            ) if show_purge_targets and shop_state["shop"]["purge_targets"] else 0
            purge_tray_rect = pygame.Rect(content_rect.x, purge_tray_y, content_rect.width, purge_tray_height) if show_purge_targets else None
        else:
            content_rect = _inflate_rect_tuple(SHOP_LAYOUT["canvas_rect"], -SHOP_LAYOUT["content_padding"] * 2, -SHOP_LAYOUT["content_padding"] * 2)
            last_offer_rect = offers[-1]["rect"] if offers else (content_rect["x"], content_rect["y"], 0, 0)
            purge_tray_y = last_offer_rect[1] + last_offer_rect[3] + SHOP_LAYOUT["purge_tray_gap"]
            purge_tray_height = max(
                88,
                32
                + (
                    ((len(shop_state["shop"]["purge_targets"]) - 1) // SHOP_LAYOUT["purge_columns"] + 1)
                    * (SHOP_LAYOUT["purge_chip_height"] + SHOP_LAYOUT["purge_chip_gap_y"])
                ),
            ) if show_purge_targets and shop_state["shop"]["purge_targets"] else 0
            purge_tray_rect = (content_rect["x"], purge_tray_y, content_rect["width"], purge_tray_height) if show_purge_targets else None

        purge_targets = []
        if purge_tray_rect is not None:
            if pygame is not None:
                tray_rect = purge_tray_rect.inflate(-16, -16)
                chip_width = (tray_rect.width - (SHOP_LAYOUT["purge_chip_gap_x"] * (SHOP_LAYOUT["purge_columns"] - 1))) // SHOP_LAYOUT["purge_columns"]
                for index, target in enumerate(shop_state["shop"]["purge_targets"]):
                    row = index // SHOP_LAYOUT["purge_columns"]
                    col = index % SHOP_LAYOUT["purge_columns"]
                    purge_targets.append(
                        {
                            **target,
                            "rect": (
                                tray_rect.x + (col * (chip_width + SHOP_LAYOUT["purge_chip_gap_x"])),
                                tray_rect.y + (row * (SHOP_LAYOUT["purge_chip_height"] + SHOP_LAYOUT["purge_chip_gap_y"])),
                                chip_width,
                                SHOP_LAYOUT["purge_chip_height"],
                            ),
                            "shortcut": index + 1 if index < 9 else None,
                        }
                    )
            else:
                tray_rect = _inflate_rect_tuple(purge_tray_rect, -16, -16)
                chip_width = (tray_rect["width"] - (SHOP_LAYOUT["purge_chip_gap_x"] * (SHOP_LAYOUT["purge_columns"] - 1))) // SHOP_LAYOUT["purge_columns"]
                for index, target in enumerate(shop_state["shop"]["purge_targets"]):
                    row = index // SHOP_LAYOUT["purge_columns"]
                    col = index % SHOP_LAYOUT["purge_columns"]
                    purge_targets.append(
                        {
                            **target,
                            "rect": (
                                tray_rect["x"] + (col * (chip_width + SHOP_LAYOUT["purge_chip_gap_x"])),
                                tray_rect["y"] + (row * (SHOP_LAYOUT["purge_chip_height"] + SHOP_LAYOUT["purge_chip_gap_y"])),
                                chip_width,
                                SHOP_LAYOUT["purge_chip_height"],
                            ),
                            "shortcut": index + 1 if index < 9 else None,
                        }
                    )

        buttons = self._build_buttons(footer_rect, selected_offer, can_purchase, shop_state)
        return {
            "player_credits": player_credits,
            "player_current_hp": player_current_hp,
            "player_max_hp": player_max_hp,
            "offers": offers,
            "selected_offer": selected_offer,
            "selected_offer_id": shop_state["shop"]["selected_offer_id"],
            "selected_purge_index": shop_state["shop"]["selected_purge_index"],
            "purge_targets": purge_targets,
            "show_purge_targets": show_purge_targets,
            "can_purchase": can_purchase,
            "purchase_disabled_reason": purchase_disabled_reason,
            "reroll_count": shop_state["shop"].get("reroll_count", 0),
            "reroll_price": shop_state["shop"].get("reroll_price", 0),
            "can_reroll": shop_state["shop"].get("can_reroll", False),
            "reroll_disabled_reason": shop_state["shop"].get("reroll_disabled_reason") or "Reroll unavailable.",
            "buttons": buttons,
            "header_rect": tuple(header_rect) if pygame is not None else SHOP_LAYOUT["header_rect"],
            "canvas_rect": tuple(canvas_rect) if pygame is not None else SHOP_LAYOUT["canvas_rect"],
            "footer_rect": tuple(footer_rect) if pygame is not None else SHOP_LAYOUT["footer_rect"],
            "purge_tray_rect": tuple(purge_tray_rect) if pygame is not None and purge_tray_rect is not None else purge_tray_rect,
        }

    def render(self, surface: Any, shop_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(shop_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = shop_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(shop_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (64, 64))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=166)

        canvas_rect = pygame.Rect(*layout["canvas_rect"])
        footer_rect = pygame.Rect(*layout["footer_rect"])
        self._draw_panel(surface, panel, canvas_rect, border=(72, 96, 138), alpha=230)
        self._draw_footer_bar(surface, footer_rect)

        self._draw_text(surface, "Black Market", (56, 66), self._font)
        self._draw_text(surface, "Contracts and services on the wire.", (56, 100), self._tiny_font, color=(196, 212, 232))
        self._draw_stat_chip(surface, f"{layout['player_credits']} cr", (960, 72), width=118, accent=(255, 214, 110))
        self._draw_stat_chip(surface, f"{layout['player_current_hp']}/{layout['player_max_hp']} HP", (1088, 72), width=136, accent=(236, 110, 124))

        for offer in layout["offers"]:
            self._draw_offer_tile(surface, offer, layout, high_contrast=high_contrast)

        if layout["purge_tray_rect"] is not None:
            self._draw_purge_tray(surface, layout)

        for button in layout["buttons"]:
            self._draw_button(
                surface,
                button["rect"],
                button["label"],
                self._hovered_action == button["action_id"],
                self._pressed_action == button["action_id"],
                enabled=button["enabled"],
                kind=button["kind"],
            )

    def _build_buttons(
        self,
        footer_rect: pygame.Rect | dict[str, int],
        selected_offer: dict[str, Any] | None,
        can_purchase: bool,
        shop_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if pygame is None:
            footer_width = footer_rect["width"]
            footer_x = footer_rect["x"]
            footer_y = footer_rect["y"]
        else:
            footer_width = footer_rect.width
            footer_x = footer_rect.x
            footer_y = footer_rect.y

        leave_rect = (footer_x + footer_width - 176, footer_y + 5, 160, 46)
        if selected_offer is None:
            return [{"action_id": "leave", "label": "Leave", "rect": leave_rect, "enabled": True, "kind": "secondary"}]

        return [
            {
                "action_id": "purchase",
                "label": self._purchase_label(selected_offer, can_purchase, shop_state),
                "rect": (footer_x + footer_width - 560, footer_y + 5, 180, 46),
                "enabled": can_purchase,
                "kind": "primary",
            },
            {
                "action_id": "reroll",
                "label": f"Reroll {shop_state['shop'].get('reroll_price', 0)}",
                "rect": (footer_x + footer_width - 364, footer_y + 5, 172, 46),
                "enabled": shop_state["shop"].get("can_reroll", False),
                "kind": "secondary",
            },
            {"action_id": "leave", "label": "Leave", "rect": leave_rect, "enabled": True, "kind": "secondary"},
        ]

    def _purchase_label(self, selected_offer: dict[str, Any], can_purchase: bool, shop_state: dict[str, Any]) -> str:
        if selected_offer.get("sold_out"):
            return "Sold Out"
        if not can_purchase:
            if selected_offer["type"] == "purge" and shop_state["shop"]["selected_purge_index"] is None:
                return "Pick Card"
            if selected_offer["type"] == "heal" and shop_state["player"]["current_hp"] >= shop_state["player"]["max_hp"]:
                return "At Full HP"
            if selected_offer["price"] > shop_state["player"]["credits"]:
                return f"Need {selected_offer['price']}"
        return f"Buy {selected_offer['price']}"

    def _draw_offer_tile(
        self,
        surface: Any,
        offer: dict[str, Any],
        layout: dict[str, Any],
        *,
        high_contrast: bool,
    ) -> None:
        rect = pygame.Rect(*offer["rect"])
        hovered = self._hovered_action == f"offer:{offer['offer_id']}"
        pressed = self._pressed_action == f"offer:{offer['offer_id']}"
        selected = layout["selected_offer_id"] == offer["offer_id"]
        available = not offer.get("sold_out")
        draw_rect = rect.move(0, -4 if hovered and available else 0)

        fill = offer["theme"]["fill_hover"] if hovered and available else offer["theme"]["fill"]
        border = offer["theme"]["border"]
        if selected:
            fill = offer["theme"]["fill_selected"]
        if pressed and available:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        if high_contrast and available and not selected:
            border = (230, 238, 248)
        if offer.get("sold_out"):
            fill = (22, 24, 30)
            border = (108, 92, 104)

        pygame.draw.rect(surface, fill, draw_rect, border_radius=18)
        pygame.draw.rect(surface, border, draw_rect, 2, border_radius=18)

        badge_rect = pygame.Rect(draw_rect.x + 14, draw_rect.y + 14, 44, 44)
        pygame.draw.rect(surface, offer["theme"]["pill"], badge_rect, border_radius=14)
        badge_surface = self._micro_font.render(self._offer_badge(offer), True, (14, 20, 32))
        surface.blit(badge_surface, badge_surface.get_rect(center=badge_rect.center))

        title_color = (16, 24, 36) if pressed and available else (244, 248, 255) if available else (172, 180, 194)
        body_color = (28, 36, 46) if pressed and available else offer["theme"]["muted"]
        self._draw_text(surface, offer["label"], (draw_rect.x + 74, draw_rect.y + 16), self._small_font, width=draw_rect.width - 212, color=title_color)
        self._draw_text(surface, offer["summary"], (draw_rect.x + 74, draw_rect.y + 46), self._tiny_font, width=draw_rect.width - 212, color=body_color)

        price_rect = pygame.Rect(draw_rect.right - 124, draw_rect.y + 16, 100, 30)
        pygame.draw.rect(surface, (16, 24, 38), price_rect, border_radius=15)
        pygame.draw.rect(surface, border, price_rect, 2, border_radius=15)
        price_text = "Sold Out" if offer.get("sold_out") else f"{offer['price']} cr"
        price_surface = self._tiny_font.render(price_text, True, title_color if pressed and available else (236, 242, 250))
        surface.blit(price_surface, price_surface.get_rect(center=price_rect.center))

        if offer["shortcut"] is not None:
            shortcut_rect = pygame.Rect(draw_rect.right - 38, draw_rect.bottom - 34, 24, 24)
            pygame.draw.rect(surface, (16, 24, 38), shortcut_rect, border_radius=12)
            pygame.draw.rect(surface, border, shortcut_rect, 2, border_radius=12)
            shortcut_surface = self._micro_font.render(str(offer["shortcut"]), True, border)
            surface.blit(shortcut_surface, shortcut_surface.get_rect(center=shortcut_rect.center))

    def _draw_purge_tray(self, surface: Any, layout: dict[str, Any]) -> None:
        tray_rect = pygame.Rect(*layout["purge_tray_rect"])
        pygame.draw.rect(surface, (14, 18, 28), tray_rect, border_radius=18)
        pygame.draw.rect(surface, (255, 148, 124), tray_rect, 2, border_radius=18)
        self._draw_text(surface, "Purge Target", (tray_rect.x + 16, tray_rect.y + 10), self._tiny_font, color=(255, 216, 206))

        for target in layout["purge_targets"]:
            rect = pygame.Rect(*target["rect"])
            hovered = self._hovered_action == f"purge:{target['deck_index']}"
            pressed = self._pressed_action == f"purge:{target['deck_index']}"
            selected = target["selected"]
            fill = (34, 42, 58) if hovered else (24, 30, 42)
            border = (238, 244, 255) if hovered else (112, 128, 152)
            if selected:
                fill = (82, 42, 46)
                border = (255, 214, 110)
            if pressed:
                fill = (255, 214, 110)
                border = (255, 214, 110)
            pygame.draw.rect(surface, fill, rect, border_radius=12)
            pygame.draw.rect(surface, border, rect, 2, border_radius=12)
            text_color = (18, 24, 36) if pressed else (236, 242, 250)
            self._draw_text(surface, target["card"]["name"], (rect.x + 10, rect.y + 6), self._micro_font, width=rect.width - 20, color=text_color)

    def _draw_footer_bar(self, surface: Any, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, (12, 18, 30), rect, border_radius=18)
        pygame.draw.rect(surface, (72, 94, 126), rect, 2, border_radius=18)

    def _draw_panel(self, surface: Any, panel_image: Any, rect: pygame.Rect, *, border: tuple[int, int, int], alpha: int) -> None:
        panel = pygame.transform.smoothscale(panel_image, rect.size).copy()
        panel.set_alpha(alpha)
        surface.blit(panel, rect.topleft)
        pygame.draw.rect(surface, border, rect, 2, border_radius=24)

    def _offer_badge(self, offer: dict[str, Any]) -> str:
        if offer["type"] == "card":
            return {"attack": "ATK", "skill": "SKL", "power": "PWR"}.get(offer["card"].get("type", "card"), "CRD")
        return "HP" if offer["type"] == "heal" else "DEL"

    def _offer_summary(self, offer: dict[str, Any]) -> str:
        if offer["type"] == "card":
            return compact_card_summary(offer["card"])
        return offer.get("description", "Service")

    def _offer_theme(self, offer: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
        if offer["type"] == "card":
            type_theme = resolve_card_theme(offer["card"])["type_theme"]
            return {
                "fill": type_theme["body_fill"],
                "fill_hover": type_theme["mid_band_fill"],
                "fill_selected": type_theme["outer_fill"],
                "border": type_theme["accent"],
                "muted": type_theme["muted"],
                "pill": type_theme["accent_soft"],
            }
        return SERVICE_THEMES.get(offer["type"], SERVICE_THEMES["heal"])

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
        for button in layout["buttons"]:
            if point_in_rect(position, button["rect"]):
                return button["action_id"]
        return None

    def _draw_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        hovered: bool,
        pressed: bool,
        enabled: bool,
        *,
        kind: str,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        if kind == "primary":
            fill = (46, 110, 186) if enabled else (32, 38, 52)
            border = (238, 244, 255) if enabled else (112, 124, 144)
        else:
            fill = (20, 30, 46) if enabled else (22, 28, 38)
            border = (160, 176, 202) if enabled else (96, 106, 122)
        if hovered and enabled:
            fill = (64, 132, 214) if kind == "primary" else (34, 48, 72)
        if pressed and enabled:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        pygame.draw.rect(surface, fill, rect, border_radius=14)
        pygame.draw.rect(surface, border, rect, 2, border_radius=14)
        text_color = (240, 245, 255) if enabled and not pressed else (18, 24, 36) if pressed else (156, 166, 184)
        label_surface = self._tiny_font.render(label, True, text_color)
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_stat_chip(self, surface: Any, text: str, position: tuple[int, int], *, width: int, accent: tuple[int, int, int]) -> None:
        rect = pygame.Rect(position[0], position[1], width, 28)
        pygame.draw.rect(surface, (14, 20, 30), rect, border_radius=14)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=14)
        label_surface = self._tiny_font.render(text, True, (238, 244, 255))
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
        color: tuple[int, int, int] = (238, 244, 255),
    ) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return
        self._font_scale = scale
        self._font = pygame.font.SysFont("consolas", max(24, int(30 * scale)), bold=True)
        self._small_font = pygame.font.SysFont("consolas", max(17, int(21 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(13, int(16 * scale)))
        self._micro_font = pygame.font.SysFont("consolas", max(11, int(13 * scale)))

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


def _rect_tuple_to_dict(rect: tuple[int, int, int, int]) -> dict[str, int]:
    return {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]}


def _inflate_rect_tuple(rect: tuple[int, int, int, int], delta_x: int, delta_y: int) -> dict[str, int]:
    return {"x": rect[0] - (delta_x // 2), "y": rect[1] - (delta_y // 2), "width": rect[2] + delta_x, "height": rect[3] + delta_y}


def simulate_shop_ui() -> dict[str, Any]:
    ui = ShopUI()
    return ui.build_layout(
        {
            "shop": {
                "inventory": [
                    {
                        "offer_id": "card:surge_strike_01",
                        "type": "card",
                        "card": {"id": "surge_strike_01", "name": "Surge Strike", "cost": 2, "type": "attack", "effects": [{"type": "damage", "value": 12}]},
                        "label": "Surge Strike",
                        "price": 55,
                        "sold_out": False,
                    },
                    {"offer_id": "purge_service", "type": "purge", "label": "Purge Service", "description": "Remove one card.", "price": 45, "sold_out": False},
                ],
                "selected_offer_id": "purge_service",
                "selected_purge_index": 0,
                "purge_targets": [{"option_id": "purge_target:0", "deck_index": 0, "card": {"id": "strike_01", "name": "Strike"}, "selected": True}],
                "reroll_price": 18,
                "can_reroll": True,
                "reroll_disabled_reason": None,
            },
            "player": {"credits": 80, "current_hp": 52, "max_hp": 70},
            "presentation": {"ui_scale": 1.0},
        }
    )
