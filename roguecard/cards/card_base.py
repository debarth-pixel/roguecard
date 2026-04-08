from __future__ import annotations

from dataclasses import dataclass, field
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
class CardTheme:
    faction: str
    palette: str
    art_style: str

    @classmethod
    def from_dict(cls, theme_data: dict[str, Any]) -> "CardTheme":
        if not isinstance(theme_data, dict):
            raise ValueError("Card theme must be a dictionary.")

        faction = theme_data.get("faction")
        palette = theme_data.get("palette")
        art_style = theme_data.get("art_style")
        if not isinstance(faction, str) or not faction:
            raise ValueError("Card theme faction must be a non-empty string.")
        if not isinstance(palette, str) or not palette:
            raise ValueError("Card theme palette must be a non-empty string.")
        if not isinstance(art_style, str) or not art_style:
            raise ValueError("Card theme art_style must be a non-empty string.")
        return cls(faction=faction, palette=palette, art_style=art_style)

    def to_dict(self) -> dict[str, Any]:
        return {
            "faction": self.faction,
            "palette": self.palette,
            "art_style": self.art_style,
        }


@dataclass(frozen=True)
class CardResourceCost:
    resource: str
    amount: int

    @classmethod
    def from_dict(cls, cost_data: dict[str, Any]) -> "CardResourceCost":
        if not isinstance(cost_data, dict):
            raise ValueError("Card resource costs must be dictionaries.")

        resource = cost_data.get("resource")
        amount = cost_data.get("amount")
        if not isinstance(resource, str) or not resource:
            raise ValueError("Card resource cost resource must be a non-empty string.")
        if not isinstance(amount, int) or amount < 0:
            raise ValueError("Card resource cost amount must be a non-negative integer.")
        return cls(resource=resource, amount=amount)

    def to_dict(self) -> dict[str, Any]:
        return {"resource": self.resource, "amount": self.amount}


@dataclass(frozen=True)
class CardResourceEffect:
    resource: str
    delta: int

    @classmethod
    def from_dict(cls, effect_data: dict[str, Any]) -> "CardResourceEffect":
        if not isinstance(effect_data, dict):
            raise ValueError("Card resource effects must be dictionaries.")

        resource = effect_data.get("resource")
        delta = effect_data.get("delta")
        if not isinstance(resource, str) or not resource:
            raise ValueError("Card resource effect resource must be a non-empty string.")
        if not isinstance(delta, int):
            raise ValueError("Card resource effect delta must be an integer.")
        return cls(resource=resource, delta=delta)

    def to_dict(self) -> dict[str, Any]:
        return {"resource": self.resource, "delta": self.delta}


@dataclass(frozen=True)
class CardBase:
    id: str
    name: str
    cost: int
    type: str
    effects: list[CardEffect]
    theme: CardTheme | None = None
    resource_costs: list[CardResourceCost] = field(default_factory=list)
    resource_effects: list[CardResourceEffect] = field(default_factory=list)

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
        theme_data = card_data.get("theme")
        resource_costs_data = card_data.get("resource_costs", [])
        resource_effects_data = card_data.get("resource_effects", [])

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
        if theme_data is not None and not isinstance(theme_data, dict):
            raise ValueError("Card theme must be a dictionary when provided.")
        if not isinstance(resource_costs_data, list):
            raise ValueError("Card resource_costs must be a list when provided.")
        if not isinstance(resource_effects_data, list):
            raise ValueError("Card resource_effects must be a list when provided.")

        effects = [CardEffect.from_dict(effect) for effect in effects_data]
        theme = None if theme_data is None else CardTheme.from_dict(theme_data)
        resource_costs = [CardResourceCost.from_dict(cost_entry) for cost_entry in resource_costs_data]
        resource_effects = [
            CardResourceEffect.from_dict(effect_entry) for effect_entry in resource_effects_data
        ]
        return cls(
            id=card_id,
            name=name,
            cost=cost,
            type=card_type,
            effects=effects,
            theme=theme,
            resource_costs=resource_costs,
            resource_effects=resource_effects,
        )

    def to_dict(self) -> dict[str, Any]:
        card_data = {
            "id": self.id,
            "name": self.name,
            "cost": self.cost,
            "type": self.type,
            "effects": [effect.to_dict() for effect in self.effects],
        }
        if self.theme is not None:
            card_data["theme"] = self.theme.to_dict()
        if self.resource_costs:
            card_data["resource_costs"] = [cost.to_dict() for cost in self.resource_costs]
        if self.resource_effects:
            card_data["resource_effects"] = [
                effect.to_dict() for effect in self.resource_effects
            ]
        return card_data


def simulate_card_base() -> dict[str, Any]:
    strike = CardBase.from_dict(
        {
            "id": "strike_01",
            "name": "Strike",
            "cost": 1,
            "type": "attack",
            "effects": [{"type": "damage", "value": 6}],
            "theme": {
                "faction": "starter",
                "palette": "starter_neutral",
                "art_style": "circuit_burst",
            },
            "resource_effects": [{"resource": "heat", "delta": 1}],
        }
    )
    return {
        "card": strike.to_dict(),
        "effect_count": len(strike.effects),
        "resource_effect_count": len(strike.resource_effects),
    }
