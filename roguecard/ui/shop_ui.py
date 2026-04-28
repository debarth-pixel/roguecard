from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    MAX_UI_SCALE,
    MIN_UI_SCALE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHOP_CLEANSE_OFFER_ID,
    SHOP_HEAL_AMOUNT,
    SHOP_HEAL_OFFER_ID,
    SHOP_PURGE_OFFER_ID,
    resolve_art_path,
)
from ui.card_renderer import draw_card
from ui.card_style import fit_portrait_card, resolve_card_theme
from ui.encounter_backgrounds import resolve_encounter_background_path
from ui.relic_assets import relic_assets
from ui.render_utils import clamp_scale, draw_wrapped_text, point_in_rect
from ui.ui_system import (
    COLOR_GOLD,
    COLOR_LINE,
    COLOR_LINE_SOFT,
    COLOR_MUTED,
    COLOR_PANEL_ELEVATED,
    COLOR_RED,
    COLOR_TEXT,
    RADIUS_LG,
    RADIUS_MD,
    draw_chip,
    draw_panel,
)

MERCHANT_VAN_ART_PATH = resolve_art_path("merchant_van.png")
MERCHANT_VAN_ART_SIZE = (1672, 941)
BOOT_DURATION_SECONDS = 3.0
DENIAL_FLASH_SECONDS = 0.28

MERCHANT_SFX_CUES = {
    "terminal_boot": "merchant_terminal_boot",
    "button_hover": "merchant_button_hover",
    "button_click": "merchant_button_click",
    "purchase_success": "merchant_purchase_success",
    "purchase_fail": "merchant_purchase_fail",
    "purge_confirm": "merchant_purge_confirm",
    "cleanse_confirm": "merchant_cleanse_confirm",
    "logout": "merchant_logout",
}

MERCHANT_VAN_LAYOUT = {
    "terminal_rect": (276, 180, 420, 488),
    "terminal_padding": 20,
    "terminal_title_height": 36,
    "terminal_gap": 12,
    "terminal_logout_height": 54,
    "terminal_button_height": 46,
    "shelf_region": (856, 620, 516, 182),
    "status_rect": (116, 60, 520, 44),
    "relic_tooltip_rect": (908, 420, 408, 176),
    "purge_window_rect": (152, 96, 1124, 522),
}

TERMINAL_THEMES = {
    "boot": {
        "top": (10, 22, 42),
        "bottom": (4, 10, 24),
        "accent": (86, 188, 255),
        "accent_soft": (34, 86, 140),
        "panel": (10, 22, 40),
        "button": (24, 70, 128),
        "button_hover": (42, 108, 178),
        "button_disabled": (18, 24, 34),
        "text": (228, 240, 255),
        "muted": (138, 170, 204),
    },
    "main_menu": {
        "top": (10, 24, 46),
        "bottom": (4, 12, 28),
        "accent": (98, 196, 255),
        "accent_soft": (42, 88, 140),
        "panel": (10, 20, 36),
        "button": (30, 84, 148),
        "button_hover": (48, 118, 188),
        "button_disabled": (18, 24, 34),
        "text": (236, 244, 255),
        "muted": (154, 182, 214),
    },
    "purchase": {
        "top": (10, 24, 46),
        "bottom": (4, 12, 28),
        "accent": (98, 196, 255),
        "accent_soft": (42, 88, 140),
        "panel": (10, 20, 36),
        "button": (30, 84, 148),
        "button_hover": (48, 118, 188),
        "button_disabled": (18, 24, 34),
        "text": (236, 244, 255),
        "muted": (154, 182, 214),
    },
    "purge": {
        "top": (64, 16, 22),
        "bottom": (28, 8, 12),
        "accent": (236, 108, 124),
        "accent_soft": (118, 42, 58),
        "panel": (24, 8, 12),
        "button": (126, 34, 46),
        "button_hover": (162, 44, 60),
        "button_disabled": (42, 18, 22),
        "text": (255, 236, 240),
        "muted": (226, 164, 174),
    },
    "cleanse": {
        "top": (12, 42, 34),
        "bottom": (8, 20, 16),
        "accent": (122, 226, 182),
        "accent_soft": (40, 104, 82),
        "panel": (8, 22, 18),
        "button": (28, 92, 72),
        "button_hover": (44, 126, 98),
        "button_disabled": (18, 30, 26),
        "text": (236, 252, 244),
        "muted": (168, 216, 194),
    },
}

RELIC_PALETTES = {
    "common": {
        "fill": (34, 42, 54),
        "fill_hover": (46, 58, 74),
        "border": (146, 186, 240),
        "accent": (166, 208, 255),
        "muted": (202, 214, 232),
    },
    "uncommon": {
        "fill": (28, 50, 44),
        "fill_hover": (40, 66, 58),
        "border": (130, 214, 176),
        "accent": (154, 236, 196),
        "muted": (196, 226, 214),
    },
    "rare": {
        "fill": (54, 38, 20),
        "fill_hover": (72, 50, 28),
        "border": (238, 188, 112),
        "accent": (255, 216, 132),
        "muted": (242, 220, 190),
    },
    "boss": {
        "fill": (60, 24, 20),
        "fill_hover": (82, 34, 28),
        "border": (244, 208, 132),
        "accent": (255, 228, 166),
        "muted": (248, 228, 200),
    },
}

