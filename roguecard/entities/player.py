from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cards.card_base import CardBase
from cards.deck_manager import DeckManager
from config import (
    PLAYER_STARTING_CREDITS,
    PLAYER_STARTING_DRAW,
    PLAYER_STARTING_ENERGY,
    PLAYER_STARTING_HP,
)


@dataclass
class Player:
    max_hp: int = PLAYER_STARTING_HP
    current_hp: int = PLAYER_STARTING_HP
    max_energy: int = PLAYER_STARTING_ENERGY
    energy: int = PLAYER_STARTING_ENERGY
    block: int = 0
    draw_per_turn: int = PLAYER_STARTING_DRAW
    credits: int = PLAYER_STARTING_CREDITS
    healing_multiplier: float = 1.0
    resources: dict[str, dict[str, int]] = field(default_factory=dict)
    deck_manager: DeckManager | None = None
    character_id: str | None = None
    strength: int = 0
    weak: int = 0
    vulnerable: int = 0
    next_card_cost_delta: int = 0
    next_attack_bonus: int = 0
    active_powers: list[CardBase] = field(default_factory=list)
    temporary_combat_cards: list[CardBase] = field(default_factory=list)
    first_card_played: bool = False
    first_attack_played: bool = False

    def __post_init__(self) -> None:
        self.resources = self._normalized_additional_resources(self.resources)

    def attach_deck(self, deck_manager: DeckManager) -> None:
        self.deck_manager = deck_manager

    def start_combat(self) -> None:
        self.block = 0
        self.energy = self.max_energy
        self.strength = 0
        self.weak = 0
        self.vulnerable = 0
        self.next_card_cost_delta = 0
        self.next_attack_bonus = 0
        self.active_powers = []
        self.temporary_combat_cards = []
        self.first_card_played = False
        self.first_attack_played = False
        if self.deck_manager is not None:
            self.deck_manager.reset_for_combat()

    def start_turn(self) -> None:
        self.block = 0
        self.energy = self.max_energy
        self.next_card_cost_delta = 0
        self.next_attack_bonus = 0
        self.first_card_played = False
        self.first_attack_played = False
        self._tick_statuses()

    def end_combat(self) -> None:
        self.block = 0
        self.energy = self.max_energy
        self.strength = 0
        self.weak = 0
        self.vulnerable = 0
        self.next_card_cost_delta = 0
        self.next_attack_bonus = 0
        self.active_powers = []
        self.temporary_combat_cards = []
        self.first_card_played = False
        self.first_attack_played = False

    def spend_energy(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Energy cost cannot be negative.")
        if amount > self.energy:
            raise ValueError("Not enough energy to play the requested card.")
        self.energy -= amount

    def gain_energy(self, amount: int) -> int:
        if not isinstance(amount, int):
            raise ValueError("Energy changes must be integers.")
        self.energy = max(0, self.energy + amount)
        return amount

    def gain_block(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Block gain cannot be negative.")
        self.block += amount
        return amount

    def lose_block(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Block loss cannot be negative.")
        lost = min(self.block, amount)
        self.block -= lost
        return lost

    def take_damage(self, amount: int, *, ignore_block: bool = False) -> int:
        if amount < 0:
            raise ValueError("Damage cannot be negative.")

        absorbed = 0
        if not ignore_block:
            absorbed = min(self.block, amount)
            self.block -= absorbed
        damage_taken = amount - absorbed
        self.current_hp = max(0, self.current_hp - damage_taken)
        return damage_taken

    def lose_hp(self, amount: int) -> int:
        return self.take_damage(amount, ignore_block=True)

    def heal(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Healing cannot be negative.")
        effective_amount = max(0, int(round(amount * self.healing_multiplier)))
        healed = min(self.max_hp - self.current_hp, effective_amount)
        self.current_hp += healed
        return healed

    def adjust_strength(self, amount: int) -> int:
        if not isinstance(amount, int):
            raise ValueError("Strength changes must be integers.")
        self.strength = max(0, self.strength + amount)
        return self.strength

    def apply_weak(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Weak amount cannot be negative.")
        self.weak += amount
        return self.weak

    def apply_vulnerable(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Vulnerable amount cannot be negative.")
        self.vulnerable += amount
        return self.vulnerable

    def adjust_next_card_cost(self, delta: int) -> int:
        if not isinstance(delta, int):
            raise ValueError("Card cost modifiers must be integers.")
        self.next_card_cost_delta += delta
        return self.next_card_cost_delta

    def adjust_next_attack_damage(self, amount: int) -> int:
        if not isinstance(amount, int):
            raise ValueError("Attack damage modifiers must be integers.")
        self.next_attack_bonus += amount
        return self.next_attack_bonus

    def consume_next_card_cost_delta(self) -> int:
        amount = self.next_card_cost_delta
        self.next_card_cost_delta = 0
        return amount

    def consume_next_attack_bonus(self) -> int:
        amount = self.next_attack_bonus
        self.next_attack_bonus = 0
        return amount

    def adjust_max_hp(self, amount: int) -> int:
        if not isinstance(amount, int):
            raise ValueError("Max HP adjustment must be an integer.")
        previous_max_hp = self.max_hp
        self.max_hp = max(1, self.max_hp + amount)
        self.current_hp = min(self.current_hp, self.max_hp)
        return self.max_hp - previous_max_hp

    def adjust_healing_multiplier(self, percent_delta: int) -> float:
        if not isinstance(percent_delta, int):
            raise ValueError("Healing multiplier changes must be integer percents.")
        self.healing_multiplier = max(0.1, self.healing_multiplier + (percent_delta / 100.0))
        return self.healing_multiplier

    def add_active_power(self, card: CardBase) -> None:
        self.active_powers.append(card)

    def add_temporary_combat_card(self, card: CardBase) -> None:
        self.temporary_combat_cards.append(card)

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def gain_credits(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Credit gain cannot be negative.")
        self.credits += amount
        return amount

    def spend_credits(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Credit spend cannot be negative.")
        if amount > self.credits:
            raise ValueError("Not enough credits for that purchase.")
        self.credits -= amount
        return amount

    def snapshot_resources(self) -> dict[str, dict[str, int]]:
        snapshot = {
            "energy": {
                "current": self.energy,
                "max": self.max_energy,
            }
        }
        for resource_id, resource_state in self.resources.items():
            snapshot[resource_id] = {
                "current": resource_state["current"],
                "max": resource_state["max"],
            }
        return snapshot

    def get_state(self) -> dict[str, Any]:
        state = {
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "max_energy": self.max_energy,
            "energy": self.energy,
            "block": self.block,
            "draw_per_turn": self.draw_per_turn,
            "credits": self.credits,
            "healing_multiplier": round(self.healing_multiplier, 2),
            "resources": self.snapshot_resources(),
            "character_id": self.character_id,
            "strength": self.strength,
            "weak": self.weak,
            "vulnerable": self.vulnerable,
            "next_card_cost_delta": self.next_card_cost_delta,
            "next_attack_bonus": self.next_attack_bonus,
            "active_powers": [card.to_dict() for card in self.active_powers],
            "temporary_combat_cards": [card.to_dict() for card in self.temporary_combat_cards],
        }
        if self.deck_manager is not None:
            state.update(
                {
                    "draw_pile": len(self.deck_manager.draw_pile),
                    "discard_pile": len(self.deck_manager.discard_pile),
                    "exhaust_pile": len(self.deck_manager.exhaust_pile),
                    "hand_size": len(self.deck_manager.hand),
                }
            )
        return state

    def _tick_statuses(self) -> None:
        self.weak = max(0, self.weak - 1)
        self.vulnerable = max(0, self.vulnerable - 1)

    def _normalized_additional_resources(
        self,
        resources: dict[str, Any],
    ) -> dict[str, dict[str, int]]:
        if not isinstance(resources, dict):
            raise ValueError("Player resources must be a dictionary.")

        normalized: dict[str, dict[str, int]] = {}
        for resource_id, resource_state in resources.items():
            if resource_id == "energy":
                continue
            if not isinstance(resource_id, str) or not resource_id:
                raise ValueError("Player resource ids must be non-empty strings.")
            if not isinstance(resource_state, dict):
                raise ValueError("Player resource states must be dictionaries.")

            current = resource_state.get("current")
            maximum = resource_state.get("max")
            if not isinstance(current, int) or current < 0:
                raise ValueError("Player resource current values must be non-negative integers.")
            if not isinstance(maximum, int) or maximum < 0:
                raise ValueError("Player resource max values must be non-negative integers.")
            normalized[resource_id] = {
                "current": current,
                "max": maximum,
            }
        return normalized


def simulate_player() -> dict[str, Any]:
    player = Player(resources={"heat": {"current": 1, "max": 3}}, character_id="operator")
    player.energy = 0
    player.start_turn()
    player.adjust_healing_multiplier(-25)
    player.gain_block(5)
    player.gain_credits(20)
    player.spend_credits(5)
    player.adjust_strength(2)
    player.apply_vulnerable(1)
    damage_taken = player.take_damage(8)
    player.current_hp = 40
    healed = player.heal(12)
    return {
        "damage_taken": damage_taken,
        "energy_after_reset": player.energy,
        "credits": player.credits,
        "healed": healed,
        "state": player.get_state(),
    }
