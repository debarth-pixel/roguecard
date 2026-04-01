from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from animation.animator import Animator
from audio.audio_manager import AudioManager, DEFAULT_AUDIO_CUES
from config import FRAME_RATE, SCREEN_SIZE
from core.state_manager import StateManager
from ui.ui_manager import UIManager


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

    def run(self) -> None:
        if pygame is None:
            raise RuntimeError("Pygame is required to run the game loop.")

        pygame.init()
        self._initialize_audio()
        screen = self._create_display_surface()
        pygame.display.set_caption("Error: Not Found")
        clock = pygame.time.Clock()

        self._preload_presentation_assets()
        self.state_manager.start_new_run()
        self.animator.trigger("map")
        self.running = True

        while self.running:
            delta_time = clock.tick(FRAME_RATE) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                    continue

                action = self.ui_manager.handle_event(event, self._snapshot_with_hand())
                if action is not None:
                    self._dispatch_action(action)

            self.animator.update(delta_time)
            self._render_frame(screen)
            pygame.display.flip()

        pygame.quit()

    def _dispatch_action(self, action: dict[str, Any]) -> None:
        before_snapshot = self._snapshot_with_hand()
        action_type = action["type"]

        if action_type == "new_run":
            self.state_manager.start_new_run()
        elif action_type == "select_node":
            self.state_manager.select_map_node(action["node_id"])
        elif action_type == "play_card":
            self.state_manager.play_card_from_hand(action["hand_index"], action.get("target_id"))
        elif action_type == "end_turn":
            self.state_manager.end_combat_turn()
        else:
            raise ValueError(f"Unsupported UI action: {action_type}")

        after_snapshot = self._snapshot_with_hand()
        self._apply_feedback(action_type, before_snapshot, after_snapshot)

    def _apply_feedback(
        self,
        action_type: str,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> None:
        if action_type == "new_run":
            self.animator.trigger("map")
        elif action_type == "select_node":
            self.animator.trigger("select")
            self.audio_manager.trigger("node_select")
        elif action_type == "play_card":
            self.animator.trigger("card_play")
            self.audio_manager.trigger("card_play")
        elif action_type == "end_turn":
            self.audio_manager.trigger("turn_end")

        if self._enemy_hp_total(after_snapshot) < self._enemy_hp_total(before_snapshot):
            self.animator.trigger("attack")
            self.audio_manager.trigger("enemy_hit")

        if self._player_hp(after_snapshot) < self._player_hp(before_snapshot):
            self.animator.trigger("hit")
            self.audio_manager.trigger("player_hit")

        if (
            before_snapshot["current_state"] != "victory"
            and after_snapshot["current_state"] == "victory"
        ):
            self.animator.trigger("victory")
            self.audio_manager.trigger("victory")
            return

        if (
            before_snapshot["current_state"] != "game_over"
            and after_snapshot["current_state"] == "game_over"
        ):
            self.animator.trigger("defeat")
            self.audio_manager.trigger("defeat")
            return

        if (
            before_snapshot["current_state"] != "map"
            and after_snapshot["current_state"] == "map"
        ):
            self.animator.trigger("map")

    def _initialize_audio(self) -> None:
        if pygame is None:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            return

    def _preload_presentation_assets(self) -> None:
        self.ui_manager.preload_assets()
        for cue_name, filename in DEFAULT_AUDIO_CUES.items():
            self.audio_manager.load_sound(cue_name, filename)

    def _create_display_surface(self) -> Any:
        if pygame is None:
            raise RuntimeError("Pygame is required to create the display surface.")

        try:
            display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            display_surface = pygame.display.set_mode(SCREEN_SIZE)

        self._logical_surface = pygame.Surface(SCREEN_SIZE).convert()
        return display_surface

    def _render_frame(self, display_surface: Any) -> None:
        if pygame is None:
            return

        if self._logical_surface is None:
            self._logical_surface = pygame.Surface(SCREEN_SIZE).convert()

        self.ui_manager.render(self._logical_surface, self._snapshot_with_hand())
        scaled_size, offset = self._presentation_layout(
            display_surface.get_size(),
            self._logical_surface.get_size(),
        )

        display_surface.fill((0, 0, 0))
        if scaled_size == self._logical_surface.get_size():
            display_surface.blit(self._logical_surface, offset)
            return

        scaled_frame = pygame.transform.smoothscale(self._logical_surface, scaled_size)
        display_surface.blit(scaled_frame, offset)

    def _presentation_layout(
        self,
        display_size: tuple[int, int],
        logical_size: tuple[int, int],
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        display_width, display_height = display_size
        logical_width, logical_height = logical_size
        scale = min(display_width / logical_width, display_height / logical_height)
        scaled_width = max(1, int(logical_width * scale))
        scaled_height = max(1, int(logical_height * scale))
        offset_x = (display_width - scaled_width) // 2
        offset_y = (display_height - scaled_height) // 2
        return (scaled_width, scaled_height), (offset_x, offset_y)

    def _snapshot_with_hand(self) -> dict[str, Any]:
        return self.state_manager.get_state_snapshot()

    def _enemy_hp_total(self, snapshot: dict[str, Any]) -> int:
        combat_state = snapshot.get("combat")
        if combat_state is None:
            return 0
        return sum(enemy["current_hp"] for enemy in combat_state["enemies"])

    def _player_hp(self, snapshot: dict[str, Any]) -> int:
        player_state = snapshot.get("player")
        if player_state is None:
            return 0
        return player_state["current_hp"]


def simulate_game_loop() -> dict[str, Any]:
    loop = GameLoop()
    start_snapshot = loop.state_manager.start_new_run(seed=31)
    before_select = loop._snapshot_with_hand()
    loop.state_manager.select_map_node(start_snapshot["map"]["available_node_ids"][0])
    after_select = loop._snapshot_with_hand()
    loop._apply_feedback("select_node", before_select, after_select)
    layout = loop._presentation_layout((1024, 768), SCREEN_SIZE)
    return {
        "current_state": after_select["current_state"],
        "run_seed": after_select["run_seed"],
        "snapshot_keys": sorted(after_select.keys()),
        "animation_state": loop.animator.get_state()["current_state"],
        "audio_history": list(loop.audio_manager.trigger_history),
        "presentation_layout": layout,
    }
