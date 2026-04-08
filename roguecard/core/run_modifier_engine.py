from __future__ import annotations

import math
import random
from typing import Any

from config import STATUS_RARITY_WEIGHTS
from core.run_modifier_library import RunModifierLibrary

INTENSITY_SCALABLE_EFFECT_TYPES = {
    "gain_credits",
    "lose_credits",
    "damage",
    "modify_max_hp",
    "modify_healing_multiplier_percent",
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
    "heal_after_event",
    "lose_credits_each_floor",
    "reduce_first_block_each_combat",
    "bonus_attack_damage_if_attacked_last_turn",
    "cost_surcharge_after_first_card",
}
STACK_COUNT_REPEATABLE_EFFECT_TYPES = {
    "gain_credits",
    "lose_credits",
    "damage",
    "gain_block",
    "lose_block",
    "draw_cards",
    "gain_energy",
    "heal",
    "extra_card_choice",
}


class RunModifierEngine:
    def __init__(self, modifier_library: RunModifierLibrary) -> None:
        self.modifier_library = modifier_library

    def generate_starter_offers(self, rng: random.Random) -> list[str]:
        weighted_draft_pool = self.weighted_modifier_candidates(
            active_modifiers=[],
            source_type="run_start",
            rarity_profile="positive",
            draft_only=True,
            allow_types=["relic", "blessing", "status"],
        )
        safe_offer_ids = self._pick_weighted_ids(weighted_draft_pool, rng, count=2)

        risky_pool = self.weighted_modifier_candidates(
            active_modifiers=[],
            source_type="run_start",
            rarity_profile="risky",
            draft_only=True,
            pool_ids=[
                candidate["modifier"]["id"]
                for candidate in self.weighted_modifier_candidates(
                    active_modifiers=[],
                    source_type="run_start",
                    rarity_profile="risky",
                    draft_only=True,
                )
                if candidate["modifier"]["id"] not in safe_offer_ids
            ],
        )
        final_offer_ids = list(safe_offer_ids)
        final_offer_ids.extend(self._pick_weighted_ids(risky_pool, rng, count=1))

        if len(final_offer_ids) < 3:
            fallback_pool = self.weighted_modifier_candidates(
                active_modifiers=[],
                source_type="run_start",
                rarity_profile="risky",
                draft_only=True,
                pool_ids=[
                    modifier["id"]
                    for modifier in self.modifier_library.list_modifiers(
                        draft_only=True,
                        source_type="run_start",
                    )
                    if modifier["id"] not in final_offer_ids
                ],
            )
            final_offer_ids.extend(self._pick_weighted_ids(fallback_pool, rng, count=3 - len(final_offer_ids)))

        return final_offer_ids[:3]

    def has_modifier(self, active_modifiers: list[dict[str, Any]], modifier_id: str) -> bool:
        return self.get_modifier_record(active_modifiers, modifier_id) is not None

    def get_modifier_record(
        self,
        active_modifiers: list[dict[str, Any]],
        modifier_id: str,
    ) -> dict[str, Any] | None:
        return next(
            (modifier for modifier in active_modifiers if modifier.get("id") == modifier_id),
            None,
        )

    def can_gain_modifier(
        self,
        active_modifiers: list[dict[str, Any]],
        modifier_id: str,
    ) -> tuple[bool, str | None]:
        existing = self.get_modifier_record(active_modifiers, modifier_id)
        if existing is None:
            return True, None

        modifier = self.modifier_library.get_modifier(modifier_id)
        if modifier["stack_behavior"] in {"refresh_duration", "stack_intensity", "stack_count"}:
            return True, None
        return False, f"Already active: {modifier['name']}."

    def create_modifier_record(
        self,
        modifier_id: str,
        source: str,
        source_detail: str | None = None,
        duration_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        modifier = self.modifier_library.get_modifier(modifier_id)
        duration = self._resolved_duration(modifier, duration_override)
        return {
            "id": modifier_id,
            "source": source,
            "source_detail": source_detail,
            "duration_type": duration["type"],
            "remaining": duration["value"],
            "active_in_current_combat": False,
            "stack_count": 1,
            "stack_intensity": 1,
        }

    def refresh_modifier_record(
        self,
        record: dict[str, Any],
        duration_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        modifier = self.modifier_library.get_modifier(record["id"])
        duration = self._resolved_duration(modifier, duration_override)
        record["duration_type"] = duration["type"]
        record["remaining"] = duration["value"]
        record["active_in_current_combat"] = False
        record["stack_count"] = max(1, int(record.get("stack_count", 1)))
        record["stack_intensity"] = max(1, int(record.get("stack_intensity", 1)))
        return record

    def increment_modifier_record(
        self,
        record: dict[str, Any],
        *,
        duration_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        modifier = self.modifier_library.get_modifier(record["id"])
        stack_behavior = modifier["stack_behavior"]
        if stack_behavior == "stack_intensity":
            record["stack_intensity"] = max(1, int(record.get("stack_intensity", 1))) + 1
        elif stack_behavior == "stack_count":
            record["stack_count"] = max(1, int(record.get("stack_count", 1))) + 1
        if duration_override is not None or modifier["duration"]["type"] != "permanent":
            self.refresh_modifier_record(record, duration_override=duration_override)
        return record

    def hydrate_modifier(self, modifier_record: dict[str, Any]) -> dict[str, Any]:
        modifier_id = modifier_record["id"]
        modifier = self.modifier_library.get_modifier(modifier_id)
        duration_type = modifier_record.get("duration_type", modifier["duration"]["type"])
        remaining = modifier_record.get("remaining", modifier["duration"]["value"])
        duration_label = self._duration_label(
            duration_type,
            remaining,
            bool(modifier_record.get("active_in_current_combat", False)),
        )
        stack_count = max(1, int(modifier_record.get("stack_count", 1)))
        stack_intensity = max(1, int(modifier_record.get("stack_intensity", 1)))
        return {
            **modifier,
            "type": modifier["type"],
            "kind": modifier["type"],
            "source": modifier_record.get("source", "unknown"),
            "source_detail": modifier_record.get("source_detail"),
            "duration_type": duration_type,
            "remaining": remaining,
            "duration_label": duration_label,
            "temporary": duration_type != "permanent",
            "stack_count": stack_count,
            "stack_intensity": stack_intensity,
        }

    def snapshot(self, active_modifiers: list[dict[str, Any]]) -> dict[str, Any]:
        active = [self.hydrate_modifier(modifier) for modifier in active_modifiers]
        return {
            "active": active,
            "count": len(active),
            "primary_label": None if not active else active[0]["name"],
        }

    def get_effects(
        self,
        active_modifiers: list[dict[str, Any]],
        hook_name: str,
    ) -> list[dict[str, Any]]:
        effects: list[dict[str, Any]] = []
        for modifier_record in active_modifiers:
            modifier = self.modifier_library.get_modifier(modifier_record["id"])
            stack_count = max(1, int(modifier_record.get("stack_count", 1)))
            stack_intensity = max(1, int(modifier_record.get("stack_intensity", 1)))
            stack_behavior = modifier["stack_behavior"]
            for effect in modifier.get("hooks", {}).get(hook_name, []):
                effect_payload = {
                    **effect,
                    "modifier_id": modifier["id"],
                    "modifier_name": modifier["name"],
                    "modifier_type": modifier["type"],
                }
                scaled_effect = self._apply_stack_intensity(effect_payload, stack_intensity)
                repeat_count = (
                    stack_count
                    if stack_behavior == "stack_count"
                    and scaled_effect["type"] in STACK_COUNT_REPEATABLE_EFFECT_TYPES
                    else 1
                )
                for _ in range(repeat_count):
                    effects.append(dict(scaled_effect))
        return effects

    def reward_card_choice_bonus(self, active_modifiers: list[dict[str, Any]]) -> int:
        return sum(
            effect["value"]
            for effect in self.get_effects(active_modifiers, "on_reward")
            if effect["type"] == "extra_card_choice"
        )

    def price_for_offer(
        self,
        base_price: int,
        offer_type: str,
        active_modifiers: list[dict[str, Any]],
        runtime_flags: dict[str, Any],
        shop_node_id: str | None,
    ) -> int:
        if base_price <= 0:
            return 0

        effects = self.get_effects(active_modifiers, "on_shop")
        discounted_price = base_price
        total_discount_percent = 0
        total_surcharge_percent = 0
        total_flat_delta = 0

        for effect in effects:
            effect_type = effect["type"]
            target = effect.get("target")

            if effect_type == "percent_discount" and self._targets_offer_type(target, offer_type):
                total_discount_percent += effect["value"]
            elif effect_type == "percent_surcharge" and self._targets_offer_type(target, offer_type):
                total_surcharge_percent += effect["value"]
            elif effect_type == "flat_discount" and self._targets_offer_type(target, offer_type):
                total_flat_delta -= effect["value"]
            elif effect_type == "free_first_purge_run" and offer_type == "purge":
                if not runtime_flags.get("clean_slate_used", False):
                    return 0
            elif effect_type == "free_first_reroll_shop" and offer_type == "reroll":
                used_shops = set(runtime_flags.get("ghost_warranty_used_shops", []))
                if shop_node_id is not None and shop_node_id not in used_shops:
                    return 0
            elif effect_type == "flat_surcharge_first_card_shop" and offer_type == "card":
                used_shops = set(runtime_flags.get("debt_spike_used_shops", []))
                if shop_node_id is not None and shop_node_id not in used_shops:
                    total_flat_delta += effect["value"]

        if total_discount_percent:
            discount_multiplier = max(0.0, 1.0 - (total_discount_percent / 100.0))
            discounted_price = math.floor(discounted_price * discount_multiplier)
        if total_surcharge_percent:
            surcharge_multiplier = 1.0 + (total_surcharge_percent / 100.0)
            discounted_price = math.ceil(discounted_price * surcharge_multiplier)

        final_price = max(0, discounted_price + total_flat_delta)
        return final_price

    def event_post_resolution_effects(self, active_modifiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.get_effects(active_modifiers, "on_event")

    def filter_post_victory_effects(
        self,
        active_modifiers: list[dict[str, Any]],
        encounter_type: str | None,
    ) -> list[dict[str, Any]]:
        effects = []
        for effect in self.get_effects(active_modifiers, "post_victory"):
            encounter_types = effect.get("encounter_types")
            if encounter_types is not None and encounter_type not in encounter_types:
                continue
            effects.append(effect)
        return effects

    def weighted_modifier_candidates(
        self,
        active_modifiers: list[dict[str, Any]],
        *,
        source_type: str,
        rarity_profile: str,
        allow_types: list[str] | None = None,
        allow_rarities: list[str] | None = None,
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        draft_only: bool = False,
        pool_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        modifiers = self.modifier_library.list_modifiers(draft_only=draft_only, source_type=source_type)
        if pool_ids is not None:
            allowed_pool_ids = set(pool_ids)
            modifiers = [modifier for modifier in modifiers if modifier["id"] in allowed_pool_ids]

        allow_type_set = None if allow_types is None else set(allow_types)
        allow_rarity_set = None if allow_rarities is None else set(allow_rarities)
        include_tag_set = None if not include_tags else set(include_tags)
        exclude_tag_set = set(exclude_tags or [])
        candidates: list[dict[str, Any]] = []

        for modifier in modifiers:
            if allow_type_set is not None and modifier["type"] not in allow_type_set:
                continue
            if allow_rarity_set is not None and modifier["rarity"] not in allow_rarity_set:
                continue
            modifier_tags = set(modifier["tags"])
            if include_tag_set is not None and not include_tag_set.intersection(modifier_tags):
                continue
            if exclude_tag_set and exclude_tag_set.intersection(modifier_tags):
                continue

            existing = self.get_modifier_record(active_modifiers, modifier["id"])
            if existing is not None and modifier["stack_behavior"] == "no_duplicate":
                continue

            weight = modifier["base_weight"]
            weight *= self._rarity_weight(
                modifier["rarity"],
                rarity_profile,
                special_enabled=allow_rarity_set is not None and "special" in allow_rarity_set,
            )
            if weight <= 0:
                continue

            candidates.append({"modifier": modifier, "weight": weight})

        return candidates

    def choose_weighted_modifier(
        self,
        rng: random.Random,
        active_modifiers: list[dict[str, Any]],
        *,
        source_type: str,
        rarity_profile: str,
        allow_types: list[str] | None = None,
        allow_rarities: list[str] | None = None,
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        draft_only: bool = False,
        pool_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        candidates = self.weighted_modifier_candidates(
            active_modifiers,
            source_type=source_type,
            rarity_profile=rarity_profile,
            allow_types=allow_types,
            allow_rarities=allow_rarities,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            draft_only=draft_only,
            pool_ids=pool_ids,
        )
        if not candidates:
            return None

        total_weight = sum(candidate["weight"] for candidate in candidates)
        roll = rng.random() * total_weight
        running_total = 0.0
        for candidate in candidates:
            running_total += candidate["weight"]
            if roll <= running_total:
                return candidate["modifier"]
        return candidates[-1]["modifier"]

    def _resolved_duration(
        self,
        modifier: dict[str, Any],
        duration_override: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not duration_override:
            return dict(modifier["duration"])
        duration_type = duration_override.get("type", modifier["duration"]["type"])
        value = duration_override.get("value", modifier["duration"]["value"])
        return {"type": duration_type, "value": value}

    def _duration_label(
        self,
        duration_type: str,
        remaining: int | None,
        active_in_current_combat: bool = False,
    ) -> str | None:
        if duration_type == "permanent":
            return None
        if duration_type == "combat" and active_in_current_combat and remaining == 0:
            return "Active this combat"
        if remaining is None:
            return None
        if duration_type == "combat":
            unit = "combat" if remaining == 1 else "combats"
            return f"{remaining} {unit} left"
        if duration_type == "floor":
            unit = "floor" if remaining == 1 else "floors"
            return f"{remaining} {unit} left"
        return None

    def _targets_offer_type(self, target: str | None, offer_type: str) -> bool:
        return target in {"all", offer_type}

    def _rarity_weight(
        self,
        rarity: str,
        rarity_profile: str,
        *,
        special_enabled: bool,
    ) -> float:
        if rarity == "special":
            return 1.0 if special_enabled else 0.0
        return STATUS_RARITY_WEIGHTS[rarity_profile][rarity]

    def _apply_stack_intensity(self, effect: dict[str, Any], stack_intensity: int) -> dict[str, Any]:
        if stack_intensity <= 1 or effect["type"] not in INTENSITY_SCALABLE_EFFECT_TYPES:
            return dict(effect)
        scaled_effect = dict(effect)
        if isinstance(effect.get("value"), int):
            scaled_effect["value"] = effect["value"] * stack_intensity
        return scaled_effect

    def _pick_weighted_ids(
        self,
        weighted_candidates: list[dict[str, Any]],
        rng: random.Random,
        *,
        count: int,
    ) -> list[str]:
        pool = [dict(candidate) for candidate in weighted_candidates]
        chosen_ids: list[str] = []
        while pool and len(chosen_ids) < count:
            total_weight = sum(candidate["weight"] for candidate in pool)
            roll = rng.random() * total_weight
            running_total = 0.0
            chosen_index = len(pool) - 1
            for index, candidate in enumerate(pool):
                running_total += candidate["weight"]
                if roll <= running_total:
                    chosen_index = index
                    break
            chosen_ids.append(pool.pop(chosen_index)["modifier"]["id"])
        return chosen_ids


def simulate_run_modifier_engine() -> dict[str, Any]:
    library = RunModifierLibrary()
    engine = RunModifierEngine(library)
    rng = random.Random(19)
    offers = engine.generate_starter_offers(rng)
    snapshot = engine.snapshot([engine.create_modifier_record(offers[0], source="starter")])
    card_price = engine.price_for_offer(
        base_price=50,
        offer_type="card",
        active_modifiers=[engine.create_modifier_record("market_key", source="starter")],
        runtime_flags={},
        shop_node_id="floor_1_node_0",
    )
    weighted_event_pick = engine.choose_weighted_modifier(
        rng=random.Random(41),
        active_modifiers=[],
        source_type="event",
        rarity_profile="positive",
        allow_types=["status", "blessing"],
        include_tags=["energy"],
    )
    return {
        "offer_count": len(offers),
        "snapshot_count": snapshot["count"],
        "card_price": card_price,
        "weighted_pick": None if weighted_event_pick is None else weighted_event_pick["id"],
    }
