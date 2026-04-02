from __future__ import annotations

import copy
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import core.state_manager as state_manager_module
from config import (
    CARD_SHOP_PRICES,
    ELITE_COMBAT_CREDIT_REWARD,
    REGULAR_COMBAT_CREDIT_REWARD,
    REGULAR_REWARD_CARD_WEIGHT,
    REGULAR_REWARD_PURGE_WEIGHT,
    SHOP_PURGE_PRICE,
    SHOP_REROLL_BASE_PRICE,
    SHOP_REROLL_PRICE_STEP,
)
from core.event_library import EventLibrary
from core.state_manager import StateManager

BASELINE_CARD_SHOP_PRICES = {
    "surge_strike_01": 55,
    "firewall_01": 50,
    "patch_kit_01": 48,
    "cache_draw_01": 54,
    "overclock_01": 62,
    "volley_01": 58,
}
BASELINE_SHOP_PURGE_PRICE = 45
BASELINE_REGULAR_REWARD_CARD_WEIGHT = 1
BASELINE_REGULAR_REWARD_PURGE_WEIGHT = 1
TARGET_AVERAGE_SHOP_CARD_BUYS = (0.5, 1.0)
TARGET_AVERAGE_FINAL_CREDITS = (15.0, 35.0)
TARGET_AVERAGE_FINAL_DECK_SIZE = (10.5, 12.0)
TARGET_AVERAGE_PAID_SINKS = (1.0, 2.0)
PREFERRED_CARD_ORDER = (
    "overclock_01",
    "cache_draw_01",
    "firewall_01",
    "surge_strike_01",
    "volley_01",
    "patch_kit_01",
)
MAX_COMBAT_ACTIONS = 140


@dataclass(frozen=True)
class EconomyScenario:
    name: str
    card_prices: dict[str, int]
    purge_price: int
    regular_reward_card_weight: int
    regular_reward_purge_weight: int
    event_effect_values: dict[str, dict[str, dict[str, int]]]
    reroll_enabled: bool = False


def simulate_run_economy(seed_count: int = 200, start_seed: int = 1) -> dict[str, Any]:
    if seed_count <= 0:
        raise ValueError("seed_count must be a positive integer.")

    baseline_scenario = EconomyScenario(
        name="baseline",
        card_prices=copy.deepcopy(BASELINE_CARD_SHOP_PRICES),
        purge_price=BASELINE_SHOP_PURGE_PRICE,
        regular_reward_card_weight=BASELINE_REGULAR_REWARD_CARD_WEIGHT,
        regular_reward_purge_weight=BASELINE_REGULAR_REWARD_PURGE_WEIGHT,
        event_effect_values={
            "street_clinic_01": {"pay_for_treatment": {"lose_credits": 18, "heal": 14}},
            "credit_shakedown_01": {"refuse": {"damage": 8}},
        },
    )
    tuned_scenario = EconomyScenario(
        name="current_tuned",
        card_prices=copy.deepcopy(CARD_SHOP_PRICES),
        purge_price=SHOP_PURGE_PRICE,
        regular_reward_card_weight=REGULAR_REWARD_CARD_WEIGHT,
        regular_reward_purge_weight=REGULAR_REWARD_PURGE_WEIGHT,
        event_effect_values={
            "street_clinic_01": {"pay_for_treatment": {"lose_credits": 15, "heal": 15}},
            "credit_shakedown_01": {"refuse": {"damage": 6}},
        },
    )
    reroll_scenario = EconomyScenario(
        name="reroll_enabled",
        card_prices=copy.deepcopy(CARD_SHOP_PRICES),
        purge_price=SHOP_PURGE_PRICE,
        regular_reward_card_weight=REGULAR_REWARD_CARD_WEIGHT,
        regular_reward_purge_weight=REGULAR_REWARD_PURGE_WEIGHT,
        event_effect_values={
            "street_clinic_01": {"pay_for_treatment": {"lose_credits": 15, "heal": 15}},
            "credit_shakedown_01": {"refuse": {"damage": 6}},
        },
        reroll_enabled=True,
    )

    baseline_metrics = _simulate_scenario(baseline_scenario, seed_count, start_seed)
    tuned_metrics = _simulate_scenario(tuned_scenario, seed_count, start_seed)
    reroll_metrics = _simulate_scenario(reroll_scenario, seed_count, start_seed)
    comparisons = {
        "current_tuned_vs_baseline": _build_delta(baseline_metrics, tuned_metrics),
        "reroll_enabled_vs_current_tuned": _build_delta(tuned_metrics, reroll_metrics),
        "reroll_enabled_vs_baseline": _build_delta(baseline_metrics, reroll_metrics),
    }
    targets = _assess_targets(reroll_metrics)

    return {
        "seed_count": seed_count,
        "start_seed": start_seed,
        "baseline": baseline_metrics,
        "current_tuned": tuned_metrics,
        "reroll_enabled": reroll_metrics,
        "delta": comparisons["current_tuned_vs_baseline"],
        "comparisons": comparisons,
        "targets": targets,
    }


