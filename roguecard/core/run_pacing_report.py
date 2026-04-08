from __future__ import annotations

from collections import Counter
from typing import Any

from core.state_manager import StateManager
from core.run_modifier_library import RunModifierLibrary

PREFERRED_CARD_ORDER = (
    "overclock_01",
    "cache_draw_01",
    "firewall_01",
    "surge_strike_01",
    "volley_01",
    "patch_kit_01",
)
MAX_COMBAT_ACTIONS = 140


def simulate_run_pacing(seed_count: int = 200, start_seed: int = 1) -> dict[str, Any]:
    if seed_count <= 0:
        raise ValueError("seed_count must be a positive integer.")

    modifier_library = RunModifierLibrary()
    modifiers_by_name = {
        modifier["name"]: modifier for modifier in modifier_library.list_modifiers()
    }

    totals: Counter[str] = Counter()
    event_rarity_distribution: Counter[str] = Counter()
    event_tag_distribution: Counter[str] = Counter()
    status_rarity_distribution: Counter[str] = Counter()
    status_source_distribution: Counter[str] = Counter()
    starter_offer_rarity_distribution: Counter[str] = Counter()

    for seed in range(start_seed, start_seed + seed_count):
        run_report = _simulate_single_run(seed, modifiers_by_name)
        totals.update(run_report["totals"])
        event_rarity_distribution.update(run_report["event_rarity_distribution"])
        event_tag_distribution.update(run_report["event_tag_distribution"])
        status_rarity_distribution.update(run_report["status_rarity_distribution"])
        status_source_distribution.update(run_report["status_source_distribution"])
        starter_offer_rarity_distribution.update(run_report["starter_offer_rarity_distribution"])

    total_event_picks = totals["event_picks"]
    total_transitions = totals["tag_transitions"]
    total_starter_offers = totals["starter_offer_count"]

    return {
        "seed_count": seed_count,
        "start_seed": start_seed,
        "event_rarity_distribution": _as_ratio_dict(event_rarity_distribution, total_event_picks),
        "event_tag_distribution": _as_ratio_dict(event_tag_distribution, total_event_picks),
        "status_rarity_distribution": _as_ratio_dict(status_rarity_distribution, totals["status_grants"]),
        "status_source_distribution": _as_ratio_dict(status_source_distribution, totals["status_grants"]),
        "starter_offer_rarity_distribution": _as_ratio_dict(
            starter_offer_rarity_distribution,
            total_starter_offers,
        ),
        "repeat_event_rate": _round(_safe_divide(totals["repeat_event_picks"], total_event_picks)),
        "dominant_tag_repeat_rate": _round(_safe_divide(totals["same_tag_transitions"], total_transitions)),
        "starter_curse_slot_rate": _round(_safe_divide(totals["starter_curse_slots"], seed_count)),
        "average_events_per_run": _round(_safe_divide(total_event_picks, seed_count)),
        "average_status_grants_per_run": _round(_safe_divide(totals["status_grants"], seed_count)),
        "wins": totals["wins"],
        "win_rate": _round(_safe_divide(totals["wins"], seed_count)),
    }


