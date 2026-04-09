from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any

from config import (
    FINAL_MAP_BARKS_DATA_PATH,
    FINAL_MAP_BOSSES_DATA_PATH,
    FINAL_MAP_ENCOUNTERS_DATA_PATH,
    FINAL_MAP_FACTION_IDS,
    FINAL_MAP_ROUTE_IDS,
    GRAYSPINE_LORE_DATA_PATH,
)


class GrayspineContentLibrary:
    def __init__(
        self,
        *,
        lore_path: Path = GRAYSPINE_LORE_DATA_PATH,
        bosses_path: Path = FINAL_MAP_BOSSES_DATA_PATH,
        encounters_path: Path = FINAL_MAP_ENCOUNTERS_DATA_PATH,
        barks_path: Path = FINAL_MAP_BARKS_DATA_PATH,
    ) -> None:
        self.lore_path = lore_path
        self.bosses_path = bosses_path
        self.encounters_path = encounters_path
        self.barks_path = barks_path
        self._lore: dict[str, Any] | None = None
        self._bosses: dict[str, dict[str, Any]] = {}
        self._factions: dict[str, dict[str, Any]] = {}
        self._route_map_ids: dict[str, str] = {}
        self._encounter_generation: dict[str, Any] = {}
        self._barks: dict[str, Any] = {}

    def load(self) -> None:
        if self._lore is not None:
            return
        self._lore = self._load_lore()
        self._bosses = self._load_bosses()
        lore_factions = self._load_lore_factions(self._lore)
        encounter_factions, self._route_map_ids, self._encounter_generation = self._load_encounters()
        self._factions = {
            faction_id: {**lore_factions[faction_id], **encounter_factions[faction_id]}
            for faction_id in lore_factions
        }
        self._barks = self._load_barks()

    def lore(self) -> dict[str, Any]:
        self.load()
        return copy.deepcopy(self._lore)

    def list_factions(self) -> list[dict[str, Any]]:
        self.load()
        return [copy.deepcopy(faction) for faction in self._factions.values()]

    def get_faction(self, faction_id: str) -> dict[str, Any]:
        self.load()
        try:
            return copy.deepcopy(self._factions[faction_id])
        except KeyError as error:
            raise KeyError(f"Unknown Grayspine faction id: {faction_id}") from error

    def faction_for_map(self, map_id: str) -> str | None:
        self.load()
        for faction_id, route_map_id in self._route_map_ids.items():
            if route_map_id == map_id:
                return faction_id
        return None

    def route_intro_text(self, faction_id: str) -> str:
        self.load()
        faction = self._factions[faction_id]
        return f"{faction['route_name']}. {faction['slogan']}"

    def spine_core_summary(self, *, unlocked: bool) -> str:
        self.load()
        spine_core = self._lore["spine_core"]
        return spine_core["unlocked_summary"] if unlocked else spine_core["locked_summary"]

    def get_boss(self, boss_id: str) -> dict[str, Any]:
        self.load()
        try:
            boss = self._bosses[boss_id]
        except KeyError as error:
            raise KeyError(f"Unknown Grayspine boss id: {boss_id}") from error
        resolved = copy.deepcopy(boss)
        resolved.setdefault("enemy_ids", [boss_id])
        return resolved

    def get_bosses_for_faction(self, faction_id: str) -> list[dict[str, Any]]:
        self.load()
        return [
            self.get_boss(boss_id)
            for boss_id in self._factions[faction_id].get("boss_ids", [])
        ]

    def choose_encounter(
        self,
        faction_id: str,
        *,
        node_type: str,
        route_floor: int,
        rng: random.Random,
    ) -> dict[str, Any]:
        self.load()
        if node_type not in {"combat", "elite"}:
            raise ValueError(f"Unsupported Grayspine encounter node type: {node_type}")
        faction = self._factions[faction_id]
        difficulty_weights = self._difficulty_weights(node_type=node_type, route_floor=route_floor)
        weighted_encounters: list[tuple[dict[str, Any], float]] = []
        for encounter in faction["encounters"]:
            if node_type not in encounter["node_types"]:
                continue
            weight = difficulty_weights.get(encounter["difficulty"], 0.0) * float(encounter.get("weight", 1.0))
            if weight <= 0:
                continue
            weighted_encounters.append((encounter, weight))
        if not weighted_encounters:
            raise ValueError(f"No Grayspine encounters available for {faction_id} {node_type} floor {route_floor}.")
        total_weight = sum(weight for _, weight in weighted_encounters)
        roll = rng.random() * total_weight
        running_total = 0.0
        for encounter, weight in weighted_encounters:
            running_total += weight
            if roll <= running_total:
                return copy.deepcopy(encounter)
        return copy.deepcopy(weighted_encounters[-1][0])

    def bark_lines(
        self,
        *,
        boss_id: str | None = None,
        faction_id: str | None = None,
        trigger: str,
    ) -> list[str]:
        self.load()
        if boss_id is not None:
            boss_lines = self._barks.get("bosses", {}).get(boss_id, {})
            if trigger in boss_lines:
                return list(boss_lines[trigger])
        if faction_id is not None:
            faction_lines = self._barks.get("factions", {}).get(faction_id, {})
            if trigger in faction_lines:
                return list(faction_lines[trigger])
            if trigger in {"phase_change", "heal"} and "attack" in faction_lines:
                return list(faction_lines["attack"])
        return []

    def _difficulty_weights(self, *, node_type: str, route_floor: int) -> dict[str, float]:
        key = "elite_bands" if node_type == "elite" else "combat_bands"
        bands = self._encounter_generation[key]
        for band in bands:
            if route_floor <= band["max_floor"]:
                return dict(band["difficulty_weights"])
        return dict(bands[-1]["difficulty_weights"])

    def _load_json(self, path: Path, *, expected: type) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, expected):
            raise ValueError(f"{path.name} must contain a {expected.__name__}.")
        return payload

    def _load_lore(self) -> dict[str, Any]:
        payload = self._load_json(self.lore_path, expected=dict)
        if "city" not in payload or "factions" not in payload or "spine_core" not in payload:
            raise ValueError("grayspine_lore.json is missing required top-level keys.")
        return payload

    def _load_lore_factions(self, lore_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        factions = lore_data.get("factions")
        if not isinstance(factions, list) or not factions:
            raise ValueError("grayspine_lore.json must define factions.")
        loaded: dict[str, dict[str, Any]] = {}
        for faction in factions:
            if not isinstance(faction, dict):
                raise ValueError("Lore faction entries must be dictionaries.")
            faction_id = faction.get("id")
            if faction_id not in FINAL_MAP_FACTION_IDS:
                raise ValueError(f"Unsupported lore faction id: {faction_id}")
            loaded[faction_id] = copy.deepcopy(faction)
        return loaded

    def _load_bosses(self) -> dict[str, dict[str, Any]]:
        payload = self._load_json(self.bosses_path, expected=dict)
        bosses = payload.get("bosses")
        if not isinstance(bosses, list) or not bosses:
            raise ValueError("final_map_bosses.json must define a non-empty bosses list.")
        loaded: dict[str, dict[str, Any]] = {}
        for boss in bosses:
            if not isinstance(boss, dict):
                raise ValueError("Boss definitions must be dictionaries.")
            boss_id = boss.get("id")
            if not isinstance(boss_id, str) or not boss_id:
                raise ValueError("Boss definitions must define a non-empty id.")
            if boss_id in loaded:
                raise ValueError(f"Duplicate boss id detected: {boss_id}")
            loaded[boss_id] = copy.deepcopy(boss)
        return loaded

    def _load_encounters(self) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, Any]]:
        payload = self._load_json(self.encounters_path, expected=dict)
        generation = payload.get("generation")
        factions = payload.get("factions")
        if not isinstance(generation, dict):
            raise ValueError("final_map_encounters.json must define generation rules.")
        if not isinstance(factions, list) or not factions:
            raise ValueError("final_map_encounters.json must define factions.")
        loaded_factions: dict[str, dict[str, Any]] = {}
        route_map_ids: dict[str, str] = {}
        for faction in factions:
            if not isinstance(faction, dict):
                raise ValueError("Encounter factions must be dictionaries.")
            faction_id = faction.get("id")
            route_map_id = faction.get("route_map_id")
            if faction_id not in FINAL_MAP_FACTION_IDS:
                raise ValueError(f"Unsupported Grayspine faction id: {faction_id}")
            if route_map_id != FINAL_MAP_ROUTE_IDS[faction_id]:
                raise ValueError(f"Faction {faction_id} route_map_id must be {FINAL_MAP_ROUTE_IDS[faction_id]}.")
            encounters = faction.get("encounters")
            if not isinstance(encounters, list) or not encounters:
                raise ValueError(f"Faction {faction_id} must define encounters.")
            for encounter in encounters:
                enemy_ids = encounter.get("enemy_ids")
                if (
                    not isinstance(enemy_ids, list)
                    or not enemy_ids
                    or len(enemy_ids) > generation.get("max_enemies", 5)
                    or not all(isinstance(enemy_id, str) and enemy_id for enemy_id in enemy_ids)
                ):
                    raise ValueError(f"Faction {faction_id} encounter {encounter.get('id')} has invalid enemy_ids.")
            loaded_factions[faction_id] = copy.deepcopy(faction)
            route_map_ids[faction_id] = route_map_id
        return loaded_factions, route_map_ids, copy.deepcopy(generation)

    def _load_barks(self) -> dict[str, Any]:
        payload = self._load_json(self.barks_path, expected=dict)
        if not isinstance(payload.get("factions"), dict) or not isinstance(payload.get("bosses"), dict):
            raise ValueError("final_map_barks.json must define faction and boss bark dictionaries.")
        return payload


def simulate_grayspine_content_library() -> dict[str, Any]:
    library = GrayspineContentLibrary()
    encounter = library.choose_encounter(
        "helix_ward",
        node_type="combat",
        route_floor=8,
        rng=random.Random(17),
    )
    return {
        "faction_count": len(library.list_factions()),
        "helix_route": library.get_faction("helix_ward")["route_map_id"],
        "sample_boss": library.get_boss("miremother_vexa")["name"],
        "sample_encounter": encounter["id"],
        "spine_locked": library.spine_core_summary(unlocked=False),
    }
