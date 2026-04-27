from __future__ import annotations

import copy
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import DEFAULT_HIGH_CONTRAST, DEFAULT_UI_SCALE, SCREEN_SIZE
from core.state_manager import StateManager
from ui.ui_manager import UIManager


def capture_visual_audit(
    output_dir: str | Path | None = None,
    seed: int = 29,
    max_steps: int = 240,
) -> dict[str, Any]:
    if pygame is None:
        raise RuntimeError("Pygame is required to capture visual audit screenshots.")

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    pygame.init()
    pygame.display.set_mode((1, 1))

    output_path = Path(output_dir) if output_dir is not None else Path(tempfile.mkdtemp(prefix="roguecard_visual_audit_"))
    output_path.mkdir(parents=True, exist_ok=True)

    manager = StateManager()
    ui_manager = UIManager()
    ui_manager.preload_assets()
    surface = pygame.Surface(SCREEN_SIZE).convert_alpha()

    captured_paths: dict[str, str] = {}
    manager.start_new_run(seed=seed)

    step_count = 0
    while manager.current_state not in {"victory", "game_over"} and step_count < max_steps:
        step_count += 1
        snapshot = _presentation_snapshot(manager.get_state_snapshot())
        _capture_screen(ui_manager, surface, snapshot, output_path, captured_paths)

        if manager.current_state == "character_select":
            manager.select_character("operator")
            manager.confirm_character_selection()
            continue

        if manager.current_state == "map":
            manager.select_map_node(_choose_map_node(snapshot, captured_paths))
            continue

        if manager.current_state == "modifier_draft":
            _resolve_modifier_draft(manager)
            continue

        if manager.current_state == "combat":
            _capture_combat_status_icon_showcase(ui_manager, surface, snapshot, output_path, captured_paths)
            _capture_combat_relic_tray_showcase(manager, ui_manager, surface, snapshot, output_path, captured_paths)
            _play_simple_combat(manager)
            continue

        if manager.current_state == "reward":
            _resolve_reward(manager)
            continue

        if manager.current_state == "shop":
            _resolve_shop(manager, output_path, ui_manager, surface, captured_paths)
            continue

        if manager.current_state == "event":
            _resolve_event(manager)
            continue

        raise ValueError(f"Unsupported state during visual audit capture: {manager.current_state}")

    final_snapshot = _presentation_snapshot(manager.get_state_snapshot())
    _capture_screen(ui_manager, surface, final_snapshot, output_path, captured_paths, force_name=manager.current_state)
    pygame.quit()

    return {
        "output_dir": str(output_path),
        "final_state": manager.current_state,
        "captured": captured_paths,
        "steps": step_count,
    }


def _presentation_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot["presentation"] = {
        "fullscreen": False,
        "fast_mode": False,
        "pause_open": False,
        "settings_open": False,
        "settings_page": "general",
        "presentation_scale": 1.0,
        "ui_scale": DEFAULT_UI_SCALE,
        "screen_shake": False,
        "high_contrast": DEFAULT_HIGH_CONTRAST,
        "master_volume": 0.8,
        "music_volume": 0.5,
        "muted": True,
        "animation": {"state": "idle"},
    }
    snapshot["ui_notice"] = None
    return snapshot


def _capture_screen(
    ui_manager: UIManager,
    surface: Any,
    snapshot: dict[str, Any],
    output_path: Path,
    captured_paths: dict[str, str],
    force_name: str | None = None,
) -> None:
    current_state = snapshot["current_state"]
    capture_name = force_name or _capture_name_for_state(current_state)
    if capture_name in captured_paths:
        return

    ui_manager.render(surface, snapshot)
    file_path = output_path / f"{capture_name}.png"
    pygame.image.save(surface, str(file_path))
    captured_paths[capture_name] = str(file_path)


def _capture_name_for_state(current_state: str) -> str:
    return {
        "modifier_draft": "modifier_draft",
        "map": "map",
        "combat": "combat",
        "reward": "reward",
        "shop": "shop",
        "event": "event",
        "victory": "victory",
        "game_over": "game_over",
    }.get(current_state, current_state)


