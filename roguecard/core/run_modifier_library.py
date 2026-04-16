from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cards.card_library import CardLibrary
from config import RUN_MODIFIERS_DATA_PATH, STATUS_SOURCE_TYPES, STATUS_TAGS

ALLOWED_MODIFIER_TYPES = {"relic", "blessing", "curse", "status"}
ALLOWED_MODIFIER_RARITIES = {"common", "uncommon", "rare", "cursed", "special"}
ALLOWED_DURATION_TYPES = {"permanent", "combat", "floor"}
ALLOWED_ONCE_PER_VALUES = {"turn", "combat"}
ALLOWED_STACK_BEHAVIORS = {
    "no_duplicate",
    "refresh_duration",
    "stack_intensity",
    "stack_count",
}
LEGACY_HOOK_ALIASES = {
    "reward_generation": "on_reward",
    "shop_pricing": "on_shop",
    "event_value": "on_event",
}
ALLOWED_MODIFIER_HOOKS = {
    "on_acquire",
    "combat_start",
    "turn_one",
    "on_turn_start",
    "turn_end",
    "on_status_drawn",
    "on_enemy_status_applied",
    "on_player_status_applied",
    "on_card_exhausted",
    "on_enemy_death",
    "on_attack_hit",
    "post_victory",
    "on_reward",
    "on_shop",
    "on_event",
    "passive",
}
ALLOWED_MODIFIER_EFFECT_TYPES = {
    "gain_credits",
    "lose_credits",
    "damage",
    "modify_max_hp",
    "modify_healing_multiplier_percent",
    "add_card",
    "gain_block",
    "lose_block",
    "draw_cards",
    "gain_energy",
    "heal",
    "extra_card_choice",
    "percent_discount",
    "percent_surcharge",
    "flat_discount",
    "flat_surcharge_first_card_shop",
    "free_first_purge_run",
    "free_first_reroll_shop",
    "heal_after_event",
    "lose_credits_each_floor",
    "reduce_first_block_each_combat",
    "bonus_attack_damage_if_attacked_last_turn",
    "first_card_free",
    "cost_surcharge_after_first_card",
    "repeat_first_card",
    "random_one_of",
    "damage_event_target",
    "damage_random_enemy",
    "apply_status_all_enemies",
    "increase_highest_enemy_status",
    "gain_next_turn_energy",
    "reduce_player_status",
}
SHOP_PRICE_TARGETS = {"all", "card", "relic", "purge", "heal", "reroll"}
ALLOWED_MODIFIER_CARD_TYPES = {"attack", "skill", "power", "status"}


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

    def list_modifiers(
        self,
        *,
        draft_only: bool = False,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._modifiers:
            self.load_modifiers()

        modifiers = [copy.deepcopy(modifier) for modifier in self._modifiers.values()]
        if draft_only:
            modifiers = [modifier for modifier in modifiers if modifier["draft_eligible"]]
        if source_type is not None:
            modifiers = [
                modifier
                for modifier in modifiers
                if source_type in modifier["source_types"]
            ]
        return modifiers

    def supported_tags(self) -> tuple[str, ...]:
        return tuple(STATUS_TAGS)

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

        required_keys = {
            "id",
            "name",
            "type",
            "draft_eligible",
            "description",
            "rarity",
            "base_weight",
            "tags",
            "source_types",
            "hooks",
        }
        missing_keys = required_keys.difference(modifier_data).difference({"type"})
        if missing_keys:
            raise ValueError(
                f"Run modifier is missing required keys: {', '.join(sorted(missing_keys))}"
            )

        modifier_id = modifier_data["id"]
        name = modifier_data["name"]
        modifier_type = modifier_data.get("type", modifier_data.get("kind"))
        draft_eligible = modifier_data["draft_eligible"]
        description = modifier_data["description"]
        downside = modifier_data.get("downside")
        rarity = modifier_data.get("rarity")
        base_weight = modifier_data.get("base_weight")
        tags = self._validate_tags(modifier_data.get("tags"), modifier_id)
        source_types = self._validate_source_types(modifier_data.get("source_types"), modifier_id)
        hooks = modifier_data["hooks"]
        duration = self._validate_duration(
            modifier_data.get("duration", {"type": "permanent"}),
            modifier_id,
        )
        stack_behavior = modifier_data.get("stack_behavior")

        if not isinstance(modifier_id, str) or not modifier_id:
            raise ValueError("Run modifier id must be a non-empty string.")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Run modifier {modifier_id} must have a non-empty name.")
        if modifier_type not in ALLOWED_MODIFIER_TYPES:
            raise ValueError(f"Run modifier {modifier_id} has unsupported type: {modifier_type}")
        if not isinstance(draft_eligible, bool):
            raise ValueError(f"Run modifier {modifier_id} draft_eligible must be a boolean.")
        if not isinstance(description, str) or not description:
            raise ValueError(f"Run modifier {modifier_id} must have a non-empty description.")
        if downside is not None and (not isinstance(downside, str) or not downside):
            raise ValueError(f"Run modifier {modifier_id} downside must be a non-empty string when provided.")
        if rarity not in ALLOWED_MODIFIER_RARITIES:
            raise ValueError(f"Run modifier {modifier_id} has unsupported rarity: {rarity}")
        if not isinstance(base_weight, (int, float)) or base_weight < 0:
            raise ValueError(f"Run modifier {modifier_id} base_weight must be a non-negative number.")
        if not isinstance(hooks, dict) or not hooks:
            raise ValueError(f"Run modifier {modifier_id} must define at least one hook.")

        if stack_behavior is None:
            stack_behavior = "no_duplicate" if duration["type"] == "permanent" else "refresh_duration"
        if stack_behavior not in ALLOWED_STACK_BEHAVIORS:
            raise ValueError(
                f"Run modifier {modifier_id} has unsupported stack_behavior: {stack_behavior}"
            )

        validated_hooks: dict[str, list[dict[str, Any]]] = {}
        for raw_hook_name, effects in hooks.items():
            hook_name = LEGACY_HOOK_ALIASES.get(raw_hook_name, raw_hook_name)
            if hook_name not in ALLOWED_MODIFIER_HOOKS:
                raise ValueError(f"Run modifier {modifier_id} has unsupported hook: {raw_hook_name}")
            if not isinstance(effects, list) or not effects:
                raise ValueError(f"Run modifier {modifier_id} hook {raw_hook_name} must be a non-empty list.")
            validated_hooks.setdefault(hook_name, []).extend(
                self._validate_effect(effect, modifier_id, hook_name) for effect in effects
            )

        return {
            "id": modifier_id,
            "name": name,
            "type": modifier_type,
            "kind": modifier_type,
            "draft_eligible": draft_eligible,
            "description": description,
            "downside": downside,
            "rarity": rarity,
            "base_weight": float(base_weight),
            "tags": tags,
            "primary_tag": tags[0],
            "source_types": source_types,
            "duration": duration,
            "duration_type": duration["type"],
            "stack_behavior": stack_behavior,
            "hooks": validated_hooks,
        }

    def _validate_tags(self, raw_tags: Any, modifier_id: str) -> list[str]:
        if not isinstance(raw_tags, list) or not raw_tags:
            raise ValueError(f"Run modifier {modifier_id} tags must be a non-empty list.")
        validated: list[str] = []
        for tag in raw_tags:
            if tag not in STATUS_TAGS:
                raise ValueError(f"Run modifier {modifier_id} uses unsupported tag: {tag}")
            if tag not in validated:
                validated.append(tag)
        return validated

    def _validate_source_types(self, raw_source_types: Any, modifier_id: str) -> list[str]:
        if not isinstance(raw_source_types, list) or not raw_source_types:
            raise ValueError(f"Run modifier {modifier_id} source_types must be a non-empty list.")
        validated: list[str] = []
        for source_type in raw_source_types:
            if source_type not in STATUS_SOURCE_TYPES:
                raise ValueError(
                    f"Run modifier {modifier_id} uses unsupported source_type: {source_type}"
                )
            if source_type not in validated:
                validated.append(source_type)
        return validated

    def _validate_duration(
        self,
        duration_data: Any,
        modifier_id: str,
    ) -> dict[str, Any]:
        if duration_data is None:
            return {"type": "permanent", "value": None}
        if not isinstance(duration_data, dict):
            raise ValueError(f"Run modifier {modifier_id} duration must be a dictionary when provided.")

        duration_type = duration_data.get("type")
        if duration_type not in ALLOWED_DURATION_TYPES:
            raise ValueError(f"Run modifier {modifier_id} has unsupported duration type: {duration_type}")

        value = duration_data.get("value")
        if duration_type == "permanent":
            return {"type": "permanent", "value": None}
        if not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"Run modifier {modifier_id} duration value must be a positive integer for {duration_type} durations."
            )
        return {"type": duration_type, "value": value}

    def _validate_effect(
        self,
        effect_data: dict[str, Any],
        modifier_id: str,
        hook_name: str,
        *,
        allow_random: bool = True,
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
            return self._apply_common_effect_metadata(validated, effect_data, modifier_id, hook_name)

        if effect_type in {"free_first_purge_run", "free_first_reroll_shop", "first_card_free", "repeat_first_card"}:
            return self._apply_common_effect_metadata(validated, effect_data, modifier_id, hook_name)

        if effect_type == "random_one_of":
            if not allow_random:
                raise ValueError(f"Run modifier {modifier_id} random_one_of effects cannot be nested.")
            options = effect_data.get("options")
            if not isinstance(options, list) or not options:
                raise ValueError(f"Run modifier {modifier_id} random_one_of effects must define options.")
            validated["options"] = [
                self._validate_random_option(option, modifier_id, hook_name) for option in options
            ]
            return self._apply_common_effect_metadata(validated, effect_data, modifier_id, hook_name)

        if effect_type in {
            "percent_discount",
            "percent_surcharge",
            "flat_discount",
        }:
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
            return self._apply_common_effect_metadata(validated, effect_data, modifier_id, hook_name)

        if effect_type in {"apply_status_all_enemies", "increase_highest_enemy_status"}:
            status_id = effect_data.get("status_id")
            if not isinstance(status_id, str) or not status_id:
                raise ValueError(
                    f"Run modifier {modifier_id} hook {hook_name} effect {effect_type} must define status_id."
                )
            validated["status_id"] = status_id
        elif effect_type == "reduce_player_status":
            status_id = effect_data.get("status_id")
            if status_id is not None:
                if not isinstance(status_id, str) or not status_id:
                    raise ValueError(
                        f"Run modifier {modifier_id} hook {hook_name} effect {effect_type} status_id must be a non-empty string when provided."
                    )
                validated["status_id"] = status_id

        value = effect_data.get("value")
        if not isinstance(value, int):
            raise ValueError(
                f"Run modifier {modifier_id} hook {hook_name} effect {effect_type} must define an integer value."
            )
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

        return self._apply_common_effect_metadata(validated, effect_data, modifier_id, hook_name)

    def _apply_common_effect_metadata(
        self,
        validated: dict[str, Any],
        effect_data: dict[str, Any],
        modifier_id: str,
        hook_name: str,
    ) -> dict[str, Any]:
        once_per = effect_data.get("once_per")
        if once_per is not None:
            if once_per not in ALLOWED_ONCE_PER_VALUES:
                raise ValueError(
                    f"Run modifier {modifier_id} hook {hook_name} once_per must be one of: "
                    f"{', '.join(sorted(ALLOWED_ONCE_PER_VALUES))}"
                )
            validated["once_per"] = once_per

        status_ids = effect_data.get("status_ids")
        if status_ids is not None:
            if (
                not isinstance(status_ids, list)
                or not status_ids
                or not all(isinstance(status_id, str) and status_id for status_id in status_ids)
            ):
                raise ValueError(
                    f"Run modifier {modifier_id} hook {hook_name} status_ids must be a non-empty list of strings."
                )
            validated["status_ids"] = list(status_ids)

        card_type = effect_data.get("card_type")
        if card_type is not None:
            if card_type not in ALLOWED_MODIFIER_CARD_TYPES:
                raise ValueError(
                    f"Run modifier {modifier_id} hook {hook_name} card_type must be one of: "
                    f"{', '.join(sorted(ALLOWED_MODIFIER_CARD_TYPES))}"
                )
            validated["card_type"] = card_type

        require_target_has_statuses = effect_data.get("require_target_has_statuses")
        if require_target_has_statuses is not None:
            if (
                not isinstance(require_target_has_statuses, list)
                or not require_target_has_statuses
                or not all(isinstance(status_id, str) and status_id for status_id in require_target_has_statuses)
            ):
                raise ValueError(
                    f"Run modifier {modifier_id} hook {hook_name} require_target_has_statuses must be a "
                    "non-empty list of strings."
                )
            validated["require_target_has_statuses"] = list(require_target_has_statuses)

        return validated

    def _validate_random_option(
        self,
        option_data: dict[str, Any],
        modifier_id: str,
        hook_name: str,
    ) -> dict[str, Any]:
        if not isinstance(option_data, dict):
            raise ValueError(
                f"Run modifier {modifier_id} random_one_of option in {hook_name} must be a dictionary."
            )
        effects = option_data.get("effects")
        weight = option_data.get("weight", 1)
        summary = option_data.get("summary")

        if not isinstance(weight, int) or weight <= 0:
            raise ValueError(
                f"Run modifier {modifier_id} random_one_of options must use positive integer weights."
            )
        if not isinstance(effects, list) or not effects:
            raise ValueError(
                f"Run modifier {modifier_id} random_one_of options must define a non-empty effects list."
            )
        if summary is not None and (not isinstance(summary, str) or not summary):
            raise ValueError(
                f"Run modifier {modifier_id} random_one_of option summaries must be non-empty strings when provided."
            )

        return {
            "weight": weight,
            "summary": summary,
            "effects": [
                self._validate_effect(effect, modifier_id, hook_name, allow_random=False)
                for effect in effects
            ],
        }


def simulate_run_modifier_library() -> dict[str, Any]:
    library = RunModifierLibrary()
    modifiers = library.list_modifiers()
    first_modifier = modifiers[0]
    return {
        "modifier_count": len(modifiers),
        "first_modifier_id": first_modifier["id"],
        "first_modifier_rarity": first_modifier["rarity"],
        "draft_eligible": len(library.list_modifier_ids(draft_only=True)),
        "first_modifier_type": first_modifier["type"],
    }
