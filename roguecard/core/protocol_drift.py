from __future__ import annotations

import copy
from typing import Any

DRIFT_TIERS: tuple[dict[str, Any], ...] = (
    {"index": 0, "label": "Stable", "min": 0, "max": 19, "attack_bonus": 0, "skill_bonus": 0, "status_bonus": 0, "feedback_threshold": None},
    {"index": 1, "label": "Signal Noise", "min": 20, "max": 39, "attack_bonus": 1, "skill_bonus": 1, "status_bonus": 0, "feedback_threshold": 7},
    {"index": 2, "label": "Surge", "min": 40, "max": 59, "attack_bonus": 2, "skill_bonus": 2, "status_bonus": 1, "feedback_threshold": 6},
    {"index": 3, "label": "Fracture", "min": 60, "max": 79, "attack_bonus": 3, "skill_bonus": 3, "status_bonus": 1, "feedback_threshold": 5},
    {"index": 4, "label": "Eclipse", "min": 80, "max": 99, "attack_bonus": 4, "skill_bonus": 4, "status_bonus": 1, "feedback_threshold": 4},
    {"index": 5, "label": "Full Drift", "min": 100, "max": 100, "attack_bonus": 5, "skill_bonus": 5, "status_bonus": 1, "feedback_threshold": 3},
)

ATTACK_EFFECT_TYPES = {"damage", "multi_damage", "lifesteal_damage"}
SKILL_EFFECT_TYPES = {"block", "heal"}
STATUS_APPLY_EFFECT_TYPES = {
    "apply_weak",
    "apply_vulnerable",
    "apply_bleed",
    "apply_infect",
    "apply_nullified",
}
LOOP_PRONE_EFFECT_TYPES = {
    "draw",
    "energy",
    "modify_next_card_cost",
    "add_status_card",
}
OVERRIDE_NUMERIC_KEYS = {
    "attack_bonus",
    "skill_bonus",
    "status_bonus",
    "draw_bonus",
    "energy_bonus",
    "cost_reduction_bonus",
    "card_creation_bonus",
}
BACKLASH_PRECEDENCE = ("status", "zero_cost", "power", "skill", "attack")


def clamp_protocol_drift(value: Any) -> int:
    try:
        drift_value = int(value)
    except (TypeError, ValueError):
        drift_value = 0
    return max(0, min(100, drift_value))


def drift_tier(protocol_drift_pct: Any) -> dict[str, Any]:
    pct = clamp_protocol_drift(protocol_drift_pct)
    for tier in DRIFT_TIERS:
        if tier["min"] <= pct <= tier["max"]:
            return dict(tier)
    return dict(DRIFT_TIERS[-1])


def next_drift_threshold(protocol_drift_pct: Any) -> dict[str, Any] | None:
    pct = clamp_protocol_drift(protocol_drift_pct)
    for tier in DRIFT_TIERS:
        if pct < tier["min"]:
            return {"pct": tier["min"], "label": tier["label"]}
    return None


def drift_snapshot(protocol_drift_pct: Any) -> dict[str, Any]:
    pct = clamp_protocol_drift(protocol_drift_pct)
    tier = drift_tier(pct)
    next_threshold = next_drift_threshold(pct)
    return {
        "protocol_drift_pct": pct,
        "tier_index": tier["index"],
        "tier_label": tier["label"],
        "band_index": tier["index"],
        "band_label": tier["label"],
        "next_threshold_pct": None if next_threshold is None else next_threshold["pct"],
        "next_threshold_label": None if next_threshold is None else next_threshold["label"],
        "at_full_drift": pct >= 100,
    }


def ambient_drift_for_node(node_type: str | None) -> int:
    normalized = str(node_type or "").strip().lower()
    if normalized == "boss":
        return 3
    if normalized in {"combat", "elite", "event", "shop"}:
        return 1
    return 0


def unstable_energy_gain(protocol_drift_pct: Any, turn_number: int) -> int:
    pct = clamp_protocol_drift(protocol_drift_pct)
    if pct >= 100:
        return 2
    if pct >= 80:
        return 1
    if pct >= 60:
        return 1
    if pct >= 40 and int(turn_number) <= 1:
        return 1
    return 0