def _choose_map_node(snapshot: dict[str, Any], captured_paths: dict[str, str]) -> str:
    map_state = snapshot["map"]
    available_node_ids = list(map_state["available_node_ids"])
    nodes = map_state["nodes"]

    preferred_missing = []
    if "shop" not in captured_paths:
        preferred_missing.append("shop")
    if "event" not in captured_paths:
        preferred_missing.append("event")
    if "reward" not in captured_paths:
        preferred_missing.extend(["combat", "elite"])

    for preferred_type in preferred_missing:
        for node_id in available_node_ids:
            if nodes[node_id]["node_type"] == preferred_type:
                return node_id

    priority = {"boss": 99, "elite": 75, "combat": 60, "shop": 48, "event": 44}
    ranked_nodes = sorted(
        available_node_ids,
        key=lambda node_id: (priority.get(nodes[node_id]["node_type"], 0), node_id),
        reverse=True,
    )
    return ranked_nodes[0]


def _play_simple_combat(manager: StateManager) -> None:
    # The audit only needs a representative combat screen; force a deterministic
    # win after capture so unrelated combat bugs do not block the screenshot pass.
    if manager.current_state != "combat" or manager.combat_manager is None:
        return

    for enemy in manager.combat_manager.enemies:
        enemy.current_hp = 0
    manager.combat_manager.combat_active = False
    manager._close_combat()


def _capture_combat_status_icon_showcase(
    ui_manager: UIManager,
    surface: Any,
    snapshot: dict[str, Any],
    output_path: Path,
    captured_paths: dict[str, str],
) -> None:
    if snapshot.get("current_state") != "combat" or snapshot.get("combat") is None:
        return
    if "combat_status_icons" in captured_paths:
        return

    ui_manager.combat_ui._reset_feedback_state()
    showcase = copy.deepcopy(snapshot)
    showcase["status_message"] = "Combat status icon showcase."
    showcase["combat"]["turn_number"] = 5
    showcase["combat"]["turn_owner"] = "player"
    showcase["combat"]["event_log"] = [
        {"card_id": "bio_hemorrhage_01", "summary": "Hemorrhage applied Bleed 2 to Salvage Brute."}
    ]
    showcase["combat"]["active_bark"] = None
    showcase["combat"]["player"] = {
        **showcase["combat"]["player"],
        "current_hp": 57,
        "max_hp": 70,
        "block": 4,
        "energy": 3,
        "max_energy": 3,
        "strength": 2,
        "weak": 1,
        "vulnerable": 1,
        "combat_statuses": {
            "infect": 2,
            "burn": 1,
            "bleed": 3,
            "marked": 2,
            "suppressed": 1,
            "nullified": True,
        },
    }
    showcase["combat"]["enemies"] = [
        {
            "id": "showcase_salvage_brute",
            "name": "Salvage Brute",
            "faction_id": "cinder_jackals",
            "tier": "normal",
            "current_hp": 18,
            "max_hp": 34,
            "block": 0,
            "strength": 1,
            "weak": 0,
            "vulnerable": 1,
            "current_intent": "scrap_rend",
            "intent_value": 7,
            "intent_summary": "Attack for 7 and apply 2 Bleed.",
            "intent_display": {
                "kind": "mixed",
                "damage_per_hit": 7,
                "hit_count": 1,
                "total_damage": 7,
                "block": 0,
                "buffs": [],
                "debuffs": ["Bleed"],
                "icon_effects": [
                    {"icon_id": "bleed", "count": 2, "category": "combat_status", "label": "Bleed"}
                ],
                "summon_count": 0,
                "tooltip": "Attack for 7 and apply 2 Bleed.",
            },
            "statuses": {
                "bleed": 4,
                "marked": 2,
                "suppressed": 1,
                "nullified": 1,
                "momentum": 2,
            },
        },
        {
            "id": "showcase_signal_leech",
            "name": "Signal Leech",
            "faction_id": "blackwire_directorate",
            "tier": "normal",
            "current_hp": 16,
            "max_hp": 28,
            "block": 6,
            "strength": 0,
            "weak": 1,
            "vulnerable": 0,
            "current_intent": "lag_spike",
            "intent_value": 1,
            "intent_summary": "Add 1 Lag Card to the discard pile.",
            "intent_display": {
                "kind": "debuff",
                "damage_per_hit": 0,
                "hit_count": 0,
                "total_damage": 0,
                "block": 0,
                "buffs": [],
                "debuffs": ["Lag Card"],
                "icon_effects": [
                    {"icon_id": "intent_lag", "count": 1, "category": "enemy_intent", "label": "Lag Card"}
                ],
                "summon_count": 0,
                "tooltip": "Add 1 Lag Card to the discard pile.",
            },
            "statuses": {
                "fortified": 3,
                "regenerate": 2,
                "biomass": 1,
                "mutated": 1,
            },
        },
    ]
    showcase["combat"]["living_enemy_ids"] = [enemy["id"] for enemy in showcase["combat"]["enemies"]]
    _capture_screen(ui_manager, surface, showcase, output_path, captured_paths, force_name="combat_status_icons")


