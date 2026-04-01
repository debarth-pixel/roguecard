from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import ENEMIES_DATA_PATH
from entities.enemy import Enemy, SUPPORTED_ENEMY_INTENTS


class EnemyLibrary:
    def __init__(self, data_path: Path = ENEMIES_DATA_PATH) -> None:
        self.data_path = data_path
        self._enemies: dict[str, dict[str, object]] = {}

    def load_enemies(self) -> dict[str, dict[str, object]]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("enemies.json must contain a list of enemy definitions.")

        definitions: dict[str, dict[str, object]] = {}
        for enemy_data in payload:
            if not isinstance(enemy_data, dict):
                raise ValueError("enemies.json entries must be enemy definition dictionaries.")

            enemy_id = enemy_data.get("id")
            name = enemy_data.get("name")
            max_hp = enemy_data.get("max_hp")
            intent_pattern = enemy_data.get("intent_pattern")

            if not isinstance(enemy_id, str) or not enemy_id:
                raise ValueError("Enemy id must be a non-empty string.")
            if not isinstance(name, str) or not name:
                raise ValueError("Enemy name must be a non-empty string.")
            if not isinstance(max_hp, int) or max_hp <= 0:
                raise ValueError("Enemy max_hp must be a positive integer.")
            if not isinstance(intent_pattern, list) or not intent_pattern or not all(
                isinstance(intent, str) and intent for intent in intent_pattern
            ):
                raise ValueError("Enemy intent_pattern must be a non-empty list of strings.")
            if any(intent not in SUPPORTED_ENEMY_INTENTS for intent in intent_pattern):
                raise ValueError(
                    f"Enemy {enemy_id} contains unsupported intents: {intent_pattern}"
                )
            if enemy_id in definitions:
                raise ValueError(f"Duplicate enemy id detected: {enemy_id}")

            definitions[enemy_id] = {
                "id": enemy_id,
                "name": name,
                "max_hp": max_hp,
                "intent_pattern": list(intent_pattern),
            }

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
            max_hp=enemy_data["max_hp"],
            intent_pattern=list(enemy_data["intent_pattern"]),
        )


def simulate_enemy_library() -> dict[str, Any]:
    library = EnemyLibrary()
    enemies = library.load_enemies()
    first_enemy = library.create_enemy("enemy_basic_01")
    second_enemy = library.create_enemy("enemy_basic_01")
    first_enemy.take_damage(6)
    return {
        "loaded_enemies": {enemy_id: enemy["name"] for enemy_id, enemy in enemies.items()},
        "independent_instances": [first_enemy.current_hp, second_enemy.current_hp],
    }
