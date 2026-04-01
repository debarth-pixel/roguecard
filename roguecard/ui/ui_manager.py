from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from ui.combat_ui import CombatUI
from ui.map_ui import MapUI


class UIManager:
    def __init__(self) -> None:
        self.combat_ui = CombatUI()
        self.map_ui = MapUI()
        self._font = None

    def handle_event(self, event: Any, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        current_state = state_snapshot["current_state"]

        if current_state == "combat" and state_snapshot["combat"] is not None:
            return self.combat_ui.handle_event(event, self._combat_view_state(state_snapshot))

        if current_state == "map" and state_snapshot["map"] is not None:
            return self.map_ui.handle_event(event, state_snapshot["map"])

        if pygame is not None and event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            return {"type": "new_run"}

        return None

    def render(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 24)

        surface.fill((18, 21, 28))

        current_state = state_snapshot["current_state"]
        if current_state == "combat" and state_snapshot["combat"] is not None:
            self.combat_ui.render(surface, self._combat_view_state(state_snapshot))
        elif state_snapshot["map"] is not None:
            self.map_ui.render(surface, state_snapshot["map"])

        status = self._font.render(state_snapshot["status_message"], True, (245, 245, 245))
        surface.blit(status, (24, 24))

    def simulate_ui(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        if state_snapshot["current_state"] == "combat" and state_snapshot["combat"] is not None:
            return self.combat_ui.build_layout(self._combat_view_state(state_snapshot))
        if state_snapshot["map"] is not None:
            return self.map_ui.build_layout(state_snapshot["map"])
        return {"status_message": state_snapshot["status_message"]}

    def _combat_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        combat_state = state_snapshot["combat"]
        player_hand = []
        if state_snapshot["player"] is not None and state_snapshot["current_state"] == "combat":
            hand = state_snapshot.get("player_hand")
            if hand is None:
                hand = []
            player_hand = hand

        return {
            "player": combat_state["player"],
            "enemies": combat_state["enemies"],
            "player_hand": player_hand,
        }


def simulate_ui_manager() -> dict[str, Any]:
    manager = UIManager()
    return manager.simulate_ui(
        {
            "current_state": "map",
            "status_message": "Select the next node.",
            "map": {
                "nodes": {
                    "floor_0_node_0": {
                        "node_id": "floor_0_node_0",
                        "node_type": "combat",
                        "floor": 0,
                        "column": 0,
                        "next_nodes": [],
                    }
                },
                "available_node_ids": ["floor_0_node_0"],
            },
            "combat": None,
            "player": None,
        }
    )
