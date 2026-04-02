from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    HELP_PANEL_HEIGHT,
    HELP_PANEL_WIDTH,
    MAX_PRESENTATION_SCALE,
    MAX_UI_SCALE,
    MIN_PRESENTATION_SCALE,
    MIN_UI_SCALE,
    PRESENTATION_SCALE_STEP,
    SETTINGS_PANEL_HEIGHT,
    SETTINGS_PANEL_WIDTH,
    UI_SCALE_STEP,
    VOLUME_STEP,
    resolve_asset_path,
)
from ui.combat_ui import CombatUI
from ui.event_ui import EventUI
from ui.map_ui import MapUI
from ui.reward_ui import RewardUI
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.shop_ui import ShopUI


class UIManager:
    def __init__(self) -> None:
        self.combat_ui = CombatUI()
        self.event_ui = EventUI()
        self.map_ui = MapUI()
        self.reward_ui = RewardUI()
        self.shop_ui = ShopUI()
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._settings_hovered_action: str | None = None
        self._settings_pressed_action: str | None = None
        self._settings_selected_index = 0

    def preload_assets(self) -> None:
        self.map_ui.preload_assets()
        self.combat_ui.preload_assets()
        self.event_ui.preload_assets()
        self.reward_ui.preload_assets()
        self.shop_ui.preload_assets()
        if pygame is None:
            return
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("ui", "banner_victory.png"),
            resolve_asset_path("ui", "banner_game_over.png"),
        ):
            self._load_image(path)

    def handle_event(self, event: Any, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        presentation = state_snapshot.get("presentation", {})
        if presentation.get("settings_open"):
            return self._handle_settings_event(event, presentation)

        current_state = state_snapshot["current_state"]

        if current_state == "combat" and state_snapshot["combat"] is not None:
            action = self.combat_ui.handle_event(event, self._combat_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "reward" and state_snapshot["reward"] is not None:
            action = self.reward_ui.handle_event(event, self._reward_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "event" and state_snapshot["event"] is not None:
            action = self.event_ui.handle_event(event, self._event_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "shop" and state_snapshot["shop"] is not None:
            action = self.shop_ui.handle_event(event, self._shop_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "map" and state_snapshot["map"] is not None:
            action = self.map_ui.handle_event(event, self._map_view_state(state_snapshot))
            if action is not None:
                return action

        if pygame is not None and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                return {"type": "new_run"}
            if current_state in {"victory", "game_over"} and event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                return {"type": "new_run"}

        return None

    def render(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(state_snapshot.get("presentation", {}).get("ui_scale", 1.0))
        current_state = state_snapshot["current_state"]

        if current_state == "combat" and state_snapshot["combat"] is not None:
            self.combat_ui.render(surface, self._combat_view_state(state_snapshot))
        elif current_state == "event" and state_snapshot["event"] is not None:
            self.event_ui.render(surface, self._event_view_state(state_snapshot))
        elif current_state == "reward" and state_snapshot["reward"] is not None:
            self.reward_ui.render(surface, self._reward_view_state(state_snapshot))
        elif current_state == "shop" and state_snapshot["shop"] is not None:
            self.shop_ui.render(surface, self._shop_view_state(state_snapshot))
        elif current_state == "map" and state_snapshot["map"] is not None:
            self.map_ui.render(surface, self._map_view_state(state_snapshot))
        elif current_state in {"victory", "game_over"}:
            self._render_status_screen(surface, self._status_screen_layout(state_snapshot))
        else:
            surface.fill((18, 21, 28))

        self._render_top_bar(surface, state_snapshot)
        self._render_notice(
            surface,
            state_snapshot.get("ui_notice"),
            state_snapshot.get("presentation", {}),
            current_state,
        )

        presentation = state_snapshot.get("presentation", {})
        if presentation.get("settings_open"):
            self._render_settings_overlay(surface, presentation)
        elif presentation.get("show_help"):
            self._render_help_overlay(surface, current_state, presentation)

    def simulate_ui(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        if state_snapshot["current_state"] == "combat" and state_snapshot["combat"] is not None:
            return self.combat_ui.build_layout(self._combat_view_state(state_snapshot))
        if state_snapshot["current_state"] == "event" and state_snapshot["event"] is not None:
            return self.event_ui.build_layout(self._event_view_state(state_snapshot))
        if state_snapshot["current_state"] == "reward" and state_snapshot["reward"] is not None:
            return self.reward_ui.build_layout(self._reward_view_state(state_snapshot))
        if state_snapshot["current_state"] == "shop" and state_snapshot["shop"] is not None:
            return self.shop_ui.build_layout(self._shop_view_state(state_snapshot))
        if state_snapshot["current_state"] == "map" and state_snapshot["map"] is not None:
            return self.map_ui.build_layout(self._map_view_state(state_snapshot))
        if state_snapshot["current_state"] in {"victory", "game_over"}:
            return self._status_screen_layout(state_snapshot)
        return {"status_message": state_snapshot["status_message"]}

    def _combat_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        combat_state = state_snapshot["combat"]
        hand = state_snapshot.get("player_hand") or []
        return {
            "status_message": state_snapshot["status_message"],
            "player": combat_state["player"],
            "enemies": combat_state["enemies"],
            "turn_number": combat_state.get("turn_number", 0),
            "turn_owner": combat_state.get("turn_owner", "player"),
            "living_enemy_ids": combat_state.get("living_enemy_ids", []),
            "event_log": combat_state.get("event_log", []),
            "player_hand": hand,
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _map_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            **state_snapshot["map"],
            "status_message": state_snapshot["status_message"],
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _reward_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "status_message": state_snapshot["status_message"],
            "reward": state_snapshot["reward"],
            "player": state_snapshot["player"],
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _event_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "status_message": state_snapshot["status_message"],
            "event": state_snapshot["event"],
            "player": state_snapshot["player"],
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _shop_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "status_message": state_snapshot["status_message"],
            "shop": state_snapshot["shop"],
            "player": state_snapshot["player"],
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _status_screen_layout(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        is_victory = state_snapshot["current_state"] == "victory"
        return {
            "title": "RUN COMPLETE" if is_victory else "RUN FAILED",
            "subtitle": state_snapshot["status_message"],
            "prompt": "Press Enter, Space, or N to start a new run.",
            "banner": "banner_victory.png" if is_victory else "banner_game_over.png",
            "chips": [
                "H: controls",
                "S: settings",
                "F11: windowed" if state_snapshot.get("presentation", {}).get("fullscreen") else "F11: fullscreen",
                "N: new run",
            ],
        }

    def _render_status_screen(self, surface: Any, layout: dict[str, Any]) -> None:
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (760, 280))
        banner = self._scaled_image(resolve_asset_path("ui", layout["banner"]), (760, 180))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176)
        surface.blit(panel, (260, 220))
        surface.blit(banner, (260, 58))

        self._draw_text(surface, layout["subtitle"], (330, 348), self._small_font, width=620)
        self._draw_text(surface, layout["prompt"], (356, 420), self._small_font, width=580)

        chip_x = 314
        for chip in layout["chips"]:
            chip_width = max(132, self._tiny_font.size(chip)[0] + 24)
            self._draw_chip(surface, chip, (chip_x, 462), chip_width, accent=(126, 140, 168))
            chip_x += chip_width + 12

    def _render_top_bar(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        presentation = state_snapshot.get("presentation", {})
        high_contrast = presentation.get("high_contrast", False)
        chip_border = (220, 230, 255) if high_contrast else (105, 120, 150)
        current_state = state_snapshot["current_state"]
        compact_state = current_state in {"combat", "reward", "shop", "event"}
        panel_size = (1232, 48) if compact_state else (1232, 68)
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), panel_size)
        surface.blit(panel, (24, 10))

        state_label = current_state.replace("_", " ").title()
        run_seed = state_snapshot.get("run_seed")
        left_text = f"{state_label} | Seed {run_seed}" if run_seed is not None else state_label
        self._draw_text(surface, left_text, (44, 20 if compact_state else 26), self._small_font)
        if not compact_state:
            self._draw_text(surface, state_snapshot["status_message"], (330, 26), self._small_font, width=420)

        audio_chip = "Muted" if presentation.get("muted") else f"Audio {int(presentation.get('master_volume', 0) * 100)}%"
        chips = [
            "Fast On" if presentation.get("fast_mode") else "Fast Off",
            audio_chip,
            "Settings",
        ]
        chip_x = 786 if compact_state else 796
        for chip in chips:
            chip_width = max(90, self._tiny_font.size(chip)[0] + 18)
            self._draw_chip(surface, chip, (chip_x, 15 if compact_state else 21), chip_width, accent=chip_border)
            chip_x += chip_width + 8

    def _render_notice(
        self,
        surface: Any,
        notice: dict[str, Any] | None,
        presentation: dict[str, Any],
        current_state: str,
    ) -> None:
        if not notice:
            return

        colors = {
            "info": (55, 120, 210),
            "success": (40, 170, 110),
            "error": (210, 70, 90),
        }
        accent = colors.get(notice.get("level", "info"), colors["info"])
        if presentation.get("high_contrast"):
            accent = tuple(min(255, channel + 25) for channel in accent)
        if current_state in {"combat", "reward", "shop", "event"}:
            panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (700, 54))
            panel_rect = pygame.Rect(290, 64, 700, 54)
            text_y = 80
            text_x = 312
            text_width = 654
        else:
            panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (520, 90))
            panel_rect = pygame.Rect(736, 612, 520, 90)
            text_y = 636
            text_x = 756
            text_width = 476

        surface.blit(panel, panel_rect.topleft)
        pygame.draw.rect(surface, accent, panel_rect, 3, border_radius=14)
        self._draw_text(surface, notice["text"], (text_x, text_y), self._small_font, width=text_width)

    def _render_help_overlay(
        self,
        surface: Any,
        current_state: str,
        presentation: dict[str, Any],
    ) -> None:
        backdrop = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        backdrop.fill((6, 10, 18, 180))
        surface.blit(backdrop, (0, 0))

        panel = self._scaled_image(
            resolve_asset_path("ui", "panel.png"),
            (HELP_PANEL_WIDTH, HELP_PANEL_HEIGHT),
        )
        panel_pos = ((surface.get_width() - HELP_PANEL_WIDTH) // 2, (surface.get_height() - HELP_PANEL_HEIGHT) // 2)
        surface.blit(panel, panel_pos)

        x = panel_pos[0] + 36
        y = panel_pos[1] + 28
        self._draw_text(surface, "Controls And Quality-of-Life Shortcuts", (x, y), self._title_font)
        y += 54
        self._draw_text(surface, "Global", (x, y), self._font)
        y += 36
        for line in self._help_lines(current_state, presentation):
            self._draw_text(surface, line, (x, y), self._small_font, width=HELP_PANEL_WIDTH - 72)
            y += 28

    def _render_settings_overlay(self, surface: Any, presentation: dict[str, Any]) -> None:
        high_contrast = presentation.get("high_contrast", False)
        backdrop = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        backdrop.fill((4, 8, 14, 196))
        surface.blit(backdrop, (0, 0))

        panel = self._scaled_image(
            resolve_asset_path("ui", "panel.png"),
            (SETTINGS_PANEL_WIDTH, SETTINGS_PANEL_HEIGHT),
        )
        panel_pos = (
            (surface.get_width() - SETTINGS_PANEL_WIDTH) // 2,
            (surface.get_height() - SETTINGS_PANEL_HEIGHT) // 2,
        )
        surface.blit(panel, panel_pos)

        layout = self._settings_layout(presentation, panel_pos)
        self._draw_text(surface, "Settings And Comfort Options", (panel_pos[0] + 34, panel_pos[1] + 24), self._title_font)
        self._draw_text(
            surface,
            "Adjust the game live. Changes save automatically and apply immediately.",
            (panel_pos[0] + 34, panel_pos[1] + 66),
            self._small_font,
            width=SETTINGS_PANEL_WIDTH - 68,
        )

        for index, row in enumerate(layout["rows"]):
            row_rect = pygame.Rect(*row["row_rect"])
            selected = index == self._settings_selected_index
            outline = (255, 236, 140) if selected else (190, 205, 230) if high_contrast else (108, 122, 148)
            pygame.draw.rect(
                surface,
                (10, 16, 24) if high_contrast else (12, 18, 28),
                row_rect,
                border_radius=14,
            )
            pygame.draw.rect(surface, outline, row_rect, 2, border_radius=14)
            self._draw_text(surface, row["label"], (row_rect.x + 18, row_rect.y + 12), self._small_font)
            self._draw_text(surface, row["description"], (row_rect.x + 18, row_rect.y + 38), self._tiny_font, width=420)

            if row["kind"] == "toggle":
                self._draw_settings_button(
                    surface,
                    row["toggle_action"],
                    row["toggle_rect"],
                    row["value_text"],
                    active=row["value"],
                )
            else:
                self._draw_settings_button(
                    surface,
                    row["decrease_action"],
                    row["decrease_rect"],
                    "-",
                    active=False,
                )
                self._draw_text(surface, row["value_text"], (row_rect.x + 590, row_rect.y + 24), self._small_font)
                self._draw_settings_button(
                    surface,
                    row["increase_action"],
                    row["increase_rect"],
                    "+",
                    active=False,
                )

        for button in layout["footer_buttons"]:
            self._draw_settings_button(
                surface,
                button["action"],
                button["rect"],
                button["label"],
                active=button.get("active", False),
            )

    def _help_lines(self, current_state: str, presentation: dict[str, Any]) -> list[str]:
        lines = [
            "H toggles this panel. Esc closes overlays first, then exits the game.",
            "S opens the settings overlay.",
            "F11 toggles fullscreen and windowed mode.",
            "F toggles fast feedback mode.",
            "M mutes or restores audio.",
            "[ and ] lower or raise SFX volume.",
            "- and + adjust presentation scale inside the display frame.",
            "N starts a fresh run from anywhere.",
        ]

        if current_state == "map":
            lines.extend(
                [
                    "Map: click an available node or press 1-9 to choose a route.",
                    "Map: Enter or Space confirms the hovered route, or the first available route if nothing is hovered.",
                    "Available routes glow gold, visited routes glow green, and locked routes stay dim.",
                ]
            )
        elif current_state == "combat":
            lines.extend(
                [
                    "Combat: click a card or press 1-9 to play it.",
                    "Combat: Enter, Space, or E ends the turn.",
                    "Disabled cards show why they cannot be played before you click them.",
                    "Enemy intent panels preview the next attack or block amount.",
                ]
            )
        elif current_state == "reward":
            lines.extend(
                [
                    "Reward: click or press 1-9 to select a reward option in the active section.",
                    "Reward: Enter or Space confirms the selected option.",
                    "Reward: X skips the active section and C continues once every section is resolved.",
                ]
            )
        elif current_state == "event":
            lines.extend(
                [
                    "Event: click or press 1-9 to choose an event option.",
                    "Event: click a deck card target when a purge option is selected.",
                    "Event: Enter or Space confirms the choice, and C continues after it resolves.",
                ]
            )
        elif current_state == "shop":
            lines.extend(
                [
                    "Shop: click or press 1-9 to select an offer.",
                    "Shop: Enter or Space buys the selected offer, R rerolls the unsold card offers, and L leaves the shop.",
                    "Purge service requires choosing a deck card before confirming the purchase.",
                ]
            )
        else:
            lines.append("Victory / Game Over: Enter, Space, or N starts a new run.")

        if presentation.get("fast_mode"):
            lines.append("Fast mode is currently enabled.")
        if presentation.get("muted"):
            lines.append("Audio is currently muted.")
        if presentation.get("settings_open"):
            lines.append("Settings overlay is currently open.")
        return lines

    def _handle_settings_event(self, event: Any, presentation: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self._settings_layout(presentation, self._settings_panel_position())
        row_count = len(layout["rows"])

        if event.type == pygame.MOUSEMOTION:
            self._settings_hovered_action = self._settings_action_at_position(layout, event.pos)
            for index, row in enumerate(layout["rows"]):
                if point_in_rect(event.pos, row["row_rect"]):
                    self._settings_selected_index = index
                    break
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._settings_pressed_action = self._settings_action_at_position(layout, event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            action_id = self._settings_action_at_position(layout, event.pos)
            pressed_action = self._settings_pressed_action
            self._settings_pressed_action = None
            if action_id is None or action_id != pressed_action:
                return None
            return self._settings_action_to_event(action_id, presentation)

        if event.type != pygame.KEYDOWN:
            return None

        if event.key in {pygame.K_ESCAPE, pygame.K_s}:
            return {"type": "close_settings"}

        if event.key == pygame.K_UP:
            self._settings_selected_index = (self._settings_selected_index - 1) % row_count
            return None

        if event.key == pygame.K_DOWN:
            self._settings_selected_index = (self._settings_selected_index + 1) % row_count
            return None

        selected_row = layout["rows"][self._settings_selected_index]
        if event.key == pygame.K_LEFT and selected_row["kind"] == "step":
            return self._settings_action_to_event(selected_row["decrease_action"], presentation)
        if event.key == pygame.K_RIGHT and selected_row["kind"] == "step":
            return self._settings_action_to_event(selected_row["increase_action"], presentation)
        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            action_id = (
                selected_row["toggle_action"]
                if selected_row["kind"] == "toggle"
                else selected_row["increase_action"]
            )
            return self._settings_action_to_event(action_id, presentation)

        if event.key == pygame.K_r:
            return {"type": "reset_settings"}

        return None

    def _settings_layout(self, presentation: dict[str, Any], panel_pos: tuple[int, int]) -> dict[str, Any]:
        rows = []
        base_x = panel_pos[0] + 32
        base_y = panel_pos[1] + 108
        row_height = 48
        row_gap = 8

        for index, row in enumerate(self._settings_rows(presentation)):
            row_y = base_y + (index * (row_height + row_gap))
            row_rect = (base_x, row_y, SETTINGS_PANEL_WIDTH - 64, row_height)
            entry = {**row, "row_rect": row_rect}
            if row["kind"] == "toggle":
                entry["toggle_rect"] = (base_x + 644, row_y + 8, 190, 32)
                entry["toggle_action"] = f"toggle:{row['id']}"
            else:
                entry["decrease_rect"] = (base_x + 566, row_y + 8, 34, 32)
                entry["increase_rect"] = (base_x + 790, row_y + 8, 34, 32)
                entry["decrease_action"] = f"decrease:{row['id']}"
                entry["increase_action"] = f"increase:{row['id']}"
            rows.append(entry)

        footer_buttons = [
            {"action": "reset", "label": "Reset Defaults", "rect": (base_x, panel_pos[1] + 500, 180, 38)},
            {"action": "close", "label": "Close", "rect": (panel_pos[0] + 690, panel_pos[1] + 500, 146, 38), "active": True},
        ]
        return {"rows": rows, "footer_buttons": footer_buttons}

    def _settings_rows(self, presentation: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"id": "fullscreen", "label": "Display Mode", "description": "Toggle fullscreen or a resizable window.", "kind": "toggle", "value": presentation.get("fullscreen", True), "value_text": "Fullscreen" if presentation.get("fullscreen", True) else "Windowed"},
            {"id": "fast_mode", "label": "Fast Mode", "description": "Shorten non-critical feedback and transitions.", "kind": "toggle", "value": presentation.get("fast_mode", False), "value_text": "Enabled" if presentation.get("fast_mode", False) else "Disabled"},
            {"id": "master_volume", "label": "SFX Volume", "description": "Adjust sound effect volume for combat and UI cues.", "kind": "step", "value": presentation.get("master_volume", 0.8), "value_text": f"{int(presentation.get('master_volume', 0.8) * 100)}%"},
            {"id": "music_volume", "label": "Music Volume", "description": "Reserve volume for music playback when tracks are added.", "kind": "step", "value": presentation.get("music_volume", 0.65), "value_text": f"{int(presentation.get('music_volume', 0.65) * 100)}%"},
            {"id": "muted", "label": "Mute Audio", "description": "Silence all current and future audio output.", "kind": "toggle", "value": presentation.get("muted", False), "value_text": "Muted" if presentation.get("muted", False) else "Live"},
            {"id": "presentation_scale", "label": "Presentation Scale", "description": "Fit the 1280x720 canvas comfortably inside the display.", "kind": "step", "value": presentation.get("presentation_scale", 1.0), "value_text": f"{int(presentation.get('presentation_scale', 1.0) * 100)}%"},
            {"id": "ui_scale", "label": "UI Text Scale", "description": "Scale text and labels for readability.", "kind": "step", "value": presentation.get("ui_scale", 1.0), "value_text": f"{int(presentation.get('ui_scale', 1.0) * 100)}%"},
            {"id": "screen_shake", "label": "Screen Shake", "description": "Toggle impact shake on heavy feedback moments.", "kind": "toggle", "value": presentation.get("screen_shake", True), "value_text": "Enabled" if presentation.get("screen_shake", True) else "Disabled"},
            {"id": "high_contrast", "label": "High Contrast", "description": "Boost contrast and reduce reliance on subtle color differences.", "kind": "toggle", "value": presentation.get("high_contrast", False), "value_text": "Enabled" if presentation.get("high_contrast", False) else "Disabled"},
        ]

    def _settings_action_to_event(
        self,
        action_id: str,
        presentation: dict[str, Any],
    ) -> dict[str, Any]:
        if action_id == "reset":
            return {"type": "reset_settings"}
        if action_id == "close":
            return {"type": "close_settings"}

        action_type, _, setting_name = action_id.partition(":")
        if action_type == "toggle":
            return {"type": "set_setting", "setting": setting_name, "value": not presentation.get(setting_name, False)}

        current_value = presentation.get(setting_name)
        if action_type == "decrease":
            return {"type": "set_setting", "setting": setting_name, "value": self._next_setting_value(setting_name, current_value, -1)}
        if action_type == "increase":
            return {"type": "set_setting", "setting": setting_name, "value": self._next_setting_value(setting_name, current_value, 1)}

        return {"type": "notice", "message": "Unknown settings action.", "level": "error"}

    def _next_setting_value(self, setting_name: str, current_value: Any, direction: int) -> Any:
        if setting_name in {"master_volume", "music_volume"}:
            return max(0.0, min(1.0, float(current_value) + (VOLUME_STEP * direction)))
        if setting_name == "presentation_scale":
            return max(MIN_PRESENTATION_SCALE, min(MAX_PRESENTATION_SCALE, float(current_value) + (PRESENTATION_SCALE_STEP * direction)))
        if setting_name == "ui_scale":
            return max(MIN_UI_SCALE, min(MAX_UI_SCALE, float(current_value) + (UI_SCALE_STEP * direction)))
        return current_value

    def _settings_action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for row in layout["rows"]:
            if row["kind"] == "toggle" and self._point_in_rect(position, row["toggle_rect"]):
                return row["toggle_action"]
            if row["kind"] == "step":
                if self._point_in_rect(position, row["decrease_rect"]):
                    return row["decrease_action"]
                if self._point_in_rect(position, row["increase_rect"]):
                    return row["increase_action"]
        for button in layout["footer_buttons"]:
            if self._point_in_rect(position, button["rect"]):
                return button["action"]
        return None

    def _settings_panel_position(self) -> tuple[int, int]:
        return ((1280 - SETTINGS_PANEL_WIDTH) // 2, (720 - SETTINGS_PANEL_HEIGHT) // 2)

    def _draw_settings_button(
        self,
        surface: Any,
        action_id: str,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        active: bool,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        hovered = self._settings_hovered_action == action_id
        pressed = self._settings_pressed_action == action_id
        fill = (48, 82, 132) if active else (24, 34, 50)
        if hovered:
            fill = (62, 104, 164) if active else (40, 52, 72)
        if pressed:
            fill = (255, 214, 110)
        border = (255, 214, 110) if active or hovered else (120, 136, 160)
        pygame.draw.rect(surface, fill, rect, border_radius=12)
        pygame.draw.rect(surface, border, rect, 2, border_radius=12)
        text_color = (18, 22, 28) if pressed else (240, 245, 255)
        label_surface = self._tiny_font.render(label, True, text_color)
        label_rect = label_surface.get_rect(center=rect.center)
        surface.blit(label_surface, label_rect)

    def _draw_chip(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        width: int,
        accent: tuple[int, int, int],
    ) -> None:
        rect = pygame.Rect(position[0], position[1], width, 26)
        pygame.draw.rect(surface, (18, 28, 42), rect, border_radius=10)
        pygame.draw.rect(surface, accent, rect, 1, border_radius=10)
        label = self._tiny_font.render(text, True, (232, 240, 255))
        label_rect = label.get_rect(center=rect.center)
        surface.blit(label, label_rect)

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
        self._title_font = pygame.font.SysFont("consolas", max(30, int(38 * scale)))
        self._font = pygame.font.SysFont("consolas", max(22, int(28 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(16, int(20 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(16 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((90, 10, 150, 180))

        self._image_cache[cache_key] = image
        return image

    def _point_in_rect(self, point: tuple[int, int], rect: tuple[int, int, int, int]) -> bool:
        return point_in_rect(point, rect)


def simulate_ui_manager() -> dict[str, Any]:
    manager = UIManager()
    event_layout = manager.simulate_ui(
        {
            "current_state": "event",
            "status_message": "Choose how to handle the dead drop.",
            "map": None,
            "combat": None,
            "reward": None,
            "shop": None,
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
                    }
                ],
                "selected_choice_id": None,
                "selected_choice_type": None,
                "selected_target_id": None,
                "purge_targets": [],
                "resolved": False,
                "resolution_summary": None,
                "resolution_details": [],
                "deck_size": 10,
                "can_continue": False,
            },
            "player": {"current_hp": 70, "max_hp": 70, "credits": 0},
            "player_hand": [],
            "presentation": {
                "fullscreen": True,
                "fast_mode": False,
                "muted": False,
                "master_volume": 0.8,
                "music_volume": 0.65,
                "presentation_scale": 1.0,
                "ui_scale": 1.0,
                "screen_shake": True,
                "high_contrast": False,
                "show_help": False,
                "settings_open": False,
            },
            "ui_notice": {"text": "Event screen shown.", "level": "info"},
        }
    )
    victory_layout = manager.simulate_ui(
        {
            "current_state": "victory",
            "status_message": "Run completed.",
            "map": None,
            "combat": None,
            "reward": None,
            "shop": None,
            "event": None,
            "player": None,
            "player_hand": [],
            "presentation": {
                "fullscreen": True,
                "fast_mode": False,
                "muted": False,
                "master_volume": 0.8,
                "music_volume": 0.65,
                "presentation_scale": 1.0,
                "ui_scale": 1.0,
                "screen_shake": True,
                "high_contrast": False,
                "show_help": False,
                "settings_open": False,
            },
            "ui_notice": {"text": "Victory banner shown.", "level": "success"},
        }
    )
    return {
        "event_title": event_layout["title"],
        "event_choices": len(event_layout["choices"]),
        "victory_title": victory_layout["title"],
    }
