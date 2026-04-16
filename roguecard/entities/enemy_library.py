from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from config import ENEMIES_DATA_PATH
from entities.enemy import Enemy

ALLOWED_ENEMY_TIERS = {"normal", "elite", "boss"}


class EnemyLibrary:
    def __init__(self, data_path: Path = ENEMIES_DATA_PATH) -> None:
        self.data_path = data_path
        self._enemies: dict[str, dict[str, Any]] = {}

    def load_enemies(self) -> dict[str, dict[str, Any]]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("enemies.json must contain a list of enemy definitions.")

        definitions: dict[str, dict[str, Any]] = {}
        for enemy_data in payload:
            if not isinstance(enemy_data, dict):
                raise ValueError("enemies.json entries must be enemy definition dictionaries.")
            normalized = self._validate_enemy(enemy_data)
            enemy_id = normalized["id"]
            if enemy_id in definitions:
                raise ValueError(f"Duplicate enemy id detected: {enemy_id}")
            definitions[enemy_id] = normalized

        self._enemies = definitions
        return self._enemies

    def create_enemy(self, enemy_id: str) -> Enemy:
        if not self._enemies:
            self.load_enemies()

        try:
            enemy_data = self._enemies[enemy_id]
        except KeyError as error:
            raise KeyError(f"Unknown enemy id: {enemy_id}") from error

        return Enemy(
            id=enemy_data["id"],
            name=enemy_data["name"],
            faction_id=enemy_data["faction_id"],
            role=enemy_data["role"],
            tier=enemy_data["tier"],
            tags=list(enemy_data["tags"]),
            max_hp=enemy_data["max_hp"],
            bark_profile_id=enemy_data["bark_profile_id"],
            intent_pattern=list(enemy_data["intent_pattern"]),
            moves=copy.deepcopy(enemy_data["moves"]),
            summon_ids=list(enemy_data.get("summon_ids", [])),
            phase_rules=copy.deepcopy(enemy_data.get("phase_rules", [])),
            death_effects=copy.deepcopy(enemy_data.get("death_effects", [])),
            ally_death_effects=copy.deepcopy(enemy_data.get("ally_death_effects", [])),
        )

    def _validate_enemy(self, enemy_data: dict[str, Any]) -> dict[str, Any]:
        enemy_id = self._require_text(enemy_data.get("id"), "Enemy id")
        name = self._require_text(enemy_data.get("name"), f"Enemy {enemy_id} name")
        faction_id = self._require_text(enemy_data.get("faction_id"), f"Enemy {enemy_id} faction_id")
        role = self._require_text(enemy_data.get("role"), f"Enemy {enemy_id} role")
        tier = self._require_text(enemy_data.get("tier"), f"Enemy {enemy_id} tier")
        if tier not in ALLOWED_ENEMY_TIERS:
            raise ValueError(f"Enemy {enemy_id} has unsupported tier: {tier}")

        max_hp = enemy_data.get("max_hp")
        if not isinstance(max_hp, int) or max_hp <= 0:
            raise ValueError(f"Enemy {enemy_id} max_hp must be a positive integer.")

        tags = enemy_data.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError(f"Enemy {enemy_id} tags must be a list of non-empty strings.")

        bark_profile_id = enemy_data.get("bark_profile_id")
        if bark_profile_id is not None and (not isinstance(bark_profile_id, str) or not bark_profile_id):
            raise ValueError(f"Enemy {enemy_id} bark_profile_id must be a non-empty string when present.")

        intent_pattern = enemy_data.get("intent_pattern")
        if (
            not isinstance(intent_pattern, list)
            or not intent_pattern
            or not all(isinstance(intent, str) and intent for intent in intent_pattern)
        ):
            raise ValueError(f"Enemy {enemy_id} intent_pattern must be a non-empty list of move ids.")

        moves = enemy_data.get("moves")
        if not isinstance(moves, list) or not moves:
            raise ValueError(f"Enemy {enemy_id} must define a non-empty moves list.")
        move_ids: set[str] = set()
        normalized_moves: list[dict[str, Any]] = []
        for move in moves:
            if not isinstance(move, dict):
                raise ValueError(f"Enemy {enemy_id} moves must be dictionaries.")
            move_id = self._require_text(move.get("id"), f"Enemy {enemy_id} move id")
            if move_id in move_ids:
                raise ValueError(f"Enemy {enemy_id} has duplicate move id {move_id}.")
            move_ids.add(move_id)
            normalized_moves.append(self._validate_move(enemy_id, move))
        if any(move_id not in move_ids for move_id in intent_pattern):
            raise ValueError(f"Enemy {enemy_id} intent_pattern references an unknown move.")

        summon_ids = enemy_data.get("summon_ids", [])
        if not isinstance(summon_ids, list) or not all(
            isinstance(summon_id, str) and summon_id for summon_id in summon_ids
        ):
            raise ValueError(f"Enemy {enemy_id} summon_ids must be a list of non-empty strings.")

        phase_rules = enemy_data.get("phase_rules", [])
        if not isinstance(phase_rules, list):
            raise ValueError(f"Enemy {enemy_id} phase_rules must be a list.")
        normalized_phase_rules: list[dict[str, Any]] = []
        for phase_rule in phase_rules:
            if not isinstance(phase_rule, dict):
                raise ValueError(f"Enemy {enemy_id} phase rules must be dictionaries.")
            phase_name = self._require_text(phase_rule.get("name"), f"Enemy {enemy_id} phase name")
            threshold_ratio = phase_rule.get("threshold_ratio")
            if not isinstance(threshold_ratio, (int, float)) or threshold_ratio <= 0 or threshold_ratio >= 1:
                raise ValueError(f"Enemy {enemy_id} phase {phase_name} threshold_ratio must be between 0 and 1.")
            phase_pattern = phase_rule.get("intent_pattern")
            if (
                not isinstance(phase_pattern, list)
                or not phase_pattern
                or not all(isinstance(move_id, str) and move_id in move_ids for move_id in phase_pattern)
            ):
                raise ValueError(f"Enemy {enemy_id} phase {phase_name} must use known move ids.")
            normalized_phase_rules.append(
                {
                    "name": phase_name,
                    "threshold_ratio": float(threshold_ratio),
                    "intent_pattern": list(phase_pattern),
                    "bark_trigger": phase_rule.get("bark_trigger"),
                }
            )

        return {
            "id": enemy_id,
            "name": name,
            "faction_id": faction_id,
            "role": role,
            "tier": tier,
            "tags": list(tags),
            "max_hp": max_hp,
            "bark_profile_id": bark_profile_id,
            "intent_pattern": list(intent_pattern),
            "moves": normalized_moves,
            "summon_ids": list(summon_ids),
            "phase_rules": normalized_phase_rules,
            "death_effects": self._validate_effect_list(enemy_id, enemy_data.get("death_effects", []), "death_effects"),
            "ally_death_effects": self._validate_effect_list(enemy_id, enemy_data.get("ally_death_effects", []), "ally_death_effects"),
        }

    def _validate_move(self, enemy_id: str, move: dict[str, Any]) -> dict[str, Any]:
        move_id = self._require_text(move.get("id"), f"Enemy {enemy_id} move id")
        intent_text = self._require_text(move.get("intent_text"), f"Enemy {enemy_id} move {move_id} intent_text")
        target = self._require_text(move.get("target"), f"Enemy {enemy_id} move {move_id} target")
        cooldown = move.get("cooldown", 0)
        if not isinstance(cooldown, int) or cooldown < 0:
            raise ValueError(f"Enemy {enemy_id} move {move_id} cooldown must be a non-negative integer.")
        conditions = move.get("conditions", {})
        if not isinstance(conditions, dict):
            raise ValueError(f"Enemy {enemy_id} move {move_id} conditions must be a dictionary.")
        return {
            "id": move_id,
            "intent_text": intent_text,
            "target": target,
            "cooldown": cooldown,
            "conditions": copy.deepcopy(conditions),
            "bark_trigger": move.get("bark_trigger"),
            "effects": self._validate_effect_list(enemy_id, move.get("effects", []), f"move {move_id} effects"),
        }

    def _validate_effect_list(
        self,
        enemy_id: str,
        effects: Any,
        label: str,
    ) -> list[dict[str, Any]]:
        if effects in (None, []):
            return []
        if not isinstance(effects, list):
            raise ValueError(f"Enemy {enemy_id} {label} must be a list.")
        normalized: list[dict[str, Any]] = []
        for effect in effects:
            if not isinstance(effect, dict):
                raise ValueError(f"Enemy {enemy_id} {label} entries must be dictionaries.")
            effect_type = self._require_text(effect.get("type"), f"Enemy {enemy_id} {label} effect type")
            value = effect.get("value", 0)
            if not isinstance(value, int):
                raise ValueError(f"Enemy {enemy_id} {label} effect {effect_type} must use an integer value.")
            normalized_effect = {"type": effect_type, "value": value}
            for optional_key in {"target", "enemy_id", "summary", "card_id", "pile"}:
                if optional_key in effect:
                    normalized_effect[optional_key] = effect[optional_key]
            if "count" in effect:
                count = effect["count"]
                if not isinstance(count, int) or count <= 0:
                    raise ValueError(f"Enemy {enemy_id} {label} effect {effect_type} count must be positive.")
                normalized_effect["count"] = count
            normalized.append(normalized_effect)
        return normalized

    def _require_text(self, value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be a non-empty string.")
        return value.strip()


def simulate_enemy_library() -> dict[str, Any]:
    library = EnemyLibrary()
    enemies = library.load_enemies()
    first_enemy = library.create_enemy("enemy_basic_01")
    second_enemy = library.create_enemy("enemy_basic_01")
    first_enemy.take_damage(6)
    return {
        "loaded_enemy_count": len(enemies),
        "independent_instances": [first_enemy.current_hp, second_enemy.current_hp],
        "has_grayspine_boss": "miremother_vexa" in enemies,
    }