def _simulate_scenario(
    scenario: EconomyScenario,
    seed_count: int,
    start_seed: int,
) -> dict[str, Any]:
    aggregate: Counter[str] = Counter()
    event_choices: Counter[str] = Counter()
    risky_outcomes: Counter[str] = Counter()
    reward_exposure_totals: Counter[str] = Counter()
    shop_exposure_totals: Counter[str] = Counter()

    for seed in range(start_seed, start_seed + seed_count):
        run_metrics = _simulate_run(seed, scenario)
        aggregate.update(run_metrics["totals"])
        event_choices.update(run_metrics["event_choices"])
        risky_outcomes.update(run_metrics["risky_outcomes"])
        reward_exposure_totals.update(run_metrics["reward_exposure"])
        shop_exposure_totals.update(run_metrics["shop_exposure"])

    averages = _build_averages(aggregate, seed_count)
    return {
        "scenario": scenario.name,
        "seed_count": seed_count,
        "win_rate": _round(aggregate["victories"] / seed_count),
        "averages": averages,
        "event_choice_frequency": dict(sorted(event_choices.items())),
        "risky_outcome_frequency": dict(sorted(risky_outcomes.items())),
        "reward_exposure_frequency": dict(sorted(reward_exposure_totals.items())),
        "shop_exposure_frequency": dict(sorted(shop_exposure_totals.items())),
    }


def _simulate_run(seed: int, scenario: EconomyScenario) -> dict[str, Any]:
    with _patched_state_manager(scenario):
        manager = StateManager(event_library=_event_library_for_scenario(scenario))
        manager.start_new_run(seed=seed)

        totals: Counter[str] = Counter()
        event_choices: Counter[str] = Counter()
        risky_outcomes: Counter[str] = Counter()
        reward_exposure: Counter[str] = Counter()
        shop_exposure: Counter[str] = Counter()

        while manager.current_state not in {"victory", "game_over"}:
            if manager.current_state == "map":
                snapshot = manager.get_state_snapshot()
                chosen_node_id = _choose_map_node(snapshot, scenario)
                node_type = snapshot["map"]["nodes"][chosen_node_id]["node_type"]
                totals[f"node_visit_{node_type}"] += 1
                manager.select_map_node(chosen_node_id)
                continue

            if manager.current_state == "combat":
                encounter_type = manager._current_node_type()
                starting_hp = manager.player.current_hp
                stalled = _play_combat(manager)
                totals["hp_damage_combat"] += max(0, starting_hp - manager.player.current_hp)
                if stalled:
                    totals["stalled_combats"] += 1
                if manager.current_state != "combat":
                    if encounter_type == "combat":
                        totals["credits_earned_combat"] += REGULAR_COMBAT_CREDIT_REWARD
                    elif encounter_type == "elite":
                        totals["credits_earned_elite"] += ELITE_COMBAT_CREDIT_REWARD
                continue

            if manager.current_state == "reward":
                _resolve_reward(manager, totals, reward_exposure)
                continue

            if manager.current_state == "shop":
                _resolve_shop(manager, scenario, totals, shop_exposure)
                continue

            if manager.current_state == "event":
                _resolve_event(manager, totals, event_choices, risky_outcomes)
                continue

            raise ValueError(f"Unsupported state during economy simulation: {manager.current_state}")

        totals["final_hp"] = manager.player.current_hp
        totals["final_credits"] = manager.player.credits
        totals["final_deck_size"] = len(manager.player.deck_manager.starting_deck)
        if manager.current_state == "victory":
            totals["victories"] += 1

        reward_unique_cards = sum(1 for count in reward_exposure.values() if count > 0)
        shop_unique_cards = sum(1 for count in shop_exposure.values() if count > 0)
        totals["reward_unique_cards_seen"] += reward_unique_cards
        totals["shop_unique_cards_seen"] += shop_unique_cards
        totals["combined_unique_cards_seen"] += len(
            {card_id for card_id, count in reward_exposure.items() if count > 0}
            | {card_id for card_id, count in shop_exposure.items() if count > 0}
        )
        totals["paid_sink_count"] += (
            totals["shop_card_buys"]
            + totals["shop_purges"]
            + totals["shop_rerolls"]
            + totals["clinic_uses"]
            + totals["tax_payments"]
        )

        return {
            "totals": totals,
            "event_choices": event_choices,
            "risky_outcomes": risky_outcomes,
            "reward_exposure": reward_exposure,
            "shop_exposure": shop_exposure,
        }


