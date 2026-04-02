from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    deck_manager: DeckManager | None = None

    def attach_deck(self, deck_manager: DeckManager) -> None:
        self.deck_manager = deck_manager

    def start_combat(self) -> None:
        self.block = 0
        self.energy = self.max_energy
        if self.deck_manager is not None:
            self.deck_manager.reset_for_combat()

    def start_turn(self) -> None:
        self.block = 0
        self.energy = self.max_energy

    def spend_energy(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Energy cost cannot be negative.")
        if amount > self.energy:
            raise ValueError("Not enough energy to play the requested card.")
        self.energy -= amount

    def gain_block(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Block gain cannot be negative.")
        self.block += amount
        return amount

    def take_damage(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Damage cannot be negative.")

        absorbed = min(self.block, amount)
        self.block -= absorbed
        damage_taken = amount - absorbed
        self.current_hp = max(0, self.current_hp - damage_taken)
        return damage_taken

    def heal(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Healing cannot be negative.")
        healed = min(self.max_hp - self.current_hp, amount)
        self.current_hp += healed
        return healed

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

    def get_state(self) -> dict[str, Any]:
        state = {
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "max_energy": self.max_energy,
            "energy": self.energy,
            "block": self.block,
            "draw_per_turn": self.draw_per_turn,
            "credits": self.credits,
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


def simulate_player() -> dict[str, Any]:
    player = Player()
    player.energy = 0
    player.start_turn()
    player.gain_block(5)
    player.gain_credits(20)
    player.spend_credits(5)
    damage_taken = player.take_damage(8)
    return {
        "damage_taken": damage_taken,
        "energy_after_reset": player.energy,
        "credits": player.credits,
        "state": player.get_state(),
    }
