from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Enemy:
    id: str
    name: str
    max_hp: int
    intent_pattern: list[str]
    moves: list[dict[str, Any]]
    faction_id: str = "legacy"
    role: str = "basic"
    tier: str = "normal"
    tags: list[str] = field(default_factory=list)
    bark_profile_id: str | None = None
    summon_ids: list[str] = field(default_factory=list)
    phase_rules: list[dict[str, Any]] = field(default_factory=list)
    death_effects: list[dict[str, Any]] = field(default_factory=list)
    ally_death_effects: list[dict[str, Any]] = field(default_factory=list)
    current_hp: int = field(init=False)
    block: int = 0
    current_intent: str | None = None
    strength: int = 0
    weak: int = 0
    vulnerable: int = 0
    _intent_index: int = 0
    _move_lookup: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _active_intent_pattern: list[str] = field(init=False, repr=False)
    _cooldowns: dict[str, int] = field(init=False, repr=False)
    _triggered_phase_names: set[str] = field(init=False, repr=False)
    _active_phase_name: str | None = field(init=False, default=None, repr=False)
    _low_hp_bark_fired: bool = field(init=False, default=False, repr=False)
    _status_counters: dict[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            raise ValueError("Enemy max_hp must be a positive integer.")
        if not self.intent_pattern:
            raise ValueError(f"Enemy {self.id} has no intent pattern.")
        if not self.moves:
            raise ValueError(f"Enemy {self.id} has no moves.")
        self._move_lookup = {}
        for move in self.moves:
            move_id = move.get("id")
            if not isinstance(move_id, str) or not move_id:
                raise ValueError(f"Enemy {self.id} has a move without a valid id.")
            if move_id in self._move_lookup:
                raise ValueError(f"Enemy {self.id} has a duplicate move id: {move_id}")
            self._move_lookup[move_id] = dict(move)
        for move_id in self.intent_pattern:
            if move_id not in self._move_lookup:
                raise ValueError(f"Enemy {self.id} intent_pattern references unknown move {move_id}.")
        for phase_rule in self.phase_rules:
            for move_id in phase_rule.get("intent_pattern", []):
                if move_id not in self._move_lookup:
                    raise ValueError(f"Enemy {self.id} phase rule references unknown move {move_id}.")

        self.current_hp = self.max_hp
        self._active_intent_pattern = list(self.intent_pattern)
        self._cooldowns = {}
        self._triggered_phase_names = set()
        self._status_counters = {}

    @property
    def is_boss(self) -> bool:
        return self.tier == "boss"

    def reset_for_combat(self) -> None:
        self.current_hp = self.max_hp
        self.block = 0
        self.current_intent = None
        self.strength = 0
        self.weak = 0
        self.vulnerable = 0
        self._intent_index = 0
        self._active_intent_pattern = list(self.intent_pattern)
        self._cooldowns = {}
        self._triggered_phase_names = set()
        self._active_phase_name = None
        self._low_hp_bark_fired = False
        self._status_counters = {}

    def start_turn(self) -> None:
        self.block = 0
        self.weak = max(0, self.weak - 1)
        self.vulnerable = max(0, self.vulnerable - 1)
        cooled_down: dict[str, int] = {}
        for move_id, turns in self._cooldowns.items():
            if turns > 1:
                cooled_down[move_id] = turns - 1
        self._cooldowns = cooled_down

    def choose_intent(self, combat_manager: Any = None) -> str:
        self.check_phase_transition()
        pattern = self._active_intent_pattern or self.intent_pattern
        pattern_size = len(pattern)
        if pattern_size == 0:
            raise ValueError(f"Enemy {self.id} has no active intent pattern.")

        start_index = self._intent_index
        for offset in range(pattern_size):
            move_index = (start_index + offset) % pattern_size
            move_id = pattern[move_index]
            move = self._move_lookup[move_id]
            if self._move_available(move, combat_manager):
                self.current_intent = move_id
                self._intent_index = move_index + 1
                return move_id

        fallback_move_id = pattern[start_index % pattern_size]
        self.current_intent = fallback_move_id
        self._intent_index = (start_index % pattern_size) + 1
        return fallback_move_id

    def execute_intent(
        self,
        action_resolver: Any,
        target: Any,
        combat_manager: Any = None,
    ) -> dict[str, Any]:
        if self.current_intent is None:
            self.choose_intent(combat_manager)

        move = self.current_move()
        if combat_manager is not None and hasattr(combat_manager, "resolve_enemy_intent"):
            resolution = combat_manager.resolve_enemy_intent(self, move, target, action_resolver)
        else:
            resolution = self._fallback_execute_intent(move, target, action_resolver)
        cooldown = int(move.get("cooldown", 0))
        if cooldown > 0:
            self._cooldowns[move["id"]] = cooldown + 1
        self.current_intent = None
        return resolution

    def current_move(self) -> dict[str, Any]:
        if self.current_intent is None:
            raise ValueError(f"Enemy {self.id} has not selected a current intent.")
        return dict(self._move_lookup[self.current_intent])

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

    def cleanse_debuffs(self, amount: int) -> int:
        if amount <= 0:
            return 0
        cleared = 0
        if self.weak > 0 and cleared < amount:
            clear_amount = min(self.weak, amount - cleared)
            self.weak -= clear_amount
            cleared += clear_amount
        if self.vulnerable > 0 and cleared < amount:
            clear_amount = min(self.vulnerable, amount - cleared)
            self.vulnerable -= clear_amount
            cleared += clear_amount
        return cleared

    def apply_status(self, status_id: str, amount: int) -> int:
        if not isinstance(status_id, str) or not status_id:
            raise ValueError("Enemy status ids must be non-empty strings.")
        if amount < 0:
            raise ValueError("Enemy status amounts cannot be negative.")
        self._status_counters[status_id] = max(0, self._status_counters.get(status_id, 0) + amount)
        return self._status_counters[status_id]

    def set_status(self, status_id: str, amount: int) -> int:
        if not isinstance(status_id, str) or not status_id:
            raise ValueError("Enemy status ids must be non-empty strings.")
        if amount < 0:
            raise ValueError("Enemy status amounts cannot be negative.")
        self._status_counters[status_id] = amount
        return amount

    def get_status(self, status_id: str) -> int:
        return max(0, int(self._status_counters.get(status_id, 0)))

    def consume_status(self, status_id: str, amount: int) -> int:
        if amount <= 0:
            return 0
        current = self.get_status(status_id)
        consumed = min(current, amount)
        remaining = current - consumed
        if remaining > 0:
            self._status_counters[status_id] = remaining
        else:
            self._status_counters.pop(status_id, None)
        return consumed

    def clear_status(self, status_id: str) -> None:
        self._status_counters.pop(status_id, None)

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def check_phase_transition(self) -> dict[str, Any] | None:
        if self.current_hp <= 0 or self.max_hp <= 0:
            return None
        hp_ratio = self.current_hp / self.max_hp
        for phase_rule in self.phase_rules:
            phase_name = phase_rule.get("name")
            threshold_ratio = float(phase_rule.get("threshold_ratio", 0.0))
            if not isinstance(phase_name, str) or not phase_name:
                continue
            if phase_name in self._triggered_phase_names:
                continue
            if hp_ratio <= threshold_ratio:
                self._triggered_phase_names.add(phase_name)
                self._active_phase_name = phase_name
                self._active_intent_pattern = list(phase_rule.get("intent_pattern", self.intent_pattern))
                return dict(phase_rule)
        return None

    def snapshot_runtime(self) -> dict[str, Any]:
        return {
            "intent_index": self._intent_index,
            "cooldowns": dict(self._cooldowns),
            "active_phase_name": self._active_phase_name,
            "triggered_phase_names": sorted(self._triggered_phase_names),
            "low_hp_bark_fired": self._low_hp_bark_fired,
            "statuses": dict(self._status_counters),
        }

    def restore_runtime(self, runtime_state: dict[str, Any]) -> None:
        self._intent_index = int(runtime_state.get("intent_index", 0))
        cooldowns = runtime_state.get("cooldowns", {})
        if isinstance(cooldowns, dict):
            self._cooldowns = {
                str(move_id): int(turns)
                for move_id, turns in cooldowns.items()
                if move_id in self._move_lookup and isinstance(turns, int) and turns > 0
            }
        else:
            self._cooldowns = {}

        triggered_phase_names = runtime_state.get("triggered_phase_names", [])
        if isinstance(triggered_phase_names, list):
            self._triggered_phase_names = {str(name) for name in triggered_phase_names}
        else:
            self._triggered_phase_names = set()
        active_phase_name = runtime_state.get("active_phase_name")
        self._active_phase_name = str(active_phase_name) if isinstance(active_phase_name, str) else None
        self._active_intent_pattern = list(self.intent_pattern)
        for phase_rule in self.phase_rules:
            if phase_rule.get("name") == self._active_phase_name:
                self._active_intent_pattern = list(phase_rule.get("intent_pattern", self.intent_pattern))
                break
        self._low_hp_bark_fired = bool(runtime_state.get("low_hp_bark_fired", False))
        statuses = runtime_state.get("statuses", {})
        if isinstance(statuses, dict):
            self._status_counters = {
                str(status_id): int(amount)
                for status_id, amount in statuses.items()
                if isinstance(status_id, str) and isinstance(amount, int) and amount > 0
            }
        else:
            self._status_counters = {}

    def mark_low_hp_bark_fired(self) -> None:
        self._low_hp_bark_fired = True

    def low_hp_bark_fired(self) -> bool:
        return self._low_hp_bark_fired

    def get_state(self) -> dict[str, Any]:
        move = None if self.current_intent is None else self._move_lookup[self.current_intent]
        intent_value = self._intent_value(move)
        return {
            "id": self.id,
            "name": self.name,
            "faction_id": self.faction_id,
            "role": self.role,
            "tier": self.tier,
            "tags": list(self.tags),
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "block": self.block,
            "current_intent": self.current_intent,
            "intent_value": intent_value,
            "intent_category": self._intent_category(move),
            "intent_summary": self._intent_summary(move),
            "strength": self.strength,
            "weak": self.weak,
            "vulnerable": self.vulnerable,
            "phase_name": self._active_phase_name,
            "cooldowns": dict(self._cooldowns),
            "statuses": dict(self._status_counters),
        }

    def _move_available(self, move: dict[str, Any], combat_manager: Any) -> bool:
        if self._cooldowns.get(move["id"], 0) > 0:
            return False
        conditions = move.get("conditions", {})
        if not isinstance(conditions, dict) or not conditions:
            return True
        return self._conditions_met(conditions, combat_manager)

    def _conditions_met(self, conditions: dict[str, Any], combat_manager: Any) -> bool:
        if combat_manager is None:
            return False

        player = getattr(combat_manager, "player", None)
        for key, value in conditions.items():
            if key == "any_ally_missing_hp":
                if not combat_manager.any_ally_missing_hp(self):
                    return False
            elif key == "any_ally_debuffed":
                if not combat_manager.any_ally_debuffed(self):
                    return False
            elif key == "any_other_ally_present":
                if not combat_manager.any_other_ally_present(self):
                    return False
            elif key == "living_enemies_below":
                if combat_manager.living_enemy_count() >= int(value):
                    return False
            elif key == "player_hp_below_ratio":
                if player is None or player.max_hp <= 0 or (player.current_hp / player.max_hp) >= float(value):
                    return False
            elif key == "self_hp_below_ratio":
                if self.max_hp <= 0 or (self.current_hp / self.max_hp) >= float(value):
                    return False
            elif key == "player_status_at_least":
                if not isinstance(value, dict):
                    return False
                status_id = value.get("status")
                minimum = int(value.get("value", 0))
                if not isinstance(status_id, str) or player is None:
                    return False
                if getattr(player, f"{status_id}", 0) < minimum:
                    return False
            elif key == "player_cards_played_last_turn_at_least":
                if combat_manager.player_cards_played_last_turn() < int(value):
                    return False
            elif key == "allies_attacked_this_turn_at_least":
                if combat_manager.allies_attacked_this_turn(self) < int(value):
                    return False
            elif key == "ally_id_present":
                if not isinstance(value, str) or not combat_manager.ally_id_present(self, value):
                    return False
            elif key == "self_status_at_least":
                if not isinstance(value, dict):
                    return False
                status_id = value.get("status")
                minimum = int(value.get("value", 0))
                if not isinstance(status_id, str):
                    return False
                if self.get_status(status_id) < minimum:
                    return False
        return True

    def _fallback_execute_intent(
        self,
        move: dict[str, Any],
        target: Any,
        action_resolver: Any,
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for effect in move.get("effects", []):
            effect_type = effect.get("type")
            if effect_type == "enemy_damage":
                results.append(
                    action_resolver.resolve(
                        {"type": "damage", "value": int(effect.get("value", 0))},
                        source=self,
                        target=target,
                    )
                )
            elif effect_type == "enemy_block":
                results.append(
                    action_resolver.resolve(
                        {"type": "block", "value": int(effect.get("value", 0))},
                        source=self,
                        target=self,
                    )
                )
        return {
            "intent_id": move["id"],
            "target": getattr(target, "id", "player"),
            "resolutions": results,
            "summary": move.get("intent_text", move["id"]),
        }

    def _intent_value(self, move: dict[str, Any] | None) -> int | None:
        if move is None:
            return None
        total = 0
        for effect in move.get("effects", []):
            if effect.get("type") == "enemy_damage":
                count = int(effect.get("count", 1))
                total += self._outgoing_attack_damage(int(effect.get("value", 0))) * count
        return total if total > 0 else None

    def _intent_summary(self, move: dict[str, Any] | None) -> str:
        if move is None:
            return "Waiting"
        return str(move.get("intent_text", move["id"]))

    def _intent_category(self, move: dict[str, Any] | None) -> str:
        if move is None:
            return "waiting"
        effect_types = {effect.get("type") for effect in move.get("effects", [])}
        if "enemy_damage" in effect_types:
            return "attack"
        if "enemy_block" in effect_types:
            return "defend"
        return "support"

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
        faction_id="legacy",
        role="basic",
        tier="normal",
        tags=["legacy"],
        bark_profile_id=None,
        intent_pattern=["jab", "brace"],
        moves=[
            {
                "id": "jab",
                "intent_text": "Attack for 6",
                "target": "player",
                "effects": [{"type": "enemy_damage", "value": 6}],
            },
            {
                "id": "brace",
                "intent_text": "Gain 5 Block",
                "target": "self",
                "effects": [{"type": "enemy_block", "value": 5}],
            },
        ],
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
