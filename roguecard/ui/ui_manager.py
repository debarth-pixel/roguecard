from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

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
    SHOP_PURGE_OFFER_ID,
    STATUS_ICON_GAP,
    STATUS_ICON_SIZE,
    STATUS_TOOLTIP_WIDTH,
    UI_SCALE_STEP,
    VOLUME_STEP,
    resolve_asset_path,
)
from ui.card_renderer import draw_card
from ui.character_select_ui import CharacterSelectUI
from ui.combat_layout import build_combat_layout
from ui.combat_ui import CombatUI
from ui.combat_ui_assets import combat_ui_assets
from ui.event_ui import EventUI
from ui.grayspine_intel_ui import GrayspineIntelUI
from ui.map_tablet_view import MapTabletView
from ui.map_ui import MapUI
from ui.machine_hud import (
    CYAN as MACHINE_CYAN,
    HEALTH_RED as MACHINE_HEALTH_RED,
    YELLOW as MACHINE_YELLOW,
)
from ui.modifier_draft_ui import ModifierDraftUI
from ui.relic_assets import relic_assets
from ui.reward_ui import RewardUI
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.shop_ui import ShopUI
from ui.sprite_sheet_assets import sprite_sheet_assets
from ui.status_icon_assets import status_icon_assets
from ui.title_ui import TitleUI
from ui.ui_system import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_LINE,
    COLOR_LINE_SOFT,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PANEL_ELEVATED,
    COLOR_RED,
    RADIUS_LG,
    RADIUS_MD,
    SPACE_2,
    SPACE_3,
    draw_focus_glow,
    draw_modal_scrim,
    draw_panel,
)

LOGGER = logging.getLogger(__name__)