def _choose_map_node(snapshot: dict[str, Any], scenario: EconomyScenario) -> str:
    player = snapshot["player"]
    map_state = snapshot["map"]
    hp_ratio = player["current_hp"] / max(1, player["max_hp"])
    credits = player["credits"]
    affordable_card = min(scenario.card_prices.values())
    affordable_sink = min(affordable_card, scenario.purge_price)

    scored_nodes = []
    for node_id in map_state["available_node_ids"]:
        node_type = map_state["nodes"][node_id]["node_type"]
        score = {"combat": 50, "event": 42, "shop": 20, "elite": 16, "boss": 1000}.get(node_type, 0)

        if node_type == "elite" and hp_ratio > 0.72:
            score = 82
        elif node_type == "shop" and credits >= affordable_sink:
            score = 74
        elif node_type == "event" and (hp_ratio < 0.8 or credits < affordable_card):
            score = 58

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


def _resolve_reward(
    manager: StateManager,
    totals: Counter[str],
    reward_exposure: Counter[str],
) -> None:
    reward_state = manager.get_state_snapshot()["reward"]
    totals["reward_screens"] += 1

    for section in reward_state["sections"]:
        if section["resolved"]:
            continue

        section_id = section["id"]
        if section["type"] == "card_offer":
            for option in section["options"]:
                reward_exposure[option["card_id"]] += 1
            selected_option = max(section["options"], key=lambda option: _card_offer_score(option["card"], manager))
            manager.select_reward_option(section_id, selected_option["option_id"])
            manager.confirm_reward_selection(section_id)
            totals["deck_delta_reward_cards"] += 1
            continue

        if section["type"] == "purge_offer" and section["options"]:
            if _purge_desirability(manager) >= 45:
                selected_option = max(section["options"], key=lambda option: _purge_priority(option, manager))
                manager.select_reward_option(section_id, selected_option["option_id"])
                manager.confirm_reward_selection(section_id)
                totals["deck_delta_reward_purges"] -= 1
            else:
                manager.skip_reward_section(section_id)
            continue

        if section["can_skip"]:
            manager.skip_reward_section(section_id)

    manager.continue_from_reward()


