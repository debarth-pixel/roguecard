from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from animation.animator import Animator
from audio.audio_manager import AudioManager, CHOSEN_AUDIO_CUES, DEFAULT_AUDIO_CUES
from config import (
    ACTION_COOLDOWN_SECONDS,
    DEFAULT_FAST_MODE,
    DEFAULT_FULLSCREEN,
    DEFAULT_HIGH_CONTRAST,
    DEFAULT_MASTER_VOLUME,
    DEFAULT_MUSIC_VOLUME,
    DEFAULT_PRESENTATION_SCALE,
    DEFAULT_SCREEN_SHAKE,
    DEFAULT_UI_SCALE,
    FAST_MODE_MULTIPLIER,
    FRAME_RATE,
    MAX_PRESENTATION_SCALE,
    MAX_UI_SCALE,
    MIN_SUPPORTED_HEIGHT,
    MIN_SUPPORTED_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_PRESENTATION_SCALE,
    MIN_UI_SCALE,
    NOTICE_DURATION_SECONDS,
    PRESENTATION_SCALE_STEP,
    RUN_SAVE_DATA_PATH,
    SCREEN_SIZE,
    SETTINGS_DATA_PATH,
    SETTINGS_FORMAT_VERSION,
    UI_SCALE_STEP,
    VOLUME_STEP,
)
from core.state_manager import StateManager
from ui.ui_manager import UIManager

LOGGER = logging.getLogger(__name__)