def unstable_energy_adds_pressure(protocol_drift_pct: Any) -> bool:
    return clamp_protocol_drift(protocol_drift_pct) >= 80


def base_feedback_threshold(protocol_drift_pct: Any) -> int | None:
    return drift_tier(protocol_drift_pct)["feedback_threshold"]


def feedback_safe_threshold(protocol_drift_pct: Any, pressure: int = 0) -> int | None:
    base_threshold = base_feedback_threshold(protocol_drift_pct)
    if base_threshold is None:
        return None
    return max(1, base_threshold - max(0, int(pressure)))


def card_will_trigger_feedback(protocol_drift_pct: Any, cards_played_this_turn: int, pressure: int = 0) -> bool:
    threshold = feedback_safe_threshold(protocol_drift_pct, pressure=pressure)
    if threshold is None:
        return False
    return int(cards_played_this_turn) + 1 > threshold


def feedback_damage_value(trigger_count_this_turn: int, card_type: str | None) -> int:
    base_damage = min(4, max(1, int(trigger_count_this_turn)))
    if str(card_type or "").strip().lower() == "status":
        return max(0, base_damage - 1)
    return base_damage


def feedback_backlash_kind(
    protocol_drift_pct: Any,
    trigger_count_this_turn: int,
    *,
    card_type: str | None,
    actual_cost: int,
) -> str | None:
    if clamp_protocol_drift(protocol_drift_pct) < 60:
        return None
    if int(trigger_count_this_turn) % 2 != 0:
        return None

    normalized_type = str(card_type or "").strip().lower()
    if normalized_type == "status":
        return "status"
    if int(actual_cost) <= 0:
        return "zero_cost"
    if normalized_type == "power":
        return "power"
    if normalized_type == "skill":
        return "skill"
    if normalized_type == "attack":
        return "attack"
    return None


def feedback_preview_line(
    protocol_drift_pct: Any,
    cards_played_this_turn: int,
    pressure: int,
    *,
    card_type: str | None,
    actual_cost: int,
) -> str | None:
    if not card_will_trigger_feedback(protocol_drift_pct, cards_played_this_turn, pressure=pressure):
        return None
    next_trigger_count = max(1, int(cards_played_this_turn) + 1 - max(0, feedback_safe_threshold(protocol_drift_pct, pressure=pressure) or 0))
    damage = feedback_damage_value(next_trigger_count, card_type)
    backlash = feedback_backlash_kind(
        protocol_drift_pct,
        next_trigger_count,
        card_type=card_type,
        actual_cost=actual_cost,
    )
    message = f"Feedback: lose {damage} HP."
    if backlash == "attack":
        return f"{message} Backlash: gain 1 Vulnerable."
    if backlash == "skill":
        return f"{message} Backlash: gain 1 Suppressed."
    if backlash == "power":
        return f"{message} Backlash: add 1 Glitch to discard."
    if backlash == "zero_cost":
        return f"{message} Backlash: gain Nullified."
    if backlash == "status":
        return "Feedback: status dampens the spike by 1 HP."
    return message


def reward_hook_profile(protocol_drift_pct: Any) -> dict[str, Any]:
    pct = clamp_protocol_drift(protocol_drift_pct)
    if pct >= 100:
        return {
            "drift_card_append_chance": 0.0,
            "full_drift_signal": True,
            "eclipse_relic_append_chance": 0.35,
        }
    if pct >= 80:
        return {
            "drift_card_append_chance": 0.25,
            "full_drift_signal": False,
            "eclipse_relic_append_chance": 0.10,
        }
    if pct >= 60:
        return {
            "drift_card_append_chance": 0.15,
            "full_drift_signal": False,
            "eclipse_relic_append_chance": 0.0,
        }
    if pct >= 40:
        return {
            "drift_card_append_chance": 0.08,
            "full_drift_signal": False,
            "eclipse_relic_append_chance": 0.0,
        }
    return {
        "drift_card_append_chance": 0.0,
        "full_drift_signal": False,
        "eclipse_relic_append_chance": 0.0,
    }


def prefers_full_drift_pool(protocol_drift_pct: Any) -> bool:
    return clamp_protocol_drift(protocol_drift_pct) >= 100


