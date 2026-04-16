from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import CARDS_DATA_PATH, ENEMIES_DATA_PATH, RUN_MODIFIERS_DATA_PATH

REFERENCE_ROOT = PROJECT_ROOT.parent / "reference"

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


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list payload in {path}.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "None"
    return ", ".join(f"`{item}`" for item in items)


def _human_target(target: Any) -> str:
    if target is None:
        return "default"
    return str(target).replace("_", " ")


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
        pile = effect.get("pile", "discard")
        count = int(effect.get("count", 1))
        return f"Add {count} `{effect.get('card_id')}` status card{'s' if count != 1 else ''} to {pile}."
    if effect_type == "random_one_of":
        options = effect.get("options", [])
        option_summaries = []
        for option in options:
            if not isinstance(option, dict):
                continue
            if option.get("summary"):
                option_summaries.append(str(option["summary"]))
            else:
                nested = [_summarize_card_effect(nested_effect) for nested_effect in option.get("effects", []) if isinstance(nested_effect, dict)]
                option_summaries.append(" ".join(nested).strip())
        return "Random one of: " + " | ".join(filter(None, option_summaries))
    if effect_type == "exhaust_drawn_card":
        return "Exhaust the drawn card."
    if effect_type == "noop":
        return "No direct effect."
    return f"{effect_type} {value!r}".strip()


def _summarize_trigger(trigger: dict[str, Any]) -> str:
    hook = str(trigger.get("hook", "unknown"))
    effect_summaries = [_summarize_card_effect(effect) for effect in trigger.get("effects", []) if isinstance(effect, dict)]
    return f"`{hook}` -> " + " ".join(effect_summaries).strip()


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
        count = int(effect.get("count", 1))
        pile = effect.get("pile", "discard")
        return f"Add {count} `{effect.get('card_id')}` status card{'s' if count != 1 else ''} to the player's {pile}."
    if effect_type == "enemy_strip_buff":
        return f"Strip a removable player buff from {target}."
    if effect_type == "enemy_cleanse_ally":
        return f"Cleanse up to {value} debuff stacks from {target}."
    if effect_type == "enemy_summon":
        return f"Summon {effect.get('count', 1)} `{effect.get('enemy_id')}`."
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


def _summarize_modifier_hook(action: dict[str, Any]) -> str:
    action_type = str(action.get("type", "unknown"))
    value = action.get("value")
    qualifiers: list[str] = []
    once_per = action.get("once_per")
    if isinstance(once_per, str):
        qualifiers.append(f"First each {once_per}")
    status_ids = action.get("status_ids")
    if isinstance(status_ids, list) and status_ids:
        qualifiers.append(f"If status is {_bullet_list([str(status_id) for status_id in status_ids])}")
    card_type = action.get("card_type")
    if isinstance(card_type, str):
        qualifiers.append(f"If card type is `{card_type}`")
    required_statuses = action.get("require_target_has_statuses")
    if isinstance(required_statuses, list) and required_statuses:
        qualifiers.append(
            f"If target has {_bullet_list([str(status_id) for status_id in required_statuses])}"
        )
    if action_type == "gain_block":
        summary = f"Gain {value} Block."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "draw_cards":
        summary = f"Draw {value} card{'s' if int(value) != 1 else ''}."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "gain_energy":
        summary = f"Gain {value} Energy."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "gain_credits":
        encounter_types = action.get("encounter_types")
        if isinstance(encounter_types, list) and encounter_types:
            summary = f"Gain {value} credits after {_bullet_list([str(entry) for entry in encounter_types])}."
        else:
            summary = f"Gain {value} credits."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "heal":
        summary = f"Heal {value} HP."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "percent_discount":
        summary = f"Reduce `{action.get('target')}` prices by {value}%."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "flat_discount":
        summary = f"Reduce `{action.get('target')}` price by {value}."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "free_first_purge_run":
        return " ".join([*qualifiers, "The first purge each run is free."]).strip()
    if action_type == "extra_card_choice":
        summary = f"Show {value} extra card reward choice."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "add_card":
        summary = f"Add `{action.get('card_id')}`."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "adjust_max_hp":
        summary = f"Adjust max HP by {value}."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "adjust_healing_multiplier":
        summary = f"Adjust healing multiplier by {value}%."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "damage_event_target":
        summary = f"Deal {value} damage to the triggering enemy."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "damage_random_enemy":
        summary = f"Deal {value} damage to a random enemy."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "apply_status_all_enemies":
        summary = f"Apply {value} `{action.get('status_id')}` to all enemies."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "increase_highest_enemy_status":
        summary = f"The enemy with the highest `{action.get('status_id')}` gains {value} more `{action.get('status_id')}`."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "gain_next_turn_energy":
        summary = f"Gain {value} Energy next turn."
        return " ".join([*qualifiers, summary]).strip()
    if action_type == "reduce_player_status":
        status_id = action.get("status_id")
        if status_id is not None:
            summary = f"Reduce player `{status_id}` by {value}."
        else:
            summary = f"Reduce the triggering player status by {value}."
        return " ".join([*qualifiers, summary]).strip()
    return " ".join([*qualifiers, f"{action_type} {value!r}".strip()]).strip()


