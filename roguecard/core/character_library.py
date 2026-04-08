from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cards.card_library import CardLibrary
from config import CHARACTERS_DATA_PATH

ALLOWED_CHARACTER_IDS = {"enforcer", "operator", "bio_hacker"}


class CharacterLibrary:
    def __init__(
        self,
        data_path: Path = CHARACTERS_DATA_PATH,
        card_library: CardLibrary | None = None,
    ) -> None:
        self.data_path = data_path
        self.card_library = card_library or CardLibrary()
        self._characters: dict[str, dict[str, Any]] = {}

    def load_characters(self) -> dict[str, dict[str, Any]]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("characters.json must contain a list of character definitions.")

        loaded: dict[str, dict[str, Any]] = {}
        for raw_character in payload:
            character = self._validate_character(raw_character)
            if character["id"] in loaded:
                raise ValueError(f"Duplicate character id detected: {character['id']}")
            loaded[character["id"]] = character

        self._characters = loaded
        return self._characters

    def list_characters(self) -> list[dict[str, Any]]:
        if not self._characters:
            self.load_characters()
        return [copy.deepcopy(character) for character in self._characters.values()]

    def get_character(self, character_id: str) -> dict[str, Any]:
        if not self._characters:
            self.load_characters()
        try:
            return copy.deepcopy(self._characters[character_id])
        except KeyError as error:
            raise KeyError(f"Unknown character id: {character_id}") from error

    def _validate_character(self, character_data: Any) -> dict[str, Any]:
        if not isinstance(character_data, dict):
            raise ValueError("Character definitions must be dictionaries.")

        required_keys = {
            "id",
            "name",
            "subtitle",
            "description",
            "accent_color",
            "palette_key",
            "starting_deck_ids",
            "preview_card_ids",
        }
        missing = required_keys.difference(character_data)
        if missing:
            raise ValueError(f"Character definition missing keys: {', '.join(sorted(missing))}")

        character_id = character_data["id"]
        if character_id not in ALLOWED_CHARACTER_IDS:
            raise ValueError(f"Unsupported character id: {character_id}")

        accent_color = character_data["accent_color"]
        if (
            not isinstance(accent_color, list)
            or len(accent_color) != 3
            or any(not isinstance(channel, int) or channel < 0 or channel > 255 for channel in accent_color)
        ):
            raise ValueError(f"Character {character_id} accent_color must be an RGB list.")

        starting_deck_ids = self._validate_card_ids(character_data["starting_deck_ids"], character_id, "starting_deck_ids")
        preview_card_ids = self._validate_card_ids(character_data["preview_card_ids"], character_id, "preview_card_ids")

        return {
            "id": character_id,
            "name": self._require_text(character_data["name"], character_id, "name"),
            "subtitle": self._require_text(character_data["subtitle"], character_id, "subtitle"),
            "description": self._require_text(character_data["description"], character_id, "description"),
            "accent_color": list(accent_color),
            "palette_key": self._require_text(character_data["palette_key"], character_id, "palette_key"),
            "starting_deck_ids": starting_deck_ids,
            "preview_card_ids": preview_card_ids,
        }

    def _validate_card_ids(
        self,
        card_ids: Any,
        character_id: str,
        field_name: str,
    ) -> list[str]:
        if not isinstance(card_ids, list) or not card_ids:
            raise ValueError(f"Character {character_id} {field_name} must be a non-empty list of card ids.")
        validated: list[str] = []
        for card_id in card_ids:
            if not isinstance(card_id, str) or not card_id:
                raise ValueError(f"Character {character_id} {field_name} must contain non-empty card ids.")
            self.card_library.get_card(card_id)
            validated.append(card_id)
        return validated

    def _require_text(self, value: Any, character_id: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Character {character_id} {field_name} must be a non-empty string.")
        return value.strip()


def simulate_character_library() -> dict[str, Any]:
    library = CharacterLibrary()
    characters = library.list_characters()
    return {
        "character_count": len(characters),
        "ids": [character["id"] for character in characters],
    }
