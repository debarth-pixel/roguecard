from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cards.card_library import CardLibrary
from config import EVENTS_DATA_PATH

ALLOWED_EVENT_CHOICE_TYPES = {"effect", "purge", "risk"}
ALLOWED_EVENT_REQUIREMENTS = {"credits_at_least", "missing_hp_at_least", "deck_size_at_least"}
ALLOWED_EVENT_EFFECT_TYPES = {
    "gain_credits",
    "lose_credits",
    "gain_card",
    "heal",
    "damage",
    "purge_card",
}


class EventLibrary:
    def __init__(
        self,
        data_path: Path = EVENTS_DATA_PATH,
        card_library: CardLibrary | None = None,
    ) -> None:
        self.data_path = data_path
        self.card_library = card_library or CardLibrary()
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

        required_keys = {"id", "title", "body", "choices"}
        missing_keys = required_keys.difference(event_data)
        if missing_keys:
            raise ValueError(f"Event is missing required keys: {', '.join(sorted(missing_keys))}")

        event_id = event_data["id"]
        title = event_data["title"]
        body = event_data["body"]
        choices = event_data["choices"]

        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Event id must be a non-empty string.")
        if not isinstance(title, str) or not title:
            raise ValueError("Event title must be a non-empty string.")
        if not isinstance(body, str) or not body:
            raise ValueError("Event body must be a non-empty string.")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"Event {event_id} must define at least one choice.")

        validated_choices = []
        seen_choice_ids: set[str] = set()
        for raw_choice in choices:
            choice = self._validate_choice(raw_choice, event_id)
            if choice["id"] in seen_choice_ids:
                raise ValueError(f"Event {event_id} contains duplicate choice id: {choice['id']}")
            seen_choice_ids.add(choice["id"])
            validated_choices.append(choice)

        return {
            "id": event_id,
            "title": title,
            "body": body,
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

        validated_requirements = self._validate_requirements(requirements, event_id, choice_id)

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
            "effects": validated_effects,
            "outcomes": validated_outcomes,
        }

    def _validate_requirements(
        self,
        requirements: dict[str, Any],
        event_id: str,
        choice_id: str,
    ) -> dict[str, int]:
        validated: dict[str, int] = {}
        for key, value in requirements.items():
            if key not in ALLOWED_EVENT_REQUIREMENTS:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} has unsupported requirement: {key}"
                )
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"Event {event_id} choice {choice_id} requirement {key} must be a non-negative integer."
                )
            validated[key] = value
        return validated

    def _validate_effect(
        self,
        effect_data: dict[str, Any],
        event_id: str,
        choice_id: str,
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

        if effect_type == "purge_card":
            return {"type": effect_type}

        value = effect_data.get("value")
        if not isinstance(value, int) or value < 0:
            raise ValueError(
                f"Event {event_id} choice {choice_id} effect {effect_type} must define a non-negative integer value."
            )
        return {"type": effect_type, "value": value}

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


def simulate_event_library() -> dict[str, Any]:
    library = EventLibrary()
    event_ids = library.list_event_ids()
    first_event = library.get_event(event_ids[0])
    return {
        "event_count": len(event_ids),
        "first_event_id": first_event["id"],
        "first_choice_count": len(first_event["choices"]),
    }