class UIManager:
    def __init__(self) -> None:
        self.character_select_ui = CharacterSelectUI()
        self.combat_ui = CombatUI()
        self.event_ui = EventUI()
        self.grayspine_intel_ui = GrayspineIntelUI()
        self.map_ui = MapUI()
        self.modifier_draft_ui = ModifierDraftUI()
        self.reward_ui = RewardUI()
        self.shop_ui = ShopUI()
        self.map_tablet_view = MapTabletView(self.map_ui, self.combat_ui, self.shop_ui)
        self.title_ui = TitleUI()
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._micro_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._font_pack_cache: dict[tuple[float, float], dict[str, Any]] = {}
        self._settings_hovered_action: str | None = None
        self._settings_pressed_action: str | None = None
        self._settings_selected_index = 0
        self._pause_hovered_action: str | None = None
        self._pause_pressed_action: str | None = None
        self._pause_selected_index = 0
        self._modifier_hovered_id: str | None = None
        self._audio_callback: Callable[[str], None] | None = None
        self._purge_feedback: dict[str, Any] | None = None
        self._top_bar_warning_signature: tuple[str, ...] | None = None
        self._last_surface_size: tuple[int, int] = (1280, 720)

    def set_audio_callback(self, callback: Callable[[str], None] | None) -> None:
        self._audio_callback = callback
        self.shop_ui.set_sfx_callback(callback)

    def preload_assets(self) -> None:
        sprite_sheet_assets.preload()
        relic_assets.preload()
        status_icon_assets.preload()
        combat_ui_assets.preload()
        self.character_select_ui.preload_assets()
        self.map_ui.preload_assets()
        self.combat_ui.preload_assets()
        self.event_ui.preload_assets()
        self.grayspine_intel_ui.preload_assets()
        self.modifier_draft_ui.preload_assets()
        self.reward_ui.preload_assets()
        self.shop_ui.preload_assets()
        self.map_tablet_view.preload_assets()
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

    def handle_event(
        self,
        event: Any,
        state_snapshot: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        resolved_surface_size = self._resolve_surface_size(surface_size)
        presentation = state_snapshot.get("presentation", {})
        if pygame is not None:
            self._ensure_fonts(presentation.get("ui_scale", 1.0))
        if presentation.get("settings_open"):
            return self._handle_settings_event(event, presentation, resolved_surface_size)
        if presentation.get("intel_open"):
            return self.grayspine_intel_ui.handle_event(event, self._grayspine_intel_view_state(state_snapshot))
        if presentation.get("pause_open"):
            return self._handle_pause_event(event, state_snapshot, resolved_surface_size)

        current_state = state_snapshot["current_state"]
        if current_state in {"modifier_draft", "map", "combat", "reward", "shop", "event"} and not self.map_tablet_view.suppress_top_bar(current_state):
            top_action = self._handle_top_bar_event(event, state_snapshot, resolved_surface_size)
            if top_action is not None:
                return top_action

        if current_state in {"modifier_draft", "map", "combat", "reward", "shop", "event"} and not self.map_tablet_view.suppress_top_bar(current_state):
            self._update_modifier_hover(event, state_snapshot)
        else:
            self._modifier_hovered_id = None

        if self.map_tablet_view.is_transition_active():
            return None

        if current_state == "title" and state_snapshot.get("title") is not None:
            action = self.title_ui.handle_event(event, self._title_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "character_select" and state_snapshot.get("character_select") is not None:
            action = self.character_select_ui.handle_event(event, self._character_select_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "modifier_draft" and state_snapshot.get("modifier_draft") is not None:
            action = self.modifier_draft_ui.handle_event(event, self._modifier_draft_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "combat" and state_snapshot["combat"] is not None:
            action = self.combat_ui.handle_event(event, self._combat_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "reward" and state_snapshot["reward"] is not None:
            action = self.reward_ui.handle_event(event, self._reward_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "event" and state_snapshot["event"] is not None:
            action = self.event_ui.handle_event(event, self._event_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "shop" and state_snapshot["shop"] is not None:
            action = self.shop_ui.handle_event(event, self._shop_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if current_state == "map" and state_snapshot["map"] is not None:
            action = self.map_tablet_view.handle_event(event, self._map_view_state(state_snapshot), resolved_surface_size)
            if action is not None:
                return action

        if pygame is not None and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                return {"type": "new_run"}
            if current_state in {"victory", "game_over"} and event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                return {"type": "new_run"}

        return None

    def poll_action(self, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        if self.map_tablet_view.is_transition_active():
            return None
        if state_snapshot["current_state"] == "combat" and state_snapshot["combat"] is not None:
            return self.combat_ui.poll_action(self._combat_view_state(state_snapshot))
        return None

    def update(self, delta_time: float, state_snapshot: dict[str, Any] | None = None) -> None:
        self.map_tablet_view.update(delta_time)
        shop_view_state = None
        if isinstance(state_snapshot, dict) and state_snapshot.get("shop") is not None:
            shop_view_state = self._shop_view_state(state_snapshot)
        self.shop_ui.update(delta_time, shop_view_state, transition_active=self.map_tablet_view.is_transition_active())
        if self._purge_feedback is not None:
            self._purge_feedback["elapsed"] = min(
                self._purge_feedback["duration"],
                self._purge_feedback["elapsed"] + max(0.0, delta_time),
            )
            if self._purge_feedback["elapsed"] >= self._purge_feedback["duration"]:
                self._purge_feedback = None

    def apply_snapshot_feedback(
        self,
        action_type: str,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> None:
        before_combat = None if before_snapshot.get("combat") is None else self._combat_view_state(before_snapshot)
        after_combat = None if after_snapshot.get("combat") is None else self._combat_view_state(after_snapshot)
        self.combat_ui.apply_snapshot_feedback(action_type, before_combat, after_combat)
        before_shop = None if before_snapshot.get("shop") is None else self._shop_view_state(before_snapshot)
        after_shop = None if after_snapshot.get("shop") is None else self._shop_view_state(after_snapshot)
        self.shop_ui.handle_snapshot_feedback(action_type, before_shop, after_shop)
        self._apply_purge_feedback(action_type, before_snapshot, after_snapshot)

    def begin_map_to_combat_transition(self, state_snapshot: dict[str, Any]) -> None:
        if state_snapshot.get("map") is None or state_snapshot.get("combat") is None:
            return
        self.map_tablet_view.begin_map_to_combat_transition(
            self._map_view_state(state_snapshot),
            self._combat_view_state(state_snapshot),
        )

    def begin_map_to_shop_transition(self, state_snapshot: dict[str, Any]) -> None:
        if state_snapshot.get("map") is None or state_snapshot.get("shop") is None:
            return
        self.map_tablet_view.begin_map_to_shop_transition(
            self._map_view_state(state_snapshot),
            self._shop_view_state(state_snapshot),
        )

    def begin_map_enter_transition(self, state_snapshot: dict[str, Any]) -> None:
        if state_snapshot.get("map") is None:
            return
        self.map_tablet_view.begin_map_enter_transition(self._map_view_state(state_snapshot))

    def handle_action_denied(self, action_type: str, state_snapshot: dict[str, Any]) -> None:
        if state_snapshot.get("shop") is not None:
            self.shop_ui.handle_action_denied(action_type)

    def is_transition_active(self) -> bool:
        return self.map_tablet_view.is_transition_active()

    def render(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._last_surface_size = surface.get_size()
        self._ensure_fonts(state_snapshot.get("presentation", {}).get("ui_scale", 1.0))
        current_state = state_snapshot["current_state"]
        map_view_state = None if state_snapshot.get("map") is None else self._map_view_state(state_snapshot)
        combat_view_state = None if state_snapshot.get("combat") is None else self._combat_view_state(state_snapshot)
        shop_view_state = None if state_snapshot.get("shop") is None else self._shop_view_state(state_snapshot)

        if self.map_tablet_view.is_transition_active():
            self.map_tablet_view.render(surface, map_view_state, combat_view_state, shop_view_state)
        elif current_state == "title" and state_snapshot.get("title") is not None:
            self.title_ui.render(surface, self._title_view_state(state_snapshot))
        elif current_state == "character_select" and state_snapshot.get("character_select") is not None:
            self.character_select_ui.render(surface, self._character_select_view_state(state_snapshot))
        elif current_state == "modifier_draft" and state_snapshot.get("modifier_draft") is not None:
            self.modifier_draft_ui.render(surface, self._modifier_draft_view_state(state_snapshot))
        elif current_state == "combat" and state_snapshot["combat"] is not None:
            self.combat_ui.render(surface, combat_view_state)
        elif current_state == "event" and state_snapshot["event"] is not None:
            self.event_ui.render(surface, self._event_view_state(state_snapshot))
        elif current_state == "reward" and state_snapshot["reward"] is not None:
            self.reward_ui.render(surface, self._reward_view_state(state_snapshot))
        elif current_state == "shop" and state_snapshot["shop"] is not None:
            self.shop_ui.render(surface, shop_view_state)
        elif current_state == "map" and state_snapshot["map"] is not None:
            self.map_tablet_view.render(surface, map_view_state)
        elif current_state in {"victory", "game_over"}:
            self._render_status_screen(surface, self._status_screen_layout(state_snapshot))
        else:
            surface.fill((18, 21, 28))

        self._render_purge_feedback(surface)
        if self._should_render_top_bar(current_state):
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
        elif presentation.get("intel_open"):
            self.grayspine_intel_ui.render(surface, self._grayspine_intel_view_state(state_snapshot))
        elif presentation.get("pause_open"):
            self._render_pause_overlay(surface, state_snapshot)

    def simulate_ui(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        if self.map_tablet_view.is_transition_active():
            map_view_state = None if state_snapshot.get("map") is None else self._map_view_state(state_snapshot)
            return self.map_tablet_view.build_layout(map_view_state, self._last_surface_size)
        if state_snapshot["current_state"] == "title" and state_snapshot.get("title") is not None:
            return self.title_ui.build_layout(self._title_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "character_select" and state_snapshot.get("character_select") is not None:
            return self.character_select_ui.build_layout(self._character_select_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "modifier_draft" and state_snapshot.get("modifier_draft") is not None:
            return self.modifier_draft_ui.build_layout(self._modifier_draft_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "combat" and state_snapshot["combat"] is not None:
            return self.combat_ui.build_layout(self._combat_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "event" and state_snapshot["event"] is not None:
            return self.event_ui.build_layout(self._event_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "reward" and state_snapshot["reward"] is not None:
            return self.reward_ui.build_layout(self._reward_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "shop" and state_snapshot["shop"] is not None:
            return self.shop_ui.build_layout(self._shop_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] == "map" and state_snapshot["map"] is not None:
            return self.map_tablet_view.build_layout(self._map_view_state(state_snapshot), self._last_surface_size)
        if state_snapshot["current_state"] in {"victory", "game_over"}:
            return self._status_screen_layout(state_snapshot)
        return {"status_message": state_snapshot["status_message"]}

    def _should_render_top_bar(self, current_state: str) -> bool:
        return current_state not in {"title", "character_select", "victory", "game_over"} and not self.map_tablet_view.suppress_top_bar(current_state)

    def _combat_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        combat_state = state_snapshot["combat"]
        hand = state_snapshot.get("player_hand") or []
        campaign = state_snapshot.get("campaign") or {}
        return {
            "status_message": state_snapshot["status_message"],
            "character": state_snapshot.get("character"),
            "player": combat_state["player"],
            "enemies": combat_state["enemies"],
            "turn_number": combat_state.get("turn_number", 0),
            "turn_owner": combat_state.get("turn_owner", "player"),
            "living_enemy_ids": combat_state.get("living_enemy_ids", []),
            "enemy_phase": combat_state.get("enemy_phase", {}),
            "event_log": combat_state.get("event_log", []),
            "feedback_events": combat_state.get("feedback_events", []),
            "active_bark": combat_state.get("active_bark"),
            "player_hand": hand,
            "run_modifiers": list((state_snapshot.get("run_modifiers") or {}).get("active", [])),
            "run_state": state_snapshot.get("run_state"),
            "map_id": campaign.get("map_id"),
            "map_index": campaign.get("map_index"),
            "branch_faction": campaign.get("branch_faction"),
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

    def _grayspine_intel_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        intel_state = state_snapshot.get("grayspine_intel") or {}
        selected_faction_id = state_snapshot.get("presentation", {}).get("intel_selected_faction")
        if selected_faction_id is None:
            selected_faction_id = intel_state.get("selected_faction_id")
        return {
            **intel_state,
            "selected_faction_id": selected_faction_id,
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
        layout = self._top_bar_layout(state_snapshot, surface.get_size())
        is_combat = state_snapshot.get("current_state") == "combat"
        if is_combat:
            self._render_combat_sleek_top_bar(surface, layout, high_contrast=high_contrast)
            return
        accent = (220, 230, 255) if high_contrast else COLOR_CYAN
        state_rect = pygame.Rect(*layout["state_rect"])
        summary_rect = pygame.Rect(*layout["summary_rect"])
        state_fill = COLOR_PANEL_ELEVATED if not is_combat else (12, 18, 30)
        summary_fill = COLOR_PANEL if not is_combat else (9, 14, 24)
        summary_accent = COLOR_LINE if not is_combat else (88, 120, 168)
        if is_combat:
            draw_focus_glow(surface, state_rect, accent=(72, 108, 156), alpha=18, inflate_x=12, inflate_y=12, radius=RADIUS_MD)
            draw_focus_glow(surface, summary_rect, accent=(72, 108, 156), alpha=14, inflate_x=18, inflate_y=12, radius=RADIUS_LG)
        draw_panel(surface, state_rect, accent=summary_accent, fill=state_fill, radius=RADIUS_MD, border_width=1, shadow_alpha=0)
        self._draw_text(surface, layout["state_label"], (state_rect.x + 14, state_rect.y + 9), self._tiny_font, width=state_rect.width - 28)

        draw_panel(surface, summary_rect, accent=summary_accent, fill=summary_fill, radius=RADIUS_LG, border_width=1, shadow_alpha=0)
        for index, segment in enumerate(layout["segments"]):
            rect = pygame.Rect(*segment["rect"])
            if segment.get("active"):
                draw_focus_glow(surface, rect, accent=segment["accent"], alpha=22, inflate_x=10, inflate_y=10, radius=RADIUS_MD)
            if index > 0:
                pygame.draw.line(surface, COLOR_LINE_SOFT, (rect.x, summary_rect.y + 10), (rect.x, summary_rect.bottom - 10), 1)
            pygame.draw.rect(surface, segment["accent"], pygame.Rect(rect.x + 12, rect.y + 12, 4, rect.height - 24), border_radius=2)
            self._draw_text(surface, segment["label"], (rect.x + 24, rect.y + 15), self._tiny_font, width=rect.width - 32)

        if layout["secondary_text"]:
            self._draw_text(
                surface,
                layout["secondary_text"],
                (summary_rect.x + 16, summary_rect.bottom + 6),
                self._tiny_font,
                width=summary_rect.width - 32,
            )

        if state_snapshot.get("current_state") != "combat":
            self._render_modifier_icons(surface, layout["modifier_icons"], high_contrast)

        intel_rect = layout.get("intel_rect")
        if intel_rect is not None:
            intel_rect_obj = pygame.Rect(*intel_rect)
            intel_hovered = self._pause_hovered_action == "top_intel"
            intel_pressed = self._pause_pressed_action == "top_intel"
            intel_fill = (24, 34, 50)
            if intel_hovered:
                intel_fill = (40, 54, 76)
            if intel_pressed:
                intel_fill = (255, 214, 110)
            draw_panel(
                surface,
                intel_rect_obj,
                accent=accent if not intel_pressed else COLOR_GOLD,
                fill=intel_fill,
                radius=RADIUS_MD,
                border_width=2 if intel_hovered or intel_pressed else 1,
                shadow_alpha=0,
            )
            intel_label_color = (18, 24, 36) if intel_pressed else (240, 245, 255)
            intel_label = self._small_font.render("Intel", True, intel_label_color)
            surface.blit(intel_label, intel_label.get_rect(center=intel_rect_obj.center))

        pause_rect = pygame.Rect(*layout["pause_rect"])
        hovered = self._pause_hovered_action == "top_pause"
        pressed = self._pause_pressed_action == "top_pause"
        fill = (24, 34, 50)
        if hovered:
            fill = (40, 54, 76)
        if pressed:
            fill = (255, 214, 110)
        draw_panel(
            surface,
            pause_rect,
            accent=accent if not pressed else COLOR_GOLD,
            fill=fill,
            radius=RADIUS_MD,
            border_width=2 if hovered or pressed else 1,
            shadow_alpha=0,
        )
        label_color = (18, 24, 36) if pressed else (240, 245, 255)
        pause_label = self._small_font.render("Pause", True, label_color)
        surface.blit(pause_label, pause_label.get_rect(center=pause_rect.center))

    def _render_combat_sleek_top_bar(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        accent = (220, 238, 255) if high_contrast else COLOR_CYAN
        state_rect = pygame.Rect(*layout["state_rect"])
        summary_rect = pygame.Rect(*layout["summary_rect"])
        self._draw_combat_glass_panel(surface, state_rect, border=accent, fill=(5, 12, 20, 206), cut=10)
        self._draw_combat_glass_panel(surface, summary_rect, border=(70, 174, 214) if not high_contrast else accent, fill=(5, 13, 22, 218), cut=14)

        warnings = self._combat_top_bar_warnings(layout)
        signature = tuple(sorted(warnings))
        if signature and signature != self._top_bar_warning_signature:
            LOGGER.warning("Combat top HUD warnings: %s", " | ".join(signature))
            self._top_bar_warning_signature = signature
        elif not signature:
            self._top_bar_warning_signature = None

        state_title = str(layout.get("state_title", "Combat")).upper()
        state_subtitle = str(layout.get("state_subtitle", "")).upper()
        title = self._fit_single_line(state_title, self._tiny_font, max(24, state_rect.width - 28))
        subtitle = self._fit_single_line(state_subtitle, self._tiny_font, max(24, state_rect.width - 28))
        title_surface = self._tiny_font.render(title, True, (188, 208, 226))
        subtitle_color = COLOR_GOLD if "PLAYER" in state_subtitle else (232, 118, 132)
        subtitle_surface = self._tiny_font.render(subtitle, True, subtitle_color)
        divider_x = state_rect.x + max(78, min(state_rect.width - 78, title_surface.get_width() + 24))
        pygame.draw.line(surface, (46, 86, 108), (divider_x, state_rect.y + 9), (divider_x, state_rect.bottom - 9), 1)
        surface.blit(title_surface, (state_rect.x + 15, state_rect.y + max(8, (state_rect.height - title_surface.get_height()) // 2)))
        surface.blit(subtitle_surface, (divider_x + 15, state_rect.y + max(8, (state_rect.height - subtitle_surface.get_height()) // 2)))

        for index, segment in enumerate(layout.get("segments", [])):
            rect = pygame.Rect(*segment["rect"])
            if index > 0:
                pygame.draw.line(surface, (82, 104, 130), (rect.x, summary_rect.y + 8), (rect.x, summary_rect.bottom - 8), 1)
            if segment.get("active"):
                glow_rect = rect.inflate(8, 6)
                glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(glow, (*segment["accent"], 24), glow.get_rect(), border_radius=8)
                surface.blit(glow, glow_rect.topleft)
            label = self._fit_single_line(str(segment.get("label", "")).upper(), self._tiny_font, rect.width - 24)
            sublabel = self._fit_single_line(str(segment.get("sublabel", "")).upper(), self._micro_font, rect.width - 24)
            label_surface = self._tiny_font.render(label, True, (204, 216, 232))
            sublabel_surface = self._micro_font.render(sublabel, True, segment["accent"])
            content_h = label_surface.get_height() + sublabel_surface.get_height() + 2
            content_y = rect.y + max(3, (rect.height - content_h) // 2)
            surface.blit(label_surface, (rect.x + 12, content_y))
            surface.blit(sublabel_surface, (rect.x + 12, content_y + label_surface.get_height() + 2))

        intel_rect = layout.get("intel_rect")
        if intel_rect is not None:
            self._draw_combat_top_action(
                surface,
                pygame.Rect(*intel_rect),
                label="INTEL",
                action_id="top_intel",
                accent=accent,
                high_contrast=high_contrast,
            )
        self._draw_combat_top_action(
            surface,
            pygame.Rect(*layout["pause_rect"]),
            label="PAUSE",
            action_id="top_pause",
            accent=accent,
            high_contrast=high_contrast,
            pause_icon=True,
        )

    def _draw_combat_top_action(
        self,
        surface: Any,
        rect: Any,
        *,
        label: str,
        action_id: str,
        accent: tuple[int, int, int],
        high_contrast: bool,
        pause_icon: bool = False,
    ) -> None:
        button_rect = pygame.Rect(rect)
        hovered = self._pause_hovered_action == action_id
        pressed = self._pause_pressed_action == action_id
        border = COLOR_GOLD if pressed else ((220, 238, 255) if high_contrast else accent)
        fill = (18, 28, 42, 230) if hovered else (7, 16, 26, 218)
        if pressed:
            fill = (255, 214, 110, 232)
        self._draw_combat_glass_panel(surface, button_rect, border=border, fill=fill, cut=7)
        text_color = (15, 22, 32) if pressed else ((255, 246, 190) if hovered else (190, 214, 232))
        label_text = self._fit_single_line(label, self._tiny_font, button_rect.width - (38 if pause_icon else 18))
        label_surface = self._tiny_font.render(label_text, True, text_color)
        center_x = button_rect.centerx
        if pause_icon:
            icon_x = button_rect.x + max(13, button_rect.width // 6)
            icon_y = button_rect.centery - 7
            icon_color = text_color
            pygame.draw.rect(surface, icon_color, pygame.Rect(icon_x, icon_y, 4, 14), border_radius=1)
            pygame.draw.rect(surface, icon_color, pygame.Rect(icon_x + 10, icon_y, 4, 14), border_radius=1)
            center_x += 10
        surface.blit(label_surface, label_surface.get_rect(center=(center_x, button_rect.centery)))

    def _draw_combat_glass_panel(
        self,
        surface: Any,
        rect_value: Any,
        *,
        border: tuple[int, int, int],
        fill: tuple[int, int, int, int],
        cut: int,
    ) -> None:
        rect = pygame.Rect(rect_value)
        if rect.width <= 0 or rect.height <= 0:
            return
        cut = max(0, min(cut, rect.width // 3, rect.height // 2))
        points = [
            (rect.x + cut, rect.y),
            (rect.right - cut, rect.y),
            (rect.right, rect.y + cut),
            (rect.right, rect.bottom - cut),
            (rect.right - cut, rect.bottom),
            (rect.x + cut, rect.bottom),
            (rect.x, rect.bottom - cut),
            (rect.x, rect.y + cut),
        ]
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        local = pygame.Rect(0, 0, rect.width, rect.height)
        local_points = [(x - rect.x, y - rect.y) for x, y in points]
        pygame.draw.polygon(panel, fill, local_points)
        pygame.draw.polygon(panel, (*border, 182), local_points, 1)
        pygame.draw.line(panel, (*border, 80), (cut + 5, 2), (local.right - cut - 5, 2), 1)
        surface.blit(panel, rect.topleft)

    def _render_combat_machine_top_bar(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        del high_contrast
        hud_rect = pygame.Rect(*layout["machine_hud_rect"])
        combat_ui_assets.blit(surface, "top_machine_hud_frame", hud_rect)

        warnings = self._combat_top_bar_warnings(layout)
        signature = tuple(sorted(warnings))
        if signature and signature != self._top_bar_warning_signature:
            LOGGER.warning("Combat top HUD warnings: %s", " | ".join(signature))
            self._top_bar_warning_signature = signature
        elif not signature:
            self._top_bar_warning_signature = None

        for segment in layout["segments"]:
            rect = pygame.Rect(*segment["rect"])
            label = self._fit_single_line(str(segment["label"]), self._small_font, rect.width - 34)
            sublabel = self._fit_single_line(str(segment.get("sublabel", "")), self._tiny_font, rect.width - 34)
            line_rect = pygame.Rect(rect.x + 9, rect.y + 6, 4, max(14, rect.height - 12))
            pygame.draw.rect(surface, segment["accent"], line_rect, border_radius=2)
            label_surface = self._small_font.render(label.upper(), True, (236, 244, 255))
            sublabel_surface = self._tiny_font.render(sublabel.upper(), True, segment["accent"])
            content_y = rect.y + max(2, (rect.height - (label_surface.get_height() + sublabel_surface.get_height() + 2)) // 2)
            label_y = max(rect.y + 2, content_y)
            sublabel_y = min(rect.bottom - sublabel_surface.get_height() - 2, label_y + label_surface.get_height())
            surface.blit(label_surface, (rect.x + 24, label_y))
            surface.blit(sublabel_surface, (rect.x + 24, sublabel_y))

        intel_rect = layout.get("intel_rect")
        if intel_rect is not None:
            intel = pygame.Rect(*intel_rect)
            label_color = MACHINE_YELLOW if self._pause_hovered_action == "top_intel" else (236, 244, 255)
            label = self._small_font.render("INTEL", True, label_color)
            surface.blit(label, label.get_rect(center=intel.center))

        pause_rect = pygame.Rect(*layout["pause_rect"])
        pause_asset = "pause_button_pressed" if self._pause_pressed_action == "top_pause" else "pause_button_normal"
        combat_ui_assets.blit(surface, pause_asset, pause_rect)
        pause_color = (18, 24, 36) if self._pause_pressed_action == "top_pause" else (236, 244, 255)
        if self._pause_hovered_action == "top_pause":
            pause_color = (255, 246, 190)
        pause_label = self._small_font.render("PAUSE", True, pause_color)
        surface.blit(pause_label, pause_label.get_rect(center=pause_rect.center))

    def _top_bar_layout(self, state_snapshot: dict[str, Any], surface_size: tuple[int, int] | None = None) -> dict[str, Any]:
        resolved_surface_size = surface_size or self._last_surface_size
        surface_width, _surface_height = resolved_surface_size
        current_state = state_snapshot["current_state"]
        if current_state == "combat":
            intel_available = isinstance(state_snapshot.get("grayspine_intel"), dict)
            combat_layout = build_combat_layout(resolved_surface_size, intel_available=intel_available)
            pause_rect = combat_layout.top_pause_rect
            intel_rect = combat_layout.top_intel_rect
            hud_rect = combat_layout.top_hud_rect
            character = state_snapshot.get("character") if isinstance(state_snapshot.get("character"), dict) else {}
            campaign = state_snapshot.get("campaign") if isinstance(state_snapshot.get("campaign"), dict) else {}
            combat_state = state_snapshot.get("combat") if isinstance(state_snapshot.get("combat"), dict) else {}
            player = combat_state.get("player") if isinstance(combat_state.get("player"), dict) else state_snapshot.get("player", {})
            map_name = campaign.get("map_name", "Outskirts") if isinstance(campaign, dict) else "Outskirts"
            map_index = campaign.get("map_index", 1) if isinstance(campaign, dict) else 1
            map_label = f"M{map_index} {map_name}" if isinstance(map_index, int) and map_index > 0 else str(map_name)
            turn_owner = str(combat_state.get("turn_owner", "player")).replace("_", " ").title()
            state_w = max(
                194,
                min(
                    300,
                    int(round(hud_rect[2] * 0.28)),
                    self._tiny_font.size(f"COMBAT  {turn_owner.upper()} TURN")[0] + 46,
                ),
            )
            action_gap = max(10, int(round(resolved_surface_size[0] * 0.01)))
            state_rect = (hud_rect[0], hud_rect[1], state_w, hud_rect[3])
            summary_rect = (
                state_rect[0] + state_rect[2] + action_gap,
                hud_rect[1],
                max(220, hud_rect[2] - state_w - action_gap),
                hud_rect[3],
            )
            segment_specs = [
                {
                    "label": str(character.get("name", "Runner")),
                    "sublabel": f"HP {player.get('current_hp', 0)}/{player.get('max_hp', 0)}",
                    "accent": tuple(character.get("accent_color", [232, 88, 72])),
                    "preferred_width": 236,
                    "minimum_width": 150,
                    "active": True,
                },
                {
                    "label": map_label,
                    "sublabel": "Sector",
                    "accent": COLOR_CYAN,
                    "preferred_width": 210,
                    "minimum_width": 134,
                },
                {
                    "label": f"{player.get('credits', 0)} cr",
                    "sublabel": "Credits",
                    "accent": COLOR_GOLD,
                    "preferred_width": 150,
                    "minimum_width": 96,
                },
            ]
            segments = self._combat_sleek_segment_layout(segment_specs, summary_rect)
            return {
                "state_rect": state_rect,
                "summary_rect": summary_rect,
                "state_title": "Combat",
                "state_subtitle": f"{turn_owner} Turn",
                "state_label": f"Combat | {turn_owner} Turn",
                "intel_rect": intel_rect,
                "pause_rect": pause_rect,
                "segments": segments,
                "secondary_text": "",
                "modifier_icons": [],
            }
        state_label = {
            "modifier_draft": "Relic Draft",
            "map": "Map",
            "combat": "Combat",
            "reward": "Reward",
            "shop": "Shop",
            "event": "Event",
        }.get(current_state, current_state.replace("_", " ").title())
        intel_available = isinstance(state_snapshot.get("grayspine_intel"), dict)
        pause_rect = (surface_width - PAUSE_BUTTON_WIDTH - 24, 12, PAUSE_BUTTON_WIDTH, PAUSE_BUTTON_HEIGHT)
        intel_rect = None
        if intel_available:
            intel_rect = (pause_rect[0] - 96, 12, 84, PAUSE_BUTTON_HEIGHT)
        state_width = max(118, self._tiny_font.size(state_label)[0] + 28)
        state_rect = (24, 12, state_width, 36)
        active_modifiers = []
        if current_state != "combat":
            active_modifiers = list(state_snapshot.get("run_modifiers", {}).get("active", []))
        if len(active_modifiers) > 6:
            active_modifiers = active_modifiers[-6:]
        strip_width = 0
        if active_modifiers:
            strip_width = (len(active_modifiers) * STATUS_ICON_SIZE) + ((len(active_modifiers) - 1) * STATUS_ICON_GAP)
        modifier_icons = []
        icon_anchor_x = intel_rect[0] if intel_rect is not None else pause_rect[0]
        modifier_start_x = icon_anchor_x - 16 - strip_width
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
        segment_items = self._top_bar_stat_items(state_snapshot)
        segment_widths = [max(88, self._tiny_font.size(item["label"])[0] + 40) for item in segment_items]
        summary_width = min(
            modifier_start_x - (state_rect[0] + state_rect[2]) - 20,
            sum(segment_widths) + 12,
        )
        summary_width = max(320, summary_width)
        summary_rect = (state_rect[0] + state_rect[2] + 12, 12, summary_width, 48)
        segments = []
        cursor_x = summary_rect[0] + 8
        for index, item in enumerate(segment_items):
            width = segment_widths[index]
            if cursor_x + width > summary_rect[0] + summary_rect[2] - 8:
                break
            segments.append({**item, "rect": (cursor_x, summary_rect[1] + 4, width, summary_rect[3] - 8)})
            cursor_x += width
        secondary_text = self._top_bar_secondary_text(state_snapshot)
        return {
            "state_rect": state_rect,
            "summary_rect": summary_rect,
            "state_label": state_label,
            "intel_rect": intel_rect,
            "pause_rect": pause_rect,
            "segments": segments,
            "secondary_text": secondary_text,
            "modifier_icons": modifier_icons,
        }

    def _combat_sleek_segment_layout(
        self,
        segment_specs: list[dict[str, Any]],
        summary_rect: tuple[int, int, int, int],
    ) -> list[dict[str, Any]]:
        gap = 0
        segment_count = max(1, len(segment_specs))
        content_rect = (
            summary_rect[0] + 10,
            summary_rect[1] + 4,
            max(1, summary_rect[2] - 20),
            max(1, summary_rect[3] - 8),
        )
        widths = self._combat_top_segment_widths(segment_specs, max(1, content_rect[2] - (gap * (segment_count - 1))))
        segments: list[dict[str, Any]] = []
        cursor_x = content_rect[0]
        for index, spec in enumerate(segment_specs):
            width = widths[index]
            segments.append({**spec, "rect": (cursor_x, content_rect[1], width, content_rect[3])})
            cursor_x += width + gap
        return segments

    def _combat_machine_segment_layout(
        self,
        segment_specs: list[dict[str, Any]],
        hud_rect: tuple[int, int, int, int],
    ) -> list[dict[str, Any]]:
        x, y, width, height = hud_rect
        inset_x = max(16, int(round(width * 0.032)))
        inset_top = max(7, int(round(height * 0.10)))
        inset_bottom = max(8, int(round(height * 0.11)))
        inner_x = x + inset_x
        inner_y = y + inset_top
        inner_w = max(1, width - (inset_x * 2))
        inner_h = max(1, height - inset_top - inset_bottom)
        row_gap = max(3, int(round(height * 0.035)))
        top_h = max(24, (inner_h - row_gap) // 2)
        bottom_h = max(22, inner_h - top_h - row_gap)
        top_y = inner_y
        bottom_y = top_y + top_h + row_gap

        boxes = (
            (0.000, 0.235, top_y, top_h),
            (0.245, 0.360, top_y, top_h),
            (0.615, 0.360, top_y, top_h),
            (0.000, 0.430, bottom_y, bottom_h),
            (0.445, 0.280, bottom_y, bottom_h),
        )
        segments: list[dict[str, Any]] = []
        for spec, (left_ratio, width_ratio, row_y, row_h) in zip(segment_specs, boxes):
            rect = (
                inner_x + int(round(inner_w * left_ratio)),
                int(row_y),
                max(76, int(round(inner_w * width_ratio))),
                int(row_h),
            )
            segments.append({**spec, "rect": rect})
        return segments

    def _combat_top_segment_measurements(self, segment_specs: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
        measured: list[int] = []
        preferred: list[int] = []
        for spec in segment_specs:
            label = str(spec.get("label", "")).upper()
            sublabel = str(spec.get("sublabel", "")).upper()
            label_width = self._small_font.size(label)[0] if self._small_font is not None else len(label) * 11
            sublabel_width = self._tiny_font.size(sublabel)[0] if self._tiny_font is not None else len(sublabel) * 7
            content_width = max(label_width, sublabel_width) + 38
            minimum = max(int(spec.get("minimum_width", 96)), content_width)
            measured.append(minimum)
            preferred.append(max(minimum, int(spec.get("preferred_width", minimum))))
        return measured, preferred

    def _combat_top_required_width(self, segment_specs: list[dict[str, Any]], gap: int) -> int:
        measured, _preferred = self._combat_top_segment_measurements(segment_specs)
        return sum(measured) + (max(0, len(segment_specs) - 1) * gap)

    def _combat_top_split_index(self, segment_specs: list[dict[str, Any]], row_width: int, gap: int) -> int:
        candidates: list[tuple[int, int, int]] = []
        for split_index in range(1, len(segment_specs)):
            first_required = self._combat_top_required_width(segment_specs[:split_index], gap)
            second_required = self._combat_top_required_width(segment_specs[split_index:], gap)
            overflow = max(0, first_required - row_width) + max(0, second_required - row_width)
            balance = abs((len(segment_specs[:split_index])) - (len(segment_specs[split_index:])))
            candidates.append((overflow, balance, abs(split_index - 3), split_index))
        return min(candidates)[-1] if candidates else max(1, len(segment_specs) // 2)

    def _combat_top_row_layout(
        self,
        segment_specs: list[dict[str, Any]],
        row_rect: tuple[int, int, int, int],
        gap: int,
        *,
        align: str = "left",
    ) -> list[dict[str, Any]]:
        available_width = max(1, row_rect[2] - (max(0, len(segment_specs) - 1) * gap))
        widths = self._combat_top_segment_widths(segment_specs, available_width)
        total_width = sum(widths) + (max(0, len(widths) - 1) * gap)
        cursor_x = row_rect[0]
        if align == "center":
            cursor_x += max(0, (row_rect[2] - total_width) // 2)
        segments: list[dict[str, Any]] = []
        for spec, width in zip(segment_specs, widths):
            segments.append({**spec, "rect": (cursor_x, row_rect[1], width, row_rect[3])})
            cursor_x += width + gap
        return segments

    def _combat_top_segment_widths(self, segment_specs: list[dict[str, Any]], available_width: int) -> list[int]:
        measured, preferred = self._combat_top_segment_measurements(segment_specs)
        preferred_total = sum(preferred)
        if preferred_total <= available_width:
            slack = available_width - preferred_total
            weights = [max(1, width - minimum) for width, minimum in zip(preferred, measured)]
            total_weight = max(1, sum(weights))
            widths = [width + int(slack * (weight / total_weight)) for width, weight in zip(preferred, weights)]
            widths[-1] += available_width - sum(widths)
            return widths

        minimum_total = sum(measured)
        if minimum_total <= available_width:
            slack = available_width - minimum_total
            weights = [max(1, target - minimum) for target, minimum in zip(preferred, measured)]
            total_weight = max(1, sum(weights))
            widths = [minimum + int(slack * (weight / total_weight)) for minimum, weight in zip(measured, weights)]
            widths[-1] += available_width - sum(widths)
            return widths

        ratio = available_width / max(1, minimum_total)
        widths = [max(78, int(width * ratio)) for width in measured]
        widths[-1] += available_width - sum(widths)
        if widths[-1] < 72:
            deficit = 72 - widths[-1]
            widths[-1] = 72
            for index in range(len(widths) - 2, -1, -1):
                take = min(deficit, max(0, widths[index] - 78))
                widths[index] -= take
                deficit -= take
                if deficit <= 0:
                    break
        return widths

    def _top_bar_stat_items(self, state_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        player = state_snapshot.get("player")
        character = state_snapshot.get("character")
        campaign = state_snapshot.get("campaign")
        run_state = state_snapshot.get("run_state")
        current_state = state_snapshot.get("current_state")
        items: list[dict[str, Any]] = []
        if isinstance(character, dict):
            accent = tuple(character.get("accent_color", [120, 150, 190]))
            items.append({"label": character.get("name", "Runner"), "accent": accent})
        if isinstance(campaign, dict):
            map_name = campaign.get("map_name")
            map_index = campaign.get("map_index")
            if isinstance(map_name, str) and map_name:
                map_label = map_name if not isinstance(map_index, int) or map_index <= 0 else f"M{map_index} {map_name}"
                items.append({"label": map_label, "accent": (92, 198, 240)})
        if isinstance(player, dict):
            items.append(
                {
                    "label": f"HP {player.get('current_hp', 0)}/{player.get('max_hp', 0)}",
                    "accent": COLOR_RED,
                }
            )
            items.append(
                {
                    "label": f"{player.get('credits', 0)} cr",
                    "accent": COLOR_GOLD,
                }
            )
        if current_state != "combat" and isinstance(run_state, dict) and run_state.get("protocol_drift_seen", False):
            items.append(self._protocol_drift_segment(run_state))
        progress_label = self._top_bar_progress_label(state_snapshot)
        if progress_label is not None:
            items.append({"label": progress_label, "accent": COLOR_CYAN, "active": True})
        return items

    def _protocol_drift_segment(self, run_state: dict[str, Any]) -> dict[str, Any]:
        protocol_drift_pct = max(0, min(100, int(run_state.get("protocol_drift_pct", 0) or 0)))
        seen = bool(run_state.get("protocol_drift_seen", False))
        band_label = str(run_state.get("tier_label", run_state.get("band_label", "Stable")))
        band_index = max(0, min(5, int(run_state.get("tier_index", run_state.get("band_index", 0) or 0))))
        next_threshold_pct = run_state.get("next_threshold_pct")
        next_threshold_label = run_state.get("next_threshold_label")
        label = f"Drift {protocol_drift_pct}% {band_label}"
        if next_threshold_pct is not None and next_threshold_label:
            label = f"{label} -> {next_threshold_pct}% {next_threshold_label}"
        return {
            "label": label,
            "accent": self._protocol_drift_accent(band_index),
            "active": seen,
        }

    def _protocol_drift_accent(self, band_index: int) -> tuple[int, int, int]:
        colors = (
            (118, 138, 166),
            (106, 198, 208),
            (110, 182, 244),
            (222, 166, 92),
            (232, 118, 132),
            (255, 82, 112),
        )
        return colors[max(0, min(len(colors) - 1, band_index))]

    def _top_bar_progress_label(self, state_snapshot: dict[str, Any]) -> str | None:
        map_state = state_snapshot.get("map")
        if isinstance(map_state, dict):
            nodes = map_state.get("nodes", {})
            selected_node_id = map_state.get("selected_node_id")
            selected_node = nodes.get(selected_node_id) if isinstance(nodes, dict) and selected_node_id is not None else None
            if selected_node is None:
                return "Entrance"
            if selected_node["node_type"] == "boss":
                return f"Boss F{map_state.get('route_floor_count', 0)}"
            return f"F{selected_node['route_floor']} {selected_node['node_type'].title()}"
        campaign = state_snapshot.get("campaign")
        if isinstance(campaign, dict):
            route_floor_index = campaign.get("route_floor_index")
            map_name = campaign.get("map_name")
            if isinstance(route_floor_index, int) and isinstance(map_name, str):
                return f"F{route_floor_index} {map_name}"
        return None

    def _top_bar_secondary_text(self, state_snapshot: dict[str, Any]) -> str:
        parts: list[str] = []
        if state_snapshot.get("current_state") == "map" and isinstance(state_snapshot.get("map"), dict):
            map_state = state_snapshot["map"]
            route_count = len(map_state.get("available_node_ids", []))
            parts.append(f"{route_count} routes open")
        run_seed = state_snapshot.get("run_seed")
        if run_seed is not None:
            parts.append(f"Seed {run_seed}")
        return "  |  ".join(parts)

    def _combat_top_bar_warnings(self, layout: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        for segment in layout.get("segments", []):
            label = str(segment.get("label", ""))
            sublabel = str(segment.get("sublabel", ""))
            rect = segment.get("rect")
            if not isinstance(rect, tuple) or len(rect) != 4:
                continue
            available = rect[2] - 34
            if self._fit_single_line(label, self._small_font, available) != label:
                warnings.append(f"clipped label {label}")
            if sublabel and self._fit_single_line(sublabel, self._tiny_font, available) != sublabel:
                warnings.append(f"clipped sublabel {sublabel}")
        return warnings

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

    def _handle_top_bar_event(
        self,
        event: Any,
        state_snapshot: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self._top_bar_layout(state_snapshot, surface_size or self._last_surface_size)
        pause_rect = layout["pause_rect"]
        intel_rect = layout.get("intel_rect")
        if event.type == pygame.MOUSEMOTION:
            if intel_rect is not None and point_in_rect(event.pos, intel_rect):
                self._pause_hovered_action = "top_intel"
            elif point_in_rect(event.pos, pause_rect):
                self._pause_hovered_action = "top_pause"
            else:
                self._pause_hovered_action = None
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if intel_rect is not None and point_in_rect(event.pos, intel_rect):
                self._pause_pressed_action = "top_intel"
            elif point_in_rect(event.pos, pause_rect):
                self._pause_pressed_action = "top_pause"
            else:
                self._pause_pressed_action = None
            return None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            action_id = None
            if intel_rect is not None and point_in_rect(event.pos, intel_rect):
                action_id = "top_intel"
            elif point_in_rect(event.pos, pause_rect):
                action_id = "top_pause"
            pressed_action = self._pause_pressed_action
            self._pause_pressed_action = None
            if action_id is not None and action_id == pressed_action:
                if action_id == "top_intel":
                    return {"type": "intel_open"}
                return {"type": "pause_open"}
        return None

    def _modifier_icon_layout(
        self,
        state_snapshot: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]]:
        return self._top_bar_layout(state_snapshot, surface_size or self._last_surface_size)["modifier_icons"]

    def _update_modifier_hover(self, event: Any, state_snapshot: dict[str, Any]) -> None:
        if pygame is None or event.type not in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            return
        if state_snapshot.get("current_state") == "combat":
            self._modifier_hovered_id = None
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
            modifier_type = modifier.get("type", modifier.get("kind", "status"))
            accent = self._modifier_accent(modifier_type, high_contrast)
            fill = (18, 28, 42) if modifier["id"] != self._modifier_hovered_id else (30, 42, 62)
            pygame.draw.rect(surface, fill, rect, border_radius=10)
            pygame.draw.rect(surface, accent if modifier["id"] != self._modifier_hovered_id else (255, 214, 110), rect, 2, border_radius=10)
            if modifier_type == "relic":
                relic_art = relic_assets.get_relic_art(modifier["id"], (rect.width - 6, rect.height - 6))
                if relic_art is not None:
                    surface.blit(relic_art, relic_art.get_rect(center=rect.center))
                else:
                    label = self._tiny_font.render(self._modifier_abbrev(modifier["name"]), True, accent)
                    surface.blit(label, label.get_rect(center=rect.center))
            else:
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

        hovered_type = hovered_modifier.get("type", hovered_modifier.get("kind", "status"))
        relic_thumb = None
        if hovered_type == "relic":
            relic_thumb = relic_assets.get_relic_art(hovered_modifier["id"], (56, 56))

        hovered_rect = pygame.Rect(*hovered_modifier["rect"])
        tooltip_padding = 14
        tooltip_gap = 12
        chip_height = 26
        chip_label = hovered_type.title()
        chip_width = max(70, self._tiny_font.size(chip_label)[0] + 22)
        thumb_size = relic_thumb.get_width() if relic_thumb is not None else 0
        body_width = STATUS_TOOLTIP_WIDTH - (tooltip_padding * 2)
        title_width = body_width - (thumb_size + 12 if relic_thumb is not None else 0)
        title_lines = self._wrap_lines(hovered_modifier["name"], self._small_font, title_width)
        description_lines = self._wrap_lines(hovered_modifier["description"], self._tiny_font, body_width)
        duration_lines = self._wrap_lines(hovered_modifier.get("duration_label"), self._tiny_font, body_width)
        downside_lines = self._wrap_lines(
            f"Tradeoff: {hovered_modifier['downside']}" if hovered_modifier.get("downside") else None,
            self._tiny_font,
            body_width,
        )

        title_height = max(1, len(title_lines)) * self._small_font.get_linesize()
        header_height = title_height + 6 + chip_height
        if relic_thumb is not None:
            header_height = max(header_height, relic_thumb.get_height())

        text_line_height = self._tiny_font.get_linesize()
        body_height = max(1, len(description_lines)) * text_line_height
        if duration_lines:
            body_height += 8 + (len(duration_lines) * text_line_height)
        if downside_lines:
            body_height += 8 + (len(downside_lines) * text_line_height)

        tooltip_height = (tooltip_padding * 2) + header_height + tooltip_gap + body_height
        tooltip_x = hovered_rect.centerx - (STATUS_TOOLTIP_WIDTH // 2)
        tooltip_x = max(24, min(1280 - STATUS_TOOLTIP_WIDTH - 24, tooltip_x))
        tooltip_y = hovered_rect.bottom + 12
        tooltip_y = max(58, min(720 - tooltip_height - 24, tooltip_y))
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, STATUS_TOOLTIP_WIDTH, tooltip_height)
        pygame.draw.rect(surface, (8, 14, 24), tooltip_rect, border_radius=14)
        pygame.draw.rect(surface, (255, 214, 110), tooltip_rect, 2, border_radius=14)
        accent = self._modifier_accent(hovered_type, high_contrast)
        title_x = tooltip_rect.x + 14
        title_y = tooltip_rect.y + tooltip_padding
        if relic_thumb is not None:
            thumb_rect = relic_thumb.get_rect(topleft=(tooltip_rect.x + tooltip_padding, tooltip_rect.y + tooltip_padding))
            surface.blit(relic_thumb, thumb_rect)
            title_x = thumb_rect.right + 12
        self._draw_text(surface, hovered_modifier["name"], (title_x, title_y), self._small_font, width=tooltip_rect.right - title_x - tooltip_padding)
        chip_y = title_y + title_height + 6
        self._draw_chip(surface, chip_label, (title_x, chip_y), chip_width, accent=accent)
        text_y = tooltip_rect.y + tooltip_padding + header_height + tooltip_gap
        self._draw_text(surface, hovered_modifier["description"], (tooltip_rect.x + tooltip_padding, text_y), self._tiny_font, width=body_width)
        text_y += max(1, len(description_lines)) * text_line_height
        if duration_lines:
            text_y += 8
            self._draw_text(surface, hovered_modifier["duration_label"], (tooltip_rect.x + tooltip_padding, text_y), self._tiny_font, width=body_width)
            text_y += len(duration_lines) * text_line_height
        if downside_lines:
            text_y += 8
            self._draw_text(surface, f"Tradeoff: {hovered_modifier['downside']}", (tooltip_rect.x + tooltip_padding, text_y), self._tiny_font, width=body_width)

    def _pause_layout(
        self,
        state_snapshot: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        buttons = [
            {"action": "pause_continue", "label": "Resume", "description": ""},
            {"action": "pause_open_settings", "label": "Settings", "description": ""},
            {"action": "pause_home", "label": "Return to Title", "description": ""},
            {"action": "pause_quit", "label": "Exit Game", "description": ""},
        ]
        overlay = self._overlay_frame(self._resolve_surface_size(surface_size), (420, 284), min_padding=12)
        panel_rect = pygame.Rect(*overlay["panel_rect"])
        padding_x = max(18, int(round(28 * overlay["scale"])))
        title_y = panel_rect.y + max(18, int(round(28 * overlay["scale"])))
        button_height = max(34, int(round(40 * overlay["scale"])))
        button_gap = max(6, int(round(10 * overlay["scale"])))
        button_top = title_y + max(46, int(round(54 * overlay["scale"])))
        button_width = max(220, panel_rect.width - (padding_x * 2))
        for index, button in enumerate(buttons):
            button["rect"] = (
                panel_rect.x + padding_x,
                button_top + (index * (button_height + button_gap)),
                button_width,
                button_height,
            )
        return {
            "panel_rect": tuple(panel_rect),
            "buttons": buttons,
            "title_pos": (panel_rect.x + padding_x, title_y),
            "overlay_scale": overlay["scale"],
            "overlay_font_scale": overlay["font_scale"],
        }

    def _handle_pause_event(
        self,
        event: Any,
        state_snapshot: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self._pause_layout(state_snapshot, surface_size)
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

    def _render_pause_overlay(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        layout = self._pause_layout(state_snapshot, surface.get_size())
        fonts = self._overlay_fonts(
            float(state_snapshot.get("presentation", {}).get("ui_scale", 1.0)),
            layout["overlay_font_scale"],
        )
        draw_modal_scrim(surface, alpha=204)

        panel_rect = pygame.Rect(*layout["panel_rect"])
        draw_panel(surface, panel_rect, accent=COLOR_CYAN, fill=COLOR_PANEL_ELEVATED, radius=RADIUS_LG, border_width=2, shadow_alpha=68)
        self._draw_text(surface, "Paused", layout["title_pos"], fonts["title"])

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
            outline = COLOR_GOLD if selected else COLOR_LINE
            draw_panel(surface, rect, accent=outline, fill=fill, radius=RADIUS_MD, border_width=2 if selected or hovered else 1, shadow_alpha=0)
            label_color = (18, 24, 36) if pressed else (240, 245, 255)
            label_y = rect.y + max(7, (rect.height - fonts["small"].get_linesize()) // 2)
            self._draw_text(surface, button["label"], (rect.x + 16, label_y), fonts["small"], width=rect.width - 32, color=label_color)

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
        layout = self._settings_layout(presentation, surface.get_size())
        fonts = self._overlay_fonts(float(presentation.get("ui_scale", 1.0)), layout["overlay_font_scale"])
        panel_rect = pygame.Rect(*layout["panel_rect"])
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), panel_rect.size)
        surface.blit(panel, panel_rect.topleft)

        self._draw_text(surface, "Settings And Comfort Options", layout["title_pos"], fonts["title"])
        self._draw_text(
            surface,
            "Adjust the game live, or switch to Controls for the full shortcut reference.",
            layout["subtitle_pos"],
            fonts["tiny"],
            width=layout["subtitle_width"],
        )

        for tab in layout["tabs"]:
            self._draw_settings_button(surface, tab["action"], tab["rect"], tab["label"], active=tab["active"], font=fonts["tiny"])

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
                    (help_rect.x + max(10, int(round(14 * layout["overlay_scale"]))), help_rect.y + max(7, int(round(9 * layout["overlay_scale"])))),
                    fonts["tiny"],
                    width=help_rect.width - 36,
                )

            for section in layout["sections"]:
                section_rect = pygame.Rect(*section["rect"])
                pygame.draw.rect(surface, section_fill, section_rect, border_radius=18)
                pygame.draw.rect(surface, section_outline, section_rect, 2, border_radius=18)
                self._draw_text(surface, section["label"], (section_rect.x + max(12, int(round(16 * layout["overlay_scale"]))), section_rect.y + max(8, int(round(12 * layout["overlay_scale"])))), fonts["body"])

                for row in section["rows"]:
                    row_rect = pygame.Rect(*row["row_rect"])
                    selected = row["index"] == self._settings_selected_index
                    outline = row_outline if selected else row_idle_outline
                    pygame.draw.rect(surface, row_fill, row_rect, border_radius=14)
                    pygame.draw.rect(surface, outline, row_rect, 2, border_radius=14)
                    label_width = max(104, row_rect.width - row["control_span"] - max(14, int(round(18 * layout["overlay_scale"]))))
                    label_y = row_rect.y + max(7, (row_rect.height - fonts["small"].get_linesize()) // 2)
                    self._draw_text(surface, row["label"], (row_rect.x + max(10, int(round(14 * layout["overlay_scale"]))), label_y), fonts["small"], width=label_width)

                    if row["kind"] == "toggle":
                        self._draw_settings_button(
                            surface,
                            row["toggle_action"],
                            row["toggle_rect"],
                            row["value_text"],
                            active=row["value"],
                            font=fonts["tiny"],
                        )
                    else:
                        self._draw_settings_button(surface, row["decrease_action"], row["decrease_rect"], "-", active=False, font=fonts["tiny"])
                        value_rect = pygame.Rect(*row["value_rect"])
                        pygame.draw.rect(surface, value_fill, value_rect, border_radius=12)
                        pygame.draw.rect(surface, row_idle_outline, value_rect, 1, border_radius=12)
                        value_surface = fonts["tiny"].render(row["value_text"], True, (240, 245, 255))
                        surface.blit(value_surface, value_surface.get_rect(center=value_rect.center))
                        self._draw_settings_button(surface, row["increase_action"], row["increase_rect"], "+", active=False, font=fonts["tiny"])
        else:
            for section in layout["control_sections"]:
                section_rect = pygame.Rect(*section["rect"])
                pygame.draw.rect(surface, section_fill, section_rect, border_radius=18)
                pygame.draw.rect(surface, section_outline, section_rect, 2, border_radius=18)
                self._draw_text(surface, section["label"], (section_rect.x + max(10, int(round(12 * layout["overlay_scale"]))), section_rect.y + max(8, int(round(10 * layout["overlay_scale"])))), fonts["small"])
                for index, line in enumerate(section["lines"]):
                    line_y = section_rect.y + max(28, int(round(34 * layout["overlay_scale"]))) + (index * max(12, fonts["micro"].get_linesize() - 1))
                    self._draw_text(surface, line, (section_rect.x + max(10, int(round(12 * layout["overlay_scale"]))), line_y), fonts["micro"], width=section_rect.width - max(20, int(round(24 * layout["overlay_scale"]))))

        footer_rect = pygame.Rect(*layout["footer_rect"])
        footer_fill = (8, 14, 22) if high_contrast else (9, 14, 22)
        footer_outline = (184, 198, 224) if high_contrast else (88, 106, 134)
        pygame.draw.rect(surface, footer_fill, footer_rect, border_radius=14)
        pygame.draw.rect(surface, footer_outline, footer_rect, 2, border_radius=14)
        self._draw_text(
            surface,
            layout["footer_hint"],
            layout["footer_hint_pos"],
            fonts["tiny"],
            width=layout["footer_hint_width"],
        )

        for button in layout["footer_buttons"]:
            self._draw_settings_button(surface, button["action"], button["rect"], button["label"], active=button.get("active", False), font=fonts["tiny"])

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

    def _handle_settings_event(
        self,
        event: Any,
        presentation: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self._settings_layout(presentation, surface_size)
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

    def _settings_layout(
        self,
        presentation: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        overlay = self._overlay_frame(
            self._resolve_surface_size(surface_size),
            (SETTINGS_PANEL_WIDTH, SETTINGS_PANEL_HEIGHT),
            min_padding=10,
        )
        panel_rect = pygame.Rect(*overlay["panel_rect"])
        scale = overlay["scale"]
        page = "controls" if presentation.get("settings_page") == "controls" else "general"
        tab_width = max(104, int(round(SETTINGS_TAB_WIDTH * scale * (0.92 if overlay["mode"] == "stacked" else 1.0))))
        tab_height = max(28, int(round(SETTINGS_TAB_HEIGHT * scale)))
        tab_gap = max(10, int(round(12 * scale)))
        tab_x = panel_rect.x + max(18, int(round(28 * scale)))
        tab_y = panel_rect.y + max(76, int(round(96 * scale)))
        tabs = [
            {"action": "tab:general", "label": "General", "rect": (tab_x, tab_y, tab_width, tab_height), "active": page == "general"},
            {"action": "tab:controls", "label": "Controls", "rect": (tab_x + tab_width + tab_gap, tab_y, tab_width, tab_height), "active": page == "controls"},
        ]
        if page == "controls":
            return self._responsive_settings_controls_layout(overlay, tabs)
        return self._responsive_settings_general_layout(presentation, overlay, tabs)

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

    def _responsive_settings_general_layout(
        self,
        presentation: dict[str, Any],
        overlay: dict[str, Any],
        tabs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        panel_rect = pygame.Rect(*overlay["panel_rect"])
        scale = overlay["scale"]
        mode = overlay["mode"]
        content_pad_x = max(18, int(round(28 * scale)))
        footer_height = max(36, int(round(46 * scale)))
        footer_rect = (
            panel_rect.x + content_pad_x,
            panel_rect.bottom - max(14, int(round(18 * scale))) - footer_height,
            panel_rect.width - (content_pad_x * 2),
            footer_height,
        )
        help_height = max(26 if mode == "stacked" else 28, int(round((30 if mode == "stacked" else 42) * scale)))
        help_rect = (
            panel_rect.x + content_pad_x,
            panel_rect.y + (max(104, int(round(124 * scale))) if mode == "stacked" else max(112, int(round(142 * scale)))),
            panel_rect.width - (content_pad_x * 2),
            help_height,
        )
        section_top = help_rect[1] + help_rect[3] + (max(6, int(round(10 * scale))) if mode == "stacked" else max(8, int(round(14 * scale))))
        section_gap = max(10, int(round((12 if mode == "stacked" else 20) * scale)))
        row_height = max(22 if mode == "stacked" else 32, int(round((26 if mode == "stacked" else 46) * scale)))
        row_gap = max(2 if mode == "stacked" else 5, int(round((3 if mode == "stacked" else 8) * scale)))
        section_header_height = max(22, int(round(28 * scale)))
        section_inner_pad = max(8 if mode == "stacked" else 10, int(round((10 if mode == "stacked" else 14) * scale)))
        two_column = mode != "stacked"
        section_width = panel_rect.width - (content_pad_x * 2)
        if two_column:
            section_width = (panel_rect.width - (content_pad_x * 2) - section_gap) // 2

        section_specs = {
            "display": {"label": "Display & Motion", "rect": (panel_rect.x + content_pad_x, section_top, section_width, 0), "rows": []},
            "audio": {"label": "Audio & Accessibility", "rect": (panel_rect.x + content_pad_x + (section_width + section_gap if two_column else 0), section_top, section_width, 0), "rows": []},
        }
        settings_rows = self._settings_rows(presentation)
        display_rows = [row for row in settings_rows if row["group"] == "display"]
        audio_rows = [row for row in settings_rows if row["group"] == "audio"]
        if two_column:
            section_height = footer_rect[1] - section_top - max(10, int(round(14 * scale)))
            section_specs["display"]["rect"] = (panel_rect.x + content_pad_x, section_top, section_width, section_height)
            section_specs["audio"]["rect"] = (panel_rect.x + content_pad_x + section_width + section_gap, section_top, section_width, section_height)
        else:
            display_height = (section_inner_pad * 2) + section_header_height + (len(display_rows) * row_height) + (max(0, len(display_rows) - 1) * row_gap)
            audio_height = (section_inner_pad * 2) + section_header_height + (len(audio_rows) * row_height) + (max(0, len(audio_rows) - 1) * row_gap)
            section_specs["display"]["rect"] = (panel_rect.x + content_pad_x, section_top, section_width, display_height)
            section_specs["audio"]["rect"] = (panel_rect.x + content_pad_x, section_top + display_height + section_gap, section_width, audio_height)

        rows = []
        for index, row in enumerate(settings_rows):
            section = section_specs[row["group"]]
            row_index = len(section["rows"])
            section_x, section_y, section_w, _ = section["rect"]
            row_x = section_x + section_inner_pad
            row_y = section_y + section_inner_pad + section_header_height + (row_index * (row_height + row_gap))
            row_w = section_w - (section_inner_pad * 2)
            row_rect = (row_x, row_y, row_w, row_height)
            entry = {**row, "index": index, "row_rect": row_rect}
            if row["kind"] == "toggle":
                toggle_w = max(112, int(round((136 if mode == "stacked" else 148) * scale)))
                toggle_h = max(24, int(round(32 * scale)))
                toggle_y = row_y + max(2, (row_height - toggle_h) // 2)
                entry["toggle_rect"] = (row_x + row_w - toggle_w, toggle_y, toggle_w, toggle_h)
                entry["toggle_action"] = f"toggle:{row['id']}"
                entry["control_span"] = toggle_w
            else:
                step_size = max(24, int(round(30 * scale)))
                value_w = max(52, int(round((64 if mode == "stacked" else 72) * scale)))
                step_gap = max(5, int(round(8 * scale)))
                control_y = row_y + max(2, (row_height - step_size) // 2)
                plus_x = row_x + row_w - step_size
                value_x = plus_x - step_gap - value_w
                minus_x = value_x - step_gap - step_size
                entry["decrease_rect"] = (minus_x, control_y, step_size, step_size)
                entry["value_rect"] = (value_x, control_y, value_w, step_size)
                entry["increase_rect"] = (plus_x, control_y, step_size, step_size)
                entry["decrease_action"] = f"decrease:{row['id']}"
                entry["increase_action"] = f"increase:{row['id']}"
                entry["control_span"] = row_x + row_w - minus_x
            rows.append(entry)
            section["rows"].append(entry)

        button_height = max(30, int(round(38 * scale)))
        reset_width = max(124, int(round((150 if mode == "stacked" else 180) * scale)))
        close_width = max(104, int(round(146 * scale)))
        footer_buttons = [
            {"action": "reset", "label": "Reset Defaults", "rect": (footer_rect[0] + max(8, int(round(10 * scale))), footer_rect[1] + max(3, int(round(4 * scale))), reset_width, button_height)},
            {"action": "close", "label": "Close", "rect": (footer_rect[0] + footer_rect[2] - close_width - max(8, int(round(10 * scale))), footer_rect[1] + max(3, int(round(4 * scale))), close_width, button_height), "active": True},
        ]
        hint_x = footer_buttons[0]["rect"][0] + footer_buttons[0]["rect"][2] + max(10, int(round(18 * scale)))
        hint_right = footer_buttons[-1]["rect"][0] - max(10, int(round(18 * scale)))
        return {
            "page": "general",
            "panel_rect": tuple(panel_rect),
            "tabs": tabs,
            "rows": rows,
            "sections": [section_specs["display"], section_specs["audio"]],
            "help_rect": help_rect,
            "footer_rect": footer_rect,
            "footer_buttons": footer_buttons,
            "footer_hint": "Esc closes • Tab switches page",
            "footer_hint_pos": (hint_x, footer_rect[1] + max(8, int(round(10 * scale)))),
            "footer_hint_width": max(96, hint_right - hint_x),
            "control_sections": [],
            "overlay_scale": scale,
            "overlay_font_scale": overlay["font_scale"],
            "title_pos": (panel_rect.x + max(22, int(round(34 * scale))), panel_rect.y + max(16, int(round(22 * scale)))),
            "subtitle_pos": (panel_rect.x + max(22, int(round(34 * scale))), panel_rect.y + max(48, int(round(60 * scale)))),
            "subtitle_width": panel_rect.width - max(44, int(round(68 * scale))),
        }

    def _responsive_settings_controls_layout(
        self,
        overlay: dict[str, Any],
        tabs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        panel_rect = pygame.Rect(*overlay["panel_rect"])
        scale = overlay["scale"]
        mode = overlay["mode"]
        base_x = panel_rect.x + max(18, int(round(28 * scale)))
        footer_height = max(36, int(round(46 * scale)))
        footer_rect = (
            base_x,
            panel_rect.bottom - max(14, int(round(18 * scale))) - footer_height,
            panel_rect.width - (max(18, int(round(28 * scale))) * 2),
            footer_height,
        )
        section_gap = max(8, int(round((10 if mode == "stacked" else 14) * scale)))
        columns = 3 if mode == "desktop" else 2
        section_width = (footer_rect[2] - (section_gap * (columns - 1))) // columns
        section_top = panel_rect.y + max(112, int(round(146 * scale)))
        row_gap = max(8, int(round(10 * scale)))
        sections = self._controls_sections()
        rows = max(1, (len(sections) + columns - 1) // columns)
        available_height = footer_rect[1] - section_top - max(10, int(round(14 * scale)))
        section_height = max(76, int((available_height - (row_gap * (rows - 1))) / rows))
        control_sections = []
        for index, section in enumerate(sections):
            column = index % columns
            row = index // columns
            rect = (
                base_x + (column * (section_width + section_gap)),
                section_top + (row * (section_height + row_gap)),
                section_width,
                section_height,
            )
            control_sections.append({**section, "rect": rect})

        button_height = max(30, int(round(38 * scale)))
        close_width = max(104, int(round(146 * scale)))
        footer_buttons = [
            {"action": "close", "label": "Close", "rect": (footer_rect[0] + footer_rect[2] - close_width - max(8, int(round(10 * scale))), footer_rect[1] + max(3, int(round(4 * scale))), close_width, button_height), "active": True},
        ]
        return {
            "page": "controls",
            "panel_rect": tuple(panel_rect),
            "tabs": tabs,
            "rows": [],
            "sections": [],
            "help_rect": None,
            "footer_rect": footer_rect,
            "footer_buttons": footer_buttons,
            "footer_hint": "Esc closes • Tab switches page",
            "footer_hint_pos": (footer_rect[0] + max(12, int(round(18 * scale))), footer_rect[1] + max(8, int(round(10 * scale)))),
            "footer_hint_width": max(120, footer_rect[2] - close_width - max(36, int(round(48 * scale)))),
            "control_sections": control_sections,
            "overlay_scale": scale,
            "overlay_font_scale": overlay["font_scale"],
            "title_pos": (panel_rect.x + max(22, int(round(34 * scale))), panel_rect.y + max(16, int(round(22 * scale)))),
            "subtitle_pos": (panel_rect.x + max(22, int(round(34 * scale))), panel_rect.y + max(48, int(round(60 * scale)))),
            "subtitle_width": panel_rect.width - max(44, int(round(68 * scale))),
        }

    def _settings_rows(self, presentation: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"id": "fullscreen", "group": "display", "label": "Display Mode", "description": "Toggle fullscreen or a resizable window.", "kind": "toggle", "value": presentation.get("fullscreen", True), "value_text": "Fullscreen" if presentation.get("fullscreen", True) else "Windowed"},
            {"id": "fast_mode", "group": "display", "label": "Fast Mode", "description": "Shorten non-critical feedback and transitions.", "kind": "toggle", "value": presentation.get("fast_mode", False), "value_text": "Enabled" if presentation.get("fast_mode", False) else "Disabled"},
            {"id": "presentation_scale", "group": "display", "label": "Display Scale", "description": "Apply an optional post-layout zoom after the interface fits the current window.", "kind": "step", "value": presentation.get("presentation_scale", 1.0), "value_text": f"{int(presentation.get('presentation_scale', 1.0) * 100)}%"},
            {"id": "ui_scale", "group": "display", "label": "UI Text Scale", "description": "Scale text and labels while keeping responsive layouts aligned to the active font size.", "kind": "step", "value": presentation.get("ui_scale", 1.0), "value_text": f"{int(presentation.get('ui_scale', 1.0) * 100)}%"},
            {"id": "screen_shake", "group": "display", "label": "Screen Shake", "description": "Toggle impact shake on heavy feedback moments.", "kind": "toggle", "value": presentation.get("screen_shake", True), "value_text": "Enabled" if presentation.get("screen_shake", True) else "Disabled"},
            {"id": "combat_layout_debug", "group": "display", "label": "Combat Layout Debug", "description": "Show reserved combat screen regions for layout tuning.", "kind": "toggle", "value": presentation.get("combat_layout_debug", False), "value_text": "Enabled" if presentation.get("combat_layout_debug", False) else "Disabled"},
            {"id": "master_volume", "group": "audio", "label": "SFX Volume", "description": "Adjust sound effect volume for combat and UI cues.", "kind": "step", "value": presentation.get("master_volume", 0.8), "value_text": f"{int(presentation.get('master_volume', 0.8) * 100)}%"},
            {"id": "music_volume", "group": "audio", "label": "Music Volume", "description": "Adjust background music volume for title, map, events, and combat.", "kind": "step", "value": presentation.get("music_volume", 0.5), "value_text": f"{int(presentation.get('music_volume', 0.5) * 100)}%"},
            {"id": "muted", "group": "audio", "label": "Mute Audio", "description": "Silence all current and future audio output.", "kind": "toggle", "value": presentation.get("muted", False), "value_text": "Muted" if presentation.get("muted", False) else "Live"},
            {"id": "high_contrast", "group": "display", "label": "High Contrast", "description": "Boost contrast and reduce reliance on subtle color differences.", "kind": "toggle", "value": presentation.get("high_contrast", False), "value_text": "Enabled" if presentation.get("high_contrast", False) else "Disabled"},
        ]

    def _apply_purge_feedback(
        self,
        action_type: str,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> None:
        if pygame is None:
            return
        feedback = None
        if action_type == "confirm_shop_purchase":
            feedback = self._shop_purge_feedback(before_snapshot, after_snapshot)
        elif action_type == "confirm_reward_selection":
            feedback = self._reward_purge_feedback(before_snapshot, after_snapshot)
        elif action_type == "confirm_event_choice":
            feedback = self._event_purge_feedback(before_snapshot, after_snapshot)
        if feedback is None:
            return
        self._purge_feedback = {
            "card": feedback["card"],
            "rect": tuple(feedback["rect"]),
            "elapsed": 0.0,
            "duration": 0.72,
        }
        self._emit_audio_cue("card_purged_burn")

    def _shop_purge_feedback(
        self,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> dict[str, Any] | None:
        before_shop_state = before_snapshot.get("shop")
        after_shop_state = after_snapshot.get("shop")
        if not isinstance(before_shop_state, dict) or not isinstance(after_shop_state, dict):
            return None
        if before_shop_state.get("selected_offer_id") != SHOP_PURGE_OFFER_ID:
            return None
        selected_purge_index = before_shop_state.get("selected_purge_index")
        if not isinstance(selected_purge_index, int):
            return None
        before_targets = list(before_shop_state.get("purge_targets") or [])
        after_targets = list(after_shop_state.get("purge_targets") or [])
        if len(after_targets) >= len(before_targets):
            return None
        layout = self.shop_ui.build_layout(self._shop_view_state(before_snapshot), self._last_surface_size)
        entry = next((candidate for candidate in layout.get("purge_entries", []) if candidate.get("deck_index") == selected_purge_index), None)
        if entry is None:
            return None
        return {"card": entry["card"], "rect": entry["rect"]}

    def _reward_purge_feedback(
        self,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> dict[str, Any] | None:
        before_reward = before_snapshot.get("reward")
        after_reward = after_snapshot.get("reward")
        if not isinstance(before_reward, dict) or not isinstance(after_reward, dict):
            return None
        if int(after_reward.get("deck_size", 0)) >= int(before_reward.get("deck_size", 0)):
            return None
        layout = self.reward_ui.build_layout(self._reward_view_state(before_snapshot), self._last_surface_size)
        active_section = layout.get("active_section")
        if not isinstance(active_section, dict) or active_section.get("type") != "purge_offer":
            return None
        selected_option_id = active_section.get("selected_option_id")
        if not isinstance(selected_option_id, str):
            return None
        entry = next((candidate for candidate in layout.get("option_entries", []) if candidate.get("option_id") == selected_option_id), None)
        if entry is None:
            return None
        return {"card": entry["card"], "rect": entry["rect"]}

    def _event_purge_feedback(
        self,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> dict[str, Any] | None:
        before_event = before_snapshot.get("event")
        after_event = after_snapshot.get("event")
        if not isinstance(before_event, dict) or not isinstance(after_event, dict):
            return None
        if before_event.get("selected_choice_type") != "purge":
            return None
        selected_target_id = before_event.get("selected_target_id")
        if not isinstance(selected_target_id, str):
            return None
        if int(after_event.get("deck_size", 0)) >= int(before_event.get("deck_size", 0)):
            return None
        layout = self.event_ui.build_layout(self._event_view_state(before_snapshot), self._last_surface_size)
        entry = next((candidate for candidate in layout.get("purge_targets", []) if candidate.get("option_id") == selected_target_id), None)
        if entry is None:
            return None
        return {"card": entry["card"], "rect": entry["rect"]}

    def _render_purge_feedback(self, surface: Any) -> None:
        if pygame is None or surface is None or self._purge_feedback is None:
            return
        rect = pygame.Rect(*self._purge_feedback["rect"])
        if rect.width <= 0 or rect.height <= 0:
            return
        progress = min(1.0, self._purge_feedback["elapsed"] / max(0.01, self._purge_feedback["duration"]))
        scale = max(0.72, 1.0 - (progress * 0.18))
        width = max(48, int(round(rect.width * scale)))
        height = max(40, int(round(rect.height * scale)))
        render_rect = pygame.Rect(
            rect.centerx - (width // 2),
            rect.centery - (height // 2) - int(round(progress * 18)),
            width,
            height,
        )
        card_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        fonts = {
            "title": self._small_font or self._tiny_font,
            "body": self._tiny_font or self._small_font,
            "tiny": self._micro_font or self._tiny_font or self._small_font,
        }
        draw_card(
            card_surface,
            (0, 0, width, height),
            self._purge_feedback["card"],
            fonts,
            variant="mini",
        )
        burned_height = min(height, int(round(height * min(1.0, progress * 1.08))))
        if burned_height > 0:
            burn_top = max(0, height - burned_height)
            card_surface.fill((0, 0, 0, 0), pygame.Rect(0, burn_top, width, burned_height))
            ember_surface = pygame.Surface((width, max(18, height // 4)), pygame.SRCALPHA)
            ember_alpha = max(0, int(round((1.0 - progress) * 180)))
            for index in range(6):
                ember_rect = pygame.Rect(
                    max(0, int((width * (index / 6.0)) - 8)),
                    0 if index % 2 == 0 else 4,
                    max(10, width // 8),
                    10 + (index % 3) * 4,
                )
                color = (255, 164 - (index * 14), 84, ember_alpha)
                pygame.draw.ellipse(ember_surface, color, ember_rect)
            card_surface.blit(ember_surface, (0, max(0, burn_top - 10)))
        card_surface.set_alpha(max(0, int(round((1.0 - progress) * 255))))
        surface.blit(card_surface, render_rect.topleft)

    def _emit_audio_cue(self, cue_id: str) -> None:
        if self._audio_callback is None:
            return
        self._audio_callback(cue_id)

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

    def _draw_settings_button(
        self,
        surface: Any,
        action_id: str,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        active: bool,
        font: Any | None = None,
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
        button_font = font or self._tiny_font
        label_surface = button_font.render(label, True, text_color)
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
        color: tuple[int, int, int] = (232, 240, 255),
        width: int | None = None,
    ) -> None:
        draw_wrapped_text(surface, text, position, font, color=color, width=width)

    def _fit_single_line(self, text: str, font: Any, width: int) -> str:
        if not text or font.size(text.upper())[0] <= width:
            return text
        clipped = text
        while len(clipped) > 3 and font.size(f"{clipped.upper()}...")[0] > width:
            clipped = clipped[:-1].rstrip()
        return f"{clipped}..." if clipped else text[:1]

    def _resolve_surface_size(self, surface_size: tuple[int, int] | None) -> tuple[int, int]:
        if surface_size is None:
            return self._last_surface_size
        width = max(640, int(surface_size[0]))
        height = max(360, int(surface_size[1]))
        self._last_surface_size = (width, height)
        return self._last_surface_size

    def _wrap_lines(self, text: str | None, font: Any, width: int) -> list[str]:
        if text is None:
            return []
        words = str(text).split()
        if not words:
            return []
        lines: list[str] = []
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if font.size(candidate)[0] <= width:
                line = candidate
                continue
            if not line:
                lines.append(word)
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _overlay_frame(
        self,
        surface_size: tuple[int, int],
        design_size: tuple[int, int],
        *,
        min_padding: int,
    ) -> dict[str, Any]:
        surface_width, surface_height = surface_size
        design_width, design_height = design_size
        outer_padding = max(8, min_padding)
        available_width = max(1, surface_width - (outer_padding * 2))
        available_height = max(1, surface_height - (outer_padding * 2))
        scale = min(1.0, available_width / design_width, available_height / design_height)
        panel_width = max(240, int(round(design_width * scale)))
        panel_height = max(180, int(round(design_height * scale)))
        panel_rect = (
            max(0, (surface_width - panel_width) // 2),
            max(0, (surface_height - panel_height) // 2),
            panel_width,
            panel_height,
        )
        mode = "desktop"
        if surface_width < 1120 or surface_height < 640 or scale < 0.95:
            mode = "compact"
        if surface_width <= 1000 or surface_height <= 560 or scale < 0.88:
            mode = "stacked"
        font_scale = 1.0 if mode == "desktop" else max(0.72, min(0.98, scale * (0.97 if mode == "compact" else 0.92)))
        return {
            "panel_rect": panel_rect,
            "scale": scale,
            "font_scale": font_scale,
            "mode": mode,
        }

    def _overlay_fonts(self, base_ui_scale: float, responsive_scale: float) -> dict[str, Any]:
        return self._font_pack(base_ui_scale * responsive_scale, minimum_scale=0.72)

    def _font_pack(self, scale: float, *, minimum_scale: float = MIN_UI_SCALE) -> dict[str, Any]:
        scale = clamp_scale(scale, minimum_scale, MAX_UI_SCALE)
        cache_key = (round(scale, 4), round(minimum_scale, 4))
        if cache_key in self._font_pack_cache:
            return self._font_pack_cache[cache_key]
        minimum_title = 24 if minimum_scale < MIN_UI_SCALE else 30
        minimum_body = 18 if minimum_scale < MIN_UI_SCALE else 22
        minimum_small = 14 if minimum_scale < MIN_UI_SCALE else 16
        minimum_tiny = 11 if minimum_scale < MIN_UI_SCALE else 12
        pack = {
            "title": pygame.font.SysFont("consolas", max(minimum_title, int(38 * scale))),
            "body": pygame.font.SysFont("consolas", max(minimum_body, int(28 * scale))),
            "small": pygame.font.SysFont("consolas", max(minimum_small, int(20 * scale))),
            "tiny": pygame.font.SysFont("consolas", max(minimum_tiny, int(16 * scale))),
            "micro": pygame.font.SysFont("consolas", max(10, int(13 * scale))),
        }
        self._font_pack_cache[cache_key] = pack
        return pack

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._title_font is not None:
            return

        self._font_scale = scale
        pack = self._font_pack(scale, minimum_scale=MIN_UI_SCALE)
        self._title_font = pack["title"]
        self._font = pack["body"]
        self._small_font = pack["small"]
        self._tiny_font = pack["tiny"]
        self._micro_font = pack["micro"]

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
                "music_volume": 0.5,
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
                "music_volume": 0.5,
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
