from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cards.card_library import CardLibrary
from config import EVENT_TAGS, EVENTS_DATA_PATH, STATUS_SOURCE_TYPES
from core.character_library import ALLOWED_CHARACTER_IDS
from core.run_modifier_library import RunModifierLibrary

ALLOWED_EVENT_CHOICE_TYPES = {"effect", "purge", "risk"}
ALLOWED_EVENT_RARITIES = {"common", "uncommon", "rare", "special"}
ALLOWED_EVENT_UI_ROLES = {"normal", "secret_corruption"}
MAX_EVENT_CHOICES = 4
ALLOWED_EVENT_EFFECT_TYPES = {
    "gain_credits",
    "lose_credits",
    "gain_card",
    "gain_modifier",
    "gain_status",
    "gain_random_modifier",
    "remove_modifier",
    "remove_status",
    "refresh_modifier",
    "refresh_status",
    "heal",
    "damage",
    "purge_card",
    "adjust_protocol_drift",
    "queue_next_combat_effect",
    "remove_card_from_deck_by_id",
}
ALLOWED_INT_EVENT_REQUIREMENTS = {
    "credits_at_least",
    "credits_at_most",
    "missing_hp_at_least",
    "deck_size_at_least",
    "status_count_at_most",
    "protocol_drift_at_least",
    "protocol_drift_below",
    "current_hp_at_least",
    "current_hp_below_percent",
}
ALLOWED_MODIFIER_EVENT_REQUIREMENTS = {"modifier_active", "modifier_missing"}
ALLOWED_QUEUED_NEXT_COMBAT_EFFECT_TYPES = {
    "gain_energy",
    "draw_cards",
    "gain_block",
    "apply_player_status",
    "add_status_card",
    "add_temporary_card_to_hand",
}
ALLOWED_RANDOM_MODIFIER_FIELDS = {
    "type",
    "source_type",
    "rarity_profile",
    "allow_types",
    "allow_rarities",
    "include_tags",
    "exclude_tags",
    "duration",
    "fallback_effects",
}
ALLOWED_MODIFIER_TYPES = {"relic", "blessing", "curse", "status"}
ALLOWED_MODIFIER_RARITIES = {"common", "uncommon", "rare", "cursed", "special"}


