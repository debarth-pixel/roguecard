from __future__ import annotations

import copy
import random
from typing import Any

from cards.card_library import CardLibrary
from cards.deck_manager import DeckManager
from combat.combat_manager import CombatManager
from config import (
    CARD_SHOP_PRICES,
    ELITE_COMBAT_CREDIT_REWARD,
    ENCOUNTER_ENEMY_IDS,
    MIN_STARTING_DECK_SIZE,
    PLAYER_STARTING_CREDITS,
    REGULAR_COMBAT_CREDIT_REWARD,
    REGULAR_REWARD_CARD_WEIGHT,
    REGULAR_REWARD_CHANCE,
    REGULAR_REWARD_PURGE_WEIGHT,
    REWARD_CARD_CHOICE_COUNT,
    REWARD_CARD_POOL_IDS,
    SAVE_FORMAT_VERSION,
    SHOP_CARD_OFFER_COUNT,
    SHOP_HEAL_AMOUNT,
    SHOP_HEAL_ENABLED,
    SHOP_HEAL_OFFER_ID,
    SHOP_HEAL_PRICE,
    SHOP_PURGE_OFFER_ID,
    SHOP_PURGE_PRICE,
    SHOP_REROLL_BASE_PRICE,
    SHOP_REROLL_PRICE_STEP,
    STARTER_DECK_IDS,
)
from core.event_library import EventLibrary
from core.run_modifier_engine import RunModifierEngine
from core.run_modifier_library import RunModifierLibrary
from entities.enemy_library import EnemyLibrary
from entities.player import Player
from map.map_generator import MapGenerator
from map.node import Node


