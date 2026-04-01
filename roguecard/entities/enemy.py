from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import DEFAULT_ENEMY_ATTACK_DAMAGE, DEFAULT_ENEMY_DEFEND_BLOCK

SUPPORTED_ENEMY_INTENTS = {"attack", "defend"}


@dataclass
class Enemy:
    id: str
    name: str
    max_hp: int
    intent_pattern: list[str]
    current_hp: int = field(init=False)
    block: int = 0
    current_intent: str | None = None
    _intent_index: int = 0

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            raise ValueError("Enemy max_hp must be a positive integer.")
        if not self.intent_pattern:
            raise ValueError(f"Enemy {self.id} has no intent pattern.")
        if any(intent not in SUPPORTED_ENEMY_INTENTS for intent in self.intent_pattern):
            raise ValueError(
                f"Enemy {self.id} contains unsupported intents: {self.intent_pattern}"
            )
        self.current_hp = self.max_hp

    def reset_for_combat(self) -> None:
        self.current_hp = self.max_hp
        self.block = 0
        self.current_intent = None
        self._intent_index = 0

    def choose_intent(self) -> str:
        if not self.intent_pattern:
            raise ValueError(f"Enemy {self.id} has no intent pattern.")

        self.current_intent = self.intent_pattern[self._intent_index % len(self.intent_pattern)]
        self._intent_index += 1
        return self.current_intent

    def start_turn(self) -> None:
        self.block = 0

    def execute_intent(self, action_resolver: Any, target: Any) -> dict[str, Any]:
        if self.current_intent is None:
            self.choose_intent()

        action = self._intent_to_action(self.current_intent)
        resolution_target = self if self.current_intent == "defend" else target
        resolution = action_resolver.resolve(action=action, source=self, target=resolution_target)
        self.current_intent = None
        return resolution

    def gain_block(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Block gain cannot be negative.")
        self.block += amount

    def take_damage(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Damage cannot be negative.")

        absorbed = min(self.block, amount)
        self.block -= absorbed
        damage_taken = amount - absorbed
        self.current_hp = max(0, self.current_hp - damage_taken)
        return damage_taken

    def heal(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Healing cannot be negative.")
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def get_state(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "block": self.block,
            "current_intent": self.current_intent,
        }

    def _intent_to_action(self, intent: str) -> dict[str, Any]:
        if intent == "attack":
            return {"type": "damage", "value": DEFAULT_ENEMY_ATTACK_DAMAGE}
        if intent == "defend":
            return {"type": "block", "value": DEFAULT_ENEMY_DEFEND_BLOCK}
        raise ValueError(f"Unsupported enemy intent: {intent}")


def simulate_enemy() -> dict[str, Any]:
    from combat.action_resolver import ActionResolver
    from entities.player import Player

    enemy = Enemy(
        id="enemy_basic_01",
        name="Street Punk",
        max_hp=40,
        intent_pattern=["attack", "defend"],
    )
    player = Player()
    enemy.choose_intent()
    attack_resolution = enemy.execute_intent(ActionResolver(), player)
    enemy.choose_intent()
    defend_resolution = enemy.execute_intent(ActionResolver(), player)
    return {
        "attack_resolution": attack_resolution,
        "defend_resolution": defend_resolution,
        "enemy": enemy.get_state(),
        "player": player.get_state(),
    }
