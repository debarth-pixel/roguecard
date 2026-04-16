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
from ui.relic_assets import relic_assets
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.ui_system import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_LINE,
    COLOR_LINE_SOFT,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PANEL_ELEVATED,
    COLOR_TEXT,
    RADIUS_LG,
    RADIUS_MD,
    draw_background_stage,
    draw_chip,
    draw_hint_row,
    draw_panel,
)


REWARD_LAYOUT = {
    "header_rect": (64, 76, 1152, 92),
    "stage_rect": (64, 190, 1152, 420),
    "action_rect": (64, 632, 1152, 48),
    "card_gap": 24,
    "purge_columns": 4,
    "purge_tile_height": 86,
    "purge_tile_gap": 12,
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
        display_section = active_section
        if display_section is None and sections:
            display_section = sections[-1]

        action_rect = pygame.Rect(*REWARD_LAYOUT["action_rect"])
        stage_rect = pygame.Rect(*REWARD_LAYOUT["stage_rect"])
        option_entries = self._active_option_entries(display_section, stage_rect) if display_section is not None and not reward["can_continue"] else []
        button_layout = self._build_action_buttons(action_rect, display_section, reward["can_continue"])
        step_index = 0
        if display_section is not None:
            step_index = next((index for index, section in enumerate(sections) if section["id"] == display_section["id"]), 0)
        return {
            "encounter_type": reward["encounter_type"],
            "title": self._reward_title(reward["encounter_type"]),
            "subtitle": self._reward_subtitle(reward["encounter_type"], display_section, reward["can_continue"], reward["credits_granted"]),
            "credits_granted": reward["credits_granted"],
            "deck_size": reward["deck_size"],
            "sections": sections,
            "display_section": display_section,
            "active_section": active_section,
            "can_continue": reward["can_continue"],
            "header_rect": pygame.Rect(*REWARD_LAYOUT["header_rect"]),
            "stage_rect": stage_rect,
            "action_rect": action_rect,
            "buttons": button_layout["buttons"],
            "action_hint": button_layout["hint"],
            "continue_rect": button_layout.get("continue_rect"),
            "option_entries": option_entries,
            "step_label": "Rewards Locked" if reward["can_continue"] else f"Step {step_index + 1} of {max(1, len(sections))}",
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
        confirm_label = "Confirm"
        if active_section["type"] == "relic_offer":
            confirm_label = "Take Relic"
        elif active_section["type"] == "card_offer":
            confirm_label = "Take Card"
        elif active_section["type"] == "purge_offer":
            confirm_label = "Purge Card"
        buttons.append(
            {
                "action_id": f"confirm:{active_section['id']}",
                "label": confirm_label,
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
            "Pick 1 relic to add to this run."
            if active_section["type"] == "relic_offer"
            else
            "Pick 1 card to add to the deck, or skip it."
            if active_section["type"] == "card_offer"
            else "Choose a card to remove from the deck, or skip and keep your build intact."
        )
        return {"hint": hint, "buttons": buttons}

    def render(self, surface: Any, reward_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(reward_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = reward_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(reward_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())

        draw_background_stage(surface, background, veil_alpha=174, top_band_height=70, bottom_band_height=94, line_step=54, line_alpha=7)
        self._draw_header_clean(surface, layout)
        self._draw_stage_clean(surface, layout, high_contrast)
        self._draw_action_bar_clean(surface, layout)

    def _draw_header_clean(self, surface: Any, layout: dict[str, Any]) -> None:
        header_rect = layout["header_rect"]
        draw_panel(surface, header_rect, accent=COLOR_LINE, fill=COLOR_PANEL_ELEVATED, radius=RADIUS_LG, border_width=1, shadow_alpha=0)
        self._draw_text(surface, layout["title"], (header_rect.x + 22, header_rect.y + 14), self._title_font)
        self._draw_text(surface, layout["subtitle"], (header_rect.x + 22, header_rect.y + 48), self._tiny_font, width=720, color=COLOR_MUTED)
        step_rect = pygame.Rect(header_rect.right - 314, header_rect.y + 18, 130, 28)
        credit_rect = pygame.Rect(header_rect.right - 168, header_rect.y + 18, 144, 28)
        draw_chip(surface, step_rect, label=layout["step_label"], font=self._tiny_font, accent=COLOR_CYAN, fill=COLOR_PANEL, active=not layout["can_continue"])
        draw_chip(surface, credit_rect, label=f"+{layout['credits_granted']} cr", font=self._tiny_font, accent=COLOR_GOLD, fill=COLOR_PANEL)

    def _draw_stage_clean(self, surface: Any, layout: dict[str, Any], high_contrast: bool) -> None:
        stage_rect = layout["stage_rect"]
        draw_panel(surface, stage_rect, accent=COLOR_LINE, fill=COLOR_PANEL, radius=RADIUS_LG, border_width=1, shadow_alpha=0)
        section = layout["display_section"]
        if section is None:
            return
        self._draw_text(surface, section["title"], (stage_rect.x + 28, stage_rect.y + 22), self._font)
        self._draw_text(surface, section["description"], (stage_rect.x + 28, stage_rect.y + 54), self._tiny_font, width=stage_rect.width - 56, color=COLOR_MUTED)
        if layout["can_continue"]:
            self._draw_completed_reward_stage(surface, stage_rect, layout, high_contrast)
            return
        if section["type"] == "relic_offer":
            self._draw_relic_reward_stage(surface, stage_rect, layout, high_contrast)
        elif section["type"] == "card_offer":
            self._draw_card_reward_stage(surface, stage_rect, layout, high_contrast)
        else:
            self._draw_purge_reward_stage(surface, stage_rect, layout, high_contrast)

    def _draw_relic_reward_stage(self, surface: Any, stage_rect: pygame.Rect, layout: dict[str, Any], high_contrast: bool) -> None:
        del high_contrast
        section = layout["display_section"]
        selected_option = self._selected_option(section)
        if selected_option is not None:
            self._draw_text(surface, f"Selected: {selected_option['relic']['name']}", (stage_rect.x + 28, stage_rect.y + 84), self._tiny_font, width=360)
        for option in layout["option_entries"]:
            rect = pygame.Rect(*option["rect"])
            selected = section["selected_option_id"] == option["option_id"]
            hovered = self._hovered_action == option["action_id"]
            pressed = self._pressed_action == option["action_id"]
            self._draw_relic_option_clean(surface, rect, option, selected, hovered, pressed)

    def _draw_card_reward_stage(self, surface: Any, stage_rect: pygame.Rect, layout: dict[str, Any], high_contrast: bool) -> None:
        section = layout["display_section"]
        for option in layout["option_entries"]:
            base_rect = pygame.Rect(*option["rect"])
            selected = section["selected_option_id"] == option["option_id"]
            hovered = self._hovered_action == option["action_id"]
            pressed = self._pressed_action == option["action_id"]
            render_rect = self._reward_card_render_rect(base_rect, selected=selected, hovered=hovered, pressed=pressed)
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
        self._draw_text(surface, "Pick 1 of 3 and confirm, or skip.", (stage_rect.x + 28, stage_rect.bottom - 44), self._tiny_font, width=360, color=COLOR_MUTED)

    def _draw_purge_reward_stage(self, surface: Any, stage_rect: pygame.Rect, layout: dict[str, Any], high_contrast: bool) -> None:
        section = layout["display_section"]
        grid_rect = pygame.Rect(stage_rect.x + 28, stage_rect.y + 92, stage_rect.width - 380, stage_rect.height - 124)
        preview_rect = pygame.Rect(stage_rect.right - 320, stage_rect.y + 92, 292, stage_rect.height - 124)
        draw_panel(surface, grid_rect, accent=COLOR_LINE_SOFT, fill=COLOR_PANEL_ELEVATED, radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        draw_panel(surface, preview_rect, accent=COLOR_LINE_SOFT, fill=COLOR_PANEL_ELEVATED, radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        preview_option = self._selected_option(section)
        if preview_option is None and section["options"]:
            preview_option = section["options"][0]

        for option in layout["option_entries"]:
            rect = pygame.Rect(*option["rect"])
            selected = section["selected_option_id"] == option["option_id"]
            hovered = self._hovered_action == option["action_id"]
            pressed = self._pressed_action == option["action_id"]
            draw_card(
                surface,
                rect,
                option["card"],
                {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._tiny_font},
                variant="mini",
                shortcut_label=str(option["shortcut"]) if option["shortcut"] is not None else None,
                selected=selected,
                hovered=hovered,
                pressed=pressed,
                high_contrast=high_contrast,
            )

        self._draw_text(surface, "Preview", (preview_rect.x + 18, preview_rect.y + 14), self._tiny_font, color=COLOR_MUTED)
        if preview_option is not None:
            preview_card_rect = pygame.Rect(preview_rect.x + 22, preview_rect.y + 42, 248, int(248 * CARD_PORTRAIT_HEIGHT_RATIO))
            draw_card(
                surface,
                preview_card_rect,
                preview_option["card"],
                {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._tiny_font},
                variant="full",
                selected=True,
                high_contrast=high_contrast,
            )

    def _draw_completed_reward_stage(self, surface: Any, stage_rect: pygame.Rect, layout: dict[str, Any], high_contrast: bool) -> None:
        del high_contrast
        y = stage_rect.y + 94
        for section in layout["sections"]:
            summary_rect = pygame.Rect(stage_rect.x + 28, y, stage_rect.width - 56, 64)
            draw_panel(
                surface,
                summary_rect,
                accent=COLOR_GOLD if section["type"] == "relic_offer" else COLOR_LINE_SOFT,
                fill=COLOR_PANEL_ELEVATED,
                radius=RADIUS_MD,
                border_width=1,
                shadow_alpha=0,
            )
            self._draw_text(surface, section["title"], (summary_rect.x + 18, summary_rect.y + 12), self._tiny_font, width=200)
            self._draw_text(
                surface,
                self._section_summary(section),
                (summary_rect.x + 18, summary_rect.y + 32),
                self._tiny_font,
                width=summary_rect.width - 36,
                color=COLOR_MUTED,
            )
            y += 76

    def _draw_action_bar_clean(self, surface: Any, layout: dict[str, Any]) -> None:
        hint_text = layout["action_hint"]
        right_hint = "C continue" if layout["can_continue"] else "1-9 choose  |  Enter confirm  |  X skip"
        draw_hint_row(
            surface,
            layout["action_rect"],
            left_text=hint_text,
            right_text=right_hint,
            font=self._tiny_font,
            accent=COLOR_LINE,
            fill=COLOR_PANEL_ELEVATED,
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

    def _active_option_entries(self, section: dict[str, Any] | None, stage_rect: pygame.Rect) -> list[dict[str, Any]]:
        if section is None:
            return []
        if section["type"] == "card_offer":
            zone_rect = pygame.Rect(stage_rect.x + 46, stage_rect.y + 92, stage_rect.width - 92, stage_rect.height - 132)
            count = max(1, len(section["options"]))
            gap = REWARD_LAYOUT["card_gap"]
            card_width = min(214, int((zone_rect.width - (gap * (count - 1))) / count))
            card_height = int(card_width * CARD_PORTRAIT_HEIGHT_RATIO)
            if card_height > zone_rect.height:
                card_height = zone_rect.height
                card_width = int(card_height / CARD_PORTRAIT_HEIGHT_RATIO)
            total_width = (card_width * count) + (gap * (count - 1))
            start_x = zone_rect.x + max(0, (zone_rect.width - total_width) // 2)
            start_y = zone_rect.y + max(0, (zone_rect.height - card_height) // 2)
            return [
                {
                    "action_id": f"option:{section['id']}:{option['option_id']}",
                    "option_id": option["option_id"],
                    "card": option["card"],
                    "rect": (start_x + (index * (card_width + gap)), start_y, card_width, card_height),
                    "shortcut": index + 1 if index < 9 else None,
                }
                for index, option in enumerate(section["options"])
            ]
        if section["type"] == "relic_offer":
            zone_rect = pygame.Rect(stage_rect.x + 28, stage_rect.y + 108, stage_rect.width - 56, stage_rect.height - 146)
            count = max(1, len(section["options"]))
            gap = 18
            tile_width = min(312, int((zone_rect.width - (gap * (count - 1))) / count))
            tile_height = min(210, zone_rect.height)
            total_width = (tile_width * count) + (gap * (count - 1))
            start_x = zone_rect.x + max(0, (zone_rect.width - total_width) // 2)
            start_y = zone_rect.y + max(0, (zone_rect.height - tile_height) // 2)
            return [
                {
                    "action_id": f"option:{section['id']}:{option['option_id']}",
                    "option_id": option["option_id"],
                    "relic_id": option["relic_id"],
                    "relic": option["relic"],
                    "rect": (start_x + (index * (tile_width + gap)), start_y, tile_width, tile_height),
                    "shortcut": index + 1 if index < 9 else None,
                }
                for index, option in enumerate(section["options"])
            ]
        grid_rect = pygame.Rect(stage_rect.x + 40, stage_rect.y + 104, stage_rect.width - 404, stage_rect.height - 148)
        columns = min(REWARD_LAYOUT["purge_columns"], max(1, len(section["options"])))
        gap = REWARD_LAYOUT["purge_tile_gap"]
        tile_width = int((grid_rect.width - ((columns - 1) * gap)) / columns)
        entries = []
        for index, option in enumerate(section["options"]):
            row = index // columns
            column = index % columns
            rect = pygame.Rect(
                grid_rect.x + (column * (tile_width + gap)),
                grid_rect.y + (row * (REWARD_LAYOUT["purge_tile_height"] + gap)),
                tile_width,
                REWARD_LAYOUT["purge_tile_height"],
            )
            entries.append(
                {
                    "action_id": f"option:{section['id']}:{option['option_id']}",
                    "option_id": option["option_id"],
                    "card": option["card"],
                    "rect": rect,
                    "shortcut": index + 1 if index < 9 else None,
                }
            )
        return entries

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

        label = (
            "Relic Choice"
            if section["type"] == "relic_offer"
            else "Card Choice"
            if section["type"] == "card_offer"
            else "Deck Purge"
        )
        if layout["can_continue"]:
            label = "Rewards Collected"
        self._draw_section_heading(surface, panel_rect, label, section["title"], section["description"], section, condensed=False)

        if section["resolved"]:
            self._draw_resolved_hero(surface, section, high_contrast)
            return

        if section["type"] == "relic_offer":
            self._draw_relic_showcase(surface, section, high_contrast)
        elif section["type"] == "card_offer":
            self._draw_card_showcase(surface, section, high_contrast)
        else:
            self._draw_purge_showcase(surface, section, high_contrast)

    def _draw_secondary_section(self, surface: Any, section: dict[str, Any]) -> None:
        panel_rect = section["panel_rect"]
        border = (120, 244, 170) if section["resolved"] else (78, 102, 134)
        self._draw_panel(surface, panel_rect, fill=(12, 18, 28), border=border, radius=REWARD_LAYOUT["inner_radius"])

        label = (
            "Relic Choice"
            if section["type"] == "relic_offer"
            else "Deck Purge"
            if section["type"] == "purge_offer"
            else "Card Choice"
        )
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

    def _draw_relic_showcase(self, surface: Any, section: dict[str, Any], high_contrast: bool) -> None:
        panel_rect = section["panel_rect"]
        stage_rect = pygame.Rect(panel_rect.x + 34, panel_rect.y + 86, panel_rect.width - 68, panel_rect.height - 118)
        self._draw_panel(surface, stage_rect, fill=(16, 24, 38), border=(52, 76, 110), radius=20)

        selected_option = section["selected_option"]
        selected_text = (
            f"Selected: {selected_option['relic']['name']}"
            if selected_option is not None
            else "Choose one relic to add to this run."
        )
        self._draw_text(
            surface,
            selected_text,
            (panel_rect.x + 36, panel_rect.y + 58),
            self._small_font,
            width=560,
            color=(236, 243, 255),
        )

        for option in section["option_entries"]:
            rect = pygame.Rect(*option["rect"])
            selected = section["selected_option_id"] == option["option_id"]
            hovered = self._hovered_action == option["action_id"]
            pressed = self._pressed_action == option["action_id"]
            self._draw_relic_option(surface, rect, option, selected, hovered, pressed, high_contrast)

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
        if section["type"] == "relic_offer" and section["resolution"] is not None and section["resolution"]["type"] == "claimed":
            claimed = self._selected_option(section)
            if claimed is not None:
                preview_rect = pygame.Rect(panel_rect.centerx - 220, panel_rect.y + 110, 440, 142)
                palette = self._relic_palette(claimed["relic"])
                self._draw_panel(surface, preview_rect, fill=palette["fill"], border=palette["border"], radius=20)
                art_rect = pygame.Rect(preview_rect.x + 18, preview_rect.y + 18, 106, 106)
                pygame.draw.rect(surface, palette["art_fill"], art_rect, border_radius=18)
                art = relic_assets.get_relic_art(claimed["relic_id"], art_rect.inflate(-12, -12).size)
                if art is not None:
                    art_dest = art.get_rect(center=art_rect.center)
                    surface.blit(art, art_dest.topleft)
                else:
                    self._draw_text(
                        surface,
                        "Relic",
                        (art_rect.x + 22, art_rect.y + 42),
                        self._tiny_font,
                        width=art_rect.width - 28,
                        color=palette["accent"],
                    )
                self._draw_text(surface, claimed["relic"]["name"], (preview_rect.x + 142, preview_rect.y + 22), self._small_font, width=260, color=(248, 248, 255))
                self._draw_chip(
                    surface,
                    pygame.Rect(preview_rect.x + 142, preview_rect.y + 58, 96, 26),
                    str(claimed["relic"].get("rarity", "common")).title(),
                    palette["pill_fill"],
                    palette["accent"],
                    self._micro_font,
                )
                self._draw_text(
                    surface,
                    claimed["relic"].get("description", "No description."),
                    (preview_rect.x + 142, preview_rect.y + 90),
                    self._tiny_font,
                    width=270,
                    color=(208, 220, 236),
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
        if section["type"] == "relic_offer":
            return self._relic_option_entries(section, panel_rect, role=role)
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

    def _relic_option_entries(self, section: dict[str, Any], panel_rect: pygame.Rect, *, role: str) -> list[dict[str, Any]]:
        if role != "hero":
            return []

        stage_rect = pygame.Rect(panel_rect.x + 34, panel_rect.y + 86, panel_rect.width - 68, panel_rect.height - 118)
        tile_gap = 20
        count = max(1, len(section["options"]))
        tile_width = min(280, int((stage_rect.width - (tile_gap * (count - 1))) / count))
        tile_height = min(stage_rect.height - 16, 222)
        total_width = (tile_width * count) + (tile_gap * (count - 1))
        start_x = stage_rect.x + max(8, (stage_rect.width - total_width) // 2)
        start_y = stage_rect.y + max(8, (stage_rect.height - tile_height) // 2)

        entries = []
        for index, option in enumerate(section["options"]):
            entries.append(
                {
                    "action_id": f"option:{section['id']}:{option['option_id']}",
                    "option_id": option["option_id"],
                    "kind": "relic",
                    "relic_id": option["relic_id"],
                    "relic": option["relic"],
                    "rect": (start_x + (index * (tile_width + tile_gap)), start_y, tile_width, tile_height),
                    "shortcut": index + 1 if index < 9 else None,
                }
            )
        return entries

    def _reward_title(self, encounter_type: str | None) -> str:
        if encounter_type == "boss":
            return "Boss Reward"
        if encounter_type == "elite":
            return "Elite Reward"
        return "Combat Reward"

    def _reward_subtitle(
        self,
        encounter_type: str | None,
        active_section: dict[str, Any] | None,
        can_continue: bool,
        credits_granted: int,
    ) -> str:
        if can_continue:
            return "Resolve the route when you are ready."
        if active_section is None:
            return f"+{credits_granted} credits secured."
        if active_section["type"] == "relic_offer":
            return "Choose the relic that best reinforces this run."
        if active_section["type"] == "card_offer":
            if encounter_type == "boss":
                return "Choose the card that best prepares the next map."
            return "Pick 1 of 3 and move on."
        return "Clean the deck if you want the trim, or skip and keep the build as-is."

    def _draw_relic_option_clean(
        self,
        surface: Any,
        rect: pygame.Rect,
        option: dict[str, Any],
        selected: bool,
        hovered: bool,
        pressed: bool,
    ) -> None:
        palette = self._relic_palette(option["relic"])
        accent = palette["accent"] if selected or hovered else palette["border"]
        fill = palette["fill_selected"] if selected else palette["fill_hover"] if hovered else palette["fill"]
        if pressed:
            fill = palette["pill_fill"]
            accent = palette["accent"]
        draw_panel(
            surface,
            rect,
            accent=accent,
            fill=fill,
            radius=RADIUS_MD,
            border_width=2 if selected or hovered else 1,
            shadow_alpha=0,
        )
        if option["shortcut"] is not None:
            chip_rect = pygame.Rect(rect.right - 36, rect.y + 12, 24, 24)
            draw_chip(surface, chip_rect, label=str(option["shortcut"]), font=self._micro_font, accent=accent, fill=COLOR_PANEL_ELEVATED)

        icon_rect = pygame.Rect(rect.x + 18, rect.y + 18, 56, 56)
        pygame.draw.rect(surface, palette["pill_fill"], icon_rect, border_radius=14)
        art = relic_assets.get_relic_art(option["relic_id"], icon_rect.inflate(-14, -14).size)
        if art is not None:
            art_dest = art.get_rect(center=icon_rect.center)
            surface.blit(art, art_dest.topleft)
        else:
            self._draw_text(surface, option["relic"]["name"][:1], (icon_rect.x + 20, icon_rect.y + 12), self._small_font, color=(18, 24, 36))
        self._draw_text(surface, option["relic"]["name"], (rect.x + 92, rect.y + 20), self._small_font, width=rect.width - 110, color=COLOR_TEXT)
        rarity_rect = pygame.Rect(rect.x + 92, rect.y + 52, 100, 24)
        draw_chip(
            surface,
            rarity_rect,
            label=str(option["relic"].get("rarity", "common")).title(),
            font=self._micro_font,
            accent=accent,
            fill=COLOR_PANEL,
        )
        self._draw_text(
            surface,
            option["relic"].get("description", "No description."),
            (rect.x + 18, rect.y + 92),
            self._tiny_font,
            width=rect.width - 36,
            color=COLOR_MUTED,
        )

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
        for option in layout["option_entries"]:
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
        if encounter_type == "boss":
            title = "Checkpoint Reward"
        else:
            title = "Elite Rewards" if encounter_type == "elite" else "Combat Reward"
        if can_continue:
            if encounter_type == "boss":
                return title, "Checkpoint secured. Continue when you are ready to enter the next map."
            return title, "Victory secured. Your rewards are ready and your route is open again."
        if active_section is None:
            return title, "Resolve the remaining reward steps to continue the run."
        if active_section["type"] == "relic_offer":
            return title, "Choose the relic that best reinforces this build."
        if active_section["type"] == "card_offer":
            if encounter_type == "boss":
                return title, "Choose the reward that best prepares the next map."
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
        if section["type"] == "relic_offer":
            return "Choose one relic to claim this reward."
        if section["type"] == "card_offer":
            return "Resolve this reward to add a card or skip it."
        if section["options"]:
            return "Choose one card to remove after the primary reward, or skip it."
        return "Deck is too small to purge further."

    def _draw_relic_option(
        self,
        surface: Any,
        rect: pygame.Rect,
        option: dict[str, Any],
        selected: bool,
        hovered: bool,
        pressed: bool,
        high_contrast: bool,
    ) -> None:
        palette = self._relic_palette(option["relic"])
        fill = palette["fill_selected"] if selected else palette["fill_hover"] if hovered else palette["fill"]
        border = palette["accent"] if selected or hovered else palette["border"]
        if high_contrast and not selected and not hovered:
            border = (232, 238, 246)
        if pressed:
            fill = palette["pill_fill"]
            border = palette["accent"]
        self._draw_panel(surface, rect, fill=fill, border=border, radius=22)

        art_rect = pygame.Rect(rect.x + 16, rect.y + 16, rect.width - 32, 84)
        pygame.draw.rect(surface, palette["art_fill"], art_rect, border_radius=18)
        art = relic_assets.get_relic_art(option["relic_id"], art_rect.inflate(-18, -18).size)
        if art is not None:
            art_dest = art.get_rect(center=art_rect.center)
            surface.blit(art, art_dest.topleft)
        else:
            self._draw_text(
                surface,
                "Relic",
                (art_rect.x + 18, art_rect.y + 28),
                self._tiny_font,
                width=art_rect.width - 36,
                color=palette["accent"],
            )

        if option["shortcut"] is not None:
            shortcut_rect = pygame.Rect(rect.right - 34, rect.y + 12, 22, 22)
            self._draw_chip(surface, shortcut_rect, str(option["shortcut"]), (16, 24, 38), palette["accent"], self._micro_font)

        self._draw_text(surface, option["relic"]["name"], (rect.x + 18, rect.y + 110), self._tiny_font, width=rect.width - 36, color=(246, 248, 255))
        rarity_rect = pygame.Rect(rect.x + 18, rect.y + 138, 94, 24)
        self._draw_chip(surface, rarity_rect, str(option["relic"].get("rarity", "common")).title(), palette["pill_fill"], palette["accent"], self._micro_font)
        self._draw_text(
            surface,
            option["relic"].get("description", "No description."),
            (rect.x + 18, rect.y + 170),
            self._micro_font,
            width=rect.width - 36,
            color=(204, 216, 234),
        )

    def _relic_palette(self, relic: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
        rarity = str(relic.get("rarity", "common")).lower()
        palettes = {
            "common": {
                "fill": (24, 30, 44),
                "fill_hover": (30, 38, 56),
                "fill_selected": (40, 52, 76),
                "border": (108, 132, 168),
                "accent": (148, 188, 255),
                "pill_fill": (22, 44, 74),
                "art_fill": (18, 24, 38),
            },
            "uncommon": {
                "fill": (20, 38, 34),
                "fill_hover": (26, 50, 42),
                "fill_selected": (34, 68, 54),
                "border": (102, 170, 146),
                "accent": (144, 230, 188),
                "pill_fill": (20, 58, 48),
                "art_fill": (16, 32, 28),
            },
            "rare": {
                "fill": (38, 26, 18),
                "fill_hover": (54, 34, 22),
                "fill_selected": (76, 48, 24),
                "border": (210, 160, 98),
                "accent": (255, 214, 118),
                "pill_fill": (72, 42, 16),
                "art_fill": (34, 22, 16),
            },
        }
        return palettes.get(rarity, palettes["common"])

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