class EventLibrary:
    def __init__(
        self,
        data_path: Path = EVENTS_DATA_PATH,
        card_library: CardLibrary | None = None,
        modifier_library: RunModifierLibrary | None = None,
    ) -> None:
        self.data_path = data_path
        self.card_library = card_library or CardLibrary()
        self.modifier_library = modifier_library or RunModifierLibrary(card_library=self.card_library)
        self._events: dict[str, dict[str, Any]] = {}

    def load_events(self) -> dict[str, dict[str, Any]]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("events.json must contain a list of event definitions.")

        loaded_events: dict[str, dict[str, Any]] = {}
        for raw_event in payload:
            event = self._validate_event(raw_event)
            if event["id"] in loaded_events:
                raise ValueError(f"Duplicate event id detected: {event['id']}")
            loaded_events[event["id"]] = event

        self._events = loaded_events
        return self._events

    def list_event_ids(self) -> list[str]:
        if not self._events:
            self.load_events()
        return list(self._events)

    def list_events(self) -> list[dict[str, Any]]:
        if not self._events:
            self.load_events()
        return [copy.deepcopy(event) for event in self._events.values()]

    def get_event(self, event_id: str) -> dict[str, Any]:
        if not self._events:
            self.load_events()

        try:
            return copy.deepcopy(self._events[event_id])
        except KeyError as error:
            raise KeyError(f"Unknown event id: {event_id}") from error

    def _validate_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event_data, dict):
            raise ValueError("Event definitions must be dictionaries.")

        required_keys = {"id", "title", "body", "choices", "rarity", "base_weight", "tags"}
        missing_keys = required_keys.difference(event_data)
        if missing_keys:
            raise ValueError(f"Event is missing required keys: {', '.join(sorted(missing_keys))}")

        event_id = event_data["id"]
        title = event_data["title"]
        body = event_data["body"]
        choices = event_data["choices"]
        rarity = event_data["rarity"]
        base_weight = event_data["base_weight"]
        tags = self._validate_tags(event_data["tags"], event_id)
        exclusion_tags = self._validate_tags(
            event_data.get("exclusion_tags", []),
            event_id,
            field_name="exclusion_tags",
            allow_empty=True,
        )
        requirements = self._validate_requirements(
            event_data.get("requirements", {}),
            event_id,
            scope="event",
        )
        character_ids = self._validate_character_ids(event_data.get("character_ids", []), event_id, scope="event")
        min_floor = self._validate_optional_non_negative_int(event_data.get("min_floor"), event_id, "min_floor")
        max_floor = self._validate_optional_non_negative_int(event_data.get("max_floor"), event_id, "max_floor")
        min_act = self._validate_optional_positive_int(event_data.get("min_act"), event_id, "min_act")
        max_act = self._validate_optional_positive_int(event_data.get("max_act"), event_id, "max_act")

        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Event id must be a non-empty string.")
        if not isinstance(title, str) or not title:
            raise ValueError("Event title must be a non-empty string.")
        if not isinstance(body, str) or not body:
            raise ValueError("Event body must be a non-empty string.")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"Event {event_id} must define at least one choice.")
        if len(choices) > MAX_EVENT_CHOICES:
            raise ValueError(f"Event {event_id} may define at most {MAX_EVENT_CHOICES} choices.")
        if rarity not in ALLOWED_EVENT_RARITIES:
            raise ValueError(f"Event {event_id} has unsupported rarity: {rarity}")
        if not isinstance(base_weight, (int, float)) or base_weight < 0:
            raise ValueError(f"Event {event_id} base_weight must be a non-negative number.")
        if min_floor is not None and max_floor is not None and min_floor > max_floor:
            raise ValueError(f"Event {event_id} min_floor cannot exceed max_floor.")
        if min_act is not None and max_act is not None and min_act > max_act:
            raise ValueError(f"Event {event_id} min_act cannot exceed max_act.")
        if rarity == "special" and min_floor is None and max_floor is None and min_act is None and max_act is None and not requirements:
            raise ValueError(f"Special event {event_id} must declare at least one gating requirement.")

        validated_choices = []
        seen_choice_ids: set[str] = set()
        for raw_choice in choices:
            choice = self._validate_choice(raw_choice, event_id)
            if choice["id"] in seen_choice_ids:
                raise ValueError(f"Event {event_id} contains duplicate choice id: {choice['id']}")
            seen_choice_ids.add(choice["id"])
            validated_choices.append(choice)
        secret_choice_count = sum(
            1 for choice in validated_choices if choice["ui_role"] == "secret_corruption"
        )
        if secret_choice_count > 1:
            raise ValueError(f"Event {event_id} may define at most one secret corruption UI choice.")

        return {
            "id": event_id,
            "title": title,
            "body": body,
            "rarity": rarity,
            "base_weight": float(base_weight),
            "tags": tags,
            "primary_tag": tags[0],
            "exclusion_tags": exclusion_tags,
            "requirements": requirements,
            "character_ids": character_ids,
            "min_floor": min_floor,
            "max_floor": max_floor,
            "min_act": min_act,
            "max_act": max_act,
            "choices": validated_choices,
        }

    def _validate_choice(self, choice_data: dict[str, Any], event_id: str) -> dict[str, Any]:
        if not isinstance(choice_data, dict):
            raise ValueError(f"Event {event_id} has a choice that is not a dictionary.")

        required_keys = {"id", "label", "description", "choice_type"}
        missing_keys = required_keys.difference(choice_data)
        if missing_keys:
            raise ValueError(
                f"Choice in event {event_id} is missing required keys: {', '.join(sorted(missing_keys))}"
            )

        choice_id = choice_data["id"]
        label = choice_data["label"]
        description = choice_data["description"]
        choice_type = choice_data["choice_type"]
        requirements = choice_data.get("requirements", {})
        effects = choice_data.get("effects", [])
        outcomes = choice_data.get("outcomes", [])
        ui_role = choice_data.get("ui_role", "normal")
        character_ids = self._validate_character_ids(choice_data.get("character_ids", []), event_id, scope=f"choice {choice_id}")

        if not isinstance(choice_id, str) or not choice_id:
            raise ValueError(f"Event {event_id} choice id must be a non-empty string.")
        if not isinstance(label, str) or not label:
            raise ValueError(f"Event {event_id} choice label must be a non-empty string.")
        if not isinstance(description, str) or not description:
            raise ValueError(f"Event {event_id} choice description must be a non-empty string.")
        if choice_type not in ALLOWED_EVENT_CHOICE_TYPES:
            raise ValueError(f"Event {event_id} choice {choice_id} has unsupported type: {choice_type}")
        if not isinstance(requirements, dict):
            raise ValueError(f"Event {event_id} choice {choice_id} requirements must be a dictionary.")
        if not isinstance(ui_role, str) or ui_role not in ALLOWED_EVENT_UI_ROLES:
            raise ValueError(f"Event {event_id} choice {choice_id} has unsupported ui_role: {ui_role}")

        validated_requirements = self._validate_requirements(requirements, event_id, scope=f"choice {choice_id}")

        if choice_type == "risk":
            if not isinstance(outcomes, list) or not outcomes:
                raise ValueError(f"Risk choice {choice_id} in event {event_id} must define outcomes.")
            validated_outcomes = [
                self._validate_outcome(outcome, event_id, choice_id) for outcome in outcomes
            ]
            validated_effects: list[dict[str, Any]] = []
        else:
            if not isinstance(effects, list):
                raise ValueError(f"Choice {choice_id} in event {event_id} effects must be a list.")
            validated_effects = [
                self._validate_effect(effect, event_id, choice_id) for effect in effects
            ]
            validated_outcomes = []
            if choice_type == "purge" and not any(
                effect["type"] == "purge_card" for effect in validated_effects
            ):
                raise ValueError(
                    f"Purge choice {choice_id} in event {event_id} must include a purge_card effect."
                )

        return {
            "id": choice_id,
            "label": label,
            "description": description,
            "choice_type": choice_type,
            "requirements": validated_requirements,
            "character_ids": character_ids,
            "effects": validated_effects,
            "outcomes": validated_outcomes,
            "ui_role": ui_role,
        }

    def _validate_character_ids(self, raw_character_ids: Any, event_id: str, *, scope: str) -> list[str]:
        if raw_character_ids in (None, []):
            return []
        if not isinstance(raw_character_ids, list):
            raise ValueError(f"Event {event_id} {scope} character_ids must be a list.")
        validated: list[str] = []
        for character_id in raw_character_ids:
            if character_id not in ALLOWED_CHARACTER_IDS:
                raise ValueError(f"Event {event_id} {scope} uses unsupported character id: {character_id}")
            if character_id not in validated:
                validated.append(character_id)
        return validated

    def _validate_tags(
        self,
        raw_tags: Any,
        event_id: str,
        *,
        field_name: str = "tags",
        allow_empty: bool = False,
    ) -> list[str]:
        if raw_tags in (None, []) and allow_empty:
            return []
        if not isinstance(raw_tags, list) or not raw_tags:
            raise ValueError(f"Event {event_id} {field_name} must be a non-empty list.")
        validated_tags: list[str] = []
        for tag in raw_tags:
            if tag not in EVENT_TAGS:
                raise ValueError(f"Event {event_id} uses unsupported {field_name} tag: {tag}")
            if tag not in validated_tags:
                validated_tags.append(tag)
        if not validated_tags and not allow_empty:
            raise ValueError(f"Event {event_id} {field_name} must contain at least one supported tag.")
        return validated_tags

    def _validate_requirements(
        self,
        requirements: dict[str, Any],
        event_id: str,
        *,
        scope: str,
    ) -> dict[str, Any]:
        validated: dict[str, Any] = {}
        if not isinstance(requirements, dict):
            raise ValueError(f"Event {event_id} {scope} requirements must be a dictionary.")

        for key, value in requirements.items():
            if key in ALLOWED_INT_EVENT_REQUIREMENTS:
                if not isinstance(value, int) or value < 0:
                    raise ValueError(
                        f"Event {event_id} {scope} requirement {key} must be a non-negative integer."
                    )
                if key == "current_hp_below_percent" and value > 100:
                    raise ValueError(
                        f"Event {event_id} {scope} requirement current_hp_below_percent must be in 0..100."
                    )
                validated[key] = value
                continue

            if key in ALLOWED_MODIFIER_EVENT_REQUIREMENTS:
                if not isinstance(value, str) or not value:
                    raise ValueError(
                        f"Event {event_id} {scope} requirement {key} must be a non-empty modifier id."
                    )
                self.modifier_library.get_modifier(value)
                validated[key] = value
                continue

            raise ValueError(f"Event {event_id} {scope} has unsupported requirement: {key}")
        return validated

    def _validate_effect(
        self,
        effect_data: dict[str, Any],
        event_id: str,
        choice_id: str,
        *,
        allow_random_modifier: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(effect_data, dict):
            raise ValueError(f"Event {event_id} choice {choice_id} effects must be dictionaries.")

        effect_type = effect_data.get("type")
        if effect_type not in ALLOWED_EVENT_EFFECT_TYPES:
            raise ValueError(
                f"Event {event_id} choice {choice_id} has unsupported effect type: {effect_type}"
            )

        if effect_type == "gain_card":
            card_id = effect_data.get("card_id")
            if not isinstance(card_id, str) or not card_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} gain_card effect must define a card_id."
                )
            self.card_library.get_card(card_id)
            return {"type": effect_type, "card_id": card_id}

        if effect_type == "gain_random_modifier":
            if not allow_random_modifier:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} cannot nest gain_random_modifier inside fallback_effects."
                )
            return self._validate_random_modifier_effect(effect_data, event_id, choice_id)

        if effect_type in {"gain_modifier", "gain_status"}:
            modifier_id = effect_data.get("modifier_id")
            if not isinstance(modifier_id, str) or not modifier_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} {effect_type} effect must define a modifier_id."
                )
            self.modifier_library.get_modifier(modifier_id)
            validated_effect = {"type": "gain_modifier", "modifier_id": modifier_id}
            duration = effect_data.get("duration")
            if duration is not None:
                validated_effect["duration"] = self._validate_duration_override(
                    duration,
                    event_id,
                    choice_id,
                    effect_type,
                )
            return validated_effect

        if effect_type in {"remove_modifier", "remove_status", "refresh_modifier", "refresh_status"}:
            modifier_id = effect_data.get("modifier_id")
            if not isinstance(modifier_id, str) or not modifier_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} {effect_type} effect must define a modifier_id."
                )
            self.modifier_library.get_modifier(modifier_id)
            validated_effect = {
                "type": "remove_modifier" if effect_type in {"remove_modifier", "remove_status"} else "refresh_modifier",
                "modifier_id": modifier_id,
            }
            duration = effect_data.get("duration")
            if duration is not None:
                validated_effect["duration"] = self._validate_duration_override(
                    duration,
                    event_id,
                    choice_id,
                    effect_type,
                )
            return validated_effect

        if effect_type == "purge_card":
            return {"type": effect_type}

        if effect_type == "adjust_protocol_drift":
            amount = effect_data.get("amount")
            if not isinstance(amount, int):
                raise ValueError(
                    f"Event {event_id} choice {choice_id} adjust_protocol_drift must define an integer amount."
                )
            return {"type": effect_type, "amount": amount}

        if effect_type == "queue_next_combat_effect":
            return {
                "type": effect_type,
                "effect": self._validate_queued_next_combat_effect(effect_data, event_id, choice_id),
            }

        if effect_type == "remove_card_from_deck_by_id":
            card_id = effect_data.get("card_id")
            count = effect_data.get("count", 1)
            if not isinstance(card_id, str) or not card_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} remove_card_from_deck_by_id must define card_id."
                )
            self.card_library.get_card(card_id)
            if not isinstance(count, int) or count <= 0:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} remove_card_from_deck_by_id count must be a positive integer."
                )
            return {"type": effect_type, "card_id": card_id, "count": count}

        value = effect_data.get("value")
        if not isinstance(value, int) or value < 0:
            raise ValueError(
                f"Event {event_id} choice {choice_id} effect {effect_type} must define a non-negative integer value."
            )
        return {"type": effect_type, "value": value}

    def _validate_queued_next_combat_effect(
        self,
        effect_data: dict[str, Any],
        event_id: str,
        choice_id: str,
    ) -> dict[str, Any]:
        queued_effect = effect_data.get("effect")
        if not isinstance(queued_effect, dict):
            raise ValueError(
                f"Event {event_id} choice {choice_id} queue_next_combat_effect must define an effect payload."
            )

        effect_type = queued_effect.get("type")
        if effect_type not in ALLOWED_QUEUED_NEXT_COMBAT_EFFECT_TYPES:
            raise ValueError(
                f"Event {event_id} choice {choice_id} queue_next_combat_effect uses unsupported payload type: {effect_type}"
            )

        validated: dict[str, Any] = {"type": effect_type}
        if effect_type in {"gain_energy", "draw_cards", "gain_block"}:
            value = queued_effect.get("value")
            if not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued {effect_type} value must be a positive integer."
                )
            validated["value"] = value
            return validated

        if effect_type == "apply_player_status":
            status_id = queued_effect.get("status_id")
            value = queued_effect.get("value", 1)
            if not isinstance(status_id, str) or not status_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued apply_player_status must define status_id."
                )
            if not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued apply_player_status value must be a positive integer."
                )
            validated["status_id"] = status_id
            validated["value"] = value
            return validated

        if effect_type == "add_status_card":
            card_id = queued_effect.get("card_id")
            count = queued_effect.get("count", 1)
            pile = queued_effect.get("pile", "discard")
            if not isinstance(card_id, str) or not card_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued add_status_card must define card_id."
                )
            self.card_library.get_card(card_id)
            if not isinstance(count, int) or count <= 0:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued add_status_card count must be a positive integer."
                )
            if pile not in {"draw", "discard"}:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued add_status_card uses unsupported pile: {pile}"
                )
            validated["card_id"] = card_id
            validated["count"] = count
            validated["pile"] = pile
            return validated

        if effect_type == "add_temporary_card_to_hand":
            card_id = queued_effect.get("card_id")
            if not isinstance(card_id, str) or not card_id:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} queued add_temporary_card_to_hand must define card_id."
                )
            self.card_library.get_card(card_id)
            validated["card_id"] = card_id
            return validated

        return validated

    def _validate_random_modifier_effect(
        self,
        effect_data: dict[str, Any],
        event_id: str,
        choice_id: str,
    ) -> dict[str, Any]:
        unsupported_keys = set(effect_data).difference(ALLOWED_RANDOM_MODIFIER_FIELDS)
        if unsupported_keys:
            raise ValueError(
                f"Event {event_id} choice {choice_id} gain_random_modifier has unsupported fields: {', '.join(sorted(unsupported_keys))}"
            )

        source_type = effect_data.get("source_type")
        rarity_profile = effect_data.get("rarity_profile", "positive")
        allow_types = effect_data.get("allow_types", ["status", "blessing", "curse"])
        allow_rarities = effect_data.get("allow_rarities")
        include_tags = effect_data.get("include_tags", [])
        exclude_tags = effect_data.get("exclude_tags", [])
        duration = effect_data.get("duration")
        fallback_effects = effect_data.get("fallback_effects", [])

        if source_type not in STATUS_SOURCE_TYPES:
            raise ValueError(
                f"Event {event_id} choice {choice_id} gain_random_modifier source_type must be one of: {', '.join(STATUS_SOURCE_TYPES)}"
            )
        if rarity_profile not in {"positive", "risky"}:
            raise ValueError(
                f"Event {event_id} choice {choice_id} gain_random_modifier rarity_profile must be positive or risky."
            )

        if not isinstance(allow_types, list) or not allow_types:
            raise ValueError(
                f"Event {event_id} choice {choice_id} gain_random_modifier allow_types must be a non-empty list."
            )
        normalized_allow_types: list[str] = []
        for modifier_type in allow_types:
            if modifier_type not in ALLOWED_MODIFIER_TYPES:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} gain_random_modifier uses unsupported allow_type: {modifier_type}"
                )
            if modifier_type not in normalized_allow_types:
                normalized_allow_types.append(modifier_type)

        if allow_rarities is None:
            normalized_allow_rarities = None
        else:
            if not isinstance(allow_rarities, list) or not allow_rarities:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} gain_random_modifier allow_rarities must be a non-empty list when provided."
                )
            normalized_allow_rarities = []
            for rarity in allow_rarities:
                if rarity not in ALLOWED_MODIFIER_RARITIES:
                    raise ValueError(
                        f"Event {event_id} choice {choice_id} gain_random_modifier uses unsupported rarity: {rarity}"
                    )
                if rarity not in normalized_allow_rarities:
                    normalized_allow_rarities.append(rarity)

        normalized_include_tags = self._validate_modifier_tags(
            include_tags,
            event_id,
            choice_id,
            "include_tags",
        )
        normalized_exclude_tags = self._validate_modifier_tags(
            exclude_tags,
            event_id,
            choice_id,
            "exclude_tags",
            allow_empty=True,
        )

        if not isinstance(fallback_effects, list):
            raise ValueError(
                f"Event {event_id} choice {choice_id} gain_random_modifier fallback_effects must be a list when provided."
            )

        validated_effect: dict[str, Any] = {
            "type": "gain_random_modifier",
            "source_type": source_type,
            "rarity_profile": rarity_profile,
            "allow_types": normalized_allow_types,
            "allow_rarities": normalized_allow_rarities,
            "include_tags": normalized_include_tags,
            "exclude_tags": normalized_exclude_tags,
            "fallback_effects": [
                self._validate_effect(
                    fallback_effect,
                    event_id,
                    choice_id,
                    allow_random_modifier=False,
                )
                for fallback_effect in fallback_effects
            ],
        }
        if duration is not None:
            validated_effect["duration"] = self._validate_duration_override(
                duration,
                event_id,
                choice_id,
                "gain_random_modifier",
            )
        return validated_effect

    def _validate_modifier_tags(
        self,
        raw_tags: Any,
        event_id: str,
        choice_id: str,
        field_name: str,
        *,
        allow_empty: bool = False,
    ) -> list[str]:
        supported_tags = set(self.modifier_library.supported_tags())
        if raw_tags in (None, []) and allow_empty:
            return []
        if not isinstance(raw_tags, list) or not raw_tags:
            raise ValueError(
                f"Event {event_id} choice {choice_id} gain_random_modifier {field_name} must be a non-empty list."
            )
        validated: list[str] = []
        for tag in raw_tags:
            if tag not in supported_tags:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} gain_random_modifier uses unsupported {field_name} tag: {tag}"
                )
            if tag not in validated:
                validated.append(tag)
        return validated

    def _validate_duration_override(
        self,
        duration_data: Any,
        event_id: str,
        choice_id: str,
        effect_type: str,
    ) -> dict[str, Any]:
        if not isinstance(duration_data, dict):
            raise ValueError(
                f"Event {event_id} choice {choice_id} {effect_type} duration must be a dictionary."
            )
        duration_type = duration_data.get("type")
        value = duration_data.get("value")
        if duration_type not in {"permanent", "combat", "floor"}:
            raise ValueError(
                f"Event {event_id} choice {choice_id} {effect_type} duration type is unsupported: {duration_type}"
            )
        if duration_type == "permanent":
            return {"type": "permanent", "value": None}
        if not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"Event {event_id} choice {choice_id} {effect_type} duration value must be a positive integer."
            )
        return {"type": duration_type, "value": value}

    def _validate_outcome(
        self,
        outcome_data: dict[str, Any],
        event_id: str,
        choice_id: str,
    ) -> dict[str, Any]:
        if not isinstance(outcome_data, dict):
            raise ValueError(f"Event {event_id} risk choice {choice_id} outcomes must be dictionaries.")

        required_keys = {"id", "weight", "summary", "effects"}
        missing_keys = required_keys.difference(outcome_data)
        if missing_keys:
            raise ValueError(
                f"Outcome in event {event_id} choice {choice_id} is missing required keys: {', '.join(sorted(missing_keys))}"
            )

        outcome_id = outcome_data["id"]
        weight = outcome_data["weight"]
        summary = outcome_data["summary"]
        effects = outcome_data["effects"]

        if not isinstance(outcome_id, str) or not outcome_id:
            raise ValueError(f"Event {event_id} choice {choice_id} outcome id must be a non-empty string.")
        if not isinstance(weight, int) or weight <= 0:
            raise ValueError(f"Event {event_id} choice {choice_id} outcome {outcome_id} must have positive weight.")
        if not isinstance(summary, str) or not summary:
            raise ValueError(f"Event {event_id} choice {choice_id} outcome {outcome_id} must have a summary.")
        if not isinstance(effects, list):
            raise ValueError(
                f"Event {event_id} choice {choice_id} outcome {outcome_id} effects must be a list."
            )

        return {
            "id": outcome_id,
            "weight": weight,
            "summary": summary,
            "effects": [
                self._validate_effect(effect, event_id, f"{choice_id}.{outcome_id}") for effect in effects
            ],
        }

    def _validate_optional_non_negative_int(
        self,
        value: Any,
        event_id: str,
        field_name: str,
    ) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"Event {event_id} {field_name} must be a non-negative integer when provided.")
        return value

    def _validate_optional_positive_int(
        self,
        value: Any,
        event_id: str,
        field_name: str,
    ) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"Event {event_id} {field_name} must be a positive integer when provided.")
        return value


def simulate_event_library() -> dict[str, Any]:
    library = EventLibrary()
    events = library.list_events()
    first_event = events[0]
    return {
        "event_count": len(events),
        "first_event_id": first_event["id"],
        "first_event_rarity": first_event["rarity"],
        "first_event_primary_tag": first_event["primary_tag"],
        "first_choice_count": len(first_event["choices"]),
    }
