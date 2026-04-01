from __future__ import annotations

import copy
import json
from pathlib import Path

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
        return copy.deepcopy(self.get_card(card_id))


def simulate_card_library() -> dict[str, Any]:
    library = CardLibrary()
    cards = library.load_cards()
    strike_copy = library.create_card("strike_01")
    return {
        "loaded_cards": {card_id: card.name for card_id, card in cards.items()},
        "copy_card_id": strike_copy.id,
    }
