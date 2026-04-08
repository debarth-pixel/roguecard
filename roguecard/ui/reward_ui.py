from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.card_renderer import draw_card
from ui.card_style import CARD_PORTRAIT_HEIGHT_RATIO, resolve_card_theme
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


REWARD_LAYOUT = {
    "header_rect": (56, 54, 1168, 114),
    "hero_rect": (64, 192, 1152, 344),
    "secondary_rect": (92, 552, 1096, 86),
    "action_rect": (92, 652, 1096, 52),
    "panel_radius": 24,
    "inner_radius": 20,
    "chip_gap": 18,
    "card_gap": 28,
    "purge_columns": 4,
    "purge_tile_height": 42,
    "purge_tile_gap": 10,
}


class RewardUI:
    def __init__(self) -> None:
        self._title_font = None
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
        self._load_image(resolve_asset_path("ui", "bg_map.png"))

    def handle_event(self, event: Any, reward_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(reward_state)
        active_section = layout["active_section"]

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
            return {"type": "continue_from_reward"}

        if event.key == pygame.K_x and active_section is not None and active_section["can_skip"]:
            return {"type": "skip_reward_section", "section": active_section["id"]}

        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if active_section is not None and active_section["selected_option_id"] is not None and not active_section["resolved"]:
                return {"type": "confirm_reward_selection", "section": active_section["id"]}
            if layout["can_continue"]:
                return {"type": "continue_from_reward"}
            return {"type": "notice", "message": "Choose or skip the remaining rewards first.", "level": "error"}

        if pygame.K_1 <= event.key <= pygame.K_9 and active_section is not None:
            option_index = event.key - pygame.K_1
            if option_index >= len(active_section["options"]):
                return {"type": "notice", "message": "That reward slot is empty.", "level": "error"}
            option = active_section["options"][option_index]
            return {
                "type": "select_reward_option",
                "section": active_section["id"],
                "option_id": option["option_id"],
            }

        return None

    def build_layout(self, reward_state: dict[str, Any]) -> dict[str, Any]:
        reward = reward_state["reward"]
        sections = [dict(section) for section in reward["sections"]]
        active_section = next((section for section in sections if not section["resolved"]), None)
        hero_section = active_section
        if hero_section is None:
            hero_section = next((section for section in sections if section["type"] == "card_offer"), sections[0] if sections else None)
        secondary_sections = [section for section in sections if hero_section is None or section["id"] != hero_section["id"]]

        title, subtitle = self._header_copy(reward["encounter_type"], active_section, reward["can_continue"])
        hero_panel = pygame.Rect(*REWARD_LAYOUT["hero_rect"])
        secondary_base = pygame.Rect(*REWARD_LAYOUT["secondary_rect"])
        action_rect = pygame.Rect(*REWARD_LAYOUT["action_rect"])

        layout_sections = []
        if hero_section is not None:
            layout_sections.append(
                self._layout_section(
                    hero_section,
                    hero_panel,
                    role="hero",
                    active=(active_section is not None and hero_section["id"] == active_section["id"]),
                )
            )

        for index, section in enumerate(secondary_sections):
            rect = secondary_base.move(0, index * (secondary_base.height + 12))
            layout_sections.append(
                self._layout_section(
                    section,
                    rect,
                    role="secondary",
                    active=(active_section is not None and section["id"] == active_section["id"]),
                )
            )

        button_layout = self._build_action_buttons(action_rect, active_section, reward["can_continue"])
        return {
            "encounter_type": reward["encounter_type"],
            "title": title,
            "subtitle": subtitle,
            "credits_granted": reward["credits_granted"],
            "player_credits": reward_state["player"]["credits"],
            "deck_size": reward["deck_size"],
            "sections": layout_sections,
            "active_section": active_section,
            "can_continue": reward["can_continue"],
            "action_rect": action_rect,
            "buttons": button_layout["buttons"],
            "action_hint": button_layout["hint"],
            "continue_rect": button_layout.get("continue_rect"),
        }

    def _layout_section(
        self,
        section: dict[str, Any],
        panel_rect: pygame.Rect,
        *,
        role: str,
        active: bool,
    ) -> dict[str, Any]:
        option_entries = self._option_entries(section, panel_rect, role=role) if role == "hero" and not section["resolved"] else []
        selected_option = self._selected_option(section)
        return {
            **section,
            "role": role,
            "active": active,
            "panel_rect": panel_rect,
            "option_entries": option_entries,
            "selected_option": selected_option,
        }

    def _build_action_buttons(
        self,
        action_rect: pygame.Rect,
        active_section: dict[str, Any] | None,
        can_continue: bool,
    ) -> dict[str, Any]:
        if can_continue:
            continue_rect = pygame.Rect(action_rect.right - 236, action_rect.y + 2, 220, 48)
            return {
                "hint": "Rewards secured. Continue when you are ready for the next node.",
                "continue_rect": continue_rect,
                "buttons": [
                    {
                        "action_id": "continue",
                        "label": "Continue",
                        "rect": continue_rect,
                        "kind": "primary",
                        "enabled": True,
                    }
                ],
            }

        if active_section is None:
            return {"hint": "Resolve the remaining rewards to continue.", "buttons": []}

        buttons = []
        primary_rect = pygame.Rect(action_rect.right - 236, action_rect.y + 2, 220, 48)
        buttons.append(
            {
                "action_id": f"confirm:{active_section['id']}",
                "label": "Confirm",
                "rect": primary_rect,
                "kind": "primary",
                "enabled": active_section["selected_option_id"] is not None,
            }
        )
        if active_section["can_skip"]:
            skip_rect = pygame.Rect(action_rect.right - 424, action_rect.y + 2, 172, 48)
            buttons.append(
                {
                    "action_id": f"skip:{active_section['id']}",
                    "label": "Skip",
                    "rect": skip_rect,
                    "kind": "secondary",
                    "enabled": True,
                }
            )

        hint = (
            "Choose one card to shape the next fight, then confirm or skip."
            if active_section["type"] == "card_offer"
            else "Optional cleanup: remove one deck card, or skip and keep your build as-is."
        )
        return {"hint": hint, "buttons": buttons}

    def render(self, surface: Any, reward_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(reward_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = reward_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(reward_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=188)

        self._draw_header(surface, layout, high_contrast)
        for section in layout["sections"]:
            if section["role"] == "hero":
                self._draw_hero_section(surface, section, layout, high_contrast)
            else:
                self._draw_secondary_section(surface, section)
        self._draw_action_bar(surface, layout)

    def _draw_header(self, surface: Any, layout: dict[str, Any], high_contrast: bool) -> None:
        header_rect = pygame.Rect(*REWARD_LAYOUT["header_rect"])
        self._draw_panel(surface, header_rect, fill=(14, 22, 34), border=(90, 118, 160), radius=REWARD_LAYOUT["panel_radius"])
        shimmer_x = (pygame.time.get_ticks() // 6) % (header_rect.width + 220) - 220
        shimmer_rect = pygame.Rect(header_rect.x + shimmer_x, header_rect.y + 10, 180, header_rect.height - 20)
        shimmer = pygame.Surface(shimmer_rect.size, pygame.SRCALPHA)
        shimmer.fill((255, 220, 160, 18))
        surface.blit(shimmer, shimmer_rect.topleft)
        pygame.draw.line(surface, (255, 206, 118), (header_rect.x + 26, header_rect.y + 18), (header_rect.x + 196, header_rect.y + 18), 3)

        self._draw_text(surface, layout["title"], (header_rect.x + 28, header_rect.y + 18), self._title_font)
        self._draw_text(
            surface,
            layout["subtitle"],
            (header_rect.x + 30, header_rect.y + 58),
            self._small_font,
            width=640,
            color=(188, 206, 230),
        )

        chips = [
            {"label": "Earned", "value": f"+{layout['credits_granted']} credits", "accent": (255, 212, 120), "emphasis": True},
            {"label": "Total", "value": f"{layout['player_credits']} credits", "accent": (102, 212, 255), "emphasis": False},
            {"label": "Deck", "value": f"{layout['deck_size']} cards", "accent": (132, 238, 184), "emphasis": False},
        ]
        chip_width = 186
        chip_height = 56
        start_x = header_rect.right - 36 - (len(chips) * chip_width) - ((len(chips) - 1) * REWARD_LAYOUT["chip_gap"])
        for index, chip in enumerate(chips):
            chip_rect = pygame.Rect(start_x + index * (chip_width + REWARD_LAYOUT["chip_gap"]), header_rect.y + 28, chip_width, chip_height)
            self._draw_summary_chip(surface, chip_rect, chip["label"], chip["value"], chip["accent"], chip["emphasis"], high_contrast)

    def _draw_hero_section(
        self,
        surface: Any,
        section: dict[str, Any],
        layout: dict[str, Any],
        high_contrast: bool,
    ) -> None:
        panel_rect = section["panel_rect"]
        border = (255, 214, 110) if section["active"] else (94, 124, 162)
        self._draw_panel(surface, panel_rect, fill=(10, 18, 30), border=border, radius=REWARD_LAYOUT["panel_radius"])

        label = "Primary Reward" if section["type"] == "card_offer" else "Optional Reward"
        if layout["can_continue"]:
            label = "Rewards Collected"
        self._draw_section_heading(surface, panel_rect, label, section["title"], section["description"], section, condensed=False)

        if section["resolved"]:
            self._draw_resolved_hero(surface, section, high_contrast)
            return

        if section["type"] == "card_offer":
            self._draw_card_showcase(surface, section, high_contrast)
        else:
            self._draw_purge_showcase(surface, section, high_contrast)

    def _draw_secondary_section(self, surface: Any, section: dict[str, Any]) -> None:
        panel_rect = section["panel_rect"]
        border = (120, 244, 170) if section["resolved"] else (78, 102, 134)
        self._draw_panel(surface, panel_rect, fill=(12, 18, 28), border=border, radius=REWARD_LAYOUT["inner_radius"])

        label = "Optional Utility" if section["type"] == "purge_offer" else "Reward Summary"
        self._draw_section_heading(surface, panel_rect, label, section["title"], section["description"], section, condensed=True)

        summary = self._section_summary(section)
        color = (206, 242, 220) if section["resolved"] else (176, 190, 210)
        self._draw_text(
            surface,
            summary,
            (panel_rect.x + 28, panel_rect.y + 46),
            self._tiny_font,
            width=panel_rect.width - 56,
            color=color,
        )

        if section["type"] == "purge_offer" and not section["resolved"]:
            chip_rect = pygame.Rect(panel_rect.right - 246, panel_rect.y + 22, 220, 28)
            self._draw_chip(surface, chip_rect, "Optional after current choice", (24, 36, 56), (96, 182, 255), self._micro_font)

    def _draw_card_showcase(self, surface: Any, section: dict[str, Any], high_contrast: bool) -> None:
        panel_rect = section["panel_rect"]
        stage_rect = pygame.Rect(panel_rect.x + 34, panel_rect.y + 86, panel_rect.width - 68, panel_rect.height - 118)
        self._draw_panel(surface, stage_rect, fill=(16, 24, 38), border=(52, 76, 110), radius=20)

        selected_option = section["selected_option"]
        selected_text = f"Selected: {selected_option['card']['name']}" if selected_option is not None else "Choose one card to add to your deck."
        self._draw_text(
            surface,
            selected_text,
            (panel_rect.x + 36, panel_rect.y + 58),
            self._small_font,
            width=560,
            color=(236, 243, 255),
        )

        for option in section["option_entries"]:
            base_rect = pygame.Rect(*option["rect"])
            selected = section["selected_option_id"] == option["option_id"]
            hovered = self._hovered_action == option["action_id"]
            pressed = self._pressed_action == option["action_id"]
            render_rect = self._reward_card_render_rect(base_rect, selected=selected, hovered=hovered, pressed=pressed)
            pedestal_rect = pygame.Rect(render_rect).inflate(28, 26)
            pedestal_surface = pygame.Surface(pedestal_rect.size, pygame.SRCALPHA)
            pedestal_color = (255, 204, 120, 26) if selected else (112, 178, 255, 18) if hovered else (92, 110, 142, 14)
            pygame.draw.rect(pedestal_surface, pedestal_color, pedestal_surface.get_rect(), border_radius=26)
            surface.blit(pedestal_surface, pedestal_rect.topleft)

            draw_card(
                surface,
                render_rect,
                option["card"],
                {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._tiny_font},
                variant="full",
                shortcut_label=str(option["shortcut"]) if option["shortcut"] is not None else None,
                selected=selected,
                hovered=hovered,
                pressed=pressed,
                high_contrast=high_contrast,
            )

    def _draw_purge_showcase(self, surface: Any, section: dict[str, Any], high_contrast: bool) -> None:
        panel_rect = section["panel_rect"]
        selected_option = section["selected_option"]
        self._draw_text(
            surface,
            "Remove one card from your deck, or keep the deck as-is.",
            (panel_rect.x + 36, panel_rect.y + 58),
            self._small_font,
            width=640,
            color=(226, 234, 246),
        )

        if selected_option is not None:
            selected_rect = pygame.Rect(panel_rect.right - 324, panel_rect.y + 40, 286, 42)
            self._draw_panel(surface, selected_rect, fill=(22, 32, 48), border=(255, 214, 110), radius=16)
            self._draw_text(
                surface,
                f"Selected for purge: {selected_option['card']['name']}",
                (selected_rect.x + 14, selected_rect.y + 11),
                self._tiny_font,
                width=selected_rect.width - 24,
                color=(255, 235, 188),
            )

        grid_rect = pygame.Rect(panel_rect.x + 34, panel_rect.y + 100, panel_rect.width - 68, panel_rect.height - 132)
        self._draw_panel(surface, grid_rect, fill=(16, 24, 38), border=(54, 74, 104), radius=18)

        for option in section["option_entries"]:
            rect = pygame.Rect(*option["rect"])
            selected = section["selected_option_id"] == option["option_id"]
            hovered = self._hovered_action == option["action_id"]
            pressed = self._pressed_action == option["action_id"]
            self._draw_purge_option(surface, rect, option, selected, hovered, pressed, high_contrast)

    def _draw_resolved_hero(self, surface: Any, section: dict[str, Any], high_contrast: bool) -> None:
        panel_rect = section["panel_rect"]
        summary = self._section_summary(section)
        self._draw_text(
            surface,
            summary,
            (panel_rect.x + 36, panel_rect.y + 66),
            self._small_font,
            width=panel_rect.width - 72,
            color=(204, 242, 222),
        )

        if section["type"] == "card_offer" and section["resolution"] is not None and section["resolution"]["type"] == "claimed":
            claimed = self._selected_option(section)
            if claimed is not None:
                preview_width = 200
                preview_height = int(preview_width * CARD_PORTRAIT_HEIGHT_RATIO)
                preview_rect = pygame.Rect(panel_rect.centerx - (preview_width // 2), panel_rect.y + 102, preview_width, preview_height)
                draw_card(
                    surface,
                    preview_rect,
                    claimed["card"],
                    {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._tiny_font},
                    variant="full",
                    selected=True,
                    high_contrast=high_contrast,
                )
                return

        badge_rect = pygame.Rect(panel_rect.x + 36, panel_rect.y + 110, 210, 34)
        self._draw_chip(surface, badge_rect, "Reward resolved", (20, 44, 38), (132, 238, 184), self._tiny_font)

    def _draw_action_bar(self, surface: Any, layout: dict[str, Any]) -> None:
        action_rect = layout["action_rect"]
        self._draw_panel(surface, action_rect, fill=(10, 16, 28), border=(74, 104, 142), radius=18)
        self._draw_text(
            surface,
            layout["action_hint"],
            (action_rect.x + 20, action_rect.y + 14),
            self._tiny_font,
            width=620,
            color=(196, 208, 226),
        )

        hotkeys = "C continue" if layout["can_continue"] else "1-9 choose  -  Enter confirm  -  X skip"
        self._draw_text(
            surface,
            hotkeys,
            (action_rect.x + 20, action_rect.y + 30),
            self._micro_font,
            width=420,
            color=(120, 138, 164),
        )

        for button in layout["buttons"]:
            self._draw_button(
                surface,
                button["rect"],
                button["label"],
                self._hovered_action == button["action_id"],
                self._pressed_action == button["action_id"],
                button["enabled"],
                kind=button["kind"],
            )

    def _draw_purge_option(
        self,
        surface: Any,
        rect: pygame.Rect,
        option: dict[str, Any],
        selected: bool,
        hovered: bool,
        pressed: bool,
        high_contrast: bool,
    ) -> None:
        card = option["card"]
        type_theme = resolve_card_theme(card)["type_theme"]
        fill = (20, 28, 42)
        border = type_theme["accent"]
        if not selected:
            border = (236, 244, 255) if hovered else (168, 182, 206) if high_contrast else (86, 102, 132)
        if pressed:
            fill = (34, 44, 60)
        self._draw_panel(surface, rect, fill=fill, border=border, radius=14)

        stripe_rect = pygame.Rect(rect.x + 8, rect.y + 7, 8, rect.height - 14)
        pygame.draw.rect(surface, type_theme["accent"], stripe_rect, border_radius=4)

        if option["shortcut"] is not None:
            badge_rect = pygame.Rect(rect.right - 34, rect.y + 10, 24, 22)
            self._draw_chip(surface, badge_rect, str(option["shortcut"]), (18, 24, 36), type_theme["accent"], self._micro_font)

        self._draw_text(surface, card["name"], (rect.x + 28, rect.y + 9), self._tiny_font, width=rect.width - 92, color=(244, 248, 255))
        subtitle = f"{card['type'].title()}  -  Cost {card.get('cost', 0)}"
        self._draw_text(surface, subtitle, (rect.x + 28, rect.y + 24), self._micro_font, width=rect.width - 92, color=type_theme["primary_support"])

    def _option_entries(self, section: dict[str, Any], panel_rect: pygame.Rect, *, role: str) -> list[dict[str, Any]]:
        if section["type"] == "card_offer":
            return self._card_option_entries(section, panel_rect, role=role)
        return self._purge_option_entries(section, panel_rect, role=role)

    def _card_option_entries(self, section: dict[str, Any], panel_rect: pygame.Rect, *, role: str) -> list[dict[str, Any]]:
        if role != "hero":
            return []

        stage_rect = pygame.Rect(panel_rect.x + 34, panel_rect.y + 86, panel_rect.width - 68, panel_rect.height - 118)
        card_zone_width = stage_rect.width - 56
        card_zone_height = stage_rect.height - 34
        count = max(1, len(section["options"]))
        gap = REWARD_LAYOUT["card_gap"]
        card_width = min(216, int((card_zone_width - (gap * (count - 1))) / count))
        card_height = int(card_width * CARD_PORTRAIT_HEIGHT_RATIO)
        max_height = card_zone_height - 6
        if card_height > max_height:
            card_height = max_height
            card_width = int(card_height / CARD_PORTRAIT_HEIGHT_RATIO)
        total_width = (count * card_width) + ((count - 1) * gap)
        while total_width > card_zone_width and gap > 18:
            gap -= 2
            total_width = (count * card_width) + ((count - 1) * gap)
        start_x = stage_rect.x + ((stage_rect.width - total_width) // 2)
        start_y = stage_rect.y + max(8, (stage_rect.height - card_height) // 2)

        entries = []
        for index, option in enumerate(section["options"]):
            entries.append(
                {
                    "action_id": f"option:{section['id']}:{option['option_id']}",
                    "option_id": option["option_id"],
                    "kind": "card",
                    "card": option["card"],
                    "rect": (start_x + (index * (card_width + gap)), start_y, card_width, card_height),
                    "shortcut": index + 1 if index < 9 else None,
                }
            )
        return entries

    def _purge_option_entries(self, section: dict[str, Any], panel_rect: pygame.Rect, *, role: str) -> list[dict[str, Any]]:
        if role != "hero":
            return []

        grid_rect = pygame.Rect(panel_rect.x + 34, panel_rect.y + 100, panel_rect.width - 68, panel_rect.height - 132)
        columns = min(REWARD_LAYOUT["purge_columns"], max(1, len(section["options"])))
        gap = REWARD_LAYOUT["purge_tile_gap"]
        tile_width = int((grid_rect.width - ((columns - 1) * gap) - 16) / columns)
        tile_width = max(160, tile_width)
        entries = []
        for index, option in enumerate(section["options"]):
            row = index // columns
            column = index % columns
            rect = pygame.Rect(
                grid_rect.x + 8 + (column * (tile_width + gap)),
                grid_rect.y + 8 + (row * (REWARD_LAYOUT["purge_tile_height"] + gap)),
                tile_width,
                REWARD_LAYOUT["purge_tile_height"],
            )
            entries.append(
                {
                    "action_id": f"option:{section['id']}:{option['option_id']}",
                    "option_id": option["option_id"],
                    "kind": "purge",
                    "card": option["card"],
                    "rect": rect,
                    "shortcut": index + 1 if index < 9 else None,
                }
            )
        return entries

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "continue":
            if not layout["can_continue"]:
                return {"type": "notice", "message": "Resolve or skip every reward section first.", "level": "error"}
            return {"type": "continue_from_reward"}

        action_type, _, payload = action_id.partition(":")
        if action_type in {"confirm", "skip"}:
            return {
                "type": "confirm_reward_selection" if action_type == "confirm" else "skip_reward_section",
                "section": payload,
            }

        if action_type == "option":
            section_id, _, option_id = payload.partition(":")
            return {"type": "select_reward_option", "section": section_id, "option_id": option_id}

        return {"type": "notice", "message": "Unknown reward action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for section in layout["sections"]:
            for option in section["option_entries"]:
                if point_in_rect(position, option["rect"]):
                    return option["action_id"]
        for button in layout["buttons"]:
            if button["enabled"] and point_in_rect(position, button["rect"]):
                return button["action_id"]
        return None

    def _header_copy(
        self,
        encounter_type: str | None,
        active_section: dict[str, Any] | None,
        can_continue: bool,
    ) -> tuple[str, str]:
        title = "Elite Rewards" if encounter_type == "elite" else "Combat Reward"
        if can_continue:
            return title, "Victory secured. Your rewards are ready and your route is open again."
        if active_section is None:
            return title, "Resolve the remaining reward steps to continue the run."
        if active_section["type"] == "card_offer":
            return title, "Choose the card that best sharpens this run."
        return title, "Take a clean deck if you want it, or skip and keep your momentum."

    def _reward_card_render_rect(
        self,
        rect: pygame.Rect,
        *,
        selected: bool,
        hovered: bool,
        pressed: bool,
    ) -> tuple[int, int, int, int]:
        if pressed:
            return (rect.x, rect.y + 6, rect.width, rect.height)
        if selected:
            grown = rect.inflate(18, 24)
            return (grown.x, grown.y - 10, grown.width, grown.height)
        if hovered:
            grown = rect.inflate(12, 18)
            return (grown.x, grown.y - 6, grown.width, grown.height)
        return rect.x, rect.y, rect.width, rect.height

    def _section_summary(self, section: dict[str, Any]) -> str:
        if section["resolution"] is not None:
            return section["resolution"]["summary"]
        if section["resolved"]:
            return "Resolved."
        if section["type"] == "card_offer":
            return "Resolve this reward to add a card or skip it."
        if section["options"]:
            return "Choose one card to remove after the primary reward, or skip it."
        return "Deck is too small to purge further."

    def _selected_option(self, section: dict[str, Any]) -> dict[str, Any] | None:
        option_id = section.get("selected_option_id")
        resolution = section.get("resolution")
        if option_id is None and isinstance(resolution, dict):
            option_id = resolution.get("option_id")
        if option_id is None:
            return None
        return next((option for option in section["options"] if option["option_id"] == option_id), None)

    def _draw_panel(
        self,
        surface: Any,
        rect: pygame.Rect,
        *,
        fill: tuple[int, int, int],
        border: tuple[int, int, int],
        radius: int,
    ) -> None:
        panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (*fill, 224), panel_surface.get_rect(), border_radius=radius)
        pygame.draw.rect(panel_surface, (*border, 242), panel_surface.get_rect(), 2, border_radius=radius)
        surface.blit(panel_surface, rect.topleft)

    def _draw_summary_chip(
        self,
        surface: Any,
        rect: pygame.Rect,
        label: str,
        value: str,
        accent: tuple[int, int, int],
        emphasis: bool,
        high_contrast: bool,
    ) -> None:
        fill = (24, 34, 48) if not emphasis else (38, 32, 22)
        border = accent if emphasis else (202, 218, 244) if high_contrast else (102, 124, 154)
        self._draw_panel(surface, rect, fill=fill, border=border, radius=18)
        self._draw_text(surface, label, (rect.x + 16, rect.y + 8), self._micro_font, color=(164, 182, 204))
        self._draw_text(surface, value, (rect.x + 16, rect.y + 24), self._small_font, width=rect.width - 28, color=(248, 248, 255))

    def _draw_chip(
        self,
        surface: Any,
        rect: pygame.Rect,
        text: str,
        fill: tuple[int, int, int],
        border: tuple[int, int, int],
        font: Any,
    ) -> None:
        pygame.draw.rect(surface, fill, rect, border_radius=min(14, rect.height // 2))
        pygame.draw.rect(surface, border, rect, 2, border_radius=min(14, rect.height // 2))
        label = font.render(text, True, border)
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_section_heading(
        self,
        surface: Any,
        panel_rect: pygame.Rect,
        label: str,
        title: str,
        description: str,
        section: dict[str, Any],
        *,
        condensed: bool,
    ) -> None:
        label_rect = pygame.Rect(panel_rect.x + 28, panel_rect.y + 18, 160, 26)
        accent = (255, 214, 110) if section["active"] and not section["resolved"] else (132, 238, 184) if section["resolved"] else (102, 212, 255)
        self._draw_chip(surface, label_rect, label, (18, 28, 42), accent, self._micro_font)
        self._draw_text(surface, title, (panel_rect.x + 204, panel_rect.y + 18), self._small_font, color=(244, 248, 255))
        if condensed:
            return
        self._draw_text(
            surface,
            description,
            (panel_rect.x + 204, panel_rect.y + 42),
            self._tiny_font,
            width=panel_rect.width - 240,
            color=(172, 190, 214),
        )

    def _draw_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int] | pygame.Rect,
        label: str,
        hovered: bool,
        pressed: bool,
        enabled: bool,
        *,
        kind: str,
    ) -> None:
        rect = pygame.Rect(rect_tuple)
        if kind == "primary":
            fill = (56, 108, 190) if enabled else (26, 34, 48)
            border = (240, 246, 255) if enabled else (110, 118, 136)
            text_color = (246, 250, 255) if enabled else (152, 164, 182)
            if enabled and hovered:
                fill = (74, 132, 220)
            if enabled and pressed:
                fill = (255, 214, 110)
                border = (255, 214, 110)
                text_color = (18, 24, 36)
        else:
            fill = (18, 26, 38)
            border = (168, 182, 206) if enabled else (104, 112, 128)
            text_color = (228, 236, 248) if enabled else (144, 154, 170)
            if enabled and hovered:
                fill = (28, 38, 56)
            if enabled and pressed:
                fill = (44, 58, 82)

        pygame.draw.rect(surface, fill, rect, border_radius=16)
        pygame.draw.rect(surface, border, rect, 2, border_radius=16)
        label_surface = self._tiny_font.render(label, True, text_color)
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
        color: tuple[int, int, int] = (240, 245, 255),
    ) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return

        self._font_scale = scale
        self._title_font = pygame.font.SysFont("consolas", max(28, int(36 * scale)), bold=True)
        self._font = pygame.font.SysFont("consolas", max(20, int(24 * scale)), bold=True)
        self._small_font = pygame.font.SysFont("consolas", max(16, int(19 * scale)), bold=True)
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))
        self._micro_font = pygame.font.SysFont("consolas", max(10, int(12 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load reward UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((120, 90, 220, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_reward_ui() -> dict[str, Any]:
    ui = RewardUI()
    return ui.build_layout(
        {
            "reward": {
                "encounter_type": "elite",
                "credits_granted": 40,
                "deck_size": 10,
                "can_continue": False,
                "sections": [
                    {
                        "id": "card_offer",
                        "type": "card_offer",
                        "title": "Card Reward",
                        "description": "Choose a card to add.",
                        "options": [
                            {
                                "option_id": "surge_strike_01",
                                "card": {
                                    "id": "surge_strike_01",
                                    "name": "Surge Strike",
                                    "cost": 2,
                                    "type": "attack",
                                    "effects": [{"type": "damage", "value": 12}],
                                },
                            },
                            {
                                "option_id": "firewall_01",
                                "card": {
                                    "id": "firewall_01",
                                    "name": "Firewall",
                                    "cost": 1,
                                    "type": "skill",
                                    "effects": [{"type": "block", "value": 8}],
                                },
                            },
                        ],
                        "selected_option_id": None,
                        "resolved": False,
                        "resolution": None,
                        "can_skip": True,
                    },
                    {
                        "id": "purge_offer",
                        "type": "purge_offer",
                        "title": "Deck Purge",
                        "description": "Choose a card to remove from the deck, or skip it.",
                        "options": [
                            {
                                "option_id": "purge_0",
                                "card": {
                                    "id": "strike_01",
                                    "name": "Strike",
                                    "cost": 1,
                                    "type": "attack",
                                    "effects": [{"type": "damage", "value": 6}],
                                },
                            }
                        ],
                        "selected_option_id": None,
                        "resolved": False,
                        "resolution": None,
                        "can_skip": True,
                    },
                ],
            },
            "player": {"credits": 40},
            "presentation": {"ui_scale": 1.0},
        }
    )
