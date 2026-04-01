from __future__ import annotations

import random
from typing import Any

from cards.card_library import CardLibrary
from cards.deck_manager import DeckManager
from combat.combat_manager import CombatManager
from config import ENCOUNTER_ENEMY_IDS, STARTER_DECK_IDS
from entities.enemy_library import EnemyLibrary
from entities.player import Player
from map.map_generator import MapGenerator


class StateManager:
    def __init__(
        self,
        card_library: CardLibrary | None = None,
        enemy_library: EnemyLibrary | None = None,
    ) -> None:
        self.card_library = card_library or CardLibrary()
        self.enemy_library = enemy_library or EnemyLibrary()
        self.current_state = "boot"
        self.status_message = "Initialize a run."
        self.run_seed: int | None = None

        self.player: Player | None = None
        self.map_graph: dict[str, Any] | None = None
        self.available_node_ids: list[str] = []
        self.visited_node_ids: list[str] = []
        self.selected_node_id: str | None = None
        self.combat_manager: CombatManager | None = None

    def start_new_run(self, seed: int | None = None) -> dict[str, Any]:
        self.run_seed = seed if seed is not None else random.randrange(1, 1_000_000)

        self.player = self._create_player(self.run_seed)
        self.map_graph = MapGenerator(rng=random.Random(self.run_seed)).generate_map()
        self._enter_map_state(status_message="Select the next node.")
        self.available_node_ids = list(self.map_graph["start_nodes"])
        self.visited_node_ids = []
        self.selected_node_id = None
        self.combat_manager = None
        return self.get_state_snapshot()

    def select_map_node(self, node_id: str) -> dict[str, Any]:
        self._require_map()
        if node_id not in self.available_node_ids:
            raise ValueError(f"Node {node_id} is not currently available.")

        node = self.map_graph["nodes"][node_id]
        self.selected_node_id = node_id
        if node_id not in self.visited_node_ids:
            self.visited_node_ids.append(node_id)
        self.available_node_ids = list(node.next_nodes)

        if node.node_type in ENCOUNTER_ENEMY_IDS:
            self._start_combat_for_node(node.node_type)
        elif node.node_type in {"shop", "event"}:
            self._handle_placeholder_node(node.node_type)
        else:
            raise ValueError(f"Unsupported selectable node type: {node.node_type}")

        return self.get_state_snapshot()

    def play_card_from_hand(self, hand_index: int, target_id: str | None = None) -> dict[str, Any]:
        self._require_combat()

        hand = self.player.deck_manager.hand
        if hand_index < 0 or hand_index >= len(hand):
            raise IndexError("Requested hand index is out of range.")

        card = hand[hand_index]
        target = self.combat_manager.get_enemy(target_id) if target_id else None
        self.combat_manager.resolve_action({"card": card, "target": target})

        if not self.combat_manager.combat_active:
            self._close_combat()

        return self.get_state_snapshot()

    def end_combat_turn(self) -> dict[str, Any]:
        self._require_combat()
        self.combat_manager.end_turn()

        if not self.combat_manager.combat_active:
            self._close_combat()

        return self.get_state_snapshot()

    def get_state_snapshot(self) -> dict[str, Any]:
        return {
            "current_state": self.current_state,
            "status_message": self.status_message,
            "run_seed": self.run_seed,
            "map": self._snapshot_map(),
            "combat": self.combat_manager.get_state() if self.combat_manager is not None else None,
            "player": self.player.get_state() if self.player is not None else None,
            "player_hand": self._snapshot_hand(),
        }

    def _start_combat_for_node(self, node_type: str) -> None:
        if node_type not in ENCOUNTER_ENEMY_IDS:
            raise ValueError(f"Encounter node type is not mapped for combat: {node_type}")
        enemy_id = ENCOUNTER_ENEMY_IDS[node_type]
        enemy = self.enemy_library.create_enemy(enemy_id)
        self.combat_manager = CombatManager(player=self.player, enemies=[enemy])
        self.combat_manager.start_combat()
        self.current_state = "combat"
        self.status_message = f"Entered {node_type} encounter."

    def _close_combat(self) -> None:
        if self.player is None or self.combat_manager is None:
            return

        if self.player.is_alive():
            if self._current_node_type() == "boss":
                self.current_state = "victory"
                self.status_message = "Run completed."
            else:
                self._enter_map_state(status_message="Encounter cleared. Select the next node.")
        else:
            self.current_state = "game_over"
            self.status_message = "Run failed."
        self.combat_manager = None

    def _snapshot_map(self) -> dict[str, Any] | None:
        if self.map_graph is None:
            return None

        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.map_graph["nodes"].items()},
            "start_nodes": list(self.map_graph["start_nodes"]),
            "boss_node_id": self.map_graph["boss_node_id"],
            "available_node_ids": list(self.available_node_ids),
            "visited_node_ids": list(self.visited_node_ids),
            "selected_node_id": self.selected_node_id,
        }

    def _require_map(self) -> None:
        if self.map_graph is None or self.current_state not in {"map"}:
            raise ValueError("Map selection is only available while in the map state.")

    def _require_combat(self) -> None:
        if self.player is None or self.player.deck_manager is None or self.combat_manager is None:
            raise ValueError("Combat action requested without an active combat manager.")
        if self.current_state != "combat":
            raise ValueError("Combat actions are only available during combat.")

    def _snapshot_hand(self) -> list[dict[str, Any]]:
        if self.player is None or self.player.deck_manager is None:
            return []
        return [card.to_dict() for card in self.player.deck_manager.hand]

    def _current_node_type(self) -> str | None:
        if self.map_graph is None or self.selected_node_id is None:
            return None
        node = self.map_graph["nodes"].get(self.selected_node_id)
        return None if node is None else node.node_type

    def _create_player(self, seed: int) -> Player:
        starter_cards = [self.card_library.create_card(card_id) for card_id in STARTER_DECK_IDS]
        deck_manager = DeckManager(starter_cards, rng=random.Random(seed))
        player = Player()
        player.attach_deck(deck_manager)
        return player

    def _enter_map_state(self, status_message: str) -> None:
        self.current_state = "map"
        self.status_message = status_message

    def _handle_placeholder_node(self, node_type: str) -> None:
        self._enter_map_state(
            status_message=(
                f"{node_type.title()} node selected. Content is blocked until the contract defines that subsystem."
            )
        )


def simulate_state_manager() -> dict[str, Any]:
    manager = StateManager()
    start_snapshot = manager.start_new_run(seed=29)
    first_node = start_snapshot["map"]["available_node_ids"][0]
    selection_snapshot = manager.select_map_node(first_node)
    return {
        "start_state": start_snapshot["current_state"],
        "selected_node_id": first_node,
        "current_state": selection_snapshot["current_state"],
        "status_message": selection_snapshot["status_message"],
        "run_seed": selection_snapshot["run_seed"],
    }