def _resolve_shop(
    manager: StateManager,
    scenario: EconomyScenario,
    totals: Counter[str],
    shop_exposure: Counter[str],
) -> None:
    while manager.current_state == "shop":
        shop_state = manager.get_state_snapshot()["shop"]
        player_credits = manager.player.credits

        available_offers = [offer for offer in shop_state["inventory"] if not offer["sold_out"]]
        for offer in available_offers:
            if offer["type"] == "card":
                shop_exposure[offer["card_id"]] += 1

        card_offers = [offer for offer in available_offers if offer["type"] == "card"]
        purge_offer = next((offer for offer in available_offers if offer["type"] == "purge"), None)

        best_card_offer = None
        best_card_score = float("-inf")
        for offer in card_offers:
            score = _shop_offer_score(offer, player_credits, shop_state, manager)
            if score > best_card_score:
                best_card_offer = offer
                best_card_score = score

        purge_score = (
            _shop_offer_score(purge_offer, player_credits, shop_state, manager)
            if purge_offer is not None
            else float("-inf")
        )

        if best_card_offer is not None and best_card_score >= 18:
            manager.select_shop_offer(best_card_offer["offer_id"])
            totals["shop_spend_cards"] += scenario.card_prices[best_card_offer["card_id"]]
            totals["shop_card_buys"] += 1
            totals["deck_delta_shop_cards"] += 1
            manager.confirm_shop_purchase()
            continue

        if scenario.reroll_enabled and _should_reroll_shop(shop_state, player_credits, best_card_score):
            totals["shop_spend_reroll"] += shop_state["reroll_price"]
            totals["shop_rerolls"] += 1
            manager.reroll_shop_inventory()
            continue

        if best_card_offer is not None and best_card_score >= 8:
            manager.select_shop_offer(best_card_offer["offer_id"])
            totals["shop_spend_cards"] += scenario.card_prices[best_card_offer["card_id"]]
            totals["shop_card_buys"] += 1
            totals["deck_delta_shop_cards"] += 1
            manager.confirm_shop_purchase()
            continue

        if purge_offer is not None and purge_score >= 14:
            manager.select_shop_offer(purge_offer["offer_id"])
            purge_targets = manager.get_state_snapshot()["shop"]["purge_targets"]
            selected_target = max(purge_targets, key=lambda option: _purge_priority(option, manager))
            manager.select_shop_offer(selected_target["option_id"])
            totals["shop_spend_purge"] += scenario.purge_price
            totals["shop_purges"] += 1
            totals["deck_delta_shop_purges"] -= 1
            manager.confirm_shop_purchase()
            continue

        manager.leave_shop()
        return


def _should_reroll_shop(shop_state: dict[str, Any], player_credits: int, best_card_score: float) -> bool:
    if not shop_state.get("can_reroll", False):
        return False
    reroll_price = shop_state["reroll_price"]
    affordable_follow_up = min(CARD_SHOP_PRICES.values())
    if player_credits < reroll_price + affordable_follow_up:
        return False
    return best_card_score < 18


def _shop_offer_score(
    offer: dict[str, Any],
    player_credits: int,
    shop_state: dict[str, Any],
    manager: StateManager,
) -> float:
    if offer["price"] > player_credits:
        return float("-inf")

    if offer["type"] == "purge":
        purge_score = _purge_desirability(manager)
        return purge_score if shop_state["purge_targets"] else float("-inf")

    preference_score = _card_offer_score(offer["card"], manager)
    return preference_score - (offer["price"] * 0.52)


