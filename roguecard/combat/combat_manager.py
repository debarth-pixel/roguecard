from __future__ import annotations

from typing import Any

from combat.action_resolver import ActionResolver
from combat.turn_manager import TurnManager


class CombatManager:
    def __init__(self, player: Any, enemies: list[Any]) -> None:
        self.player = player
        self.enemies = enemies
        self.action_resolver = ActionResolver()
        self.turn_manager = TurnManager()
        self.combat_active = False
        self.event_log: list[dict[str, Any]] = []

    def start_combat(self) -> dict[str, Any]:
        if self.player.deck_manager is None:
            raise ValueError("Combat requires a player with an attached deck manager.")
        if not self.enemies:
            raise ValueError("Combat requires at least one enemy.")

        self.turn_manager = TurnManager()
        self.player.start_combat()
        for enemy in self.enemies:
            enemy.reset_for_combat()
            enemy.choose_intent()

        self.combat_active = True
        self.event_log.clear()
        opening_turn = self.turn_manager.start_player_turn(self.player)
        return {"combat_active": self.combat_active, "opening_turn": opening_turn}

    def end_turn(self) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot end a turn outside of active combat.")

        self.turn_manager.end_player_turn(self.player)
        enemy_results: list[dict[str, Any]] = []

        for enemy in self._living_enemies():
            self.turn_manager.start_enemy_turn(enemy)
            resolution = enemy.execute_intent(self.action_resolver, self.player)
            enemy_results.append({"enemy_id": enemy.id, "resolution": resolution})
            if not self.player.is_alive():
                self.combat_active = False
                return {"combat_active": self.combat_active, "enemy_results": enemy_results}

        if not self._living_enemies():
            self.combat_active = False
            return {"combat_active": self.combat_active, "enemy_results": enemy_results}

        for enemy in self._living_enemies():
            enemy.choose_intent()

        next_turn = self.turn_manager.start_player_turn(self.player)
        return {
            "combat_active": self.combat_active,
            "enemy_results": enemy_results,
            "next_turn": next_turn,
        }

    def resolve_action(self, action: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.combat_active:
            raise ValueError("Cannot resolve actions outside of active combat.")
        if not isinstance(action, dict):
            raise ValueError("Combat actions must be dictionaries.")

        card = action.get("card")
        explicit_target = action.get("target")
        exhaust = bool(action.get("exhaust", False))

        if card is None:
            raise ValueError("Combat actions require a card instance.")

        self.player.spend_energy(card.cost)
        resolutions: list[dict[str, Any]] = []
        logged_resolutions: list[dict[str, Any]] = []
        for effect in card.effects:
            target = self._resolve_effect_target(effect.type, explicit_target)
            resolution = self.action_resolver.resolve(
                action={"type": effect.type, "value": effect.value},
                source=self.player,
                target=target,
                combat_manager=self,
            )
            resolutions.append(resolution)
            logged_resolutions.append(
                {
                    **resolution,
                    "target": getattr(target, "id", "player"),
                }
            )

        if exhaust:
            self.player.deck_manager.exhaust_card(card)
        else:
            self.player.deck_manager.discard_card(card)

        self.event_log.append(
            {
                "card_id": card.id,
                "resolutions": logged_resolutions,
            }
        )

        if not self._living_enemies():
            self.combat_active = False

        return resolutions

    def get_state(self) -> dict[str, Any]:
        return {
            "combat_active": self.combat_active,
            "turn_number": self.turn_manager.turn_number,
            "player": self.player.get_state(),
            "enemies": [enemy.get_state() for enemy in self.enemies],
            "event_log": list(self.event_log),
        }

    def get_enemy(self, enemy_id: str) -> Any | None:
        for enemy in self.enemies:
            if enemy.id == enemy_id and enemy.is_alive():
                return enemy
        return None

    def _resolve_effect_target(self, effect_type: str, explicit_target: Any | None) -> Any:
        target = explicit_target
        if target is None:
            if effect_type == "damage":
                target = self._first_living_enemy()
            else:
                target = self.player

        if target is None:
            raise ValueError(f"No valid target available for effect type: {effect_type}")
        if hasattr(target, "is_alive") and not target.is_alive():
            raise ValueError("Combat effects cannot target defeated combatants.")
        return target

    def _living_enemies(self) -> list[Any]:
        return [enemy for enemy in self.enemies if enemy.is_alive()]

    def _first_living_enemy(self) -> Any | None:
        living = self._living_enemies()
        return living[0] if living else None


def simulate_combat_manager() -> dict[str, Any]:
    import random

    from cards.card_library import CardLibrary
    from cards.deck_manager import DeckManager
    from entities.enemy_library import EnemyLibrary
    from entities.player import Player

    card_library = CardLibrary()
    deck = DeckManager(
        [
            card_library.create_card("strike_01"),
            card_library.create_card("strike_01"),
            card_library.create_card("defend_01"),
        ],
        rng=random.Random(17),
    )
    player = Player()
    player.attach_deck(deck)
    enemy = EnemyLibrary().create_enemy("enemy_basic_01")
    combat = CombatManager(player=player, enemies=[enemy])
    combat.start_combat()
    defend_card = next(card for card in player.deck_manager.hand if card.id == "defend_01")
    strike_card = next(card for card in player.deck_manager.hand if card.id == "strike_01")
    combat.resolve_action({"card": defend_card})
    combat.resolve_action({"card": strike_card, "target": enemy})
    return {
        "player_block_after_defend": player.block,
        "enemy_hp_after_strike": enemy.current_hp,
        "combat_state": combat.get_state(),
    }
