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
    strength: int = 0
    weak: int = 0
    vulnerable: int = 0
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
        self.strength = 0
        self.weak = 0
        self.vulnerable = 0
        self._intent_index = 0

    def choose_intent(self) -> str:
        if not self.intent_pattern:
            raise ValueError(f"Enemy {self.id} has no intent pattern.")

        self.current_intent = self.intent_pattern[self._intent_index % len(self.intent_pattern)]
        self._intent_index += 1
        return self.current_intent

    def start_turn(self) -> None:
        self.block = 0
        self.weak = max(0, self.weak - 1)
        self.vulnerable = max(0, self.vulnerable - 1)

    def execute_intent(self, action_resolver: Any, target: Any, combat_manager: Any = None) -> dict[str, Any]:
        if self.current_intent is None:
            self.choose_intent()

        action = self._intent_to_action(self.current_intent)
        resolution_target = self if self.current_intent == "defend" else target
        resolution = action_resolver.resolve(
            action=action,
            source=self,
            target=resolution_target,
            combat_manager=combat_manager,
        )
        self.current_intent = None
        return resolution

    def gain_block(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("Block gain cannot be negative.")
        self.block += amount
        return amount

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
        healed = min(self.max_hp - self.current_hp, amount)
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

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def get_state(self) -> dict[str, Any]:
        intent_value = self._intent_value(self.current_intent)
        return {
            "id": self.id,
            "name": self.name,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "block": self.block,
            "current_intent": self.current_intent,
            "intent_value": intent_value,
            "intent_summary": self._intent_summary(self.current_intent, intent_value),
            "strength": self.strength,
            "weak": self.weak,
            "vulnerable": self.vulnerable,
        }

    def _intent_to_action(self, intent: str) -> dict[str, Any]:
        if intent == "attack":
            return {"type": "damage", "value": DEFAULT_ENEMY_ATTACK_DAMAGE}
        if intent == "defend":
            return {"type": "block", "value": DEFAULT_ENEMY_DEFEND_BLOCK}
        raise ValueError(f"Unsupported enemy intent: {intent}")

    def _intent_value(self, intent: str | None) -> int | None:
        if intent == "attack":
            return self._outgoing_attack_damage(DEFAULT_ENEMY_ATTACK_DAMAGE)
        if intent == "defend":
            return DEFAULT_ENEMY_DEFEND_BLOCK
        return None

    def _intent_summary(self, intent: str | None, value: int | None) -> str:
        if intent is None:
            return "Waiting"
        if value is None:
            return intent.title()
        if intent == "attack":
            return f"Attack for {value}"
        if intent == "defend":
            return f"Gain {value} Block"
        return intent.title()

    def _outgoing_attack_damage(self, base_value: int) -> int:
        amount = max(0, base_value + self.strength)
        if self.weak > 0:
            amount = max(0, int(amount * 0.75))
        return amount


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
    enemy.apply_weak(1)
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