def _resolve_event(
    manager: StateManager,
    totals: Counter[str],
    event_choices: Counter[str],
    risky_outcomes: Counter[str],
) -> None:
    event_state = manager.get_state_snapshot()["event"]
    available_choices = [choice for choice in event_state["choices"] if choice["available"]]
    selected_choice = max(available_choices, key=lambda choice: _event_choice_score(choice, manager))
    before_credits = manager.player.credits
    before_hp = manager.player.current_hp
    before_deck_size = len(manager.player.deck_manager.starting_deck)

    manager.select_event_choice(selected_choice["id"])
    event_choices[selected_choice["id"]] += 1

    if selected_choice["choice_type"] == "purge":
        selected_target = max(
            manager.get_state_snapshot()["event"]["purge_targets"],
            key=lambda option: _purge_priority(option, manager),
        )
        manager.select_event_target(selected_target["option_id"])

    manager.confirm_event_choice()

    if manager.current_state == "event":
        resolved_event = manager.get_state_snapshot()["event"]
        outcome_id = resolved_event["resolved_outcome_id"]
        if outcome_id is not None:
            risky_outcomes[outcome_id] += 1
        manager.continue_from_event()

    credit_delta = manager.player.credits - before_credits
    hp_delta = manager.player.current_hp - before_hp
    deck_delta = len(manager.player.deck_manager.starting_deck) - before_deck_size

    if credit_delta > 0:
        totals["credits_earned_events"] += credit_delta
    elif credit_delta < 0:
        if selected_choice["id"] == "pay_for_treatment":
            totals["credits_spent_clinic"] += -credit_delta
            totals["clinic_uses"] += 1
        elif selected_choice["id"] == "pay_the_tax":
            totals["credits_spent_tax"] += -credit_delta
            totals["tax_payments"] += 1
        else:
            totals["credits_lost_events"] += -credit_delta

    if hp_delta < 0:
        totals["hp_damage_events"] += -hp_delta
    elif hp_delta > 0:
        totals["hp_healing_events"] += hp_delta

    if deck_delta > 0:
        totals["deck_delta_event_cards"] += deck_delta
    elif deck_delta < 0:
        totals["deck_delta_event_purges"] += deck_delta


def _event_choice_score(choice: dict[str, Any], manager: StateManager) -> int:
    player = manager.player
    missing_hp = player.max_hp - player.current_hp
    return {
        "crack_cache": 90,
        "walk_away": 10,
        "pay_for_treatment": 88 if missing_hp >= 14 else 56 if missing_hp >= 10 else 24,
        "decline_treatment": 15,
        "purge_card": _purge_desirability(manager),
        "leave_deck_alone": 10,
        "force_the_cache": 72 if player.current_hp > 20 else 20,
        "leave_the_shard": 15,
        "pay_the_tax": 55 if player.current_hp < 22 else 30,
        "refuse": 50 if player.current_hp > 25 else 5,
        "spin_the_daemon": 68 if player.current_hp > 20 else 20,
        "ignore_terminal": 15,
    }.get(choice["id"], 0)


def _card_preference_rank(card_id: str) -> int:
    try:
        return len(PREFERRED_CARD_ORDER) - PREFERRED_CARD_ORDER.index(card_id)
    except ValueError:
        return 0


def _card_offer_score(card: dict[str, Any], manager: StateManager) -> int:
    profile = _deck_profile(manager)
    card_id = card["id"]
    score = _card_preference_rank(card_id) * 14
    if card["type"] == "attack" and profile["attack_cards"] < 4:
        score += 45
    if card_id == "patch_kit_01" and profile["missing_hp"] >= 12:
        score += 18
    if card_id in {"overclock_01", "cache_draw_01"} and profile["deck_size"] > 11:
        score += 12
    return score


def _purge_priority(option: dict[str, Any], manager: StateManager) -> int:
    profile = _deck_profile(manager)
    card = option["card"]
    card_id = card["id"]
    if card_id == "strike_01" and profile["attack_cards"] > 4:
        return 3
    if card_id == "defend_01":
        return 2
    if card_id == "strike_01":
        return 1
    return 1


def _purge_desirability(manager: StateManager) -> int:
    profile = _deck_profile(manager)
    if profile["starter_cards"] < 5 or profile["deck_size"] <= 9:
        return 4
    if profile["attack_cards"] <= 3:
        return 8
    if profile["deck_size"] >= 12 and profile["starter_cards"] >= 6:
        return 48
    if profile["deck_size"] >= 11 and profile["starter_cards"] >= 5:
        return 34
    if profile["starter_cards"] >= 6:
        return 18
    return 8


def _deck_profile(manager: StateManager) -> dict[str, int]:
    deck = manager.player.deck_manager.starting_deck
    attack_cards = sum(1 for card in deck if card.type == "attack")
    starter_cards = sum(1 for card in deck if card.id in {"strike_01", "defend_01"})
    return {
        "deck_size": len(deck),
        "attack_cards": attack_cards,
        "starter_cards": starter_cards,
        "missing_hp": manager.player.max_hp - manager.player.current_hp,
    }


