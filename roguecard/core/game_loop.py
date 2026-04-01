from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from animation.animator import Animator
from audio.audio_manager import AudioManager
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

    def run(self) -> None:
        if pygame is None:
            raise RuntimeError("Pygame is required to run the game loop.")

        pygame.init()
        screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Error: Not Found")
        clock = pygame.time.Clock()

        self.state_manager.start_new_run()
        self.running = True

        while self.running:
            delta_time = clock.tick(FRAME_RATE) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                action = self.ui_manager.handle_event(event, self._snapshot_with_hand())
                if action is not None:
                    self._dispatch_action(action)

            self.animator.update(delta_time)
            self.ui_manager.render(screen, self._snapshot_with_hand())
            pygame.display.flip()

        pygame.quit()

    def _dispatch_action(self, action: dict[str, Any]) -> None:
        action_type = action["type"]

        if action_type == "new_run":
            self.state_manager.start_new_run()
            self.animator.trigger("idle")
            return

        if action_type == "select_node":
            self.state_manager.select_map_node(action["node_id"])
            self.animator.trigger("idle")
            self.audio_manager.trigger("node_select")
            return

        if action_type == "play_card":
            self.state_manager.play_card_from_hand(action["hand_index"], action.get("target_id"))
            self.animator.trigger("attack")
            self.audio_manager.trigger("card_play")
            return

        if action_type == "end_turn":
            self.state_manager.end_combat_turn()
            self.animator.trigger("idle")
            self.audio_manager.trigger("turn_end")
            return

        raise ValueError(f"Unsupported UI action: {action_type}")

    def _snapshot_with_hand(self) -> dict[str, Any]:
        return self.state_manager.get_state_snapshot()


def simulate_game_loop() -> dict[str, Any]:
    loop = GameLoop()
    snapshot = loop.state_manager.start_new_run(seed=31)
    return {"current_state": snapshot["current_state"], "run_seed": snapshot["run_seed"]}
