from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_CARD_TYPES = {"attack", "skill", "power", "status"}
ALLOWED_CARD_OWNERS = {"shared", "enforcer", "operator", "bio_hacker"}
ALLOWED_CARD_KEYWORDS = {"retain", "exhaust", "combat_only"}
ALLOWED_CARD_TRIGGER_HOOKS = {
    "on_draw",
    "turn_start",
    "turn_end",
    "after_card_played",
    "after_attack_played",
    "on_self_damage",
    "on_status_drawn",
}
DIRECT_DAMAGE_EFFECT_TYPES = {"damage", "multi_damage", "lifesteal_damage"}
ALLOWED_CARD_EFFECT_TYPES = DIRECT_DAMAGE_EFFECT_TYPES | {
    "noop",
    "block",
    "heal",
    "draw",
    "energy",
    "self_damage",
    "gain_strength",
    "apply_weak",
    "apply_vulnerable",
    "modify_next_card_cost",
    "modify_next_attack_damage",
    "add_status_card",
    "random_one_of",
    "exhaust_drawn_card",
}
ALLOWED_TRIGGER_CONDITION_KEYS = {
    "first_card_this_turn",
    "played_card_type",
    "below_hp_ratio",
}
ALLOWED_EFFECT_TARGETS = {"self", "enemy", "all_enemies", "drawn_card"}
ALLOWED_CARD_PILES = {"draw", "discard"}


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
    effects: list[dict[str, Any]]
    owners: list[str]
    shop_price: int
    theme: CardTheme | None = None
    keywords: list[str] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    resource_costs: list[CardResourceCost] = field(default_factory=list)
    resource_effects: list[CardResourceEffect] = field(default_factory=list)

    @classmethod
    def from_dict(cls, card_data: dict[str, Any]) -> "CardBase":
        if not isinstance(card_data, dict):
            raise ValueError("Card definitions must be dictionaries.")

        required_keys = {"id", "name", "cost", "type", "effects", "owners", "shop_price"}
        missing_keys = required_keys.difference(card_data)
        if missing_keys:
            missing_display = ", ".join(sorted(missing_keys))
            raise ValueError(f"Card is missing required keys: {missing_display}")

        card_id = card_data["id"]
        name = card_data["name"]
        cost = card_data["cost"]
        card_type = str(card_data["type"]).strip().lower()
        effects_data = card_data["effects"]
        owners_data = card_data["owners"]
        shop_price = card_data["shop_price"]
        theme_data = card_data.get("theme")
        keywords_data = card_data.get("keywords", [])
        triggers_data = card_data.get("triggers", [])
        resource_costs_data = card_data.get("resource_costs", [])
        resource_effects_data = card_data.get("resource_effects", [])

        if not isinstance(card_id, str) or not card_id:
            raise ValueError("Card id must be a non-empty string.")
        if not isinstance(name, str) or not name:
            raise ValueError("Card name must be a non-empty string.")
        if not isinstance(cost, int) or cost < 0:
            raise ValueError("Card cost must be a non-negative integer.")
        if card_type not in ALLOWED_CARD_TYPES:
            raise ValueError(f"Card {card_id} has unsupported type: {card_type}")
        if not isinstance(effects_data, list):
            raise ValueError("Card effects must be a list.")
        if not isinstance(owners_data, list) or not owners_data:
            raise ValueError(f"Card {card_id} owners must be a non-empty list.")
        if not isinstance(shop_price, int) or shop_price < 0:
            raise ValueError(f"Card {card_id} shop_price must be a non-negative integer.")
        if theme_data is not None and not isinstance(theme_data, dict):
            raise ValueError("Card theme must be a dictionary when provided.")
        if not isinstance(keywords_data, list):
            raise ValueError("Card keywords must be a list when provided.")
        if not isinstance(triggers_data, list):
            raise ValueError("Card triggers must be a list when provided.")
        if not isinstance(resource_costs_data, list):
            raise ValueError("Card resource_costs must be a list when provided.")
        if not isinstance(resource_effects_data, list):
            raise ValueError("Card resource_effects must be a list when provided.")

        owners = cls._validate_owners(card_id, owners_data)
        keywords = cls._validate_keywords(card_id, keywords_data)
        effects = [cls._validate_effect(card_id, effect, context="effect") for effect in effects_data]
        triggers = [cls._validate_trigger(card_id, trigger) for trigger in triggers_data]

        if not effects and not triggers:
            raise ValueError(f"Card {card_id} must define at least one effect or trigger.")

        direct_damage_present = any(effect["type"] in DIRECT_DAMAGE_EFFECT_TYPES for effect in effects)
        if card_type == "attack" and not direct_damage_present:
            raise ValueError(f"Attack card {card_id} must include a direct damage effect.")
        if card_type == "skill" and direct_damage_present:
            raise ValueError(f"Skill card {card_id} cannot include direct damage effects.")
        if card_type == "power" and not triggers:
            raise ValueError(f"Power card {card_id} must define at least one trigger.")
        if card_type == "status" and "combat_only" not in keywords:
            raise ValueError(f"Status card {card_id} must include the combat_only keyword.")

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
            owners=owners,
            shop_price=shop_price,
            theme=theme,
            keywords=keywords,
            triggers=triggers,
            resource_costs=resource_costs,
            resource_effects=resource_effects,
        )

    @classmethod
    def _validate_owners(cls, card_id: str, owners_data: list[Any]) -> list[str]:
        owners: list[str] = []
        for owner in owners_data:
            if owner not in ALLOWED_CARD_OWNERS:
                raise ValueError(f"Card {card_id} uses unsupported owner: {owner}")
            if owner not in owners:
                owners.append(owner)
        return owners

    @classmethod
    def _validate_keywords(cls, card_id: str, keywords_data: list[Any]) -> list[str]:
        keywords: list[str] = []
        for keyword in keywords_data:
            if keyword not in ALLOWED_CARD_KEYWORDS:
                raise ValueError(f"Card {card_id} uses unsupported keyword: {keyword}")
            if keyword not in keywords:
                keywords.append(keyword)
        return keywords

    @classmethod
    def _validate_trigger(cls, card_id: str, trigger_data: Any) -> dict[str, Any]:
        if not isinstance(trigger_data, dict):
            raise ValueError(f"Card {card_id} triggers must be dictionaries.")

        hook = trigger_data.get("hook")
        effects = trigger_data.get("effects")
        conditions = trigger_data.get("conditions", {})
        if hook not in ALLOWED_CARD_TRIGGER_HOOKS:
            raise ValueError(f"Card {card_id} uses unsupported trigger hook: {hook}")
        if not isinstance(effects, list) or not effects:
            raise ValueError(f"Card {card_id} trigger {hook} must define at least one effect.")
        if not isinstance(conditions, dict):
            raise ValueError(f"Card {card_id} trigger {hook} conditions must be a dictionary.")

        validated_conditions: dict[str, Any] = {}
        for key, value in conditions.items():
            if key not in ALLOWED_TRIGGER_CONDITION_KEYS:
                raise ValueError(f"Card {card_id} trigger {hook} uses unsupported condition: {key}")
            if key == "first_card_this_turn":
                if not isinstance(value, bool):
                    raise ValueError(f"Card {card_id} trigger {hook} first_card_this_turn must be boolean.")
            elif key == "played_card_type":
                if value not in ALLOWED_CARD_TYPES:
                    raise ValueError(f"Card {card_id} trigger {hook} played_card_type is unsupported: {value}")
            elif key == "below_hp_ratio":
                if not isinstance(value, (int, float)) or value <= 0 or value > 1:
                    raise ValueError(f"Card {card_id} trigger {hook} below_hp_ratio must be in (0, 1].")
            validated_conditions[key] = value

        return {
            "hook": hook,
            "effects": [cls._validate_effect(card_id, effect, context=f"trigger:{hook}") for effect in effects],
            "conditions": validated_conditions,
        }

    @classmethod
    def _validate_effect(
        cls,
        card_id: str,
        effect_data: Any,
        *,
        context: str,
        allow_random: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(effect_data, dict):
            raise ValueError(f"Card {card_id} {context} entries must be dictionaries.")

        effect_type = effect_data.get("type")
        if effect_type not in ALLOWED_CARD_EFFECT_TYPES:
            raise ValueError(f"Card {card_id} uses unsupported effect type: {effect_type}")

        validated: dict[str, Any] = {"type": effect_type}

        if effect_type in {
            "damage",
            "block",
            "heal",
            "draw",
            "energy",
            "self_damage",
            "gain_strength",
            "apply_weak",
            "apply_vulnerable",
            "modify_next_card_cost",
            "modify_next_attack_damage",
            "lifesteal_damage",
            "noop",
        }:
            value = effect_data.get("value")
            if not isinstance(value, int):
                raise ValueError(f"Card {card_id} {effect_type} effects must define an integer value.")
            validated["value"] = value
        elif effect_type == "multi_damage":
            value = effect_data.get("value")
            count = effect_data.get("count")
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"Card {card_id} multi_damage effects must define a positive integer value.")
            if not isinstance(count, int) or count <= 1:
                raise ValueError(f"Card {card_id} multi_damage effects must define a hit count greater than 1.")
            validated["value"] = value
            validated["count"] = count
        elif effect_type == "add_status_card":
            card_ref = effect_data.get("card_id")
            count = effect_data.get("count", 1)
            pile = effect_data.get("pile", "discard")
            if not isinstance(card_ref, str) or not card_ref:
                raise ValueError(f"Card {card_id} add_status_card effects must define card_id.")
            if not isinstance(count, int) or count <= 0:
                raise ValueError(f"Card {card_id} add_status_card effects must define a positive count.")
            if pile not in ALLOWED_CARD_PILES:
                raise ValueError(f"Card {card_id} add_status_card effects use unsupported pile: {pile}")
            validated["card_id"] = card_ref
            validated["count"] = count
            validated["pile"] = pile
        elif effect_type == "random_one_of":
            if not allow_random:
                raise ValueError(f"Card {card_id} random_one_of effects cannot be nested.")
            options = effect_data.get("options")
            if not isinstance(options, list) or not options:
                raise ValueError(f"Card {card_id} random_one_of effects must define options.")
            validated["options"] = [
                cls._validate_random_option(card_id, option, context=context) for option in options
            ]
        elif effect_type == "exhaust_drawn_card":
            pass

        target = effect_data.get("target")
        if target is not None:
            if target not in ALLOWED_EFFECT_TARGETS:
                raise ValueError(f"Card {card_id} {effect_type} uses unsupported target: {target}")
            validated["target"] = target
        return validated

    @classmethod
    def _validate_random_option(
        cls,
        card_id: str,
        option_data: Any,
        *,
        context: str,
    ) -> dict[str, Any]:
        if not isinstance(option_data, dict):
            raise ValueError(f"Card {card_id} {context} random options must be dictionaries.")
        effects = option_data.get("effects")
        weight = option_data.get("weight", 1)
        summary = option_data.get("summary")
        if not isinstance(weight, int) or weight <= 0:
            raise ValueError(f"Card {card_id} random options must define a positive integer weight.")
        if not isinstance(effects, list) or not effects:
            raise ValueError(f"Card {card_id} random options must define effects.")
        if summary is not None and (not isinstance(summary, str) or not summary):
            raise ValueError(f"Card {card_id} random option summaries must be non-empty when provided.")
        return {
            "weight": weight,
            "summary": summary,
            "effects": [cls._validate_effect(card_id, effect, context=context, allow_random=False) for effect in effects],
        }

    def has_keyword(self, keyword: str) -> bool:
        return keyword in self.keywords

    def owned_by(self, owner_id: str) -> bool:
        return owner_id in self.owners

    def is_shared(self) -> bool:
        return "shared" in self.owners

    def to_dict(self) -> dict[str, Any]:
        card_data = {
            "id": self.id,
            "name": self.name,
            "cost": self.cost,
            "type": self.type,
            "effects": [dict(effect) for effect in self.effects],
            "owners": list(self.owners),
            "shop_price": self.shop_price,
        }
        if self.theme is not None:
            card_data["theme"] = self.theme.to_dict()
        if self.keywords:
            card_data["keywords"] = list(self.keywords)
        if self.triggers:
            card_data["triggers"] = copy_triggers(self.triggers)
        if self.resource_costs:
            card_data["resource_costs"] = [cost.to_dict() for cost in self.resource_costs]
        if self.resource_effects:
            card_data["resource_effects"] = [
                effect.to_dict() for effect in self.resource_effects
            ]
        return card_data


def copy_effects(effects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for effect in effects:
        duplicate = dict(effect)
        if "options" in duplicate:
            duplicate["options"] = [
                {
                    "weight": option["weight"],
                    "summary": option.get("summary"),
                    "effects": copy_effects(option["effects"]),
                }
                for option in duplicate["options"]
            ]
        copied.append(duplicate)
    return copied


def copy_triggers(triggers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "hook": trigger["hook"],
            "conditions": dict(trigger.get("conditions", {})),
            "effects": copy_effects(trigger["effects"]),
        }
        for trigger in triggers
    ]


def simulate_card_base() -> dict[str, Any]:
    strike = CardBase.from_dict(
        {
            "id": "strike_01",
            "name": "Strike",
            "cost": 1,
            "type": "attack",
            "owners": ["shared"],
            "shop_price": 45,
            "effects": [{"type": "damage", "value": 6}],
            "theme": {
                "faction": "shared",
                "palette": "starter_neutral",
                "art_style": "circuit_burst",
            },
        }
    )
    return {
        "card": strike.to_dict(),
        "effect_count": len(strike.effects),
        "owner_count": len(strike.owners),
    }