class GameLoop:
    def __init__(
        self,
        state_manager: StateManager | None = None,
        ui_manager: UIManager | None = None,
        animator: Animator | None = None,
        audio_manager: AudioManager | None = None,
    ) -> None:
        self.state_manager = state_manager or StateManager()
        self.ui_manager = ui_manager or UIManager()
        self.animator = animator or Animator()
        self.audio_manager = audio_manager or AudioManager()
        self.running = False
        self._logical_surface = None
        self._fullscreen = DEFAULT_FULLSCREEN
        self._fast_mode = DEFAULT_FAST_MODE
        self._pause_open = False
        self._intel_open = False
        self._intel_selected_faction: str | None = None
        self._settings_open = False
        self._settings_page = "general"
        self._intel_return_to_pause = False
        self._settings_return_to_pause = False
        self._presentation_scale = DEFAULT_PRESENTATION_SCALE
        self._ui_scale = DEFAULT_UI_SCALE
        self._screen_shake = DEFAULT_SCREEN_SHAKE
        self._high_contrast = DEFAULT_HIGH_CONTRAST
        self._notice: dict[str, Any] | None = None
        self._notice_timer = 0.0
        self._interaction_cooldown = 0.0
        self._title_active = True
        self._title_confirm_new_run = False
        self._title_continue_payload: dict[str, Any] | None = None
        self._title_continue_summary: dict[str, Any] | None = None
        self._title_status_message = "Choose how to enter the city."
        self._last_music_scene: str | None = None

    def run(self) -> None:
        if pygame is None:
            raise RuntimeError("Pygame is required to run the game loop.")

        pygame.init()
        self._load_settings()
        self._initialize_audio()
        screen = self._create_display_surface()
        pygame.display.set_caption("Rogue Card")
        clock = pygame.time.Clock()

        self._preload_presentation_assets()
        boot_message, boot_level = self._bootstrap_run_state()
        self._sync_music_scene(self._snapshot_with_hand(), force=True)
        self._set_notice(boot_message, level=boot_level, duration=3.2)
        self.running = True

        while self.running:
            delta_time = clock.tick(FRAME_RATE) / 1000.0
            self._advance_notice(delta_time)
            self._advance_interaction_cooldown(delta_time)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                screen, consumed = self._handle_global_event(event, screen)
                if consumed:
                    continue

                current_snapshot = self._snapshot_with_hand()
                self._sync_logical_surface(current_snapshot, screen.get_size())
                translated_event = self._translate_event(event, screen)
                if translated_event is None:
                    continue

                action = self.ui_manager.handle_event(
                    translated_event,
                    current_snapshot,
                    surface_size=self._logical_surface.get_size(),
                )
                if action is not None:
                    screen = self._dispatch_action(action, screen)

            current_snapshot = self._snapshot_with_hand()
            self._sync_logical_surface(current_snapshot, screen.get_size())
            polled_action = self.ui_manager.poll_action(current_snapshot)
            if polled_action is not None:
                screen = self._dispatch_action(polled_action, screen)

            animation_speed = FAST_MODE_MULTIPLIER if self._fast_mode else 1.0
            self.audio_manager.update(delta_time)
            self.animator.update(delta_time * animation_speed)
            self.ui_manager.update(delta_time * animation_speed, self._snapshot_with_hand())
            self._render_frame(screen)
            pygame.display.flip()

        pygame.quit()

    def _dispatch_action(self, action: dict[str, Any], screen: Any) -> Any:
        if not isinstance(action, dict) or "type" not in action:
            self._trigger_denial_feedback("Received an invalid UI action payload.")
            return screen

        action_type = action["type"]

        if action_type == "notice":
            message = action.get("message", "Action unavailable.")
            level = action.get("level", "info")
            self._set_notice(message, level=level)
            if level == "error":
                self._trigger_denial_feedback(message)
            return screen

        if action_type in {
            "toggle_settings",
            "close_settings",
            "set_setting",
            "reset_settings",
            "open_general_settings_page",
            "open_controls_page",
        }:
            return self._handle_settings_action(action, screen)
        if action_type in {
            "pause_open",
            "pause_continue",
            "pause_open_intel",
            "pause_open_settings",
            "pause_home",
            "pause_quit",
        }:
            return self._handle_pause_action(action, screen)
        if action_type in {"intel_open", "intel_close", "intel_select_faction"}:
            return self._handle_intel_action(action, screen)

        if self._action_uses_cooldown(action_type) and self._interaction_cooldown > 0:
            return screen

        before_snapshot = self._snapshot_with_hand()

        try:
            if action_type == "title_new_run":
                if self._title_continue_payload is not None and not self._title_confirm_new_run:
                    self._title_confirm_new_run = True
                    self._title_status_message = "Overwrite the current resumable run?"
                else:
                    self._begin_new_run()
            elif action_type == "title_confirm_new_run":
                self._begin_new_run()
            elif action_type == "title_cancel_new_run":
                self._title_confirm_new_run = False
                self._title_status_message = "Choose how to enter the city."
            elif action_type == "title_continue":
                self._continue_saved_run()
            elif action_type == "title_quit":
                self.running = False
            elif action_type == "new_run":
                self._begin_new_run()
            elif action_type == "select_character":
                self.state_manager.select_character(action["character_id"])
            elif action_type == "confirm_character_selection":
                self.state_manager.confirm_character_selection()
            elif action_type == "select_run_modifier_offer":
                self.state_manager.select_run_modifier_offer(action["modifier_id"])
            elif action_type == "confirm_run_modifier_selection":
                self.state_manager.confirm_run_modifier_selection()
            elif action_type == "select_node":
                self.state_manager.select_map_node(action["node_id"])
            elif action_type == "play_card":
                self.state_manager.play_card_from_hand(action["hand_index"], action.get("target_id"))
            elif action_type == "end_turn":
                self.state_manager.end_combat_turn()
            elif action_type == "resolve_enemy_phase_step":
                self.state_manager.resolve_enemy_phase_step()
            elif action_type == "select_reward_option":
                self.state_manager.select_reward_option(action["section"], action["option_id"])
            elif action_type == "confirm_reward_selection":
                self.state_manager.confirm_reward_selection(action["section"])
            elif action_type == "skip_reward_section":
                self.state_manager.skip_reward_section(action["section"])
            elif action_type == "continue_from_reward":
                self.state_manager.continue_from_reward()
            elif action_type == "select_shop_offer":
                self.state_manager.select_shop_offer(action["offer_id"])
            elif action_type == "open_shop_menu":
                self.state_manager.open_shop_menu(action["menu_id"])
            elif action_type == "clear_shop_selection":
                self.state_manager.clear_shop_selection()
            elif action_type == "purchase_shop_offer":
                self.state_manager.purchase_shop_offer(action["offer_id"])
            elif action_type == "confirm_shop_purchase":
                self.state_manager.confirm_shop_purchase()
            elif action_type == "confirm_shop_cleanse":
                self.state_manager.confirm_shop_cleanse()
            elif action_type == "reroll_shop_inventory":
                self.state_manager.reroll_shop_inventory()
            elif action_type == "leave_shop":
                self.state_manager.leave_shop()
            elif action_type == "select_event_choice":
                self.state_manager.select_event_choice(action["choice_id"])
            elif action_type == "select_event_target":
                self.state_manager.select_event_target(action["target_id"])
            elif action_type == "confirm_event_choice":
                self.state_manager.confirm_event_choice()
            elif action_type == "continue_from_event":
                self.state_manager.continue_from_event()
            else:
                raise ValueError(f"Unsupported UI action: {action_type}")
        except (IndexError, ValueError, KeyError) as exc:
            LOGGER.warning("Action rejected: %s", exc)
            self._trigger_denial_feedback(str(exc))
            self.ui_manager.handle_action_denied(action_type, before_snapshot)
            return screen
        except Exception:  # pragma: no cover - defensive runtime guard.
            LOGGER.exception("Unexpected error while dispatching action %s", action_type)
            self._trigger_denial_feedback("An unexpected error interrupted that action.")
            self.ui_manager.handle_action_denied(action_type, before_snapshot)
            return screen

        after_snapshot = self._snapshot_with_hand()
        if action_type != "title_quit":
            self._apply_feedback(action_type, before_snapshot, after_snapshot)
            self.ui_manager.apply_snapshot_feedback(action_type, before_snapshot, after_snapshot)
            self._sync_music_scene(
                after_snapshot,
                before_snapshot=before_snapshot,
                action_type=action_type,
            )
        self._persist_run_state(after_snapshot)
        if self._action_uses_cooldown(action_type):
            self._interaction_cooldown = ACTION_COOLDOWN_SECONDS
        return screen

    def _handle_settings_action(self, action: dict[str, Any], screen: Any) -> Any:
        action_type = action["type"]

        if action_type == "toggle_settings":
            self._toggle_settings(
                page=action.get("page"),
                from_pause=action.get("from_pause"),
            )
            return screen

        if action_type == "close_settings":
            self._toggle_settings(False)
            return screen

        if action_type == "open_general_settings_page":
            self._settings_page = "general"
            return screen

        if action_type == "open_controls_page":
            self._settings_page = "controls"
            return screen

        if action_type == "reset_settings":
            screen = self._apply_runtime_settings(self._default_settings(), screen)
            self._persist_settings()
            self.animator.trigger("settings")
            self.audio_manager.trigger("menu_open")
            self._set_notice("Settings reset to defaults.", level="success", duration=1.8)
            return screen

        if action_type == "set_setting":
            setting_name = action.get("setting")
            if not isinstance(setting_name, str):
                self._trigger_denial_feedback("Settings action is missing a valid setting name.")
                return screen
            screen = self._apply_setting_change(setting_name, action.get("value"), screen)
            return screen

        self._trigger_denial_feedback(f"Unsupported settings action: {action_type}")
        return screen

    def _handle_pause_action(self, action: dict[str, Any], screen: Any) -> Any:
        action_type = action["type"]

        if action_type == "pause_open":
            if not self._title_active:
                self._pause_open = True
                self.animator.trigger("select")
                self.audio_manager.trigger("menu_open")
                self._set_notice("Paused.", duration=1.2)
            return screen

        if action_type == "pause_continue":
            self._pause_open = False
            self._set_notice("Resumed.", duration=1.2)
            return screen

        if action_type == "pause_open_intel":
            return self._open_intel(screen, from_pause=True)

        if action_type == "pause_open_settings":
            self._toggle_settings(True, page="general", from_pause=True)
            return screen

        if action_type == "pause_home":
            if not self._title_active:
                self._persist_run_state(self.state_manager.get_state_snapshot())
            self._pause_open = False
            self._toggle_settings(False)
            self._bootstrap_run_state()
            self._sync_music_scene(self._snapshot_with_hand(), force=True)
            self._set_notice("Returned to the title screen. Continue is available.", level="success", duration=2.0)
            return screen

        if action_type == "pause_quit":
            self.running = False
            return screen

        self._trigger_denial_feedback(f"Unsupported pause action: {action_type}")
        return screen

    def _handle_intel_action(self, action: dict[str, Any], screen: Any) -> Any:
        action_type = action["type"]

        if action_type == "intel_open":
            return self._open_intel(screen, from_pause=self._pause_open)

        if action_type == "intel_close":
            self._intel_open = False
            return_to_pause = self._intel_return_to_pause
            self._intel_return_to_pause = False
            self._pause_open = return_to_pause
            return screen

        if action_type == "intel_select_faction":
            faction_id = action.get("faction_id")
            if not isinstance(faction_id, str) or not faction_id:
                self._trigger_denial_feedback("Intel selection is missing a faction id.")
                return screen
            self._intel_selected_faction = faction_id
            return screen

        self._trigger_denial_feedback(f"Unsupported intel action: {action_type}")
        return screen

    def _open_intel(self, screen: Any, *, from_pause: bool) -> Any:
        intel_state = self._snapshot_with_hand().get("grayspine_intel")
        if not isinstance(intel_state, dict):
            self._set_notice("Grayspine intel unlocks in the final map.", duration=1.8)
            return screen
        self._intel_open = True
        self._intel_return_to_pause = bool(from_pause)
        self._pause_open = False
        if self._intel_selected_faction is None:
            selected_faction_id = intel_state.get("selected_faction_id")
            if isinstance(selected_faction_id, str) and selected_faction_id:
                self._intel_selected_faction = selected_faction_id
        self.animator.trigger("select")
        self.audio_manager.trigger("menu_open")
        return screen

    def _apply_feedback(
        self,
        action_type: str,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> None:
        if action_type == "title_new_run":
            if after_snapshot["current_state"] == "title":
                self.animator.trigger("select")
                self.audio_manager.trigger("menu_open")
                self._set_notice(after_snapshot["status_message"], duration=1.8)
            else:
                self.animator.trigger("select")
                self.audio_manager.trigger("menu_open")
                self._set_notice("New run prepared. Choose a character.", duration=2.4)
        elif action_type == "title_confirm_new_run":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice("New run prepared. Choose a character.", duration=2.4)
        elif action_type == "title_cancel_new_run":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice("Kept the current resumable run.", duration=1.6)
        elif action_type == "title_continue":
            self.animator.trigger(self._animator_state_for_current_state(after_snapshot["current_state"]))
            self.audio_manager.trigger("menu_open")
            self._set_notice("Continued the saved run.", level="success", duration=2.4)
        elif action_type == "new_run":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice("New run prepared. Choose a character.", duration=2.4)
        elif action_type == "select_character":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], duration=1.6)
        elif action_type == "confirm_character_selection":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], duration=2.0)
        elif action_type == "select_run_modifier_offer":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], duration=1.6)
        elif action_type == "confirm_run_modifier_selection":
            self.animator.trigger("map")
            self.audio_manager.trigger("card_play")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.4)
        elif action_type == "select_node":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
        elif action_type == "play_card":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
        elif action_type == "end_turn":
            self.audio_manager.trigger("turn_end")
        elif action_type == "select_reward_option":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], duration=1.6)
        elif action_type == "confirm_reward_selection":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)
        elif action_type == "skip_reward_section":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], duration=1.8)
        elif action_type == "continue_from_reward":
            self.animator.trigger("map")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)
        elif action_type == "select_shop_offer":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], duration=1.6)
        elif action_type == "open_shop_menu":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], duration=1.4)
        elif action_type == "clear_shop_selection":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], duration=1.2)
        elif action_type == "purchase_shop_offer":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)
        elif action_type == "confirm_shop_purchase":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)
        elif action_type == "confirm_shop_cleanse":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)
        elif action_type == "reroll_shop_inventory":
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], level="success", duration=1.8)
        elif action_type == "leave_shop":
            self.animator.trigger("map")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)
        elif action_type == "select_event_choice":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], duration=1.6)
        elif action_type == "select_event_target":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], duration=1.4)
        elif action_type == "confirm_event_choice":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.2)
        elif action_type == "continue_from_event":
            self.animator.trigger("map")
            self.audio_manager.trigger("node_select")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.0)

        enemy_hp_change = self._enemy_hp_total(before_snapshot) - self._enemy_hp_total(after_snapshot)
        player_hp_change = self._player_hp(after_snapshot) - self._player_hp(before_snapshot)
        player_block_gain = self._player_block(after_snapshot) - self._player_block(before_snapshot)
        enemy_block_gain = self._enemy_block_total(after_snapshot) - self._enemy_block_total(before_snapshot)

        if enemy_hp_change > 0:
            self.animator.trigger("attack")
            self.audio_manager.trigger("enemy_hit")

        if player_hp_change < 0:
            self.animator.trigger("hit")
            self.audio_manager.trigger("player_hit")
        elif player_hp_change > 0:
            self.animator.trigger("heal")
            self.audio_manager.trigger("heal")

        if player_block_gain > 0 or enemy_block_gain > 0:
            self.animator.trigger("block")
            self.audio_manager.trigger("block")

        if (
            before_snapshot["current_state"] != "victory"
            and after_snapshot["current_state"] == "victory"
        ):
            self.animator.trigger("victory")
            self.audio_manager.trigger("victory")
            self._set_notice("Boss defeated. Run complete.", level="success", duration=3.2)
            return

        if (
            before_snapshot["current_state"] != "game_over"
            and after_snapshot["current_state"] == "game_over"
        ):
            self.animator.trigger("defeat")
            self.audio_manager.trigger("defeat")
            self._set_notice("Run failed. Press N to restart.", level="error", duration=3.2)
            return

        if (
            before_snapshot["current_state"] != "reward"
            and after_snapshot["current_state"] == "reward"
        ):
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.4)
            return

        if (
            before_snapshot["current_state"] != "shop"
            and after_snapshot["current_state"] == "shop"
        ):
            if before_snapshot["current_state"] == "map":
                self.ui_manager.begin_map_to_shop_transition(after_snapshot)
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.4)
            return

        if (
            before_snapshot["current_state"] != "event"
            and after_snapshot["current_state"] == "event"
        ):
            self.animator.trigger("select")
            self.audio_manager.trigger("menu_open")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.4)
            return

        if (
            before_snapshot["current_state"] != "combat"
            and after_snapshot["current_state"] == "combat"
        ):
            if before_snapshot["current_state"] == "map":
                self.ui_manager.begin_map_to_combat_transition(after_snapshot)
            self.animator.trigger("idle")
            self._set_notice(after_snapshot["status_message"], duration=2.0)
            return

        if (
            before_snapshot["current_state"] != "map"
            and after_snapshot["current_state"] == "map"
        ):
            self.ui_manager.begin_map_enter_transition(after_snapshot)
            self.animator.trigger("map")
            self._set_notice(after_snapshot["status_message"], level="success", duration=2.2)

    def _initialize_audio(self) -> None:
        self.ui_manager.set_audio_callback(self.audio_manager.trigger)
        if pygame is None:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            return
        self.audio_manager.apply_settings(self._persistent_settings_payload())

    def _preload_presentation_assets(self) -> None:
        self.ui_manager.preload_assets()
        for cue_name, filename in {**DEFAULT_AUDIO_CUES, **CHOSEN_AUDIO_CUES}.items():
            self.audio_manager.load_sound(cue_name, filename)

    def _create_display_surface(self) -> Any:
        if pygame is None:
            raise RuntimeError("Pygame is required to create the display surface.")

        info = pygame.display.Info()
        if self._fullscreen:
            try:
                display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                display_surface = pygame.display.set_mode(self._windowed_size(info), pygame.RESIZABLE)
                self._fullscreen = False
        else:
            display_surface = pygame.display.set_mode(self._windowed_size(info), pygame.RESIZABLE)

        initial_size = self._logical_surface_size_for_display(display_surface.get_size())
        self._logical_surface = pygame.Surface(initial_size).convert()
        return display_surface

    def _handle_global_event(self, event: Any, screen: Any) -> tuple[Any, bool]:
        if pygame is None:
            return screen, False

        if event.type == pygame.VIDEORESIZE and not self._fullscreen:
            resized = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            return resized, True

        if event.type != pygame.KEYDOWN:
            return screen, False

        current_state = "title" if self._title_active else self.state_manager.current_state
        if self.ui_manager.is_transition_active():
            return screen, True

        if event.key == pygame.K_ESCAPE:
            if self._settings_open:
                self._toggle_settings(False)
                return screen, True
            if self._intel_open:
                self._dispatch_action({"type": "intel_close"}, screen)
                return screen, True
            if current_state in {"modifier_draft", "map", "combat", "reward", "shop", "event"}:
                self._pause_open = not self._pause_open
                self.animator.trigger("select")
                self.audio_manager.trigger("menu_open")
                self._set_notice("Paused." if self._pause_open else "Resumed.", duration=1.2)
                return screen, True
            if self._title_active and self._title_confirm_new_run:
                return screen, False
            self.running = False
            return screen, True

        if event.key == pygame.K_h:
            self._set_notice("Controls moved to Settings -> Controls.", duration=1.6)
            return screen, True

        if event.key == pygame.K_i:
            if current_state in {"map", "combat", "reward", "shop", "event", "modifier_draft"}:
                if self._intel_open:
                    self._dispatch_action({"type": "intel_close"}, screen)
                else:
                    self._dispatch_action({"type": "intel_open"}, screen)
            return screen, True

        if event.key == pygame.K_s:
            if self._settings_open:
                self._toggle_settings(False)
            else:
                self._toggle_settings(True, page="general", from_pause=self._pause_open)
            return screen, True

        if event.key == pygame.K_F11:
            updated_screen = self._apply_setting_change("fullscreen", not self._fullscreen, screen)
            return updated_screen, True

        if event.key == pygame.K_f:
            updated_screen = self._apply_setting_change("fast_mode", not self._fast_mode, screen)
            return updated_screen, True

        if event.key == pygame.K_m:
            updated_screen = self._apply_setting_change("muted", not self.audio_manager.muted, screen)
            return updated_screen, True

        if event.key in {pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET}:
            delta = -VOLUME_STEP if event.key == pygame.K_LEFTBRACKET else VOLUME_STEP
            updated_screen = self._apply_setting_change(
                "master_volume",
                self.audio_manager.master_volume + delta,
                screen,
            )
            return updated_screen, True

        if event.key in {pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_EQUALS, pygame.K_KP_PLUS}:
            delta = -PRESENTATION_SCALE_STEP if event.key in {pygame.K_MINUS, pygame.K_KP_MINUS} else PRESENTATION_SCALE_STEP
            updated_screen = self._apply_setting_change(
                "presentation_scale",
                self._presentation_scale + delta,
                screen,
            )
            return updated_screen, True

        return screen, False

    def _render_frame(self, display_surface: Any) -> None:
        if pygame is None:
            return

        state_snapshot = self._snapshot_with_hand()
        self._sync_logical_surface(state_snapshot, display_surface.get_size())
        self.ui_manager.render(self._logical_surface, state_snapshot)
        self._render_feedback_overlay(self._logical_surface)
        scaled_size, offset = self._presentation_layout(
            display_surface.get_size(),
            self._logical_surface.get_size(),
        )

        display_surface.fill((0, 0, 0))
        scaled_frame = (
            self._logical_surface
            if scaled_size == self._logical_surface.get_size()
            else pygame.transform.smoothscale(self._logical_surface, scaled_size)
        )

        shake_x, shake_y = self._screen_offset()
        display_surface.blit(scaled_frame, (offset[0] + shake_x, offset[1] + shake_y))

    def _presentation_layout(
        self,
        display_size: tuple[int, int],
        logical_size: tuple[int, int],
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        display_width, display_height = display_size
        logical_width, logical_height = logical_size
        scale = min(display_width / logical_width, display_height / logical_height)
        scale *= self._presentation_scale
        scaled_width = min(display_width, max(1, int(logical_width * scale)))
        scaled_height = min(display_height, max(1, int(logical_height * scale)))
        offset_x = (display_width - scaled_width) // 2
        offset_y = (display_height - scaled_height) // 2
        return (scaled_width, scaled_height), (offset_x, offset_y)

    def _translate_event(self, event: Any, display_surface: Any) -> Any | None:
        if pygame is None or self._logical_surface is None:
            return event

        if event.type not in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            return event

        logical_pos = self._logical_position_for_display(event.pos, display_surface.get_size())
        if logical_pos is None:
            if event.type == pygame.MOUSEMOTION:
                event_data = dict(event.dict)
                event_data["pos"] = (-1, -1)
                event_data["rel"] = (0, 0)
                return pygame.event.Event(event.type, event_data)
            return None

        event_data = dict(event.dict)
        event_data["pos"] = logical_pos
        if event.type == pygame.MOUSEMOTION:
            event_data["rel"] = (0, 0)
        return pygame.event.Event(event.type, event_data)

    def _logical_position_for_display(
        self,
        position: tuple[int, int],
        display_size: tuple[int, int],
    ) -> tuple[int, int] | None:
        logical_size = SCREEN_SIZE if self._logical_surface is None else self._logical_surface.get_size()
        scaled_size, offset = self._presentation_layout(display_size, logical_size)
        scaled_width, scaled_height = scaled_size
        offset_x, offset_y = offset
        x, y = position
        if not (offset_x <= x < offset_x + scaled_width and offset_y <= y < offset_y + scaled_height):
            return None

        relative_x = (x - offset_x) / scaled_width
        relative_y = (y - offset_y) / scaled_height
        logical_x = min(logical_size[0] - 1, max(0, int(relative_x * logical_size[0])))
        logical_y = min(logical_size[1] - 1, max(0, int(relative_y * logical_size[1])))
        return logical_x, logical_y

    def _snapshot_with_hand(self) -> dict[str, Any]:
        if self._title_active:
            snapshot = self._title_snapshot()
        else:
            snapshot = self.state_manager.get_state_snapshot()
        snapshot["presentation"] = self._presentation_state()
        snapshot["ui_notice"] = None if self._notice is None else dict(self._notice)
        return snapshot

    def _presentation_state(self) -> dict[str, Any]:
        return {
            "fullscreen": self._fullscreen,
            "fast_mode": self._fast_mode,
            "pause_open": self._pause_open,
            "intel_open": self._intel_open,
            "intel_selected_faction": self._intel_selected_faction,
            "settings_open": self._settings_open,
            "settings_page": self._settings_page,
            "presentation_scale": round(self._presentation_scale, 2),
            "ui_scale": round(self._ui_scale, 2),
            "screen_shake": self._screen_shake,
            "high_contrast": self._high_contrast,
            "master_volume": round(self.audio_manager.master_volume, 2),
            "music_volume": round(self.audio_manager.music_volume, 2),
            "muted": self.audio_manager.muted,
            "animation": self.animator.get_state(),
        }

    def _title_snapshot(self) -> dict[str, Any]:
        return {
            "current_state": "title",
            "status_message": self._title_status_message,
            "run_seed": None,
            "title": {
                "continue_enabled": self._title_continue_payload is not None,
                "continue_summary": None if self._title_continue_summary is None else dict(self._title_continue_summary),
                "confirm_overwrite": self._title_confirm_new_run,
            },
            "modifier_draft": None,
            "character": None,
            "character_select": None,
            "run_modifiers": {"active": [], "count": 0, "primary_label": None},
            "map": None,
            "combat": None,
            "event": None,
            "reward": None,
            "shop": None,
            "player": None,
            "player_hand": [],
        }

    def _advance_notice(self, delta_time: float) -> None:
        if self._notice is None:
            return
        speed = FAST_MODE_MULTIPLIER if self._fast_mode else 1.0
        self._notice_timer -= delta_time * speed
        if self._notice_timer <= 0:
            self._notice = None
            self._notice_timer = 0.0

    def _advance_interaction_cooldown(self, delta_time: float) -> None:
        self._interaction_cooldown = max(0.0, self._interaction_cooldown - delta_time)

    def _set_notice(
        self,
        text: str,
        level: str = "info",
        duration: float = NOTICE_DURATION_SECONDS,
    ) -> None:
        self._notice = {"text": text, "level": level}
        self._notice_timer = duration

    def _windowed_size(self, display_info: Any) -> tuple[int, int]:
        width = min(display_info.current_w, max(MIN_SUPPORTED_WIDTH, int(display_info.current_w * 0.9)))
        height = min(display_info.current_h, max(MIN_SUPPORTED_HEIGHT, int(display_info.current_h * 0.9)))
        return width, height

    def _sync_logical_surface(self, state_snapshot: dict[str, Any], display_size: tuple[int, int]) -> None:
        if pygame is None:
            return
        desired_size = self._logical_surface_size_for_state(state_snapshot, display_size)
        if self._logical_surface is None or self._logical_surface.get_size() != desired_size:
            self._logical_surface = pygame.Surface(desired_size).convert()

    def _logical_surface_size_for_state(
        self,
        state_snapshot: dict[str, Any],
        display_size: tuple[int, int],
    ) -> tuple[int, int]:
        del state_snapshot
        return self._logical_surface_size_for_display(display_size)

    def _logical_surface_size_for_display(self, display_size: tuple[int, int]) -> tuple[int, int]:
        return (
            max(MIN_WINDOW_WIDTH, int(display_size[0])),
            max(MIN_WINDOW_HEIGHT, int(display_size[1])),
        )

    def _enemy_hp_total(self, snapshot: dict[str, Any]) -> int:
        combat_state = snapshot.get("combat")
        if combat_state is None:
            return 0
        return sum(enemy["current_hp"] for enemy in combat_state["enemies"])

    def _enemy_block_total(self, snapshot: dict[str, Any]) -> int:
        combat_state = snapshot.get("combat")
        if combat_state is None:
            return 0
        return sum(enemy["block"] for enemy in combat_state["enemies"])

    def _player_hp(self, snapshot: dict[str, Any]) -> int:
        player_state = snapshot.get("player")
        if player_state is None:
            return 0
        return player_state["current_hp"]

    def _player_block(self, snapshot: dict[str, Any]) -> int:
        player_state = snapshot.get("player")
        if player_state is None:
            return 0
        return player_state["block"]

    def _screen_offset(self) -> tuple[int, int]:
        if not self._screen_shake:
            return 0, 0

        animation = self.animator.get_state()
        state = animation["current_state"]
        time_in_state = animation["time_in_state"]
        strength_map = {
            "attack": 3,
            "hit": 7,
            "deny": 3,
            "select": 2,
            "victory": 2,
            "defeat": 5,
        }
        strength = strength_map.get(state, 0)
        if strength == 0 or time_in_state > 0.28:
            return 0, 0

        falloff = 1.0 - (time_in_state / 0.28)
        x = int(math.sin(time_in_state * 62) * strength * falloff)
        y = int(math.cos(time_in_state * 48) * (strength * 0.45) * falloff)
        return x, y

    def _render_feedback_overlay(self, surface: Any) -> None:
        if pygame is None:
            return

        animation = self.animator.get_state()
        state = animation["current_state"]
        time_in_state = animation["time_in_state"]
        color_map = {
            "attack": ((255, 180, 90), 28, 0.18),
            "hit": ((255, 90, 110), 56, 0.24),
            "heal": ((90, 235, 170), 42, 0.24),
            "block": ((110, 180, 255), 34, 0.24),
            "deny": ((255, 120, 120), 48, 0.18),
            "victory": ((255, 230, 140), 36, 0.4),
            "defeat": ((180, 90, 120), 44, 0.34),
            "settings": ((100, 180, 255), 18, 0.14),
        }
        if state not in color_map:
            return

        color, max_alpha, duration = color_map[state]
        if time_in_state > duration:
            return

        progress = 1.0 - (time_in_state / duration)
        alpha = int(max_alpha * progress)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*color, alpha))
        surface.blit(overlay, (0, 0))

    def _toggle_settings(
        self,
        open_state: bool | None = None,
        *,
        page: str | None = None,
        from_pause: bool | None = None,
    ) -> None:
        target_state = (not self._settings_open) if open_state is None else bool(open_state)
        if self._settings_open == target_state and page is None and from_pause is None:
            return

        if target_state:
            self._settings_open = True
            self._settings_page = "controls" if page == "controls" else "general"
            self._settings_return_to_pause = self._pause_open if from_pause is None else bool(from_pause)
            self.animator.trigger("settings")
            self.audio_manager.trigger("menu_open")
            self._set_notice("Settings opened.", duration=1.4)
        else:
            return_to_pause = self._settings_return_to_pause
            self._settings_open = False
            self._settings_return_to_pause = False
            self._pause_open = return_to_pause
            self._set_notice(
                "Returned to pause menu." if return_to_pause else "Settings closed.",
                duration=1.4,
            )

    def _default_settings(self) -> dict[str, Any]:
        return {
            "settings_format_version": SETTINGS_FORMAT_VERSION,
            "fullscreen": DEFAULT_FULLSCREEN,
            "fast_mode": DEFAULT_FAST_MODE,
            "master_volume": DEFAULT_MASTER_VOLUME,
            "music_volume": DEFAULT_MUSIC_VOLUME,
            "muted": False,
            "presentation_scale": DEFAULT_PRESENTATION_SCALE,
            "ui_scale": DEFAULT_UI_SCALE,
            "screen_shake": DEFAULT_SCREEN_SHAKE,
            "high_contrast": DEFAULT_HIGH_CONTRAST,
        }

    def _load_settings(self) -> None:
        defaults = self._default_settings()
        path_exists = SETTINGS_DATA_PATH.exists()
        payload = self._load_json(SETTINGS_DATA_PATH)
        if not isinstance(payload, dict):
            self._apply_loaded_settings(defaults)
            self._persist_settings()
            if path_exists:
                LOGGER.warning("Settings file was invalid and has been reset to defaults.")
            return

        merged = {**defaults}
        for key in defaults:
            if key in payload:
                merged[key] = payload[key]
        merged = self._migrate_settings_payload(payload, merged)
        self._apply_loaded_settings(merged)
        self._persist_settings()

    def _migrate_settings_payload(self, payload: dict[str, Any], merged: dict[str, Any]) -> dict[str, Any]:
        version = payload.get("settings_format_version")
        try:
            version_number = int(version)
        except (TypeError, ValueError):
            version_number = 0
        if version_number >= SETTINGS_FORMAT_VERSION:
            return merged
        if self._is_legacy_scale_baseline(payload):
            merged["presentation_scale"] = DEFAULT_PRESENTATION_SCALE
            merged["ui_scale"] = DEFAULT_UI_SCALE
        return merged

    def _is_legacy_scale_baseline(self, payload: dict[str, Any]) -> bool:
        try:
            presentation_scale = float(payload.get("presentation_scale"))
            ui_scale = float(payload.get("ui_scale"))
        except (TypeError, ValueError):
            return False
        return abs(presentation_scale - 0.95) < 0.0001 and abs(ui_scale - 0.9) < 0.0001

    def _apply_loaded_settings(self, settings: dict[str, Any]) -> None:
        self._fullscreen = bool(settings.get("fullscreen", DEFAULT_FULLSCREEN))
        self._fast_mode = bool(settings.get("fast_mode", DEFAULT_FAST_MODE))
        self._presentation_scale = self._clamp_setting(
            settings.get("presentation_scale", DEFAULT_PRESENTATION_SCALE),
            MIN_PRESENTATION_SCALE,
            MAX_PRESENTATION_SCALE,
        )
        self._ui_scale = self._clamp_setting(
            settings.get("ui_scale", DEFAULT_UI_SCALE),
            MIN_UI_SCALE,
            MAX_UI_SCALE,
        )
        self._screen_shake = bool(settings.get("screen_shake", DEFAULT_SCREEN_SHAKE))
        self._high_contrast = bool(settings.get("high_contrast", DEFAULT_HIGH_CONTRAST))
        self.audio_manager.apply_settings(settings)

    def _apply_setting_change(self, setting_name: str, value: Any, screen: Any) -> Any:
        if setting_name == "fullscreen":
            self._fullscreen = bool(value)
            self._persist_settings()
            updated_screen = self._create_display_surface() if pygame is not None else screen
            mode = "Fullscreen" if self._fullscreen else "Windowed"
            self.animator.trigger("settings")
            self.audio_manager.trigger("menu_open")
            self._set_notice(f"{mode} mode enabled.", duration=1.6)
            return updated_screen

        if setting_name == "fast_mode":
            self._fast_mode = bool(value)
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(
                "Fast mode enabled." if self._fast_mode else "Fast mode disabled.",
                duration=1.6,
            )
            return screen

        if setting_name == "master_volume":
            volume = self.audio_manager.set_master_volume(float(value))
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(f"SFX volume {int(volume * 100)}%.", duration=1.6)
            return screen

        if setting_name == "music_volume":
            volume = self.audio_manager.set_music_volume(float(value))
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(f"Music volume {int(volume * 100)}%.", duration=1.6)
            return screen

        if setting_name == "muted":
            muted = self.audio_manager.set_muted(bool(value))
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice("Audio muted." if muted else "Audio restored.", duration=1.6)
            return screen

        if setting_name == "presentation_scale":
            self._presentation_scale = self._clamp_setting(
                float(value),
                MIN_PRESENTATION_SCALE,
                MAX_PRESENTATION_SCALE,
            )
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(
                f"Presentation scale {int(self._presentation_scale * 100)}%.",
                duration=1.6,
            )
            return screen

        if setting_name == "ui_scale":
            self._ui_scale = self._clamp_setting(float(value), MIN_UI_SCALE, MAX_UI_SCALE)
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(f"UI scale {int(self._ui_scale * 100)}%.", duration=1.6)
            return screen

        if setting_name == "screen_shake":
            self._screen_shake = bool(value)
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(
                "Screen shake enabled." if self._screen_shake else "Screen shake disabled.",
                duration=1.6,
            )
            return screen

        if setting_name == "high_contrast":
            self._high_contrast = bool(value)
            self._persist_settings()
            self.animator.trigger("settings")
            self._set_notice(
                "High contrast enabled." if self._high_contrast else "High contrast disabled.",
                duration=1.6,
            )
            return screen

        self._trigger_denial_feedback(f"Unsupported setting: {setting_name}")
        return screen

    def _apply_runtime_settings(self, settings: dict[str, Any], screen: Any) -> Any:
        self._apply_loaded_settings(settings)
        if pygame is not None:
            screen = self._create_display_surface()
        return screen

    def _persistent_settings_payload(self) -> dict[str, Any]:
        return {
            "settings_format_version": SETTINGS_FORMAT_VERSION,
            "fullscreen": self._fullscreen,
            "fast_mode": self._fast_mode,
            "master_volume": self.audio_manager.master_volume,
            "music_volume": self.audio_manager.music_volume,
            "muted": self.audio_manager.muted,
            "presentation_scale": self._presentation_scale,
            "ui_scale": self._ui_scale,
            "screen_shake": self._screen_shake,
            "high_contrast": self._high_contrast,
        }

    def _persist_settings(self) -> None:
        self._save_json_atomic(SETTINGS_DATA_PATH, self._persistent_settings_payload())

    def _bootstrap_run_state(self) -> tuple[str, str]:
        self._title_active = True
        self._title_confirm_new_run = False
        self._pause_open = False
        self._intel_open = False
        self._intel_selected_faction = None
        self._settings_open = False
        self._settings_page = "general"
        self._intel_return_to_pause = False
        self._settings_return_to_pause = False
        available, restore_message, restore_level = self._inspect_saved_run_if_available()
        self.animator.trigger("idle")
        self._title_status_message = (
            "Continue a saved run or start fresh with a new character."
            if available
            else "Choose how to enter the city."
        )
        return restore_message or "Title screen ready.", restore_level

    def _inspect_saved_run_if_available(self) -> tuple[bool, str | None, str]:
        path_exists = RUN_SAVE_DATA_PATH.exists()
        payload = self._load_json(RUN_SAVE_DATA_PATH)
        if payload is None:
            if path_exists:
                self._clear_run_save()
                self._title_continue_payload = None
                self._title_continue_summary = None
                return False, "Saved run data was invalid and has been cleared.", "error"
            return False, None, "info"

        if not isinstance(payload, dict):
            self._clear_run_save()
            self._title_continue_payload = None
            self._title_continue_summary = None
            return False, "Saved run data was invalid and has been cleared.", "error"

        if payload.get("current_state") in {"victory", "game_over"}:
            self._clear_run_save()
            self._title_continue_payload = None
            self._title_continue_summary = None
            return False, "Previous run had already ended. Start a new one.", "info"

        try:
            probe_manager = StateManager()
            snapshot = probe_manager.restore_save_data(payload)
        except Exception as exc:  # pragma: no cover - recovery path.
            LOGGER.warning("Failed to restore saved run: %s", exc)
            self._clear_run_save()
            self._title_continue_payload = None
            self._title_continue_summary = None
            return False, "Saved run could not be restored and has been cleared.", "error"

        if snapshot["current_state"] not in {"character_select", "modifier_draft", "map", "combat", "reward", "shop", "event"}:
            self._clear_run_save()
            self._title_continue_payload = None
            self._title_continue_summary = None
            return False, "Saved run was not resumable and has been cleared.", "error"

        self._title_continue_payload = payload
        self._title_continue_summary = {
            "current_state": snapshot["current_state"],
            "run_seed": snapshot["run_seed"],
            "status_message": snapshot["status_message"],
            "modifier_label": snapshot.get("run_modifiers", {}).get("primary_label"),
            "character_name": None if snapshot.get("character") is None else snapshot["character"].get("name"),
            "map_name": None if snapshot.get("campaign") is None else snapshot["campaign"].get("map_name"),
            "map_index": None if snapshot.get("campaign") is None else snapshot["campaign"].get("map_index"),
            "current_hp": None if snapshot.get("player") is None else snapshot["player"].get("current_hp"),
            "max_hp": None if snapshot.get("player") is None else snapshot["player"].get("max_hp"),
        }
        return True, "Continue is available.", "success"

    def _begin_new_run(self) -> None:
        self._title_active = False
        self._title_confirm_new_run = False
        self._pause_open = False
        self._intel_open = False
        self._intel_selected_faction = None
        self._settings_open = False
        self._settings_page = "general"
        self._intel_return_to_pause = False
        self._settings_return_to_pause = False
        self.state_manager = StateManager()
        self.state_manager.start_new_run()
        self._persist_run_state(self.state_manager.get_state_snapshot())

    def _continue_saved_run(self) -> None:
        if self._title_continue_payload is None:
            raise ValueError("No resumable run is available.")
        self.state_manager = StateManager()
        self.state_manager.restore_save_data(self._title_continue_payload)
        self._title_active = False
        self._title_confirm_new_run = False
        self._pause_open = False
        self._intel_open = False
        self._intel_selected_faction = None
        self._settings_open = False
        self._settings_page = "general"
        self._intel_return_to_pause = False
        self._settings_return_to_pause = False

    def _persist_run_state(self, snapshot: dict[str, Any]) -> None:
        current_state = snapshot.get("current_state")
        if current_state == "title":
            return
        if current_state not in {"character_select", "modifier_draft", "map", "combat", "reward", "shop", "event"}:
            self._clear_run_save()
            return

        try:
            payload = self.state_manager.build_save_data()
            self._save_json_atomic(RUN_SAVE_DATA_PATH, payload)
        except Exception as exc:  # pragma: no cover - recovery path.
            LOGGER.warning("Failed to persist run state: %s", exc)
            self._set_notice("Auto-save failed, but the run is still active.", level="error", duration=2.6)

    def _clear_run_save(self) -> None:
        try:
            RUN_SAVE_DATA_PATH.unlink(missing_ok=True)
        except OSError:
            return

    def _load_json(self, path: Path) -> Any | None:
        try:
            if not path.exists():
                return None
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

    def _save_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)

    def _clamp_setting(self, value: Any, minimum: float, maximum: float) -> float:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = minimum
        return max(minimum, min(maximum, numeric_value))

    def _trigger_denial_feedback(self, message: str) -> None:
        self.animator.trigger("deny")
        self.audio_manager.trigger("deny")
        self._set_notice(message, level="error")

    def _action_uses_cooldown(self, action_type: str) -> bool:
        return action_type in {
            "new_run",
            "title_continue",
            "title_confirm_new_run",
            "confirm_character_selection",
            "select_node",
            "confirm_run_modifier_selection",
            "play_card",
            "end_turn",
            "purchase_shop_offer",
            "confirm_reward_selection",
            "skip_reward_section",
            "continue_from_reward",
            "confirm_shop_purchase",
            "confirm_shop_cleanse",
            "reroll_shop_inventory",
            "leave_shop",
            "confirm_event_choice",
            "continue_from_event",
        }

    def _animator_state_for_current_state(self, current_state: str) -> str:
        if current_state == "map":
            return "map"
        if current_state in {"character_select", "modifier_draft", "reward", "shop", "event"}:
            return "select"
        if current_state in {"victory", "game_over"}:
            return "idle"
        return "idle"

    def _music_scene_for_snapshot(self, snapshot: dict[str, Any]) -> str:
        if self._title_active or snapshot.get("current_state") == "title":
            return "title"
        current_state = snapshot.get("current_state")
        if current_state == "combat":
            return "combat"
        if current_state in {"character_select", "modifier_draft", "map", "shop", "event", "reward"}:
            return "noncombat"
        return "silence"

    def _sync_music_scene(
        self,
        snapshot: dict[str, Any],
        *,
        before_snapshot: dict[str, Any] | None = None,
        action_type: str | None = None,
        force: bool = False,
    ) -> None:
        target_scene = self._music_scene_for_snapshot(snapshot)
        resume_existing_combat = (
            action_type == "title_continue"
            and before_snapshot is not None
            and before_snapshot.get("current_state") == "title"
            and target_scene == "combat"
        )
        if not force and target_scene == self._last_music_scene and not resume_existing_combat:
            return
        self.audio_manager.set_scene(
            target_scene,
            resume_existing_combat=resume_existing_combat,
            force=force,
        )
        LOGGER.info(
            "Audio scene requested: scene=%s requested_track=%s playing_track=%s",
            target_scene,
            self.audio_manager.requested_track_id,
            self.audio_manager.current_track_id,
        )
        self._last_music_scene = target_scene


