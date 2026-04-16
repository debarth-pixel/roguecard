from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

from config import OUTSKIRTS_ENCOUNTERS_DATA_PATH


class OutskirtsContentLibrary:
    def __init__(self, encounters_path: Path = OUTSKIRTS_ENCOUNTERS_DATA_PATH) -> None:
        self.encounters_path = encounters_path
        self._generation: dict[str, Any] = {}
        self._regions: dict[str, dict[str, Any]] = {}

    def load(self) -> None:
        if self._regions:
            return

        with self.encounters_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("outskirts_encounters.json must contain an object.")

        generation = payload.get("generation")
        regions = payload.get("regions")
        if not isinstance(generation, dict):
            raise ValueError("outskirts_encounters.json must define generation rules.")
        if not isinstance(regions, list) or not regions:
            raise ValueError("outskirts_encounters.json must define regions.")

        loaded_regions: dict[str, dict[str, Any]] = {}
        max_enemies = int(generation.get("max_enemies", 5))
        for region in regions:
            if not isinstance(region, dict):
                raise ValueError("Outskirts regions must be dictionaries.")
            region_id = region.get("id")
            if not isinstance(region_id, str) or not region_id:
                raise ValueError("Outskirts regions must define a non-empty id.")
            encounters = region.get("encounters")
            if not isinstance(encounters, list) or not encounters:
                raise ValueError(f"Outskirts region {region_id} must define encounters.")
            for encounter in encounters:
                enemy_ids = encounter.get("enemy_ids")
                if (
                    not isinstance(enemy_ids, list)
                    or not enemy_ids
                    or len(enemy_ids) > max_enemies
                    or not all(isinstance(enemy_id, str) and enemy_id for enemy_id in enemy_ids)
                ):
                    raise ValueError(f"Outskirts encounter {encounter.get('id')} has invalid enemy_ids.")
            loaded_regions[region_id] = copy.deepcopy(region)

        self._generation = copy.deepcopy(generation)
        self._regions = loaded_regions

    def choose_encounter(
        self,
        region_id: str,
        *,
        node_type: str,
        route_floor: int,
        rng: random.Random,
    ) -> dict[str, Any]:
        self.load()
        if node_type not in {"combat", "elite"}:
            raise ValueError(f"Unsupported outskirts encounter node type: {node_type}")
        try:
            region = self._regions[region_id]
        except KeyError as error:
            raise KeyError(f"Unknown outskirts region id: {region_id}") from error

        difficulty_weights = self._difficulty_weights(node_type=node_type, route_floor=route_floor)
        weighted_encounters: list[tuple[dict[str, Any], float]] = []
        for encounter in region["encounters"]:
            if node_type not in encounter.get("node_types", []):
                continue
            difficulty = str(encounter.get("difficulty", ""))
            weight = float(encounter.get("weight", 1.0)) * difficulty_weights.get(difficulty, 0.0)
            if weight <= 0:
                continue
            weighted_encounters.append((encounter, weight))

        if not weighted_encounters:
            raise ValueError(
                f"No outskirts encounters available for {region_id} {node_type} floor {route_floor}."
            )

        total_weight = sum(weight for _, weight in weighted_encounters)
        roll = rng.random() * total_weight
        running_total = 0.0
        for encounter, weight in weighted_encounters:
            running_total += weight
            if roll <= running_total:
                return copy.deepcopy(encounter)
        return copy.deepcopy(weighted_encounters[-1][0])

    def _difficulty_weights(self, *, node_type: str, route_floor: int) -> dict[str, float]:
        key = "elite_bands" if node_type == "elite" else "combat_bands"
        bands = self._generation.get(key, [])
        if not isinstance(bands, list) or not bands:
            raise ValueError("Outskirts generation rules are missing encounter bands.")
        for band in bands:
            if route_floor <= int(band.get("max_floor", 0)):
                return {
                    str(difficulty): float(weight)
                    for difficulty, weight in dict(band.get("difficulty_weights", {})).items()
                }
        return {
            str(difficulty): float(weight)
            for difficulty, weight in dict(bands[-1].get("difficulty_weights", {})).items()
        }


def simulate_outskirts_content_library() -> dict[str, Any]:
    library = OutskirtsContentLibrary()
    encounter = library.choose_encounter(
        "outskirts",
        node_type="combat",
        route_floor=4,
        rng=random.Random(13),
    )
    return {
        "encounter_id": encounter["id"],
        "enemy_count": len(encounter["enemy_ids"]),
    }