def _card_summary(card: dict[str, Any]) -> str:
    parts: list[str] = []
    for effect in card.get("effects", []):
        if isinstance(effect, dict):
            parts.append(_summarize_card_effect(effect))
    for trigger in card.get("triggers", []):
        if isinstance(trigger, dict):
            parts.append(_summarize_trigger(trigger))
    return " ".join(parts).strip() or "No direct gameplay text recorded."


def _effect_types_from_enemy(enemy: dict[str, Any]) -> set[str]:
    effect_types: set[str] = set()
    for collection_key in ("moves", "death_effects", "ally_death_effects"):
        for entry in enemy.get(collection_key, []):
            if not isinstance(entry, dict):
                continue
            effects = entry.get("effects", []) if collection_key == "moves" else [entry]
            for effect in effects:
                if isinstance(effect, dict):
                    effect_types.add(str(effect.get("type", "")))
    return {effect_type for effect_type in effect_types if effect_type}


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
    seen: set[str] = set()
    deduped: list[str] = []
    for mechanic in mechanics:
        if mechanic not in seen:
            deduped.append(mechanic)
            seen.add(mechanic)
    return deduped


def _collect_enemy_sources(enemies: list[dict[str, Any]], effect_types: list[str]) -> list[str]:
    matches: set[str] = set()
    wanted = set(effect_types)
    for enemy in enemies:
        enemy_name = f"{enemy['name']} (`{enemy['id']}`)"
        for move in enemy.get("moves", []):
            if not isinstance(move, dict):
                continue
            for effect in move.get("effects", []):
                if isinstance(effect, dict) and str(effect.get("type", "")) in wanted:
                    matches.add(enemy_name)
        for collection_key in ("death_effects", "ally_death_effects"):
            for effect in enemy.get(collection_key, []):
                if isinstance(effect, dict) and str(effect.get("type", "")) in wanted:
                    matches.add(enemy_name)
    return sorted(matches)


def _collect_card_sources(cards: list[dict[str, Any]], effect_types: list[str]) -> list[str]:
    matches: set[str] = set()
    wanted = set(effect_types)
    for card in cards:
        card_name = f"{card['name']} (`{card['id']}`)"
        for effect in card.get("effects", []):
            if isinstance(effect, dict) and str(effect.get("type", "")) in wanted:
                matches.add(card_name)
        for trigger in card.get("triggers", []):
            if not isinstance(trigger, dict):
                continue
            for effect in trigger.get("effects", []):
                if isinstance(effect, dict) and str(effect.get("type", "")) in wanted:
                    matches.add(card_name)
    return sorted(matches)


def _collect_modifier_sources(run_modifiers: list[dict[str, Any]], status_id: str) -> list[str]:
    matches: set[str] = set()
    wanted = str(status_id)
    for modifier in run_modifiers:
        if str(modifier.get("type", "")).lower() != "relic":
            continue
        hooks = modifier.get("hooks", {})
        if not isinstance(hooks, dict):
            continue
        for actions in hooks.values():
            if not isinstance(actions, list):
                continue
            for action in actions:
                if not isinstance(action, dict):
                    continue
                action_statuses = set()
                if isinstance(action.get("status_id"), str):
                    action_statuses.add(str(action["status_id"]))
                if isinstance(action.get("status_ids"), list):
                    action_statuses.update(str(entry) for entry in action["status_ids"] if isinstance(entry, str))
                if isinstance(action.get("require_target_has_statuses"), list):
                    action_statuses.update(
                        str(entry) for entry in action["require_target_has_statuses"] if isinstance(entry, str)
                    )
                if wanted in action_statuses:
                    matches.add(f"{modifier['name']} (`{modifier['id']}`)")
                    break
    return sorted(matches)


def _collect_status_card_sources(
    cards: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    status_card_id: str,
) -> list[str]:
    matches: set[str] = set()
    wanted = str(status_card_id)
    for card in cards:
        card_name = f"{card['name']} (`{card['id']}`)"
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
        enemy_name = f"{enemy['name']} (`{enemy['id']}`)"
        for move in enemy.get("moves", []):
            if not isinstance(move, dict):
                continue
            for effect in move.get("effects", []):
                if isinstance(effect, dict) and effect.get("type") == "enemy_add_status_card" and effect.get("card_id") == wanted:
                    matches.add(enemy_name)
    return sorted(matches)


