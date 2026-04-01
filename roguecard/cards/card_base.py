from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CardEffect:
    type: str
    value: int

    @classmethod
    def from_dict(cls, effect_data: dict[str, Any]) -> "CardEffect":
        if not isinstance(effect_data, dict):
            raise ValueError("Card effect entries must be dictionaries.")

        effect_type = effect_data.get("type")
        value = effect_data.get("value")
        if not isinstance(effect_type, str) or not effect_type:
            raise ValueError("Card effect type must be a non-empty string.")
        if not isinstance(value, int):
            raise ValueError("Card effect value must be an integer.")
        return cls(type=effect_type, value=value)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "value": self.value}


@dataclass(frozen=True)
class CardBase:
    id: str
    name: str
    cost: int
    type: str
    effects: list[CardEffect]

    @classmethod
    def from_dict(cls, card_data: dict[str, Any]) -> "CardBase":
        if not isinstance(card_data, dict):
            raise ValueError("Card definitions must be dictionaries.")

        required_keys = {"id", "name", "cost", "type", "effects"}
        missing_keys = required_keys.difference(card_data)
        if missing_keys:
            missing_display = ", ".join(sorted(missing_keys))
            raise ValueError(f"Card is missing required keys: {missing_display}")

        card_id = card_data["id"]
        name = card_data["name"]
        cost = card_data["cost"]
        card_type = card_data["type"]
        effects_data = card_data["effects"]

        if not isinstance(card_id, str) or not card_id:
            raise ValueError("Card id must be a non-empty string.")
        if not isinstance(name, str) or not name:
            raise ValueError("Card name must be a non-empty string.")
        if not isinstance(cost, int) or cost < 0:
            raise ValueError("Card cost must be a non-negative integer.")
        if not isinstance(card_type, str) or not card_type:
            raise ValueError("Card type must be a non-empty string.")
        if not isinstance(effects_data, list) or not effects_data:
            raise ValueError("Card effects must be a non-empty list.")

        effects = [CardEffect.from_dict(effect) for effect in effects_data]
        return cls(
            id=card_id,
            name=name,
            cost=cost,
            type=card_type,
            effects=effects,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cost": self.cost,
            "type": self.type,
            "effects": [effect.to_dict() for effect in self.effects],
        }


def simulate_card_base() -> dict[str, Any]:
    strike = CardBase.from_dict(
        {
            "id": "strike_01",
            "name": "Strike",
            "cost": 1,
            "type": "attack",
            "effects": [{"type": "damage", "value": 6}],
        }
    )
    return {
        "card": strike.to_dict(),
        "effect_count": len(strike.effects),
    }
