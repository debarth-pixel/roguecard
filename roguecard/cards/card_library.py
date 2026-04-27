from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

from cards.card_base import CardBase
from config import CARDS_DATA_PATH


class CardLibrary:
    def __init__(self, data_path: Path = CARDS_DATA_PATH) -> None:
        self.data_path = data_path
        self._cards: dict[str, CardBase] = {}

    def load_cards(self) -> dict[str, CardBase]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("cards.json must contain a list of card definitions.")

        loaded_cards: dict[str, CardBase] = {}
        for raw_card in payload:
            if not isinstance(raw_card, dict):
                raise ValueError("cards.json entries must be card definition dictionaries.")
            card = CardBase.from_dict(raw_card)
            if card.id in loaded_cards:
                raise ValueError(f"Duplicate card id detected: {card.id}")
            loaded_cards[card.id] = card

        self._cards = loaded_cards
        return self._cards

    def get_card(self, card_id: str) -> CardBase:
        if not self._cards:
            self.load_cards()

        try:
            return self._cards[card_id]
        except KeyError as error:
            raise KeyError(f"Unknown card id: {card_id}") from error

    def create_card(self, card_id: str) -> CardBase:
        card = copy.deepcopy(self.get_card(card_id))
        card.assign_instance_id(force=True)
        card.clear_temporary_cost_override()
        return card

    def list_cards(self) -> list[CardBase]:
        if not self._cards:
            self.load_cards()
        return [copy.deepcopy(card) for card in self._cards.values()]

    def find_cards(
        self,
        *,
        owners: Iterable[str] | None = None,
        include_types: Iterable[str] | None = None,
        exclude_types: Iterable[str] | None = None,
        hidden: bool | None = None,
        reward_eligible: bool | None = None,
        shop_eligible: bool | None = None,
        generation_tags: Iterable[str] | None = None,
    ) -> list[CardBase]:
        if not self._cards:
            self.load_cards()

        owner_set = None if owners is None else set(owners)
        include_type_set = None if include_types is None else {value.lower() for value in include_types}
        exclude_type_set = set() if exclude_types is None else {value.lower() for value in exclude_types}
        generation_tag_set = None if generation_tags is None else {
            str(value).strip() for value in generation_tags if str(value).strip()
        }
        results: list[CardBase] = []
        for card in self._cards.values():
            if owner_set is not None and not owner_set.intersection(card.owners):
                continue
            if include_type_set is not None and card.type not in include_type_set:
                continue
            if exclude_type_set and card.type in exclude_type_set:
                continue
            if hidden is not None and bool(card.hidden) != hidden:
                continue
            if reward_eligible is not None and bool(card.reward_eligible) != reward_eligible:
                continue
            if shop_eligible is not None and bool(card.shop_eligible) != shop_eligible:
                continue
            if generation_tag_set is not None and not generation_tag_set.issubset(set(card.generation_tags)):
                continue
            results.append(copy.deepcopy(card))
        return results


def simulate_card_library() -> dict[str, Any]:
    library = CardLibrary()
    cards = library.load_cards()
    strike_copy = library.create_card("strike_01")
    return {
        "loaded_cards": {card_id: card.name for card_id, card in cards.items()},
        "copy_card_id": strike_copy.id,
    }