def _write_enemies_reference(enemies: list[dict[str, Any]]) -> Path:
    lines: list[str] = [
        "# Enemies Master Reference",
        "",
        "Generated from `data/enemies.json`.",
        "",
        f"- Total enemies: **{len(enemies)}**",
        "",
    ]

    faction_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for enemy in sorted(enemies, key=lambda entry: (str(entry.get("faction_id", "")), str(entry.get("name", "")))):
        faction_groups[str(enemy.get("faction_id", "unknown"))].append(enemy)

    for faction_id, faction_enemies in faction_groups.items():
        lines.extend([f"## {faction_id}", ""])
        for enemy in faction_enemies:
            special_mechanics = _enemy_special_mechanics(enemy)
            lines.extend(
                [
                    f"### {enemy['name']} (`{enemy['id']}`)",
                    "",
                    f"- Faction: `{enemy.get('faction_id', 'unknown')}`",
                    f"- Role / Tier: `{enemy.get('role', 'unknown')}` / `{enemy.get('tier', 'unknown')}`",
                    f"- Max HP: `{enemy.get('max_hp', 'unknown')}`",
                    f"- Tags: {_bullet_list([str(tag) for tag in enemy.get('tags', [])])}",
                    f"- Bark Profile: `{enemy.get('bark_profile_id')}`" if enemy.get("bark_profile_id") else "- Bark Profile: None",
                    f"- Summon IDs: {_bullet_list([str(enemy_id) for enemy_id in enemy.get('summon_ids', [])])}",
                    f"- Special Mechanics: {', '.join(special_mechanics) if special_mechanics else 'None'}",
                ]
            )
            phase_rules = enemy.get("phase_rules", [])
            if phase_rules:
                lines.append("- Phase Rules:")
                for phase_rule in phase_rules:
                    if not isinstance(phase_rule, dict):
                        continue
                    lines.append(
                        f"  - `{phase_rule.get('name', 'phase')}` at <= {phase_rule.get('threshold_ratio', 'n/a')} HP ratio -> pattern {phase_rule.get('intent_pattern', [])}"
                    )
            else:
                lines.append("- Phase Rules: None")

            for label, key in (("Death Effects", "death_effects"), ("Ally-Death Effects", "ally_death_effects")):
                effects = [effect for effect in enemy.get(key, []) if isinstance(effect, dict)]
                if effects:
                    lines.append(f"- {label}:")
                    for effect in effects:
                        lines.append(f"  - {_summarize_enemy_effect(effect)}")
                else:
                    lines.append(f"- {label}: None")

            lines.append("- Moves:")
            for move in enemy.get("moves", []):
                if not isinstance(move, dict):
                    continue
                lines.append(f"  - `{move.get('id')}`: {move.get('intent_text', 'No intent text')}")
                lines.append(f"    - Target: `{move.get('target', 'default')}`")
                lines.append(f"    - Cooldown: `{move.get('cooldown', 0)}`")
                if move.get("conditions"):
                    lines.append(f"    - Conditions: `{json.dumps(move['conditions'], sort_keys=True)}`")
                effects = [effect for effect in move.get("effects", []) if isinstance(effect, dict)]
                if effects:
                    lines.append("    - Effects:")
                    for effect in effects:
                        lines.append(f"      - {_summarize_enemy_effect(effect)}")
                else:
                    lines.append("    - Effects: None")
            lines.append("")

    output_path = REFERENCE_ROOT / "enemies_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_cards_reference(cards: list[dict[str, Any]]) -> Path:
    lines: list[str] = [
        "# Cards Master Reference",
        "",
        "Generated from `data/cards.json`.",
        "",
        f"- Total cards: **{len(cards)}**",
        "",
    ]

    owner_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in sorted(cards, key=lambda entry: (",".join(entry.get("owners", ["unknown"])), str(entry.get("name", "")))):
        owners = card.get("owners", ["unknown"])
        owner_key = ",".join(str(owner) for owner in owners) if isinstance(owners, list) else str(owners)
        owner_groups[owner_key].append(card)

    for owner_key, owner_cards in owner_groups.items():
        lines.extend([f"## Owners: {owner_key}", ""])
        for card in owner_cards:
            keywords = [str(keyword) for keyword in card.get("keywords", [])]
            lines.extend(
                [
                    f"### {card['name']} (`{card['id']}`)",
                    "",
                    f"- Owners: {_bullet_list([str(owner) for owner in card.get('owners', [])])}",
                    f"- Type / Cost: `{card.get('type', 'unknown')}` / `{card.get('cost', 'unknown')}`",
                    f"- Shop Price: `{card.get('shop_price', 'unknown')}`",
                    f"- Keywords: {_bullet_list(keywords)}",
                    f"- Summary: {_card_summary(card)}",
                ]
            )
            theme = card.get("theme")
            if isinstance(theme, dict) and theme:
                lines.append(f"- Theme: `{json.dumps(theme, sort_keys=True)}`")
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


