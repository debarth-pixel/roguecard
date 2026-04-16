from __future__ import annotations

import copy
import random
from typing import Any

from cards.card_library import CardLibrary
from cards.deck_manager import DeckManager
from combat.combat_manager import CombatManager
from config import (
    BOSS_CHECKPOINT_HEAL,
    BOSS_RELIC_CHOICE_COUNT,
    BOSS_REWARD_CARD_CHOICE_COUNT,
    ELITE_COMBAT_CREDIT_REWARD,
    ELITE_RELIC_CHOICE_COUNT,
    ENCOUNTER_ENEMY_IDS,
    MIN_STARTING_DECK_SIZE,
    PLAYER_STARTING_CREDITS,
    REGULAR_COMBAT_CREDIT_REWARD,
    REGULAR_REWARD_CARD_WEIGHT,
    REGULAR_REWARD_CHANCE,
    REGULAR_REWARD_PURGE_WEIGHT,
    REWARD_CARD_CHOICE_COUNT,
    SAVE_FORMAT_VERSION,
    SHOP_CARD_OFFER_COUNT,
    SHOP_HEAL_AMOUNT,
    SHOP_HEAL_ENABLED,
    SHOP_HEAL_OFFER_ID,
    SHOP_HEAL_PRICE,
    SHOP_PURGE_OFFER_ID,
    SHOP_PURGE_PRICE,
    SHOP_RELIC_OFFER_COUNT,
    SHOP_RELIC_PRICES_BY_RARITY,
    SHOP_REROLL_BASE_PRICE,
    SHOP_REROLL_PRICE_STEP,
)
from core.campaign_library import CampaignLibrary
from core.character_library import CharacterLibrary
from core.event_library import EventLibrary
from core.event_selector import EventSelector
from core.outskirts_content_library import OutskirtsContentLibrary
from core.run_modifier_engine import RunModifierEngine
from core.run_modifier_library import RunModifierLibrary
from entities.enemy_library import EnemyLibrary
from entities.player import Player
from map.map_generator import MapGenerator
from map.node import Node

CARD_SHOP_PRICE_OVERRIDES: dict[str, int] = {}