def _capture_combat_relic_tray_showcase(
    manager: StateManager,
    ui_manager: UIManager,
    surface: Any,
    snapshot: dict[str, Any],
    output_path: Path,
    captured_paths: dict[str, str],
) -> None:
    if snapshot.get("current_state") != "combat" or snapshot.get("combat") is None:
        return
    if "combat_relic_tray" in captured_paths:
        return

    ui_manager.combat_ui._reset_feedback_state()
    showcase = copy.deepcopy(snapshot)
    showcase["status_message"] = "Combat relic tray showcase."
    showcase["combat"]["turn_number"] = 4
    showcase["combat"]["turn_owner"] = "player"
    showcase["combat"]["active_bark"] = None
    showcase["combat"]["player"] = {
        **showcase["combat"]["player"],
        "current_hp": 49,
        "max_hp": 70,
        "block": 7,
        "energy": 4,
        "max_energy": 4,
        "draw_pile": 9,
        "discard_pile": 5,
        "exhaust_pile": 1,
    }
    active_modifiers = [
        manager.run_modifier_engine.create_modifier_record("carbon_weave", source="audit"),
        manager.run_modifier_engine.create_modifier_record("flash_cache", source="audit"),
        manager.run_modifier_engine.create_modifier_record("signal_router", source="audit"),
        manager.run_modifier_engine.create_modifier_record("overclock_relay", source="audit"),
        manager.run_modifier_engine.create_modifier_record("salvage_license", source="audit"),
    ]
    active_modifiers[-1]["remaining"] = 2
    active_modifiers[-1]["active_in_current_combat"] = True
    showcase["run_modifiers"] = manager.run_modifier_engine.snapshot(active_modifiers)
    showcase["combat"]["feedback_events"] = [
        {
            "type": "relic_triggered",
            "sequence": 1,
            "combo_index": 1,
            "relic_id": "carbon_weave",
            "relic_name": "Carbon Weave",
            "trigger_hook": "combat_start",
        },
        {
            "type": "relic_triggered",
            "sequence": 2,
            "combo_index": 2,
            "relic_id": "flash_cache",
            "relic_name": "Flash Cache",
            "trigger_hook": "turn_one",
        },
        {
            "type": "relic_triggered",
            "sequence": 3,
            "combo_index": 3,
            "relic_id": "signal_router",
            "relic_name": "Signal Router",
            "trigger_hook": "after_card_played",
            "card_id": "hemorrhage_01",
        },
    ]
    before_showcase = copy.deepcopy(showcase)
    before_showcase["combat"]["feedback_events"] = []
    ui_manager.apply_snapshot_feedback("visual_audit", before_showcase, showcase)
    _capture_screen(ui_manager, surface, showcase, output_path, captured_paths, force_name="combat_relic_tray")
    ui_manager.combat_ui._reset_feedback_state()


