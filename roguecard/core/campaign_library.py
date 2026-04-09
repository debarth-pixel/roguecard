from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

from config import CAMPAIGN_MAPS_DATA_PATH
from core.grayspine_content_library import GrayspineContentLibrary

ALLOWED_CAMPAIGN_MAP_IDS = {
    "outskirts",
    "city_streets",
    "helix_ward_depths",
    "blackwire_lockdown_sector",
    "cinder_jackals_edgeworks",
}
ALLOWED_BRANCH_FACTIONS = {"helix_ward", "blackwire_directorate", "cinder_jackals"}
ALLOWED_NEXT_MAP_TYPES = {"fixed", "branch_from_boss", "victory"}
ALLOWED_NODE_WEIGHT_TYPES = {"combat", "event", "shop", "elite"}


class CampaignLibrary:
    def __init__(
        self,
        data_path: Path = CAMPAIGN_MAPS_DATA_PATH,
        grayspine_content: GrayspineContentLibrary | None = None,
    ) -> None:
        self.data_path = data_path
        self.grayspine_content = grayspine_content or GrayspineContentLibrary()
        self._maps: dict[str, dict[str, Any]] = {}

    def load_maps(self) -> dict[str, dict[str, Any]]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("campaign_maps.json must contain a list of map definitions.")

        loaded_maps: dict[str, dict[str, Any]] = {}
        for raw_map in payload:
            map_definition = self._validate_map(raw_map)
            if map_definition["id"] in loaded_maps:
                raise ValueError(f"Duplicate campaign map id detected: {map_definition['id']}")
            loaded_maps[map_definition["id"]] = map_definition

        self._maps = loaded_maps
        return self._maps

    def get_map_definition(self, map_id: str) -> dict[str, Any]:
        if not self._maps:
            self.load_maps()
        try:
            return copy.deepcopy(self._maps[map_id])
        except KeyError as error:
            raise KeyError(f"Unknown campaign map id: {map_id}") from error

    def list_maps(self) -> list[dict[str, Any]]:
        if not self._maps:
            self.load_maps()
        return [copy.deepcopy(map_definition) for map_definition in self._maps.values()]

    def choose_boss(self, map_id: str, rng: random.Random) -> dict[str, Any]:
        map_definition = self.get_map_definition(map_id)
        boss_pool = map_definition["boss_pool"]
        if len(boss_pool) == 1:
            return boss_pool[0]

        weighted_pool = [
            (boss, max(0.01, float(boss.get("base_weight", 1.0))))
            for boss in boss_pool
        ]
        total_weight = sum(weight for _, weight in weighted_pool)
        roll = rng.random() * total_weight
        running_total = 0.0
        for boss, weight in weighted_pool:
            running_total += weight
            if roll <= running_total:
                return boss
        return weighted_pool[-1][0]

    def next_map_id_for_boss(
        self,
        map_id: str,
        selected_boss: dict[str, Any],
    ) -> str | None:
        map_definition = self.get_map_definition(map_id)
        next_map = map_definition["next_map"]
        next_type = next_map["type"]
        if next_type == "victory":
            return None
        if next_type == "fixed":
            return next_map["map_id"]
        branch_faction = selected_boss.get("branch_faction")
        if branch_faction not in next_map["branches"]:
            raise ValueError(
                f"Boss {selected_boss['id']} on map {map_id} does not resolve to a branch map."
            )
        return next_map["branches"][branch_faction]

    def map_branch_faction(self, map_id: str) -> str | None:
        return self.get_map_definition(map_id).get("branch_faction")

    def _validate_map(self, map_data: Any) -> dict[str, Any]:
        if not isinstance(map_data, dict):
            raise ValueError("Campaign map definitions must be dictionaries.")

        required_keys = {
            "id",
            "name",
            "theme_tag",
            "branch_faction",
            "route_floor_count",
            "regular_node_weights",
            "placeholder_enemy_ids",
            "boss_pool",
            "next_map",
        }
        missing_keys = required_keys.difference(map_data)
        if missing_keys:
            raise ValueError(
                f"Campaign map definition is missing keys: {', '.join(sorted(missing_keys))}"
            )

        map_id = map_data["id"]
        if map_id not in ALLOWED_CAMPAIGN_MAP_IDS:
            raise ValueError(f"Unsupported campaign map id: {map_id}")

        branch_faction = map_data["branch_faction"]
        if branch_faction is not None and branch_faction not in ALLOWED_BRANCH_FACTIONS:
            raise ValueError(f"Campaign map {map_id} has unsupported branch_faction: {branch_faction}")

        route_floor_count = map_data["route_floor_count"]
        if not isinstance(route_floor_count, int) or route_floor_count < 2:
            raise ValueError(f"Campaign map {map_id} route_floor_count must be an integer >= 2.")

        regular_node_weights = self._validate_node_weights(map_data["regular_node_weights"], map_id)
        placeholder_enemy_ids = self._validate_placeholder_enemy_ids(
            map_data["placeholder_enemy_ids"],
            map_id,
        )
        boss_pool = self._validate_boss_pool(map_data["boss_pool"], map_id)
        next_map = self._validate_next_map(map_data["next_map"], map_id, branch_faction)

        return {
            "id": map_id,
            "name": self._require_text(map_data["name"], map_id, "name"),
            "theme_tag": self._require_text(map_data["theme_tag"], map_id, "theme_tag"),
            "branch_faction": branch_faction,
            "route_floor_count": route_floor_count,
            "regular_node_weights": regular_node_weights,
            "placeholder_enemy_ids": placeholder_enemy_ids,
            "boss_pool": boss_pool,
            "next_map": next_map,
        }

    def _validate_node_weights(self, node_weights: Any, map_id: str) -> dict[str, float]:
        if not isinstance(node_weights, dict):
            raise ValueError(f"Campaign map {map_id} regular_node_weights must be a dictionary.")
        validated: dict[str, float] = {}
        for node_type in ALLOWED_NODE_WEIGHT_TYPES:
            weight = node_weights.get(node_type)
            if not isinstance(weight, (int, float)) or weight < 0:
                raise ValueError(
                    f"Campaign map {map_id} regular_node_weights[{node_type}] must be non-negative."
                )
            validated[node_type] = float(weight)
        return validated

    def _validate_placeholder_enemy_ids(
        self,
        placeholder_enemy_ids: Any,
        map_id: str,
    ) -> dict[str, list[str]]:
        if not isinstance(placeholder_enemy_ids, dict):
            raise ValueError(f"Campaign map {map_id} placeholder_enemy_ids must be a dictionary.")

        validated: dict[str, list[str]] = {}
        for node_type in ("combat", "elite", "boss"):
            enemy_ids = placeholder_enemy_ids.get(node_type)
            if (
                not isinstance(enemy_ids, list)
                or not enemy_ids
                or not all(isinstance(enemy_id, str) and enemy_id for enemy_id in enemy_ids)
            ):
                raise ValueError(
                    f"Campaign map {map_id} placeholder_enemy_ids[{node_type}] must be a non-empty list of enemy ids."
                )
            validated[node_type] = list(enemy_ids)
        return validated

    def _validate_boss_pool(self, boss_pool: Any, map_id: str) -> list[dict[str, Any]]:
        if not isinstance(boss_pool, list) or not boss_pool:
            raise ValueError(f"Campaign map {map_id} boss_pool must be a non-empty list.")

        validated_bosses: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for raw_boss in boss_pool:
            if not isinstance(raw_boss, dict):
                raise ValueError(f"Campaign map {map_id} boss entries must be dictionaries.")
            boss_id = raw_boss.get("id")
            base_weight = raw_boss.get("base_weight", 1.0)
            if not isinstance(boss_id, str) or not boss_id:
                raise ValueError(f"Campaign map {map_id} boss entries must have a non-empty id.")
            if boss_id in seen_ids:
                raise ValueError(f"Campaign map {map_id} includes duplicate boss id {boss_id}.")
            if not isinstance(base_weight, (int, float)) or base_weight < 0:
                raise ValueError(f"Campaign map {map_id} boss {boss_id} base_weight must be non-negative.")
            boss_name = raw_boss.get("name")
            boss_branch = raw_boss.get("branch_faction")
            enemy_ids = raw_boss.get("enemy_ids")
            if boss_name is None and enemy_ids is None:
                catalog_boss = self.grayspine_content.get_boss(boss_id)
                boss_name = catalog_boss["name"]
                boss_branch = catalog_boss.get("faction")
                enemy_ids = list(catalog_boss.get("enemy_ids", [boss_id]))
            if not isinstance(boss_name, str) or not boss_name.strip():
                raise ValueError(f"Campaign map {map_id} boss {boss_id} must have a name.")
            if boss_branch is not None and boss_branch not in ALLOWED_BRANCH_FACTIONS:
                raise ValueError(
                    f"Campaign map {map_id} boss {boss_id} has unsupported branch_faction {boss_branch}."
                )
            if (
                not isinstance(enemy_ids, list)
                or not enemy_ids
                or not all(isinstance(enemy_id, str) and enemy_id for enemy_id in enemy_ids)
            ):
                raise ValueError(f"Campaign map {map_id} boss {boss_id} must define enemy_ids.")
            seen_ids.add(boss_id)
            validated_bosses.append(
                {
                    "id": boss_id,
                    "name": boss_name.strip(),
                    "branch_faction": boss_branch,
                    "enemy_ids": list(enemy_ids),
                    "base_weight": float(base_weight),
                }
            )
        return validated_bosses

    def _validate_next_map(
        self,
        next_map_data: Any,
        map_id: str,
        branch_faction: str | None,
    ) -> dict[str, Any]:
        if not isinstance(next_map_data, dict):
            raise ValueError(f"Campaign map {map_id} next_map must be a dictionary.")
        next_type = next_map_data.get("type")
        if next_type not in ALLOWED_NEXT_MAP_TYPES:
            raise ValueError(f"Campaign map {map_id} next_map has unsupported type: {next_type}")

        if next_type == "fixed":
            target_map_id = next_map_data.get("map_id")
            if target_map_id not in ALLOWED_CAMPAIGN_MAP_IDS:
                raise ValueError(f"Campaign map {map_id} fixed next_map must point to a known map id.")
            return {"type": next_type, "map_id": target_map_id}

        if next_type == "branch_from_boss":
            branches = next_map_data.get("branches")
            if not isinstance(branches, dict) or not branches:
                raise ValueError(f"Campaign map {map_id} branch_from_boss must define branches.")
            normalized_branches: dict[str, str] = {}
            for faction, target_map_id in branches.items():
                if faction not in ALLOWED_BRANCH_FACTIONS:
                    raise ValueError(f"Campaign map {map_id} has unsupported branch key: {faction}")
                if target_map_id not in ALLOWED_CAMPAIGN_MAP_IDS:
                    raise ValueError(
                        f"Campaign map {map_id} branch {faction} must point to a known map id."
                    )
                normalized_branches[faction] = target_map_id
            return {"type": next_type, "branches": normalized_branches}

        if branch_faction is None and map_id not in {"outskirts", "city_streets"}:
            raise ValueError(
                f"Campaign map {map_id} ending in victory should usually declare a branch_faction."
            )
        return {"type": next_type}

    def _require_text(self, value: Any, map_id: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Campaign map {map_id} {field_name} must be a non-empty string.")
        return value.strip()


def simulate_campaign_library() -> dict[str, Any]:
    library = CampaignLibrary()
    maps = library.list_maps()
    rng = random.Random(17)
    map_one_boss = library.choose_boss("outskirts", rng)
    map_two_boss = library.choose_boss("city_streets", rng)
    return {
        "map_count": len(maps),
        "first_map": maps[0]["id"],
        "map_one_boss": map_one_boss["id"],
        "map_two_branch": map_two_boss["branch_faction"],
        "branched_map": library.next_map_id_for_boss("city_streets", map_two_boss),
    }
