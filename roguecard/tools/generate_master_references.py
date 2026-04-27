from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    CAMPAIGN_MAPS_DATA_PATH,
    CARDS_DATA_PATH,
    CHARACTERS_DATA_PATH,
    ENEMIES_DATA_PATH,
    EVENTS_DATA_PATH,
    FINAL_MAP_BOSSES_DATA_PATH,
    FINAL_MAP_ENCOUNTERS_DATA_PATH,
    OUTSKIRTS_ENCOUNTERS_DATA_PATH,
    RUN_MODIFIERS_DATA_PATH,
)

REFERENCE_ROOT = PROJECT_ROOT.parent / "reference"
VISUAL_BRIEFS_DATA_PATH = PROJECT_ROOT / "data" / "reference_visual_briefs.json"
EXPECTED_VISUAL_BRIEF_SECTIONS = (
    "cards",
    "enemies",
    "run_modifiers",
    "combat_statuses",
    "characters",
    "events",
)
RARITY_ORDER = {
    "common": 0,
    "uncommon": 1,
    "rare": 2,
    "boss": 3,
    "cursed": 4,
    "special": 5,
}
NODE_ORDER = {"combat": 0, "elite": 1, "boss": 2}
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2, "elite": 3, "boss": 4}

STATUS_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "strength",
        "label": "Strength",
        "category": "Core Combat Modifier",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py"],
        "effect": "Adds its value to outgoing attack damage.",
        "clears": "Persists until combat ends or another effect removes it.",
        "enemy_effect_types": ["enemy_gain_strength"],
        "card_effect_types": ["gain_strength"],
        "extra_sources": ["Enemy phase transitions such as Gland Brute and Graft Saint"],
    },
    {
        "id": "weak",
        "label": "Weak",
        "category": "Core Combat Modifier",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py"],
        "effect": "Outgoing attack damage is reduced to 75% while Weak is active.",
        "clears": "Ticks down by 1 at the start of that unit's turn.",
        "enemy_effect_types": ["enemy_apply_weak"],
        "card_effect_types": ["apply_weak"],
    },
    {
        "id": "vulnerable",
        "label": "Vulnerable",
        "category": "Core Combat Modifier",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py"],
        "effect": "Incoming attack damage is increased by 50% while Vulnerable is active.",
        "clears": "Ticks down by 1 at the start of that unit's turn.",
        "enemy_effect_types": ["enemy_apply_vulnerable"],
        "card_effect_types": ["apply_vulnerable"],
    },
    {
        "id": "infect",
        "label": "Infection",
        "category": "Combat Status",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "At end of the afflicted unit's turn, it loses HP equal to Infection. If Infection is 6 or more, it takes 4 extra damage and resets to 3.",
        "clears": "Persists until combat ends or an explicit effect changes it.",
        "card_effect_types": ["apply_infect"],
        "enemy_effect_types": ["enemy_apply_infect", "enemy_trigger_infection_burst"],
    },
    {
        "id": "burn",
        "label": "Burn",
        "category": "Combat Status",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "At end of the afflicted unit's turn, it loses HP equal to Burn.",
        "clears": "Burn decays by 1 at end of turn until it reaches 0.",
        "enemy_effect_types": ["enemy_apply_burn"],
    },
    {
        "id": "bleed",
        "label": "Bleed",
        "category": "Combat Status",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "When the afflicted target is hit, it takes bonus damage equal to Bleed.",
        "clears": "Bleed drops by 1 each time the bonus damage triggers.",
        "card_effect_types": ["apply_bleed"],
        "enemy_effect_types": ["enemy_apply_bleed"],
    },
    {
        "id": "marked",
        "label": "Marked",
        "category": "Combat Status",
        "lives_in": ["entities/player.py", "entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Blackwire attacks gain +2 damage per current Marked stack, then consume 1 stack on hit.",
        "clears": "Player Marked lasts up to 2 turns unless consumed sooner. Generic enemy-side counters persist until removed.",
        "enemy_effect_types": ["enemy_apply_marked"],
    },
    {
        "id": "suppressed",
        "label": "Suppressed",
        "category": "Combat Status",
        "lives_in": ["entities/player.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Attack cards deal 15% less damage per stack, with a minimum of 1 damage.",
        "clears": "Clears at the end of the player's turn. Player stacks are capped at 3.",
        "enemy_effect_types": ["enemy_apply_suppressed"],
    },
    {
        "id": "nullified",
        "label": "Nullified",
        "category": "Combat Status",
        "lives_in": ["entities/player.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Blocks the next positive player combat gain: Block, positive Strength, positive next-attack bonus, or a negative next-card-cost modifier.",
        "clears": "Removes itself after blocking one eligible positive effect or when combat ends.",
        "card_effect_types": ["apply_nullified"],
        "enemy_effect_types": ["enemy_apply_nullified"],
    },
    {
        "id": "fortified",
        "label": "Fortified",
        "category": "Combat Status",
        "lives_in": ["entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "At the start of turn, gain Block equal to Fortified, capped at 12.",
        "clears": "Persists until combat ends or another effect removes it.",
        "enemy_effect_types": ["enemy_apply_fortified"],
        "extra_sources": [
            "Spawn rules for Audit Hound, Sentry Node, Compliance Engine AX-9, and Junction-9 Sentinel",
            "Director Vale's first drone or machine summon gets Fortified 4",
        ],
    },
    {
        "id": "regenerate",
        "label": "Regenerate",
        "category": "Combat Status",
        "lives_in": ["entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "At the start of turn, heal HP equal to Regenerate.",
        "clears": "Consumes 1 stack after each start-of-turn heal.",
        "enemy_effect_types": ["enemy_apply_regenerate"],
        "extra_sources": ["Failed Saint phase transition grants Regenerate 3"],
    },
    {
        "id": "momentum",
        "label": "Momentum",
        "category": "Combat Status",
        "lives_in": ["entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Adds its value to the next outgoing enemy attack.",
        "clears": "Clears after that attack or at the end of the enemy's turn.",
        "enemy_effect_types": ["enemy_apply_momentum", "enemy_apply_momentum_allies"],
        "extra_sources": ["Cinder Jackals also gain Momentum from scripted ally-attack synergies such as Ashfang Rook's Blood Rally"],
    },
    {
        "id": "overheat",
        "label": "Overheat",
        "category": "Boss Resource",
        "lives_in": ["entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Stored heat resource used by Furnace Hound to scale Boiler Spit and Redline Charge.",
        "clears": "Boiler Spit consumes 1 Overheat. Redline Charge clears all Overheat. Furnace Hound gains 1 at end of each turn.",
        "enemy_effect_types": ["enemy_apply_overheat"],
        "extra_sources": ["Furnace Hound end-of-turn passive gain"],
    },
    {
        "id": "biomass",
        "label": "Biomass",
        "category": "Boss Resource",
        "lives_in": ["entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Stored Helix boss resource used by Miremother Vexa to empower Biomass Collapse.",
        "clears": "Miremother Vexa clears Biomass after a thresholded Biomass Collapse.",
        "enemy_effect_types": ["enemy_apply_biomass"],
        "extra_sources": ["Miremother Vexa gains Biomass when allied fodder dies"],
    },
    {
        "id": "mutated",
        "label": "Mutated",
        "category": "Enemy Phase State",
        "lives_in": ["entities/enemy.py", "combat/combat_manager.py", "ui/combat_ui.py"],
        "effect": "Marks an enemy as having crossed a phase threshold and switched to its phase-rule intent pattern.",
        "clears": "Persists for the rest of combat once applied.",
        "extra_sources": ["Applied automatically by enemy phase transitions from enemies.json phase_rules"],
    },
]


def _load_list_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected list payload in {path}.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _load_dict_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object payload in {path}.")
    return payload


def _bullet_list(items: Iterable[str]) -> str:
    cleaned = [str(item) for item in items if str(item)]
    if not cleaned:
        return "None"
    return ", ".join(f"`{item}`" for item in cleaned)


def _named_id_ref(entry: dict[str, Any]) -> str:
    return f"{entry.get('name', entry.get('id', 'unknown'))} (`{entry.get('id', 'unknown')}`)"


def _human_target(target: Any) -> str:
    if target is None:
        return "default"
    return str(target).replace("_", " ")


def _format_rgb(value: Any) -> str:
    if isinstance(value, list) and len(value) == 3:
        return f"RGB({value[0]}, {value[1]}, {value[2]})"
    return json.dumps(value, sort_keys=True)


def _format_theme(theme: Any) -> str:
    if not isinstance(theme, dict) or not theme:
        return "None"
    faction = theme.get("faction", "unknown")
    palette = theme.get("palette", "unknown")
    art_style = theme.get("art_style", "unknown")
    return f"faction `{faction}`, palette `{palette}`, art style `{art_style}`"


def _dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output


def _card_summary(card: dict[str, Any]) -> str:
    parts: list[str] = []
    for effect in card.get("effects", []):
        if isinstance(effect, dict):
            parts.append(_summarize_card_effect(effect))
    for trigger in card.get("triggers", []):
        if isinstance(trigger, dict):
            parts.append(_summarize_trigger(trigger))
    return " ".join(parts).strip() or "No direct gameplay text recorded."


def _summarize_card_effect(effect: dict[str, Any]) -> str:
    effect_type = str(effect.get("type", "unknown"))
    value = effect.get("value")
    if effect_type == "damage":
        return f"Deal {value} damage."
    if effect_type == "multi_damage":
        return f"Deal {value} damage {effect.get('count', 1)} times."
    if effect_type == "lifesteal_damage":
        return f"Deal {value} damage and heal for damage dealt."
    if effect_type == "block":
        return f"Gain {value} Block."
    if effect_type == "heal":
        return f"Heal {value} HP."
    if effect_type == "draw":
        return f"Draw {value} card{'s' if int(value) != 1 else ''}."
    if effect_type == "energy":
        return f"Gain {value} Energy."
    if effect_type == "self_damage":
        return f"Lose {value} HP."
    if effect_type == "gain_strength":
        return f"Gain {value} Strength."
    if effect_type == "apply_weak":
        return f"Apply {value} Weak."
    if effect_type == "apply_vulnerable":
        return f"Apply {value} Vulnerable."
    if effect_type == "apply_bleed":
        return f"Apply {value} Bleed."
    if effect_type == "apply_infect":
        return f"Apply {value} Infect."
    if effect_type == "apply_nullified":
        return "Apply Nullified."
    if effect_type == "cleanse_status":
        return f"Cleanse {value} `{effect.get('status_id')}`."
    if effect_type == "remove_nullified":
        return "Remove Nullified."
    if effect_type == "modify_next_card_cost":
        return f"Modify the next card cost by {value}."
    if effect_type == "modify_next_attack_damage":
        return f"Modify the next attack damage by {value}."
    if effect_type == "add_status_card":
        count = int(effect.get("count", 1))
        pile = effect.get("pile", "discard")
        return f"Add {count} `{effect.get('card_id')}` status card{'s' if count != 1 else ''} to {pile}."
    if effect_type == "random_one_of":
        options = []
        for option in effect.get("options", []):
            if not isinstance(option, dict):
                continue
            if isinstance(option.get("summary"), str):
                options.append(str(option["summary"]))
                continue
            nested = [
                _summarize_card_effect(nested_effect)
                for nested_effect in option.get("effects", [])
                if isinstance(nested_effect, dict)
            ]
            if nested:
                options.append(" ".join(nested))
        return "Random one of: " + " | ".join(options)
    if effect_type == "exhaust_drawn_card":
        return "Exhaust the drawn card."
    if effect_type == "noop":
        return "No direct effect."
    return f"{effect_type} {value!r}".strip()


def _summarize_trigger(trigger: dict[str, Any]) -> str:
    hook = str(trigger.get("hook", "unknown"))
    parts = [
        _summarize_card_effect(effect)
        for effect in trigger.get("effects", [])
        if isinstance(effect, dict)
    ]
    return f"`{hook}` -> " + " ".join(parts).strip()


def _summarize_enemy_effect(effect: dict[str, Any]) -> str:
    effect_type = str(effect.get("type", "unknown"))
    value = effect.get("value")
    count = int(effect.get("count", 1))
    target = _human_target(effect.get("target"))
    if effect_type == "enemy_damage":
        suffix = f" {count} times" if count > 1 else ""
        return f"Deal {value} damage to {target}{suffix}."
    if effect_type == "enemy_block":
        return f"Gain {value} Block."
    if effect_type == "enemy_heal_ally":
        return f"Heal {target} for {value} HP."
    if effect_type == "enemy_apply_infect":
        return f"Apply {value} Infection to {target}."
    if effect_type == "enemy_apply_weak":
        return f"Apply {value} Weak to {target}."
    if effect_type == "enemy_apply_vulnerable":
        return f"Apply {value} Vulnerable to {target}."
    if effect_type == "enemy_apply_marked":
        return f"Apply {value} Marked to {target}."
    if effect_type == "enemy_apply_suppressed":
        return f"Apply {value} Suppressed to {target}."
    if effect_type == "enemy_apply_burn":
        return f"Apply {value} Burn to {target}."
    if effect_type == "enemy_apply_bleed":
        return f"Apply {value} Bleed to {target}."
    if effect_type == "enemy_apply_nullified":
        return f"Apply Nullified to {target}."
    if effect_type == "enemy_add_status_card":
        pile = effect.get("pile", "discard")
        return f"Add {count} `{effect.get('card_id')}` status card{'s' if count != 1 else ''} to the player's {pile}."
    if effect_type == "enemy_strip_buff":
        return f"Strip a removable player buff from {target}."
    if effect_type == "enemy_cleanse_ally":
        return f"Cleanse up to {value} debuff stacks from {target}."
    if effect_type == "enemy_summon":
        return f"Summon {count} `{effect.get('enemy_id')}`."
    if effect_type == "enemy_gain_strength":
        return f"Gain {value} Strength."
    if effect_type == "enemy_apply_regenerate":
        return f"Gain Regenerate {value}."
    if effect_type == "enemy_apply_fortified":
        return f"Gain Fortified {value}."
    if effect_type == "enemy_apply_momentum":
        return f"Gain Momentum {value}."
    if effect_type == "enemy_apply_momentum_allies":
        return f"All living allies gain Momentum {value}."
    if effect_type == "enemy_block_allies":
        return f"All living allies gain {value} Block."
    if effect_type == "enemy_trigger_infection_burst":
        return "Trigger Infection Burst if the target's Infection is high enough."
    if effect_type == "enemy_steal_block":
        return f"Steal up to {value} Block from the player."
    if effect_type == "enemy_apply_overheat":
        return f"Gain Overheat {value}."
    if effect_type == "enemy_apply_biomass":
        return f"Gain Biomass {value}."
    if effect_type == "enemy_self_destruct":
        return "Self-destruct."
    return f"{effect_type} {value!r}".strip()


def _action_qualifiers(action: dict[str, Any]) -> list[str]:
    qualifiers: list[str] = []
    once_per = action.get("once_per")
    if isinstance(once_per, str):
        qualifiers.append(f"First each {once_per}")
    status_id = action.get("status_id")
    if isinstance(status_id, str):
        qualifiers.append(f"If status is `{status_id}`")
    status_ids = action.get("status_ids")
    if isinstance(status_ids, list) and status_ids:
        qualifiers.append(f"If status is {_bullet_list([str(item) for item in status_ids])}")
    card_type = action.get("card_type")
    if isinstance(card_type, str):
        qualifiers.append(f"If card type is `{card_type}`")
    card_id = action.get("card_id")
    if isinstance(card_id, str) and str(action.get("type")) not in {"add_card", "add_status_card"}:
        qualifiers.append(f"If card is `{card_id}`")
    played_cost_equals = action.get("played_cost_equals")
    if isinstance(played_cost_equals, int):
        qualifiers.append(f"If played cost is `{played_cost_equals}`")
    multiple_of = action.get("played_card_type_count_multiple_of")
    if isinstance(multiple_of, int):
        qualifiers.append(f"Every `{multiple_of}` matching cards this turn")
    played_type_set = action.get("require_played_type_set")
    if isinstance(played_type_set, list) and played_type_set:
        qualifiers.append(f"If played types include {_bullet_list([str(item) for item in played_type_set])}")
    required_statuses = action.get("require_target_has_statuses")
    if isinstance(required_statuses, list) and required_statuses:
        qualifiers.append(f"If target has {_bullet_list([str(item) for item in required_statuses])}")
    min_target_status_count = action.get("min_target_status_count")
    if isinstance(min_target_status_count, int):
        qualifiers.append(f"At least `{min_target_status_count}` matching statuses")
    turn_interval = action.get("turn_interval")
    if isinstance(turn_interval, int):
        turn_offset = int(action.get("turn_offset", 0))
        qualifiers.append(f"Every `{turn_interval}` turns starting after offset `{turn_offset}`")
    require_modifier_flag = action.get("require_modifier_flag")
    if isinstance(require_modifier_flag, str):
        qualifiers.append(f"If modifier flag `{require_modifier_flag}` is set")
    return qualifiers


def _summarize_modifier_action(action: dict[str, Any]) -> str:
    action_type = str(action.get("type", "unknown"))
    value = action.get("value")
    qualifiers = _action_qualifiers(action)
    if action_type == "gain_block":
        summary = f"Gain {value} Block."
    elif action_type == "draw_cards":
        summary = f"Draw {value} card{'s' if int(value) != 1 else ''}."
    elif action_type == "gain_energy":
        summary = f"Gain {value} Energy."
    elif action_type == "gain_next_turn_energy":
        summary = f"Gain {value} Energy next turn."
    elif action_type == "gain_credits":
        encounter_types = action.get("encounter_types")
        if isinstance(encounter_types, list) and encounter_types:
            summary = f"Gain {value} credits after {_bullet_list([str(item) for item in encounter_types])}."
        else:
            summary = f"Gain {value} credits."
    elif action_type == "heal":
        summary = f"Heal {value} HP."
    elif action_type == "heal_after_event":
        summary = f"Heal {value} HP after each event."
    elif action_type == "heal_if_any_enemy_has_status":
        summary = f"Heal {value} HP if any enemy has a matching status."
    elif action_type == "gain_strength":
        summary = f"Gain {value} Strength."
    elif action_type == "percent_discount":
        summary = f"Reduce `{action.get('target')}` prices by {value}%."
    elif action_type == "percent_surcharge":
        summary = f"Increase `{action.get('target')}` prices by {value}%."
    elif action_type == "flat_discount":
        summary = f"Reduce `{action.get('target')}` price by {value}."
    elif action_type == "flat_surcharge_first_card_shop":
        summary = f"The first card purchase in each shop costs {value} more."
    elif action_type == "free_first_purge_run":
        summary = "The first purge each run is free."
    elif action_type == "free_first_reroll_shop":
        summary = "The first reroll in each shop is free."
    elif action_type == "extra_card_choice":
        summary = f"Show {value} extra card reward choice."
    elif action_type == "add_card":
        summary = f"Add `{action.get('card_id')}`."
    elif action_type == "add_random_temporary_card_to_hand":
        summary = "Add a random temporary card to your hand."
    elif action_type == "add_status_card":
        count = int(action.get("count", 1))
        summary = f"Add {count} `{action.get('card_id')}` status card{'s' if count != 1 else ''}."
    elif action_type == "modify_max_hp":
        summary = f"Adjust max HP by {value}."
    elif action_type == "modify_healing_multiplier_percent":
        summary = f"Adjust healing multiplier by {value}%."
    elif action_type == "damage_event_target":
        summary = f"Deal {value} damage to the triggering enemy."
    elif action_type == "damage_highest_status_enemy":
        summary = f"Deal {value} damage to the enemy with the highest matching status."
    elif action_type == "damage_random_enemy":
        summary = f"Deal {value} damage to a random enemy."
    elif action_type == "damage":
        summary = f"Take {value} damage."
    elif action_type == "apply_status_all_enemies":
        summary = f"Apply {value} `{action.get('status_id')}` to all enemies."
    elif action_type == "apply_status_other_enemies":
        summary = f"Apply {value} `{action.get('status_id')}` to all other enemies."
    elif action_type == "apply_status_event_target":
        summary = f"Apply {value} `{action.get('status_id')}` to the event target."
    elif action_type == "bonus_attack_damage_if_attacked_last_turn":
        summary = f"If you attacked last turn, Attack cards deal {value} extra damage."
    elif action_type == "first_card_free":
        summary = "The first card each combat costs 0."
    elif action_type == "cost_surcharge_after_first_card":
        summary = f"Cards cost {value} more after the first one each combat."
    elif action_type == "reduce_first_block_each_combat":
        summary = f"The first Block gain each combat is reduced by {value}."
    elif action_type == "repeat_first_card":
        summary = "The first card you play each combat repeats."
    elif action_type == "set_modifier_flag":
        summary = f"Set modifier flag `{action.get('flag_id')}`."
    elif action_type == "clear_modifier_flag":
        summary = f"Clear modifier flag `{action.get('flag_id')}`."
    elif action_type == "set_random_hand_card_cost_until_played":
        summary = f"Set a random card in hand to cost {value} until played."
    elif action_type == "lose_credits_each_floor":
        summary = f"Lose {value} credits at each new floor."
    elif action_type == "modify_next_attack_damage":
        summary = f"Your next attack deals {value} more damage."
    elif action_type == "modify_next_card_cost":
        summary = f"Your next card cost changes by {value}."
    elif action_type == "increase_highest_enemy_status":
        summary = f"Increase the highest enemy `{action.get('status_id')}` by {value}."
    elif action_type == "reduce_player_status":
        summary = f"Reduce player `{action.get('status_id')}` by {value}."
    elif action_type == "random_one_of":
        options = []
        for option in action.get("options", []):
            if not isinstance(option, dict):
                continue
            if isinstance(option.get("summary"), str):
                options.append(str(option["summary"]))
                continue
            nested = [
                _summarize_modifier_action(nested_action)
                for nested_action in option.get("effects", [])
                if isinstance(nested_action, dict)
            ]
            if nested:
                options.append(" ".join(nested))
        summary = "Random one of: " + " | ".join(options)
    elif action_type == "exhaust_drawn_card":
        summary = "Exhaust the drawn status card."
    else:
        summary = f"{action_type} {value!r}".strip()
    return " ".join([*qualifiers, summary]).strip()


def _summarize_event_effect(effect: dict[str, Any]) -> str:
    effect_type = str(effect.get("type", "unknown"))
    value = effect.get("value")
    if effect_type == "gain_credits":
        return f"Gain {value} credits."
    if effect_type == "lose_credits":
        return f"Lose {value} credits."
    if effect_type == "heal":
        return f"Heal {value} HP."
    if effect_type == "damage":
        return f"Take {value} damage."
    if effect_type == "gain_card":
        return f"Gain `{effect.get('card_id')}`."
    if effect_type == "purge_card":
        return "Purge one deck card."
    if effect_type == "gain_modifier":
        return f"Gain `{effect.get('modifier_id')}`."
    if effect_type == "gain_random_modifier":
        parts = ["Roll a random modifier"]
        allow_types = [str(item) for item in effect.get("allow_types", [])]
        if allow_types:
            parts.append(f"from {_bullet_list(allow_types)}")
        allow_rarities = [str(item) for item in effect.get("allow_rarities", [])]
        if allow_rarities:
            parts.append(f"with rarities {_bullet_list(allow_rarities)}")
        include_tags = [str(item) for item in effect.get("include_tags", [])]
        if include_tags:
            parts.append(f"including {_bullet_list(include_tags)}")
        exclude_tags = [str(item) for item in effect.get("exclude_tags", [])]
        if exclude_tags:
            parts.append(f"excluding {_bullet_list(exclude_tags)}")
        duration = effect.get("duration")
        if isinstance(duration, dict) and duration.get("value") is not None:
            parts.append(f"for {duration.get('value')} {duration.get('type', 'steps')}")
        summary = " ".join(parts).strip() + "."
        fallback_effects = [
            fallback_effect
            for fallback_effect in effect.get("fallback_effects", [])
            if isinstance(fallback_effect, dict)
        ]
        if fallback_effects:
            fallback_summary = " ".join(_summarize_event_effect(fallback_effect) for fallback_effect in fallback_effects)
            summary += f" Fallback: {fallback_summary}"
        return summary
    if effect_type == "remove_modifier":
        return f"Remove `{effect.get('modifier_id')}`."
    return f"{effect_type} {value!r}".strip()


def _summarize_event_outcome(outcome: dict[str, Any]) -> str:
    summary_text = " ".join(
        _summarize_event_effect(effect)
        for effect in outcome.get("effects", [])
        if isinstance(effect, dict)
    ).strip()
    if summary_text:
        return summary_text
    return "No explicit mechanical effect text in current data."


def _effect_types_from_enemy(enemy: dict[str, Any]) -> set[str]:
    effect_types: set[str] = set()
    for collection_key in ("moves", "death_effects", "ally_death_effects"):
        for entry in enemy.get(collection_key, []):
            if not isinstance(entry, dict):
                continue
            effects = entry.get("effects", []) if collection_key == "moves" else [entry]
            for effect in effects:
                if isinstance(effect, dict) and effect.get("type"):
                    effect_types.add(str(effect["type"]))
    return effect_types


def _enemy_special_mechanics(enemy: dict[str, Any]) -> list[str]:
    labels = {
        "enemy_apply_weak": "Weak",
        "enemy_apply_vulnerable": "Vulnerable",
        "enemy_apply_infect": "Infection",
        "enemy_apply_marked": "Marked",
        "enemy_apply_suppressed": "Suppressed",
        "enemy_apply_burn": "Burn",
        "enemy_apply_bleed": "Bleed",
        "enemy_apply_nullified": "Nullified",
        "enemy_add_status_card": "Status-card injection",
        "enemy_strip_buff": "Strip Buff",
        "enemy_cleanse_ally": "Cleanse",
        "enemy_summon": "Summoning",
        "enemy_gain_strength": "Strength gain",
        "enemy_apply_regenerate": "Regenerate",
        "enemy_apply_fortified": "Fortified",
        "enemy_apply_momentum": "Momentum",
        "enemy_apply_momentum_allies": "Momentum support",
        "enemy_block_allies": "Team block",
        "enemy_trigger_infection_burst": "Infection Burst",
        "enemy_steal_block": "Block steal",
        "enemy_apply_overheat": "Overheat",
        "enemy_apply_biomass": "Biomass",
        "enemy_self_destruct": "Self-destruct",
    }
    mechanics = [labels[effect_type] for effect_type in sorted(_effect_types_from_enemy(enemy)) if effect_type in labels]
    if enemy.get("phase_rules"):
        mechanics.append("Phase change")
    if enemy.get("death_effects"):
        mechanics.append("Death effect")
    if enemy.get("ally_death_effects"):
        mechanics.append("Ally-death passive")
    return _dedupe_preserve(mechanics)


def _load_visual_briefs(
    cards: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    run_modifiers: list[dict[str, Any]],
    characters: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    payload = _load_dict_json(VISUAL_BRIEFS_DATA_PATH)
    errors: list[str] = []
    payload_sections = set(payload)
    expected_sections = set(EXPECTED_VISUAL_BRIEF_SECTIONS)
    missing_sections = sorted(expected_sections - payload_sections)
    extra_sections = sorted(payload_sections - expected_sections)
    if missing_sections:
        errors.append(f"Missing top-level visual brief sections: {', '.join(missing_sections)}")
    if extra_sections:
        errors.append(f"Unknown top-level visual brief sections: {', '.join(extra_sections)}")

    expected_ids = {
        "cards": {str(entry["id"]) for entry in cards},
        "enemies": {str(entry["id"]) for entry in enemies},
        "run_modifiers": {str(entry["id"]) for entry in run_modifiers},
        "combat_statuses": {str(entry["id"]) for entry in STATUS_DEFINITIONS},
        "characters": {str(entry["id"]) for entry in characters},
        "events": {str(entry["id"]) for entry in events},
    }

    resolved: dict[str, dict[str, str]] = {}
    for section in EXPECTED_VISUAL_BRIEF_SECTIONS:
        section_payload = payload.get(section, {})
        if not isinstance(section_payload, dict):
            errors.append(f"Section `{section}` must be an object keyed by id.")
            resolved[section] = {}
            continue
        actual_ids = set(section_payload)
        missing_ids = sorted(expected_ids[section] - actual_ids)
        extra_ids = sorted(actual_ids - expected_ids[section])
        if missing_ids:
            errors.append(f"Section `{section}` is missing ids: {', '.join(missing_ids)}")
        if extra_ids:
            errors.append(f"Section `{section}` has unknown ids: {', '.join(extra_ids)}")
        resolved[section] = {}
        for entity_id, entry in section_payload.items():
            if not isinstance(entry, dict):
                errors.append(f"Entry `{section}.{entity_id}` must be an object.")
                continue
            visual_flavor = entry.get("visual_flavor")
            if not isinstance(visual_flavor, str) or not visual_flavor.strip():
                errors.append(f"Entry `{section}.{entity_id}` needs a non-empty `visual_flavor` string.")
                continue
            resolved[section][entity_id] = visual_flavor.strip()
    if errors:
        raise ValueError("Visual brief validation failed:\n- " + "\n- ".join(errors))
    return resolved


def _collect_enemy_sources(enemies: list[dict[str, Any]], effect_types: list[str]) -> list[str]:
    wanted = set(effect_types)
    matches: set[str] = set()
    for enemy in enemies:
        enemy_name = _named_id_ref(enemy)
        for move in enemy.get("moves", []):
            if not isinstance(move, dict):
                continue
            for effect in move.get("effects", []):
                if isinstance(effect, dict) and str(effect.get("type")) in wanted:
                    matches.add(enemy_name)
        for collection_key in ("death_effects", "ally_death_effects"):
            for effect in enemy.get(collection_key, []):
                if isinstance(effect, dict) and str(effect.get("type")) in wanted:
                    matches.add(enemy_name)
    return sorted(matches)


def _collect_card_sources(cards: list[dict[str, Any]], effect_types: list[str]) -> list[str]:
    wanted = set(effect_types)
    matches: set[str] = set()
    for card in cards:
        card_name = _named_id_ref(card)
        for effect in card.get("effects", []):
            if isinstance(effect, dict) and str(effect.get("type")) in wanted:
                matches.add(card_name)
        for trigger in card.get("triggers", []):
            if not isinstance(trigger, dict):
                continue
            for effect in trigger.get("effects", []):
                if isinstance(effect, dict) and str(effect.get("type")) in wanted:
                    matches.add(card_name)
    return sorted(matches)


def _collect_modifier_sources(run_modifiers: list[dict[str, Any]], status_id: str) -> list[str]:
    wanted = str(status_id)
    matches: set[str] = set()
    for modifier in run_modifiers:
        hooks = modifier.get("hooks", {})
        if not isinstance(hooks, dict):
            continue
        for actions in hooks.values():
            if not isinstance(actions, list):
                continue
            for action in actions:
                if not isinstance(action, dict):
                    continue
                referenced_statuses: set[str] = set()
                if isinstance(action.get("status_id"), str):
                    referenced_statuses.add(str(action["status_id"]))
                if isinstance(action.get("status_ids"), list):
                    referenced_statuses.update(str(item) for item in action["status_ids"] if isinstance(item, str))
                if isinstance(action.get("require_target_has_statuses"), list):
                    referenced_statuses.update(
                        str(item) for item in action["require_target_has_statuses"] if isinstance(item, str)
                    )
                if wanted in referenced_statuses:
                    matches.add(f"{modifier['name']} (`{modifier['id']}`) [{modifier.get('type', 'unknown')}]")
                    break
    return sorted(matches)


def _collect_status_card_sources(
    cards: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    status_card_id: str,
) -> list[str]:
    wanted = str(status_card_id)
    matches: set[str] = set()
    for card in cards:
        card_name = _named_id_ref(card)
        for effect in card.get("effects", []):
            if isinstance(effect, dict) and effect.get("type") == "add_status_card" and effect.get("card_id") == wanted:
                matches.add(card_name)
        for trigger in card.get("triggers", []):
            if not isinstance(trigger, dict):
                continue
            for effect in trigger.get("effects", []):
                if isinstance(effect, dict) and effect.get("type") == "add_status_card" and effect.get("card_id") == wanted:
                    matches.add(card_name)
    for enemy in enemies:
        enemy_name = _named_id_ref(enemy)
        for move in enemy.get("moves", []):
            if not isinstance(move, dict):
                continue
            for effect in move.get("effects", []):
                if isinstance(effect, dict) and effect.get("type") == "enemy_add_status_card" and effect.get("card_id") == wanted:
                    matches.add(enemy_name)
    return sorted(matches)


def _format_card_refs(
    card_ids: Iterable[str],
    card_lookup: dict[str, dict[str, Any]],
    *,
    compress_duplicates: bool,
) -> str:
    card_id_list = [str(card_id) for card_id in card_ids]
    if not card_id_list:
        return "None"
    if compress_duplicates:
        counts = Counter(card_id_list)
        ordered_ids = _dedupe_preserve(card_id_list)
        items = []
        for card_id in ordered_ids:
            card = card_lookup.get(card_id, {"id": card_id, "name": card_id})
            label = _named_id_ref(card)
            count = counts[card_id]
            items.append(f"{label} x{count}" if count > 1 else label)
        return ", ".join(items)
    items = []
    for card_id in card_id_list:
        card = card_lookup.get(card_id, {"id": card_id, "name": card_id})
        items.append(_named_id_ref(card))
    return ", ".join(items)


def _floor_bands_for_difficulty(bands: list[dict[str, Any]], difficulty: str) -> list[str]:
    labels: list[str] = []
    start_floor = 1
    for band in bands:
        end_floor = int(band.get("max_floor", start_floor))
        weight = band.get("difficulty_weights", {}).get(difficulty)
        if isinstance(weight, (int, float)) and weight > 0:
            floor_label = f"floor {start_floor}" if start_floor == end_floor else f"floors {start_floor}-{end_floor}"
            labels.append(f"{floor_label} (weight {weight:g})")
        start_floor = end_floor + 1
    return labels


def _collect_direct_enemy_placements(
    outskirts_encounters: dict[str, Any],
    final_map_encounters: dict[str, Any],
    map_lookup: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    placements: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def add_encounter_placements(
        *,
        map_id: str,
        encounter: dict[str, Any],
        generation: dict[str, Any],
    ) -> None:
        map_name = str(map_lookup.get(map_id, {}).get("name", map_id))
        difficulty = str(encounter.get("difficulty", "unknown"))
        for node_type in encounter.get("node_types", []):
            if node_type == "combat":
                bands = generation.get("combat_bands", [])
            elif node_type == "elite":
                bands = generation.get("elite_bands", [])
            else:
                continue
            floor_bands = _floor_bands_for_difficulty([band for band in bands if isinstance(band, dict)], difficulty)
            for enemy_id in encounter.get("enemy_ids", []):
                placements[str(enemy_id)].append(
                    {
                        "map_id": map_id,
                        "map_name": map_name,
                        "node_type": str(node_type),
                        "difficulty": difficulty,
                        "encounter_id": str(encounter.get("id", "unknown")),
                        "floor_bands": floor_bands,
                    }
                )

    outskirts_generation = outskirts_encounters.get("generation", {})
    for region in outskirts_encounters.get("regions", []):
        if not isinstance(region, dict):
            continue
        map_id = str(region.get("id", "outskirts"))
        for encounter in region.get("encounters", []):
            if isinstance(encounter, dict):
                add_encounter_placements(map_id=map_id, encounter=encounter, generation=outskirts_generation)

    final_generation = final_map_encounters.get("generation", {})
    for faction in final_map_encounters.get("factions", []):
        if not isinstance(faction, dict):
            continue
        map_id = str(faction.get("route_map_id", "unknown"))
        for encounter in faction.get("encounters", []):
            if isinstance(encounter, dict):
                add_encounter_placements(map_id=map_id, encounter=encounter, generation=final_generation)

    return placements


def _collect_boss_pool_placements(campaign_maps: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    placements: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for map_definition in campaign_maps:
        map_id = str(map_definition.get("id", "unknown"))
        map_name = str(map_definition.get("name", map_id))
        map_branch_faction = map_definition.get("branch_faction")
        for boss_entry in map_definition.get("boss_pool", []):
            if not isinstance(boss_entry, dict):
                continue
            raw_enemy_ids = boss_entry.get("enemy_ids")
            if isinstance(raw_enemy_ids, list) and raw_enemy_ids:
                boss_ids = [str(enemy_id) for enemy_id in raw_enemy_ids]
            elif boss_entry.get("id"):
                boss_ids = [str(boss_entry["id"])]
            else:
                continue
            for boss_id in boss_ids:
                placements[boss_id].append(
                    {
                        "map_id": map_id,
                        "map_name": map_name,
                        "branch_faction": str(boss_entry.get("branch_faction") or map_branch_faction or ""),
                    }
                )
    return placements


def _collect_placeholder_placements(campaign_maps: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    placements: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for map_definition in campaign_maps:
        map_id = str(map_definition.get("id", "unknown"))
        map_name = str(map_definition.get("name", map_id))
        placeholder_enemy_ids = map_definition.get("placeholder_enemy_ids", {})
        if not isinstance(placeholder_enemy_ids, dict):
            continue
        for node_type, enemy_ids in placeholder_enemy_ids.items():
            if not isinstance(enemy_ids, list):
                continue
            for enemy_id in enemy_ids:
                placements[str(enemy_id)].append(
                    {
                        "map_id": map_id,
                        "map_name": map_name,
                        "node_type": str(node_type),
                    }
                )
    return placements


def _collect_summon_sources(enemies: list[dict[str, Any]]) -> dict[str, list[str]]:
    summon_sources: dict[str, set[str]] = defaultdict(set)
    for enemy in enemies:
        summoner_id = str(enemy.get("id"))
        for summon_id in enemy.get("summon_ids", []):
            summon_sources[str(summon_id)].add(summoner_id)
        for move in enemy.get("moves", []):
            if not isinstance(move, dict):
                continue
            for effect in move.get("effects", []):
                if not isinstance(effect, dict) or effect.get("type") != "enemy_summon":
                    continue
                summon_id = effect.get("enemy_id")
                if summon_id:
                    summon_sources[str(summon_id)].add(summoner_id)
    return {enemy_id: sorted(source_ids) for enemy_id, source_ids in summon_sources.items()}


def _format_enemy_placement_lines(
    enemy_id: str,
    *,
    direct_placements: dict[str, list[dict[str, Any]]],
    boss_placements: dict[str, list[dict[str, Any]]],
    placeholder_placements: dict[str, list[dict[str, Any]]],
    summon_sources: dict[str, list[str]],
    enemy_lookup: dict[str, dict[str, Any]],
    map_order: dict[str, int],
) -> list[str]:
    lines: list[str] = []

    direct_records = direct_placements.get(enemy_id, [])
    grouped_direct: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in direct_records:
        key = (record["map_id"], record["node_type"], record["difficulty"])
        grouped = grouped_direct.setdefault(
            key,
            {
                "map_name": record["map_name"],
                "encounter_ids": set(),
                "floor_bands": [],
            },
        )
        grouped["encounter_ids"].add(record["encounter_id"])
        grouped["floor_bands"].extend(record["floor_bands"])
    for (map_id, node_type, difficulty), data in sorted(
        grouped_direct.items(),
        key=lambda item: (
            map_order.get(item[0][0], 999),
            NODE_ORDER.get(item[0][1], 999),
            DIFFICULTY_ORDER.get(item[0][2], 999),
            item[0][0],
        ),
    ):
        floor_bands = ", ".join(_dedupe_preserve(data["floor_bands"])) or "authored encounter placement"
        encounter_ids = ", ".join(f"`{encounter_id}`" for encounter_id in sorted(data["encounter_ids"]))
        lines.append(
            f"{data['map_name']} `{node_type}` `{difficulty}`: {floor_bands} via {encounter_ids}."
        )

    for record in sorted(
        boss_placements.get(enemy_id, []),
        key=lambda item: (map_order.get(item["map_id"], 999), item["map_id"]),
    ):
        branch_faction = record.get("branch_faction", "")
        if record["map_id"] == "city_streets" and branch_faction:
            lines.append(f"{record['map_name']} boss pool: city-streets boss route for `{branch_faction}`.")
        elif branch_faction:
            lines.append(f"{record['map_name']} boss pool: final-route boss pool for `{branch_faction}`.")
        else:
            lines.append(f"{record['map_name']} boss pool.")

    source_ids = summon_sources.get(enemy_id, [])
    if source_ids:
        if not direct_records and not boss_placements.get(enemy_id):
            lines.append("Summon-only in current authored data; not placed directly in encounter pools.")
        source_refs = [_named_id_ref(enemy_lookup[source_id]) for source_id in source_ids if source_id in enemy_lookup]
        if source_refs:
            lines.append(f"Live summoners: {', '.join(source_refs)}.")

    placeholder_records = placeholder_placements.get(enemy_id, [])
    if placeholder_records:
        placeholder_lines = []
        for record in sorted(
            placeholder_records,
            key=lambda item: (map_order.get(item["map_id"], 999), NODE_ORDER.get(item["node_type"], 999), item["map_id"]),
        ):
            placeholder_lines.append(f"{record['map_name']} `{record['node_type']}` placeholder slot")
        lines.append(
            "Placeholder / unplaced current-state use: "
            + ", ".join(_dedupe_preserve(placeholder_lines))
            + "; not part of authored live encounter pools."
        )

    if not lines:
        lines.append("No live authored placement found in current data.")
    return lines


def _format_boss_route_lines(
    boss_id: str,
    boss_placements: dict[str, list[dict[str, Any]]],
    map_order: dict[str, int],
) -> list[str]:
    records = boss_placements.get(boss_id, [])
    if not records:
        return ["No live boss-pool placement found in current campaign data."]
    lines: list[str] = []
    for record in sorted(records, key=lambda item: (map_order.get(item["map_id"], 999), item["map_id"])):
        branch_faction = record.get("branch_faction", "")
        if record["map_id"] == "city_streets" and branch_faction:
            lines.append(f"{record['map_name']}: city-streets boss route for `{branch_faction}`.")
        elif branch_faction:
            lines.append(f"{record['map_name']}: final-route boss pool for `{branch_faction}`.")
        else:
            lines.append(f"{record['map_name']}: boss pool.")
    return _dedupe_preserve(lines)


def _append_phase_rules(lines: list[str], enemy: dict[str, Any]) -> None:
    phase_rules = [rule for rule in enemy.get("phase_rules", []) if isinstance(rule, dict)]
    if not phase_rules:
        lines.append("- Phase Rules: None")
        return
    lines.append("- Phase Rules:")
    for phase_rule in phase_rules:
        lines.append(
            f"  - `{phase_rule.get('name', 'phase')}` at <= {phase_rule.get('threshold_ratio', 'n/a')} HP ratio -> pattern {phase_rule.get('intent_pattern', [])}"
        )


def _append_effect_block(lines: list[str], *, label: str, effects: list[dict[str, Any]]) -> None:
    if not effects:
        lines.append(f"- {label}: None")
        return
    lines.append(f"- {label}:")
    for effect in effects:
        lines.append(f"  - {_summarize_enemy_effect(effect)}")


def _append_moves_block(lines: list[str], enemy: dict[str, Any]) -> None:
    lines.append("- Moves:")
    for move in enemy.get("moves", []):
        if not isinstance(move, dict):
            continue
        lines.append(f"  - `{move.get('id')}`: {move.get('intent_text', 'No intent text')}")
        lines.append(f"    - Target: `{move.get('target', 'default')}`")
        lines.append(f"    - Cooldown: `{move.get('cooldown', 0)}`")
        if move.get("bark_trigger"):
            lines.append(f"    - Bark Trigger: `{move.get('bark_trigger')}`")
        if move.get("conditions"):
            lines.append(f"    - Conditions: `{json.dumps(move['conditions'], sort_keys=True)}`")
        effects = [effect for effect in move.get("effects", []) if isinstance(effect, dict)]
        if effects:
            lines.append("    - Effects:")
            for effect in effects:
                lines.append(f"      - {_summarize_enemy_effect(effect)}")
        else:
            lines.append("    - Effects: None")


def _append_modifier_entry(
    lines: list[str],
    entry: dict[str, Any],
    visual_flavor: str,
    *,
    include_track: bool,
) -> None:
    lines.extend(
        [
            f"### {entry['name']} (`{entry['id']}`)",
            "",
            f"- Description: {entry.get('description', 'No description.')}",
            f"- Visual Flavor: {visual_flavor}",
            f"- Rarity: `{entry.get('rarity', 'unknown')}`",
            f"- Base Weight: `{entry.get('base_weight', 'unknown')}`",
            f"- Draft Eligible: `{bool(entry.get('draft_eligible', False))}`",
            f"- Source Types: {_bullet_list([str(item) for item in entry.get('source_types', [])])}",
            f"- Tags: {_bullet_list([str(item) for item in entry.get('tags', [])])}",
        ]
    )
    downside = entry.get("downside")
    if isinstance(downside, str) and downside.strip():
        lines.append(f"- Downside: {downside}")
    if include_track:
        lines.append(f"- Track: `{entry.get('track') or 'legacy/untracked'}`")
    duration = entry.get("duration")
    if duration:
        lines.append(f"- Duration: `{json.dumps(duration, sort_keys=True)}`")
    stack_behavior = entry.get("stack_behavior")
    if isinstance(stack_behavior, str) and stack_behavior.strip():
        lines.append(f"- Stack Behavior: `{stack_behavior}`")
    synergies = entry.get("synergies", [])
    if isinstance(synergies, list) and synergies:
        lines.append(f"- Synergies: {_bullet_list([str(item) for item in synergies])}")
    notes = entry.get("notes")
    if isinstance(notes, str) and notes.strip():
        lines.append(f"- Notes: {notes}")
    hooks = entry.get("hooks", {})
    if isinstance(hooks, dict) and hooks:
        lines.append("- Hooks:")
        for hook_name, actions in hooks.items():
            if not isinstance(actions, list):
                continue
            lines.append(f"  - `{hook_name}`")
            for action in actions:
                if isinstance(action, dict):
                    lines.append(f"    - {_summarize_modifier_action(action)}")
    else:
        lines.append("- Hooks: None")
    lines.append("")


def _write_cards_reference(cards: list[dict[str, Any]], visual_briefs: dict[str, dict[str, str]]) -> Path:
    lines: list[str] = [
        "# Cards Master Reference",
        "",
        "Generated from `data/cards.json`.",
        "",
        f"- Total cards: **{len(cards)}**",
        f"- Status cards included in this catalog: **{sum(1 for card in cards if str(card.get('type', '')).lower() == 'status')}**",
        "",
    ]
    owner_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in sorted(cards, key=lambda entry: (",".join(entry.get("owners", ["unknown"])), str(entry.get("name", "")))):
        owner_key = ",".join(str(owner) for owner in card.get("owners", ["unknown"]))
        owner_groups[owner_key].append(card)
    for owner_key, owner_cards in owner_groups.items():
        lines.extend([f"## Owners: {owner_key}", ""])
        for card in owner_cards:
            lines.extend(
                [
                    f"### {card['name']} (`{card['id']}`)",
                    "",
                    f"- Owners: {_bullet_list([str(owner) for owner in card.get('owners', [])])}",
                    f"- Type / Cost: `{card.get('type', 'unknown')}` / `{card.get('cost', 'unknown')}`",
                    f"- Shop Price: `{card.get('shop_price', 'unknown')}`",
                    f"- Keywords: {_bullet_list([str(keyword) for keyword in card.get('keywords', [])])}",
                    f"- Summary: {_card_summary(card)}",
                    f"- Visual Flavor: {visual_briefs['cards'][card['id']]}",
                    f"- Theme Lens: {_format_theme(card.get('theme'))}",
                ]
            )
            triggers = [trigger for trigger in card.get("triggers", []) if isinstance(trigger, dict)]
            if triggers:
                lines.append("- Triggers:")
                for trigger in triggers:
                    lines.append(f"  - {_summarize_trigger(trigger)}")
            else:
                lines.append("- Triggers: None")
            lines.append("")
    output_path = REFERENCE_ROOT / "cards_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_enemies_reference(
    enemies: list[dict[str, Any]],
    campaign_maps: list[dict[str, Any]],
    outskirts_encounters: dict[str, Any],
    final_map_encounters: dict[str, Any],
    visual_briefs: dict[str, dict[str, str]],
) -> Path:
    map_lookup = {str(entry["id"]): entry for entry in campaign_maps}
    map_order = {str(entry["id"]): index for index, entry in enumerate(campaign_maps)}
    direct_placements = _collect_direct_enemy_placements(outskirts_encounters, final_map_encounters, map_lookup)
    boss_placements = _collect_boss_pool_placements(campaign_maps)
    placeholder_placements = _collect_placeholder_placements(campaign_maps)
    summon_sources = _collect_summon_sources(enemies)
    enemy_lookup = {str(enemy["id"]): enemy for enemy in enemies}

    lines: list[str] = [
        "# Enemies Master Reference",
        "",
        "Generated from `data/enemies.json`, `data/outskirts_encounters.json`, `data/final_map_encounters.json`, and `data/campaign_maps.json`.",
        "",
        f"- Total enemies: **{len(enemies)}**",
        "- `city_streets` currently has authored boss routes only in live data; regular combat and elite routing still point at placeholder ids from `campaign_maps.json`.",
        "",
    ]
    faction_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for enemy in sorted(enemies, key=lambda entry: (str(entry.get("faction_id", "")), str(entry.get("name", "")))):
        faction_groups[str(enemy.get("faction_id", "unknown"))].append(enemy)
    for faction_id, faction_enemies in faction_groups.items():
        lines.extend([f"## {faction_id}", ""])
        for enemy in faction_enemies:
            lines.extend(
                [
                    f"### {enemy['name']} (`{enemy['id']}`)",
                    "",
                    f"- Faction: `{enemy.get('faction_id', 'unknown')}`",
                    f"- Role / Tier: `{enemy.get('role', 'unknown')}` / `{enemy.get('tier', 'unknown')}`",
                    f"- Max HP: `{enemy.get('max_hp', 'unknown')}`",
                    f"- Tags: {_bullet_list([str(tag) for tag in enemy.get('tags', [])])}",
                    f"- Bark Profile: `{enemy.get('bark_profile_id')}`" if enemy.get("bark_profile_id") else "- Bark Profile: None",
                    f"- Intent Pattern: {_bullet_list([str(item) for item in enemy.get('intent_pattern', [])])}",
                    f"- Summon IDs: {_bullet_list([str(item) for item in enemy.get('summon_ids', [])])}",
                    f"- Special Mechanics: {', '.join(_enemy_special_mechanics(enemy)) if _enemy_special_mechanics(enemy) else 'None'}",
                    f"- Visual Flavor: {visual_briefs['enemies'][enemy['id']]}",
                ]
            )
            placement_lines = _format_enemy_placement_lines(
                enemy["id"],
                direct_placements=direct_placements,
                boss_placements=boss_placements,
                placeholder_placements=placeholder_placements,
                summon_sources=summon_sources,
                enemy_lookup=enemy_lookup,
                map_order=map_order,
            )
            lines.append("- Placement:")
            for placement_line in placement_lines:
                lines.append(f"  - {placement_line}")
            _append_phase_rules(lines, enemy)
            death_effects = [effect for effect in enemy.get("death_effects", []) if isinstance(effect, dict)]
            ally_death_effects = [effect for effect in enemy.get("ally_death_effects", []) if isinstance(effect, dict)]
            _append_effect_block(lines, label="Death Effects", effects=death_effects)
            _append_effect_block(lines, label="Ally-Death Effects", effects=ally_death_effects)
            _append_moves_block(lines, enemy)
            lines.append("")
    output_path = REFERENCE_ROOT / "enemies_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_modifier_reference(
    *,
    title: str,
    filename: str,
    entries: list[dict[str, Any]],
    visual_briefs: dict[str, dict[str, str]],
    include_track: bool,
    summary_lines: list[str] | None = None,
) -> Path:
    lines: list[str] = [
        f"# {title}",
        "",
        "Generated from `data/run_modifiers.json`.",
        "",
        f"- Total entries: **{len(entries)}**",
    ]
    if summary_lines:
        lines.extend(summary_lines)
    lines.append("")
    rarity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in sorted(entries, key=lambda item: (RARITY_ORDER.get(str(item.get("rarity", "")), 999), str(item.get("name", "")))):
        rarity_groups[str(entry.get("rarity", "unknown"))].append(entry)
    ordered_rarities = sorted(rarity_groups, key=lambda item: (RARITY_ORDER.get(item, 999), item))
    for rarity in ordered_rarities:
        lines.extend([f"## {rarity}", ""])
        for entry in rarity_groups[rarity]:
            _append_modifier_entry(
                lines,
                entry,
                visual_briefs["run_modifiers"][entry["id"]],
                include_track=include_track,
            )
    output_path = REFERENCE_ROOT / filename
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_relics_reference(run_modifiers: list[dict[str, Any]], visual_briefs: dict[str, dict[str, str]]) -> Path:
    relics = [entry for entry in run_modifiers if str(entry.get("type", "")).lower() == "relic"]
    skipped_types = Counter(
        str(entry.get("type", "unknown"))
        for entry in run_modifiers
        if str(entry.get("type", "")).lower() != "relic"
    )
    track_counts = Counter(str(entry.get("track") or "legacy/untracked") for entry in relics)
    summary_lines = [
        f"- Track breakdown: {', '.join(f'`{track}` x{track_counts.get(track, 0)}' for track in ('legacy/untracked', 'drop_in', 'advanced') if track in track_counts)}",
        f"- Related files: see `blessings_master_reference.md` for **{skipped_types.get('blessing', 0)}** blessings and `curses_master_reference.md` for **{skipped_types.get('curse', 0)}** curses.",
        f"- Non-relic modifier types excluded from this list: {', '.join(f'`{modifier_type}` x{count}' for modifier_type, count in sorted(skipped_types.items())) or 'None'}",
    ]
    return _write_modifier_reference(
        title="Relics Master Reference",
        filename="relics_master_reference.md",
        entries=relics,
        visual_briefs=visual_briefs,
        include_track=True,
        summary_lines=summary_lines,
    )


def _write_blessings_reference(run_modifiers: list[dict[str, Any]], visual_briefs: dict[str, dict[str, str]]) -> Path:
    blessings = [entry for entry in run_modifiers if str(entry.get("type", "")).lower() == "blessing"]
    return _write_modifier_reference(
        title="Blessings Master Reference",
        filename="blessings_master_reference.md",
        entries=blessings,
        visual_briefs=visual_briefs,
        include_track=False,
    )


def _write_curses_reference(run_modifiers: list[dict[str, Any]], visual_briefs: dict[str, dict[str, str]]) -> Path:
    curses = [entry for entry in run_modifiers if str(entry.get("type", "")).lower() == "curse"]
    return _write_modifier_reference(
        title="Curses Master Reference",
        filename="curses_master_reference.md",
        entries=curses,
        visual_briefs=visual_briefs,
        include_track=False,
    )


def _write_statuses_reference(
    cards: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    run_modifiers: list[dict[str, Any]],
    visual_briefs: dict[str, dict[str, str]],
) -> Path:
    status_cards = [card for card in cards if str(card.get("type", "")).lower() == "status"]
    modifier_statuses = [entry for entry in run_modifiers if str(entry.get("type", "")).lower() == "status"]
    lines: list[str] = [
        "# Statuses Master Reference",
        "",
        "Generated from combat/status code plus `data/cards.json`, `data/enemies.json`, and `data/run_modifiers.json`.",
        "",
        f"- Combat statuses: **{len(STATUS_DEFINITIONS)}**",
        f"- Status cards: **{len(status_cards)}**",
        f"- Run-modifier statuses: **{len(modifier_statuses)}**",
        "",
        "## Combat Statuses",
        "",
    ]
    for definition in STATUS_DEFINITIONS:
        enemy_sources = _collect_enemy_sources(enemies, definition.get("enemy_effect_types", []))
        card_sources = _collect_card_sources(cards, definition.get("card_effect_types", []))
        modifier_sources = _collect_modifier_sources(run_modifiers, definition["id"])
        extra_sources = [str(source) for source in definition.get("extra_sources", [])]
        sources = enemy_sources + card_sources + modifier_sources + extra_sources
        lines.extend(
            [
                f"### {definition['label']} (`{definition['id']}`)",
                "",
                f"- Category: {definition['category']}",
                f"- Lives In: {_bullet_list([str(path) for path in definition.get('lives_in', [])])}",
                f"- Effect: {definition['effect']}",
                f"- Clears / Decay: {definition['clears']}",
                f"- Visual Flavor: {visual_briefs['combat_statuses'][definition['id']]}",
                f"- Who Can Apply It: {', '.join(sources) if sources else 'No direct live appliers found in current data.'}",
                "",
            ]
        )

    lines.extend(["## Status Cards", ""])
    for card in sorted(status_cards, key=lambda entry: str(entry.get("name", ""))):
        generators = _collect_status_card_sources(cards, enemies, card["id"])
        lines.extend(
            [
                f"### {card['name']} (`{card['id']}`)",
                "",
                f"- Owners: {_bullet_list([str(owner) for owner in card.get('owners', [])])}",
                f"- Cost: `{card.get('cost', 'unknown')}`",
                f"- Keywords: {_bullet_list([str(keyword) for keyword in card.get('keywords', [])])}",
                f"- Behavior: {_card_summary(card)}",
                f"- Visual Flavor: {visual_briefs['cards'][card['id']]}",
                f"- Theme Lens: {_format_theme(card.get('theme'))}",
                f"- Live Generators: {', '.join(generators) if generators else 'None found in current data.'}",
                "",
            ]
        )

    lines.extend(["## Run Modifier Statuses", ""])
    for entry in sorted(modifier_statuses, key=lambda item: (RARITY_ORDER.get(str(item.get("rarity", "")), 999), str(item.get("name", "")))):
        _append_modifier_entry(
            lines,
            entry,
            visual_briefs["run_modifiers"][entry["id"]],
            include_track=False,
        )

    output_path = REFERENCE_ROOT / "statuses_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_characters_reference(
    characters: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    visual_briefs: dict[str, dict[str, str]],
) -> Path:
    card_lookup = {str(card["id"]): card for card in cards}
    lines: list[str] = [
        "# Characters Master Reference",
        "",
        "Generated from `data/characters.json`.",
        "",
        f"- Total characters: **{len(characters)}**",
        "",
    ]
    for character in sorted(characters, key=lambda entry: str(entry.get("name", ""))):
        lines.extend(
            [
                f"### {character['name']} (`{character['id']}`)",
                "",
                f"- Subtitle: {character.get('subtitle', 'None')}",
                f"- Description: {character.get('description', 'No description.')}",
                f"- Accent Color: `{_format_rgb(character.get('accent_color'))}`",
                f"- Palette Key: `{character.get('palette_key', 'unknown')}`",
                f"- Visual Flavor: {visual_briefs['characters'][character['id']]}",
                f"- Starting Deck: {_format_card_refs(character.get('starting_deck_ids', []), card_lookup, compress_duplicates=True)}",
                f"- Preview Cards: {_format_card_refs(character.get('preview_card_ids', []), card_lookup, compress_duplicates=False)}",
                "",
            ]
        )
    output_path = REFERENCE_ROOT / "characters_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_bosses_reference(
    bosses_payload: dict[str, Any],
    enemies: list[dict[str, Any]],
    campaign_maps: list[dict[str, Any]],
    visual_briefs: dict[str, dict[str, str]],
) -> Path:
    bosses = [entry for entry in bosses_payload.get("bosses", []) if isinstance(entry, dict)]
    enemy_lookup = {str(enemy["id"]): enemy for enemy in enemies}
    boss_placements = _collect_boss_pool_placements(campaign_maps)
    map_order = {str(entry["id"]): index for index, entry in enumerate(campaign_maps)}
    lines: list[str] = [
        "# Bosses Master Reference",
        "",
        "Generated from `data/final_map_bosses.json`, `data/enemies.json`, and `data/campaign_maps.json`.",
        "",
        f"- Total bosses: **{len(bosses)}**",
        "",
    ]
    category_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for boss in sorted(bosses, key=lambda entry: (str(entry.get("category", "")), str(entry.get("name", "")))):
        category_groups[str(boss.get("category", "unknown"))].append(boss)
    for category, group in category_groups.items():
        lines.extend([f"## {category}", ""])
        for boss in group:
            enemy = enemy_lookup.get(str(boss["id"]))
            if enemy is None:
                raise ValueError(f"Boss `{boss['id']}` is missing from enemies.json.")
            lines.extend(
                [
                    f"### {boss['name']} (`{boss['id']}`)",
                    "",
                    f"- Category: `{boss.get('category', 'unknown')}`",
                    f"- Faction: `{boss.get('faction') or 'general'}`",
                    f"- Combat Role: {boss.get('combat_role', 'Unknown')}",
                    f"- Catalog Summary: {boss.get('summary', 'No summary.')}",
                    f"- Intro Text: {boss.get('intro_text', 'None')}",
                    f"- Role / Tier: `{enemy.get('role', 'unknown')}` / `{enemy.get('tier', 'unknown')}`",
                    f"- Max HP: `{enemy.get('max_hp', 'unknown')}`",
                    f"- Tags: {_bullet_list([str(tag) for tag in enemy.get('tags', [])])}",
                    f"- Special Mechanics: {', '.join(_enemy_special_mechanics(enemy)) if _enemy_special_mechanics(enemy) else 'None'}",
                    f"- Visual Flavor: {visual_briefs['enemies'][boss['id']]}",
                ]
            )
            lines.append("- Route Availability:")
            for route_line in _format_boss_route_lines(boss["id"], boss_placements, map_order):
                lines.append(f"  - {route_line}")
            _append_phase_rules(lines, enemy)
            death_effects = [effect for effect in enemy.get("death_effects", []) if isinstance(effect, dict)]
            ally_death_effects = [effect for effect in enemy.get("ally_death_effects", []) if isinstance(effect, dict)]
            _append_effect_block(lines, label="Death Effects", effects=death_effects)
            _append_effect_block(lines, label="Ally-Death Effects", effects=ally_death_effects)
            _append_moves_block(lines, enemy)
            lines.append("")
    output_path = REFERENCE_ROOT / "bosses_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _append_event_choices(lines: list[str], event: dict[str, Any]) -> None:
    choices = [choice for choice in event.get("choices", []) if isinstance(choice, dict)]
    if not choices:
        lines.append("- Choices: None")
        return
    lines.append("- Choices:")
    for choice in choices:
        choice_type = str(choice.get("choice_type", "effect"))
        description = str(choice.get("description", "No description."))
        lines.append(f"  - `{choice.get('label', 'Choice')}` (`{choice_type}`): {description}")
        requirements = choice.get("requirements")
        if requirements:
            lines.append(f"    - Requirements: `{json.dumps(requirements, sort_keys=True)}`")
        outcomes = [outcome for outcome in choice.get("outcomes", []) if isinstance(outcome, dict)]
        if outcomes:
            lines.append("    - Outcomes:")
            for outcome in outcomes:
                lines.append(
                    f"      - `{outcome.get('id', 'outcome')}` (weight {outcome.get('weight', 'n/a')}): {_summarize_event_outcome(outcome)}"
                )


def _write_events_reference(events: list[dict[str, Any]], visual_briefs: dict[str, dict[str, str]]) -> Path:
    lines: list[str] = [
        "# Events Master Reference",
        "",
        "Generated from `data/events.json`.",
        "",
        f"- Total events: **{len(events)}**",
        "",
    ]
    rarity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in sorted(events, key=lambda entry: (RARITY_ORDER.get(str(entry.get("rarity", "")), 999), str(entry.get("title", "")))):
        rarity_groups[str(event.get("rarity", "unknown"))].append(event)
    for rarity in sorted(rarity_groups, key=lambda item: (RARITY_ORDER.get(item, 999), item)):
        lines.extend([f"## {rarity}", ""])
        for event in rarity_groups[rarity]:
            lines.extend(
                [
                    f"### {event['title']} (`{event['id']}`)",
                    "",
                    f"- Body: {event.get('body', 'No body text.')}",
                    f"- Visual Flavor: {visual_briefs['events'][event['id']]}",
                    f"- Base Weight: `{event.get('base_weight', 'unknown')}`",
                    f"- Tags: {_bullet_list([str(tag) for tag in event.get('tags', [])])}",
                ]
            )
            min_floor = event.get("min_floor")
            if isinstance(min_floor, int):
                lines.append(f"- Min Floor: `{min_floor}`")
            requirements = event.get("requirements")
            if isinstance(requirements, dict) and requirements:
                lines.append(f"- Requirements: `{json.dumps(requirements, sort_keys=True)}`")
            character_ids = event.get("character_ids")
            if isinstance(character_ids, list) and character_ids:
                lines.append(f"- Character IDs: {_bullet_list([str(character_id) for character_id in character_ids])}")
            exclusion_tags = event.get("exclusion_tags")
            if isinstance(exclusion_tags, list) and exclusion_tags:
                lines.append(f"- Exclusion Tags: {_bullet_list([str(tag) for tag in exclusion_tags])}")
            _append_event_choices(lines, event)
            lines.append("")
    output_path = REFERENCE_ROOT / "events_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def generate_master_references() -> list[Path]:
    cards = _load_list_json(CARDS_DATA_PATH)
    enemies = _load_list_json(ENEMIES_DATA_PATH)
    run_modifiers = _load_list_json(RUN_MODIFIERS_DATA_PATH)
    characters = _load_list_json(CHARACTERS_DATA_PATH)
    events = _load_list_json(EVENTS_DATA_PATH)
    campaign_maps = _load_list_json(CAMPAIGN_MAPS_DATA_PATH)
    outskirts_encounters = _load_dict_json(OUTSKIRTS_ENCOUNTERS_DATA_PATH)
    final_map_encounters = _load_dict_json(FINAL_MAP_ENCOUNTERS_DATA_PATH)
    bosses_payload = _load_dict_json(FINAL_MAP_BOSSES_DATA_PATH)
    visual_briefs = _load_visual_briefs(cards, enemies, run_modifiers, characters, events)
    REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)

    return [
        _write_cards_reference(cards, visual_briefs),
        _write_enemies_reference(
            enemies,
            campaign_maps,
            outskirts_encounters,
            final_map_encounters,
            visual_briefs,
        ),
        _write_relics_reference(run_modifiers, visual_briefs),
        _write_blessings_reference(run_modifiers, visual_briefs),
        _write_curses_reference(run_modifiers, visual_briefs),
        _write_statuses_reference(cards, enemies, run_modifiers, visual_briefs),
        _write_characters_reference(characters, cards, visual_briefs),
        _write_bosses_reference(bosses_payload, enemies, campaign_maps, visual_briefs),
        _write_events_reference(events, visual_briefs),
    ]


if __name__ == "__main__":
    print(f"Generated at {datetime.now().isoformat(timespec='seconds')}")
    for path in generate_master_references():
        print(path)
