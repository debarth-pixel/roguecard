from __future__ import annotations

import math
import random
from typing import Any

from core.run_modifier_library import RunModifierLibrary


class RunModifierEngine:
    def __init__(self, modifier_library: RunModifierLibrary) -> None:
        self.modifier_library = modifier_library

    def generate_starter_offers(self, rng: random.Random) -> list[str]:
        draft_ids = self.modifier_library.list_modifier_ids(draft_only=True)
        safe_ids = [
            modifier_id
            for modifier_id in draft_ids
            if self.modifier_library.get_modifier(modifier_id)["kind"] != "curse"
        ]
        full_pool = list(draft_ids)

        chosen_ids: list[str] = []
        safe_pool = list(safe_ids)
        rng.shuffle(safe_pool)
        for modifier_id in safe_pool:
            if len(chosen_ids) >= 2:
                break
            chosen_ids.append(modifier_id)

        remaining_full_pool = [modifier_id for modifier_id in full_pool if modifier_id not in chosen_ids]
        rng.shuffle(remaining_full_pool)
        if remaining_full_pool:
            chosen_ids.append(remaining_full_pool[0])

        fallback_pool = [modifier_id for modifier_id in full_pool if modifier_id not in chosen_ids]
        rng.shuffle(fallback_pool)
        while len(chosen_ids) < min(3, len(full_pool)) and fallback_pool:
            chosen_ids.append(fallback_pool.pop(0))

        return chosen_ids[:3]

    def has_modifier(self, active_modifiers: list[dict[str, Any]], modifier_id: str) -> bool:
        return any(modifier.get("id") == modifier_id for modifier in active_modifiers)

    def hydrate_modifier(self, modifier_record: dict[str, Any]) -> dict[str, Any]:
        modifier_id = modifier_record["id"]
        modifier = self.modifier_library.get_modifier(modifier_id)
        return {
            **modifier,
            "source": modifier_record.get("source", "unknown"),
            "source_detail": modifier_record.get("source_detail"),
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
            for effect in modifier.get("hooks", {}).get(hook_name, []):
                effects.append(
                    {
                        **effect,
                        "modifier_id": modifier["id"],
                        "modifier_name": modifier["name"],
                        "modifier_kind": modifier["kind"],
                    }
                )
        return effects

    def reward_card_choice_bonus(self, active_modifiers: list[dict[str, Any]]) -> int:
        return sum(
            effect["value"]
            for effect in self.get_effects(active_modifiers, "reward_generation")
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

        effects = self.get_effects(active_modifiers, "shop_pricing")
        discounted_price = base_price
        total_discount_percent = 0
        total_flat_delta = 0

        for effect in effects:
            effect_type = effect["type"]
            target = effect.get("target")

            if effect_type == "percent_discount" and self._targets_offer_type(target, offer_type):
                total_discount_percent += effect["value"]
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

        final_price = max(0, discounted_price + total_flat_delta)
        return final_price

    def mark_shop_purchase(
        self,
        offer_type: str,
        runtime_flags: dict[str, Any],
        shop_node_id: str | None,
    ) -> None:
        if offer_type == "purge":
            if any(
                effect["type"] == "free_first_purge_run"
                for effect in self.get_effects_from_flags(runtime_flags, "clean_slate")
            ):
                runtime_flags["clean_slate_used"] = True
                return
            if runtime_flags.get("clean_slate_used") is False:
                runtime_flags["clean_slate_used"] = True

        if offer_type == "card" and shop_node_id is not None:
            used_shops = set(runtime_flags.get("debt_spike_used_shops", []))
            used_shops.add(shop_node_id)
            runtime_flags["debt_spike_used_shops"] = sorted(used_shops)

    def mark_shop_reroll(
        self,
        runtime_flags: dict[str, Any],
        shop_node_id: str | None,
    ) -> None:
        if shop_node_id is None:
            return
        used_shops = set(runtime_flags.get("ghost_warranty_used_shops", []))
        used_shops.add(shop_node_id)
        runtime_flags["ghost_warranty_used_shops"] = sorted(used_shops)

    def event_post_resolution_heal(self, active_modifiers: list[dict[str, Any]]) -> int:
        return sum(
            effect["value"]
            for effect in self.get_effects(active_modifiers, "event_value")
            if effect["type"] == "heal_after_event"
        )

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

    def get_effects_from_flags(
        self,
        runtime_flags: dict[str, Any],
        modifier_id: str,
    ) -> list[dict[str, Any]]:
        active_ids = runtime_flags.get("_active_modifier_ids", [])
        if modifier_id not in active_ids:
            return []
        modifier = self.modifier_library.get_modifier(modifier_id)
        return [
            {
                **effect,
                "modifier_id": modifier["id"],
                "modifier_name": modifier["name"],
                "modifier_kind": modifier["kind"],
            }
            for effect in modifier.get("hooks", {}).get("shop_pricing", [])
        ]

    def _targets_offer_type(self, target: str | None, offer_type: str) -> bool:
        return target in {"all", offer_type}


def simulate_run_modifier_engine() -> dict[str, Any]:
    library = RunModifierLibrary()
    engine = RunModifierEngine(library)
    rng = random.Random(19)
    offers = engine.generate_starter_offers(rng)
    snapshot = engine.snapshot([{"id": offers[0], "source": "starter"}])
    card_price = engine.price_for_offer(
        base_price=50,
        offer_type="card",
        active_modifiers=[{"id": "market_key", "source": "starter"}],
        runtime_flags={},
        shop_node_id="floor_1_node_0",
    )
    return {
        "offer_count": len(offers),
        "snapshot_count": snapshot["count"],
        "card_price": card_price,
    }