def _build_averages(aggregate: Counter[str], seed_count: int) -> dict[str, Any]:
    return {
        "node_visits": {
            "combat": _round(aggregate["node_visit_combat"] / seed_count),
            "elite": _round(aggregate["node_visit_elite"] / seed_count),
            "event": _round(aggregate["node_visit_event"] / seed_count),
            "shop": _round(aggregate["node_visit_shop"] / seed_count),
            "boss": _round(aggregate["node_visit_boss"] / seed_count),
        },
        "credits_earned_by_source": {
            "combat": _round(aggregate["credits_earned_combat"] / seed_count),
            "elite": _round(aggregate["credits_earned_elite"] / seed_count),
            "events": _round(aggregate["credits_earned_events"] / seed_count),
        },
        "credits_spent_by_source": {
            "shop_cards": _round(aggregate["shop_spend_cards"] / seed_count),
            "shop_purge": _round(aggregate["shop_spend_purge"] / seed_count),
            "shop_reroll": _round(aggregate["shop_spend_reroll"] / seed_count),
            "clinic": _round(aggregate["credits_spent_clinic"] / seed_count),
            "shakedown": _round(aggregate["credits_spent_tax"] / seed_count),
        },
        "hp_delta_by_source": {
            "combat_damage_taken": _round(aggregate["hp_damage_combat"] / seed_count),
            "event_damage_taken": _round(aggregate["hp_damage_events"] / seed_count),
            "event_healing": _round(aggregate["hp_healing_events"] / seed_count),
        },
        "deck_delta_by_source": {
            "reward_cards": _round(aggregate["deck_delta_reward_cards"] / seed_count),
            "reward_purges": _round(aggregate["deck_delta_reward_purges"] / seed_count),
            "shop_cards": _round(aggregate["deck_delta_shop_cards"] / seed_count),
            "shop_purges": _round(aggregate["deck_delta_shop_purges"] / seed_count),
            "event_cards": _round(aggregate["deck_delta_event_cards"] / seed_count),
            "event_purges": _round(aggregate["deck_delta_event_purges"] / seed_count),
        },
        "final_stats": {
            "hp": _round(aggregate["final_hp"] / seed_count),
            "credits": _round(aggregate["final_credits"] / seed_count),
            "deck_size": _round(aggregate["final_deck_size"] / seed_count),
        },
        "reward_screens": _round(aggregate["reward_screens"] / seed_count),
        "shop_card_buys": _round(aggregate["shop_card_buys"] / seed_count),
        "shop_purges": _round(aggregate["shop_purges"] / seed_count),
        "shop_rerolls": _round(aggregate["shop_rerolls"] / seed_count),
        "clinic_uses": _round(aggregate["clinic_uses"] / seed_count),
        "tax_payments": _round(aggregate["tax_payments"] / seed_count),
        "paid_sink_count": _round(aggregate["paid_sink_count"] / seed_count),
        "unique_card_exposure_per_run": {
            "reward": _round(aggregate["reward_unique_cards_seen"] / seed_count),
            "shop": _round(aggregate["shop_unique_cards_seen"] / seed_count),
            "combined": _round(aggregate["combined_unique_cards_seen"] / seed_count),
        },
    }


def _build_delta(baseline: dict[str, Any], tuned: dict[str, Any]) -> dict[str, Any]:
    baseline_averages = baseline["averages"]
    tuned_averages = tuned["averages"]
    return {
        "shop_card_buys": _round(
            tuned_averages["shop_card_buys"] - baseline_averages["shop_card_buys"]
        ),
        "shop_rerolls": _round(
            tuned_averages.get("shop_rerolls", 0) - baseline_averages.get("shop_rerolls", 0)
        ),
        "paid_sink_count": _round(
            tuned_averages["paid_sink_count"] - baseline_averages["paid_sink_count"]
        ),
        "final_credits": _round(
            tuned_averages["final_stats"]["credits"] - baseline_averages["final_stats"]["credits"]
        ),
        "final_deck_size": _round(
            tuned_averages["final_stats"]["deck_size"] - baseline_averages["final_stats"]["deck_size"]
        ),
        "win_rate": _round(tuned["win_rate"] - baseline["win_rate"]),
    }


