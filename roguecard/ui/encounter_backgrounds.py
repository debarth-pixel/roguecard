from __future__ import annotations

from pathlib import Path
from typing import Any

from config import ARTS_ROOT, resolve_asset_path

DEFAULT_ENCOUNTER_BACKGROUND_PATH = resolve_asset_path("ui", "bg_combat.png")
ENCOUNTER_BACKGROUND_PATHS = {
    "outskirts": ARTS_ROOT / "map_1_combat.png",
    "city_streets": ARTS_ROOT / "map_2_combat.png",
    "blackwire_lockdown_sector": ARTS_ROOT / "map_3_blackwire.png",
    "cinder_jackals_edgeworks": ARTS_ROOT / "map_3_cinderjackal.png",
    "helix_ward_depths": ARTS_ROOT / "map_3_helixware.png",
}
ENCOUNTER_BACKGROUND_FACTION_PATHS = {
    "blackwire_directorate": ARTS_ROOT / "map_3_blackwire.png",
    "cinder_jackals": ARTS_ROOT / "map_3_cinderjackal.png",
    "helix_ward": ARTS_ROOT / "map_3_helixware.png",
}


def resolve_encounter_background_path(
    map_id: Any = None,
    branch_faction: Any = None,
) -> Path:
    if isinstance(map_id, str):
        background_path = ENCOUNTER_BACKGROUND_PATHS.get(map_id)
        if background_path is not None and background_path.exists():
            return background_path
    if isinstance(branch_faction, str):
        background_path = ENCOUNTER_BACKGROUND_FACTION_PATHS.get(branch_faction)
        if background_path is not None and background_path.exists():
            return background_path
    return DEFAULT_ENCOUNTER_BACKGROUND_PATH


def resolve_encounter_background_path_from_state(state: dict[str, Any] | None) -> Path:
    if not isinstance(state, dict):
        return DEFAULT_ENCOUNTER_BACKGROUND_PATH
    return resolve_encounter_background_path(
        map_id=state.get("map_id"),
        branch_faction=state.get("branch_faction"),
    )
