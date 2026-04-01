from __future__ import annotations

from typing import Any


class TurnManager:
    def __init__(self) -> None:
        self.turn_number = 0
        self.turn_owner = "player"

    def start_player_turn(self, player: Any) -> dict[str, Any]:
        if player.deck_manager is None:
            raise ValueError("Player turn cannot start without an attached deck manager.")

        self.turn_number += 1
        self.turn_owner = "player"
        player.start_turn()
        drawn_cards = player.deck_manager.draw_cards(player.draw_per_turn)
        return {"turn_number": self.turn_number, "drawn_cards": [card.id for card in drawn_cards]}

    def end_player_turn(self, player: Any) -> None:
        if player.deck_manager is None:
            raise ValueError("Player turn cannot end without an attached deck manager.")

        player.deck_manager.discard_hand()
        self.turn_owner = "enemy"

    def start_enemy_turn(self, enemy: Any) -> None:
        self.turn_owner = "enemy"
        enemy.start_turn()


def simulate_turn_manager() -> dict[str, Any]:
    import random

    from cards.card_library import CardLibrary
    from cards.deck_manager import DeckManager
    from entities.player import Player

    library = CardLibrary()
    deck = DeckManager(
        [library.create_card("strike_01"), library.create_card("defend_01")],
        rng=random.Random(11),
    )
    player = Player()
    player.attach_deck(deck)
    player.energy = 0
    turn_manager = TurnManager()
    start_summary = turn_manager.start_player_turn(player)
    turn_manager.end_player_turn(player)
    return {
        "start": start_summary,
        "energy_after_reset": player.energy,
        "turn_owner": turn_manager.turn_owner,
    }