CARD_TYPE_BADGES = {
    "attack": "ATK",
    "skill": "SKL",
    "power": "PWR",
    "status": "STS",
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _ease_out_cubic(progress: float) -> float:
    progress = _clamp(progress, 0.0, 1.0)
    inverse = 1.0 - progress
    return 1.0 - (inverse * inverse * inverse)


def _rect_from_art(rect: tuple[int, int, int, int], screen_size: tuple[int, int]) -> tuple[int, int, int, int]:
    scale_x = screen_size[0] / MERCHANT_VAN_ART_SIZE[0]
    scale_y = screen_size[1] / MERCHANT_VAN_ART_SIZE[1]
    return (
        int(round(rect[0] * scale_x)),
        int(round(rect[1] * scale_y)),
        max(1, int(round(rect[2] * scale_x))),
        max(1, int(round(rect[3] * scale_y))),
    )


def _inset_rect(rect: tuple[int, int, int, int], inset_x: int, inset_y: int) -> tuple[int, int, int, int]:
    return (
        rect[0] + inset_x,
        rect[1] + inset_y,
        max(1, rect[2] - (inset_x * 2)),
        max(1, rect[3] - (inset_y * 2)),
    )


def _rect_top(rect: tuple[int, int, int, int], height: int) -> tuple[int, int, int, int]:
    return (rect[0], rect[1], rect[2], height)


def _rect_bottom(rect: tuple[int, int, int, int], height: int) -> tuple[int, int, int, int]:
    return (rect[0], rect[1] + rect[3] - height, rect[2], height)


def _centered_rect(center_x: int, center_y: int, width: int, height: int) -> tuple[int, int, int, int]:
    return (int(round(center_x - (width / 2))), int(round(center_y - (height / 2))), width, height)


def _stack_vertical(
    rect: tuple[int, int, int, int],
    item_count: int,
    *,
    height: int,
    gap: int,
) -> list[tuple[int, int, int, int]]:
    return [
        (rect[0], rect[1] + (index * (height + gap)), rect[2], height)
        for index in range(item_count)
    ]


def _split_grid(
    rect: tuple[int, int, int, int],
    columns: int,
    rows: int,
    gap_x: int,
    gap_y: int,
) -> list[tuple[int, int, int, int]]:
    if columns <= 0 or rows <= 0:
        return []
    cell_width = max(1, int((rect[2] - (gap_x * (columns - 1))) / columns))
    cell_height = max(1, int((rect[3] - (gap_y * (rows - 1))) / rows))
    result: list[tuple[int, int, int, int]] = []
    for row in range(rows):
        for column in range(columns):
            result.append(
                (
                    rect[0] + (column * (cell_width + gap_x)),
                    rect[1] + (row * (cell_height + gap_y)),
                    cell_width,
                    cell_height,
                )
            )
    return result


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
        self._last_hover_action: str | None = None
        self._session_shop_node_id: str | None = None
        self._boot_elapsed = 0.0
        self._boot_started = False
        self._terminal_clock = 0.0
        self._denial_flash = 0.0
        self._sfx_callback: Callable[[str], None] | None = None
        self._last_surface_size: tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT)

    def preload_assets(self) -> None:
        if pygame is None:
            return
        # Warm the decoded art without running the expensive cutout prep on boot.
        # That keeps launch responsive while still avoiding a cold disk load later.
        self._load_image(MERCHANT_VAN_ART_PATH)

    def set_sfx_callback(self, callback: Callable[[str], None] | None) -> None:
        self._sfx_callback = callback

    def reset_session(self) -> None:
        self._hovered_action = None
        self._pressed_action = None
        self._last_hover_action = None
        self._session_shop_node_id = None
        self._boot_elapsed = 0.0
        self._boot_started = False
        self._denial_flash = 0.0

    def update(
        self,
        delta_time: float,
        shop_state: dict[str, Any] | None = None,
        *,
        transition_active: bool = False,
    ) -> None:
        self._terminal_clock += max(0.0, delta_time)
        self._denial_flash = max(0.0, self._denial_flash - max(0.0, delta_time))

        if not isinstance(shop_state, dict) or shop_state.get("shop") is None:
            self.reset_session()
            return

        shop_node_id = shop_state["shop"].get("shop_node_id")
        if shop_node_id != self._session_shop_node_id:
            self._session_shop_node_id = shop_node_id
            self._boot_elapsed = 0.0
            self._boot_started = False
            self._hovered_action = None
            self._pressed_action = None
            self._last_hover_action = None

        if transition_active:
            return

        if self._boot_elapsed < BOOT_DURATION_SECONDS:
            if not self._boot_started:
                self._boot_started = True
                self._emit_sfx("terminal_boot")
            self._boot_elapsed = min(BOOT_DURATION_SECONDS, self._boot_elapsed + max(0.0, delta_time))

    def handle_snapshot_feedback(
        self,
        action_type: str,
        before_shop_state: dict[str, Any] | None,
        after_shop_state: dict[str, Any] | None,
    ) -> None:
        if action_type == "leave_shop":
            self._emit_sfx("logout")
            if after_shop_state is None:
                self.reset_session()
            return

        if action_type not in {"confirm_shop_purchase", "purchase_shop_offer", "confirm_shop_cleanse"}:
            return

        if before_shop_state is not None:
            selected_offer_id = before_shop_state["shop"].get("selected_offer_id")
            menu_id = before_shop_state["shop"].get("merchant_menu")
            if action_type == "confirm_shop_cleanse" or selected_offer_id == SHOP_CLEANSE_OFFER_ID:
                self._emit_sfx("cleanse_confirm")
            elif menu_id == "purge" or selected_offer_id == SHOP_PURGE_OFFER_ID:
                self._emit_sfx("purge_confirm")
        self._emit_sfx("purchase_success")

    def handle_action_denied(self, action_type: str) -> None:
        if action_type not in {"confirm_shop_purchase", "purchase_shop_offer", "confirm_shop_cleanse", "reroll_shop_inventory"}:
            return
        self._denial_flash = DENIAL_FLASH_SECONDS
        self._emit_sfx("purchase_fail")

    def handle_event(
        self,
        event: Any,
        shop_state: dict[str, Any],
        screen_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(shop_state, self._last_surface_size if screen_size is None else screen_size)

        if event.type == pygame.MOUSEMOTION:
            hovered_action = self._action_at_position(layout, event.pos)
            if (
                hovered_action != self._last_hover_action
                and hovered_action is not None
                and self._action_supports_hover_sfx(layout, hovered_action)
            ):
                self._emit_sfx("button_hover")
            self._last_hover_action = hovered_action
            self._hovered_action = hovered_action
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed_action = self._action_at_position(layout, event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            released_action = self._action_at_position(layout, event.pos)
            pressed_action = self._pressed_action
            self._pressed_action = None
            if released_action is None or released_action != pressed_action:
                return None
            action_event = self._event_for_action(layout, released_action)
            if action_event.get("type") != "notice":
                self._emit_click_sfx(released_action)
            return action_event

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_l:
            self._emit_sfx("logout")
            return {"type": "leave_shop"}

        if layout["booting"]:
            return None

        menu_id = layout["menu_id"]

        if menu_id == "main_menu":
            if event.key == pygame.K_1:
                return {"type": "open_shop_menu", "menu_id": "purchase"}
            if event.key == pygame.K_2:
                return {"type": "open_shop_menu", "menu_id": "purge"}
            if event.key == pygame.K_3:
                return {"type": "open_shop_menu", "menu_id": "cleanse"}
            return None

        if event.key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
            if menu_id == "purchase" and layout["selected_card_offer"] is not None:
                return {"type": "clear_shop_selection"}
            return {"type": "open_shop_menu", "menu_id": "main_menu"}

        if menu_id == "purchase":
            if layout["selected_card_offer"] is None and pygame.K_1 <= event.key <= pygame.K_4:
                option_index = event.key - pygame.K_1
                if option_index < len(layout["card_entries"]):
                    return {"type": "select_shop_offer", "offer_id": layout["card_entries"][option_index]["offer_id"]}
            if layout["selected_card_offer"] is not None and event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                return self._event_for_action(layout, "purchase_confirm")
            if layout["selected_card_offer"] is None and event.key == pygame.K_r:
                return self._event_for_action(layout, "purchase_reroll")
            return None

        if menu_id == "purge":
            if pygame.K_1 <= event.key <= pygame.K_9:
                option_index = event.key - pygame.K_1
                if option_index < len(layout["purge_entries"]):
                    target = layout["purge_entries"][option_index]
                    if target.get("selected"):
                        return {"type": "clear_shop_selection"}
                    return {"type": "select_shop_offer", "offer_id": f"purge_target:{target['deck_index']}"}
            if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                return self._event_for_action(layout, "purge_confirm")
            return None

        if menu_id == "cleanse":
            if event.key == pygame.K_1:
                return self._event_for_action(layout, f"service:{SHOP_HEAL_OFFER_ID}")
            if event.key == pygame.K_2:
                return self._event_for_action(layout, f"service:{SHOP_CLEANSE_OFFER_ID}")
            return None

        return None

    def build_layout(
        self,
        shop_state: dict[str, Any],
        screen_size: tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT),
    ) -> dict[str, Any]:
        shop = shop_state["shop"]
        player = shop_state["player"]
        terminal_rect = _rect_from_art(MERCHANT_VAN_LAYOUT["terminal_rect"], screen_size)
        terminal_content = _inset_rect(
            terminal_rect,
            int(round(MERCHANT_VAN_LAYOUT["terminal_padding"] * (screen_size[0] / MERCHANT_VAN_ART_SIZE[0]))),
            int(round(MERCHANT_VAN_LAYOUT["terminal_padding"] * (screen_size[1] / MERCHANT_VAN_ART_SIZE[1]))),
        )
        gap = max(8, int(round(MERCHANT_VAN_LAYOUT["terminal_gap"] * (screen_size[1] / MERCHANT_VAN_ART_SIZE[1]))))
        title_height = max(28, int(round(36 * (screen_size[1] / MERCHANT_VAN_ART_SIZE[1]))))
        logout_height = max(46, int(round(MERCHANT_VAN_LAYOUT["terminal_logout_height"] * (screen_size[1] / MERCHANT_VAN_ART_SIZE[1]))))
        button_height = max(42, int(round(MERCHANT_VAN_LAYOUT["terminal_button_height"] * (screen_size[1] / MERCHANT_VAN_ART_SIZE[1]))))

        booting = self._boot_elapsed < BOOT_DURATION_SECONDS
        menu_id = shop.get("merchant_menu", "main_menu")
        theme_id = "boot" if booting else menu_id if menu_id in TERMINAL_THEMES else "main_menu"
        theme = TERMINAL_THEMES[theme_id]

        title_rect = _rect_top(terminal_content, title_height)
        logout_rect = _rect_bottom(terminal_content, logout_height)
        body_rect = (
            terminal_content[0],
            title_rect[1] + title_rect[3] + gap,
            terminal_content[2],
            max(60, logout_rect[1] - gap - (title_rect[1] + title_rect[3] + gap)),
        )
        back_rect = (
            title_rect[0] + title_rect[2] - max(96, int(title_rect[2] * 0.28)),
            title_rect[1],
            max(96, int(title_rect[2] * 0.28)),
            title_rect[3],
        )

        status_rect = _rect_from_art(MERCHANT_VAN_LAYOUT["status_rect"], screen_size)
        shelf_region = _rect_from_art(MERCHANT_VAN_LAYOUT["shelf_region"], screen_size)
        relic_tooltip_rect = _rect_from_art(MERCHANT_VAN_LAYOUT["relic_tooltip_rect"], screen_size)
        purge_window_rect = _rect_from_art(MERCHANT_VAN_LAYOUT["purge_window_rect"], screen_size)

        action_entries: list[dict[str, Any]] = []
        if menu_id != "purge":
            action_entries.append({"action_id": "logout", "rect": logout_rect, "enabled": True, "disabled_reason": None, "kind": "logout"})

        relic_entries = self._build_relic_entries(list(shop.get("relic_offers") or [])[:3], shelf_region, shop_state)
        for entry in relic_entries:
            action_entries.append(
                {
                    "action_id": entry["action_id"],
                    "rect": entry["rect"],
                    "enabled": entry["enabled"],
                    "disabled_reason": entry["disabled_reason"],
                    "kind": "relic",
                }
            )

        hovered_relic = next((entry for entry in relic_entries if entry["action_id"] == self._hovered_action), None)
        selected_card_offer = next(
            (
                offer
                for offer in list(shop.get("card_offers") or [])
                if offer["offer_id"] == shop.get("selected_offer_id")
            ),
            None,
        )

        menu_buttons: list[dict[str, Any]] = []
        card_entries: list[dict[str, Any]] = []
        purchase_reroll_button: dict[str, Any] | None = None
        purchase_confirm_button: dict[str, Any] | None = None
        purchase_preview_rect: tuple[int, int, int, int] | None = None
        purchase_hover_offer: dict[str, Any] | None = None
        purchase_preview_offer: dict[str, Any] | None = None
        purge_entries: list[dict[str, Any]] = []
        purge_preview_rect: tuple[int, int, int, int] | None = None
        purge_preview_target: dict[str, Any] | None = None
        purge_confirm_button: dict[str, Any] | None = None
        service_entries: list[dict[str, Any]] = []
        service_tooltip_rect: tuple[int, int, int, int] | None = None
        hovered_service_offer: dict[str, Any] | None = None

        if menu_id == "main_menu":
            button_height = max(70, int(body_rect[3] * 0.2))
            buttons_rect = (body_rect[0], body_rect[1], body_rect[2], button_height)
            button_rects = _stack_vertical(buttons_rect, 3, height=button_height, gap=gap)
            labels = [("purchase", "Purchase"), ("purge", "Purge"), ("cleanse", "Cleanse")]
            for rect, (target_menu_id, label) in zip(button_rects, labels, strict=False):
                button = {
                    "action_id": f"menu:{target_menu_id}",
                    "rect": rect,
                    "label": label,
                    "enabled": not booting,
                    "disabled_reason": "Terminal booting..." if booting else None,
                    "kind": "primary",
                }
                menu_buttons.append(button)
                action_entries.append(button)

        elif menu_id == "purchase":
            action_entries.append({"action_id": "back", "rect": back_rect, "enabled": not booting, "disabled_reason": None, "kind": "secondary"})
            selected_offer_id = None if selected_card_offer is None else selected_card_offer["offer_id"]
            if selected_card_offer is None:
                list_width = max(148, int(body_rect[2] * 0.40))
                preview_width = max(160, body_rect[2] - list_width - gap)
                row_height = max(42, int((body_rect[3] - button_height - gap - (gap * 3)) / 4))
                rows_rect = (body_rect[0], body_rect[1], list_width, (row_height * 4) + (gap * 3))
                row_rects = _stack_vertical(rows_rect, 4, height=row_height, gap=gap)
                for index, offer in enumerate(list(shop.get("card_offers") or [])[:4]):
                    row = {
                        **offer,
                        "rect": row_rects[index] if index < len(row_rects) else row_rects[-1],
                        "action_id": f"card:{offer['offer_id']}",
                        "selected": False,
                        "shortcut": index + 1 if index < 9 else None,
                    }
                    card_entries.append(row)
                    action_entries.append(
                        {
                            "action_id": row["action_id"],
                            "rect": row["rect"],
                            "enabled": not booting and not offer.get("sold_out"),
                            "disabled_reason": "Sold out." if offer.get("sold_out") else ("Terminal booting..." if booting else None),
                            "kind": "card_row",
                        }
                    )
                purchase_reroll_button = {
                    "action_id": "purchase_reroll",
                    "rect": (body_rect[0], rows_rect[1] + rows_rect[3] + gap, list_width, button_height),
                    "label": f"Reroll {shop.get('reroll_price', 0)}",
                    "enabled": bool(shop.get("can_reroll")) and not booting,
                    "disabled_reason": "Terminal booting..." if booting else shop.get("reroll_disabled_reason") or "Reroll unavailable.",
                    "kind": "secondary",
                }
                action_entries.append(purchase_reroll_button)
                purchase_preview_rect = (
                    body_rect[0] + list_width + gap,
                    body_rect[1],
                    preview_width,
                    body_rect[3],
                )
                purchase_hover_offer = next(
                    (row for row in card_entries if row["action_id"] == self._hovered_action),
                    None,
                )
                purchase_preview_offer = purchase_hover_offer
            else:
                purchase_preview_rect = (
                    body_rect[0],
                    body_rect[1],
                    body_rect[2],
                    max(120, body_rect[3] - button_height - gap),
                )
                can_purchase, disabled_reason = self._offer_purchase_state(selected_card_offer, shop_state)
                purchase_confirm_button = {
                    "action_id": "purchase_confirm",
                    "rect": (
                        body_rect[0] + max(0, int(body_rect[2] * 0.2)),
                        purchase_preview_rect[1] + purchase_preview_rect[3] + gap,
                        max(120, int(body_rect[2] * 0.6)),
                        button_height,
                    ),
                    "label": f"{selected_card_offer['price']} cr",
                    "enabled": can_purchase and not booting,
                    "disabled_reason": "Terminal booting..." if booting else disabled_reason,
                    "kind": "confirm",
                }
                action_entries.append(purchase_confirm_button)
                purchase_preview_offer = selected_card_offer

        elif menu_id == "purge":
            window_padding = max(18, int(purge_window_rect[2] * 0.025))
            window_header_height = 56
            content_rect = _inset_rect(purge_window_rect, window_padding, window_padding)
            back_rect = (
                content_rect[0] + max(0, content_rect[2] - max(128, int(content_rect[2] * 0.18))),
                content_rect[1],
                max(128, int(content_rect[2] * 0.18)),
                max(40, int(window_header_height * 0.72)),
            )
            action_entries.append({"action_id": "back", "rect": back_rect, "enabled": not booting, "disabled_reason": None, "kind": "secondary"})
            list_width = max(260, int(content_rect[2] * 0.48))
            preview_width = max(260, content_rect[2] - list_width - gap)
            list_rect = (content_rect[0], content_rect[1] + window_header_height, list_width, content_rect[3] - window_header_height)
            preview_column_rect = (list_rect[0] + list_rect[2] + gap, list_rect[1], preview_width, list_rect[3])
            purge_preview_rect = (
                preview_column_rect[0],
                preview_column_rect[1],
                preview_column_rect[2],
                max(120, preview_column_rect[3] - button_height - gap),
            )
            purge_targets = list(shop.get("purge_targets") or [])
            columns = 2 if len(purge_targets) > 5 else 1
            rows = max(1, math.ceil(len(purge_targets) / max(1, columns)))
            grid_cells = _split_grid(list_rect, columns=columns, rows=rows, gap_x=gap, gap_y=gap)
            for index, target in enumerate(purge_targets):
                entry = {
                    **target,
                    "label": target.get("label") or target.get("card", {}).get("name", "Card"),
                    "rect": grid_cells[index] if index < len(grid_cells) else list_rect,
                    "action_id": f"purge_target:{target['deck_index']}",
                    "shortcut": index + 1 if index < 9 else None,
                }
                purge_entries.append(entry)
                action_entries.append(
                    {
                        "action_id": entry["action_id"],
                        "rect": entry["rect"],
                        "enabled": not booting,
                        "disabled_reason": "Terminal booting..." if booting else None,
                        "kind": "purge_row",
                    }
                )
            selected_purge_entry = next((entry for entry in purge_entries if entry.get("selected")), None)
            hovered_purge_entry = next((entry for entry in purge_entries if entry["action_id"] == self._hovered_action), None)
            purge_preview_target = selected_purge_entry or hovered_purge_entry
            purge_offer = shop.get("purge_offer")
            can_purchase, disabled_reason = self._offer_purchase_state(purge_offer, shop_state)
            purge_confirm_button = {
                "action_id": "purge_confirm",
                "rect": (
                    preview_column_rect[0] + max(0, int(preview_column_rect[2] * 0.12)),
                    purge_preview_rect[1] + purge_preview_rect[3] + gap,
                    max(160, int(preview_column_rect[2] * 0.76)),
                    button_height,
                ),
                "label": "Purge",
                "enabled": can_purchase and not booting,
                "disabled_reason": "Terminal booting..." if booting else disabled_reason,
                "kind": "danger",
            }
            action_entries.append(purge_confirm_button)

        elif menu_id == "cleanse":
            action_entries.append({"action_id": "back", "rect": back_rect, "enabled": not booting, "disabled_reason": None, "kind": "secondary"})
            row_height = max(58, int(body_rect[3] * 0.18))
            row_rects = _stack_vertical((body_rect[0], body_rect[1], body_rect[2], row_height), 2, height=row_height, gap=gap)
            for rect, offer in zip(row_rects, [shop.get("heal_offer"), shop.get("cleanse_offer")], strict=False):
                if offer is None:
                    continue
                enabled, disabled_reason = self._offer_purchase_state(offer, shop_state)
                entry = {
                    **offer,
                    "rect": rect,
                    "action_id": f"service:{offer['offer_id']}",
                    "enabled": enabled and not booting,
                    "disabled_reason": "Terminal booting..." if booting else disabled_reason,
                }
                service_entries.append(entry)
                action_entries.append(
                    {
                        "action_id": entry["action_id"],
                        "rect": entry["rect"],
                        "enabled": entry["enabled"],
                        "disabled_reason": entry["disabled_reason"],
                        "kind": "service",
                    }
                )
            hovered_service_offer = next((entry for entry in service_entries if entry["action_id"] == self._hovered_action), None)
            tooltip_top = row_rects[-1][1] + row_rects[-1][3] + gap if row_rects else body_rect[1]
            tooltip_bottom = logout_rect[1] - gap
            if tooltip_bottom - tooltip_top >= 56:
                service_tooltip_rect = (
                    body_rect[0],
                    tooltip_top,
                    body_rect[2],
                    tooltip_bottom - tooltip_top,
                )

        return {
            "screen_size": screen_size,
            "booting": booting,
            "boot_progress": _clamp(self._boot_elapsed / BOOT_DURATION_SECONDS, 0.0, 1.0),
            "menu_id": menu_id,
            "theme": theme,
            "terminal_rect": terminal_rect,
            "terminal_content": terminal_content,
            "title_rect": title_rect,
            "body_rect": body_rect,
            "logout_rect": logout_rect,
            "back_rect": back_rect,
            "status_rect": status_rect,
            "shelf_region": shelf_region,
            "relic_tooltip_rect": relic_tooltip_rect,
            "purge_window_rect": purge_window_rect,
            "action_entries": action_entries,
            "menu_buttons": menu_buttons,
            "card_entries": card_entries,
            "selected_card_offer": selected_card_offer,
            "purchase_reroll_button": purchase_reroll_button,
            "purchase_confirm_button": purchase_confirm_button,
            "purchase_preview_rect": purchase_preview_rect,
            "purchase_preview_offer": purchase_preview_offer,
            "purge_entries": purge_entries,
            "purge_preview_rect": purge_preview_rect,
            "purge_preview_target": purge_preview_target,
            "purge_confirm_button": purge_confirm_button,
            "service_entries": service_entries,
            "service_tooltip_rect": service_tooltip_rect,
            "hovered_service_offer": hovered_service_offer,
            "relic_entries": relic_entries,
            "hovered_relic": hovered_relic,
            "player_credits": player.get("credits", 0),
            "active_curses": list(shop.get("active_curses") or []),
            "status_message": shop_state.get("status_message"),
        }

    def render_scene_background(self, surface: Any, shop_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        shop = shop_state["shop"]
        background_path = resolve_encounter_background_path(shop.get("map_id"), shop.get("branch_faction"))
        background = self._scaled_image(background_path, surface.get_size())
        surface.blit(background, (0, 0))

    def render_transition_scene(
        self,
        surface: Any,
        shop_state: dict[str, Any],
        progress: float,
        *,
        sway_x: float = 0.0,
        sway_y: float = 0.0,
    ) -> None:
        if pygame is None or surface is None:
            return
        self.render_scene_background(surface, shop_state)
        eased = _ease_out_cubic(progress)
        zoom = 0.78 + (0.22 * eased)
        center = (
            int(round((surface.get_width() * 0.52) + sway_x)),
            int(round((surface.get_height() * 0.51) + sway_y)),
        )
        self._draw_merchant_van(surface, scale=zoom, center=center, alpha=int(round(210 + (45 * eased))))
        if eased < 1.0:
            fade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(round(28 * (1.0 - eased)))))
            surface.blit(fade, (0, 0))

    def render(self, surface: Any, shop_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._last_surface_size = surface.get_size()
        self._ensure_fonts(shop_state.get("presentation", {}).get("ui_scale", 1.0))
        layout = self.build_layout(shop_state, self._last_surface_size)
        self.render_scene_background(surface, shop_state)
        self._draw_merchant_van(surface)
        self._draw_scene_status(surface, layout)
        self._draw_relic_shelf(surface, layout)
        if layout["menu_id"] == "purge":
            self._draw_purge_overlay(surface, layout)
        else:
            self._draw_terminal(surface, layout)

        if layout["hovered_relic"] is not None:
            self._draw_relic_tooltip(surface, layout["hovered_relic"], layout["relic_tooltip_rect"])

        if self._denial_flash > 0:
            alpha = int(round(52 * (self._denial_flash / DENIAL_FLASH_SECONDS)))
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((236, 108, 124, alpha))
            surface.blit(overlay, (0, 0))

    def _draw_scene_status(self, surface: Any, layout: dict[str, Any]) -> None:
        rect = pygame.Rect(*layout["status_rect"])
        status_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(status_surface, (8, 14, 20, 128), status_surface.get_rect(), border_radius=18)
        pygame.draw.rect(status_surface, (72, 102, 134, 176), status_surface.get_rect(), 1, border_radius=18)
        surface.blit(status_surface, rect.topleft)
        self._draw_text(
            surface,
            layout["status_message"] or "Merchant terminal online.",
            (rect.x + 18, rect.y + 11),
            self._tiny_font,
            width=rect.width - 36,
        )

    def _draw_terminal(self, surface: Any, layout: dict[str, Any]) -> None:
        rect = pygame.Rect(*layout["terminal_rect"])
        self._draw_terminal_surface(surface, rect, layout["theme"])
        self._draw_terminal_header(surface, layout)

        if layout["booting"]:
            self._draw_boot_sequence(surface, rect, layout["boot_progress"])
        elif layout["menu_id"] == "main_menu":
            for button in layout["menu_buttons"]:
                self._draw_terminal_button(surface, button, layout["theme"])
        elif layout["menu_id"] == "purchase":
            self._draw_purchase_view(surface, layout)
        elif layout["menu_id"] == "cleanse":
            self._draw_cleanse_view(surface, layout)

        self._draw_logout_button(
            surface,
            layout["logout_rect"],
            hovered=self._hovered_action == "logout",
            pressed=self._pressed_action == "logout",
        )

    def _draw_terminal_surface(self, surface: Any, rect: pygame.Rect, theme: dict[str, Any]) -> None:
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        for offset in range(rect.height):
            blend = offset / max(1, rect.height - 1)
            color = tuple(
                int(theme["top"][index] + ((theme["bottom"][index] - theme["top"][index]) * blend))
                for index in range(3)
            )
            pygame.draw.line(layer, (*color, 224), (0, offset), (rect.width, offset))
        for y in range(0, rect.height, 5):
            pygame.draw.line(layer, (*theme["accent_soft"], 12), (0, y), (rect.width, y))
        pygame.draw.rect(layer, (*theme["accent"], 56), pygame.Rect(10, 10, rect.width - 20, rect.height - 20), 2, border_radius=22)
        surface.blit(layer, rect.topleft)
        pygame.draw.rect(surface, theme["accent"], rect, 2, border_radius=24)

    def _draw_terminal_header(self, surface: Any, layout: dict[str, Any]) -> None:
        title_rect = pygame.Rect(*layout["title_rect"])
        credits_rect = pygame.Rect(title_rect.x, title_rect.y, max(120, int(title_rect.width * 0.40)), title_rect.height)
        draw_chip(
            surface,
            credits_rect,
            label=f"Credits {layout['player_credits']}",
            font=self._tiny_font,
            accent=layout["theme"]["accent"],
            fill=COLOR_PANEL_ELEVATED,
        )
        title_label = {
            "main_menu": "MERCHANT",
            "purchase": "PURCHASE",
            "purge": "PURGE",
            "cleanse": "CLEANSE",
        }.get(layout["menu_id"], "MERCHANT")
        self._draw_text(
            surface,
            title_label,
            (credits_rect.right + 10, title_rect.y + 9),
            self._micro_font,
            width=max(0, title_rect.width - credits_rect.width - 128),
            color=layout["theme"]["muted"],
        )
        if layout["menu_id"] != "main_menu" and not layout["booting"]:
            self._draw_terminal_button(
                surface,
                {
                    "action_id": "back",
                    "rect": layout["back_rect"],
                    "label": "Back",
                    "enabled": True,
                    "disabled_reason": None,
                    "kind": "secondary",
                },
                layout["theme"],
            )

    def _draw_boot_sequence(self, surface: Any, terminal_rect: pygame.Rect, progress: float) -> None:
        inner_rect = terminal_rect.inflate(-34, -34)
        layer = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (18, 54, 92, 62), layer.get_rect(), border_radius=18)
        band_y = int(round((self._terminal_clock * 120) % max(1, inner_rect.height + 100))) - 50
        for offset in range(-1, 2):
            beam_rect = pygame.Rect(0, band_y + (offset * 8), inner_rect.width, 12)
            pygame.draw.rect(layer, (92, 206, 255, 26 if offset else 56), beam_rect)
        center = (inner_rect.width // 2, int(inner_rect.height * 0.42))
        radius = int(28 + (22 * progress))
        pygame.draw.circle(layer, (88, 198, 255, int(36 + (76 * progress))), center, radius, 2)
        pygame.draw.circle(layer, (88, 198, 255, int(64 + (98 * progress))), center, max(3, int(radius * 0.18)))
        for index in range(4):
            width = int(inner_rect.width * (0.25 + (0.12 * index)))
            bar_rect = pygame.Rect((inner_rect.width - width) // 2, int(inner_rect.height * 0.64) + (index * 16), width, 6)
            alpha = int(round((46 + (52 * math.sin((self._terminal_clock * 2.2) + index))) * progress))
            pygame.draw.rect(layer, (88, 198, 255, max(10, alpha)), bar_rect, border_radius=3)
        pygame.draw.rect(layer, (88, 198, 255, int(72 + (96 * progress))), layer.get_rect(), 2, border_radius=18)
        surface.blit(layer, inner_rect.topleft)

    def _draw_purchase_view(self, surface: Any, layout: dict[str, Any]) -> None:
        theme = TERMINAL_THEMES["purchase"]
        if layout["selected_card_offer"] is None:
            for entry in layout["card_entries"]:
                self._draw_card_row(
                    surface,
                    entry,
                    hovered=self._hovered_action == entry["action_id"],
                    selected=False,
                )
            if layout["purchase_reroll_button"] is not None:
                self._draw_terminal_button(surface, layout["purchase_reroll_button"], theme)
        if layout["purchase_preview_rect"] is not None and layout["purchase_preview_offer"] is not None:
            self._draw_card_preview(surface, layout["purchase_preview_rect"], layout["purchase_preview_offer"], accent=theme["accent"])
        if layout["purchase_confirm_button"] is not None:
            self._draw_terminal_button(surface, layout["purchase_confirm_button"], theme)

    def _draw_cleanse_view(self, surface: Any, layout: dict[str, Any]) -> None:
        theme = TERMINAL_THEMES["cleanse"]
        for index, entry in enumerate(layout["service_entries"]):
            rect = pygame.Rect(*entry["rect"])
            hovered = self._hovered_action == entry["action_id"]
            fill = theme["button_hover"] if hovered and entry["enabled"] else theme["button"] if entry["enabled"] else theme["button_disabled"]
            draw_panel(surface, rect, accent=theme["accent"], fill=fill, radius=RADIUS_MD, border_width=2 if hovered else 1, shadow_alpha=0)
            badge_rect = pygame.Rect(rect.x + 12, rect.y + 12, 34, rect.height - 24)
            draw_panel(surface, badge_rect, accent=theme["accent"], fill=theme["panel"], radius=RADIUS_MD, border_width=1, shadow_alpha=0)
            label_surface = self._micro_font.render(str(index + 1), True, theme["accent"])
            surface.blit(label_surface, label_surface.get_rect(center=badge_rect.center))
            self._draw_centered_label(
                surface,
                entry["label"],
                (rect.x + 56, rect.y, rect.width - 68, rect.height),
                self._small_font,
                theme["text"],
            )
        if layout["service_tooltip_rect"] is not None and layout["hovered_service_offer"] is not None:
            self._draw_service_tooltip(surface, layout["service_tooltip_rect"], layout["hovered_service_offer"], theme)

    def _draw_relic_shelf(self, surface: Any, layout: dict[str, Any]) -> None:
        for entry in layout["relic_entries"]:
            rect = pygame.Rect(*entry["draw_rect"])
            palette = entry["palette"]
            hovered = self._hovered_action == entry["action_id"]
            draw_panel(
                surface,
                rect,
                accent=palette["border"],
                fill=palette["fill_hover"] if hovered and entry["enabled"] else palette["fill"],
                radius=RADIUS_MD,
                border_width=2 if hovered else 1,
                shadow_alpha=42,
                shadow_offset=8,
            )
            art_rect = pygame.Rect(rect.x + 16, rect.y + 12, rect.width - 32, rect.height - 44)
            art = relic_assets.get_relic_art(entry["relic_id"], art_rect.size)
            if art is not None:
                surface.blit(art, art.get_rect(center=art_rect.center))
            else:
                self._draw_text(surface, entry["label"][:3].upper(), (art_rect.x + 10, art_rect.y + 12), self._small_font, color=palette["accent"])
            chip_rect = pygame.Rect(rect.x + 10, rect.bottom - 28, rect.width - 20, 20)
            draw_chip(
                surface,
                chip_rect,
                label="SOLD" if entry.get("sold_out") else f"{entry['price']} cr",
                font=self._micro_font,
                accent=palette["border"],
                fill=COLOR_PANEL_ELEVATED,
            )
            if entry.get("sold_out"):
                sold_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
                sold_surface.fill((0, 0, 0, 132))
                surface.blit(sold_surface, rect.topleft)
                self._draw_text(surface, "SOLD", (rect.x + 22, rect.y + 16), self._small_font, color=(248, 232, 212))

    def _draw_relic_tooltip(self, surface: Any, entry: dict[str, Any], rect_tuple: tuple[int, int, int, int]) -> None:
        rect = pygame.Rect(*rect_tuple)
        draw_panel(surface, rect, accent=entry["palette"]["border"], fill=(8, 12, 18), radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        self._draw_text(surface, entry["label"], (rect.x + 18, rect.y + 14), self._small_font, width=rect.width - 36)
        self._draw_text(surface, f"{entry['price']} credits", (rect.x + 18, rect.y + 42), self._micro_font, color=entry["palette"]["accent"])
        self._draw_text(surface, entry["relic"].get("description"), (rect.x + 18, rect.y + 68), self._tiny_font, width=rect.width - 36, color=entry["palette"]["muted"])

    def _draw_purge_overlay(self, surface: Any, layout: dict[str, Any]) -> None:
        theme = TERMINAL_THEMES["purge"]
        window_rect = pygame.Rect(*layout["purge_window_rect"])
        draw_panel(surface, window_rect, accent=theme["accent"], fill=(22, 6, 12), radius=RADIUS_LG, border_width=2, shadow_alpha=0)
        self._draw_text(surface, "MEMORY JACK", (window_rect.x + 24, window_rect.y + 18), self._small_font, color=theme["accent"])
        self._draw_terminal_button(
            surface,
            {
                "action_id": "back",
                "rect": layout["back_rect"],
                "label": "Back",
                "enabled": not layout["booting"],
                "disabled_reason": None,
                "kind": "secondary",
            },
            theme,
        )

        for entry in layout["purge_entries"]:
            self._draw_card_row(
                surface,
                entry,
                hovered=self._hovered_action == entry["action_id"],
                selected=bool(entry.get("selected")),
                variant="purge",
            )

        if layout["purge_preview_rect"] is not None and layout["purge_preview_target"] is not None:
            self._draw_card_preview(
                surface,
                layout["purge_preview_rect"],
                layout["purge_preview_target"],
                accent=theme["accent"],
            )

        if layout["purge_confirm_button"] is not None:
            self._draw_terminal_button(surface, layout["purge_confirm_button"], theme)

    def _draw_card_row(
        self,
        surface: Any,
        entry: dict[str, Any],
        *,
        hovered: bool,
        selected: bool,
        variant: str = "purchase",
    ) -> None:
        rect = pygame.Rect(*entry["rect"])
        card_theme = resolve_card_theme(entry["card"])
        accent = card_theme["type_theme"]["accent"]
        fill = (18, 26, 40) if variant == "purchase" else (42, 14, 20)
        hover_fill = (26, 38, 58) if variant == "purchase" else (58, 18, 28)
        selected_fill = (36, 48, 72) if variant == "purchase" else (84, 24, 34)
        if hovered:
            fill = hover_fill
        if selected:
            fill = selected_fill
        if entry.get("sold_out"):
            fill = (20, 22, 28)
            accent = COLOR_LINE_SOFT
        draw_panel(surface, rect, accent=accent, fill=fill, radius=RADIUS_MD, border_width=2 if hovered or selected else 1, shadow_alpha=0)

        badge_rect = pygame.Rect(rect.x + 10, rect.y + 8, 42, rect.height - 16)
        draw_panel(surface, badge_rect, accent=accent, fill=(10, 16, 24), radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        badge_label = CARD_TYPE_BADGES.get(str(entry["card"].get("type", "status")).lower(), "CRD")
        badge_surface = self._micro_font.render(badge_label, True, accent)
        surface.blit(badge_surface, badge_surface.get_rect(center=badge_rect.center))

        text_x = badge_rect.right + 12
        text_width = rect.width - (text_x - rect.x) - 42
        row_label = entry.get("label") or entry.get("card", {}).get("name", "Card")
        self._draw_text(surface, row_label, (text_x, rect.y + 12), self._tiny_font, width=text_width, color=COLOR_TEXT)
        if entry.get("shortcut") is not None:
            shortcut_surface = self._micro_font.render(str(entry["shortcut"]), True, COLOR_MUTED)
            surface.blit(shortcut_surface, shortcut_surface.get_rect(midright=(rect.right - 12, rect.centery)))

    def _draw_card_preview(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        entry: dict[str, Any],
        *,
        accent: tuple[int, int, int],
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        draw_panel(surface, rect, accent=accent, fill=(10, 14, 22), radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        card_rect = fit_portrait_card((rect.x + 12, rect.y + 12, rect.width - 24, rect.height - 24), padding=0)
        draw_card(
            surface,
            card_rect,
            entry["card"],
            {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._micro_font},
            variant="full",
            selected=True,
            high_contrast=False,
        )

    def _draw_service_tooltip(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        entry: dict[str, Any],
        theme: dict[str, Any],
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        draw_panel(surface, rect, accent=theme["accent"], fill=theme["panel"], radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        if entry["offer_id"] == SHOP_HEAL_OFFER_ID:
            self._draw_centered_label(surface, f"{entry['price']} cr", (rect.x, rect.y + 8, rect.width, 20), self._tiny_font, theme["accent"])
            self._draw_centered_label(surface, f"Recover {SHOP_HEAL_AMOUNT} HP", (rect.x + 12, rect.y + 34, rect.width - 24, rect.height - 42), self._tiny_font, theme["text"])
            return
        self._draw_centered_label(surface, "Removes one random curse.", rect, self._tiny_font, theme["text"])

    def _draw_terminal_button(self, surface: Any, button: dict[str, Any], theme: dict[str, Any]) -> None:
        rect = pygame.Rect(*button["rect"])
        hovered = self._hovered_action == button["action_id"]
        pressed = self._pressed_action == button["action_id"]
        enabled = button.get("enabled", True)
        kind = button.get("kind", "primary")
        fill = theme["button"]
        border = theme["accent"]
        text_color = theme["text"]
        if kind == "secondary":
            fill = theme["accent_soft"]
        elif kind == "confirm":
            fill = COLOR_GOLD
            border = COLOR_GOLD
            text_color = (22, 26, 32)
        elif kind == "danger":
            fill = (126, 34, 46)
            border = COLOR_RED
        if not enabled:
            fill = theme["button_disabled"]
            border = COLOR_LINE_SOFT
            text_color = COLOR_MUTED
        elif hovered and kind not in {"confirm"}:
            fill = theme["button_hover"]
        elif hovered and kind == "confirm":
            fill = (255, 224, 128)
            border = (255, 224, 128)
        if enabled and pressed:
            fill = COLOR_GOLD
            border = COLOR_GOLD
            text_color = (20, 26, 32)
        draw_panel(surface, rect, accent=border, fill=fill, radius=RADIUS_MD, border_width=2 if hovered else 1, shadow_alpha=0)
        self._draw_centered_label(surface, button["label"], button["rect"], self._tiny_font, text_color)

    def _draw_logout_button(self, surface: Any, rect_tuple: tuple[int, int, int, int], *, hovered: bool, pressed: bool) -> None:
        rect = pygame.Rect(*rect_tuple)
        fill = (104, 18, 28)
        border = COLOR_RED
        if hovered:
            fill = (146, 28, 42)
        if pressed:
            fill = COLOR_GOLD
            border = COLOR_GOLD
        draw_panel(surface, rect, accent=border, fill=fill, radius=RADIUS_MD, border_width=2 if hovered else 1, shadow_alpha=0)

        icon_surface = pygame.Surface((22, 22), pygame.SRCALPHA)
        icon_color = (248, 238, 242) if not pressed else (24, 28, 36)
        pygame.draw.circle(icon_surface, icon_color, (11, 12), 8, 2)
        pygame.draw.line(icon_surface, icon_color, (11, 0), (11, 8), 3)
        text_surface = self._tiny_font.render("Logout", True, icon_color)
        group_width = icon_surface.get_width() + 8 + text_surface.get_width()
        group_x = rect.x + max(0, (rect.width - group_width) // 2)
        group_y = rect.y + max(0, (rect.height - text_surface.get_height()) // 2)
        surface.blit(icon_surface, (group_x, rect.y + max(0, (rect.height - icon_surface.get_height()) // 2)))
        surface.blit(text_surface, (group_x + icon_surface.get_width() + 8, group_y))

    def _draw_centered_label(
        self,
        surface: Any,
        label: str,
        rect_tuple: tuple[int, int, int, int],
        font: Any,
        color: tuple[int, int, int],
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        rendered = font.render(label, True, color)
        surface.blit(rendered, rendered.get_rect(center=rect.center))

    def _build_relic_entries(
        self,
        offers: list[dict[str, Any]],
        shelf_region: tuple[int, int, int, int],
        shop_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not offers:
            return []
        results: list[dict[str, Any]] = []
        slot_positions = [0.20, 0.50, 0.80]
        slot_width = max(88, int(shelf_region[2] * 0.19))
        slot_height = max(102, int(shelf_region[3] * 0.66))
        base_y = int(round(shelf_region[1] + (shelf_region[3] * 0.46)))
        for index, offer in enumerate(offers[:3]):
            enabled, disabled_reason = self._offer_purchase_state(offer, shop_state)
            center_x = int(round(shelf_region[0] + (shelf_region[2] * slot_positions[index])))
            hovered = self._hovered_action == f"relic:{offer['offer_id']}"
            rect = _centered_rect(center_x, base_y - (12 if hovered and enabled else 0), slot_width, slot_height)
            rarity = str(offer["relic"].get("rarity", "common")).lower()
            palette = RELIC_PALETTES.get(rarity, RELIC_PALETTES["common"])
            results.append(
                {
                    **offer,
                    "action_id": f"relic:{offer['offer_id']}",
                    "rect": rect,
                    "draw_rect": rect,
                    "enabled": enabled,
                    "disabled_reason": disabled_reason,
                    "palette": palette,
                }
            )
        return results

    def _offer_purchase_state(
        self,
        offer: dict[str, Any] | None,
        shop_state: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if offer is None:
            return False, "Offer unavailable."

        player = shop_state["player"]
        shop = shop_state["shop"]

        if offer.get("sold_out"):
            return False, "Already sold."
        if offer.get("price", 0) > player.get("credits", 0):
            return False, f"Requires {offer.get('price', 0)} credits."
        if offer.get("type") == "heal" and player.get("current_hp", 0) >= player.get("max_hp", 0):
            return False, "Heal unavailable."
        if offer.get("type") == "cleanse" and not shop.get("active_curses"):
            return False, "No curses active."
        if offer.get("type") == "purge" and shop.get("selected_purge_index") is None:
            return False, "Select a card first."
        return True, None

    def _event_for_action(self, layout: dict[str, Any], action_id: str) -> dict[str, Any]:
        action = next((entry for entry in layout["action_entries"] if entry["action_id"] == action_id), None)
        if action is None:
            return {"type": "notice", "message": "Unknown merchant action.", "level": "error"}
        if not action.get("enabled", True):
            return {"type": "notice", "message": action.get("disabled_reason") or "That control is unavailable.", "level": "error"}

        if action_id == "logout":
            return {"type": "leave_shop"}
        if action_id == "back":
            if layout["menu_id"] == "purchase" and layout["selected_card_offer"] is not None:
                return {"type": "clear_shop_selection"}
            return {"type": "open_shop_menu", "menu_id": "main_menu"}
        if action_id.startswith("menu:"):
            return {"type": "open_shop_menu", "menu_id": action_id.removeprefix("menu:")}
        if action_id.startswith("card:"):
            return {"type": "select_shop_offer", "offer_id": action_id.removeprefix("card:")}
        if action_id == "purchase_confirm":
            return {"type": "confirm_shop_purchase"}
        if action_id == "purchase_reroll":
            return {"type": "reroll_shop_inventory"}
        if action_id.startswith("relic:"):
            return {"type": "purchase_shop_offer", "offer_id": action_id.removeprefix("relic:")}
        if action_id.startswith("purge_target:"):
            target = next((entry for entry in layout["purge_entries"] if entry["action_id"] == action_id), None)
            if target is not None and target.get("selected"):
                return {"type": "clear_shop_selection"}
            return {"type": "select_shop_offer", "offer_id": action_id}
        if action_id == "purge_confirm":
            return {"type": "confirm_shop_purchase"}
        if action_id.startswith("service:"):
            offer_id = action_id.removeprefix("service:")
            if offer_id == SHOP_CLEANSE_OFFER_ID:
                return {"type": "confirm_shop_cleanse"}
            return {"type": "purchase_shop_offer", "offer_id": offer_id}
        return {"type": "notice", "message": "Unknown merchant action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for action in reversed(layout["action_entries"]):
            if point_in_rect(position, action["rect"]):
                return action["action_id"]
        return None

    def _emit_click_sfx(self, action_id: str) -> None:
        if action_id == "logout":
            self._emit_sfx("logout")
            return
        if action_id == "purge_confirm":
            self._emit_sfx("purge_confirm")
            return
        if action_id == f"service:{SHOP_CLEANSE_OFFER_ID}":
            self._emit_sfx("cleanse_confirm")
            return
        self._emit_sfx("button_click")

    def _action_supports_hover_sfx(self, layout: dict[str, Any], action_id: str) -> bool:
        action_entry = next((entry for entry in layout["action_entries"] if entry["action_id"] == action_id), None)
        if action_entry is None:
            return False
        return action_entry.get("kind") in {"primary", "secondary", "confirm", "danger", "service"}

    def _emit_sfx(self, cue_id: str) -> None:
        if self._sfx_callback is None:
            return
        self._sfx_callback(MERCHANT_SFX_CUES.get(cue_id, cue_id))

    def _draw_merchant_van(
        self,
        surface: Any,
        *,
        scale: float = 1.0,
        center: tuple[int, int] | None = None,
        alpha: int = 255,
    ) -> None:
        van = self._load_image(MERCHANT_VAN_ART_PATH, prepare_cutout=True)
        width = max(1, int(round(surface.get_width() * scale)))
        height = max(1, int(round(surface.get_height() * scale)))
        van_scaled = self._scaled_surface(van, (width, height))
        if alpha < 255:
            van_scaled = van_scaled.copy()
            van_scaled.set_alpha(alpha)
        destination = van_scaled.get_rect(center=center or (surface.get_width() // 2, surface.get_height() // 2))
        surface.blit(van_scaled, destination.topleft)

    def _draw_text(
        self,
        surface: Any,
        text: str | None,
        position: tuple[int, int],
        font: Any,
        *,
        width: int | None = None,
        color: tuple[int, int, int] = COLOR_TEXT,
    ) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        if pygame is None:
            return
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return
        self._font_scale = scale
        self._font = pygame.font.SysFont("consolas", max(22, int(28 * scale)), bold=True)
        self._small_font = pygame.font.SysFont("consolas", max(16, int(20 * scale)), bold=True)
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))
        self._micro_font = pygame.font.SysFont("consolas", max(10, int(12 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        return self._scaled_surface(self._load_image(path), size)

    def _scaled_surface(self, source: Any, size: tuple[int, int]) -> Any:
        cache_key = f"scaled::{id(source)}::{size[0]}x{size[1]}"
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        scaled = pygame.transform.smoothscale(source, size)
        self._image_cache[cache_key] = scaled
        return scaled

    def _load_image(self, path: Path, *, prepare_cutout: bool = False) -> Any:
        cache_key = f"{path}::merchant_cutout" if prepare_cutout else str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load shop UI assets.")

        base_cache_key = str(path)
        image = self._image_cache.get(base_cache_key)
        if image is None:
            try:
                image = pygame.image.load(str(path)).convert_alpha()
            except (FileNotFoundError, pygame.error):
                image = pygame.Surface((64, 64), pygame.SRCALPHA)
                image.fill((90, 180, 140, 180))
            self._image_cache[base_cache_key] = image

        if prepare_cutout:
            image = self._prepare_merchant_van_cutout(image)

        self._image_cache[cache_key] = image
        return image

    def _prepare_merchant_van_cutout(self, image: Any) -> Any:
        if pygame is None:
            return image
        cutout = image.copy()
        background_mask = pygame.mask.from_threshold(cutout, (8, 8, 8, 255), (8, 8, 8, 255))
        if background_mask.count() <= 0:
            return cutout
        edge_seed = self._find_mask_edge_seed(background_mask)
        if edge_seed is None:
            edge_mask = background_mask.connected_component()
        else:
            edge_mask = background_mask.connected_component(edge_seed)
        mask_surface = edge_mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        cutout.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        return cutout

    def _find_mask_edge_seed(self, mask: Any) -> tuple[int, int] | None:
        width, height = mask.get_size()
        if width <= 0 or height <= 0:
            return None
        last_x = width - 1
        last_y = height - 1
        for x in range(width):
            if mask.get_at((x, 0)):
                return (x, 0)
            if mask.get_at((x, last_y)):
                return (x, last_y)
        for y in range(height):
            if mask.get_at((0, y)):
                return (0, y)
            if mask.get_at((last_x, y)):
                return (last_x, y)
        return None


def simulate_shop_ui() -> dict[str, Any]:
    ui = ShopUI()
    return ui.build_layout(
        {
            "shop": {
                "shop_node_id": "shop_demo",
                "map_id": "map_1",
                "branch_faction": None,
                "merchant_menu": "purchase",
                "selected_offer_id": None,
                "selected_purge_index": None,
                "card_offers": [
                    {
                        "offer_id": "card:surge_strike_01",
                        "type": "card",
                        "card": {"id": "surge_strike_01", "name": "Surge Strike", "cost": 2, "type": "attack", "effects": [{"type": "damage", "value": 12}]},
                        "label": "Surge Strike",
                        "price": 55,
                        "sold_out": False,
                    },
                    {
                        "offer_id": "card:scatter_shot_01",
                        "type": "card",
                        "card": {"id": "scatter_shot_01", "name": "Scatter Shot", "cost": 1, "type": "attack", "effects": [{"type": "damage", "value": 7}]},
                        "label": "Scatter Shot",
                        "price": 43,
                        "sold_out": False,
                    },
                    {
                        "offer_id": "card:flash_cage_01",
                        "type": "card",
                        "card": {"id": "flash_cage_01", "name": "Flash Cage", "cost": 1, "type": "skill", "effects": [{"type": "block", "value": 8}]},
                        "label": "Flash Cage",
                        "price": 39,
                        "sold_out": False,
                    },
                    {
                        "offer_id": "card:echo_pulse_01",
                        "type": "card",
                        "card": {"id": "echo_pulse_01", "name": "Echo Pulse", "cost": 2, "type": "power", "effects": [{"type": "gain_energy", "value": 1}]},
                        "label": "Echo Pulse",
                        "price": 71,
                        "sold_out": False,
                    },
                ],
                "relic_offers": [
                    {
                        "offer_id": "relic:demo_a",
                        "type": "relic",
                        "relic_id": "demo_a",
                        "relic": {"id": "demo_a", "name": "Pulse Core", "rarity": "common", "description": "Gain 1 Block at turn start."},
                        "label": "Pulse Core",
                        "price": 84,
                        "sold_out": False,
                    }
                ],
                "purge_offer": {"offer_id": SHOP_PURGE_OFFER_ID, "type": "purge", "label": "Deck Purge", "price": 55, "sold_out": False},
                "heal_offer": {"offer_id": SHOP_HEAL_OFFER_ID, "type": "heal", "label": "Clinic Patch", "price": 18, "sold_out": False},
                "cleanse_offer": {"offer_id": SHOP_CLEANSE_OFFER_ID, "type": "cleanse", "label": "Deep Cleanse", "price": 54, "sold_out": False},
                "reroll_price": 18,
                "can_reroll": True,
                "reroll_disabled_reason": None,
                "purge_targets": [],
                "active_curses": [{"id": "curse_a", "name": "Corroded Nerves", "description": "Lose 10 Max HP."}],
            },
            "player": {"credits": 120, "current_hp": 42, "max_hp": 70},
            "status_message": "Merchant van ready.",
            "presentation": {"ui_scale": 1.0},
        }
    )
