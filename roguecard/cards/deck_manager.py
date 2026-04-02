from __future__ import annotations

import random

from cards.card_base import CardBase
from config import MAX_HAND_SIZE


class DeckManager:
    def __init__(
        self,
        cards: list[CardBase],
        rng: random.Random | None = None,
        max_hand_size: int = MAX_HAND_SIZE,
    ) -> None:
        self.rng = rng or random.Random()
        self.max_hand_size = max_hand_size
        self.starting_deck = list(cards)
        self.draw_pile = list(cards)
        self.hand: list[CardBase] = []
        self.discard_pile: list[CardBase] = []
        self.exhaust_pile: list[CardBase] = []
        self.shuffle_deck()

    def draw_cards(self, n: int) -> list[CardBase]:
        if n < 0:
            raise ValueError("draw_cards expects a non-negative amount.")

        drawn_cards: list[CardBase] = []
        while len(drawn_cards) < n and len(self.hand) < self.max_hand_size:
            if not self.draw_pile and not self._reshuffle_if_needed():
                break

            if not self.draw_pile:
                break

            card = self.draw_pile.pop(0)
            self.hand.append(card)
            drawn_cards.append(card)

        return drawn_cards

    def discard_card(self, card: CardBase) -> None:
        self._move_from_hand(card, self.discard_pile)

    def exhaust_card(self, card: CardBase) -> None:
        self._move_from_hand(card, self.exhaust_pile)

    def shuffle_deck(self) -> None:
        if not self.draw_pile and self.discard_pile:
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile.clear()
        self.rng.shuffle(self.draw_pile)

    def reset_for_combat(self) -> None:
        self.draw_pile = list(self.starting_deck)
        self.hand.clear()
        self.discard_pile.clear()
        self.exhaust_pile.clear()
        self.shuffle_deck()

    def discard_hand(self) -> None:
        for card in list(self.hand):
            self.discard_card(card)

    def add_to_starting_deck(self, card: CardBase) -> None:
        self.starting_deck.append(card)

    def remove_from_starting_deck(self, index: int) -> CardBase:
        if index < 0 or index >= len(self.starting_deck):
            raise IndexError("Requested deck index is out of range.")
        return self.starting_deck.pop(index)

    def normalize_overworld_deck(self) -> None:
        self.draw_pile = list(self.starting_deck)
        self.hand.clear()
        self.discard_pile.clear()
        self.exhaust_pile.clear()

    def _reshuffle_if_needed(self) -> bool:
        if self.draw_pile or not self.discard_pile:
            return False

        self.draw_pile.extend(self.discard_pile)
        self.discard_pile.clear()
        self.shuffle_deck()
        return True

    def _move_from_hand(self, card: CardBase, destination: list[CardBase]) -> None:
        for index, hand_card in enumerate(self.hand):
            if hand_card is card:
                destination.append(self.hand.pop(index))
                return

        raise ValueError(f"Card {card.id} is not currently in hand.")


def simulate_deck_manager() -> dict[str, int]:
    from cards.card_library import CardLibrary

    library = CardLibrary()
    starter_cards = [
        library.create_card("strike_01"),
        library.create_card("strike_01"),
        library.create_card("strike_01"),
        library.create_card("strike_01"),
        library.create_card("strike_01"),
        library.create_card("strike_01"),
        library.create_card("defend_01"),
        library.create_card("defend_01"),
        library.create_card("defend_01"),
        library.create_card("defend_01"),
        library.create_card("defend_01"),
        library.create_card("defend_01"),
    ]
    deck = DeckManager(starter_cards, rng=random.Random(7))
    first_draw = deck.draw_cards(10)
    deck.discard_hand()
    redraw = deck.draw_cards(3)
    deck.exhaust_card(redraw[0])
    deck.add_to_starting_deck(library.create_card("volley_01"))
    removed_card = deck.remove_from_starting_deck(0)
    deck.normalize_overworld_deck()
    return {
        "first_draw": len(first_draw),
        "redraw": len(redraw),
        "removed_card": removed_card.id,
        "starting_deck": len(deck.starting_deck),
        "draw_pile": len(deck.draw_pile),
        "hand": len(deck.hand),
        "discard_pile": len(deck.discard_pile),
        "exhaust_pile": len(deck.exhaust_pile),
    }
