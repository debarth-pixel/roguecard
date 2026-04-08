from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    MAX_PRESENTATION_SCALE,
    MAX_UI_SCALE,
    MIN_PRESENTATION_SCALE,
    MIN_UI_SCALE,
    PAUSE_BUTTON_HEIGHT,
    PAUSE_BUTTON_WIDTH,
    PRESENTATION_SCALE_STEP,
    SETTINGS_PANEL_HEIGHT,
    SETTINGS_PANEL_WIDTH,
    SETTINGS_TAB_HEIGHT,
    SETTINGS_TAB_WIDTH,
    STATUS_ICON_GAP,
    STATUS_ICON_SIZE,
    STATUS_TOOLTIP_WIDTH,
    UI_SCALE_STEP,
    VOLUME_STEP,
    resolve_asset_path,
)
from ui.character_select_ui import CharacterSelectUI
from ui.combat_ui import CombatUI
from ui.event_ui import EventUI
from ui.map_ui import MapUI
from ui.modifier_draft_ui import ModifierDraftUI
from ui.reward_ui import RewardUI
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.shop_ui import ShopUI
from ui.title_ui import TitleUI


class UIManager:
    def __init__(self) -> None:
        self.character_select_ui = CharacterSelectUI()
        self.combat_ui = CombatUI()
        self.event_ui = EventUI()
        self.map_ui = MapUI()
        self.modifier_draft_ui = ModifierDraftUI()
        self.reward_ui = RewardUI()
        self.shop_ui = ShopUI()
        self.title_ui = TitleUI()
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._settings_hovered_action: str | None = None
        self._settings_pressed_action: str | None = None
        self._settings_selected_index = 0
        self._pause_hovered_action: str | None = None
        self._pause_pressed_action: str | None = None
        self._pause_selected_index = 0
        self._modifier_hovered_id: str | None = None

    def preload_assets(self) -> None:
        self.character_select_ui.preload_assets()
        self.map_ui.preload_assets()
        self.combat_ui.preload_assets()
        self.event_ui.preload_assets()
        self.modifier_draft_ui.preload_assets()
        self.reward_ui.preload_assets()
        self.shop_ui.preload_assets()
        self.title_ui.preload_assets()
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
        if pygame is not None:
            self._ensure_fonts(presentation.get("ui_scale", 1.0))
        if presentation.get("settings_open"):
            return self._handle_settings_event(event, presentation)
        if presentation.get("pause_open"):
            return self._handle_pause_event(event)

        current_state = state_snapshot["current_state"]
        if current_state in {"modifier_draft", "map", "combat", "reward", "shop", "event"}:
            top_action = self._handle_top_bar_event(event, state_snapshot)
            if top_action is not None:
                return top_action

        if current_state in {"modifier_draft", "map", "combat", "reward", "shop", "event"}:
            self._update_modifier_hover(event, state_snapshot)
        else:
            self._modifier_hovered_id = None

        if current_state == "title" and state_snapshot.get("title") is not None:
            action = self.title_ui.handle_event(event, self._title_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "character_select" and state_snapshot.get("character_select") is not None:
            action = self.character_select_ui.handle_event(event, self._character_select_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "modifier_draft" and state_snapshot.get("modifier_draft") is not None:
            action = self.modifier_draft_ui.handle_event(event, self._modifier_draft_view_state(state_snapshot))
            if action is not None:
                return action

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

        if current_state == "title" and state_snapshot.get("title") is not None:
            self.title_ui.render(surface, self._title_view_state(state_snapshot))
        elif current_state == "character_select" and state_snapshot.get("character_select") is not None:
            self.character_select_ui.render(surface, self._character_select_view_state(state_snapshot))
        elif current_state == "modifier_draft" and state_snapshot.get("modifier_draft") is not None:
            self.modifier_draft_ui.render(surface, self._modifier_draft_view_state(state_snapshot))
        elif current_state == "combat" and state_snapshot["combat"] is not None:
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

        if current_state not in {"title", "character_select", "victory", "game_over"}:
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
        elif presentation.get("pause_open"):
            self._render_pause_overlay(surface)

    def simulate_ui(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        if state_snapshot["current_state"] == "title" and state_snapshot.get("title") is not None:
            return self.title_ui.build_layout(self._title_view_state(state_snapshot))
        if state_snapshot["current_state"] == "character_select" and state_snapshot.get("character_select") is not None:
            return self.character_select_ui.build_layout(self._character_select_view_state(state_snapshot))
        if state_snapshot["current_state"] == "modifier_draft" and state_snapshot.get("modifier_draft") is not None:
            return self.modifier_draft_ui.build_layout(self._modifier_draft_view_state(state_snapshot))
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

    def _title_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "status_message": state_snapshot["status_message"],
            "title": state_snapshot["title"],
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _modifier_draft_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "status_message": state_snapshot["status_message"],
            "modifier_draft": state_snapshot["modifier_draft"],
            "character": state_snapshot.get("character"),
            "presentation": state_snapshot.get("presentation", {}),
        }

    def _character_select_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "status_message": state_snapshot["status_message"],
            "character_select": state_snapshot["character_select"],
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
            "hint": "S opens settings",
        }

    def _render_status_screen(self, surface: Any, layout: dict[str, Any]) -> None:
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (760, 280))
        banner = self._scaled_image(resolve_asset_path("ui", layout["banner"]), (760, 180))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176)
        surface.blit(panel, (260, 220))
        surface.blit(banner, (260, 58))

        self._draw_text(surface, layout["title"], (420, 268), self._title_font, width=430)
        self._draw_text(surface, layout["subtitle"], (330, 348), self._small_font, width=620)
        self._draw_text(surface, layout["prompt"], (356, 420), self._small_font, width=580)
        self._draw_text(surface, layout["hint"], (524, 462), self._tiny_font, width=240)

    def _render_top_bar(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        presentation = state_snapshot.get("presentation", {})
        high_contrast = presentation.get("high_contrast", False)
        accent = (220, 230, 255) if high_contrast else (105, 120, 150)
        layout = self._top_bar_layout(state_snapshot)
        if layout["state_rect"] is not None:
            state_rect = pygame.Rect(*layout["state_rect"])
            pygame.draw.rect(surface, (12, 19, 30), state_rect, border_radius=12)
            pygame.draw.rect(surface, accent, state_rect, 2, border_radius=12)
            self._draw_text(surface, layout["state_label"], (state_rect.x + 16, state_rect.y + 10), self._tiny_font, width=state_rect.width - 32)

        for stat in layout["stats"]:
            self._draw_top_stat_chip(surface, stat, high_contrast)

        self._render_modifier_icons(surface, layout["modifier_icons"], high_contrast)

        pause_rect = pygame.Rect(*layout["pause_rect"])
        hovered = self._pause_hovered_action == "top_pause"
        pressed = self._pause_pressed_action == "top_pause"
        fill = (24, 34, 50)
        if hovered:
            fill = (40, 54, 76)
        if pressed:
            fill = (255, 214, 110)
        pygame.draw.rect(surface, fill, pause_rect, border_radius=12)
        pygame.draw.rect(surface, accent if not pressed else (255, 214, 110), pause_rect, 2, border_radius=12)
        label_color = (18, 24, 36) if pressed else (240, 245, 255)
        pause_label = self._small_font.render("Pause", True, label_color)
        surface.blit(pause_label, pause_label.get_rect(center=pause_rect.center))

    def _top_bar_layout(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        current_state = state_snapshot["current_state"]
        state_label = {
            "modifier_draft": "Run Draft",
            "map": "Map",
            "combat": "Combat",
            "reward": "Reward",
            "shop": "Shop",
            "event": "Event",
        }.get(current_state, current_state.replace("_", " ").title())
        run_seed = state_snapshot.get("run_seed")
        label = f"{state_label} | Seed {run_seed}" if run_seed is not None and current_state in {"map", "modifier_draft"} else state_label
        pause_rect = (1280 - PAUSE_BUTTON_WIDTH - 24, 12, PAUSE_BUTTON_WIDTH, PAUSE_BUTTON_HEIGHT)
        state_width = max(152, self._tiny_font.size(label)[0] + 32)
        state_rect = (24, 14, state_width, 34)
        active_modifiers = list(state_snapshot.get("run_modifiers", {}).get("active", []))
        if len(active_modifiers) > 6:
            active_modifiers = active_modifiers[-6:]
        strip_width = 0
        if active_modifiers:
            strip_width = (len(active_modifiers) * STATUS_ICON_SIZE) + ((len(active_modifiers) - 1) * STATUS_ICON_GAP)
        modifier_icons = []
        modifier_start_x = pause_rect[0] - 16 - strip_width
        for index, modifier in enumerate(active_modifiers):
            modifier_icons.append(
                {
                    **modifier,
                    "rect": (
                        modifier_start_x + (index * (STATUS_ICON_SIZE + STATUS_ICON_GAP)),
                        17,
                        STATUS_ICON_SIZE,
                        STATUS_ICON_SIZE,
                    ),
                }
            )
        stats = []
        cursor_x = state_rect[0] + state_rect[2] + 12
        max_x = modifier_start_x - 12 if modifier_icons else pause_rect[0] - 12
        for item in self._top_bar_stat_items(state_snapshot):
            chip_width = max(82, self._tiny_font.size(item["label"])[0] + 34)
            if cursor_x + chip_width > max_x:
                break
            stats.append({**item, "rect": (cursor_x, 14, chip_width, 34)})
            cursor_x += chip_width + 10
        return {
            "state_rect": state_rect,
            "state_label": label,
            "pause_rect": pause_rect,
            "stats": stats,
            "modifier_icons": modifier_icons,
        }

    def _top_bar_stat_items(self, state_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        player = state_snapshot.get("player")
        character = state_snapshot.get("character")
        current_state = state_snapshot.get("current_state")
        items: list[dict[str, Any]] = []
        if isinstance(character, dict):
            accent = tuple(character.get("accent_color", [120, 150, 190]))
            items.append({"label": character.get("name", "Runner"), "accent": accent})
        if current_state == "event":
            return items
        if isinstance(player, dict):
            items.append(
                {
                    "label": f"HP {player.get('current_hp', 0)}/{player.get('max_hp', 0)}",
                    "accent": (232, 106, 112),
                }
            )
            items.append(
                {
                    "label": f"Credits {player.get('credits', 0)}",
                    "accent": (240, 196, 96),
                }
            )

        if current_state == "map" and isinstance(state_snapshot.get("map"), dict):
            map_state = state_snapshot["map"]
            nodes = map_state.get("nodes", {})
            selected_node_id = map_state.get("selected_node_id")
            selected_node = nodes.get(selected_node_id) if isinstance(nodes, dict) and selected_node_id is not None else None
            if selected_node is None:
                progress_label = "Progress Entrance"
            else:
                progress_label = f"Progress F{selected_node['floor'] + 1} {selected_node['node_type'].title()}"
            items.append({"label": progress_label, "accent": (92, 198, 240)})
            items.append(
                {
                    "label": f"Routes {len(map_state.get('available_node_ids', []))}",
                    "accent": (255, 214, 110),
                }
            )
        return items

    def _draw_top_stat_chip(
        self,
        surface: Any,
        stat: dict[str, Any],
        high_contrast: bool,
    ) -> None:
        rect = pygame.Rect(*stat["rect"])
        accent = stat["accent"]
        fill = (14, 22, 34)
        border = (220, 230, 255) if high_contrast else accent
        pygame.draw.rect(surface, fill, rect, border_radius=12)
        pygame.draw.rect(surface, border, rect, 2, border_radius=12)
        pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 6, rect.y + 7, 6, rect.height - 14), border_radius=3)
        self._draw_text(surface, stat["label"], (rect.x + 18, rect.y + 10), self._tiny_font, width=rect.width - 28)

    def _modifier_accent(self, modifier_type: str, high_contrast: bool) -> tuple[int, int, int]:
        colors = {
            "relic": (100, 184, 242),
            "blessing": (110, 220, 164),
            "curse": (230, 116, 116),
            "status": (168, 148, 244),
        }
        accent = colors.get(modifier_type, (144, 156, 182))
        if high_contrast:
            accent = tuple(min(255, channel + 16) for channel in accent)
        return accent

    def _modifier_abbrev(self, name: str) -> str:
        words = [part for part in name.split() if part]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return (words[0][0] + words[1][0]).upper()

    def _handle_top_bar_event(self, event: Any, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None
        pause_rect = self._top_bar_layout(state_snapshot)["pause_rect"]
        if event.type == pygame.MOUSEMOTION:
            self._pause_hovered_action = "top_pause" if point_in_rect(event.pos, pause_rect) else None
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pause_pressed_action = "top_pause" if point_in_rect(event.pos, pause_rect) else None
            return None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            action_id = "top_pause" if point_in_rect(event.pos, pause_rect) else None
            pressed_action = self._pause_pressed_action
            self._pause_pressed_action = None
            if action_id is not None and action_id == pressed_action:
                return {"type": "pause_open"}
        return None

    def _modifier_icon_layout(self, state_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        return self._top_bar_layout(state_snapshot)["modifier_icons"]

    def _update_modifier_hover(self, event: Any, state_snapshot: dict[str, Any]) -> None:
        if pygame is None or event.type not in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            return
        self._modifier_hovered_id = None
        for modifier in self._modifier_icon_layout(state_snapshot):
            if point_in_rect(event.pos, modifier["rect"]):
                self._modifier_hovered_id = modifier["id"]
                return

    def _render_modifier_icons(
        self,
        surface: Any,
        modifiers: list[dict[str, Any]],
        high_contrast: bool,
    ) -> None:
        if not modifiers:
            return

        for modifier in modifiers:
            rect = pygame.Rect(*modifier["rect"])
            accent = self._modifier_accent(modifier.get("type", modifier.get("kind", "status")), high_contrast)
            fill = (18, 28, 42) if modifier["id"] != self._modifier_hovered_id else (30, 42, 62)
            pygame.draw.rect(surface, fill, rect, border_radius=10)
            pygame.draw.rect(surface, accent if modifier["id"] != self._modifier_hovered_id else (255, 214, 110), rect, 2, border_radius=10)
            label = self._tiny_font.render(self._modifier_abbrev(modifier["name"]), True, accent)
            surface.blit(label, label.get_rect(center=rect.center))
            if modifier.get("temporary") and isinstance(modifier.get("remaining"), int):
                badge_rect = pygame.Rect(rect.right - 14, rect.y - 4, 18, 18)
                pygame.draw.rect(surface, (255, 214, 110), badge_rect, border_radius=9)
                badge = self._tiny_font.render(str(modifier["remaining"]), True, (18, 24, 36))
                surface.blit(badge, badge.get_rect(center=badge_rect.center))

        hovered_modifier = next(
            (modifier for modifier in modifiers if modifier["id"] == self._modifier_hovered_id),
            None,
        )
        if hovered_modifier is None:
            return

        tooltip_height = 118 if hovered_modifier.get("downside") else 96
        if hovered_modifier.get("duration_label"):
            tooltip_height += 22
        tooltip_x = max(24, min(1280 - STATUS_TOOLTIP_WIDTH - 24, hovered_modifier["rect"][0] - STATUS_TOOLTIP_WIDTH + hovered_modifier["rect"][2]))
        tooltip_y = 58
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, STATUS_TOOLTIP_WIDTH, tooltip_height)
        pygame.draw.rect(surface, (8, 14, 24), tooltip_rect, border_radius=14)
        pygame.draw.rect(surface, (255, 214, 110), tooltip_rect, 2, border_radius=14)
        accent = self._modifier_accent(hovered_modifier.get("type", hovered_modifier.get("kind", "status")), high_contrast)
        self._draw_text(surface, hovered_modifier["name"], (tooltip_rect.x + 14, tooltip_rect.y + 12), self._small_font, width=tooltip_rect.width - 28)
        self._draw_chip(surface, hovered_modifier.get("type", hovered_modifier.get("kind", "status")).title(), (tooltip_rect.x + 14, tooltip_rect.y + 38), 96, accent=accent)
        self._draw_text(surface, hovered_modifier["description"], (tooltip_rect.x + 14, tooltip_rect.y + 68), self._tiny_font, width=tooltip_rect.width - 28)
        text_y = tooltip_rect.y + 88
        if hovered_modifier.get("duration_label"):
            self._draw_text(surface, hovered_modifier["duration_label"], (tooltip_rect.x + 14, text_y), self._tiny_font, width=tooltip_rect.width - 28)
            text_y += 22
        if hovered_modifier.get("downside"):
            self._draw_text(surface, f"Tradeoff: {hovered_modifier['downside']}", (tooltip_rect.x + 14, text_y), self._tiny_font, width=tooltip_rect.width - 28)

    def _pause_layout(self) -> dict[str, Any]:
        buttons = [
            {"action": "pause_continue", "label": "Continue", "description": "Close the menu and resume the run."},
            {"action": "pause_open_settings", "label": "Settings", "description": "Open settings and controls."},
            {"action": "pause_home", "label": "Home Screen", "description": "Return to title and keep Continue available."},
            {"action": "pause_quit", "label": "Close Game", "description": "Exit the game immediately."},
        ]
        panel_rect = (440, 170, 400, 380)
        for index, button in enumerate(buttons):
            button["rect"] = (472, 238 + (index * 66), 336, 52)
        return {"panel_rect": panel_rect, "buttons": buttons}

    def _handle_pause_event(self, event: Any) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self._pause_layout()
        buttons = layout["buttons"]
        self._pause_selected_index = max(0, min(self._pause_selected_index, len(buttons) - 1))

        if event.type == pygame.MOUSEMOTION:
            self._pause_hovered_action = None
            for index, button in enumerate(buttons):
                if point_in_rect(event.pos, button["rect"]):
                    self._pause_hovered_action = button["action"]
                    self._pause_selected_index = index
                    break
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pause_pressed_action = next(
                (button["action"] for button in buttons if point_in_rect(event.pos, button["rect"])),
                None,
            )
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            action_id = next(
                (button["action"] for button in buttons if point_in_rect(event.pos, button["rect"])),
                None,
            )
            pressed_action = self._pause_pressed_action
            self._pause_pressed_action = None
            if action_id is not None and action_id == pressed_action:
                return {"type": action_id}
            return None

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            return {"type": "pause_continue"}
        if event.key in {pygame.K_UP, pygame.K_LEFT}:
            self._pause_selected_index = (self._pause_selected_index - 1) % len(buttons)
            return None
        if event.key in {pygame.K_DOWN, pygame.K_RIGHT}:
            self._pause_selected_index = (self._pause_selected_index + 1) % len(buttons)
            return None
        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            return {"type": buttons[self._pause_selected_index]["action"]}
        return None

    def _render_pause_overlay(self, surface: Any) -> None:
        layout = self._pause_layout()
        backdrop = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        backdrop.fill((4, 8, 14, 188))
        surface.blit(backdrop, (0, 0))

        panel_rect = pygame.Rect(*layout["panel_rect"])
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), panel_rect.size)
        surface.blit(panel, panel_rect.topleft)
        pygame.draw.rect(surface, (180, 198, 226), panel_rect, 2, border_radius=16)
        self._draw_text(surface, "Paused", (panel_rect.x + 34, panel_rect.y + 28), self._title_font)
        self._draw_text(surface, "Continue, adjust settings, head home, or exit the game.", (panel_rect.x + 34, panel_rect.y + 72), self._tiny_font, width=panel_rect.width - 68)

        for index, button in enumerate(layout["buttons"]):
            rect = pygame.Rect(*button["rect"])
            selected = index == self._pause_selected_index
            hovered = self._pause_hovered_action == button["action"]
            pressed = self._pause_pressed_action == button["action"]
            fill = (18, 28, 42)
            if hovered:
                fill = (34, 50, 72)
            if pressed:
                fill = (255, 214, 110)
            outline = (255, 214, 110) if selected else (168, 184, 214)
            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, outline, rect, 2, border_radius=14)
            label_color = (18, 24, 36) if pressed else (240, 245, 255)
            self._draw_text(surface, button["label"], (rect.x + 16, rect.y + 12), self._small_font, width=140)
            self._draw_text(surface, button["description"], (rect.x + 16, rect.y + 30), self._tiny_font, width=rect.width - 32)

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
        if current_state in {"combat", "modifier_draft", "reward", "shop", "event"}:
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

    def _render_settings_overlay(self, surface: Any, presentation: dict[str, Any]) -> None:
        high_contrast = presentation.get("high_contrast", False)
        backdrop = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        backdrop.fill((2, 6, 12, 224))
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
            "Adjust the game live, or switch to Controls for the full shortcut reference.",
            (panel_pos[0] + 34, panel_pos[1] + 66),
            self._tiny_font,
            width=SETTINGS_PANEL_WIDTH - 68,
        )

        for tab in layout["tabs"]:
            self._draw_settings_button(
                surface,
                tab["action"],
                tab["rect"],
                tab["label"],
                active=tab["active"],
            )

        section_fill = (10, 16, 24) if high_contrast else (11, 17, 27)
        section_outline = (184, 198, 224) if high_contrast else (92, 108, 134)
        row_fill = (14, 22, 32) if high_contrast else (14, 20, 30)
        row_outline = (255, 236, 140)
        row_idle_outline = (186, 198, 222) if high_contrast else (96, 110, 136)
        value_fill = (20, 30, 44) if high_contrast else (19, 28, 41)

        if layout["page"] == "general":
            if layout["rows"]:
                self._settings_selected_index = max(0, min(self._settings_selected_index, len(layout["rows"]) - 1))
                selected_row = layout["rows"][self._settings_selected_index]
                help_rect = pygame.Rect(*layout["help_rect"])
                help_fill = (10, 16, 24) if high_contrast else (9, 15, 23)
                help_outline = (255, 236, 140) if high_contrast else (88, 110, 146)
                pygame.draw.rect(surface, help_fill, help_rect, border_radius=14)
                pygame.draw.rect(surface, help_outline, help_rect, 2, border_radius=14)
                self._draw_text(
                    surface,
                    f"Focused setting: {selected_row['label']} | {selected_row['description']}",
                    (help_rect.x + 18, help_rect.y + 13),
                    self._tiny_font,
                    width=help_rect.width - 36,
                )

            for section in layout["sections"]:
                section_rect = pygame.Rect(*section["rect"])
                pygame.draw.rect(surface, section_fill, section_rect, border_radius=18)
                pygame.draw.rect(surface, section_outline, section_rect, 2, border_radius=18)
                self._draw_text(surface, section["label"], (section_rect.x + 18, section_rect.y + 14), self._font)

                for row in section["rows"]:
                    row_rect = pygame.Rect(*row["row_rect"])
                    selected = row["index"] == self._settings_selected_index
                    outline = row_outline if selected else row_idle_outline
                    pygame.draw.rect(surface, row_fill, row_rect, border_radius=14)
                    pygame.draw.rect(surface, outline, row_rect, 2, border_radius=14)
                    self._draw_text(surface, row["label"], (row_rect.x + 16, row_rect.y + 13), self._small_font, width=240)

                    if row["kind"] == "toggle":
                        self._draw_settings_button(
                            surface,
                            row["toggle_action"],
                            row["toggle_rect"],
                            row["value_text"],
                            active=row["value"],
                        )
                    else:
                        self._draw_settings_button(surface, row["decrease_action"], row["decrease_rect"], "-", active=False)
                        value_rect = pygame.Rect(*row["value_rect"])
                        pygame.draw.rect(surface, value_fill, value_rect, border_radius=12)
                        pygame.draw.rect(surface, row_idle_outline, value_rect, 1, border_radius=12)
                        value_surface = self._tiny_font.render(row["value_text"], True, (240, 245, 255))
                        surface.blit(value_surface, value_surface.get_rect(center=value_rect.center))
                        self._draw_settings_button(surface, row["increase_action"], row["increase_rect"], "+", active=False)
        else:
            for section in layout["control_sections"]:
                section_rect = pygame.Rect(*section["rect"])
                pygame.draw.rect(surface, section_fill, section_rect, border_radius=18)
                pygame.draw.rect(surface, section_outline, section_rect, 2, border_radius=18)
                self._draw_text(surface, section["label"], (section_rect.x + 16, section_rect.y + 12), self._small_font)
                for index, line in enumerate(section["lines"]):
                    self._draw_text(surface, line, (section_rect.x + 16, section_rect.y + 38 + (index * 16)), self._tiny_font, width=section_rect.width - 32)

        footer_rect = pygame.Rect(*layout["footer_rect"])
        footer_fill = (8, 14, 22) if high_contrast else (9, 14, 22)
        footer_outline = (184, 198, 224) if high_contrast else (88, 106, 134)
        pygame.draw.rect(surface, footer_fill, footer_rect, border_radius=14)
        pygame.draw.rect(surface, footer_outline, footer_rect, 2, border_radius=14)
        self._draw_text(
            surface,
            layout["footer_hint"],
            (footer_rect.x + 294, footer_rect.y + 14),
            self._tiny_font,
            width=320,
        )

        for button in layout["footer_buttons"]:
            self._draw_settings_button(
                surface,
                button["action"],
                button["rect"],
                button["label"],
                active=button.get("active", False),
            )

    def _controls_sections(self) -> list[dict[str, Any]]:
        return [
            {
                "label": "Global",
                "lines": [
                    "Esc: pause during a run",
                    "S: settings",
                    "F11: fullscreen",
                    "F: fast mode",
                    "M: mute audio",
                ],
            },
            {
                "label": "Title / Menu",
                "lines": [
                    "N: new run",
                    "C: continue",
                    "Q: quit",
                    "Enter / Space: confirm",
                ],
            },
            {
                "label": "Modifier Draft",
                "lines": [
                    "1-3 / click: select",
                    "Enter / Space: confirm",
                ],
            },
            {
                "label": "Map",
                "lines": [
                    "1-9 / click: route",
                    "Arrows: move focus",
                    "Enter / Space: confirm",
                    "Hover modifier icons",
                ],
            },
            {
                "label": "Combat",
                "lines": [
                    "1-9 / click: play card",
                    "E / Enter / Space: end turn",
                    "Pause button or Esc: pause",
                ],
            },
            {
                "label": "Reward / Event / Shop",
                "lines": [
                    "1-9 / click: select",
                    "Enter / Space: confirm",
                    "X: skip reward",
                    "C: continue",
                    "Shop: R reroll, L leave",
                ],
            },
            {
                "label": "Pause",
                "lines": [
                    "Esc: continue",
                    "Arrows: move selection",
                    "Enter / Space: activate",
                ],
            },
        ]

    def _handle_settings_event(self, event: Any, presentation: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self._settings_layout(presentation, self._settings_panel_position())
        row_count = len(layout["rows"])
        if row_count > 0:
            self._settings_selected_index = max(0, min(self._settings_selected_index, row_count - 1))

        if event.type == pygame.MOUSEMOTION:
            self._settings_hovered_action = self._settings_action_at_position(layout, event.pos)
            if layout["page"] == "general":
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
        if event.key == pygame.K_TAB:
            target_page = "controls" if layout["page"] == "general" else "general"
            return {"type": "open_controls_page" if target_page == "controls" else "open_general_settings_page"}

        if row_count == 0:
            return None

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
        page = "controls" if presentation.get("settings_page") == "controls" else "general"
        base_x = panel_pos[0] + 28
        tabs = [
            {
                "action": "tab:general",
                "label": "General",
                "rect": (base_x, panel_pos[1] + 102, SETTINGS_TAB_WIDTH, SETTINGS_TAB_HEIGHT),
                "active": page == "general",
            },
            {
                "action": "tab:controls",
                "label": "Controls",
                "rect": (base_x + SETTINGS_TAB_WIDTH + 12, panel_pos[1] + 102, SETTINGS_TAB_WIDTH, SETTINGS_TAB_HEIGHT),
                "active": page == "controls",
            },
        ]
        if page == "controls":
            return self._settings_controls_layout(panel_pos, tabs)
        return self._settings_general_layout(presentation, panel_pos, tabs)

    def _settings_general_layout(
        self,
        presentation: dict[str, Any],
        panel_pos: tuple[int, int],
        tabs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rows = []
        base_x = panel_pos[0] + 28
        row_height = 50
        row_gap = 8
        help_rect = (base_x, panel_pos[1] + 148, SETTINGS_PANEL_WIDTH - 56, 42)
        section_gap = 20
        section_width = (SETTINGS_PANEL_WIDTH - 56 - section_gap) // 2
        section_top = panel_pos[1] + 206
        footer_rect = (base_x, panel_pos[1] + SETTINGS_PANEL_HEIGHT - 66, SETTINGS_PANEL_WIDTH - 56, 46)
        section_height = footer_rect[1] - section_top - 18
        section_specs = {
            "display": {
                "label": "Display & Motion",
                "rect": (base_x, section_top, section_width, section_height),
                "rows": [],
            },
            "audio": {
                "label": "Audio & Accessibility",
                "rect": (base_x + section_width + section_gap, section_top, section_width, section_height),
                "rows": [],
            },
        }

        for index, row in enumerate(self._settings_rows(presentation)):
            section = section_specs[row["group"]]
            row_index = len(section["rows"])
            section_x, section_y, section_w, _ = section["rect"]
            row_x = section_x + 16
            row_y = section_y + 48 + (row_index * (row_height + row_gap))
            row_w = section_w - 32
            row_rect = (row_x, row_y, row_w, row_height)
            entry = {**row, "index": index, "row_rect": row_rect}
            if row["kind"] == "toggle":
                entry["toggle_rect"] = (row_x + row_w - 164, row_y + 9, 148, 32)
                entry["toggle_action"] = f"toggle:{row['id']}"
            else:
                plus_x = row_x + row_w - 48
                value_x = plus_x - 82
                minus_x = value_x - 42
                entry["decrease_rect"] = (minus_x, row_y + 9, 32, 32)
                entry["value_rect"] = (value_x, row_y + 9, 72, 32)
                entry["increase_rect"] = (plus_x, row_y + 9, 32, 32)
                entry["decrease_action"] = f"decrease:{row['id']}"
                entry["increase_action"] = f"increase:{row['id']}"
            rows.append(entry)
            section["rows"].append(entry)

        footer_buttons = [
            {"action": "reset", "label": "Reset Defaults", "rect": (footer_rect[0] + 16, footer_rect[1] + 4, 180, 38)},
            {"action": "close", "label": "Close", "rect": (footer_rect[0] + footer_rect[2] - 162, footer_rect[1] + 4, 146, 38), "active": True},
        ]
        return {
            "page": "general",
            "tabs": tabs,
            "rows": rows,
            "sections": [section_specs["display"], section_specs["audio"]],
            "help_rect": help_rect,
            "footer_rect": footer_rect,
            "footer_buttons": footer_buttons,
            "footer_hint": "Esc closes • Tab switches page",
            "control_sections": [],
        }

    def _settings_controls_layout(
        self,
        panel_pos: tuple[int, int],
        tabs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        base_x = panel_pos[0] + 28
        footer_rect = (base_x, panel_pos[1] + SETTINGS_PANEL_HEIGHT - 66, SETTINGS_PANEL_WIDTH - 56, 46)
        section_gap = 14
        section_width = (SETTINGS_PANEL_WIDTH - 56 - (section_gap * 2)) // 3
        section_top = panel_pos[1] + 150
        section_height = 112
        control_sections = []
        for index, section in enumerate(self._controls_sections()):
            column = index % 3
            row = index // 3
            rect = (
                base_x + (column * (section_width + section_gap)),
                section_top + (row * (section_height + 10)),
                section_width,
                section_height,
            )
            control_sections.append({**section, "rect": rect})

        footer_buttons = [
            {"action": "close", "label": "Close", "rect": (footer_rect[0] + footer_rect[2] - 162, footer_rect[1] + 4, 146, 38), "active": True},
        ]
        return {
            "page": "controls",
            "tabs": tabs,
            "rows": [],
            "sections": [],
            "help_rect": None,
            "footer_rect": footer_rect,
            "footer_buttons": footer_buttons,
            "footer_hint": "Esc closes • Tab switches page",
            "control_sections": control_sections,
        }

    def _settings_rows(self, presentation: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"id": "fullscreen", "group": "display", "label": "Display Mode", "description": "Toggle fullscreen or a resizable window.", "kind": "toggle", "value": presentation.get("fullscreen", True), "value_text": "Fullscreen" if presentation.get("fullscreen", True) else "Windowed"},
            {"id": "fast_mode", "group": "display", "label": "Fast Mode", "description": "Shorten non-critical feedback and transitions.", "kind": "toggle", "value": presentation.get("fast_mode", False), "value_text": "Enabled" if presentation.get("fast_mode", False) else "Disabled"},
            {"id": "presentation_scale", "group": "display", "label": "Display Scale", "description": "Fit the 1280x720 canvas comfortably inside the display.", "kind": "step", "value": presentation.get("presentation_scale", 1.0), "value_text": f"{int(presentation.get('presentation_scale', 1.0) * 100)}%"},
            {"id": "ui_scale", "group": "display", "label": "UI Text Scale", "description": "Scale text and labels for readability.", "kind": "step", "value": presentation.get("ui_scale", 1.0), "value_text": f"{int(presentation.get('ui_scale', 1.0) * 100)}%"},
            {"id": "screen_shake", "group": "display", "label": "Screen Shake", "description": "Toggle impact shake on heavy feedback moments.", "kind": "toggle", "value": presentation.get("screen_shake", True), "value_text": "Enabled" if presentation.get("screen_shake", True) else "Disabled"},
            {"id": "master_volume", "group": "audio", "label": "SFX Volume", "description": "Adjust sound effect volume for combat and UI cues.", "kind": "step", "value": presentation.get("master_volume", 0.8), "value_text": f"{int(presentation.get('master_volume', 0.8) * 100)}%"},
            {"id": "music_volume", "group": "audio", "label": "Music Volume", "description": "Reserve volume for music playback when tracks are added.", "kind": "step", "value": presentation.get("music_volume", 0.65), "value_text": f"{int(presentation.get('music_volume', 0.65) * 100)}%"},
            {"id": "muted", "group": "audio", "label": "Mute Audio", "description": "Silence all current and future audio output.", "kind": "toggle", "value": presentation.get("muted", False), "value_text": "Muted" if presentation.get("muted", False) else "Live"},
            {"id": "high_contrast", "group": "audio", "label": "High Contrast", "description": "Boost contrast and reduce reliance on subtle color differences.", "kind": "toggle", "value": presentation.get("high_contrast", False), "value_text": "Enabled" if presentation.get("high_contrast", False) else "Disabled"},
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
        if action_id == "tab:general":
            return {"type": "open_general_settings_page"}
        if action_id == "tab:controls":
            return {"type": "open_controls_page"}

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
        for tab in layout["tabs"]:
            if self._point_in_rect(position, tab["rect"]):
                return tab["action"]
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
                "settings_open": False,
                "settings_page": "general",
                "pause_open": False,
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
                "settings_open": False,
                "settings_page": "general",
                "pause_open": False,
            },
            "ui_notice": {"text": "Victory banner shown.", "level": "success"},
        }
    )
    return {
        "event_title": event_layout["title"],
        "event_choices": len(event_layout["choices"]),
        "victory_title": victory_layout["title"],
    }