def simulate_game_loop() -> dict[str, Any]:
    loop = GameLoop()
    loop._load_settings()
    boot_message, boot_level = loop._bootstrap_run_state()
    title_snapshot = loop._snapshot_with_hand()
    loop._begin_new_run()
    select_snapshot = loop._snapshot_with_hand()
    loop.state_manager.select_character("enforcer")
    loop.state_manager.confirm_character_selection()
    draft_snapshot = loop._snapshot_with_hand()
    first_offer_id = draft_snapshot["modifier_draft"]["offers"][0]["id"]
    loop.state_manager.select_run_modifier_offer(first_offer_id)
    before_confirm = loop._snapshot_with_hand()
    loop.state_manager.confirm_run_modifier_selection()
    after_confirm = loop._snapshot_with_hand()
    loop._apply_feedback("confirm_run_modifier_selection", before_confirm, after_confirm)
    layout = loop._presentation_layout((1024, 768), SCREEN_SIZE)
    return {
        "boot_message": boot_message,
        "boot_level": boot_level,
        "title_state": title_snapshot["current_state"],
        "character_select_state": select_snapshot["current_state"],
        "current_state": after_confirm["current_state"],
        "run_seed": after_confirm["run_seed"],
        "snapshot_keys": sorted(after_confirm.keys()),
        "animation_state": loop.animator.get_state()["current_state"],
        "audio_history": list(loop.audio_manager.trigger_history),
        "presentation_layout": layout,
        "notice": loop._notice,
        "settings": loop._persistent_settings_payload(),
    }