class StateManager:
    def __init__(
        self,
        card_library: CardLibrary | None = None,
        enemy_library: EnemyLibrary | None = None,
        modifier_library: RunModifierLibrary | None = None,
        event_library: EventLibrary | None = None,
    ) -> None:
        self.card_library = card_library or CardLibrary()
        self.enemy_library = enemy_library or EnemyLibrary()
        self.run_modifier_library = modifier_library or RunModifierLibrary(card_library=self.card_library)
        self.run_modifier_engine = RunModifierEngine(self.run_modifier_library)
        self.event_library = event_library or EventLibrary(
            card_library=self.card_library,
            modifier_library=self.run_modifier_library,
        )
        self.current_state = "boot"
        self.status_message = "Initialize a run."
        self.run_seed: int | None = None

        self.player: Player | None = None
        self.map_graph: dict[str, Any] | None = None
        self.available_node_ids: list[str] = []
        self.visited_node_ids: list[str] = []
        self.selected_node_id: str | None = None
        self.combat_manager: CombatManager | None = None
        self.active_reward: dict[str, Any] | None = None
        self.active_shop: dict[str, Any] | None = None
        self.active_event: dict[str, Any] | None = None
        self.active_modifier_draft: dict[str, Any] | None = None
        self.run_modifiers: list[dict[str, Any]] = []
        self.modifier_runtime_flags: dict[str, Any] = self._default_modifier_runtime_flags()
        self.seen_event_ids: list[str] = []

    def start_new_run(self, seed: int | None = None) -> dict[str, Any]:
        self.run_seed = seed if seed is not None else random.randrange(1, 1_000_000)

        self.player = self._create_player(self.run_seed)
        self.map_graph = MapGenerator(rng=random.Random(self.run_seed)).generate_map()
        self.available_node_ids = list(self.map_graph["start_nodes"])
        self.visited_node_ids = []
        self.selected_node_id = None
        self.combat_manager = None
        self.active_reward = None
        self.active_shop = None
        self.active_event = None
        self.active_modifier_draft = self._generate_modifier_draft_state()
        self.run_modifiers = []
        self.modifier_runtime_flags = self._default_modifier_runtime_flags()
        self.seen_event_ids = []
        self.current_state = "modifier_draft"
        self.status_message = "Choose a run modifier before entering the city."
        return self.get_state_snapshot()

    def select_run_modifier_offer(self, modifier_id: str) -> dict[str, Any]:
        self._require_modifier_draft()
        if modifier_id not in self.active_modifier_draft["offer_ids"]:
            raise ValueError(f"Unknown modifier offer: {modifier_id}")

        self.active_modifier_draft["selected_offer_id"] = modifier_id
        modifier = self.run_modifier_library.get_modifier(modifier_id)
        self.status_message = f"Selected {modifier['name']}."
        return self.get_state_snapshot()

    def confirm_run_modifier_selection(self) -> dict[str, Any]:
        self._require_modifier_draft()
        modifier_id = self.active_modifier_draft.get("selected_offer_id")
        if modifier_id is None:
            raise ValueError("Select a modifier before confirming it.")

        modifier = self.run_modifier_library.get_modifier(modifier_id)
        self._acquire_run_modifier(modifier_id, source="starter_draft")
        self.active_modifier_draft = None
        self._enter_map_state(status_message=f"{modifier['name']} installed. Select the next node.")
        return self.get_state_snapshot()

    def select_map_node(self, node_id: str) -> dict[str, Any]:
        self._require_map()
        if node_id not in self.available_node_ids:
            raise ValueError(f"Node {node_id} is not currently available.")

        node = self.map_graph["nodes"][node_id]
        self.selected_node_id = node_id
        if node_id not in self.visited_node_ids:
            self.visited_node_ids.append(node_id)
        self.available_node_ids = list(node.next_nodes)
        self.active_reward = None
        self.active_shop = None
        self.active_event = None

        if node.node_type in ENCOUNTER_ENEMY_IDS:
            self._start_combat_for_node(node.node_type)
        elif node.node_type == "shop":
            self._start_shop_for_node()
        elif node.node_type == "event":
            self._start_event_for_node()
        else:
            raise ValueError(f"Unsupported selectable node type: {node.node_type}")

        return self.get_state_snapshot()

    def play_card_from_hand(self, hand_index: int, target_id: str | None = None) -> dict[str, Any]:
        self._require_combat()

        hand = self.player.deck_manager.hand
        if hand_index < 0 or hand_index >= len(hand):
            raise IndexError("Requested hand index is out of range.")

        card = hand[hand_index]
        target = self.combat_manager.get_enemy(target_id) if target_id else None
        self.combat_manager.resolve_action({"card": card, "target": target})

        if not self.combat_manager.combat_active:
            self._close_combat()

        return self.get_state_snapshot()

    def end_combat_turn(self) -> dict[str, Any]:
        self._require_combat()
        self.combat_manager.end_turn()

        if not self.combat_manager.combat_active:
            self._close_combat()

        return self.get_state_snapshot()

    def select_reward_option(self, section: str, option_id: str) -> dict[str, Any]:
        self._require_reward()
        section_state = self._reward_section(section)
        if section_state["resolved"]:
            raise ValueError("That reward section has already been resolved.")

        option = self._reward_option(section_state, option_id)
        section_state["selected_option_id"] = option_id
        self.status_message = f"Selected {option['label']}."
        return self.get_state_snapshot()

    def confirm_reward_selection(self, section: str) -> dict[str, Any]:
        self._require_reward()
        section_state = self._reward_section(section)
        if section_state["resolved"]:
            raise ValueError("That reward section has already been resolved.")

        option_id = section_state.get("selected_option_id")
        if option_id is None:
            raise ValueError("Select a reward option before confirming it.")

        option = self._reward_option(section_state, option_id)
        if section_state["type"] == "card_offer":
            card = self.card_library.create_card(option["card_id"])
            self.player.deck_manager.add_to_starting_deck(card)
            self.player.deck_manager.normalize_overworld_deck()
            summary = f"Added {option['card']['name']} to the deck."
        elif section_state["type"] == "purge_offer":
            removed_card = self.player.deck_manager.remove_from_starting_deck(option["deck_index"])
            self.player.deck_manager.normalize_overworld_deck()
            summary = f"Removed {removed_card.name} from the deck."
        else:
            raise ValueError(f"Unsupported reward section type: {section_state['type']}")

        section_state["resolved"] = True
        section_state["resolution"] = {"type": "claimed", "option_id": option_id, "summary": summary}
        self.status_message = summary
        return self.get_state_snapshot()

    def skip_reward_section(self, section: str) -> dict[str, Any]:
        self._require_reward()
        section_state = self._reward_section(section)
        if section_state["resolved"]:
            raise ValueError("That reward section has already been resolved.")
        if not section_state.get("can_skip", True):
            raise ValueError("That reward section cannot be skipped.")

        section_state["resolved"] = True
        section_state["selected_option_id"] = None
        section_state["resolution"] = {
            "type": "skipped",
            "summary": f"Skipped {section_state['title'].lower()}.",
        }
        self.status_message = section_state["resolution"]["summary"]
        return self.get_state_snapshot()

    def continue_from_reward(self) -> dict[str, Any]:
        self._require_reward()
        if not self._all_reward_sections_resolved():
            raise ValueError("Resolve or skip every reward section before continuing.")

        self.active_reward = None
        self._enter_map_state(status_message="Rewards resolved. Select the next node.")
        return self.get_state_snapshot()

    def select_shop_offer(self, offer_id: str) -> dict[str, Any]:
        self._require_shop()
        if offer_id.startswith("purge_target:"):
            offer = self._selected_shop_offer()
            if offer is None or offer["offer_id"] != SHOP_PURGE_OFFER_ID:
                raise ValueError("Select the purge service before choosing a card to remove.")
            deck_index = self._purge_target_index(offer_id)
            self._validate_purge_target(deck_index)
            self.active_shop["selected_purge_index"] = deck_index
            card = self.player.deck_manager.starting_deck[deck_index]
            self.status_message = f"Selected {card.name} as the purge target."
            return self.get_state_snapshot()

        offer = self._shop_offer(offer_id)
        if offer.get("sold_out"):
            raise ValueError("That shop offer has already been purchased.")

        self.active_shop["selected_offer_id"] = offer_id
        if offer["type"] != "purge":
            self.active_shop["selected_purge_index"] = None
        self.status_message = f"Selected {offer['label']}."
        return self.get_state_snapshot()

    def confirm_shop_purchase(self) -> dict[str, Any]:
        self._require_shop()
        self._refresh_shop_prices()
        offer = self._selected_shop_offer()
        if offer is None:
            raise ValueError("Select a shop offer before confirming a purchase.")
        can_purchase, disabled_reason = self._shop_offer_purchase_availability(offer)
        if not can_purchase:
            raise ValueError(disabled_reason or "That shop purchase is unavailable.")

        price = offer["price"]
        self.player.spend_credits(price)
        if offer["type"] == "card":
            card = self.card_library.create_card(offer["card_id"])
            self.player.deck_manager.add_to_starting_deck(card)
            self.player.deck_manager.normalize_overworld_deck()
            summary = f"Purchased {offer['card']['name']} for {price} credits."
            self._mark_shop_modifier_use("card")
        elif offer["type"] == "purge":
            if len(self.player.deck_manager.starting_deck) <= MIN_STARTING_DECK_SIZE:
                self.player.gain_credits(price)
                raise ValueError("The deck is too small to purge any further.")
            purge_index = self.active_shop.get("selected_purge_index")
            if purge_index is None:
                self.player.gain_credits(price)
                raise ValueError("Select a card to purge before confirming the service.")
            removed_card = self.player.deck_manager.remove_from_starting_deck(purge_index)
            self.player.deck_manager.normalize_overworld_deck()
            summary = f"Purged {removed_card.name} for {price} credits."
            self.active_shop["selected_purge_index"] = None
            self._mark_shop_modifier_use("purge")
        elif offer["type"] == "heal":
            healed = self.player.heal(offer["heal_amount"])
            summary = f"Recovered {healed} HP for {price} credits."
        else:
            self.player.gain_credits(price)
            raise ValueError(f"Unsupported shop offer type: {offer['type']}")

        if offer["type"] != "heal":
            offer["sold_out"] = True
        self.active_shop["selected_offer_id"] = None
        self._refresh_shop_prices()
        self.status_message = summary
        return self.get_state_snapshot()

    def reroll_shop_inventory(self) -> dict[str, Any]:
        self._require_shop()
        can_reroll, disabled_reason = self._shop_reroll_availability()
        if not can_reroll:
            raise ValueError(disabled_reason or "That shop cannot reroll right now.")

        reroll_price = self._shop_reroll_price()
        self.player.spend_credits(reroll_price)
        self._apply_shop_reroll()
        self._mark_shop_modifier_use("reroll")
        self.active_shop["selected_offer_id"] = None
        self.active_shop["selected_purge_index"] = None
        self.status_message = f"Rerolled the shop for {reroll_price} credits."
        return self.get_state_snapshot()

    def leave_shop(self) -> dict[str, Any]:
        self._require_shop()
        self.active_shop = None
        self._enter_map_state(status_message="Shop visit complete. Select the next node.")
        return self.get_state_snapshot()

    def select_event_choice(self, choice_id: str) -> dict[str, Any]:
        self._require_event()
        if self.active_event["resolved"]:
            raise ValueError("This event has already been resolved.")

        event_definition = self.event_library.get_event(self.active_event["event_id"])
        choice = self._event_choice_definition(event_definition, choice_id)
        available, disabled_reason = self._event_choice_availability(choice)
        if not available:
            raise ValueError(disabled_reason)

        self.active_event["selected_choice_id"] = choice_id
        if choice["choice_type"] != "purge":
            self.active_event["selected_target_id"] = None
        self.status_message = f"Selected {choice['label']}."
        return self.get_state_snapshot()

    def select_event_target(self, target_id: str) -> dict[str, Any]:
        self._require_event()
        if self.active_event["resolved"]:
            raise ValueError("This event has already been resolved.")

        event_definition = self.event_library.get_event(self.active_event["event_id"])
        selected_choice = self._selected_event_choice_definition(event_definition)
        if selected_choice is None or selected_choice["choice_type"] != "purge":
            raise ValueError("Select a purge event choice before choosing a target card.")

        target_index = self._event_target_index(target_id)
        self._validate_purge_target(target_index)
        self.active_event["selected_target_id"] = target_id
        selected_card = self.player.deck_manager.starting_deck[target_index]
        self.status_message = f"Selected {selected_card.name} for removal."
        return self.get_state_snapshot()

    def confirm_event_choice(self) -> dict[str, Any]:
        self._require_event()
        if self.active_event["resolved"]:
            raise ValueError("This event has already been resolved.")

        event_definition = self.event_library.get_event(self.active_event["event_id"])
        choice = self._selected_event_choice_definition(event_definition)
        if choice is None:
            raise ValueError("Select an event choice before confirming it.")

        available, disabled_reason = self._event_choice_availability(choice)
        if not available:
            raise ValueError(disabled_reason)

        target_id = self.active_event.get("selected_target_id")
        if choice["choice_type"] == "purge" and target_id is None:
            raise ValueError("Choose a deck card target before confirming this event choice.")

        resolved_outcome_id: str | None = None
        if choice["choice_type"] == "risk":
            outcome = self._event_outcome(choice)
            resolved_outcome_id = outcome["id"]
            resolution_summary = outcome["summary"]
            resolution_details = self._apply_event_effects(outcome["effects"], target_id=target_id)
        else:
            resolution_details = self._apply_event_effects(choice["effects"], target_id=target_id)
            resolution_summary = self._event_resolution_summary(choice, resolution_details)

        if self.player.is_alive():
            event_value_details = self._apply_post_event_modifier_effects()
            if event_value_details:
                resolution_details.extend(event_value_details)
                resolution_summary = self._compose_status_message(
                    resolution_summary,
                    " ".join(event_value_details),
                )

        self.active_event["resolved"] = True
        self.active_event["resolved_choice_id"] = choice["id"]
        self.active_event["resolved_outcome_id"] = resolved_outcome_id
        self.active_event["resolution_summary"] = resolution_summary
        self.active_event["resolution_details"] = list(resolution_details)
        self.status_message = resolution_summary

        if not self.player.is_alive():
            self.active_event = None
            self.current_state = "game_over"
            self.status_message = f"{resolution_summary} Run failed."

        return self.get_state_snapshot()

    def continue_from_event(self) -> dict[str, Any]:
        self._require_event()
        if not self.active_event["resolved"]:
            raise ValueError("Resolve the event before continuing.")

        self.active_event = None
        self._enter_map_state(status_message="Event resolved. Select the next node.")
        return self.get_state_snapshot()

    def get_state_snapshot(self) -> dict[str, Any]:
        return {
            "current_state": self.current_state,
            "status_message": self.status_message,
            "run_seed": self.run_seed,
            "modifier_draft": self._snapshot_modifier_draft(),
            "run_modifiers": self.run_modifier_engine.snapshot(self.run_modifiers),
            "map": self._snapshot_map(),
            "combat": self.combat_manager.get_state() if self.combat_manager is not None else None,
            "event": self._snapshot_event(),
            "reward": self._snapshot_reward(),
            "shop": self._snapshot_shop(),
            "player": self.player.get_state() if self.player is not None else None,
            "player_hand": self._snapshot_hand(),
        }

    def build_save_data(self) -> dict[str, Any]:
        if self.player is None or self.player.deck_manager is None or self.run_seed is None:
            raise ValueError("Cannot build save data before a run has been initialized.")

        return {
            "save_format_version": SAVE_FORMAT_VERSION,
            "current_state": self.current_state,
            "status_message": self.status_message,
            "run_seed": self.run_seed,
            "player": self._serialize_player(),
            "deck": self._serialize_deck(self.player.deck_manager),
            "map": self._serialize_map(),
            "combat": self._serialize_combat(),
            "event": self._serialize_event(),
            "reward": self._serialize_reward(),
            "shop": self._serialize_shop(),
            "modifier_draft": self._serialize_modifier_draft(),
            "run_modifiers": copy.deepcopy(self.run_modifiers),
            "modifier_runtime_flags": copy.deepcopy(self.modifier_runtime_flags),
            "seen_event_ids": list(self.seen_event_ids),
        }

    def restore_save_data(self, save_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(save_data, dict):
            raise ValueError("Save data must be a dictionary.")

        save_version = save_data.get("save_format_version")
        if save_version not in {2, 3, 4, 5, 6}:
            raise ValueError(f"Unsupported save format version: {save_version}")

        run_seed = save_data.get("run_seed")
        current_state = save_data.get("current_state")
        status_message = save_data.get("status_message")
        player_data = save_data.get("player")
        deck_data = save_data.get("deck")
        map_data = save_data.get("map")
        combat_data = save_data.get("combat")
        event_data = save_data.get("event") if save_version >= 5 else None
        reward_data = save_data.get("reward") if save_version >= 3 else None
        shop_data = save_data.get("shop") if save_version >= 4 else None
        seen_event_ids = save_data.get("seen_event_ids") if save_version >= 5 else []
        modifier_draft_data = save_data.get("modifier_draft") if save_version >= 6 else None
        run_modifiers_data = save_data.get("run_modifiers") if save_version >= 6 else []
        modifier_runtime_flags = save_data.get("modifier_runtime_flags") if save_version >= 6 else {}

        allowed_states = {"map", "combat", "victory", "game_over"}
        if save_version >= 3:
            allowed_states.add("reward")
        if save_version >= 4:
            allowed_states.add("shop")
        if save_version >= 5:
            allowed_states.add("event")
        if save_version >= 6:
            allowed_states.add("modifier_draft")

        if not isinstance(run_seed, int):
            raise ValueError("Save data is missing a valid run_seed.")
        if current_state not in allowed_states:
            raise ValueError(f"Save data has an unsupported current_state: {current_state}")
        if not isinstance(status_message, str) or not status_message:
            raise ValueError("Save data must include a non-empty status_message.")

        self.run_seed = run_seed
        self.player = self._restore_player(player_data, deck_data, run_seed, save_version)
        self.map_graph = self._restore_map(map_data)
        self.status_message = status_message
        self.current_state = current_state
        self.available_node_ids = list(map_data["available_node_ids"])
        self.visited_node_ids = list(map_data["visited_node_ids"])
        self.selected_node_id = map_data["selected_node_id"]
        self.combat_manager = None
        self.active_reward = None
        self.active_shop = None
        self.active_event = None
        self.active_modifier_draft = None
        self.run_modifiers = self._restore_run_modifiers(run_modifiers_data)
        self.modifier_runtime_flags = self._restore_modifier_runtime_flags(modifier_runtime_flags)
        self.seen_event_ids = self._restore_seen_event_ids(seen_event_ids)

        if current_state == "combat":
            self.combat_manager = self._restore_combat(combat_data)
        elif current_state == "event":
            self.active_event = self._restore_event(event_data)
        elif current_state == "reward":
            self.active_reward = self._restore_reward(reward_data)
        elif current_state == "shop":
            self.active_shop = self._restore_shop(shop_data)
        elif current_state == "modifier_draft":
            self.active_modifier_draft = self._restore_modifier_draft(modifier_draft_data)

        return self.get_state_snapshot()

    def _start_combat_for_node(self, node_type: str) -> None:
        if node_type not in ENCOUNTER_ENEMY_IDS:
            raise ValueError(f"Encounter node type is not mapped for combat: {node_type}")
        enemy_id = ENCOUNTER_ENEMY_IDS[node_type]
        enemy = self.enemy_library.create_enemy(enemy_id)
        self.combat_manager = CombatManager(player=self.player, enemies=[enemy])
        self.combat_manager.start_combat()
        self._apply_combat_modifier_effects("combat_start")
        self._apply_combat_modifier_effects("turn_one")
        self.current_state = "combat"
        self.status_message = f"Entered {node_type} encounter. Play cards or end your turn."

    def _start_shop_for_node(self) -> None:
        self._require_player()
        self.player.deck_manager.normalize_overworld_deck()
        self.active_shop = self._generate_shop_state()
        self.current_state = "shop"
        self.status_message = f"Shop open. Spend, reroll, or leave with {self.player.credits} credits."

    def _start_event_for_node(self) -> None:
        self._require_player()
        self.player.deck_manager.normalize_overworld_deck()
        self.active_event = self._generate_event_state()
        self.current_state = "event"
        self.status_message = f"{self.active_event['title']}: choose how to respond."

    def _close_combat(self) -> None:
        if self.player is None or self.combat_manager is None:
            return

        encounter_type = self._current_node_type()
        self.combat_manager = None

        if not self.player.is_alive():
            self.active_reward = None
            self.current_state = "game_over"
            self.status_message = "Run failed."
            return

        self.player.deck_manager.normalize_overworld_deck()
        if encounter_type == "boss":
            self.active_reward = None
            self.current_state = "victory"
            self.status_message = "Run completed."
            return

        credits_granted = self._credits_for_encounter(encounter_type)
        if credits_granted > 0:
            self.player.gain_credits(credits_granted)

        modifier_summary = self._apply_post_victory_modifier_effects(encounter_type)

        reward_state = self._generate_reward_state(encounter_type, credits_granted)
        if reward_state is None:
            self.active_reward = None
            self._enter_map_state(
                status_message=self._compose_status_message(
                    f"Encounter cleared. +{credits_granted} credits. Select the next node.",
                    modifier_summary,
                )
            )
            return

        self.active_reward = reward_state
        self.current_state = "reward"
        self.status_message = self._compose_status_message(reward_state["intro_message"], modifier_summary)

    def _snapshot_map(self) -> dict[str, Any] | None:
        if self.map_graph is None:
            return None

        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.map_graph["nodes"].items()},
            "start_nodes": list(self.map_graph["start_nodes"]),
            "boss_node_id": self.map_graph["boss_node_id"],
            "available_node_ids": list(self.available_node_ids),
            "visited_node_ids": list(self.visited_node_ids),
            "selected_node_id": self.selected_node_id,
        }

    def _snapshot_modifier_draft(self) -> dict[str, Any] | None:
        if self.active_modifier_draft is None:
            return None

        offers = []
        for modifier_id in self.active_modifier_draft["offer_ids"]:
            modifier = self.run_modifier_library.get_modifier(modifier_id)
            offers.append(
                {
                    "id": modifier["id"],
                    "name": modifier["name"],
                    "kind": modifier["kind"],
                    "description": modifier["description"],
                    "downside": modifier.get("downside"),
                    "selected": self.active_modifier_draft.get("selected_offer_id") == modifier_id,
                }
            )

        return {
            "offers": offers,
            "selected_offer_id": self.active_modifier_draft.get("selected_offer_id"),
            "can_confirm": self.active_modifier_draft.get("selected_offer_id") is not None,
        }

    def _snapshot_event(self) -> dict[str, Any] | None:
        if self.active_event is None:
            return None

        event_definition = self.event_library.get_event(self.active_event["event_id"])
        choices = []
        for choice in event_definition["choices"]:
            available, disabled_reason = self._event_choice_availability(choice)
            choices.append(
                {
                    "id": choice["id"],
                    "label": choice["label"],
                    "description": choice["description"],
                    "choice_type": choice["choice_type"],
                    "available": available and not self.active_event["resolved"],
                    "disabled_reason": disabled_reason,
                    "selected": self.active_event.get("selected_choice_id") == choice["id"],
                }
            )

        return {
            "event_id": event_definition["id"],
            "title": event_definition["title"],
            "body": event_definition["body"],
            "choices": choices,
            "selected_choice_id": self.active_event.get("selected_choice_id"),
            "selected_choice_type": self._selected_event_choice_type(event_definition),
            "selected_target_id": self.active_event.get("selected_target_id"),
            "purge_targets": self._event_purge_targets(),
            "resolved": self.active_event["resolved"],
            "resolved_choice_id": self.active_event.get("resolved_choice_id"),
            "resolved_outcome_id": self.active_event.get("resolved_outcome_id"),
            "resolution_summary": self.active_event.get("resolution_summary"),
            "resolution_details": list(self.active_event.get("resolution_details", [])),
            "deck_size": len(self.player.deck_manager.starting_deck),
            "can_continue": self.active_event["resolved"],
        }

    def _snapshot_reward(self) -> dict[str, Any] | None:
        if self.active_reward is None:
            return None

        return {
            "encounter_type": self.active_reward["encounter_type"],
            "credits_granted": self.active_reward["credits_granted"],
            "sections": [
                {
                    **copy.deepcopy(self.active_reward["sections"][section_id]),
                    "id": section_id,
                }
                for section_id in self.active_reward["section_order"]
            ],
            "can_continue": self._all_reward_sections_resolved(),
            "deck_size": len(self.player.deck_manager.starting_deck),
        }

    def _snapshot_shop(self) -> dict[str, Any] | None:
        if self.active_shop is None:
            return None

        self._refresh_shop_prices()
        can_reroll, reroll_disabled_reason = self._shop_reroll_availability()
        return {
            "inventory": copy.deepcopy(self.active_shop["inventory"]),
            "selected_offer_id": self.active_shop.get("selected_offer_id"),
            "selected_purge_index": self.active_shop.get("selected_purge_index"),
            "reroll_count": self.active_shop.get("reroll_count", 0),
            "reroll_price": self._shop_reroll_price(),
            "can_reroll": can_reroll,
            "reroll_disabled_reason": reroll_disabled_reason,
            "purge_targets": self._shop_purge_targets(),
            "heal_service_enabled": SHOP_HEAL_ENABLED,
            "can_leave": True,
        }

    def _require_map(self) -> None:
        if self.map_graph is None or self.current_state != "map":
            raise ValueError("Map selection is only available while in the map state.")

    def _require_combat(self) -> None:
        if self.player is None or self.player.deck_manager is None or self.combat_manager is None:
            raise ValueError("Combat action requested without an active combat manager.")
        if self.current_state != "combat":
            raise ValueError("Combat actions are only available during combat.")

    def _require_event(self) -> None:
        if self.player is None or self.player.deck_manager is None or self.active_event is None:
            raise ValueError("Event actions require an active event state.")
        if self.current_state != "event":
            raise ValueError("Event actions are only available during the event state.")

    def _require_modifier_draft(self) -> None:
        if self.player is None or self.player.deck_manager is None or self.active_modifier_draft is None:
            raise ValueError("Modifier draft actions require an active draft state.")
        if self.current_state != "modifier_draft":
            raise ValueError("Modifier draft actions are only available during the draft state.")

    def _require_reward(self) -> None:
        if self.player is None or self.player.deck_manager is None or self.active_reward is None:
            raise ValueError("Reward actions require an active reward state.")
        if self.current_state != "reward":
            raise ValueError("Reward actions are only available during the reward state.")

    def _require_shop(self) -> None:
        if self.player is None or self.player.deck_manager is None or self.active_shop is None:
            raise ValueError("Shop actions require an active shop state.")
        if self.current_state != "shop":
            raise ValueError("Shop actions are only available during the shop state.")

    def _require_player(self) -> None:
        if self.player is None or self.player.deck_manager is None:
            raise ValueError("Run actions require an initialized player and deck.")

    def _event_choice_definition(self, event_definition: dict[str, Any], choice_id: str) -> dict[str, Any]:
        for choice in event_definition["choices"]:
            if choice["id"] == choice_id:
                return choice
        raise ValueError(f"Unknown event choice: {choice_id}")

    def _selected_event_choice_definition(
        self,
        event_definition: dict[str, Any],
    ) -> dict[str, Any] | None:
        choice_id = self.active_event.get("selected_choice_id")
        if choice_id is None:
            return None
        return self._event_choice_definition(event_definition, choice_id)

    def _selected_event_choice_type(self, event_definition: dict[str, Any]) -> str | None:
        selected_choice = self._selected_event_choice_definition(event_definition)
        return None if selected_choice is None else selected_choice["choice_type"]

    def _event_choice_availability(self, choice: dict[str, Any]) -> tuple[bool, str | None]:
        requirements = choice.get("requirements", {})
        credits_at_least = requirements.get("credits_at_least")
        if credits_at_least is not None and self.player.credits < credits_at_least:
            return False, f"Requires at least {credits_at_least} credits."

        missing_hp_at_least = requirements.get("missing_hp_at_least")
        missing_hp = self.player.max_hp - self.player.current_hp
        if missing_hp_at_least is not None and missing_hp < missing_hp_at_least:
            return False, f"Requires at least {missing_hp_at_least} missing HP."

        deck_size_at_least = requirements.get("deck_size_at_least")
        deck_size = len(self.player.deck_manager.starting_deck)
        if deck_size_at_least is not None and deck_size < deck_size_at_least:
            return False, f"Requires a deck of at least {deck_size_at_least} cards."

        for effect in choice.get("effects", []):
            if effect["type"] != "gain_modifier":
                continue
            modifier = self.run_modifier_library.get_modifier(effect["modifier_id"])
            if self.run_modifier_engine.has_modifier(self.run_modifiers, effect["modifier_id"]):
                return False, f"Already installed: {modifier['name']}."

        return True, None

    def _event_target_index(self, target_id: str) -> int:
        _, _, raw_index = target_id.partition(":")
        try:
            return int(raw_index)
        except ValueError as error:
            raise ValueError(f"Invalid event target identifier: {target_id}") from error

    def _event_purge_targets(self) -> list[dict[str, Any]]:
        if self.player is None or self.player.deck_manager is None:
            return []
        return [
            {
                "option_id": f"purge_target:{index}",
                "deck_index": index,
                "card": card.to_dict(),
                "selected": self.active_event is not None
                and self.active_event.get("selected_target_id") == f"purge_target:{index}",
            }
            for index, card in enumerate(self.player.deck_manager.starting_deck)
        ]

    def _event_resolution_summary(
        self,
        choice: dict[str, Any],
        resolution_details: list[str],
    ) -> str:
        if resolution_details:
            return " ".join(resolution_details)
        if choice["choice_type"] == "purge":
            return "Card purged from the deck."
        return "You move on without changing the run."

    def _event_outcome(self, choice: dict[str, Any]) -> dict[str, Any]:
        rng = self._state_rng(f"event_outcome:{self.active_event['event_id']}:{choice['id']}")
        total_weight = sum(outcome["weight"] for outcome in choice["outcomes"])
        roll = rng.randint(1, total_weight)
        running_total = 0
        for outcome in choice["outcomes"]:
            running_total += outcome["weight"]
            if roll <= running_total:
                return outcome
        return choice["outcomes"][-1]

    def _apply_event_effects(
        self,
        effects: list[dict[str, Any]],
        target_id: str | None = None,
    ) -> list[str]:
        details: list[str] = []
        deck_changed = False

        for effect in effects:
            effect_type = effect["type"]
            if effect_type == "gain_credits":
                gained = self.player.gain_credits(effect["value"])
                details.append(f"Gained {gained} credits.")
            elif effect_type == "lose_credits":
                lost = min(effect["value"], self.player.credits)
                if lost > 0:
                    self.player.spend_credits(lost)
                details.append(f"Lost {lost} credits.")
            elif effect_type == "gain_card":
                card = self.card_library.create_card(effect["card_id"])
                self.player.deck_manager.add_to_starting_deck(card)
                deck_changed = True
                details.append(f"Gained {card.name}.")
            elif effect_type == "gain_modifier":
                modifier_details = self._acquire_run_modifier(
                    effect["modifier_id"],
                    source="event",
                    source_detail=self.active_event["event_id"] if self.active_event is not None else None,
                )
                details.extend(modifier_details)
            elif effect_type == "heal":
                healed = self.player.heal(effect["value"])
                details.append(f"Recovered {healed} HP.")
            elif effect_type == "damage":
                damage = self.player.take_damage(effect["value"])
                details.append(f"Took {damage} damage.")
            elif effect_type == "purge_card":
                if target_id is None:
                    raise ValueError("This event effect requires a selected deck target.")
                target_index = self._event_target_index(target_id)
                self._validate_purge_target(target_index)
                removed_card = self.player.deck_manager.remove_from_starting_deck(target_index)
                deck_changed = True
                details.append(f"Purged {removed_card.name}.")
            else:
                raise ValueError(f"Unsupported event effect type: {effect_type}")

        if deck_changed:
            self.player.deck_manager.normalize_overworld_deck()

        return details

    def _reward_section(self, section: str) -> dict[str, Any]:
        if section not in self.active_reward["sections"]:
            raise ValueError(f"Unknown reward section: {section}")
        return self.active_reward["sections"][section]

    def _reward_option(self, section_state: dict[str, Any], option_id: str) -> dict[str, Any]:
        for option in section_state["options"]:
            if option["option_id"] == option_id:
                return option
        raise ValueError(f"Unknown reward option: {option_id}")

    def _all_reward_sections_resolved(self) -> bool:
        return all(
            self.active_reward["sections"][section_id]["resolved"]
            for section_id in self.active_reward["section_order"]
        )

    def _shop_offer(self, offer_id: str) -> dict[str, Any]:
        for offer in self.active_shop["inventory"]:
            if offer["offer_id"] == offer_id:
                return offer
        raise ValueError(f"Unknown shop offer: {offer_id}")

    def _selected_shop_offer(self) -> dict[str, Any] | None:
        offer_id = self.active_shop.get("selected_offer_id")
        if offer_id is None:
            return None
        return self._shop_offer(offer_id)

    def _purge_target_index(self, offer_id: str) -> int:
        _, _, raw_index = offer_id.partition(":")
        try:
            return int(raw_index)
        except ValueError as error:
            raise ValueError(f"Invalid purge target identifier: {offer_id}") from error

    def _validate_purge_target(self, deck_index: int) -> None:
        deck = self.player.deck_manager.starting_deck
        if len(deck) <= MIN_STARTING_DECK_SIZE:
            raise ValueError("The deck is too small to purge any further.")
        if deck_index < 0 or deck_index >= len(deck):
            raise ValueError("That purge target is out of range.")

    def _snapshot_hand(self) -> list[dict[str, Any]]:
        if self.player is None or self.player.deck_manager is None:
            return []
        return [card.to_dict() for card in self.player.deck_manager.hand]

    def _current_node_type(self) -> str | None:
        if self.map_graph is None or self.selected_node_id is None:
            return None
        node = self.map_graph["nodes"].get(self.selected_node_id)
        return None if node is None else node.node_type

    def _create_player(self, seed: int) -> Player:
        starter_cards = [self.card_library.create_card(card_id) for card_id in STARTER_DECK_IDS]
        deck_manager = DeckManager(starter_cards, rng=random.Random(seed))
        player = Player(credits=PLAYER_STARTING_CREDITS)
        player.attach_deck(deck_manager)
        return player

    def _generate_modifier_draft_state(self) -> dict[str, Any]:
        rng = self._state_rng("modifier_draft")
        return {
            "offer_ids": self.run_modifier_engine.generate_starter_offers(rng),
            "selected_offer_id": None,
        }

    def _default_modifier_runtime_flags(self) -> dict[str, Any]:
        return {
            "clean_slate_used": False,
            "ghost_warranty_used_shops": [],
            "debt_spike_used_shops": [],
        }

    def _acquire_run_modifier(
        self,
        modifier_id: str,
        source: str,
        source_detail: str | None = None,
    ) -> list[str]:
        if self.run_modifier_engine.has_modifier(self.run_modifiers, modifier_id):
            modifier = self.run_modifier_library.get_modifier(modifier_id)
            raise ValueError(f"{modifier['name']} is already active for this run.")

        modifier = self.run_modifier_library.get_modifier(modifier_id)
        self.run_modifiers.append(
            {
                "id": modifier_id,
                "source": source,
                "source_detail": source_detail,
            }
        )

        details = [f"Installed {modifier['name']}."]
        for effect in modifier.get("hooks", {}).get("on_acquire", []):
            details.extend(self._apply_modifier_effect(effect))
        return details

    def _apply_modifier_effect(self, effect: dict[str, Any]) -> list[str]:
        effect_type = effect["type"]
        if effect_type == "gain_credits":
            gained = self.player.gain_credits(effect["value"])
            return [f"Gained {gained} credits."]
        if effect_type == "modify_max_hp":
            delta = self.player.adjust_max_hp(effect["value"])
            direction = "max HP" if delta >= 0 else "max HP"
            return [f"{'Gained' if delta >= 0 else 'Lost'} {abs(delta)} {direction}."]
        if effect_type == "modify_healing_multiplier_percent":
            multiplier = self.player.adjust_healing_multiplier(effect["value"])
            return [f"Healing efficiency set to {int(round(multiplier * 100))}%."]
        if effect_type == "add_card":
            card = self.card_library.create_card(effect["card_id"])
            self.player.deck_manager.add_to_starting_deck(card)
            self.player.deck_manager.normalize_overworld_deck()
            return [f"Added {card.name} to the deck."]
        if effect_type == "gain_block":
            gained = self.player.gain_block(effect["value"])
            return [f"Gained {gained} Block."]
        if effect_type == "draw_cards":
            drawn = self.player.deck_manager.draw_cards(effect["value"])
            return [f"Drew {len(drawn)} card{'s' if len(drawn) != 1 else ''}."]
        if effect_type == "gain_energy":
            self.player.energy += effect["value"]
            return [f"Gained {effect['value']} Energy."]
        if effect_type == "heal":
            healed = self.player.heal(effect["value"])
            return [f"Recovered {healed} HP."]
        return []

    def _apply_combat_modifier_effects(self, hook_name: str) -> None:
        for effect in self.run_modifier_engine.get_effects(self.run_modifiers, hook_name):
            self._apply_modifier_effect(effect)

    def _apply_post_victory_modifier_effects(self, encounter_type: str | None) -> str | None:
        summaries: list[str] = []
        for effect in self.run_modifier_engine.filter_post_victory_effects(self.run_modifiers, encounter_type):
            summaries.extend(self._apply_modifier_effect(effect))
        return None if not summaries else " ".join(summaries)

    def _apply_post_event_modifier_effects(self) -> list[str]:
        bonus_heal = self.run_modifier_engine.event_post_resolution_heal(self.run_modifiers)
        if bonus_heal <= 0:
            return []
        healed = self.player.heal(bonus_heal)
        if healed <= 0:
            return []
        return [f"Street effects restored {healed} HP."]

    def _shop_price(
        self,
        offer_type: str,
        base_price: int,
        shop_node_id: str | None,
    ) -> int:
        return self.run_modifier_engine.price_for_offer(
            base_price=base_price,
            offer_type=offer_type,
            active_modifiers=self.run_modifiers,
            runtime_flags=self.modifier_runtime_flags,
            shop_node_id=shop_node_id,
        )

    def _mark_shop_modifier_use(self, offer_type: str) -> None:
        shop_node_id = None if self.active_shop is None else self.active_shop.get("shop_node_id")
        if offer_type == "purge" and self.run_modifier_engine.has_modifier(self.run_modifiers, "clean_slate"):
            self.modifier_runtime_flags["clean_slate_used"] = True
        elif offer_type == "reroll" and self.run_modifier_engine.has_modifier(self.run_modifiers, "ghost_warranty"):
            used_shops = set(self.modifier_runtime_flags.get("ghost_warranty_used_shops", []))
            if shop_node_id is not None:
                used_shops.add(shop_node_id)
            self.modifier_runtime_flags["ghost_warranty_used_shops"] = sorted(used_shops)
        elif offer_type == "card" and self.run_modifier_engine.has_modifier(self.run_modifiers, "debt_spike"):
            used_shops = set(self.modifier_runtime_flags.get("debt_spike_used_shops", []))
            if shop_node_id is not None:
                used_shops.add(shop_node_id)
            self.modifier_runtime_flags["debt_spike_used_shops"] = sorted(used_shops)

    def _refresh_shop_prices(self, shop_state: dict[str, Any] | None = None) -> None:
        target_shop = self.active_shop if shop_state is None else shop_state
        if target_shop is None:
            return
        shop_node_id = target_shop.get("shop_node_id")
        for offer in target_shop["inventory"]:
            if offer["type"] == "card":
                offer["price"] = self._shop_price("card", CARD_SHOP_PRICES[offer["card_id"]], shop_node_id)
            elif offer["type"] == "heal":
                offer["price"] = self._shop_price("heal", SHOP_HEAL_PRICE, shop_node_id)
            elif offer["type"] == "purge":
                offer["price"] = self._shop_price("purge", SHOP_PURGE_PRICE, shop_node_id)

    def _compose_status_message(self, primary: str, secondary: str | None) -> str:
        if secondary is None or not secondary.strip():
            return primary
        return f"{primary} {secondary}"

    def _enter_map_state(self, status_message: str) -> None:
        self.current_state = "map"
        self.status_message = status_message

    def _handle_placeholder_node(self, node_type: str) -> None:
        self._enter_map_state(
            status_message=(
                f"{node_type.title()} node selected. This content is still placeholder-only for now."
            )
        )

    def _generate_event_state(self) -> dict[str, Any]:
        event_ids = sorted(self.event_library.list_event_ids())
        seen_event_ids = set(self.seen_event_ids)
        candidate_ids = [event_id for event_id in event_ids if event_id not in seen_event_ids]
        if not candidate_ids:
            candidate_ids = event_ids

        rng = self._state_rng("event_pick")
        chosen_event_id = candidate_ids[rng.randrange(len(candidate_ids))]
        if chosen_event_id not in self.seen_event_ids:
            self.seen_event_ids.append(chosen_event_id)
        event_definition = self.event_library.get_event(chosen_event_id)
        return {
            "event_id": chosen_event_id,
            "title": event_definition["title"],
            "selected_choice_id": None,
            "selected_target_id": None,
            "resolved": False,
            "resolved_choice_id": None,
            "resolved_outcome_id": None,
            "resolution_summary": None,
            "resolution_details": [],
        }

    def _credits_for_encounter(self, node_type: str | None) -> int:
        if node_type == "combat":
            return REGULAR_COMBAT_CREDIT_REWARD
        if node_type == "elite":
            return ELITE_COMBAT_CREDIT_REWARD
        return 0

    def _generate_reward_state(
        self,
        encounter_type: str | None,
        credits_granted: int,
    ) -> dict[str, Any] | None:
        if encounter_type not in {"combat", "elite"}:
            return None

        sections: dict[str, Any] = {}
        section_order: list[str] = []

        if encounter_type == "combat":
            if not self._regular_reward_enabled():
                return None
            reward_type = self._regular_reward_type()
            if reward_type == "card_offer":
                sections["card_offer"] = self._build_card_reward_section()
                section_order.append("card_offer")
            else:
                purge_section = self._build_purge_reward_section()
                if purge_section["options"]:
                    sections["purge_offer"] = purge_section
                    section_order.append("purge_offer")
                else:
                    sections["card_offer"] = self._build_card_reward_section()
                    section_order.append("card_offer")
        else:
            sections["card_offer"] = self._build_card_reward_section()
            section_order.append("card_offer")
            sections["purge_offer"] = self._build_purge_reward_section()
            section_order.append("purge_offer")

        return {
            "encounter_type": encounter_type,
            "credits_granted": credits_granted,
            "section_order": section_order,
            "sections": sections,
            "intro_message": f"Reward ready. +{credits_granted} credits earned.",
        }

    def _regular_reward_enabled(self) -> bool:
        rng = self._state_rng("regular_reward")
        return rng.random() < REGULAR_REWARD_CHANCE

    def _regular_reward_type(self) -> str:
        rng = self._state_rng("regular_reward_type")
        total_weight = REGULAR_REWARD_CARD_WEIGHT + REGULAR_REWARD_PURGE_WEIGHT
        if total_weight <= 0:
            raise ValueError("Regular reward weights must sum to a positive value.")

        roll = rng.randint(1, total_weight)
        return "card_offer" if roll <= REGULAR_REWARD_CARD_WEIGHT else "purge_offer"

    def _build_card_reward_section(self) -> dict[str, Any]:
        rng = self._state_rng("card_reward")
        card_ids = list(REWARD_CARD_POOL_IDS)
        rng.shuffle(card_ids)
        bonus_choices = self.run_modifier_engine.reward_card_choice_bonus(self.run_modifiers)
        choice_count = min(REWARD_CARD_CHOICE_COUNT + bonus_choices, len(card_ids))
        chosen_ids = card_ids[:choice_count]
        return {
            "type": "card_offer",
            "title": "Card Reward",
            "description": "Choose a card to add to the deck, or skip it.",
            "options": [
                {
                    "option_id": card_id,
                    "card_id": card_id,
                    "card": self.card_library.create_card(card_id).to_dict(),
                    "label": f"Take {self.card_library.get_card(card_id).name}",
                }
                for card_id in chosen_ids
            ],
            "selected_option_id": None,
            "resolved": False,
            "resolution": None,
            "can_skip": True,
        }

    def _build_purge_reward_section(self) -> dict[str, Any]:
        deck = self.player.deck_manager.starting_deck
        options = [
            {
                "option_id": f"purge_{index}",
                "deck_index": index,
                "card_id": card.id,
                "card": card.to_dict(),
                "label": f"Remove {card.name}",
            }
            for index, card in enumerate(deck)
        ]
        if len(deck) <= MIN_STARTING_DECK_SIZE:
            return {
                "type": "purge_offer",
                "title": "Deck Purge",
                "description": "Choose a card to remove from the deck.",
                "options": [],
                "selected_option_id": None,
                "resolved": True,
                "resolution": {
                    "type": "locked",
                    "summary": "Deck is too small to purge further.",
                },
                "can_skip": False,
            }

        return {
            "type": "purge_offer",
            "title": "Deck Purge",
            "description": "Choose one card to remove from the deck, or skip it.",
            "options": options,
            "selected_option_id": None,
            "resolved": False,
            "resolution": None,
            "can_skip": True,
        }

    def _generate_shop_state(self) -> dict[str, Any]:
        purge_locked = len(self.player.deck_manager.starting_deck) <= MIN_STARTING_DECK_SIZE
        shop_node_id = self.selected_node_id
        chosen_ids = self._shop_card_selection(
            slot_count=min(SHOP_CARD_OFFER_COUNT, len(REWARD_CARD_POOL_IDS)),
            seen_card_ids=[],
            sold_out_card_ids=[],
            current_unsold_ids=[],
            label="shop_inventory:0",
        )
        inventory = [self._shop_card_offer(card_id, shop_node_id=shop_node_id) for card_id in chosen_ids]
        if SHOP_HEAL_ENABLED:
            inventory.append(self._shop_heal_offer(shop_node_id=shop_node_id))
        inventory.append(self._shop_purge_offer(shop_node_id=shop_node_id, purge_locked=purge_locked))
        return {
            "shop_node_id": shop_node_id,
            "inventory": inventory,
            "selected_offer_id": None,
            "selected_purge_index": None,
            "reroll_count": 0,
            "seen_card_ids": list(chosen_ids),
        }

    def _shop_card_offer(self, card_id: str, shop_node_id: str | None = None) -> dict[str, Any]:
        return {
            "offer_id": f"card:{card_id}",
            "type": "card",
            "card_id": card_id,
            "card": self.card_library.create_card(card_id).to_dict(),
            "label": self.card_library.get_card(card_id).name,
            "price": self._shop_price("card", CARD_SHOP_PRICES[card_id], shop_node_id=shop_node_id),
            "sold_out": False,
        }

    def _shop_heal_offer(self, shop_node_id: str | None = None) -> dict[str, Any]:
        return {
            "offer_id": SHOP_HEAL_OFFER_ID,
            "type": "heal",
            "label": "Clinic Patch",
            "description": f"Recover {SHOP_HEAL_AMOUNT} HP now.",
            "price": self._shop_price("heal", SHOP_HEAL_PRICE, shop_node_id=shop_node_id),
            "heal_amount": SHOP_HEAL_AMOUNT,
            "sold_out": False,
        }

    def _shop_purge_offer(self, shop_node_id: str | None, purge_locked: bool) -> dict[str, Any]:
        return {
            "offer_id": SHOP_PURGE_OFFER_ID,
            "type": "purge",
            "label": "Purge Service",
            "description": (
                "Deck too small to purge further."
                if purge_locked
                else "Remove one card from the deck."
            ),
            "price": self._shop_price("purge", SHOP_PURGE_PRICE, shop_node_id=shop_node_id),
            "sold_out": purge_locked,
        }

    def _shop_offer_purchase_availability(self, offer: dict[str, Any]) -> tuple[bool, str | None]:
        if offer.get("sold_out"):
            return False, "That shop offer has already been purchased."

        if offer["price"] > self.player.credits:
            return False, f"Requires {offer['price']} credits."

        if offer["type"] == "purge":
            if len(self.player.deck_manager.starting_deck) <= MIN_STARTING_DECK_SIZE:
                return False, "The deck is too small to purge any further."
            if self.active_shop.get("selected_purge_index") is None:
                return False, "Choose a deck card to purge before purchasing the service."
            return True, None

        if offer["type"] == "heal":
            if self.player.current_hp >= self.player.max_hp:
                return False, "Heal service is only available below max HP."
            return True, None

        return True, None

    def _shop_reroll_price(self) -> int:
        if self.active_shop is None:
            return self._shop_price("reroll", SHOP_REROLL_BASE_PRICE, shop_node_id=None)
        reroll_count = int(self.active_shop.get("reroll_count", 0))
        base_price = SHOP_REROLL_BASE_PRICE + (reroll_count * SHOP_REROLL_PRICE_STEP)
        return self._shop_price(
            "reroll",
            base_price,
            shop_node_id=self.active_shop.get("shop_node_id"),
        )

    def _shop_reroll_availability(self) -> tuple[bool, str | None]:
        if self.active_shop is None:
            return False, "No shop is active."

        unsold_offer_indices = self._rerollable_shop_offer_indices()
        if not unsold_offer_indices:
            return False, "No unsold card offers remain to reroll."

        if not self._shop_replacement_card_ids():
            return False, "No replacement card offers remain for this shop."

        reroll_price = self._shop_reroll_price()
        if self.player.credits < reroll_price:
            return False, f"Requires {reroll_price} credits to reroll."

        return True, None

    def _rerollable_shop_offer_indices(self) -> list[int]:
        if self.active_shop is None:
            return []
        return [
            index
            for index, offer in enumerate(self.active_shop["inventory"])
            if offer["type"] == "card" and not offer.get("sold_out")
        ]

    def _shop_sold_out_card_ids(self) -> list[str]:
        if self.active_shop is None:
            return []
        return [
            offer["card_id"]
            for offer in self.active_shop["inventory"]
            if offer["type"] == "card" and offer.get("sold_out")
        ]

    def _shop_current_unsold_card_ids(self) -> list[str]:
        if self.active_shop is None:
            return []
        return [
            offer["card_id"]
            for offer in self.active_shop["inventory"]
            if offer["type"] == "card" and not offer.get("sold_out")
        ]

    def _shop_replacement_card_ids(self) -> list[str]:
        sold_out_set = set(self._shop_sold_out_card_ids())
        current_unsold_set = set(self._shop_current_unsold_card_ids())
        return [
            card_id
            for card_id in REWARD_CARD_POOL_IDS
            if card_id not in sold_out_set and card_id not in current_unsold_set
        ]

    def _apply_shop_reroll(self) -> None:
        if self.active_shop is None:
            raise ValueError("Shop reroll requested without an active shop.")

        unsold_offer_indices = self._rerollable_shop_offer_indices()
        new_card_ids = self._shop_card_selection(
            slot_count=len(unsold_offer_indices),
            seen_card_ids=self.active_shop.get("seen_card_ids", []),
            sold_out_card_ids=self._shop_sold_out_card_ids(),
            current_unsold_ids=self._shop_current_unsold_card_ids(),
            label=f"shop_inventory:{self.active_shop.get('reroll_count', 0) + 1}",
        )
        if not new_card_ids:
            raise ValueError("No replacement card offers remain for this shop.")

        for offer_index, card_id in zip(unsold_offer_indices, new_card_ids):
            self.active_shop["inventory"][offer_index] = self._shop_card_offer(
                card_id,
                shop_node_id=self.active_shop.get("shop_node_id"),
            )

        self.active_shop["reroll_count"] = int(self.active_shop.get("reroll_count", 0)) + 1
        seen_card_ids = set(self.active_shop.get("seen_card_ids", []))
        seen_card_ids.update(new_card_ids)
        self.active_shop["seen_card_ids"] = sorted(seen_card_ids)
        self._refresh_shop_prices()

    def _shop_card_selection(
        self,
        slot_count: int,
        seen_card_ids: list[str],
        sold_out_card_ids: list[str],
        current_unsold_ids: list[str],
        label: str,
    ) -> list[str]:
        if slot_count <= 0:
            return []

        rng = self._state_rng(label)
        pool_ids = list(REWARD_CARD_POOL_IDS)
        seen_set = set(seen_card_ids)
        sold_out_set = set(sold_out_card_ids)
        current_unsold_set = set(current_unsold_ids)

        chosen_ids: list[str] = []

        def extend_from(candidate_ids: list[str]) -> None:
            remaining_ids = [candidate_id for candidate_id in candidate_ids if candidate_id not in chosen_ids]
            rng.shuffle(remaining_ids)
            for candidate_id in remaining_ids:
                if len(chosen_ids) >= slot_count:
                    break
                chosen_ids.append(candidate_id)

        fresh_ids = [
            card_id
            for card_id in pool_ids
            if card_id not in seen_set
            and card_id not in sold_out_set
            and card_id not in current_unsold_set
        ]
        extend_from(fresh_ids)

        prior_seen_ids = [
            card_id
            for card_id in pool_ids
            if card_id not in sold_out_set
            and card_id not in current_unsold_set
        ]
        extend_from(prior_seen_ids)

        fallback_ids = [card_id for card_id in pool_ids if card_id not in sold_out_set]
        extend_from(fallback_ids)
        return chosen_ids[:slot_count]

    def _shop_purge_targets(self) -> list[dict[str, Any]]:
        if self.player is None or self.player.deck_manager is None:
            return []
        return [
            {
                "option_id": f"purge_target:{index}",
                "deck_index": index,
                "card": card.to_dict(),
                "selected": self.active_shop is not None
                and self.active_shop.get("selected_purge_index") == index,
            }
            for index, card in enumerate(self.player.deck_manager.starting_deck)
        ]

    def _state_rng(self, label: str) -> random.Random:
        if self.run_seed is None:
            raise ValueError("Run seed is not available for deterministic state generation.")
        node_id = self.selected_node_id or "root"
        return random.Random(f"{self.run_seed}:{node_id}:{label}")

    def _serialize_player(self) -> dict[str, Any]:
        return {
            "max_hp": self.player.max_hp,
            "current_hp": self.player.current_hp,
            "max_energy": self.player.max_energy,
            "energy": self.player.energy,
            "block": self.player.block,
            "draw_per_turn": self.player.draw_per_turn,
            "credits": self.player.credits,
            "healing_multiplier": self.player.healing_multiplier,
        }

    def _serialize_deck(self, deck_manager: DeckManager) -> dict[str, Any]:
        return {
            "max_hand_size": deck_manager.max_hand_size,
            "starting_deck": [card.id for card in deck_manager.starting_deck],
            "draw_pile": [card.id for card in deck_manager.draw_pile],
            "hand": [card.id for card in deck_manager.hand],
            "discard_pile": [card.id for card in deck_manager.discard_pile],
            "exhaust_pile": [card.id for card in deck_manager.exhaust_pile],
        }

    def _serialize_map(self) -> dict[str, Any]:
        if self.map_graph is None:
            raise ValueError("Cannot serialize a run without a map graph.")

        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.map_graph["nodes"].items()},
            "start_nodes": list(self.map_graph["start_nodes"]),
            "boss_node_id": self.map_graph["boss_node_id"],
            "available_node_ids": list(self.available_node_ids),
            "visited_node_ids": list(self.visited_node_ids),
            "selected_node_id": self.selected_node_id,
        }

    def _serialize_combat(self) -> dict[str, Any] | None:
        if self.combat_manager is None:
            return None

        return {
            "combat_active": self.combat_manager.combat_active,
            "turn_number": self.combat_manager.turn_manager.turn_number,
            "turn_owner": self.combat_manager.turn_manager.turn_owner,
            "event_log": list(self.combat_manager.event_log),
            "enemies": [
                {
                    "id": enemy.id,
                    "current_hp": enemy.current_hp,
                    "block": enemy.block,
                    "current_intent": enemy.current_intent,
                    "intent_index": getattr(enemy, "_intent_index", 0),
                }
                for enemy in self.combat_manager.enemies
            ],
        }

    def _serialize_event(self) -> dict[str, Any] | None:
        return None if self.active_event is None else copy.deepcopy(self.active_event)

    def _serialize_reward(self) -> dict[str, Any] | None:
        return None if self.active_reward is None else copy.deepcopy(self.active_reward)

    def _serialize_shop(self) -> dict[str, Any] | None:
        return None if self.active_shop is None else copy.deepcopy(self.active_shop)

    def _serialize_modifier_draft(self) -> dict[str, Any] | None:
        return None if self.active_modifier_draft is None else copy.deepcopy(self.active_modifier_draft)

    def _restore_player(
        self,
        player_data: dict[str, Any],
        deck_data: dict[str, Any],
        run_seed: int,
        save_version: int,
    ) -> Player:
        if not isinstance(player_data, dict):
            raise ValueError("Save data is missing player details.")
        if not isinstance(deck_data, dict):
            raise ValueError("Save data is missing deck details.")

        required_player_keys = {
            "max_hp",
            "current_hp",
            "max_energy",
            "energy",
            "block",
            "draw_per_turn",
        }
        if not required_player_keys.issubset(player_data):
            raise ValueError("Player save data is incomplete.")

        required_deck_keys = {
            "max_hand_size",
            "starting_deck",
            "draw_pile",
            "hand",
            "discard_pile",
            "exhaust_pile",
        }
        if not required_deck_keys.issubset(deck_data):
            raise ValueError("Deck save data is incomplete.")

        starting_deck_cards = self._cards_from_ids(deck_data["starting_deck"])
        deck_manager = DeckManager(
            starting_deck_cards,
            rng=random.Random(run_seed),
            max_hand_size=deck_data["max_hand_size"],
        )
        deck_manager.starting_deck = self._cards_from_ids(deck_data["starting_deck"])
        deck_manager.draw_pile = self._cards_from_ids(deck_data["draw_pile"])
        deck_manager.hand = self._cards_from_ids(deck_data["hand"])
        deck_manager.discard_pile = self._cards_from_ids(deck_data["discard_pile"])
        deck_manager.exhaust_pile = self._cards_from_ids(deck_data["exhaust_pile"])

        credits = player_data.get("credits", PLAYER_STARTING_CREDITS if save_version >= 3 else 0)
        player = Player(
            max_hp=player_data["max_hp"],
            current_hp=player_data["current_hp"],
            max_energy=player_data["max_energy"],
            energy=player_data["energy"],
            block=player_data["block"],
            draw_per_turn=player_data["draw_per_turn"],
            credits=credits,
            healing_multiplier=float(player_data.get("healing_multiplier", 1.0)),
        )
        player.attach_deck(deck_manager)
        return player

    def _restore_map(self, map_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(map_data, dict):
            raise ValueError("Save data is missing map details.")

        required_keys = {
            "nodes",
            "start_nodes",
            "boss_node_id",
            "available_node_ids",
            "visited_node_ids",
            "selected_node_id",
        }
        if not required_keys.issubset(map_data):
            raise ValueError("Map save data is incomplete.")
        if not isinstance(map_data["nodes"], dict) or not map_data["nodes"]:
            raise ValueError("Map save data must include node definitions.")

        nodes: dict[str, Node] = {}
        for node_id, node_data in map_data["nodes"].items():
            if not isinstance(node_data, dict):
                raise ValueError("Map nodes must be dictionaries.")
            node = Node(
                node_id=node_data["node_id"],
                node_type=node_data["node_type"],
                floor=node_data["floor"],
                column=node_data["column"],
                next_nodes=list(node_data["next_nodes"]),
            )
            nodes[node_id] = node

        for node_id in map_data["start_nodes"]:
            if node_id not in nodes:
                raise ValueError(f"Unknown start node id in save data: {node_id}")
        if map_data["boss_node_id"] not in nodes:
            raise ValueError("Save data boss node id does not exist in the map graph.")
        if any(node_id not in nodes for node_id in map_data["available_node_ids"]):
            raise ValueError("Save data contains unknown available node ids.")
        if any(node_id not in nodes for node_id in map_data["visited_node_ids"]):
            raise ValueError("Save data contains unknown visited node ids.")
        selected_node_id = map_data["selected_node_id"]
        if selected_node_id is not None and selected_node_id not in nodes:
            raise ValueError("Save data contains an unknown selected node id.")

        return {
            "nodes": nodes,
            "start_nodes": list(map_data["start_nodes"]),
            "boss_node_id": map_data["boss_node_id"],
        }

    def _restore_combat(self, combat_data: dict[str, Any] | None) -> CombatManager:
        if not isinstance(combat_data, dict):
            raise ValueError("Combat save data is required to restore combat.")

        required_keys = {"combat_active", "turn_number", "turn_owner", "event_log", "enemies"}
        if not required_keys.issubset(combat_data):
            raise ValueError("Combat save data is incomplete.")
        if not isinstance(combat_data["enemies"], list) or not combat_data["enemies"]:
            raise ValueError("Combat save data must include at least one enemy.")

        enemies = []
        for enemy_data in combat_data["enemies"]:
            if not isinstance(enemy_data, dict):
                raise ValueError("Saved combat enemies must be dictionaries.")
            enemy = self.enemy_library.create_enemy(enemy_data["id"])
            enemy.current_hp = enemy_data["current_hp"]
            enemy.block = enemy_data["block"]
            enemy.current_intent = enemy_data["current_intent"]
            setattr(enemy, "_intent_index", enemy_data.get("intent_index", 0))
            enemies.append(enemy)

        combat_manager = CombatManager(player=self.player, enemies=enemies)
        combat_manager.combat_active = bool(combat_data["combat_active"])
        combat_manager.turn_manager.turn_number = combat_data["turn_number"]
        combat_manager.turn_manager.turn_owner = combat_data["turn_owner"]
        combat_manager.event_log = list(combat_data["event_log"])
        return combat_manager

    def _restore_event(self, event_data: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(event_data, dict):
            raise ValueError("Event save data is required to restore the event state.")
        required_keys = {
            "event_id",
            "title",
            "selected_choice_id",
            "selected_target_id",
            "resolved",
            "resolved_choice_id",
            "resolved_outcome_id",
            "resolution_summary",
            "resolution_details",
        }
        if not required_keys.issubset(event_data):
            raise ValueError("Event save data is incomplete.")
        if not isinstance(event_data["resolution_details"], list):
            raise ValueError("Event resolution details must be a list.")
        self.event_library.get_event(event_data["event_id"])
        return copy.deepcopy(event_data)

    def _restore_reward(self, reward_data: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(reward_data, dict):
            raise ValueError("Reward save data is required to restore the reward state.")
        required_keys = {"encounter_type", "credits_granted", "section_order", "sections", "intro_message"}
        if not required_keys.issubset(reward_data):
            raise ValueError("Reward save data is incomplete.")
        if not isinstance(reward_data["sections"], dict):
            raise ValueError("Reward sections must be stored as a dictionary.")
        return copy.deepcopy(reward_data)

    def _restore_shop(self, shop_data: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(shop_data, dict):
            raise ValueError("Shop save data is required to restore the shop state.")
        required_keys = {"inventory", "selected_offer_id", "selected_purge_index"}
        if not required_keys.issubset(shop_data):
            raise ValueError("Shop save data is incomplete.")
        if not isinstance(shop_data["inventory"], list):
            raise ValueError("Shop inventory must be a list.")
        restored_shop = copy.deepcopy(shop_data)
        reroll_count = restored_shop.get("reroll_count", 0)
        if not isinstance(reroll_count, int) or reroll_count < 0:
            raise ValueError("Shop reroll_count must be a non-negative integer.")

        seen_card_ids = restored_shop.get("seen_card_ids")
        if seen_card_ids is None:
            seen_card_ids = [
                offer["card_id"]
                for offer in restored_shop["inventory"]
                if isinstance(offer, dict) and offer.get("type") == "card" and isinstance(offer.get("card_id"), str)
            ]
        if not isinstance(seen_card_ids, list) or not all(isinstance(card_id, str) for card_id in seen_card_ids):
            raise ValueError("Shop seen_card_ids must be a list of card ids.")

        restored_shop["reroll_count"] = reroll_count
        restored_shop["seen_card_ids"] = list(dict.fromkeys(seen_card_ids))
        restored_shop["shop_node_id"] = restored_shop.get("shop_node_id", self.selected_node_id)
        if SHOP_HEAL_ENABLED and not any(
            isinstance(offer, dict) and offer.get("offer_id") == SHOP_HEAL_OFFER_ID
            for offer in restored_shop["inventory"]
        ):
            purge_index = next(
                (
                    index
                    for index, offer in enumerate(restored_shop["inventory"])
                    if isinstance(offer, dict) and offer.get("offer_id") == SHOP_PURGE_OFFER_ID
                ),
                len(restored_shop["inventory"]),
            )
            restored_shop["inventory"].insert(
                purge_index,
                self._shop_heal_offer(shop_node_id=restored_shop["shop_node_id"]),
            )
        self._refresh_shop_prices(restored_shop)
        return restored_shop

    def _restore_modifier_draft(self, modifier_draft_data: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(modifier_draft_data, dict):
            raise ValueError("Modifier draft save data is required to restore the draft state.")
        offer_ids = modifier_draft_data.get("offer_ids")
        selected_offer_id = modifier_draft_data.get("selected_offer_id")
        if not isinstance(offer_ids, list) or not offer_ids or not all(isinstance(modifier_id, str) for modifier_id in offer_ids):
            raise ValueError("Modifier draft offer_ids must be a non-empty list of modifier ids.")
        for modifier_id in offer_ids:
            self.run_modifier_library.get_modifier(modifier_id)
        if selected_offer_id is not None:
            if not isinstance(selected_offer_id, str) or selected_offer_id not in offer_ids:
                raise ValueError("Modifier draft selected_offer_id must point to one of the offered modifiers.")
        return {"offer_ids": list(offer_ids), "selected_offer_id": selected_offer_id}

    def _restore_run_modifiers(self, run_modifiers_data: Any) -> list[dict[str, Any]]:
        if run_modifiers_data in (None, []):
            return []
        if not isinstance(run_modifiers_data, list):
            raise ValueError("Saved run_modifiers must be a list.")

        restored: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for modifier_record in run_modifiers_data:
            if not isinstance(modifier_record, dict):
                raise ValueError("Saved run modifier entries must be dictionaries.")
            modifier_id = modifier_record.get("id")
            source = modifier_record.get("source")
            source_detail = modifier_record.get("source_detail")
            if not isinstance(modifier_id, str) or not modifier_id:
                raise ValueError("Saved run modifier ids must be non-empty strings.")
            if not isinstance(source, str) or not source:
                raise ValueError("Saved run modifier sources must be non-empty strings.")
            if modifier_id in seen_ids:
                raise ValueError(f"Saved run modifiers contain a duplicate id: {modifier_id}")
            self.run_modifier_library.get_modifier(modifier_id)
            seen_ids.add(modifier_id)
            restored.append(
                {
                    "id": modifier_id,
                    "source": source,
                    "source_detail": source_detail if isinstance(source_detail, str) else None,
                }
            )
        return restored

    def _restore_modifier_runtime_flags(self, modifier_runtime_flags: Any) -> dict[str, Any]:
        restored = self._default_modifier_runtime_flags()
        if modifier_runtime_flags in (None, {}):
            return restored
        if not isinstance(modifier_runtime_flags, dict):
            raise ValueError("Saved modifier_runtime_flags must be a dictionary.")

        clean_slate_used = modifier_runtime_flags.get("clean_slate_used", False)
        ghost_warranty_used_shops = modifier_runtime_flags.get("ghost_warranty_used_shops", [])
        debt_spike_used_shops = modifier_runtime_flags.get("debt_spike_used_shops", [])

        if not isinstance(clean_slate_used, bool):
            raise ValueError("clean_slate_used must be a boolean.")
        if not isinstance(ghost_warranty_used_shops, list) or not all(isinstance(value, str) for value in ghost_warranty_used_shops):
            raise ValueError("ghost_warranty_used_shops must be a list of node ids.")
        if not isinstance(debt_spike_used_shops, list) or not all(isinstance(value, str) for value in debt_spike_used_shops):
            raise ValueError("debt_spike_used_shops must be a list of node ids.")

        restored["clean_slate_used"] = clean_slate_used
        restored["ghost_warranty_used_shops"] = list(dict.fromkeys(ghost_warranty_used_shops))
        restored["debt_spike_used_shops"] = list(dict.fromkeys(debt_spike_used_shops))
        return restored

    def _restore_seen_event_ids(self, seen_event_ids: Any) -> list[str]:
        if seen_event_ids in (None, []):
            return []
        if not isinstance(seen_event_ids, list) or not all(isinstance(event_id, str) for event_id in seen_event_ids):
            raise ValueError("Saved seen_event_ids must be a list of event ids.")
        for event_id in seen_event_ids:
            self.event_library.get_event(event_id)
        return list(seen_event_ids)

    def _cards_from_ids(self, card_ids: list[str]) -> list[Any]:
        if not isinstance(card_ids, list) or not all(isinstance(card_id, str) for card_id in card_ids):
            raise ValueError("Saved deck piles must be lists of card ids.")
        return [self.card_library.create_card(card_id) for card_id in card_ids]


def simulate_state_manager() -> dict[str, Any]:
    manager = StateManager()
    draft_snapshot = manager.start_new_run(seed=29)
    first_offer_id = draft_snapshot["modifier_draft"]["offers"][0]["id"]
    manager.select_run_modifier_offer(first_offer_id)
    start_snapshot = manager.confirm_run_modifier_selection()
    manager.selected_node_id = "event_test"
    manager.active_event = manager._generate_event_state()
    manager.current_state = "event"
    event_snapshot = manager.get_state_snapshot()
    available_event_choice = next(
        choice for choice in event_snapshot["event"]["choices"] if choice["available"]
    )
    manager.select_event_choice(available_event_choice["id"])
    if manager.get_state_snapshot()["event"]["selected_choice_type"] == "purge":
        manager.select_event_target(manager.get_state_snapshot()["event"]["purge_targets"][0]["option_id"])
    manager.confirm_event_choice()
    post_event_state = manager.get_state_snapshot()["current_state"]
    if post_event_state == "event":
        manager.continue_from_event()
    manager.selected_node_id = "elite_test"
    manager.player.gain_credits(ELITE_COMBAT_CREDIT_REWARD)
    manager.active_reward = manager._generate_reward_state("elite", ELITE_COMBAT_CREDIT_REWARD)
    manager.current_state = "reward"
    reward_snapshot = manager.get_state_snapshot()
    manager.select_reward_option("card_offer", reward_snapshot["reward"]["sections"][0]["options"][0]["option_id"])
    manager.confirm_reward_selection("card_offer")
    manager.skip_reward_section("purge_offer")
    manager.continue_from_reward()
    manager.active_shop = manager._generate_shop_state()
    manager.current_state = "shop"
    shop_snapshot = manager.get_state_snapshot()
    return {
        "start_state": draft_snapshot["current_state"],
        "post_draft_state": start_snapshot["current_state"],
        "event_title": event_snapshot["event"]["title"],
        "post_event_state": "map",
        "reward_sections": len(reward_snapshot["reward"]["sections"]),
        "post_reward_state": "map",
        "shop_offers": len(shop_snapshot["shop"]["inventory"]),
        "credits": manager.player.credits,
    }