def _assess_targets(metrics: dict[str, Any]) -> dict[str, Any]:
    averages = metrics["averages"]
    checks = {
        "shop_card_buys": _target_check(
            averages["shop_card_buys"],
            TARGET_AVERAGE_SHOP_CARD_BUYS,
            "Average shop card buys per run",
        ),
        "final_credits": _target_check(
            averages["final_stats"]["credits"],
            TARGET_AVERAGE_FINAL_CREDITS,
            "Average final credits",
        ),
        "final_deck_size": _target_check(
            averages["final_stats"]["deck_size"],
            TARGET_AVERAGE_FINAL_DECK_SIZE,
            "Average final deck size",
        ),
        "paid_sink_count": _target_check(
            averages["paid_sink_count"],
            TARGET_AVERAGE_PAID_SINKS,
            "Average paid sinks per run",
        ),
    }
    checks["all_targets_met"] = all(check["met"] for check in checks.values())
    return checks


def _target_check(value: float, bounds: tuple[float, float], label: str) -> dict[str, Any]:
    lower_bound, upper_bound = bounds
    return {
        "label": label,
        "value": _round(value),
        "target_range": [_round(lower_bound), _round(upper_bound)],
        "met": lower_bound <= value <= upper_bound,
    }


def _event_library_for_scenario(scenario: EconomyScenario) -> EventLibrary:
    library = EventLibrary()
    library.load_events()
    patched_events = copy.deepcopy(library._events)

    for event_id, choice_overrides in scenario.event_effect_values.items():
        event = patched_events[event_id]
        for choice in event["choices"]:
            if choice["id"] not in choice_overrides:
                continue
            effect_overrides = choice_overrides[choice["id"]]
            for effect in choice["effects"]:
                if effect["type"] in effect_overrides:
                    effect["value"] = effect_overrides[effect["type"]]

    library._events = patched_events
    return library


@contextmanager
def _patched_state_manager(scenario: EconomyScenario) -> Iterator[None]:
    original_values = {
        "CARD_SHOP_PRICES": state_manager_module.CARD_SHOP_PRICES,
        "SHOP_PURGE_PRICE": state_manager_module.SHOP_PURGE_PRICE,
        "REGULAR_REWARD_CARD_WEIGHT": state_manager_module.REGULAR_REWARD_CARD_WEIGHT,
        "REGULAR_REWARD_PURGE_WEIGHT": state_manager_module.REGULAR_REWARD_PURGE_WEIGHT,
    }
    state_manager_module.CARD_SHOP_PRICES = copy.deepcopy(scenario.card_prices)
    state_manager_module.SHOP_PURGE_PRICE = scenario.purge_price
    state_manager_module.REGULAR_REWARD_CARD_WEIGHT = scenario.regular_reward_card_weight
    state_manager_module.REGULAR_REWARD_PURGE_WEIGHT = scenario.regular_reward_purge_weight
    try:
        yield
    finally:
        for name, value in original_values.items():
            setattr(state_manager_module, name, value)


def _round(value: float) -> float:
    return round(value, 2)


