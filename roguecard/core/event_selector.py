from __future__ import annotations

import random
from typing import Any

from core.protocol_drift import prefers_full_drift_pool

from config import (
    EARLY_MID_LATE_RUN_WEIGHT_MODIFIERS,
    EVENT_RARITY_WEIGHTS,
    EVENT_RECENTLY_SEEN_PENALTY,
    EVENT_SAME_TAG_REPEAT_PENALTY,
    MAX_SEEN_EVENT_MEMORY,
)


class EventSelector:
    def choose_event(
        self,
        events: list[dict[str, Any]],
        context: dict[str, Any],
        rng: random.Random,
    ) -> dict[str, Any]:
        weighted_candidates = self.weighted_candidates(events, context)
        if not weighted_candidates:
            raise ValueError("No eligible events are available for weighted selection.")

        total_weight = sum(candidate["weight"] for candidate in weighted_candidates)
        roll = rng.random() * total_weight
        running_total = 0.0
        for candidate in weighted_candidates:
            running_total += candidate["weight"]
            if roll <= running_total:
                return candidate["event"]
        return weighted_candidates[-1]["event"]

    def weighted_candidates(
        self,
        events: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if prefers_full_drift_pool(context.get("protocol_drift_pct", 0)):
            full_drift_events = [
                event
                for event in events
                if "full_drift_pool" in set(event.get("tags", []))
            ]
            prioritized = self._weighted_candidates_without_full_drift_overlay(full_drift_events, context)
            if prioritized:
                return prioritized
        return self._weighted_candidates_without_full_drift_overlay(events, context)

    def _weighted_candidates_without_full_drift_overlay(
        self,
        events: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        eligible = [event for event in events if self._event_is_eligible(event, context)]
        if not eligible:
            return []

        seen_ids = {entry["event_id"] for entry in context.get("event_history", [])}
        unseen = [event for event in eligible if event["id"] not in seen_ids]
        candidate_pool = unseen if unseen else eligible
        recent_event_ids = {
            entry["event_id"]
            for entry in context.get("event_history", [])[-MAX_SEEN_EVENT_MEMORY:]
            if isinstance(entry, dict) and isinstance(entry.get("event_id"), str)
        }
        recent_tags = [
            entry.get("primary_tag")
            for entry in context.get("event_history", [])[-MAX_SEEN_EVENT_MEMORY:]
            if isinstance(entry, dict) and isinstance(entry.get("primary_tag"), str)
        ]
        last_primary_tag = None if not recent_tags else recent_tags[-1]
        mixed_tag_pool = len({event["primary_tag"] for event in candidate_pool}) > 1

        weighted: list[dict[str, Any]] = []
        for event in candidate_pool:
            if any(tag in recent_tags for tag in event.get("exclusion_tags", [])):
                continue

            weight = event["base_weight"]
            weight *= self._rarity_multiplier(event["rarity"])
            weight *= self._phase_multiplier(event["rarity"], context)
            weight *= self._context_multiplier(event, context)

            if unseen:
                pass
            elif event["id"] in recent_event_ids:
                weight *= EVENT_RECENTLY_SEEN_PENALTY

            if mixed_tag_pool and last_primary_tag is not None and event["primary_tag"] == last_primary_tag:
                weight *= EVENT_SAME_TAG_REPEAT_PENALTY

            if weight > 0:
                weighted.append({"event": event, "weight": weight})

        if weighted:
            return weighted

        return [
            {"event": event, "weight": max(event["base_weight"], 0.01)}
            for event in candidate_pool
        ]

    def _event_is_eligible(self, event: dict[str, Any], context: dict[str, Any]) -> bool:
        character_ids = event.get("character_ids", [])
        character_id = context.get("character_id")
        if character_ids and character_id not in character_ids:
            return False

        floor = context.get("current_floor")
        act = context.get("current_act", 1)
        min_floor = event.get("min_floor")
        max_floor = event.get("max_floor")
        min_act = event.get("min_act")
        max_act = event.get("max_act")

        if isinstance(min_floor, int) and floor is not None and floor < min_floor:
            return False
        if isinstance(max_floor, int) and floor is not None and floor > max_floor:
            return False
        if isinstance(min_act, int) and act < min_act:
            return False
        if isinstance(max_act, int) and act > max_act:
            return False

        return self._requirements_met(event.get("requirements", {}), context)

    def _requirements_met(self, requirements: dict[str, Any], context: dict[str, Any]) -> bool:
        credits = context.get("credits", 0)
        missing_hp = max(0, context.get("max_hp", 0) - context.get("current_hp", 0))
        deck_size = context.get("deck_size", 0)
        status_count = context.get("status_count", 0)
        active_modifier_ids = set(context.get("active_modifier_ids", []))
        current_hp = int(context.get("current_hp", 0) or 0)
        max_hp = max(1, int(context.get("max_hp", 1) or 1))
        protocol_drift_pct = int(context.get("protocol_drift_pct", 0) or 0)

        credits_at_least = requirements.get("credits_at_least")
        if credits_at_least is not None and credits < credits_at_least:
            return False

        credits_at_most = requirements.get("credits_at_most")
        if credits_at_most is not None and credits > credits_at_most:
            return False

        missing_hp_at_least = requirements.get("missing_hp_at_least")
        if missing_hp_at_least is not None and missing_hp < missing_hp_at_least:
            return False

        deck_size_at_least = requirements.get("deck_size_at_least")
        if deck_size_at_least is not None and deck_size < deck_size_at_least:
            return False

        status_count_at_most = requirements.get("status_count_at_most")
        if status_count_at_most is not None and status_count > status_count_at_most:
            return False

        protocol_drift_at_least = requirements.get("protocol_drift_at_least")
        if protocol_drift_at_least is not None and protocol_drift_pct < protocol_drift_at_least:
            return False

        protocol_drift_below = requirements.get("protocol_drift_below")
        if protocol_drift_below is not None and protocol_drift_pct >= protocol_drift_below:
            return False

        current_hp_at_least = requirements.get("current_hp_at_least")
        if current_hp_at_least is not None and current_hp < current_hp_at_least:
            return False

        current_hp_below_percent = requirements.get("current_hp_below_percent")
        if current_hp_below_percent is not None:
            hp_percent = int(round((max(0, current_hp) / max_hp) * 100))
            if hp_percent >= current_hp_below_percent:
                return False

        modifier_active = requirements.get("modifier_active")
        if modifier_active is not None and modifier_active not in active_modifier_ids:
            return False

        modifier_missing = requirements.get("modifier_missing")
        if modifier_missing is not None and modifier_missing in active_modifier_ids:
            return False

        return True

    def _rarity_multiplier(self, rarity: str) -> float:
        if rarity == "special":
            return 1.0
        return EVENT_RARITY_WEIGHTS[rarity]

    def _phase_multiplier(self, rarity: str, context: dict[str, Any]) -> float:
        phase = self._phase_name(
            context.get("current_floor", 0),
            context.get("route_floor_count"),
        )
        multiplier = EARLY_MID_LATE_RUN_WEIGHT_MODIFIERS[phase][rarity]
        if rarity == "special" and multiplier <= 0:
            return 1.0
        return multiplier

    def _phase_name(self, floor: int, route_floor_count: Any) -> str:
        total_route_floors = route_floor_count if isinstance(route_floor_count, int) and route_floor_count > 0 else 15
        early_max_floor = max(1, (total_route_floors // 3) - 1)
        late_min_floor = max(2, total_route_floors - 2)
        if floor <= early_max_floor:
            return "early"
        if floor >= late_min_floor:
            return "late"
        return "mid"

    def _context_multiplier(self, event: dict[str, Any], context: dict[str, Any]) -> float:
        tags = set(event.get("tags", []))
        hp_ratio = context.get("current_hp", 1) / max(1, context.get("max_hp", 1))
        credits = context.get("credits", 0)
        deck_size = context.get("deck_size", 0)
        status_count = context.get("status_count", 0)

        multiplier = 1.0
        if hp_ratio <= 0.5:
            if "recovery" in tags:
                multiplier *= 1.25
            if "combat_prep" in tags:
                multiplier *= 1.08
        elif hp_ratio <= 0.7 and "recovery" in tags:
            multiplier *= 1.12

        if credits >= 60:
            if "merchant_style" in tags:
                multiplier *= 1.18
            if "economy" in tags:
                multiplier *= 1.1
            if "gamble" in tags:
                multiplier *= 1.08
        elif credits >= 35:
            if "merchant_style" in tags:
                multiplier *= 1.1
            if "economy" in tags:
                multiplier *= 1.05

        if deck_size >= 12:
            if "deck_edit" in tags:
                multiplier *= 1.18
            if "upgrade" in tags:
                multiplier *= 1.08
        elif deck_size >= 10 and "deck_edit" in tags:
            multiplier *= 1.08

        if status_count >= 6 and "status_gain" in tags:
            multiplier *= 0.75
        elif status_count >= 4 and "status_gain" in tags:
            multiplier *= 0.85

        return multiplier


def simulate_event_selector() -> dict[str, Any]:
    selector = EventSelector()
    context = {
        "current_floor": 2,
        "route_floor_count": 15,
        "current_act": 1,
        "current_hp": 40,
        "max_hp": 70,
        "credits": 32,
        "deck_size": 11,
        "status_count": 2,
        "active_modifier_ids": [],
        "event_history": [{"event_id": "dead_drop_01", "primary_tag": "economy", "floor": 1}],
    }
    events = [
        {
            "id": "street_clinic_01",
            "rarity": "common",
            "base_weight": 10.0,
            "tags": ["recovery"],
            "primary_tag": "recovery",
            "exclusion_tags": [],
            "requirements": {},
        },
        {
            "id": "memory_scrubber_01",
            "rarity": "common",
            "base_weight": 8.0,
            "tags": ["deck_edit"],
            "primary_tag": "deck_edit",
            "exclusion_tags": [],
            "requirements": {},
        },
    ]
    weighted = selector.weighted_candidates(events, context)
    return {
        "candidate_count": len(weighted),
        "top_event_id": weighted[0]["event"]["id"],
        "top_weight": round(weighted[0]["weight"], 4),
    }