def resolve_card_payload(
    card_data: dict[str, Any],
    *,
    protocol_drift_pct: Any,
    actual_cost: int,
    drift_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = copy.deepcopy(card_data)
    resolved["base_cost"] = int(card_data.get("cost", 0))
    resolved["cost"] = max(0, int(actual_cost))
    tier = drift_tier(protocol_drift_pct)
    override_bundle = _drift_override_bundle(drift_override, tier)
    attack_bonus = _override_int(override_bundle, "attack_bonus", tier["attack_bonus"])
    skill_bonus = _override_int(override_bundle, "skill_bonus", tier["skill_bonus"])
    status_bonus = _override_int(override_bundle, "status_bonus", tier["status_bonus"])
    draw_bonus = _clamp_draw_bonus(_override_int(override_bundle, "draw_bonus", 0))
    energy_bonus = _clamp_energy_bonus(_override_int(override_bundle, "energy_bonus", 0), tier["label"])
    cost_reduction_bonus = _clamp_cost_reduction_bonus(_override_int(override_bundle, "cost_reduction_bonus", 0))
    card_creation_bonus = _clamp_card_creation_bonus(_override_int(override_bundle, "card_creation_bonus", 0))

    adjusted_effects: list[dict[str, Any]] = []
    for effect in list(card_data.get("effects") or []):
        adjusted = copy.deepcopy(effect)
        effect_type = str(effect.get("type", ""))
        if effect_type in ATTACK_EFFECT_TYPES and int(effect.get("value", 0)) > 0:
            adjusted["value"] = int(effect["value"]) + attack_bonus
        elif effect_type in SKILL_EFFECT_TYPES and int(effect.get("value", 0)) > 0:
            adjusted["value"] = int(effect["value"]) + skill_bonus
        elif effect_type in STATUS_APPLY_EFFECT_TYPES and int(effect.get("value", 0)) > 0:
            adjusted["value"] = int(effect["value"]) + status_bonus
        elif effect_type == "draw" and draw_bonus:
            adjusted["value"] = int(effect["value"]) + draw_bonus
        elif effect_type == "energy" and energy_bonus:
            adjusted["value"] = int(effect["value"]) + energy_bonus
        elif effect_type == "modify_next_card_cost" and cost_reduction_bonus:
            delta = int(effect["value"])
            if delta < 0:
                adjusted["value"] = max(delta - cost_reduction_bonus, -resolved["cost"])
            elif delta > 0:
                adjusted["value"] = max(0, delta - cost_reduction_bonus)
        elif effect_type == "add_status_card" and card_creation_bonus:
            adjusted["count"] = max(1, int(effect.get("count", 1)) + card_creation_bonus)
        adjusted_effects.append(adjusted)

    resolved["effects"] = adjusted_effects
    resolved["drift_resolved"] = {
        "tier_index": tier["index"],
        "tier_label": tier["label"],
        "attack_bonus": attack_bonus,
        "skill_bonus": skill_bonus,
        "status_bonus": status_bonus,
        "draw_bonus": draw_bonus,
        "energy_bonus": energy_bonus,
        "cost_reduction_bonus": cost_reduction_bonus,
        "card_creation_bonus": card_creation_bonus,
    }
    return resolved


def _drift_override_bundle(drift_override: dict[str, Any] | None, tier: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(drift_override, dict):
        return {}
    tier_map = drift_override.get("tiers")
    if isinstance(tier_map, dict):
        candidates = [
            tier["label"],
            tier["label"].lower(),
            str(tier["index"]),
            str(tier["min"]),
            str(tier["max"]),
        ]
        for key in candidates:
            bundle = tier_map.get(key)
            if isinstance(bundle, dict):
                return bundle
    return drift_override


def _override_int(bundle: dict[str, Any], key: str, default: int) -> int:
    value = bundle.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _clamp_draw_bonus(value: int) -> int:
    return max(0, min(1, int(value)))


def _clamp_energy_bonus(value: int, tier_label: str) -> int:
    max_bonus = 2 if tier_label == "Full Drift" else 1
    return max(0, min(max_bonus, int(value)))


def _clamp_cost_reduction_bonus(value: int) -> int:
    return max(0, min(1, int(value)))


def _clamp_card_creation_bonus(value: int) -> int:
    return max(0, min(1, int(value)))