def _resolve_modifier_draft(manager: StateManager) -> None:
    draft_state = manager.get_state_snapshot()["modifier_draft"]
    preferred_ids = (
        "carbon_weave",
        "market_key",
        "signal_router",
        "overclock_relay",
        "flash_cache",
    )
    offers = draft_state["offers"]
    chosen_offer = next(
        (offer for preferred_id in preferred_ids for offer in offers if offer["id"] == preferred_id),
        offers[0],
    )
    manager.select_run_modifier_offer(chosen_offer["id"])
    manager.confirm_run_modifier_selection()


def _resolve_reward(manager: StateManager) -> None:
    while manager.current_state == "reward":
        reward_state = manager.get_state_snapshot()["reward"]
        unresolved_sections = [section for section in reward_state["sections"] if not section["resolved"]]
        if not unresolved_sections:
            manager.continue_from_reward()
            return

        progressed = False
        for section in unresolved_sections:
            options = section.get("options", [])
            if options:
                option = options[0]
                manager.select_reward_option(section["id"], option["option_id"])
                manager.confirm_reward_selection(section["id"])
                progressed = True
                continue
            if section.get("can_skip"):
                manager.skip_reward_section(section["id"])
                progressed = True

        if not progressed:
            raise ValueError("Could not auto-resolve reward sections for visual audit capture.")


def _resolve_shop(
    manager: StateManager,
    output_path: Path,
    ui_manager: UIManager,
    surface: Any,
    captured_paths: dict[str, str],
) -> None:
    snapshot = _presentation_snapshot(manager.get_state_snapshot())
    shop_state = snapshot["shop"]

    manager.open_shop_menu("purge")
    purge_targets = manager.get_state_snapshot()["shop"].get("purge_targets", [])
    if purge_targets:
        manager.select_shop_offer(f"purge_target:{purge_targets[0]['deck_index']}")
    if "shop_purge" not in captured_paths:
        _capture_screen(ui_manager, surface, _presentation_snapshot(manager.get_state_snapshot()), output_path, captured_paths, force_name="shop_purge")
    manager.open_shop_menu("main_menu")

    card_offers = [offer for offer in shop_state["inventory"] if offer["type"] == "card" and not offer["sold_out"]]
    if card_offers:
        manager.select_shop_offer(card_offers[0]["offer_id"])
        if "shop_selected" not in captured_paths:
            _capture_screen(ui_manager, surface, _presentation_snapshot(manager.get_state_snapshot()), output_path, captured_paths, force_name="shop_selected")

    if shop_state.get("can_reroll"):
        manager.reroll_shop_inventory()
        if "shop_reroll" not in captured_paths:
            _capture_screen(ui_manager, surface, _presentation_snapshot(manager.get_state_snapshot()), output_path, captured_paths, force_name="shop_reroll")

    post_reroll_state = manager.get_state_snapshot()["shop"]
    affordable_cards = [
        offer
        for offer in post_reroll_state["inventory"]
        if offer["type"] == "card" and not offer["sold_out"] and offer["price"] <= manager.player.credits
    ]
    if affordable_cards:
        manager.select_shop_offer(affordable_cards[0]["offer_id"])
        manager.confirm_shop_purchase()

    manager.leave_shop()


def _resolve_event(manager: StateManager) -> None:
    event_state = manager.get_state_snapshot()["event"]
    available_choices = [choice for choice in event_state["choices"] if choice["available"]]
    selected_choice = available_choices[0]
    manager.select_event_choice(selected_choice["id"])

    if selected_choice["choice_type"] == "purge":
        purge_targets = manager.get_state_snapshot()["event"]["purge_targets"]
        if purge_targets:
            manager.select_event_target(purge_targets[0]["option_id"])

    manager.confirm_event_choice()
    if manager.current_state == "event":
        manager.continue_from_event()


if __name__ == "__main__":
    report = capture_visual_audit()
    print(report["output_dir"])
