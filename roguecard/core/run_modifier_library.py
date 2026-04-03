from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cards.card_library import CardLibrary
from config import RUN_MODIFIERS_DATA_PATH

ALLOWED_MODIFIER_KINDS = {"relic", "blessing", "curse"}
ALLOWED_MODIFIER_HOOKS = {
    "on_acquire",
    "combat_start",
    "turn_one",
    "post_victory",
    "reward_generation",
    "shop_pricing",
    "event_value",
}
ALLOWED_MODIFIER_EFFECT_TYPES = {
    "gain_credits",
    "modify_max_hp",
    "modify_healing_multiplier_percent",
    "add_card",
    "gain_block",
    "draw_cards",
    "gain_energy",
    "heal",
    "extra_card_choice",
    "percent_discount",
    "flat_discount",
    "free_first_purge_run",
    "free_first_reroll_shop",
    "flat_surcharge_first_card_shop",
    "heal_after_event",
}
SHOP_PRICE_TARGETS = {"all", "card", "purge", "heal", "reroll"}


class RunModifierLibrary:
    def __init__(
        self,
        data_path: Path = RUN_MODIFIERS_DATA_PATH,
        card_library: CardLibrary | None = None,
    ) -> None:
        self.data_path = data_path
        self.card_library = card_library or CardLibrary()
        self._modifiers: dict[str, dict[str, Any]] = {}

    def load_modifiers(self) -> dict[str, dict[str, Any]]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("run_modifiers.json must contain a list of modifier definitions.")

        loaded_modifiers: dict[str, dict[str, Any]] = {}
        for raw_modifier in payload:
            modifier = self._validate_modifier(raw_modifier)
            if modifier["id"] in loaded_modifiers:
                raise ValueError(f"Duplicate run modifier id detected: {modifier['id']}")
            loaded_modifiers[modifier["id"]] = modifier

        self._modifiers = loaded_modifiers
        return self._modifiers

    def list_modifier_ids(self, draft_only: bool = False) -> list[str]:
        if not self._modifiers:
            self.load_modifiers()
        modifier_ids = list(self._modifiers)
        if not draft_only:
            return modifier_ids
        return [modifier_id for modifier_id in modifier_ids if self._modifiers[modifier_id]["draft_eligible"]]

    def get_modifier(self, modifier_id: str) -> dict[str, Any]:
        if not self._modifiers:
            self.load_modifiers()

        try:
            return copy.deepcopy(self._modifiers[modifier_id])
        except KeyError as error:
            raise KeyError(f"Unknown run modifier id: {modifier_id}") from error

    def _validate_modifier(self, modifier_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(modifier_data, dict):
            raise ValueError("Run modifier definitions must be dictionaries.")

        required_keys = {"id", "name", "kind", "draft_eligible", "description", "hooks"}
        missing_keys = required_keys.difference(modifier_data)
        if missing_keys:
            raise ValueError(
                f"Run modifier is missing required keys: {', '.join(sorted(missing_keys))}"
            )

        modifier_id = modifier_data["id"]
        name = modifier_data["name"]
        kind = modifier_data["kind"]
        draft_eligible = modifier_data["draft_eligible"]
        description = modifier_data["description"]
        downside = modifier_data.get("downside")
        hooks = modifier_data["hooks"]

        if not isinstance(modifier_id, str) or not modifier_id:
            raise ValueError("Run modifier id must be a non-empty string.")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Run modifier {modifier_id} must have a non-empty name.")
        if kind not in ALLOWED_MODIFIER_KINDS:
            raise ValueError(f"Run modifier {modifier_id} has unsupported kind: {kind}")
        if not isinstance(draft_eligible, bool):
            raise ValueError(f"Run modifier {modifier_id} draft_eligible must be a boolean.")
        if not isinstance(description, str) or not description:
            raise ValueError(f"Run modifier {modifier_id} must have a non-empty description.")
        if downside is not None and (not isinstance(downside, str) or not downside):
            raise ValueError(f"Run modifier {modifier_id} downside must be a non-empty string when provided.")
        if not isinstance(hooks, dict) or not hooks:
            raise ValueError(f"Run modifier {modifier_id} must define at least one hook.")

        validated_hooks: dict[str, list[dict[str, Any]]] = {}
        for hook_name, effects in hooks.items():
            if hook_name not in ALLOWED_MODIFIER_HOOKS:
                raise ValueError(f"Run modifier {modifier_id} has unsupported hook: {hook_name}")
            if not isinstance(effects, list) or not effects:
                raise ValueError(f"Run modifier {modifier_id} hook {hook_name} must be a non-empty list.")
            validated_hooks[hook_name] = [
                self._validate_effect(effect, modifier_id, hook_name) for effect in effects
            ]

        return {
            "id": modifier_id,
            "name": name,
            "kind": kind,
            "draft_eligible": draft_eligible,
            "description": description,
            "downside": downside,
            "hooks": validated_hooks,
        }

    def _validate_effect(
        self,
        effect_data: dict[str, Any],
        modifier_id: str,
        hook_name: str,
    ) -> dict[str, Any]:
        if not isinstance(effect_data, dict):
            raise ValueError(f"Run modifier {modifier_id} hook {hook_name} effects must be dictionaries.")

        effect_type = effect_data.get("type")
        if effect_type not in ALLOWED_MODIFIER_EFFECT_TYPES:
            raise ValueError(
                f"Run modifier {modifier_id} hook {hook_name} has unsupported effect type: {effect_type}"
            )

        validated = {"type": effect_type}

        if effect_type == "add_card":
            card_id = effect_data.get("card_id")
            if not isinstance(card_id, str) or not card_id:
                raise ValueError(f"Run modifier {modifier_id} add_card effects must define card_id.")
            self.card_library.get_card(card_id)
            validated["card_id"] = card_id
            return validated

        if effect_type in {"free_first_purge_run", "free_first_reroll_shop"}:
            return validated

        if effect_type in {"percent_discount", "flat_discount"}:
            target = effect_data.get("target")
            value = effect_data.get("value")
            if target not in SHOP_PRICE_TARGETS:
                raise ValueError(
                    f"Run modifier {modifier_id} {effect_type} target must be one of: {', '.join(sorted(SHOP_PRICE_TARGETS))}"
                )
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"Run modifier {modifier_id} {effect_type} value must be a non-negative integer.")
            validated["target"] = target
            validated["value"] = value
            return validated

        if effect_type == "flat_surcharge_first_card_shop":
            value = effect_data.get("value")
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"Run modifier {modifier_id} flat_surcharge_first_card_shop value must be a non-negative integer."
                )
            validated["value"] = value
            return validated

        value = effect_data.get("value")
        if not isinstance(value, int):
            raise ValueError(f"Run modifier {modifier_id} hook {hook_name} effect {effect_type} must define an integer value.")
        validated["value"] = value

        encounter_types = effect_data.get("encounter_types")
        if encounter_types is not None:
            if not isinstance(encounter_types, list) or not all(
                isinstance(encounter_type, str) and encounter_type for encounter_type in encounter_types
            ):
                raise ValueError(
                    f"Run modifier {modifier_id} hook {hook_name} encounter_types must be a list of strings."
                )
            validated["encounter_types"] = list(encounter_types)

        return validated


def simulate_run_modifier_library() -> dict[str, Any]:
    library = RunModifierLibrary()
    modifier_ids = library.list_modifier_ids()
    first_modifier = library.get_modifier(modifier_ids[0])
    return {
        "modifier_count": len(modifier_ids),
        "first_modifier_id": first_modifier["id"],
        "draft_eligible": len(library.list_modifier_ids(draft_only=True)),
    }
