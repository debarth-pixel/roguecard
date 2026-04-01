from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None


class CombatUI:
    def __init__(self) -> None:
        self._font = None

    def handle_event(self, event: Any, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None or event.type != pygame.KEYDOWN:
            return None

        if pygame.K_1 <= event.key <= pygame.K_9:
            hand_index = event.key - pygame.K_1
            hand = combat_state["player_hand"]
            if hand_index < len(hand):
                return {"type": "play_card", "hand_index": hand_index}

        if event.key == pygame.K_e:
            return {"type": "end_turn"}

        return None

    def build_layout(self, combat_state: dict[str, Any]) -> dict[str, Any]:
        return {
            "player_hp": f"HP {combat_state['player']['current_hp']}/{combat_state['player']['max_hp']}",
            "player_energy": f"Energy {combat_state['player']['energy']}",
            "enemy_labels": [
                f"{enemy['name']} {enemy['current_hp']}/{enemy['max_hp']} [{enemy['current_intent']}]"
                for enemy in combat_state["enemies"]
            ],
            "hand_labels": [
                f"{index + 1}. {card['name']} ({card['cost']})"
                for index, card in enumerate(combat_state["player_hand"])
            ],
        }

    def render(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 24)

        layout = self.build_layout(combat_state)
        y = 24
        for text in [layout["player_hp"], layout["player_energy"], *layout["enemy_labels"], *layout["hand_labels"]]:
            rendered = self._font.render(text, True, (230, 230, 230))
            surface.blit(rendered, (24, y))
            y += 36


def simulate_combat_ui() -> dict[str, Any]:
    ui = CombatUI()
    return ui.build_layout(
        {
            "player": {"current_hp": 70, "max_hp": 70, "energy": 3},
            "enemies": [{"name": "Street Punk", "current_hp": 40, "max_hp": 40, "current_intent": "attack"}],
            "player_hand": [{"name": "Strike", "cost": 1}, {"name": "Defend", "cost": 1}],
        }
    )