class StateManager:
    def __init__(
        self,
        card_library: CardLibrary | None = None,
        enemy_library: EnemyLibrary | None = None,
        modifier_library: RunModifierLibrary | None = None,
        event_library: EventLibrary | None = None,
    ) -> None:
        self.card_library = card_library or CardLibrary()
        self.character_library = CharacterLibrary(card_library=self.card_library)
        self.campaign_library = CampaignLibrary()
        self.grayspine_content = self.campaign_library.grayspine_content
        self.outskirts_content = OutskirtsContentLibrary()
        self.enemy_library = enemy_library or EnemyLibrary()
        self.run_modifier_library = modifier_library or RunModifierLibrary(card_library=self.card_library)
        self.run_modifier_engine = RunModifierEngine(self.run_modifier_library)
        self.event_selector = EventSelector()
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
        self.active_character_select: dict[str, Any] | None = None
        self.run_modifiers: list[dict[str, Any]] = []
        self.modifier_runtime_flags: dict[str, Any] = self._default_modifier_runtime_flags()
        self.event_history: list[dict[str, Any]] = []
        self.character_id: str | None = None
        self.campaign_state: dict[str, Any] | None = None

    def start_new_run(self, seed: int | None = None) -> dict[str, Any]:
        self.run_seed = seed if seed is not None else random.randrange(1, 1_000_000)
        self.character_id = None
        self.player = None
        self.map_graph = None
        self.available_node_ids = []
        self.visited_node_ids = []
        self.selected_node_id = None
        self.combat_manager = None
        self.active_reward = None
        self.active_shop = None
        self.active_event = None
        self.active_modifier_draft = None
        self.active_character_select = {"selected_character_id": None}
        self.run_modifiers = []
        self.modifier_runtime_flags = self._default_modifier_runtime_flags()
        self.event_history = []
        self.current_state = "character_select"
        self.status_message = "Choose a runner before drafting a modifier."
        self.campaign_state = None
        return self.get_state_snapshot()

    def select_character(self, character_id: str) -> dict[str, Any]:
        self._require_character_select()
        self.character_library.get_character(character_id)
        self.character_id = character_id
        self.active_character_select["selected_character_id"] = character_id
        character = self.character_library.get_character(character_id)
        self.status_message = f"Selected {character['name']}."
        return self.get_state_snapshot()

    def confirm_character_selection(self) -> dict[str, Any]:
        self._require_character_select()
        character_id = self.active_character_select.get("selected_character_id")
        if character_id is None:
            raise ValueError("Select a character before confirming.")

        character = self.character_library.get_character(character_id)
        self.character_id = character_id
        self.player = self._create_player(character_id, self.run_seed)
        self._initialize_campaign()
        self.combat_manager = None
        self.active_reward = None
        self.active_shop = None
        self.active_event = None
        self.active_modifier_draft = self._generate_modifier_draft_state()
        self.active_character_select = None
        self.current_state = "modifier_draft"
        self.status_message = f"{character['name']} ready. Choose a relic."
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
            raise ValueError("Select a relic before confirming it.")

        modifier = self.run_modifier_library.get_modifier(modifier_id)
        self._acquire_run_modifier(modifier_id, source="starter_draft")
        self.active_modifier_draft = None
        self._enter_map_state(status_message=f"{modifier['name']} equipped. Select the next node.")
        return self.get_state_snapshot()

    def select_map_node(self, node_id: str) -> dict[str, Any]:
        self._require_map()
        if node_id not in self.available_node_ids:
            raise ValueError(f"Node {node_id} is not currently available.")

        node = self.map_graph["nodes"][node_id]
        self._advance_floor_modifier_effects(node.campaign_floor)
        self.selected_node_id = node_id
        if self.campaign_state is not None:
            self.campaign_state["route_floor_index"] = node.route_floor
            self.campaign_state["global_route_floor_index"] = node.campaign_floor
        if node_id not in self.visited_node_ids:
            self.visited_node_ids.append(node_id)
        self.available_node_ids = list(node.next_nodes)
        self.active_reward = None
        self.active_shop = None
        self.active_event = None

        if node.node_type in ENCOUNTER_ENEMY_IDS:
            self._start_combat_for_node(node)
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
        if getattr(card, "type", "") == "status":
            raise ValueError("Status cards cannot be played.")
        target = self.combat_manager.get_enemy(target_id) if target_id else None
        play_context = self._combat_card_context(card)
        resolution = self.combat_manager.resolve_action(
            {
                "card": card,
                "target": target,
                "cost": play_context["cost"],
                "damage_bonus": play_context["damage_bonus"],
                "repeat_count": play_context["repeat_count"],
                "block_penalty": play_context["block_penalty"],
            }
        )
        self._record_combat_card_play(card, resolution)

        if not self.combat_manager.combat_active:
            self._close_combat()

        return self.get_state_snapshot()

    def end_combat_turn(self) -> dict[str, Any]:
        self._require_combat()
        self._lock_in_turn_history()
        self._apply_combat_modifier_effects("turn_end")
        self.combat_manager.end_turn()

        if not self.combat_manager.combat_active:
            self._close_combat()
        else:
            self._start_player_turn_runtime()

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
        if section_state["type"] == "relic_offer":
            acquire_details = self._acquire_run_modifier(
                option["relic_id"],
                source=section_state.get("source_type", "reward"),
                source_detail=self.selected_node_id,
            )
            summary = " ".join(acquire_details).strip() or f"Acquired {option['relic']['name']}."
        elif section_state["type"] == "card_offer":
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

        transition_state = None if self.active_reward is None else copy.deepcopy(self.active_reward.get("transition"))
        self.active_reward = None
        if transition_state is not None:
            self._apply_campaign_transition(transition_state)
            return self.get_state_snapshot()
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
        elif offer["type"] == "relic":
            acquire_details = self._acquire_run_modifier(
                offer["relic_id"],
                source="shop",
                source_detail=self.selected_node_id,
            )
            summary = " ".join(acquire_details).strip() or f"Purchased {offer['relic']['name']} for {price} credits."
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
            "character": self._snapshot_character(),
            "campaign": self._snapshot_campaign(),
            "grayspine_intel": self._snapshot_grayspine_intel(),
            "character_select": self._snapshot_character_select(),
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
        if self.run_seed is None:
            raise ValueError("Cannot build save data before a run has been initialized.")

        if self.current_state == "character_select":
            return {
                "save_format_version": SAVE_FORMAT_VERSION,
                "current_state": self.current_state,
                "status_message": self.status_message,
                "run_seed": self.run_seed,
                "character": self.character_id,
                "campaign": None,
                "character_select": self._serialize_character_select(),
                "player": None,
                "deck": None,
                "map": None,
                "combat": None,
                "event": None,
                "reward": None,
                "shop": None,
                "modifier_draft": None,
                "run_modifiers": [],
                "modifier_runtime_flags": self._default_modifier_runtime_flags(),
                "event_history": [],
                "seen_event_ids": [],
            }

        if self.player is None or self.player.deck_manager is None or self.map_graph is None:
            raise ValueError("Cannot build save data before a character has entered a run.")

        return {
            "save_format_version": SAVE_FORMAT_VERSION,
            "current_state": self.current_state,
            "status_message": self.status_message,
            "run_seed": self.run_seed,
            "character": self._active_character_id(),
            "campaign": self._serialize_campaign(),
            "character_select": None,
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
            "event_history": copy.deepcopy(self.event_history),
            "seen_event_ids": self._seen_event_ids(),
        }

    def restore_save_data(self, save_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(save_data, dict):
            raise ValueError("Save data must be a dictionary.")

        save_version = save_data.get("save_format_version")
        if save_version != SAVE_FORMAT_VERSION:
            raise ValueError(f"Unsupported save format version: {save_version}")

        run_seed = save_data.get("run_seed")
        current_state = save_data.get("current_state")
        status_message = save_data.get("status_message")
        character_id = save_data.get("character")
        campaign_data = save_data.get("campaign")
        character_select_data = save_data.get("character_select")
        player_data = save_data.get("player")
        deck_data = save_data.get("deck")
        map_data = save_data.get("map")
        combat_data = save_data.get("combat")
        event_data = save_data.get("event")
        reward_data = save_data.get("reward")
        shop_data = save_data.get("shop")
        seen_event_ids = save_data.get("seen_event_ids")
        event_history_data = save_data.get("event_history")
        modifier_draft_data = save_data.get("modifier_draft")
        run_modifiers_data = save_data.get("run_modifiers")
        modifier_runtime_flags = save_data.get("modifier_runtime_flags")

        allowed_states = {
            "character_select",
            "modifier_draft",
            "map",
            "combat",
            "reward",
            "shop",
            "event",
            "victory",
            "game_over",
        }

        if not isinstance(run_seed, int):
            raise ValueError("Save data is missing a valid run_seed.")
        if current_state not in allowed_states:
            raise ValueError(f"Save data has an unsupported current_state: {current_state}")
        if not isinstance(status_message, str) or not status_message:
            raise ValueError("Save data must include a non-empty status_message.")

        self.run_seed = run_seed
        self.character_id = None if character_id is None else self._restore_character_id(character_id)
        self.status_message = status_message
        self.current_state = current_state
        self.combat_manager = None
        self.active_reward = None
        self.active_shop = None
        self.active_event = None
        self.active_modifier_draft = None
        self.active_character_select = None
        self.run_modifiers = []
        self.modifier_runtime_flags = self._default_modifier_runtime_flags()
        self.event_history = []
        self.player = None
        self.campaign_state = None
        self.map_graph = None
        self.available_node_ids = []
        self.visited_node_ids = []
        self.selected_node_id = None

        if current_state == "character_select":
            self.active_character_select = self._restore_character_select(character_select_data, self.character_id)
            return self.get_state_snapshot()

        self.player = self._restore_player(player_data, deck_data, run_seed)
        self.campaign_state = self._restore_campaign(campaign_data)
        self.map_graph = self._restore_map(map_data)
        self.available_node_ids = list(map_data["available_node_ids"])
        self.visited_node_ids = list(map_data["visited_node_ids"])
        self.selected_node_id = map_data["selected_node_id"]
        self.run_modifiers = self._restore_run_modifiers(run_modifiers_data)
        self.modifier_runtime_flags = self._restore_modifier_runtime_flags(modifier_runtime_flags)
        self.event_history = self._restore_event_history(event_history_data, seen_event_ids)

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

    def _start_combat_for_node(self, node: Node) -> None:
        if node.node_type not in ENCOUNTER_ENEMY_IDS:
            raise ValueError(f"Encounter node type is not mapped for combat: {node.node_type}")
        enemy_ids = list(node.enemy_ids) if node.enemy_ids else [ENCOUNTER_ENEMY_IDS[node.node_type]]
        enemies = [self.enemy_library.create_enemy(enemy_id) for enemy_id in enemy_ids]
        self.combat_manager = CombatManager(
            player=self.player,
            enemies=enemies,
            rng=self._state_rng(f"combat:{node.node_id}"),
            bark_source=self.grayspine_content,
        )
        self.combat_manager.set_card_factory(self.card_library.create_card)
        self.combat_manager.set_enemy_factory(self.enemy_library.create_enemy)
        self.combat_manager.set_event_sink(self._handle_combat_runtime_event)
        self._begin_combat_modifier_runtime()
        self.current_state = "combat"
        self.combat_manager.start_combat()
        self._apply_combat_modifier_effects("combat_start")
        self._apply_combat_modifier_effects("on_turn_start")
        self._apply_combat_modifier_effects("turn_one")
        if node.node_type == "boss" and self.map_graph is not None:
            boss_id = node.boss_slot_id or self.map_graph.get("selected_boss_id")
            if isinstance(boss_id, str):
                try:
                    boss = self.grayspine_content.get_boss(boss_id)
                except KeyError:
                    boss = self.map_graph.get("selected_boss", {})
                boss_name = boss.get("name", "Boss")
                boss_summary = boss.get("summary")
                if isinstance(boss_summary, str) and boss_summary:
                    self.status_message = f"{boss_name}: {boss_summary}"
                else:
                    self.status_message = f"{boss_name} blocks the path through {self._current_map_name()}."
                return
        self.status_message = f"Entered {node.node_type} encounter on {self._current_map_name()}. Play cards or end your turn."

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
        self.player.end_combat()
        self._end_combat_modifier_runtime()

        if not self.player.is_alive():
            self.active_reward = None
            self.current_state = "game_over"
            self.status_message = "Run failed."
            return

        self.player.deck_manager.normalize_overworld_deck()
        if encounter_type == "boss":
            if self._current_map_index() >= 3:
                self.active_reward = None
                self.current_state = "victory"
                self.status_message = f"{self._current_map_name()} cleared. Run completed."
                return

            reward_state = self._generate_boss_transition_reward()
            self.active_reward = reward_state
            self.current_state = "reward"
            self.status_message = reward_state["intro_message"]
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
            "map_id": self.map_graph["map_id"],
            "map_name": self.map_graph["map_name"],
            "map_index": self.map_graph["map_index"],
            "branch_faction": self.map_graph.get("branch_faction"),
            "route_floor_count": self.map_graph["route_floor_count"],
            "selected_boss_id": self.map_graph["selected_boss_id"],
            "canvas_width": self.map_graph["canvas_width"],
            "canvas_height": self.map_graph["canvas_height"],
            "nodes": {node_id: node.to_dict() for node_id, node in self.map_graph["nodes"].items()},
            "start_nodes": list(self.map_graph["start_nodes"]),
            "boss_node_id": self.map_graph["boss_node_id"],
            "available_node_ids": list(self.available_node_ids),
            "visited_node_ids": list(self.visited_node_ids),
            "selected_node_id": self.selected_node_id,
        }

    def _snapshot_campaign(self) -> dict[str, Any] | None:
        if self.campaign_state is None:
            return None
        return copy.deepcopy(self.campaign_state)

    def _snapshot_character(self) -> dict[str, Any] | None:
        character_id = self._active_character_id()
        if character_id is None:
            return None
        character = self.character_library.get_character(character_id)
        return {
            "id": character["id"],
            "name": character["name"],
            "subtitle": character["subtitle"],
            "description": character["description"],
            "accent_color": list(character["accent_color"]),
            "palette_key": character["palette_key"],
        }

    def _snapshot_character_select(self) -> dict[str, Any] | None:
        if self.active_character_select is None:
            return None
        selected_character_id = self.active_character_select.get("selected_character_id")
        characters: list[dict[str, Any]] = []
        for character in self.character_library.list_characters():
            preview_cards = [
                self.card_library.create_card(card_id).to_dict()
                for card_id in character["preview_card_ids"]
            ]
            characters.append(
                {
                    "id": character["id"],
                    "name": character["name"],
                    "subtitle": character["subtitle"],
                    "description": character["description"],
                    "accent_color": list(character["accent_color"]),
                    "preview_cards": preview_cards,
                    "selected": character["id"] == selected_character_id,
                }
            )
        return {
            "selected_character_id": selected_character_id,
            "characters": characters,
            "can_confirm": selected_character_id is not None,
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
                    "type": modifier["type"],
                    "kind": modifier["type"],
                    "rarity": modifier["rarity"],
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
            "transition": copy.deepcopy(self.active_reward.get("transition")),
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

    def _require_character_select(self) -> None:
        if self.current_state != "character_select" or self.active_character_select is None:
            raise ValueError("Character selection is only available while choosing a character.")

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
        character_ids = choice.get("character_ids", [])
        active_character_id = self._active_character_id()
        if character_ids and active_character_id not in character_ids:
            return False, "Unavailable for this character."

        requirements = choice.get("requirements", {})
        credits_at_least = requirements.get("credits_at_least")
        if credits_at_least is not None and self.player.credits < credits_at_least:
            return False, f"Requires at least {credits_at_least} credits."

        credits_at_most = requirements.get("credits_at_most")
        if credits_at_most is not None and self.player.credits > credits_at_most:
            return False, f"Requires at most {credits_at_most} credits."

        missing_hp_at_least = requirements.get("missing_hp_at_least")
        missing_hp = self.player.max_hp - self.player.current_hp
        if missing_hp_at_least is not None and missing_hp < missing_hp_at_least:
            return False, f"Requires at least {missing_hp_at_least} missing HP."

        deck_size_at_least = requirements.get("deck_size_at_least")
        deck_size = len(self.player.deck_manager.starting_deck)
        if deck_size_at_least is not None and deck_size < deck_size_at_least:
            return False, f"Requires a deck of at least {deck_size_at_least} cards."

        status_count_at_most = requirements.get("status_count_at_most")
        if status_count_at_most is not None and len(self.run_modifiers) > status_count_at_most:
            return False, f"Requires at most {status_count_at_most} active statuses."

        modifier_active = requirements.get("modifier_active")
        if modifier_active is not None and not self.run_modifier_engine.has_modifier(self.run_modifiers, modifier_active):
            modifier = self.run_modifier_library.get_modifier(modifier_active)
            return False, f"Requires active status: {modifier['name']}."

        modifier_missing = requirements.get("modifier_missing")
        if modifier_missing is not None and self.run_modifier_engine.has_modifier(self.run_modifiers, modifier_missing):
            modifier = self.run_modifier_library.get_modifier(modifier_missing)
            return False, f"Unavailable while {modifier['name']} is active."

        for effect in choice.get("effects", []):
            if effect["type"] == "gain_modifier":
                available, disabled_reason = self.run_modifier_engine.can_gain_modifier(
                    self.run_modifiers,
                    effect["modifier_id"],
                )
                if not available:
                    return False, disabled_reason
                continue

            if effect["type"] == "gain_random_modifier":
                candidates = self.run_modifier_engine.weighted_modifier_candidates(
                    self.run_modifiers,
                    source_type=effect["source_type"],
                    rarity_profile=effect["rarity_profile"],
                    allow_types=effect.get("allow_types"),
                    allow_rarities=effect.get("allow_rarities"),
                    include_tags=effect.get("include_tags"),
                    exclude_tags=effect.get("exclude_tags"),
                )
                if not candidates and not effect.get("fallback_effects"):
                    return False, "No compatible statuses are available right now."

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
                    duration_override=effect.get("duration"),
                )
                details.extend(modifier_details)
            elif effect_type == "gain_random_modifier":
                effect_label = "unknown"
                if self.active_event is not None:
                    effect_label = (
                        f"{self.active_event['event_id']}:"
                        f"{self.active_event.get('selected_choice_id', 'choice')}:"
                        f"{len(details)}"
                    )
                chosen_modifier = self.run_modifier_engine.choose_weighted_modifier(
                    rng=self._state_rng(f"event_random_modifier:{effect_label}"),
                    active_modifiers=self.run_modifiers,
                    source_type=effect["source_type"],
                    rarity_profile=effect["rarity_profile"],
                    allow_types=effect.get("allow_types"),
                    allow_rarities=effect.get("allow_rarities"),
                    include_tags=effect.get("include_tags"),
                    exclude_tags=effect.get("exclude_tags"),
                )
                if chosen_modifier is None:
                    fallback_effects = effect.get("fallback_effects", [])
                    if fallback_effects:
                        details.extend(self._apply_event_effects(fallback_effects, target_id=target_id))
                    else:
                        details.append("No compatible status was available.")
                else:
                    details.extend(
                        self._acquire_run_modifier(
                            chosen_modifier["id"],
                            source="event",
                            source_detail=self.active_event["event_id"] if self.active_event is not None else None,
                            duration_override=effect.get("duration"),
                        )
                    )
            elif effect_type == "remove_modifier":
                details.extend(self._remove_run_modifier(effect["modifier_id"]))
            elif effect_type == "refresh_modifier":
                details.extend(
                    self._refresh_run_modifier(
                        effect["modifier_id"],
                        duration_override=effect.get("duration"),
                    )
                )
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
        if self.current_state == "combat" and self.combat_manager is not None:
            return [self._combat_card_snapshot(card) for card in self.player.deck_manager.hand]
        return [card.to_dict() for card in self.player.deck_manager.hand]

    def _current_node_type(self) -> str | None:
        if self.map_graph is None or self.selected_node_id is None:
            return None
        node = self.map_graph["nodes"].get(self.selected_node_id)
        return None if node is None else node.node_type

    def _current_node_floor(self) -> int:
        if self.map_graph is None or self.selected_node_id is None:
            return 0
        node = self.map_graph["nodes"].get(self.selected_node_id)
        return 0 if node is None else node.route_floor

    def _current_global_floor(self) -> int:
        if self.map_graph is None or self.selected_node_id is None:
            return 0
        node = self.map_graph["nodes"].get(self.selected_node_id)
        return 0 if node is None else node.campaign_floor

    def _current_map_index(self) -> int:
        if self.campaign_state is None:
            return 0
        return int(self.campaign_state.get("map_index", 0))

    def _current_map_id(self) -> str | None:
        if self.campaign_state is None:
            return None
        map_id = self.campaign_state.get("map_id")
        return map_id if isinstance(map_id, str) else None

    def _current_map_name(self) -> str:
        if self.campaign_state is None:
            return "the city"
        map_name = self.campaign_state.get("map_name")
        if isinstance(map_name, str) and map_name:
            return map_name
        return "the city"

    def _active_character_id(self) -> str | None:
        if self.player is not None and self.player.character_id is not None:
            return self.player.character_id
        if self.character_id is not None:
            return self.character_id
        if self.active_character_select is not None:
            selected_character_id = self.active_character_select.get("selected_character_id")
            if isinstance(selected_character_id, str):
                return selected_character_id
        return None

    def _active_character(self) -> dict[str, Any]:
        character_id = self._active_character_id()
        if character_id is None:
            raise ValueError("No character is currently selected.")
        return self.character_library.get_character(character_id)

    def _create_player(self, character_id: str, seed: int) -> Player:
        starter_cards = [self.card_library.create_card(card_id) for card_id in self.character_library.get_character(character_id)["starting_deck_ids"]]
        deck_manager = DeckManager(starter_cards, rng=random.Random(seed))
        player = Player(credits=PLAYER_STARTING_CREDITS, character_id=character_id)
        player.attach_deck(deck_manager)
        return player

    def _initialize_campaign(self) -> None:
        self.campaign_state = {
            "map_index": 1,
            "map_id": "outskirts",
            "map_name": self.campaign_library.get_map_definition("outskirts")["name"],
            "route_floor_index": 0,
            "route_floor_count": 0,
            "branch_faction": None,
            "selected_boss_id": None,
            "global_route_floor_index": 0,
        }
        self._generate_campaign_map("outskirts", map_index=1, branch_faction=None)

    def _generate_campaign_map(
        self,
        map_id: str,
        *,
        map_index: int,
        branch_faction: str | None,
    ) -> None:
        map_definition = self.campaign_library.get_map_definition(map_id)
        global_floor_offset = (map_index - 1) * (map_definition["route_floor_count"] + 1)
        boss_rng = self._state_rng(f"campaign_boss:{map_id}:{map_index}")
        selected_boss = self.campaign_library.choose_boss(map_id, boss_rng)
        map_rng = self._state_rng(f"campaign_map:{map_id}:{map_index}")
        self.map_graph = MapGenerator(rng=map_rng).generate_map(
            map_definition,
            map_index=map_index,
            global_floor_offset=global_floor_offset,
            branch_faction=branch_faction,
            selected_boss=selected_boss,
        )
        self._assign_route_encounters(self.map_graph)
        self.available_node_ids = list(self.map_graph["start_nodes"])
        self.visited_node_ids = []
        self.selected_node_id = None
        if self.campaign_state is None:
            self.campaign_state = {}
        self.campaign_state.update(
            {
                "map_index": map_index,
                "map_id": map_definition["id"],
                "map_name": map_definition["name"],
                "route_floor_index": 0,
                "route_floor_count": map_definition["route_floor_count"],
                "branch_faction": branch_faction,
                "selected_boss_id": selected_boss["id"],
                "global_route_floor_index": global_floor_offset,
            }
        )
        self.modifier_runtime_flags["last_floor_status_tick"] = max(
            self.modifier_runtime_flags.get("last_floor_status_tick", 0),
            max(0, global_floor_offset - 1),
        )

    def _generate_boss_transition_reward(self) -> dict[str, Any]:
        current_map_id = self._current_map_id()
        if current_map_id is None or self.map_graph is None:
            raise ValueError("Boss transition reward requires an active campaign map.")
        selected_boss = copy.deepcopy(self.map_graph["selected_boss"])
        next_map_id = self.campaign_library.next_map_id_for_boss(current_map_id, selected_boss)
        if next_map_id is None:
            raise ValueError("Final-map bosses should not generate checkpoint rewards.")

        next_map_definition = self.campaign_library.get_map_definition(next_map_id)
        checkpoint_transition = {
            "from_map_id": current_map_id,
            "from_map_name": self._current_map_name(),
            "next_map_id": next_map_definition["id"],
            "next_map_name": next_map_definition["name"],
            "next_map_index": self._current_map_index() + 1,
            "branch_faction": next_map_definition.get("branch_faction"),
            "checkpoint_heal": BOSS_CHECKPOINT_HEAL,
            "defeated_boss_id": selected_boss["id"],
            "defeated_boss_name": selected_boss["name"],
        }

        sections = {
            "relic_offer": self._build_relic_reward_section(
                choice_count=BOSS_RELIC_CHOICE_COUNT,
                source_type="boss_reward",
                title="Boss Relic",
                description="Choose one relic to carry into the next map.",
                can_skip=False,
            ),
            "card_offer": self._build_card_reward_section(choice_count=BOSS_REWARD_CARD_CHOICE_COUNT),
        }
        return {
            "encounter_type": "boss",
            "credits_granted": 0,
            "section_order": ["relic_offer", "card_offer"],
            "sections": sections,
            "intro_message": (
                f"{selected_boss['name']} defeated. Claim a checkpoint reward before entering {next_map_definition['name']}."
            ),
            "transition": checkpoint_transition,
        }

    def _apply_campaign_transition(self, transition_state: dict[str, Any]) -> None:
        next_map_id = transition_state["next_map_id"]
        next_map_index = int(transition_state["next_map_index"])
        branch_faction = transition_state.get("branch_faction")
        checkpoint_heal = int(transition_state.get("checkpoint_heal", 0))
        healed = 0 if checkpoint_heal <= 0 else self.player.heal(checkpoint_heal)
        self._generate_campaign_map(
            next_map_id,
            map_index=next_map_index,
            branch_faction=branch_faction,
        )
        heal_summary = f"Recovered {healed} HP at the checkpoint." if healed > 0 else "Checkpoint secured."
        route_intro = ""
        if next_map_index >= 3:
            route_faction_id = self.grayspine_content.faction_for_map(next_map_id)
            if route_faction_id is not None:
                route_intro = f" {self.grayspine_content.route_intro_text(route_faction_id)}"
        self._enter_map_state(
            status_message=(
                f"{heal_summary} Entering {self._current_map_name()}.{route_intro} Select the next node."
            )
        )

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
            "last_floor_status_tick": 0,
            "combat": self._default_combat_runtime_flags(),
        }

    def _default_combat_runtime_flags(self) -> dict[str, Any]:
        return {
            "active_modifier_ids": [],
            "cards_played_this_combat": 0,
            "cards_played_this_turn": 0,
            "current_turn_attack_played": False,
            "last_turn_attack_played": False,
            "first_block_penalty_remaining": 0,
            "pending_energy_next_turn": 0,
            "triggered_modifier_ids_this_turn": [],
            "triggered_modifier_ids_this_combat": [],
            "runtime_event_index": 0,
        }

    def _combat_runtime_flags(self) -> dict[str, Any]:
        combat_flags = self.modifier_runtime_flags.get("combat")
        if not isinstance(combat_flags, dict):
            combat_flags = self._default_combat_runtime_flags()
            self.modifier_runtime_flags["combat"] = combat_flags
        return combat_flags

    def _acquire_run_modifier(
        self,
        modifier_id: str,
        source: str,
        source_detail: str | None = None,
        duration_override: dict[str, Any] | None = None,
    ) -> list[str]:
        modifier = self.run_modifier_library.get_modifier(modifier_id)
        available, disabled_reason = self.run_modifier_engine.can_gain_modifier(self.run_modifiers, modifier_id)
        if not available:
            raise ValueError(disabled_reason or f"{modifier['name']} cannot be acquired right now.")

        existing = self.run_modifier_engine.get_modifier_record(self.run_modifiers, modifier_id)
        if existing is not None:
            if modifier["stack_behavior"] == "refresh_duration":
                self.run_modifier_engine.refresh_modifier_record(existing, duration_override=duration_override)
                duration_label = self.run_modifier_engine.hydrate_modifier(existing).get("duration_label")
                refreshed_text = f"Refreshed: {modifier['name']}."
                if duration_label:
                    refreshed_text = f"{refreshed_text} {duration_label.title()}."
                return [refreshed_text]

            self.run_modifier_engine.increment_modifier_record(existing, duration_override=duration_override)
            hydrated_modifier = self.run_modifier_engine.hydrate_modifier(existing)
            if modifier["stack_behavior"] == "stack_intensity":
                return [f"Intensified: {modifier['name']} x{hydrated_modifier['stack_intensity']}."]
            if modifier["stack_behavior"] == "stack_count":
                return [f"Stacked: {modifier['name']} x{hydrated_modifier['stack_count']}."]
            duration_label = self.run_modifier_engine.hydrate_modifier(existing).get("duration_label")
            refreshed_text = f"Refreshed: {modifier['name']}."
            if duration_label:
                refreshed_text = f"{refreshed_text} {duration_label.title()}."
            return [refreshed_text]

        self.run_modifiers.append(
            self.run_modifier_engine.create_modifier_record(
                modifier_id,
                source=source,
                source_detail=source_detail,
                duration_override=duration_override,
            )
        )

        details = [f"Gained: {modifier['name']}."]
        for effect in modifier.get("hooks", {}).get("on_acquire", []):
            details.extend(self._apply_modifier_effect(effect))
        return details

    def _remove_run_modifier(self, modifier_id: str) -> list[str]:
        modifier = self.run_modifier_library.get_modifier(modifier_id)
        remaining_records = [record for record in self.run_modifiers if record.get("id") != modifier_id]
        if len(remaining_records) == len(self.run_modifiers):
            return [f"{modifier['name']} was not active."]
        self.run_modifiers = remaining_records
        combat_flags = self._combat_runtime_flags()
        combat_flags["active_modifier_ids"] = [
            active_id for active_id in combat_flags.get("active_modifier_ids", []) if active_id != modifier_id
        ]
        return [f"Removed: {modifier['name']}."]

    def _refresh_run_modifier(
        self,
        modifier_id: str,
        duration_override: dict[str, Any] | None = None,
    ) -> list[str]:
        record = self.run_modifier_engine.get_modifier_record(self.run_modifiers, modifier_id)
        modifier = self.run_modifier_library.get_modifier(modifier_id)
        if record is None:
            return [f"{modifier['name']} is not active."]
        self.run_modifier_engine.refresh_modifier_record(record, duration_override=duration_override)
        duration_label = self.run_modifier_engine.hydrate_modifier(record).get("duration_label")
        refreshed_text = f"Refreshed: {modifier['name']}."
        if duration_label:
            refreshed_text = f"{refreshed_text} {duration_label.title()}."
        return [refreshed_text]

    def _apply_modifier_effect(
        self,
        effect: dict[str, Any],
        *,
        event: dict[str, Any] | None = None,
    ) -> list[str]:
        effect_type = effect["type"]
        if effect_type == "gain_credits":
            gained = self.player.gain_credits(effect["value"])
            return [f"Gained {gained} credits."]
        if effect_type == "lose_credits":
            lost = min(effect["value"], self.player.credits)
            if lost > 0:
                self.player.spend_credits(lost)
            return [f"Lost {lost} credits."]
        if effect_type == "damage":
            damage = self.player.take_damage(effect["value"])
            return [f"Lost {damage} HP."]
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
        if effect_type == "lose_block":
            lost = min(effect["value"], self.player.block)
            self.player.block -= lost
            return [f"Lost {lost} Block."]
        if effect_type == "draw_cards":
            if self.combat_manager is not None and self.current_state == "combat":
                drawn = self.combat_manager.draw_cards(self.player, effect["value"])
            else:
                drawn = self.player.deck_manager.draw_cards(effect["value"])
            return [f"Drew {len(drawn)} card{'s' if len(drawn) != 1 else ''}."]
        if effect_type == "gain_energy":
            self.player.energy += effect["value"]
            return [f"Gained {effect['value']} Energy."]
        if effect_type == "gain_next_turn_energy":
            combat_flags = self._combat_runtime_flags()
            combat_flags["pending_energy_next_turn"] = max(
                0,
                int(combat_flags.get("pending_energy_next_turn", 0)) + effect["value"],
            )
            return [f"Banked {effect['value']} Energy for next turn."]
        if effect_type == "heal":
            healed = self.player.heal(effect["value"])
            return [f"Recovered {healed} HP."]
        if effect_type == "heal_after_event":
            healed = self.player.heal(effect["value"])
            return [] if healed <= 0 else [f"Recovered {healed} HP."]
        if effect_type == "damage_event_target":
            enemy = self._event_target_enemy(event)
            if enemy is None:
                return []
            applied = self.combat_manager.apply_damage(self.player, enemy, effect["value"], emit_event=False)
            return [] if applied <= 0 else [f"{enemy.name} took {applied} bonus damage."]
        if effect_type == "damage_random_enemy":
            enemy = self._random_living_enemy()
            if enemy is None:
                return []
            applied = self.combat_manager.apply_damage(self.player, enemy, effect["value"], emit_event=False)
            return [] if applied <= 0 else [f"{enemy.name} took {applied} random damage."]
        if effect_type == "apply_status_all_enemies":
            if self.combat_manager is None:
                return []
            applied_count = 0
            for enemy in self.combat_manager.enemies:
                if not enemy.is_alive():
                    continue
                applied = self.combat_manager._apply_status_to_enemy(
                    enemy,
                    effect["status_id"],
                    effect["value"],
                )
                if applied > 0:
                    applied_count += 1
            return [] if applied_count <= 0 else [f"Applied {effect['status_id']} to {applied_count} enemies."]
        if effect_type == "increase_highest_enemy_status":
            enemy = self._highest_status_enemy(effect["status_id"])
            if enemy is None:
                return []
            applied = self.combat_manager._apply_status_to_enemy(
                enemy,
                effect["status_id"],
                effect["value"],
            )
            return [] if applied <= 0 else [f"{enemy.name}'s {effect['status_id']} increased."]
        if effect_type == "reduce_player_status":
            status_id = effect.get("status_id")
            if status_id is None and event is not None:
                status_id = event.get("status_id")
            if not isinstance(status_id, str) or not status_id:
                return []
            if status_id == "nullified":
                reduced = 1 if self.player.remove_nullified() else 0
            else:
                reduced = self.player.cleanse_combat_status(status_id, effect["value"])
            return [] if reduced <= 0 else [f"Reduced {status_id} by {reduced}."]
        if effect_type == "random_one_of":
            option = self._resolve_random_modifier_option(effect)
            nested_details: list[str] = []
            for nested_effect in option["effects"]:
                nested_details.extend(self._apply_modifier_effect(nested_effect, event=event))
            if option.get("summary"):
                return [option["summary"], *nested_details]
            return nested_details
        return []

    def _apply_combat_modifier_effects(self, hook_name: str) -> None:
        for effect in self.run_modifier_engine.get_effects(self._active_modifiers_for_combat(), hook_name):
            self._apply_modifier_effect(effect)

    def _handle_combat_runtime_event(self, event: dict[str, Any]) -> None:
        if self.current_state != "combat" or self.combat_manager is None:
            return
        hook_name = event.get("hook")
        if not isinstance(hook_name, str) or not hook_name:
            return

        combat_flags = self._combat_runtime_flags()
        combat_flags["runtime_event_index"] = int(combat_flags.get("runtime_event_index", 0)) + 1
        triggered_this_turn = set(combat_flags.get("triggered_modifier_ids_this_turn", []))
        triggered_this_combat = set(combat_flags.get("triggered_modifier_ids_this_combat", []))

        for record in self._active_modifiers_for_combat():
            modifier = self.run_modifier_library.get_modifier(record["id"])
            hook_effects = modifier.get("hooks", {}).get(hook_name, [])
            matching_effects = [
                effect for effect in hook_effects if self._modifier_effect_matches_event(effect, event)
            ]
            if not matching_effects:
                continue

            gate_key = f"{modifier['id']}:{hook_name}"
            if any(effect.get("once_per") == "turn" for effect in matching_effects) and gate_key in triggered_this_turn:
                continue
            if any(effect.get("once_per") == "combat" for effect in matching_effects) and gate_key in triggered_this_combat:
                continue

            for effect in matching_effects:
                self._apply_modifier_effect(effect, event=event)

            if any(effect.get("once_per") == "turn" for effect in matching_effects):
                triggered_this_turn.add(gate_key)
            if any(effect.get("once_per") == "combat" for effect in matching_effects):
                triggered_this_combat.add(gate_key)

        combat_flags["triggered_modifier_ids_this_turn"] = sorted(triggered_this_turn)
        combat_flags["triggered_modifier_ids_this_combat"] = sorted(triggered_this_combat)

    def _modifier_effect_matches_event(self, effect: dict[str, Any], event: dict[str, Any]) -> bool:
        status_ids = effect.get("status_ids")
        if status_ids is not None:
            event_status_id = event.get("status_id")
            if event_status_id not in status_ids:
                return False

        card_type = effect.get("card_type")
        if card_type is not None and event.get("card_type") != card_type:
            return False

        required_statuses = effect.get("require_target_has_statuses")
        if required_statuses is not None:
            target_status_ids = set(event.get("target_status_ids", []))
            if not target_status_ids.intersection(required_statuses):
                return False

        return True

    def _event_target_enemy(self, event: dict[str, Any] | None) -> Any | None:
        if self.combat_manager is None or event is None:
            return None
        target_id = event.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            return None
        return self.combat_manager.get_enemy(target_id)

    def _random_living_enemy(self) -> Any | None:
        if self.combat_manager is None:
            return None
        living_enemies = [enemy for enemy in self.combat_manager.enemies if enemy.is_alive()]
        if not living_enemies:
            return None
        event_index = int(self._combat_runtime_flags().get("runtime_event_index", 0))
        rng = self._state_rng(f"modifier_event_enemy:{event_index}")
        return rng.choice(living_enemies)

    def _highest_status_enemy(self, status_id: str) -> Any | None:
        if self.combat_manager is None:
            return None
        living_enemies = [enemy for enemy in self.combat_manager.enemies if enemy.is_alive()]
        if not living_enemies:
            return None
        ranked = sorted(
            living_enemies,
            key=lambda enemy: (
                self._combat_status_value(enemy, status_id),
                enemy.current_hp,
                enemy.id,
            ),
            reverse=True,
        )
        top_enemy = ranked[0]
        if self._combat_status_value(top_enemy, status_id) <= 0:
            return None
        return top_enemy

    def _combat_status_value(self, target: Any, status_id: str) -> int:
        key = str(status_id).strip().lower()
        if hasattr(target, "combat_status_value"):
            try:
                return int(target.combat_status_value(key))
            except ValueError:
                return 0
        value = getattr(target, key, None)
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return max(0, value)
        if hasattr(target, "get_status"):
            return max(0, int(target.get_status(key)))
        return 0

    def _apply_post_victory_modifier_effects(self, encounter_type: str | None) -> str | None:
        summaries: list[str] = []
        for effect in self.run_modifier_engine.filter_post_victory_effects(self.run_modifiers, encounter_type):
            summaries.extend(self._apply_modifier_effect(effect))
        return None if not summaries else " ".join(summaries)

    def _apply_post_event_modifier_effects(self) -> list[str]:
        summaries: list[str] = []
        for effect in self.run_modifier_engine.event_post_resolution_effects(self.run_modifiers):
            summaries.extend(self._apply_modifier_effect(effect))
        return summaries

    def _begin_combat_modifier_runtime(self) -> None:
        combat_flags = self._default_combat_runtime_flags()
        combat_active_ids: list[str] = []

        for record in self.run_modifiers:
            duration_type = record.get("duration_type", "permanent")
            remaining = record.get("remaining")
            record["active_in_current_combat"] = False
            if duration_type == "combat" and isinstance(remaining, int) and remaining > 0:
                combat_active_ids.append(record["id"])
                record["remaining"] = max(0, remaining - 1)
                record["active_in_current_combat"] = True

        combat_flags["active_modifier_ids"] = combat_active_ids
        self.modifier_runtime_flags["combat"] = combat_flags
        self._refresh_combat_passive_flags()

    def _end_combat_modifier_runtime(self) -> None:
        for record in self.run_modifiers:
            record["active_in_current_combat"] = False
        self.modifier_runtime_flags["combat"] = self._default_combat_runtime_flags()
        self._cleanup_expired_run_modifiers()

    def _refresh_combat_passive_flags(self) -> None:
        combat_flags = self._combat_runtime_flags()
        combat_flags["first_block_penalty_remaining"] = sum(
            effect["value"]
            for effect in self.run_modifier_engine.get_effects(self._active_modifiers_for_combat(), "passive")
            if effect["type"] == "reduce_first_block_each_combat"
        )

    def _active_modifiers_for_combat(self) -> list[dict[str, Any]]:
        combat_flags = self._combat_runtime_flags()
        active_ids = set(combat_flags.get("active_modifier_ids", []))
        active_records: list[dict[str, Any]] = []
        for record in self.run_modifiers:
            duration_type = record.get("duration_type", "permanent")
            if duration_type == "combat":
                if record["id"] in active_ids:
                    active_records.append(record)
                continue
            active_records.append(record)
        return active_records

    def _lock_in_turn_history(self) -> None:
        combat_flags = self._combat_runtime_flags()
        combat_flags["last_turn_attack_played"] = bool(combat_flags.get("current_turn_attack_played", False))

    def _start_player_turn_runtime(self) -> None:
        combat_flags = self._combat_runtime_flags()
        combat_flags["cards_played_this_turn"] = 0
        combat_flags["current_turn_attack_played"] = False
        combat_flags["triggered_modifier_ids_this_turn"] = []
        pending_energy = int(combat_flags.get("pending_energy_next_turn", 0))
        if pending_energy > 0:
            self.player.gain_energy(pending_energy)
        combat_flags["pending_energy_next_turn"] = 0
        self._apply_combat_modifier_effects("on_turn_start")

    def _combat_card_context(self, card: Any) -> dict[str, int]:
        card_data = card.to_dict()
        combat_flags = self._combat_runtime_flags()
        passive_effects = self.run_modifier_engine.get_effects(self._active_modifiers_for_combat(), "passive")

        cost = card_data["cost"] + self.player.next_card_cost_delta
        if combat_flags.get("cards_played_this_combat", 0) == 0 and any(
            effect["type"] == "first_card_free" for effect in passive_effects
        ):
            cost = 0
        elif combat_flags.get("cards_played_this_combat", 0) >= 1:
            cost += sum(
                effect["value"]
                for effect in passive_effects
                if effect["type"] == "cost_surcharge_after_first_card"
            )

        damage_bonus = self.player.next_attack_bonus
        if card_data["type"] == "attack" and combat_flags.get("last_turn_attack_played", False):
            damage_bonus = sum(
                effect["value"]
                for effect in passive_effects
                if effect["type"] == "bonus_attack_damage_if_attacked_last_turn"
            ) + damage_bonus

        repeat_count = sum(1 for effect in passive_effects if effect["type"] == "repeat_first_card")
        if combat_flags.get("cards_played_this_combat", 0) > 0:
            repeat_count = 0

        return {
            "cost": max(0, cost),
            "damage_bonus": damage_bonus,
            "repeat_count": repeat_count,
            "block_penalty": combat_flags.get("first_block_penalty_remaining", 0),
        }

    def _combat_card_snapshot(self, card: Any) -> dict[str, Any]:
        card_data = card.to_dict()
        play_context = self._combat_card_context(card)
        card_data["base_cost"] = card_data["cost"]
        card_data["cost"] = play_context["cost"]

        adjusted_effects: list[dict[str, Any]] = []
        remaining_block_penalty = play_context["block_penalty"]
        for effect in card_data.get("effects", []):
            adjusted_effect = dict(effect)
            if effect["type"] in {"damage", "lifesteal_damage"} and play_context["damage_bonus"] > 0:
                adjusted_effect["value"] = effect["value"] + play_context["damage_bonus"]
            elif effect["type"] == "multi_damage" and play_context["damage_bonus"] > 0:
                adjusted_effect["value"] = effect["value"] + play_context["damage_bonus"]
            elif effect["type"] == "block" and remaining_block_penalty > 0:
                reduction = min(remaining_block_penalty, effect["value"])
                adjusted_effect["value"] = max(0, effect["value"] - reduction)
                remaining_block_penalty -= reduction
            adjusted_effects.append(adjusted_effect)
        card_data["effects"] = adjusted_effects
        return card_data

    def _record_combat_card_play(self, card: Any, resolution: dict[str, Any]) -> None:
        combat_flags = self._combat_runtime_flags()
        combat_flags["cards_played_this_combat"] += 1
        combat_flags["cards_played_this_turn"] += 1
        if getattr(card, "type", "") == "attack":
            combat_flags["current_turn_attack_played"] = True
        applied_block_penalty = resolution.get("block_penalty_applied", 0)
        combat_flags["first_block_penalty_remaining"] = max(
            0,
            combat_flags.get("first_block_penalty_remaining", 0) - applied_block_penalty,
        )

    def _advance_floor_modifier_effects(self, node_floor: int) -> None:
        last_floor = self.modifier_runtime_flags.get("last_floor_status_tick", 0)
        if not isinstance(last_floor, int):
            last_floor = 0
        if node_floor <= last_floor:
            return

        floor_steps = node_floor - last_floor
        for _ in range(floor_steps):
            for effect in self.run_modifier_engine.get_effects(self.run_modifiers, "passive"):
                if effect["type"] == "lose_credits_each_floor":
                    self._apply_modifier_effect(effect)
            for record in self.run_modifiers:
                if record.get("duration_type") == "floor" and isinstance(record.get("remaining"), int):
                    record["remaining"] = max(0, record["remaining"] - 1)

        self.modifier_runtime_flags["last_floor_status_tick"] = node_floor
        self._cleanup_expired_run_modifiers()

    def _cleanup_expired_run_modifiers(self) -> None:
        combat_active_ids = set(self._combat_runtime_flags().get("active_modifier_ids", []))
        self.run_modifiers = [
            record
            for record in self.run_modifiers
            if record.get("duration_type", "permanent") == "permanent"
            or record.get("id") in combat_active_ids
            or not isinstance(record.get("remaining"), int)
            or record.get("remaining", 0) > 0
        ]

    def _resolve_random_modifier_option(self, effect: dict[str, Any]) -> dict[str, Any]:
        combat_flags = self._combat_runtime_flags()
        turn_number = 0 if self.combat_manager is None else self.combat_manager.turn_manager.turn_number
        rng = self._state_rng(
            f"modifier_random:{effect.get('modifier_id', 'status')}:{self.current_state}:{turn_number}:{combat_flags.get('cards_played_this_combat', 0)}"
        )
        total_weight = sum(option["weight"] for option in effect["options"])
        roll = rng.randint(1, total_weight)
        running_total = 0
        for option in effect["options"]:
            running_total += option["weight"]
            if roll <= running_total:
                return option
        return effect["options"][-1]

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
                offer["price"] = self._shop_price("card", self._card_shop_base_price(offer["card_id"]), shop_node_id)
            elif offer["type"] == "relic":
                rarity = str(offer["relic"].get("rarity", "common")).lower()
                base_price = SHOP_RELIC_PRICES_BY_RARITY.get(rarity, SHOP_RELIC_PRICES_BY_RARITY["common"])
                offer["price"] = self._shop_price("relic", base_price, shop_node_id)
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

    def _event_selection_context(self) -> dict[str, Any]:
        route_floor_count = 0 if self.map_graph is None else int(self.map_graph.get("route_floor_count", 0))
        return {
            "current_floor": self._current_node_floor(),
            "current_global_floor": self._current_global_floor(),
            "current_map_index": self._current_map_index(),
            "current_map_id": self._current_map_id(),
            "route_floor_count": route_floor_count,
            "current_act": self._current_map_index(),
            "current_hp": self.player.current_hp,
            "max_hp": self.player.max_hp,
            "credits": self.player.credits,
            "deck_size": len(self.player.deck_manager.starting_deck),
            "status_count": len(self.run_modifiers),
            "active_modifier_ids": [record["id"] for record in self.run_modifiers],
            "event_history": copy.deepcopy(self.event_history),
            "character_id": self._active_character_id(),
        }

    def _event_has_available_choice(self, event_definition: dict[str, Any]) -> bool:
        character_ids = event_definition.get("character_ids", [])
        active_character_id = self._active_character_id()
        if character_ids and active_character_id not in character_ids:
            return False
        return any(self._event_choice_availability(choice)[0] for choice in event_definition["choices"])

    def _record_event_history(self, event_definition: dict[str, Any]) -> None:
        self.event_history.append(
            {
                "event_id": event_definition["id"],
                "primary_tag": event_definition["primary_tag"],
                "floor": self._current_global_floor(),
            }
        )

    def _seen_event_ids(self) -> list[str]:
        seen_ids: list[str] = []
        for entry in self.event_history:
            event_id = entry.get("event_id")
            if isinstance(event_id, str) and event_id not in seen_ids:
                seen_ids.append(event_id)
        return seen_ids

    def _generate_event_state(self) -> dict[str, Any]:
        candidate_events = [
            event_definition
            for event_definition in self.event_library.list_events()
            if self._event_has_available_choice(event_definition)
        ]
        if not candidate_events:
            raise ValueError("No event definitions are currently available.")

        context = self._event_selection_context()
        rng = self._state_rng("event_pick")
        chosen_event = self.event_selector.choose_event(candidate_events, context, rng)
        self._record_event_history(chosen_event)
        return {
            "event_id": chosen_event["id"],
            "title": chosen_event["title"],
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
        if encounter_type not in {"combat", "elite", "boss"}:
            return None

        sections: dict[str, Any] = {}
        section_order: list[str] = []

        if encounter_type == "boss":
            sections["relic_offer"] = self._build_relic_reward_section(
                choice_count=BOSS_RELIC_CHOICE_COUNT,
                source_type="boss_reward",
                title="Boss Relic",
                description="Choose one relic to strengthen the next map.",
                can_skip=False,
            )
            section_order.append("relic_offer")
            sections["card_offer"] = self._build_card_reward_section(choice_count=BOSS_REWARD_CARD_CHOICE_COUNT)
            section_order.append("card_offer")
        elif encounter_type == "combat":
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
            sections["relic_offer"] = self._build_relic_reward_section(
                choice_count=ELITE_RELIC_CHOICE_COUNT,
                source_type="elite_reward",
                title="Elite Relic",
                description="Choose one relic, then continue with the rest of the spoils.",
                can_skip=False,
            )
            section_order.append("relic_offer")
            reward_type = self._regular_reward_type()
            if reward_type == "purge_offer":
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

        return {
            "encounter_type": encounter_type,
            "credits_granted": credits_granted,
            "section_order": section_order,
            "sections": sections,
            "intro_message": (
                "Checkpoint reward ready."
                if encounter_type == "boss"
                else f"Reward ready. +{credits_granted} credits earned."
            ),
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

    def _build_card_reward_section(self, choice_count: int | None = None) -> dict[str, Any]:
        if choice_count is None:
            bonus_choices = self.run_modifier_engine.reward_card_choice_bonus(self.run_modifiers)
            choice_count = REWARD_CARD_CHOICE_COUNT + bonus_choices
        chosen_ids = self._select_offer_card_ids(
            slot_count=choice_count,
            label="card_reward",
            seen_card_ids=[],
            sold_out_card_ids=[],
            current_unsold_ids=[],
        )
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

    def _build_relic_reward_section(
        self,
        *,
        choice_count: int,
        source_type: str,
        title: str,
        description: str,
        can_skip: bool,
    ) -> dict[str, Any]:
        chosen_ids = self._select_offer_relic_ids(
            slot_count=choice_count,
            label=f"reward_relic:{source_type}",
            source_type=source_type,
            seen_relic_ids=[],
            sold_out_relic_ids=[],
            current_unsold_ids=[],
        )
        if not chosen_ids:
            return {
                "type": "relic_offer",
                "title": title,
                "description": description,
                "source_type": source_type,
                "options": [],
                "selected_option_id": None,
                "resolved": True,
                "resolution": {
                    "type": "locked",
                    "summary": "No relics remain in this pool.",
                },
                "can_skip": False,
                "seen_relic_ids": [],
            }
        return {
            "type": "relic_offer",
            "title": title,
            "description": description,
            "source_type": source_type,
            "options": [
                {
                    "option_id": relic_id,
                    "relic_id": relic_id,
                    "relic": copy.deepcopy(self.run_modifier_library.get_modifier(relic_id)),
                    "label": f"Take {self.run_modifier_library.get_modifier(relic_id)['name']}",
                }
                for relic_id in chosen_ids
            ],
            "selected_option_id": None,
            "resolved": False,
            "resolution": None,
            "can_skip": can_skip,
            "seen_relic_ids": list(chosen_ids),
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
        chosen_card_ids = self._shop_card_selection(
            slot_count=SHOP_CARD_OFFER_COUNT,
            seen_card_ids=[],
            sold_out_card_ids=[],
            current_unsold_ids=[],
            label="shop_inventory:0",
        )
        chosen_relic_ids = self._select_offer_relic_ids(
            slot_count=SHOP_RELIC_OFFER_COUNT,
            label="shop_relic_inventory:0",
            source_type="shop",
            seen_relic_ids=[],
            sold_out_relic_ids=[],
            current_unsold_ids=[],
        )
        inventory = [self._shop_card_offer(card_id, shop_node_id=shop_node_id) for card_id in chosen_card_ids]
        inventory.extend(self._shop_relic_offer(relic_id, shop_node_id=shop_node_id) for relic_id in chosen_relic_ids)
        if SHOP_HEAL_ENABLED:
            inventory.append(self._shop_heal_offer(shop_node_id=shop_node_id))
        inventory.append(self._shop_purge_offer(shop_node_id=shop_node_id, purge_locked=purge_locked))
        return {
            "shop_node_id": shop_node_id,
            "inventory": inventory,
            "selected_offer_id": None,
            "selected_purge_index": None,
            "reroll_count": 0,
            "seen_card_ids": list(chosen_card_ids),
            "seen_relic_ids": list(chosen_relic_ids),
        }

    def _shop_card_offer(self, card_id: str, shop_node_id: str | None = None) -> dict[str, Any]:
        card = self.card_library.create_card(card_id)
        return {
            "offer_id": f"card:{card_id}",
            "type": "card",
            "card_id": card_id,
            "card": card.to_dict(),
            "label": card.name,
            "price": self._shop_price("card", self._card_shop_base_price(card_id), shop_node_id=shop_node_id),
            "sold_out": False,
        }

    def _shop_relic_offer(self, relic_id: str, shop_node_id: str | None = None) -> dict[str, Any]:
        relic = copy.deepcopy(self.run_modifier_library.get_modifier(relic_id))
        rarity = str(relic.get("rarity", "common")).lower()
        base_price = SHOP_RELIC_PRICES_BY_RARITY.get(rarity, SHOP_RELIC_PRICES_BY_RARITY["common"])
        return {
            "offer_id": f"relic:{relic_id}",
            "type": "relic",
            "relic_id": relic_id,
            "relic": relic,
            "label": relic["name"],
            "price": self._shop_price("relic", base_price, shop_node_id=shop_node_id),
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
            return False, "No unsold card or relic offers remain to reroll."

        unsold_card_count = len(
            [index for index in unsold_offer_indices if self.active_shop["inventory"][index]["type"] == "card"]
        )
        unsold_relic_count = len(
            [index for index in unsold_offer_indices if self.active_shop["inventory"][index]["type"] == "relic"]
        )
        if unsold_card_count > 0 and len(self._shop_replacement_card_ids()) < unsold_card_count:
            return False, "No replacement card offers remain for this shop."
        if unsold_relic_count > 0 and len(self._shop_replacement_relic_ids()) < unsold_relic_count:
            return False, "No replacement relic offers remain for this shop."

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
            if offer["type"] in {"card", "relic"} and not offer.get("sold_out")
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

    def _shop_sold_out_relic_ids(self) -> list[str]:
        if self.active_shop is None:
            return []
        return [
            offer["relic_id"]
            for offer in self.active_shop["inventory"]
            if offer["type"] == "relic" and offer.get("sold_out")
        ]

    def _shop_current_unsold_relic_ids(self) -> list[str]:
        if self.active_shop is None:
            return []
        return [
            offer["relic_id"]
            for offer in self.active_shop["inventory"]
            if offer["type"] == "relic" and not offer.get("sold_out")
        ]

    def _shop_replacement_card_ids(self) -> list[str]:
        sold_out_set = set(self._shop_sold_out_card_ids())
        current_unsold_set = set(self._shop_current_unsold_card_ids())
        return self._select_offer_card_ids(
            slot_count=SHOP_CARD_OFFER_COUNT,
            label=f"shop_replacement_probe:{self.active_shop.get('reroll_count', 0) if self.active_shop is not None else 0}",
            seen_card_ids=self.active_shop.get("seen_card_ids", []) if self.active_shop is not None else [],
            sold_out_card_ids=list(sold_out_set),
            current_unsold_ids=list(current_unsold_set),
        )

    def _shop_replacement_relic_ids(self) -> list[str]:
        sold_out_set = set(self._shop_sold_out_relic_ids())
        current_unsold_set = set(self._shop_current_unsold_relic_ids())
        return self._select_offer_relic_ids(
            slot_count=SHOP_RELIC_OFFER_COUNT,
            label=f"shop_relic_replacement_probe:{self.active_shop.get('reroll_count', 0) if self.active_shop is not None else 0}",
            source_type="shop",
            seen_relic_ids=self.active_shop.get("seen_relic_ids", []) if self.active_shop is not None else [],
            sold_out_relic_ids=list(sold_out_set),
            current_unsold_ids=list(current_unsold_set),
        )

    def _apply_shop_reroll(self) -> None:
        if self.active_shop is None:
            raise ValueError("Shop reroll requested without an active shop.")

        unsold_card_indices = [
            index for index in self._rerollable_shop_offer_indices() if self.active_shop["inventory"][index]["type"] == "card"
        ]
        unsold_relic_indices = [
            index for index in self._rerollable_shop_offer_indices() if self.active_shop["inventory"][index]["type"] == "relic"
        ]
        new_card_ids = self._shop_card_selection(
            slot_count=len(unsold_card_indices),
            seen_card_ids=self.active_shop.get("seen_card_ids", []),
            sold_out_card_ids=self._shop_sold_out_card_ids(),
            current_unsold_ids=self._shop_current_unsold_card_ids(),
            label=f"shop_inventory:{self.active_shop.get('reroll_count', 0) + 1}",
        )
        new_relic_ids = self._select_offer_relic_ids(
            slot_count=len(unsold_relic_indices),
            label=f"shop_relic_inventory:{self.active_shop.get('reroll_count', 0) + 1}",
            source_type="shop",
            seen_relic_ids=self.active_shop.get("seen_relic_ids", []),
            sold_out_relic_ids=self._shop_sold_out_relic_ids(),
            current_unsold_ids=self._shop_current_unsold_relic_ids(),
        )
        if unsold_card_indices and len(new_card_ids) < len(unsold_card_indices):
            raise ValueError("No replacement card offers remain for this shop.")
        if unsold_relic_indices and len(new_relic_ids) < len(unsold_relic_indices):
            raise ValueError("No replacement relic offers remain for this shop.")

        for offer_index, card_id in zip(unsold_card_indices, new_card_ids):
            self.active_shop["inventory"][offer_index] = self._shop_card_offer(
                card_id,
                shop_node_id=self.active_shop.get("shop_node_id"),
            )
        for offer_index, relic_id in zip(unsold_relic_indices, new_relic_ids):
            self.active_shop["inventory"][offer_index] = self._shop_relic_offer(
                relic_id,
                shop_node_id=self.active_shop.get("shop_node_id"),
            )

        self.active_shop["reroll_count"] = int(self.active_shop.get("reroll_count", 0)) + 1
        seen_card_ids = set(self.active_shop.get("seen_card_ids", []))
        seen_card_ids.update(new_card_ids)
        self.active_shop["seen_card_ids"] = sorted(seen_card_ids)
        seen_relic_ids = set(self.active_shop.get("seen_relic_ids", []))
        seen_relic_ids.update(new_relic_ids)
        self.active_shop["seen_relic_ids"] = sorted(seen_relic_ids)
        self._refresh_shop_prices()

    def _shop_card_selection(
        self,
        slot_count: int,
        seen_card_ids: list[str],
        sold_out_card_ids: list[str],
        current_unsold_ids: list[str],
        label: str,
    ) -> list[str]:
        return self._select_offer_card_ids(
            slot_count=slot_count,
            label=label,
            seen_card_ids=seen_card_ids,
            sold_out_card_ids=sold_out_card_ids,
            current_unsold_ids=current_unsold_ids,
        )

    def _character_offer_cards(self) -> list[Any]:
        character_id = self._active_character_id()
        if character_id is None:
            return []
        return self.card_library.find_cards(owners=[character_id], exclude_types=["status"])

    def _shared_offer_cards(self) -> list[Any]:
        return self.card_library.find_cards(owners=["shared"], exclude_types=["status"])

    def _select_offer_card_ids(
        self,
        *,
        slot_count: int,
        label: str,
        seen_card_ids: list[str],
        sold_out_card_ids: list[str],
        current_unsold_ids: list[str],
    ) -> list[str]:
        if slot_count <= 0:
            return []

        rng = self._state_rng(label)
        seen_set = set(seen_card_ids)
        sold_out_set = set(sold_out_card_ids)
        current_unsold_set = set(current_unsold_ids)
        blocked_ids = sold_out_set | current_unsold_set
        chosen_ids: list[str] = []
        power_taken = False

        character_cards = self._character_offer_cards()
        shared_cards = self._shared_offer_cards()

        def candidate_ids(cards: list[Any], *, card_type: str | None = None, fresh_only: bool = False) -> list[str]:
            ids = [
                card.id
                for card in cards
                if card.id not in blocked_ids
                and card.id not in chosen_ids
                and (card_type is None or card.type == card_type)
                and (card_type is not None or True)
                and (not fresh_only or card.id not in seen_set)
            ]
            rng.shuffle(ids)
            return ids

        def pull(card_ids: list[str], count: int, *, allow_power: bool = True) -> None:
            nonlocal power_taken
            for card_id in card_ids:
                if len(chosen_ids) >= slot_count or count <= 0:
                    break
                card = self.card_library.get_card(card_id)
                if card.type == "power":
                    if power_taken or not allow_power:
                        continue
                    power_taken = True
                chosen_ids.append(card_id)
                count -= 1

        required_character_count = min(2, slot_count)
        pull(candidate_ids([card for card in character_cards if card.type != "power"], fresh_only=True), required_character_count, allow_power=False)
        if len(chosen_ids) < required_character_count:
            pull(candidate_ids([card for card in character_cards if card.type != "power"]), required_character_count - len(chosen_ids), allow_power=False)
        if len(chosen_ids) < required_character_count:
            pull(candidate_ids([card for card in character_cards if card.type == "power"], fresh_only=True), required_character_count - len(chosen_ids))
        if len(chosen_ids) < required_character_count:
            pull(candidate_ids([card for card in character_cards if card.type == "power"]), required_character_count - len(chosen_ids))

        if len(chosen_ids) < slot_count:
            allow_power_pick = not power_taken and bool(candidate_ids([card for card in character_cards if card.type == "power"]))
            if allow_power_pick and rng.random() < 0.35:
                pull(candidate_ids([card for card in character_cards if card.type == "power"], fresh_only=True), 1)
                if len(chosen_ids) < slot_count and not power_taken:
                    pull(candidate_ids([card for card in character_cards if card.type == "power"]), 1)

        mixed_non_power = [card for card in shared_cards if card.type != "power"] + [card for card in character_cards if card.type != "power"]
        pull(candidate_ids(mixed_non_power, fresh_only=True), slot_count - len(chosen_ids), allow_power=False)
        if len(chosen_ids) < slot_count:
            pull(candidate_ids(mixed_non_power), slot_count - len(chosen_ids), allow_power=False)

        if len(chosen_ids) < slot_count and not power_taken:
            pull(candidate_ids([card for card in character_cards if card.type == "power"], fresh_only=True), slot_count - len(chosen_ids))
        if len(chosen_ids) < slot_count and not power_taken:
            pull(candidate_ids([card for card in character_cards if card.type == "power"]), slot_count - len(chosen_ids))

        fallback_cards = shared_cards + character_cards
        pull(candidate_ids([card for card in fallback_cards if card.type != "power"]), slot_count - len(chosen_ids), allow_power=False)
        if len(chosen_ids) < slot_count and not power_taken:
            pull(candidate_ids([card for card in fallback_cards if card.type == "power"]), slot_count - len(chosen_ids))

        return chosen_ids[:slot_count]

    def _select_offer_relic_ids(
        self,
        *,
        slot_count: int,
        label: str,
        source_type: str,
        seen_relic_ids: list[str],
        sold_out_relic_ids: list[str],
        current_unsold_ids: list[str],
    ) -> list[str]:
        if slot_count <= 0:
            return []

        rng = self._state_rng(label)
        seen_set = set(seen_relic_ids)
        blocked_ids = set(sold_out_relic_ids) | set(current_unsold_ids) | set(self._owned_relic_ids())

        def pool_ids(*, fresh_only: bool) -> list[str]:
            return [
                modifier["id"]
                for modifier in self.run_modifier_library.list_modifiers(source_type=source_type)
                if modifier["type"] == "relic"
                and modifier["id"] not in blocked_ids
                and (not fresh_only or modifier["id"] not in seen_set)
            ]

        chosen_ids: list[str] = []
        for fresh_only in (True, False):
            candidate_ids = [modifier_id for modifier_id in pool_ids(fresh_only=fresh_only) if modifier_id not in chosen_ids]
            if not candidate_ids:
                continue
            chosen_ids.extend(
                self.run_modifier_engine.pick_weighted_modifier_ids(
                    rng,
                    self.run_modifiers,
                    source_type=source_type,
                    rarity_profile="positive",
                    allow_types=["relic"],
                    pool_ids=candidate_ids,
                    count=slot_count - len(chosen_ids),
                )
            )
            if len(chosen_ids) >= slot_count:
                break
        return chosen_ids[:slot_count]

    def _owned_relic_ids(self) -> list[str]:
        relic_ids: list[str] = []
        for record in self.run_modifiers:
            modifier = self.run_modifier_library.get_modifier(record["id"])
            if modifier["type"] == "relic":
                relic_ids.append(modifier["id"])
        return relic_ids

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

    def _card_shop_base_price(self, card_id: str) -> int:
        override = CARD_SHOP_PRICE_OVERRIDES.get(card_id)
        if isinstance(override, int) and override >= 0:
            return override
        return self.card_library.get_card(card_id).shop_price

    def _state_rng(self, label: str) -> random.Random:
        if self.run_seed is None:
            raise ValueError("Run seed is not available for deterministic state generation.")
        map_key = "root"
        if self.campaign_state is not None:
            map_key = f"{self.campaign_state.get('map_index', 0)}:{self.campaign_state.get('map_id', 'root')}"
        node_id = self.selected_node_id or "root"
        return random.Random(f"{self.run_seed}:{map_key}:{node_id}:{label}")

    def _assign_route_encounters(self, map_graph: dict[str, Any] | None) -> None:
        if map_graph is None:
            return
        if map_graph["map_id"] == "outskirts":
            for node in map_graph["nodes"].values():
                if node.node_type not in {"combat", "elite"}:
                    continue
                encounter = self.outskirts_content.choose_encounter(
                    "outskirts",
                    node_type=node.node_type,
                    route_floor=node.route_floor,
                    rng=self._state_rng(f"outskirts_encounter:{map_graph['map_id']}:{node.node_id}"),
                )
                node.encounter_hook_id = encounter["id"]
                node.enemy_ids = list(encounter["enemy_ids"])
            return
        faction_id = self.grayspine_content.faction_for_map(map_graph["map_id"])
        if faction_id is None:
            return
        for node in map_graph["nodes"].values():
            if node.node_type not in {"combat", "elite"}:
                continue
            encounter = self.grayspine_content.choose_encounter(
                faction_id,
                node_type=node.node_type,
                route_floor=node.route_floor,
                rng=self._state_rng(f"grayspine_encounter:{map_graph['map_id']}:{node.node_id}"),
            )
            node.encounter_hook_id = encounter["id"]
            node.enemy_ids = list(encounter["enemy_ids"])

    def _snapshot_grayspine_intel(self) -> dict[str, Any] | None:
        campaign = self.campaign_state
        if not isinstance(campaign, dict):
            return None
        if int(campaign.get("map_index", 0)) < 3:
            return None
        lore = self.grayspine_content.lore()
        factions = self.grayspine_content.list_factions()
        current_map_id = campaign.get("map_id")
        current_faction_id = None
        if isinstance(current_map_id, str):
            current_faction_id = self.grayspine_content.faction_for_map(current_map_id)
        unlocked = self.current_state == "victory" and int(campaign.get("map_index", 0)) >= 3
        for faction in factions:
            faction["bosses"] = self.grayspine_content.get_bosses_for_faction(faction["id"])
        return {
            "available": True,
            "city": lore["city"],
            "factions": factions,
            "selected_faction_id": current_faction_id or campaign.get("branch_faction"),
            "route_map_id": current_map_id,
            "spine_core": {
                **lore["spine_core"],
                "unlocked": unlocked,
                "display_summary": self.grayspine_content.spine_core_summary(unlocked=unlocked),
            },
        }

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
            "resources": self.player.snapshot_resources(),
            "character_id": self.player.character_id,
            "strength": self.player.strength,
            "weak": self.player.weak,
            "vulnerable": self.player.vulnerable,
            "next_card_cost_delta": self.player.next_card_cost_delta,
            "next_attack_bonus": self.player.next_attack_bonus,
            "active_powers": [card.id for card in self.player.active_powers],
            "temporary_combat_cards": [card.id for card in self.player.temporary_combat_cards],
            "first_card_played": self.player.first_card_played,
            "first_attack_played": self.player.first_attack_played,
            "combat_statuses": self.player.combat_status_snapshot(),
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
            "map_id": self.map_graph["map_id"],
            "map_name": self.map_graph["map_name"],
            "map_index": self.map_graph["map_index"],
            "theme_tag": self.map_graph["theme_tag"],
            "branch_faction": self.map_graph.get("branch_faction"),
            "route_floor_count": self.map_graph["route_floor_count"],
            "global_floor_offset": self.map_graph["global_floor_offset"],
            "selected_boss_id": self.map_graph["selected_boss_id"],
            "selected_boss": copy.deepcopy(self.map_graph["selected_boss"]),
            "canvas_width": self.map_graph["canvas_width"],
            "canvas_height": self.map_graph["canvas_height"],
            "nodes": {node_id: node.to_dict() for node_id, node in self.map_graph["nodes"].items()},
            "start_nodes": list(self.map_graph["start_nodes"]),
            "boss_node_id": self.map_graph["boss_node_id"],
            "available_node_ids": list(self.available_node_ids),
            "visited_node_ids": list(self.visited_node_ids),
            "selected_node_id": self.selected_node_id,
        }

    def _serialize_campaign(self) -> dict[str, Any] | None:
        return None if self.campaign_state is None else copy.deepcopy(self.campaign_state)

    def _serialize_combat(self) -> dict[str, Any] | None:
        if self.combat_manager is None:
            return None

        return {
            "combat_active": self.combat_manager.combat_active,
            "turn_number": self.combat_manager.turn_manager.turn_number,
            "turn_owner": self.combat_manager.turn_manager.turn_owner,
            "event_log": list(self.combat_manager.event_log),
            "active_bark": None if self.combat_manager.active_bark is None else dict(self.combat_manager.active_bark),
            "bark_runtime": {
                "nonce": getattr(self.combat_manager, "_bark_nonce", 0),
                "cooldown_remaining": getattr(self.combat_manager, "_bark_cooldown_remaining", 0),
                "speaker_counts": dict(getattr(self.combat_manager, "_speaker_bark_counts", {})),
                "defeated_enemy_ids": sorted(getattr(self.combat_manager, "_defeated_enemy_ids", set())),
            },
            "enemies": [
                {
                    "id": enemy.id,
                    "current_hp": enemy.current_hp,
                    "block": enemy.block,
                    "current_intent": enemy.current_intent,
                    "strength": enemy.strength,
                    "weak": enemy.weak,
                    "vulnerable": enemy.vulnerable,
                    "runtime": enemy.snapshot_runtime(),
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

    def _serialize_character_select(self) -> dict[str, Any] | None:
        if self.active_character_select is None:
            return None
        return {"selected_character_id": self.active_character_select.get("selected_character_id")}

    def _restore_player(
        self,
        player_data: dict[str, Any],
        deck_data: dict[str, Any],
        run_seed: int,
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

        character_id = self._restore_character_id(player_data.get("character_id"))
        if character_id is None:
            raise ValueError("Player save data is missing character_id.")
        credits = player_data.get("credits", PLAYER_STARTING_CREDITS)
        resources = self._restore_player_resources(player_data.get("resources"))
        player = Player(
            max_hp=player_data["max_hp"],
            current_hp=player_data["current_hp"],
            max_energy=player_data["max_energy"],
            energy=player_data["energy"],
            block=player_data["block"],
            draw_per_turn=player_data["draw_per_turn"],
            credits=credits,
            healing_multiplier=float(player_data.get("healing_multiplier", 1.0)),
            resources=resources,
            character_id=character_id,
            strength=int(player_data.get("strength", 0)),
            weak=int(player_data.get("weak", 0)),
            vulnerable=int(player_data.get("vulnerable", 0)),
            next_card_cost_delta=int(player_data.get("next_card_cost_delta", 0)),
            next_attack_bonus=int(player_data.get("next_attack_bonus", 0)),
        )
        player.attach_deck(deck_manager)
        player.active_powers = self._cards_from_ids(player_data.get("active_powers", []))
        player.temporary_combat_cards = self._cards_from_ids(player_data.get("temporary_combat_cards", []))
        player.first_card_played = bool(player_data.get("first_card_played", False))
        player.first_attack_played = bool(player_data.get("first_attack_played", False))
        combat_statuses = player_data.get("combat_statuses", {})
        if isinstance(combat_statuses, dict):
            player.infect = max(0, int(combat_statuses.get("infect", 0)))
            player.burn = max(0, int(combat_statuses.get("burn", 0)))
            player.bleed = max(0, int(combat_statuses.get("bleed", 0)))
            player.marked = max(0, int(combat_statuses.get("marked", 0)))
            player.marked_turns = max(0, int(combat_statuses.get("marked_turns", 0)))
            player.suppressed = max(0, min(3, int(combat_statuses.get("suppressed", 0))))
            player.nullified = bool(combat_statuses.get("nullified", False))
        self.character_id = character_id
        return player

    def _restore_player_resources(
        self,
        resources_data: Any,
    ) -> dict[str, dict[str, int]]:
        if resources_data in (None, {}):
            return {}
        if not isinstance(resources_data, dict):
            raise ValueError("Player resources save data must be a dictionary.")

        restored: dict[str, dict[str, int]] = {}
        for resource_id, resource_state in resources_data.items():
            if not isinstance(resource_id, str) or not resource_id:
                raise ValueError("Saved player resource ids must be non-empty strings.")
            if not isinstance(resource_state, dict):
                raise ValueError("Saved player resource states must be dictionaries.")

            current = resource_state.get("current")
            maximum = resource_state.get("max")
            if not isinstance(current, int) or current < 0:
                raise ValueError("Saved player resource current values must be non-negative integers.")
            if not isinstance(maximum, int) or maximum < 0:
                raise ValueError("Saved player resource max values must be non-negative integers.")
            restored[resource_id] = {
                "current": current,
                "max": maximum,
            }
        return restored

    def _restore_character_id(self, character_id: Any) -> str | None:
        if character_id is None:
            return None
        if not isinstance(character_id, str):
            raise ValueError("Saved character ids must be strings.")
        return self.character_library.get_character(character_id)["id"]

    def _restore_character_select(
        self,
        character_select_data: Any,
        fallback_character_id: str | None,
    ) -> dict[str, Any]:
        if character_select_data in (None, {}):
            return {"selected_character_id": fallback_character_id}
        if not isinstance(character_select_data, dict):
            raise ValueError("Character select save data must be a dictionary.")
        selected_character_id = character_select_data.get("selected_character_id", fallback_character_id)
        return {"selected_character_id": self._restore_character_id(selected_character_id)}

    def _restore_map(self, map_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(map_data, dict):
            raise ValueError("Save data is missing map details.")

        required_keys = {
            "map_id",
            "map_name",
            "map_index",
            "theme_tag",
            "branch_faction",
            "route_floor_count",
            "global_floor_offset",
            "selected_boss_id",
            "selected_boss",
            "canvas_width",
            "canvas_height",
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
                map_id=node_data["map_id"],
                route_floor=node_data["route_floor"],
                campaign_floor=node_data["campaign_floor"],
                node_tier=node_data["node_tier"],
                render_x=node_data["render_x"],
                render_y=node_data["render_y"],
                encounter_hook_id=node_data.get("encounter_hook_id"),
                boss_slot_id=node_data.get("boss_slot_id"),
                enemy_ids=list(node_data.get("enemy_ids", [])),
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
            "map_id": map_data["map_id"],
            "map_name": map_data["map_name"],
            "map_index": map_data["map_index"],
            "theme_tag": map_data["theme_tag"],
            "branch_faction": map_data.get("branch_faction"),
            "route_floor_count": map_data["route_floor_count"],
            "global_floor_offset": map_data["global_floor_offset"],
            "selected_boss_id": map_data["selected_boss_id"],
            "selected_boss": copy.deepcopy(map_data["selected_boss"]),
            "canvas_width": map_data["canvas_width"],
            "canvas_height": map_data["canvas_height"],
            "nodes": nodes,
            "start_nodes": list(map_data["start_nodes"]),
            "boss_node_id": map_data["boss_node_id"],
        }

    def _restore_campaign(self, campaign_data: Any) -> dict[str, Any]:
        if not isinstance(campaign_data, dict):
            raise ValueError("Save data is missing campaign details.")

        required_keys = {
            "map_index",
            "map_id",
            "map_name",
            "route_floor_index",
            "route_floor_count",
            "branch_faction",
            "selected_boss_id",
            "global_route_floor_index",
        }
        if not required_keys.issubset(campaign_data):
            raise ValueError("Campaign save data is incomplete.")

        map_definition = self.campaign_library.get_map_definition(campaign_data["map_id"])
        map_name = campaign_data["map_name"]
        if not isinstance(map_name, str) or not map_name:
            raise ValueError("Campaign save data map_name must be a non-empty string.")

        map_index = campaign_data["map_index"]
        route_floor_index = campaign_data["route_floor_index"]
        route_floor_count = campaign_data["route_floor_count"]
        global_route_floor_index = campaign_data["global_route_floor_index"]
        selected_boss_id = campaign_data["selected_boss_id"]
        branch_faction = campaign_data.get("branch_faction")

        if not isinstance(map_index, int) or map_index < 1:
            raise ValueError("Campaign save data map_index must be a positive integer.")
        if not isinstance(route_floor_index, int) or route_floor_index < 0:
            raise ValueError("Campaign save data route_floor_index must be non-negative.")
        if not isinstance(route_floor_count, int) or route_floor_count < 1:
            raise ValueError("Campaign save data route_floor_count must be positive.")
        if not isinstance(global_route_floor_index, int) or global_route_floor_index < 0:
            raise ValueError("Campaign save data global_route_floor_index must be non-negative.")
        if not isinstance(selected_boss_id, str) or not selected_boss_id:
            raise ValueError("Campaign save data selected_boss_id must be a non-empty string.")
        if branch_faction is not None and (
            not isinstance(branch_faction, str) or branch_faction != map_definition.get("branch_faction")
        ):
            if map_definition.get("branch_faction") is not None:
                raise ValueError("Campaign save data branch_faction does not match the current map.")
            branch_faction = None

        return {
            "map_index": map_index,
            "map_id": map_definition["id"],
            "map_name": map_name,
            "route_floor_index": route_floor_index,
            "route_floor_count": route_floor_count,
            "branch_faction": branch_faction,
            "selected_boss_id": selected_boss_id,
            "global_route_floor_index": global_route_floor_index,
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
            enemy.strength = int(enemy_data.get("strength", 0))
            enemy.weak = int(enemy_data.get("weak", 0))
            enemy.vulnerable = int(enemy_data.get("vulnerable", 0))
            enemy.restore_runtime(enemy_data.get("runtime", {}))
            enemies.append(enemy)

        combat_manager = CombatManager(
            player=self.player,
            enemies=enemies,
            rng=self._state_rng(f"combat_restore:{self.selected_node_id or 'root'}"),
            bark_source=self.grayspine_content,
        )
        combat_manager.set_card_factory(self.card_library.create_card)
        combat_manager.set_enemy_factory(self.enemy_library.create_enemy)
        combat_manager.combat_active = bool(combat_data["combat_active"])
        combat_manager.turn_manager.turn_number = combat_data["turn_number"]
        combat_manager.turn_manager.turn_owner = combat_data["turn_owner"]
        combat_manager.event_log = list(combat_data["event_log"])
        active_bark = combat_data.get("active_bark")
        combat_manager.active_bark = dict(active_bark) if isinstance(active_bark, dict) else None
        bark_runtime = combat_data.get("bark_runtime", {})
        if isinstance(bark_runtime, dict):
            combat_manager._bark_nonce = int(bark_runtime.get("nonce", 0))
            combat_manager._bark_cooldown_remaining = int(bark_runtime.get("cooldown_remaining", 0))
            speaker_counts = bark_runtime.get("speaker_counts", {})
            if isinstance(speaker_counts, dict):
                combat_manager._speaker_bark_counts = {
                    str(key): int(value)
                    for key, value in speaker_counts.items()
                    if isinstance(key, str) and isinstance(value, int)
                }
            defeated_ids = bark_runtime.get("defeated_enemy_ids", [])
            if isinstance(defeated_ids, list):
                combat_manager._defeated_enemy_ids = {
                    str(enemy_id)
                    for enemy_id in defeated_ids
                    if isinstance(enemy_id, str)
                }
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

        seen_relic_ids = restored_shop.get("seen_relic_ids")
        if seen_relic_ids is None:
            seen_relic_ids = [
                offer["relic_id"]
                for offer in restored_shop["inventory"]
                if isinstance(offer, dict) and offer.get("type") == "relic" and isinstance(offer.get("relic_id"), str)
            ]
        if not isinstance(seen_relic_ids, list) or not all(isinstance(relic_id, str) for relic_id in seen_relic_ids):
            raise ValueError("Shop seen_relic_ids must be a list of relic ids.")

        restored_shop["reroll_count"] = reroll_count
        restored_shop["seen_card_ids"] = list(dict.fromkeys(seen_card_ids))
        restored_shop["seen_relic_ids"] = list(dict.fromkeys(seen_relic_ids))
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
            duration_type = modifier_record.get("duration_type")
            remaining = modifier_record.get("remaining")
            active_in_current_combat = modifier_record.get("active_in_current_combat", False)
            stack_count = modifier_record.get("stack_count", 1)
            stack_intensity = modifier_record.get("stack_intensity", 1)
            if not isinstance(modifier_id, str) or not modifier_id:
                raise ValueError("Saved run modifier ids must be non-empty strings.")
            if not isinstance(source, str) or not source:
                raise ValueError("Saved run modifier sources must be non-empty strings.")
            if not isinstance(active_in_current_combat, bool):
                raise ValueError("Saved run modifier active_in_current_combat flags must be booleans.")
            if not isinstance(stack_count, int) or stack_count <= 0:
                raise ValueError("Saved run modifier stack_count must be a positive integer.")
            if not isinstance(stack_intensity, int) or stack_intensity <= 0:
                raise ValueError("Saved run modifier stack_intensity must be a positive integer.")
            if modifier_id in seen_ids:
                raise ValueError(f"Saved run modifiers contain a duplicate id: {modifier_id}")
            modifier = self.run_modifier_library.get_modifier(modifier_id)
            normalized_duration_type = modifier["duration"]["type"] if duration_type is None else duration_type
            if normalized_duration_type not in {"permanent", "combat", "floor"}:
                raise ValueError(f"Saved run modifier {modifier_id} has unsupported duration_type: {normalized_duration_type}")
            if normalized_duration_type == "permanent":
                normalized_remaining = None
            else:
                default_remaining = modifier["duration"]["value"]
                normalized_remaining = default_remaining if remaining is None else remaining
                if not isinstance(normalized_remaining, int) or normalized_remaining < 0:
                    raise ValueError(f"Saved run modifier {modifier_id} remaining duration must be a non-negative integer.")
            seen_ids.add(modifier_id)
            restored.append(
                {
                    "id": modifier_id,
                    "source": source,
                    "source_detail": source_detail if isinstance(source_detail, str) else None,
                    "duration_type": normalized_duration_type,
                    "remaining": normalized_remaining,
                    "active_in_current_combat": active_in_current_combat,
                    "stack_count": stack_count,
                    "stack_intensity": stack_intensity,
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
        last_floor_status_tick = modifier_runtime_flags.get("last_floor_status_tick", 0)
        combat_flags = modifier_runtime_flags.get("combat", {})

        if not isinstance(clean_slate_used, bool):
            raise ValueError("clean_slate_used must be a boolean.")
        if not isinstance(ghost_warranty_used_shops, list) or not all(isinstance(value, str) for value in ghost_warranty_used_shops):
            raise ValueError("ghost_warranty_used_shops must be a list of node ids.")
        if not isinstance(debt_spike_used_shops, list) or not all(isinstance(value, str) for value in debt_spike_used_shops):
            raise ValueError("debt_spike_used_shops must be a list of node ids.")
        if not isinstance(last_floor_status_tick, int) or last_floor_status_tick < 0:
            raise ValueError("last_floor_status_tick must be a non-negative integer.")
        if not isinstance(combat_flags, dict):
            raise ValueError("combat runtime flags must be stored as a dictionary.")

        restored["clean_slate_used"] = clean_slate_used
        restored["ghost_warranty_used_shops"] = list(dict.fromkeys(ghost_warranty_used_shops))
        restored["debt_spike_used_shops"] = list(dict.fromkeys(debt_spike_used_shops))
        restored["last_floor_status_tick"] = last_floor_status_tick
        restored["combat"] = self._default_combat_runtime_flags()
        restored["combat"]["active_modifier_ids"] = [
            modifier_id
            for modifier_id in combat_flags.get("active_modifier_ids", [])
            if isinstance(modifier_id, str)
        ]
        for key in {
            "cards_played_this_combat",
            "cards_played_this_turn",
            "first_block_penalty_remaining",
        }:
            value = combat_flags.get(key, restored["combat"][key])
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a non-negative integer.")
            restored["combat"][key] = value
        for key in {"current_turn_attack_played", "last_turn_attack_played"}:
            value = combat_flags.get(key, restored["combat"][key])
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be a boolean.")
            restored["combat"][key] = value
        return restored

    def _restore_event_history(
        self,
        event_history_data: Any,
        seen_event_ids: Any,
    ) -> list[dict[str, Any]]:
        if event_history_data not in (None, []):
            if not isinstance(event_history_data, list):
                raise ValueError("Saved event_history must be a list.")
            restored_history: list[dict[str, Any]] = []
            for entry in event_history_data:
                if not isinstance(entry, dict):
                    raise ValueError("Saved event history entries must be dictionaries.")
                event_id = entry.get("event_id")
                primary_tag = entry.get("primary_tag")
                floor = entry.get("floor", 0)
                if not isinstance(event_id, str) or not event_id:
                    raise ValueError("Saved event history event_id values must be non-empty strings.")
                event_definition = self.event_library.get_event(event_id)
                normalized_primary_tag = (
                    primary_tag
                    if isinstance(primary_tag, str) and primary_tag in event_definition["tags"]
                    else event_definition["primary_tag"]
                )
                if not isinstance(floor, int) or floor < 0:
                    raise ValueError("Saved event history floors must be non-negative integers.")
                restored_history.append(
                    {
                        "event_id": event_id,
                        "primary_tag": normalized_primary_tag,
                        "floor": floor,
                    }
                )
            return restored_history

        if seen_event_ids in (None, []):
            return []
        if not isinstance(seen_event_ids, list) or not all(isinstance(event_id, str) for event_id in seen_event_ids):
            raise ValueError("Saved seen_event_ids must be a list of event ids.")
        restored_from_seen: list[dict[str, Any]] = []
        for index, event_id in enumerate(seen_event_ids):
            event_definition = self.event_library.get_event(event_id)
            restored_from_seen.append(
                {
                    "event_id": event_id,
                    "primary_tag": event_definition["primary_tag"],
                    "floor": index,
                }
            )
        return restored_from_seen

    def _cards_from_ids(self, card_ids: list[str]) -> list[Any]:
        if not isinstance(card_ids, list) or not all(isinstance(card_id, str) for card_id in card_ids):
            raise ValueError("Saved deck piles must be lists of card ids.")
        return [self.card_library.create_card(card_id) for card_id in card_ids]


def simulate_state_manager() -> dict[str, Any]:
    manager = StateManager()
    select_snapshot = manager.start_new_run(seed=29)
    manager.select_character("operator")
    draft_snapshot = manager.confirm_character_selection()
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
        "start_state": select_snapshot["current_state"],
        "selected_character": draft_snapshot["character"]["id"],
        "post_draft_state": start_snapshot["current_state"],
        "event_title": event_snapshot["event"]["title"],
        "post_event_state": "map",
        "reward_sections": len(reward_snapshot["reward"]["sections"]),
        "post_reward_state": "map",
        "shop_offers": len(shop_snapshot["shop"]["inventory"]),
        "credits": manager.player.credits,
    }