def _simulate_single_run(seed: int, modifiers_by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    manager = StateManager()
    snapshot = manager.start_new_run(seed=seed)

    totals: Counter[str] = Counter()
    event_rarity_distribution: Counter[str] = Counter()
    event_tag_distribution: Counter[str] = Counter()
    status_rarity_distribution: Counter[str] = Counter()
    status_source_distribution: Counter[str] = Counter()
    starter_offer_rarity_distribution: Counter[str] = Counter()

    draft_offers = snapshot["modifier_draft"]["offers"]
    totals["starter_offer_count"] += len(draft_offers)
    for offer in draft_offers:
        starter_offer_rarity_distribution[offer["rarity"]] += 1
    if len(draft_offers) >= 3 and draft_offers[2]["type"] == "curse":
        totals["starter_curse_slots"] += 1

    chosen_offer = max(draft_offers, key=_modifier_offer_score)
    manager.select_run_modifier_offer(chosen_offer["id"])
    manager.confirm_run_modifier_selection()
    status_rarity_distribution[chosen_offer["rarity"]] += 1
    status_source_distribution["run_start"] += 1
    totals["status_grants"] += 1

    run_seen_events: set[str] = set()
    last_tag: str | None = None

    while manager.current_state not in {"victory", "game_over"}:
        if manager.current_state == "map":
            node_id = _choose_map_node(manager.get_state_snapshot())
            manager.select_map_node(node_id)
            continue

        if manager.current_state == "combat":
            stalled = _play_combat(manager)
            if stalled:
                break
            continue

        if manager.current_state == "reward":
            _resolve_reward(manager)
            continue

        if manager.current_state == "shop":
            _resolve_shop(manager)
            continue

        if manager.current_state == "event":
            event_snapshot = manager.get_state_snapshot()["event"]
            event_definition = manager.event_library.get_event(event_snapshot["event_id"])
            totals["event_picks"] += 1
            event_rarity_distribution[event_definition["rarity"]] += 1
            event_tag_distribution[event_definition["primary_tag"]] += 1
            if event_definition["id"] in run_seen_events:
                totals["repeat_event_picks"] += 1
            run_seen_events.add(event_definition["id"])
            if last_tag is not None:
                totals["tag_transitions"] += 1
                if event_definition["primary_tag"] == last_tag:
                    totals["same_tag_transitions"] += 1
            last_tag = event_definition["primary_tag"]

            before_names = {modifier["name"] for modifier in manager.get_state_snapshot()["run_modifiers"]["active"]}
            choice = max(
                (choice for choice in event_snapshot["choices"] if choice["available"]),
                key=_event_choice_score,
            )
            manager.select_event_choice(choice["id"])
            if manager.get_state_snapshot()["event"]["selected_choice_type"] == "purge":
                purge_targets = manager.get_state_snapshot()["event"]["purge_targets"]
                if purge_targets:
                    manager.select_event_target(purge_targets[0]["option_id"])
            manager.confirm_event_choice()

            if manager.current_state == "event":
                resolved_event = manager.get_state_snapshot()["event"]
                granted_names = _modifier_names_from_details(
                    resolved_event["resolution_details"],
                    modifiers_by_name,
                )
                after_names = {modifier["name"] for modifier in manager.get_state_snapshot()["run_modifiers"]["active"]}
                if not granted_names:
                    granted_names = sorted(after_names.difference(before_names))
                for modifier_name in granted_names:
                    modifier = modifiers_by_name.get(modifier_name)
                    if modifier is None:
                        continue
                    status_rarity_distribution[modifier["rarity"]] += 1
                    status_source_distribution[modifier["source_types"][0]] += 1
                    totals["status_grants"] += 1
                manager.continue_from_event()
            continue

        raise ValueError(f"Unsupported state during pacing simulation: {manager.current_state}")

    if manager.current_state == "victory":
        totals["wins"] += 1

    return {
        "totals": totals,
        "event_rarity_distribution": event_rarity_distribution,
        "event_tag_distribution": event_tag_distribution,
        "status_rarity_distribution": status_rarity_distribution,
        "status_source_distribution": status_source_distribution,
        "starter_offer_rarity_distribution": starter_offer_rarity_distribution,
    }


def _modifier_offer_score(offer: dict[str, Any]) -> int:
    return {
        "market_key": 78,
        "deep_pockets": 72,
        "signal_router": 69,
        "carbon_weave": 64,
        "overclock_relay": 61,
        "flash_cache": 58,
        "patch_priority": 54,
        "champion_contract": 52,
        "clean_slate": 48,
        "salvage_license": 44,
        "shard_seed": 42,
        "plated_grip": 40,
        "surge_fuse": 40,
        "lean_market": 34,
        "glass_engine": 28,
        "blood_money": 24,
    }.get(offer["id"], 20)


def _choose_map_node(snapshot: dict[str, Any]) -> str:
    player = snapshot["player"]
    map_state = snapshot["map"]
    hp_ratio = player["current_hp"] / max(1, player["max_hp"])
    credits = player["credits"]
    scored_nodes = []
    for node_id in map_state["available_node_ids"]:
        node_type = map_state["nodes"][node_id]["node_type"]
        score = {"boss": 1000, "event": 90, "shop": 42, "elite": 34, "combat": 28}.get(node_type, 0)
        if node_type == "elite" and hp_ratio > 0.72:
            score = 72
        elif node_type == "shop" and credits >= 40:
            score = 66
        elif node_type == "combat" and hp_ratio < 0.4:
            score = 12
        scored_nodes.append((score, node_id))
    scored_nodes.sort(reverse=True)
    return scored_nodes[0][1]


def _play_combat(manager: StateManager) -> bool:
    action_count = 0
    while manager.current_state == "combat":
        action_count += 1
        if action_count > MAX_COMBAT_ACTIONS:
            manager.player.current_hp = 0
            manager.combat_manager.combat_active = False
            manager._close_combat()
            return True

        snapshot = manager.get_state_snapshot()
        combat = snapshot["combat"]
        player = snapshot["player"]
        enemy = next(enemy for enemy in combat["enemies"] if enemy["id"] in combat["living_enemy_ids"])
        candidates = []

        for index, card in enumerate(snapshot["player_hand"]):
            if card["cost"] > player["energy"]:
                continue

            score = 0
            effect_values = {effect["type"]: effect.get("value", 0) for effect in card["effects"]}
            damage = effect_values.get("damage", 0)
            block = effect_values.get("block", 0)
            heal = effect_values.get("heal", 0)
            draw = effect_values.get("draw", 0)
            energy = effect_values.get("energy", 0)

            if energy or draw:
                score += 60 + (energy * 10) + (draw * 5)
            if damage:
                score += 30 + damage
                if damage >= enemy["current_hp"] + enemy.get("block", 0):
                    score += 100
            if block:
                score += 25 + block if enemy.get("current_intent") == "attack" else 5
            if heal and player["current_hp"] < player["max_hp"]:
                score += 15 + heal

            candidates.append((score, index, card))

        if not candidates:
            manager.end_combat_turn()
            continue

        _, chosen_index, chosen_card = max(candidates)
        target_id = (
            enemy["id"]
            if any(effect["type"] == "damage" for effect in chosen_card["effects"])
            else None
        )
        manager.play_card_from_hand(chosen_index, target_id=target_id)
    return False


def _resolve_reward(manager: StateManager) -> None:
    reward_state = manager.get_state_snapshot()["reward"]
    for section in reward_state["sections"]:
        if section["resolved"]:
            continue
        if section["type"] == "card_offer" and section["options"]:
            selected_option = max(section["options"], key=lambda option: _card_offer_score(option["card"]))
            manager.select_reward_option(section["id"], selected_option["option_id"])
            manager.confirm_reward_selection(section["id"])
            continue
        if section["can_skip"]:
            manager.skip_reward_section(section["id"])
    manager.continue_from_reward()


def _resolve_shop(manager: StateManager) -> None:
    shop_state = manager.get_state_snapshot()["shop"]
    heal_offer = next(
        (offer for offer in shop_state["inventory"] if offer["type"] == "heal" and not offer["sold_out"]),
        None,
    )
    if heal_offer is not None:
        missing_hp = manager.player.max_hp - manager.player.current_hp
        if missing_hp >= heal_offer.get("heal_amount", 14) and heal_offer["price"] <= manager.player.credits:
            manager.select_shop_offer(heal_offer["offer_id"])
            manager.confirm_shop_purchase()
            manager.leave_shop()
            return
    manager.leave_shop()


def _event_choice_score(choice: dict[str, Any]) -> int:
    return {
        "crack_cache": 90,
        "walk_away": 10,
        "pay_for_treatment": 80,
        "decline_treatment": 10,
        "purge_card": 70,
        "keep_deck_alone": 10,
        "force_the_cache": 64,
        "leave_the_shard": 10,
        "pay_the_tax": 46,
        "refuse": 44,
        "spin_the_daemon": 68,
        "ignore_terminal": 12,
        "install_warranty": 60,
        "join_the_choir": 56,
        "sign_the_advance": 42,
        "take_the_scar": 38,
        "install_chip": 62,
        "take_the_odds": 60,
        "take_the_advance": 58,
        "optimize_flow": 64,
        "install_echo": 54,
        "study_the_rhythm": 52,
        "embrace_the_glitch": 58,
        "sign_in_blood": 46,
        "take_clean_stims": 66,
        "take_dirty_stims": 55,
    }.get(choice["id"], 18)


def _card_offer_score(card: dict[str, Any]) -> int:
    try:
        return len(PREFERRED_CARD_ORDER) - PREFERRED_CARD_ORDER.index(card["id"])
    except ValueError:
        return 0


def _modifier_names_from_details(
    resolution_details: list[str],
    modifiers_by_name: dict[str, dict[str, Any]],
) -> list[str]:
    found_names: list[str] = []
    prefixes = ("Gained: ", "Refreshed: ", "Intensified: ", "Stacked: ")
    for detail in resolution_details:
        for prefix in prefixes:
            if not detail.startswith(prefix):
                continue
            raw_name = detail[len(prefix):].split(".")[0].split(" x")[0].strip()
            if raw_name in modifiers_by_name:
                found_names.append(raw_name)
            break
    return found_names


def _as_ratio_dict(counter: Counter[str], total: int) -> dict[str, Any]:
    if total <= 0:
        return {}
    return {
        key: {
            "count": count,
            "rate": _round(count / total),
        }
        for key, count in sorted(counter.items())
    }


def _safe_divide(value: float, divisor: float) -> float:
    if divisor == 0:
        return 0.0
    return value / divisor


def _round(value: float) -> float:
    return round(value, 4)


def _format_report(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Run Pacing Audit",
            f"Seeds: {report['start_seed']}..{report['start_seed'] + report['seed_count'] - 1}",
            f"Win rate: {report['win_rate']}",
            f"Average events per run: {report['average_events_per_run']}",
            f"Average status grants per run: {report['average_status_grants_per_run']}",
            f"Repeat event rate: {report['repeat_event_rate']}",
            f"Dominant tag repeat rate: {report['dominant_tag_repeat_rate']}",
            f"Starter curse-slot rate: {report['starter_curse_slot_rate']}",
            "",
            "Event rarity distribution:",
            *[
                f"- {rarity}: {payload['count']} ({payload['rate']})"
                for rarity, payload in report["event_rarity_distribution"].items()
            ],
            "",
            "Status rarity distribution:",
            *[
                f"- {rarity}: {payload['count']} ({payload['rate']})"
                for rarity, payload in report["status_rarity_distribution"].items()
            ],
            "",
            "Status source distribution:",
            *[
                f"- {source}: {payload['count']} ({payload['rate']})"
                for source, payload in report["status_source_distribution"].items()
            ],
        ]
    )


if __name__ == "__main__":
    print(_format_report(simulate_run_pacing()))