def _write_relics_reference(run_modifiers: list[dict[str, Any]]) -> Path:
    relics = [entry for entry in run_modifiers if str(entry.get("type", "")).lower() == "relic"]
    skipped_types = Counter(str(entry.get("type", "unknown")) for entry in run_modifiers if str(entry.get("type", "")).lower() != "relic")
    lines: list[str] = [
        "# Relics Master Reference",
        "",
        "Generated from `data/run_modifiers.json`.",
        "",
        f"- Total relics: **{len(relics)}**",
        f"- Non-relic modifier types excluded from the main list: {', '.join(f'`{key}` x{value}' for key, value in sorted(skipped_types.items())) or 'None'}",
        "",
    ]

    rarity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relic in sorted(relics, key=lambda entry: (str(entry.get("rarity", "")), str(entry.get("name", "")))):
        rarity_groups[str(relic.get("rarity", "unknown"))].append(relic)

    for rarity, rarity_relics in rarity_groups.items():
        lines.extend([f"## {rarity}", ""])
        for relic in rarity_relics:
            lines.extend(
                [
                    f"### {relic['name']} (`{relic['id']}`)",
                    "",
                    f"- Description: {relic.get('description', 'No description.')}",
                    f"- Base Weight: `{relic.get('base_weight', 'unknown')}`",
                    f"- Draft Eligible: `{bool(relic.get('draft_eligible', False))}`",
                    f"- Source Types: {_bullet_list([str(entry) for entry in relic.get('source_types', [])])}",
                    f"- Tags: {_bullet_list([str(entry) for entry in relic.get('tags', [])])}",
                ]
            )
            hooks = relic.get("hooks", {})
            if isinstance(hooks, dict) and hooks:
                lines.append("- Hooks:")
                for hook_name, actions in hooks.items():
                    if not isinstance(actions, list):
                        continue
                    lines.append(f"  - `{hook_name}`")
                    for action in actions:
                        if isinstance(action, dict):
                            lines.append(f"    - {_summarize_modifier_hook(action)}")
            else:
                lines.append("- Hooks: None")
            lines.append("")

    output_path = REFERENCE_ROOT / "relics_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _write_statuses_reference(
    cards: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    run_modifiers: list[dict[str, Any]],
) -> Path:
    lines: list[str] = [
        "# Statuses Master Reference",
        "",
        "Generated from combat/status code plus `data/cards.json` and `data/enemies.json`.",
        "",
        "## Combat Statuses",
        "",
    ]

    for definition in STATUS_DEFINITIONS:
        enemy_sources = _collect_enemy_sources(enemies, definition.get("enemy_effect_types", []))
        card_sources = _collect_card_sources(cards, definition.get("card_effect_types", []))
        modifier_sources = _collect_modifier_sources(run_modifiers, definition["id"])
        extra_sources = [str(entry) for entry in definition.get("extra_sources", [])]
        sources = enemy_sources + card_sources + modifier_sources + extra_sources
        lines.extend(
            [
                f"### {definition['label']} (`{definition['id']}`)",
                "",
                f"- Category: {definition['category']}",
                f"- Lives In: {_bullet_list([str(path) for path in definition.get('lives_in', [])])}",
                f"- Effect: {definition['effect']}",
                f"- Clears / Decay: {definition['clears']}",
                f"- Who Can Apply It: {', '.join(sources) if sources else 'No direct live appliers found in current data.'}",
                "",
            ]
        )

    status_cards = [card for card in cards if str(card.get("type", "")).lower() == "status"]
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
                f"- Live Generators: {', '.join(generators) if generators else 'None found in current data.'}",
                "",
            ]
        )

    output_path = REFERENCE_ROOT / "statuses_master_reference.md"
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def generate_master_references() -> list[Path]:
    enemies = _load_json(ENEMIES_DATA_PATH)
    cards = _load_json(CARDS_DATA_PATH)
    run_modifiers = _load_json(RUN_MODIFIERS_DATA_PATH)
    REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)

    return [
        _write_enemies_reference(enemies),
        _write_cards_reference(cards),
        _write_relics_reference(run_modifiers),
        _write_statuses_reference(cards, enemies, run_modifiers),
    ]


if __name__ == "__main__":
    print(f"Generated at {datetime.now().isoformat(timespec='seconds')}")
    for path in generate_master_references():
        print(path)