def _format_report(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    tuned = report["current_tuned"]
    reroll = report["reroll_enabled"]
    tuned_delta = report["comparisons"]["current_tuned_vs_baseline"]
    reroll_delta = report["comparisons"]["reroll_enabled_vs_current_tuned"]
    targets = report["targets"]
    reroll_credit_drop = -reroll_delta["final_credits"]
    second_sink_needed = (
        reroll["averages"]["final_stats"]["credits"] > 40
        or reroll["averages"]["paid_sink_count"] < 1.0
    )
    recommendation = (
        "A second shop-only sink is still recommended."
        if second_sink_needed
        else "A second shop-only sink is not required yet."
    )
    credit_assessment = (
        "End-of-run excess credits dropped meaningfully."
        if reroll_credit_drop >= 8
        else "End-of-run excess credits did not drop meaningfully."
    )
    regression_assessment = (
        "Shop engagement, deck growth, and win rate stayed within acceptable bounds."
        if reroll_delta["shop_card_buys"] >= -0.05
        and reroll_delta["win_rate"] >= -0.03
        and 10.5 <= reroll["averages"]["final_stats"]["deck_size"] <= 12.0
        else "One or more secondary metrics regressed beyond the desired band."
    )
    return "\n".join(
        [
            "Run Economy Audit",
            f"Seeds: {report['start_seed']}..{report['start_seed'] + report['seed_count'] - 1}",
            f"Shop reroll cost: {SHOP_REROLL_BASE_PRICE} + ({SHOP_REROLL_PRICE_STEP} x rerolls used in that shop)",
            "",
            "Pre-Tuning Snapshot",
            f"- Win rate: {baseline['win_rate']}",
            f"- Avg final credits: {baseline['averages']['final_stats']['credits']}",
            f"- Avg shop card buys: {baseline['averages']['shop_card_buys']}",
            f"- Avg final deck size: {baseline['averages']['final_stats']['deck_size']}",
            f"- Avg paid sinks: {baseline['averages']['paid_sink_count']}",
            "",
            "Current Tuned Snapshot",
            f"- Win rate: {tuned['win_rate']}",
            f"- Avg final credits: {tuned['averages']['final_stats']['credits']}",
            f"- Avg shop card buys: {tuned['averages']['shop_card_buys']}",
            f"- Avg shop rerolls: {tuned['averages']['shop_rerolls']}",
            f"- Avg final deck size: {tuned['averages']['final_stats']['deck_size']}",
            f"- Avg paid sinks: {tuned['averages']['paid_sink_count']}",
            "",
            "Reroll-Enabled Snapshot",
            f"- Win rate: {reroll['win_rate']}",
            f"- Avg final credits: {reroll['averages']['final_stats']['credits']}",
            f"- Avg shop card buys: {reroll['averages']['shop_card_buys']}",
            f"- Avg shop rerolls: {reroll['averages']['shop_rerolls']}",
            f"- Avg final deck size: {reroll['averages']['final_stats']['deck_size']}",
            f"- Avg paid sinks: {reroll['averages']['paid_sink_count']}",
            "",
            "Current Tuned Vs Baseline",
            f"- Win rate: {tuned_delta['win_rate']:+}",
            f"- Avg final credits: {tuned_delta['final_credits']:+}",
            f"- Avg shop card buys: {tuned_delta['shop_card_buys']:+}",
            f"- Avg shop rerolls: {tuned_delta['shop_rerolls']:+}",
            f"- Avg final deck size: {tuned_delta['final_deck_size']:+}",
            f"- Avg paid sinks: {tuned_delta['paid_sink_count']:+}",
            "",
            "Reroll-Enabled Vs Current Tuned",
            f"- Win rate: {reroll_delta['win_rate']:+}",
            f"- Avg final credits: {reroll_delta['final_credits']:+}",
            f"- Avg shop card buys: {reroll_delta['shop_card_buys']:+}",
            f"- Avg shop rerolls: {reroll_delta['shop_rerolls']:+}",
            f"- Avg final deck size: {reroll_delta['final_deck_size']:+}",
            f"- Avg paid sinks: {reroll_delta['paid_sink_count']:+}",
            "",
            "Reroll-Enabled Target Checks",
            *[
                f"- {target['label']}: {target['value']} (target {target['target_range'][0]}-{target['target_range'][1]})"
                for key, target in targets.items()
                if key != "all_targets_met"
            ],
            f"- All targets met: {targets['all_targets_met']}",
            "",
            "Assessment",
            f"- {credit_assessment}",
            f"- {regression_assessment}",
            f"- Recommendation: {recommendation}",
        ]
    )


if __name__ == "__main__":
    print(_format_report(simulate_run_economy()))
