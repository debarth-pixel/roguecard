from __future__ import annotations

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

        if manager.current_state == "map":
            manager.select_map_node(_choose_map_node(snapshot, captured_paths))
            continue

        if manager.current_state == "combat":
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
        "show_help": False,
        "settings_open": False,
        "presentation_scale": 1.0,
        "ui_scale": DEFAULT_UI_SCALE,
        "screen_shake": False,
        "high_contrast": DEFAULT_HIGH_CONTRAST,
        "master_volume": 0.8,
        "music_volume": 0.65,
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
    action_budget = 0
    while manager.current_state == "combat":
        action_budget += 1
        if action_budget > 120:
            manager.player.current_hp = 0
            manager.combat_manager.combat_active = False
            manager._close_combat()
            return

        snapshot = manager.get_state_snapshot()
        if snapshot["combat"]["turn_owner"] != "player":
            manager.end_combat_turn()
            continue

        hand = snapshot["player_hand"]
        player = snapshot["player"]
        combat = snapshot["combat"]
        living_enemy_id = combat["living_enemy_ids"][0] if combat["living_enemy_ids"] else None

        candidates: list[tuple[int, int, dict[str, Any]]] = []
        for index, card in enumerate(hand):
            if card["cost"] > player["energy"]:
                continue
            score = 0
            effect_values = {effect["type"]: effect.get("value", 0) for effect in card["effects"]}
            score += effect_values.get("damage", 0) * 4
            score += effect_values.get("block", 0) * 2
            score += effect_values.get("draw", 0) * 3
            score += effect_values.get("energy", 0) * 5
            score += effect_values.get("heal", 0)
            candidates.append((score, index, card))

        if not candidates:
            manager.end_combat_turn()
            continue

        _, hand_index, chosen_card = max(candidates)
        target_id = living_enemy_id if any(effect["type"] == "damage" for effect in chosen_card["effects"]) else None
        manager.play_card_from_hand(hand_index, target_id=target_id)


def _resolve_reward(manager: StateManager) -> None:
    reward_state = manager.get_state_snapshot()["reward"]
    for section in reward_state["sections"]:
        if section["resolved"]:
            continue
        if section["type"] == "card_offer":
            option = section["options"][0]
            manager.select_reward_option(section["id"], option["option_id"])
            manager.confirm_reward_selection(section["id"])
        elif section["type"] == "purge_offer" and section["options"]:
            manager.skip_reward_section(section["id"])
        elif section.get("can_skip"):
            manager.skip_reward_section(section["id"])
    manager.continue_from_reward()


def _resolve_shop(
    manager: StateManager,
    output_path: Path,
    ui_manager: UIManager,
    surface: Any,
    captured_paths: dict[str, str],
) -> None:
    snapshot = _presentation_snapshot(manager.get_state_snapshot())
    shop_state = snapshot["shop"]

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
