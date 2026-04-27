from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cards.card_library import CardLibrary  # noqa: E402
from config import RUN_MODIFIERS_DATA_PATH  # noqa: E402
from core.run_modifier_library import (  # noqa: E402
    DANGEROUS_LOOP_EFFECT_TYPES,
    RunModifierLibrary,
    SHOP_PRICE_TARGETS,
)

COMBAT_STATUS_IDS = {
    "bleed",
    "burn",
    "infect",
    "marked",
    "nullified",
    "suppressed",
    "vulnerable",
    "weak",
}
STATUS_CARD_PREFIX = "status"
STATUS_EFFECT_TYPES = {
    "apply_status_all_enemies",
    "apply_status_event_target",
    "apply_status_other_enemies",
    "increase_highest_enemy_status",
    "heal_if_any_enemy_has_status",
    "reduce_player_status",
}
TARGETED_PRICE_EFFECT_TYPES = {"percent_discount", "percent_surcharge", "flat_discount"}


def _load_raw_modifiers(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a list payload.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _iter_effects(effect_or_modifier: Any, *, trail: list[str] | None = None) -> list[tuple[list[str], dict[str, Any]]]:
    current_trail = list(trail or [])
    collected: list[tuple[list[str], dict[str, Any]]] = []
    if not isinstance(effect_or_modifier, dict):
        return collected
    hooks = effect_or_modifier.get("hooks")
    if isinstance(hooks, dict):
        for hook_name, effects in hooks.items():
            if not isinstance(effects, list):
                continue
            for index, effect in enumerate(effects):
                collected.extend(_iter_effects(effect, trail=current_trail + [f"hook:{hook_name}", f"effect:{index}"]))
        return collected
    if "type" in effect_or_modifier:
        collected.append((current_trail, effect_or_modifier))
    if effect_or_modifier.get("type") == "random_one_of":
        for option_index, option in enumerate(effect_or_modifier.get("options", [])):
            if not isinstance(option, dict):
                continue
            for effect_index, nested_effect in enumerate(option.get("effects", [])):
                collected.extend(
                    _iter_effects(
                        nested_effect,
                        trail=current_trail + [f"option:{option_index}", f"effect:{effect_index}"],
                    )
                )
    return collected


def _effect_location(modifier_id: str, trail: list[str]) -> str:
    return " -> ".join([modifier_id, *trail]) if trail else modifier_id


def _valid_status_ids(library: RunModifierLibrary, card_library: CardLibrary) -> set[str]:
    modifier_status_ids = {
        modifier["id"]
        for modifier in library.list_modifiers()
        if str(modifier.get("category", "")).lower() == "run_modifier_status"
    }
    status_card_ids = {
        card.id
        for card in card_library.list_cards()
        if str(getattr(card, "type", "")).lower() == STATUS_CARD_PREFIX
    }
    return COMBAT_STATUS_IDS | modifier_status_ids | status_card_ids


def _assert_status_list(
    *,
    modifier_id: str,
    trail: list[str],
    field_name: str,
    value: Any,
    valid_status_ids: set[str],
) -> None:
    location = _effect_location(modifier_id, trail)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{location} {field_name} must be a non-empty list.")
    invalid = [status_id for status_id in value if not isinstance(status_id, str) or status_id not in valid_status_ids]
    if invalid:
        raise ValueError(f"{location} {field_name} contains invalid status ids: {', '.join(map(str, invalid))}")


def _validate_raw_modifier_fields(
    *,
    raw_modifier: dict[str, Any],
    valid_status_ids: set[str],
) -> None:
    modifier_id = str(raw_modifier.get("id", "<unknown>"))
    if "track" in raw_modifier:
        raise ValueError(f"{modifier_id} still exposes legacy track in data/run_modifiers.json.")

    for trail, effect in _iter_effects(raw_modifier):
        location = _effect_location(modifier_id, trail)
        effect_type = effect.get("type")
        if effect_type in TARGETED_PRICE_EFFECT_TYPES:
            target = effect.get("target")
            if not isinstance(target, str) or target not in SHOP_PRICE_TARGETS:
                raise ValueError(f"{location} target must be one of: {', '.join(sorted(SHOP_PRICE_TARGETS))}")

        if effect_type in STATUS_EFFECT_TYPES:
            status_id = effect.get("status_id")
            status_ids = effect.get("status_ids")
            if effect_type == "reduce_player_status" and isinstance(status_ids, list) and status_ids:
                pass
            elif not isinstance(status_id, str) or status_id not in valid_status_ids:
                raise ValueError(f"{location} status_id must be a valid status reference.")

        status_id = effect.get("status_id")
        if "status_id" in effect and status_id is None:
            raise ValueError(f"{location} status_id cannot be null.")
        if isinstance(status_id, str) and status_id not in valid_status_ids:
            raise ValueError(f"{location} uses invalid status_id: {status_id}")

        if "status_ids" in effect:
            _assert_status_list(
                modifier_id=modifier_id,
                trail=trail,
                field_name="status_ids",
                value=effect.get("status_ids"),
                valid_status_ids=valid_status_ids,
            )

        if "require_target_has_statuses" in effect:
            _assert_status_list(
                modifier_id=modifier_id,
                trail=trail,
                field_name="require_target_has_statuses",
                value=effect.get("require_target_has_statuses"),
                valid_status_ids=valid_status_ids,
            )

def validate(path: Path = RUN_MODIFIERS_DATA_PATH) -> None:
    card_library = CardLibrary()
    modifier_library = RunModifierLibrary(data_path=path, card_library=card_library)
    modifier_library.load_modifiers()

    raw_modifiers = _load_raw_modifiers(path)
    valid_status_ids = _valid_status_ids(modifier_library, card_library)
    for raw_modifier in raw_modifiers:
        _validate_raw_modifier_fields(raw_modifier=raw_modifier, valid_status_ids=valid_status_ids)

    print(f"Validated {len(raw_modifiers)} run modifiers in {path.name}.")


if __name__ == "__main__":
    validate()
