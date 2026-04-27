from __future__ import annotations

import random
from typing import Any

from combat.action_resolver import ActionResolver
from combat.turn_manager import TurnManager
from config import (
    BARK_BOSS_DURATION_SECONDS,
    BARK_COOLDOWN_ACTIONS,
    BARK_GENERIC_DURATION_SECONDS,
    BARK_MAX_BOSS_PER_SPEAKER,
    BARK_MAX_GENERIC_PER_SPEAKER,
)
from core.grayspine_content_library import GrayspineContentLibrary

DIRECT_DAMAGE_TYPES = {"damage", "multi_damage", "lifesteal_damage"}
FEEDBACK_EVENT_LIMIT = 48


class CombatManager:
    def __init__(
        self,
        player: Any,
        enemies: list[Any],
        rng: random.Random | None = None,
        bark_source: Any | None = None,
    ) -> None:
        self.player = player
        self.enemies = enemies
        self.rng = rng or random.Random()
        self.action_resolver = ActionResolver()
        self.turn_manager = TurnManager()
        self.combat_active = False
        self.event_log: list[dict[str, Any]] = []
        self.active_bark: dict[str, Any] | None = None
        self._bark_source = bark_source or GrayspineContentLibrary()
        self._bark_nonce = 0
        self._bark_cooldown_remaining = 0
        self._speaker_bark_counts: dict[str, int] = {}
        self._enemy_factory: Any | None = None
        self._event_sink: Any | None = None
        self._defeated_enemy_ids: set[str] = set()
        self._player_cards_played_this_turn = 0
        self._player_cards_played_last_turn = 0
        self._player_block_cards_this_turn = 0
        self._last_player_card_type: str | None = None
        self._enemy_attacks_this_round: dict[str, int] = {}
        self._blackwire_command_net_used = False
        self._feedback_events: list[dict[str, Any]] = []
        self._feedback_sequence = 0

    def start_combat(self) -> dict[str, Any]:
        if self.player.deck_manager is None:
            raise ValueError("Combat requires a player with an attached deck manager.")
        if not self.enemies:
            raise ValueError("Combat requires at least one enemy.")

        self.turn_manager = TurnManager()
        self.player.start_combat()
        self.active_bark = None
        self._bark_nonce = 0
        self._bark_cooldown_remaining = 0
        self._speaker_bark_counts = {}
        self._defeated_enemy_ids = set()
        self._player_cards_played_this_turn = 0
        self._player_cards_played_last_turn = 0
        self._player_block_cards_this_turn = 0
        self._last_player_card_type = None
        self._enemy_attacks_this_round = {}
        self._blackwire_command_net_used = False
        self._feedback_events = []
        self._feedback_sequence = 0
        for enemy in self.enemies:
            enemy.reset_for_combat()
            self._apply_enemy_spawn_rules(enemy)
            enemy.choose_intent(self)

        self.combat_active = True
        self.event_log.clear()
        self._emit_encounter_start_bark()
        opening_turn = self._start_player_turn()
        return {"combat_active": self.combat_active, "opening_turn": opening_turn}

    def end_turn(self) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot end a turn outside of active combat.")

        begin_result = self.begin_enemy_phase()
        if not begin_result.get("combat_active", False):
            return {"combat_active": self.combat_active, "enemy_results": []}

        enemy_results: list[dict[str, Any]] = []
        for enemy_ref in begin_result.get("pending_enemy_ids", []):
            step_result = self.resolve_enemy_phase_step(enemy_ref)
            enemy_results.append(step_result)
            if not self.combat_active:
                return {"combat_active": self.combat_active, "enemy_results": enemy_results}

        next_turn = self.finalize_enemy_phase()
        return {
            "combat_active": self.combat_active,
            "enemy_results": enemy_results,
            "next_turn": next_turn,
        }

    def begin_enemy_phase(self) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot begin an enemy phase outside of active combat.")

        self.turn_manager.end_player_turn(self.player)
        self._player_cards_played_last_turn = self._player_cards_played_this_turn
        self._player_cards_played_this_turn = 0
        if self._player_block_cards_this_turn >= 2:
            for enemy in self._living_enemies():
                if enemy.id == "toll_reeve":
                    enemy.adjust_strength(1)
                    break
        self._player_block_cards_this_turn = 0
        self._enemy_attacks_this_round = {}
        turn_end_logs = self._resolve_hook_sources(
            self.player.active_powers,
            "turn_end",
            {"played_card": None, "first_card_this_turn": False},
        )
        if turn_end_logs:
            self.event_log.extend(turn_end_logs)
        self._resolve_player_end_of_turn_statuses()
        if not self.player.is_alive():
            self.combat_active = False
            return {"combat_active": self.combat_active, "pending_enemy_ids": []}

        pending_enemy_ids = [self._enemy_ref(enemy) for enemy in list(self._living_enemies())]
        if not pending_enemy_ids:
            self.combat_active = False
        return {
            "combat_active": self.combat_active,
            "pending_enemy_ids": pending_enemy_ids,
        }

    def resolve_enemy_phase_step(self, enemy_ref: str) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot resolve enemy turns outside of active combat.")

        enemy = self._enemy_from_ref(enemy_ref)
        if enemy is None or not enemy.is_alive():
            return {"enemy_id": enemy_ref, "skipped": True, "resolution": None}

        self.turn_manager.start_enemy_turn(enemy)
        self._resolve_enemy_turn_start_effects(enemy)
        if not enemy.is_alive():
            self._handle_enemy_defeat(enemy)
            if not self._living_enemies():
                self.combat_active = False
            return {"enemy_id": enemy_ref, "skipped": True, "resolution": None}

        intent = enemy.current_intent or enemy.choose_intent(self)
        resolution = enemy.execute_intent(self.action_resolver, self.player, combat_manager=self)
        self.event_log.append(self._enemy_event_entry(enemy=enemy, intent=intent, resolution=resolution))
        self._resolve_enemy_end_of_turn_effects(enemy)
        if not self.player.is_alive() or not self._living_enemies():
            self.combat_active = False
        return {
            "enemy_id": enemy_ref,
            "skipped": False,
            "intent": intent,
            "resolution": resolution,
        }

    def finalize_enemy_phase(self) -> dict[str, Any] | None:
        if not self.combat_active:
            return None
        if not self._living_enemies():
            self.combat_active = False
            return None

        for enemy in self._living_enemies():
            enemy.choose_intent(self)

        return self._start_player_turn()

    def resolve_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot resolve actions outside of active combat.")
        if not isinstance(action, dict):
            raise ValueError("Combat actions must be dictionaries.")

        card = action.get("card")
        resolved_card = action.get("resolved_card")
        explicit_target = action.get("target")
        energy_cost = action.get("cost")
        damage_bonus = action.get("damage_bonus", 0)
        repeat_count = action.get("repeat_count", 0)
        remaining_block_penalty = action.get("block_penalty", 0)

        if card is None:
            raise ValueError("Combat actions require a card instance.")
        if resolved_card is not None and not isinstance(resolved_card, dict):
            raise ValueError("resolved_card must be a dictionary when provided.")
        if energy_cost is None:
            energy_cost = card.cost
        if not isinstance(energy_cost, int) or energy_cost < 0:
            raise ValueError("Combat action costs must be non-negative integers.")
        if not isinstance(damage_bonus, int):
            raise ValueError("Combat action damage_bonus must be an integer.")
        if not isinstance(repeat_count, int) or repeat_count < 0:
            raise ValueError("Combat action repeat_count must be a non-negative integer.")
        if not isinstance(remaining_block_penalty, int) or remaining_block_penalty < 0:
            raise ValueError("Combat action block_penalty must be a non-negative integer.")

        self.player.spend_energy(energy_cost)
        first_card_this_turn = not self.player.first_card_played
        resolutions: list[dict[str, Any]] = []
        logged_resolutions: list[dict[str, Any]] = []

        resolved_effects = card.effects if resolved_card is None else list(resolved_card.get("effects", card.effects))
        resolved_name = card.name if resolved_card is None else str(resolved_card.get("name", card.name))
        resolved_type = card.type if resolved_card is None else str(resolved_card.get("type", card.type))

        for resolve_index in range(1 + repeat_count):
            for effect in resolved_effects:
                effect_results, remaining_block_penalty = self._resolve_card_effect(
                    effect=effect,
                    card=card,
                    explicit_target=explicit_target,
                    damage_bonus=damage_bonus,
                    block_penalty=remaining_block_penalty,
                    echoed=resolve_index > 0,
                )
                resolutions.extend(effect_results)
                logged_resolutions.extend(effect_results)

        moved_card = self.player.deck_manager.remove_card_from_hand(card)
        moved_card.clear_temporary_cost_override()
        if resolved_type == "power":
            self.player.add_active_power(moved_card)
        elif card.has_keyword("exhaust"):
            self.player.deck_manager.exhaust_pile.append(moved_card)
            self._notify_card_exhausted(moved_card)
        else:
            self.player.deck_manager.discard_pile.append(moved_card)

        hook_context = {
            "played_card": card,
            "first_card_this_turn": first_card_this_turn,
            "played_card_type": resolved_type,
        }
        hook_logs = self._resolve_hook_sources(self._hook_sources_for_play(card), "after_card_played", hook_context)
        if resolved_type == "attack":
            hook_logs.extend(self._resolve_hook_sources(self._hook_sources_for_play(card), "after_attack_played", hook_context))

        self.player.consume_next_card_cost_delta()
        if resolved_type == "attack":
            self.player.consume_next_attack_bonus()

        self.player.first_card_played = True
        if resolved_type == "attack":
            self.player.first_attack_played = True
        if self._last_player_card_type == resolved_type:
            for enemy in self._living_enemies():
                if enemy.id == "spine_warden_null":
                    enemy.adjust_strength(1)
                    break
        self._last_player_card_type = resolved_type

        event_entry = {
            "type": "card",
            "source": "player",
            "label": resolved_name,
            "card_id": card.id,
            "card_type": resolved_type,
            "resolutions": logged_resolutions,
            "summary": self._summarize_event(label=resolved_name, resolutions=logged_resolutions, hook_logs=hook_logs),
        }
        self.event_log.append(event_entry)
        self.event_log.extend(hook_logs)
        self._player_cards_played_this_turn += 1
        self._advance_bark_cooldown()

        if not self._living_enemies():
            self.combat_active = False

        return {
            "resolutions": resolutions,
            "block_penalty_applied": action.get("block_penalty", 0) - remaining_block_penalty,
            "repeat_count": repeat_count,
        }

    def draw_cards(self, target: Any, amount: int) -> list[Any]:
        if amount <= 0:
            return []
        if not hasattr(target, "deck_manager") or target.deck_manager is None:
            raise ValueError("Combat draw effects require a deck manager.")
        drawn_cards = target.deck_manager.draw_cards(amount)
        self._process_drawn_cards(target, drawn_cards)
        return drawn_cards

    def apply_damage(
        self,
        source: Any,
        target: Any,
        amount: int,
        *,
        emit_event: bool = True,
        feedback_context: dict[str, Any] | None = None,
    ) -> int:
        target_statuses_before = self._combat_status_ids(target)
        target_block_before = max(0, int(getattr(target, "block", 0) or 0))
        adjusted = self._adjust_attack_amount(source, target, amount)
        if getattr(source, "faction_id", None) == "blackwire_directorate" and hasattr(target, "marked"):
            adjusted += getattr(target, "marked", 0) * 2
            if hasattr(target, "consume_marked_for_hit"):
                target.consume_marked_for_hit(1)
        if hasattr(source, "get_status"):
            adjusted += source.get_status("momentum")
        applied = target.take_damage(adjusted)
        bleed_bonus = self._apply_bleed_bonus(target)
        total_applied = applied + bleed_bonus
        blocked_amount = min(target_block_before, adjusted)
        if blocked_amount > 0:
            block_feedback = {
                **self._feedback_source_payload(source),
                **self._feedback_target_payload(target),
                "type": "block_spent",
                "amount": blocked_amount,
                "reason": "damage_absorbed",
            }
            if feedback_context:
                block_feedback.update(feedback_context)
            self.emit_feedback_event(block_feedback)
            shield_feedback = {
                **self._feedback_target_payload(target),
                "type": "shield_flash",
                "amount": blocked_amount,
                "reason": "damage_absorbed",
            }
            if feedback_context:
                shield_feedback.update(feedback_context)
            self.emit_feedback_event(shield_feedback)
        if total_applied > 0 or blocked_amount > 0:
            damage_feedback = {
                **self._feedback_source_payload(source),
                **self._feedback_target_payload(target),
                "type": "damage_applied",
                "amount": total_applied,
                "hp_damage": total_applied,
                "incoming_damage": adjusted,
                "blocked_amount": blocked_amount,
                "bleed_bonus": bleed_bonus,
            }
            if feedback_context:
                damage_feedback.update(feedback_context)
            self.emit_feedback_event(damage_feedback)
        if hasattr(source, "get_status") and source.get_status("momentum") > 0:
            source.clear_status("momentum")
        if (
            emit_event
            and source is self.player
            and target in self.enemies
            and total_applied > 0
        ):
            self._emit_runtime_event(
                {
                    "hook": "on_attack_hit",
                    "source_card": getattr(source, "id", None),
                    "target": target.id,
                    "target_id": target.id,
                    "damage_dealt": total_applied,
                    "damage": total_applied,
                    "target_statuses": target_statuses_before,
                    "target_status_ids": target_statuses_before,
                }
            )
        if hasattr(target, "check_phase_transition"):
            phase_rule = target.check_phase_transition()
            if phase_rule is not None:
                self._handle_enemy_phase_change(target, phase_rule)
            if target.is_alive() and not target.low_hp_bark_fired() and target.current_hp <= max(1, target.max_hp // 3):
                target.mark_low_hp_bark_fired()
                self._maybe_emit_bark(target, "low_hp")
        if hasattr(target, "is_alive") and not target.is_alive():
            self._handle_enemy_defeat(target)
        return total_applied

    def get_state(self) -> dict[str, Any]:
        return {
            "combat_active": self.combat_active,
            "turn_number": self.turn_manager.turn_number,
            "turn_owner": self.turn_manager.turn_owner,
            "player": self.player.get_state(),
            "enemies": [
                {
                    **enemy.get_state(),
                    "enemy_ref": self._enemy_ref(enemy),
                }
                for enemy in self.enemies
            ],
            "living_enemy_ids": [enemy.id for enemy in self._living_enemies()],
            "event_log": list(self.event_log),
            "active_bark": None if self.active_bark is None else dict(self.active_bark),
            "feedback_events": list(self._feedback_events),
        }

    def get_enemy(self, enemy_id: str) -> Any | None:
        for enemy in self.enemies:
            if enemy.id == enemy_id and enemy.is_alive():
                return enemy
        return None

    def set_enemy_factory(self, factory: Any) -> None:
        self._enemy_factory = factory

    def set_event_sink(self, sink: Any) -> None:
        self._event_sink = sink

    def emit_feedback_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise ValueError("Feedback events must be dictionaries.")
        self._feedback_sequence += 1
        payload = {**event, "sequence": self._feedback_sequence}
        self._feedback_events.append(payload)
        if len(self._feedback_events) > FEEDBACK_EVENT_LIMIT:
            self._feedback_events = self._feedback_events[-FEEDBACK_EVENT_LIMIT:]
        return payload

    def grant_block(
        self,
        target: Any,
        amount: int,
        *,
        source: Any | None = None,
        feedback_context: dict[str, Any] | None = None,
    ) -> int:
        applied = target.gain_block(amount)
        if applied > 0:
            block_feedback = {
                **self._feedback_source_payload(source),
                **self._feedback_target_payload(target),
                "type": "block_gained",
                "amount": applied,
            }
            if feedback_context:
                block_feedback.update(feedback_context)
            self.emit_feedback_event(block_feedback)
            if target is self.player:
                self._emit_runtime_event(
                    {
                        "hook": "on_block_gained",
                        "amount": applied,
                        "source": None if source is None else getattr(source, "id", "player"),
                        "source_card": None if feedback_context is None else feedback_context.get("source_card_id"),
                        "card_type": None if feedback_context is None else feedback_context.get("source_card_type"),
                    }
                )
            shield_feedback = {
                **self._feedback_target_payload(target),
                "type": "shield_flash",
                "amount": applied,
                "reason": "block_gain",
            }
            if feedback_context:
                shield_feedback.update(feedback_context)
            self.emit_feedback_event(shield_feedback)
        return applied

    def restore_health(
        self,
        target: Any,
        amount: int,
        *,
        source: Any | None = None,
        feedback_context: dict[str, Any] | None = None,
    ) -> int:
        applied = target.heal(amount)
        if applied > 0:
            heal_feedback = {
                **self._feedback_source_payload(source),
                **self._feedback_target_payload(target),
                "type": "heal_applied",
                "amount": applied,
            }
            if feedback_context:
                heal_feedback.update(feedback_context)
            self.emit_feedback_event(heal_feedback)
        return applied

    def lose_hp_with_feedback(
        self,
        target: Any,
        amount: int,
        *,
        source: Any | None = None,
        feedback_context: dict[str, Any] | None = None,
    ) -> int:
        applied = target.lose_hp(amount)
        if applied > 0:
            damage_feedback = {
                **self._feedback_source_payload(source),
                **self._feedback_target_payload(target),
                "type": "damage_applied",
                "amount": applied,
                "hp_damage": applied,
                "incoming_damage": applied,
                "blocked_amount": 0,
                "bleed_bonus": 0,
                "ignore_block": True,
            }
            if feedback_context:
                damage_feedback.update(feedback_context)
            self.emit_feedback_event(damage_feedback)
        return applied

    def _feedback_source_payload(self, source: Any | None) -> dict[str, Any]:
        if source is None:
            return {}
        if source is self.player:
            return {
                "source_id": "player",
                "source_name": getattr(self.player, "character_id", "player"),
                "source_type": "player",
            }
        if source in self.enemies:
            return {
                "source_id": getattr(source, "id", "enemy"),
                "source_name": getattr(source, "name", "Enemy"),
                "source_type": "enemy",
                "source_enemy_ref": self._enemy_ref(source),
            }
        return {
            "source_id": getattr(source, "id", getattr(source, "name", "unknown")),
            "source_name": getattr(source, "name", getattr(source, "id", "Unknown")),
            "source_type": "unknown",
        }

    def _feedback_target_payload(self, target: Any | None) -> dict[str, Any]:
        if target is self.player:
            return {"target_id": "player", "target_name": "Player", "target_type": "player"}
        if target in self.enemies:
            return {
                "target_id": getattr(target, "id", "enemy"),
                "target_name": getattr(target, "name", "Enemy"),
                "target_type": "enemy",
                "target_enemy_ref": self._enemy_ref(target),
            }
        if target is None:
            return {}
        return {
            "target_id": getattr(target, "id", getattr(target, "name", "unknown")),
            "target_name": getattr(target, "name", getattr(target, "id", "Unknown")),
            "target_type": "unknown",
        }

    def _enemy_ref(self, enemy: Any) -> str:
        try:
            slot_index = self.enemies.index(enemy)
        except ValueError:
            slot_index = -1
        return self._enemy_ref_at_index(slot_index, enemy)

    def _enemy_ref_at_index(self, slot_index: int, enemy: Any) -> str:
        enemy_id = getattr(enemy, "id", "enemy")
        return f"{enemy_id}#{max(0, int(slot_index))}"

    def _enemy_from_ref(self, enemy_ref: str) -> Any | None:
        if isinstance(enemy_ref, str):
            enemy_id, separator, slot_index = enemy_ref.rpartition("#")
            if separator:
                try:
                    index = int(slot_index)
                except ValueError:
                    index = -1
                if 0 <= index < len(self.enemies):
                    enemy = self.enemies[index]
                    if self._enemy_ref_at_index(index, enemy) == enemy_ref:
                        return enemy
                if enemy_id:
                    return next((enemy for enemy in self.enemies if enemy.id == enemy_id), None)
        return next((enemy for enemy in self.enemies if enemy.id == enemy_ref), None)

    def _emit_runtime_event(self, event: dict[str, Any]) -> None:
        if self._event_sink is None:
            return
        self._event_sink(dict(event))

    def _combat_status_ids(self, target: Any) -> list[str]:
        status_ids: list[str] = []
        for status_id in ("weak", "vulnerable", "infect", "burn", "bleed", "marked", "suppressed", "nullified"):
            if status_id == "nullified":
                if bool(getattr(target, "nullified", False)):
                    status_ids.append(status_id)
                continue
            value = getattr(target, status_id, None)
            if isinstance(value, int) and value > 0:
                status_ids.append(status_id)
                continue
            if hasattr(target, "get_status") and int(target.get_status(status_id)) > 0:
                status_ids.append(status_id)
        return status_ids

    def _notify_status_applied(self, hook_name: str, target: Any, status_id: str, amount: int) -> None:
        if amount <= 0:
            return
        self._emit_runtime_event(
            {
                "hook": hook_name,
                "target": getattr(target, "id", "player"),
                "target_id": getattr(target, "id", "player"),
                "status_id": status_id,
                "amount": amount,
                "target_statuses": self._combat_status_ids(target),
                "target_status_ids": self._combat_status_ids(target),
            }
        )

    def _notify_card_exhausted(self, card: Any) -> None:
        self._emit_runtime_event(
            {
                "hook": "on_card_exhausted",
                "card_id": getattr(card, "id", None),
                "card_type": getattr(card, "type", None),
                "source": getattr(card, "id", None),
            }
        )

    def _apply_status_to_enemy(self, target: Any, status_id: str, amount: int) -> int:
        if amount <= 0:
            return 0
        key = str(status_id).strip().lower()
        if key == "weak":
            applied = target.apply_weak(amount)
        elif key == "vulnerable":
            applied = target.apply_vulnerable(amount)
        elif key == "bleed":
            applied = target.apply_bleed(amount) if hasattr(target, "apply_bleed") else target.apply_status("bleed", amount)
        elif key == "infect":
            applied = target.apply_infect(amount) if hasattr(target, "apply_infect") else target.apply_status("infect", amount)
        elif key == "burn":
            applied = target.apply_burn(amount) if hasattr(target, "apply_burn") else target.apply_status("burn", amount)
        elif key == "marked":
            applied = target.apply_marked(amount) if hasattr(target, "apply_marked") else target.apply_status("marked", amount)
        elif key == "suppressed":
            applied = target.apply_suppressed(amount) if hasattr(target, "apply_suppressed") else target.apply_status("suppressed", amount)
        elif key == "nullified":
            if hasattr(target, "apply_nullified"):
                target.apply_nullified()
                applied = amount
            else:
                applied = target.apply_status("nullified", amount)
        else:
            raise ValueError(f"Unsupported enemy combat status: {status_id}")
        self._notify_status_applied("on_enemy_status_applied", target, key, amount)
        return applied

    def _apply_status_to_player(self, target: Any, status_id: str, amount: int) -> int:
        if amount <= 0:
            return 0
        key = str(status_id).strip().lower()
        if key == "weak":
            applied = target.apply_weak(amount)
        elif key == "vulnerable":
            applied = target.apply_vulnerable(amount)
        elif key == "infect":
            applied = target.apply_infect(amount)
        elif key == "burn":
            applied = target.apply_burn(amount)
        elif key == "bleed":
            applied = target.apply_bleed(amount)
        elif key == "marked":
            applied = target.apply_marked(amount)
        elif key == "suppressed":
            applied = target.apply_suppressed(amount)
        elif key == "nullified":
            target.apply_nullified()
            applied = amount
        else:
            raise ValueError(f"Unsupported player combat status: {status_id}")
        self._notify_status_applied("on_player_status_applied", target, key, amount)
        return applied

    def _add_status_cards_to_player(self, card_id: str, count: int, pile: str = "discard") -> int:
        added = 0
        for _ in range(count):
            status_card = self._create_status_card(card_id)
            self.player.add_temporary_combat_card(status_card)
            if pile == "draw":
                self.player.deck_manager.add_to_draw_pile(status_card)
            else:
                self.player.deck_manager.add_to_discard(status_card)
                self._emit_runtime_event(
                    {
                        "hook": "on_status_card_added_to_discard",
                        "card_id": getattr(status_card, "id", None),
                        "card_type": getattr(status_card, "type", None),
                    }
                )
            added += 1
        return added

    def living_enemy_count(self) -> int:
        return len(self._living_enemies())

    def any_ally_missing_hp(self, source_enemy: Any) -> bool:
        return any(
            enemy.is_alive() and enemy.current_hp < enemy.max_hp
            for enemy in self._allies_for(source_enemy)
        )

    def any_ally_debuffed(self, source_enemy: Any) -> bool:
        return any(
            enemy.is_alive() and (enemy.weak > 0 or enemy.vulnerable > 0)
            for enemy in self._allies_for(source_enemy)
        )

    def any_other_ally_present(self, source_enemy: Any) -> bool:
        return any(
            enemy.is_alive() and enemy is not source_enemy
            for enemy in self._allies_for(source_enemy)
        )

    def allies_attacked_this_turn(self, source_enemy: Any) -> int:
        return int(self._enemy_attacks_this_round.get(getattr(source_enemy, "faction_id", ""), 0))

    def ally_id_present(self, source_enemy: Any, ally_id: str) -> bool:
        return any(
            enemy.is_alive() and enemy.id == ally_id and enemy is not source_enemy
            for enemy in self._allies_for(source_enemy)
        )

    def player_cards_played_last_turn(self) -> int:
        return int(self._player_cards_played_last_turn)

    def resolve_enemy_intent(
        self,
        enemy: Any,
        move: dict[str, Any],
        default_target: Any,
        action_resolver: Any,
    ) -> dict[str, Any]:
        move = self._effective_enemy_move(enemy, move)
        target = self._resolve_enemy_target(enemy, move, default_target)
        logged_resolutions: list[dict[str, Any]] = []
        for effect in move.get("effects", []):
            target_override = self._resolve_enemy_effect_target(enemy, effect, target)
            logged_resolutions.extend(
                self._resolve_enemy_effect(enemy, effect, target_override, action_resolver)
            )
        self._apply_enemy_move_aftereffects(enemy, move)
        bark_trigger = move.get("bark_trigger")
        if isinstance(bark_trigger, str):
            self._maybe_emit_bark(enemy, bark_trigger)
        if enemy._intent_category(move) == "attack":
            faction_id = getattr(enemy, "faction_id", "")
            self._enemy_attacks_this_round[faction_id] = self._enemy_attacks_this_round.get(faction_id, 0) + 1
            if faction_id == "cinder_jackals":
                for ally in self._allies_for(enemy):
                    if ally.is_alive() and ally.id == "ashfang_rook" and ally is not enemy:
                        ally.apply_status("momentum", 1)
        self._advance_bark_cooldown()
        return {
            "intent_id": move["id"],
            "target": getattr(target, "id", "player"),
            "resolutions": logged_resolutions,
            "summary": move.get("intent_text", move["id"]),
        }

    def _effective_enemy_move(self, enemy: Any, move: dict[str, Any]) -> dict[str, Any]:
        effective_move = {
            **move,
            "effects": [dict(effect) for effect in move.get("effects", [])],
        }
        move_id = effective_move.get("id")

        if enemy.id == "culture_shepherd" and move_id == "feed_the_vat" and self.ally_id_present(enemy, "sludge_whelp"):
            effective_move["effects"].append({"type": "enemy_heal_ally", "value": 6, "target": "self"})
        elif enemy.id == "failed_saint" and move_id == "burst_graft" and getattr(self.player, "infect", 0) >= 4:
            effective_move["effects"].append({"type": "enemy_trigger_infection_burst", "value": 4, "target": "player"})
        elif enemy.id == "audit_hound" and move_id == "intercept" and self._player_cards_played_last_turn >= 4:
            for effect in effective_move["effects"]:
                if effect.get("type") == "enemy_damage":
                    effect["value"] = int(effect.get("value", 0)) + 2
        elif enemy.id == "chain_brute" and move_id == "follow_through" and self.allies_attacked_this_turn(enemy) >= 1:
            for effect in effective_move["effects"]:
                if effect.get("type") == "enemy_damage":
                    effect["value"] = int(effect.get("value", 0)) + 6
        elif enemy.id == "road_hyena" and move_id == "frenzy":
            if getattr(self.player, "bleed", 0) > 0 or self.player.current_hp <= (self.player.max_hp // 2):
                for effect in effective_move["effects"]:
                    if effect.get("type") == "enemy_damage":
                        effect["value"] = int(effect.get("value", 0)) + 1
        elif enemy.id == "scavver" and move_id == "pack_jab" and self.allies_attacked_this_turn(enemy) >= 1:
            effective_move["effects"].append({"type": "enemy_apply_momentum", "value": 2, "target": "self"})
        elif enemy.id == "scrap_gunner" and move_id == "heavy_round" and len(self._living_enemies()) >= 3:
            for effect in effective_move["effects"]:
                if effect.get("type") == "enemy_damage":
                    effect["value"] = 19
        elif enemy.id == "ashfang_rook" and move_id == "bleed_the_weak":
            if getattr(self.player, "bleed", 0) > 0 or self.player.current_hp <= (self.player.max_hp // 2):
                for effect in effective_move["effects"]:
                    if effect.get("type") == "enemy_damage":
                        effect["value"] = 20
        elif enemy.id == "director_vale" and move_id == "kill_authority" and getattr(self.player, "marked", 0) > 0:
            effective_move["effects"].append({"type": "enemy_apply_suppressed", "value": 2, "target": "player"})
        elif enemy.id == "furnace_hound" and move_id == "boiler_spit":
            effective_move["effects"].append(
                {
                    "type": "enemy_apply_burn",
                    "value": max(0, enemy.get_status("overheat")),
                    "target": "player",
                }
            )
        elif enemy.id == "furnace_hound" and move_id == "redline_charge":
            bonus = max(0, enemy.get_status("overheat")) * 2
            for effect in effective_move["effects"]:
                if effect.get("type") == "enemy_damage":
                    effect["value"] = int(effect.get("value", 0)) + bonus
        elif enemy.id == "miremother_vexa" and move_id == "biomass_collapse" and enemy.get_status("biomass") >= 3:
            effective_move["effects"].append({"type": "enemy_trigger_infection_burst", "value": 1, "target": "player"})

        return effective_move

    def _apply_enemy_move_aftereffects(self, enemy: Any, move: dict[str, Any]) -> None:
        move_id = move.get("id")
        if enemy.id == "furnace_hound" and move_id == "boiler_spit":
            enemy.consume_status("overheat", 1)
        elif enemy.id == "furnace_hound" and move_id == "redline_charge":
            enemy.clear_status("overheat")
        elif enemy.id == "miremother_vexa" and move_id == "biomass_collapse" and enemy.get_status("biomass") >= 3:
            enemy.clear_status("biomass")

    def _resolve_enemy_target(self, enemy: Any, move: dict[str, Any], default_target: Any) -> Any:
        target_kind = move.get("target", "player")
        if target_kind == "player":
            return self.player
        if target_kind == "self":
            return enemy
        allies = [ally for ally in self._allies_for(enemy) if ally.is_alive()]
        if not allies:
            return enemy
        if target_kind in {"most_damaged_ally", "lowest_hp_ally"}:
            return min(allies, key=lambda ally: ally.current_hp / max(1, ally.max_hp))
        if target_kind == "most_debuffed_ally":
            ranked = sorted(
                allies,
                key=lambda ally: (ally.weak + ally.vulnerable, ally.max_hp - ally.current_hp),
                reverse=True,
            )
            return ranked[0]
        return default_target

    def _resolve_enemy_effect_target(self, enemy: Any, effect: dict[str, Any], current_target: Any) -> Any:
        target_kind = effect.get("target")
        if target_kind is None:
            return current_target
        if target_kind == "self":
            return enemy
        if target_kind == "player":
            return self.player
        return current_target

    def _resolve_enemy_effect(
        self,
        enemy: Any,
        effect: dict[str, Any],
        target: Any,
        action_resolver: Any,
    ) -> list[dict[str, Any]]:
        effect_type = effect["type"]
        value = int(effect.get("value", 0))
        results: list[dict[str, Any]] = []

        if effect_type == "enemy_damage":
            hit_count = int(effect.get("count", 1))
            for _ in range(hit_count):
                applied = self.apply_damage(
                    enemy,
                    target,
                    value,
                    feedback_context={"source_intent": getattr(enemy, "current_intent", None)},
                )
                results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_block":
            applied = self.grant_block(
                target,
                value,
                source=enemy,
                feedback_context={"source_intent": getattr(enemy, "current_intent", None)},
            )
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_heal_ally":
            applied = self.restore_health(
                target,
                value,
                source=enemy,
                feedback_context={"source_intent": getattr(enemy, "current_intent", None)},
            )
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_infect":
            applied = self._apply_status_to_player(target, "infect", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_marked":
            applied = self._apply_status_to_player(target, "marked", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_suppressed":
            applied = self._apply_status_to_player(target, "suppressed", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_burn":
            applied = self._apply_status_to_player(target, "burn", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_bleed":
            applied = self._apply_status_to_player(target, "bleed", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_weak":
            applied = self._apply_status_to_player(target, "weak", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_vulnerable":
            applied = self._apply_status_to_player(target, "vulnerable", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_nullified":
            applied = self._apply_status_to_player(target, "nullified", max(1, value))
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_add_status_card":
            count = int(effect.get("count", 1))
            pile = str(effect.get("pile", "discard"))
            card_id = str(effect.get("card_id", ""))
            added = self._add_status_cards_to_player(card_id, count, pile)
            results.append(self._resolution_record(effect_type, count, added, self.player, echoed=False))
            return results

        if effect_type == "enemy_strip_buff":
            if hasattr(target, "strip_enemy_buff"):
                stripped = target.strip_enemy_buff()
                applied = 0 if stripped == "none" else 1
            else:
                applied = 0
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_cleanse_ally":
            applied = target.cleanse_debuffs(value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_summon":
            enemy_id = effect.get("enemy_id")
            summon_count = int(effect.get("count", 1))
            summoned = self._summon_enemies(enemy, enemy_id, summon_count)
            results.append(self._resolution_record(effect_type, summon_count, summoned, enemy, echoed=False))
            return results

        if effect_type == "enemy_gain_strength":
            applied = target.adjust_strength(value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_regenerate":
            applied = target.apply_status("regenerate", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_fortified":
            applied = target.apply_status("fortified", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_momentum":
            applied = target.apply_status("momentum", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_momentum_allies":
            applied = 0
            for ally in self._allies_for(enemy):
                if ally.is_alive():
                    ally.apply_status("momentum", value)
                    applied += 1
            results.append(self._resolution_record(effect_type, value, applied, enemy, echoed=False))
            return results

        if effect_type == "enemy_block_allies":
            applied = 0
            for ally in self._allies_for(enemy):
                if ally.is_alive():
                    self.grant_block(
                        ally,
                        value,
                        source=enemy,
                        feedback_context={"source_intent": getattr(enemy, "current_intent", None)},
                    )
                    applied += 1
            results.append(self._resolution_record(effect_type, value, applied, enemy, echoed=False))
            return results

        if effect_type == "enemy_trigger_infection_burst":
            applied = 0
            if hasattr(target, "infect") and getattr(target, "infect", 0) >= max(1, value):
                self.lose_hp_with_feedback(
                    target,
                    4,
                    source=enemy,
                    feedback_context={"source_intent": getattr(enemy, "current_intent", None), "source_status_id": "infect_burst"},
                )
                target.infect = 3
                applied = 4
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_steal_block":
            stolen = min(max(0, int(value)), max(0, getattr(target, "block", 0)))
            if stolen > 0:
                target.block -= stolen
                self.emit_feedback_event(
                    {
                        **self._feedback_source_payload(enemy),
                        **self._feedback_target_payload(target),
                        "type": "block_spent",
                        "amount": stolen,
                        "reason": "steal_block",
                    }
                )
                self.emit_feedback_event(
                    {
                        **self._feedback_target_payload(target),
                        "type": "shield_flash",
                        "amount": stolen,
                        "reason": "steal_block",
                    }
                )
                self.grant_block(
                    enemy,
                    stolen,
                    source=enemy,
                    feedback_context={"source_intent": getattr(enemy, "current_intent", None)},
                )
            results.append(self._resolution_record(effect_type, value, stolen, target, echoed=False))
            return results

        if effect_type == "enemy_apply_overheat":
            applied = target.apply_status("overheat", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_apply_biomass":
            applied = target.apply_status("biomass", value)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        if effect_type == "enemy_self_destruct":
            applied = 0
            if hasattr(target, "is_alive") and target.is_alive():
                applied = self.lose_hp_with_feedback(
                    target,
                    max(1, getattr(target, "current_hp", 0)),
                    source=enemy,
                    feedback_context={"source_intent": getattr(enemy, "current_intent", None), "source_status_id": "self_destruct"},
                )
                if hasattr(target, "is_alive") and not target.is_alive():
                    self._handle_enemy_defeat(target)
            results.append(self._resolution_record(effect_type, value, applied, target, echoed=False))
            return results

        results.append(self._resolution_record(effect_type, value, 0, target, echoed=False))
        return results

    def _summon_enemies(self, source_enemy: Any, enemy_id: Any, count: int) -> int:
        if self._enemy_factory is None or not isinstance(enemy_id, str) or count <= 0:
            return 0
        living = self.living_enemy_count()
        available_slots = max(0, 5 - living)
        summon_total = min(count, available_slots)
        for _ in range(summon_total):
            summoned = self._enemy_factory(enemy_id)
            summoned.reset_for_combat()
            self._apply_enemy_spawn_rules(summoned)
            if (
                not self._blackwire_command_net_used
                and summoned.id in {"patrol_drone", "sentry_node"}
                and any(ally.is_alive() and ally.id == "director_vale" for ally in self._living_enemies())
            ):
                summoned.apply_status("fortified", 4)
                self._blackwire_command_net_used = True
            self.enemies.append(summoned)
        if summon_total < count:
            self._apply_summon_overflow_fallback(source_enemy)
        return summon_total

    def _apply_summon_overflow_fallback(self, source_enemy: Any) -> None:
        if source_enemy.faction_id == "helix_ward":
            self.restore_health(source_enemy, 8, source=source_enemy)
            return
        if source_enemy.faction_id == "blackwire_directorate":
            for ally in self._allies_for(source_enemy):
                if ally.is_alive() and ally.id in {"patrol_drone", "sentry_node"}:
                    self.grant_block(ally, 4, source=source_enemy)
            return
        source_enemy.adjust_strength(2)

    def _allies_for(self, source_enemy: Any) -> list[Any]:
        return [
            enemy
            for enemy in self.enemies
            if getattr(enemy, "faction_id", None) == getattr(source_enemy, "faction_id", None)
        ]

    def _resolve_player_end_of_turn_statuses(self) -> None:
        if self.player.infect > 0:
            self.lose_hp_with_feedback(self.player, self.player.infect, source=self.player, feedback_context={"source_status_id": "infect"})
            if self.player.infect >= 6:
                self.lose_hp_with_feedback(self.player, 4, source=self.player, feedback_context={"source_status_id": "infect_burst"})
                self.player.infect = 3
        if self.player.burn > 0:
            burn_amount = self.player.burn
            self.lose_hp_with_feedback(self.player, burn_amount, source=self.player, feedback_context={"source_status_id": "burn"})
            self._emit_runtime_event({"hook": "on_player_burn_tick", "amount": burn_amount})
            self.player.burn = max(0, self.player.burn - 1)
        self.player.tick_marked_turns()
        self.player.clear_suppressed()

    def _clear_expired_player_statuses_for_turn_start(self) -> None:
        if self.player.marked == 0:
            self.player.marked_turns = 0

    def _resolve_enemy_turn_start_effects(self, enemy: Any) -> None:
        fortified = enemy.get_status("fortified")
        if fortified > 0:
            self.grant_block(enemy, min(12, fortified), source=enemy, feedback_context={"source_status_id": "fortified"})
        regenerate = enemy.get_status("regenerate")
        if regenerate > 0:
            self.restore_health(enemy, regenerate, source=enemy, feedback_context={"source_status_id": "regenerate"})
            enemy.consume_status("regenerate", 1)
        if enemy.id == "graft_saint":
            self.restore_health(
                enemy,
                10 if enemy.get_status("mutated") > 0 else 6,
                source=enemy,
                feedback_context={"source_status_id": "graft_saint"},
            )

    def _resolve_enemy_end_of_turn_effects(self, enemy: Any) -> None:
        if not enemy.is_alive():
            return
        infect = enemy.get_status("infect")
        if infect > 0:
            self.lose_hp_with_feedback(enemy, infect, source=enemy, feedback_context={"source_status_id": "infect"})
            if infect >= 6:
                self.lose_hp_with_feedback(enemy, 4, source=enemy, feedback_context={"source_status_id": "infect_burst"})
                enemy.set_status("infect", 3)
                self._emit_runtime_event({"hook": "on_infect_burst", "target_id": enemy.id})
        burn = enemy.get_status("burn")
        if burn > 0:
            self.lose_hp_with_feedback(enemy, burn, source=enemy, feedback_context={"source_status_id": "burn"})
            enemy.consume_status("burn", 1)
        enemy.clear_status("momentum")
        if enemy.id == "furnace_hound":
            enemy.apply_status("overheat", 1)
        if not enemy.is_alive():
            self._handle_enemy_defeat(enemy)

    def _apply_enemy_spawn_rules(self, enemy: Any) -> None:
        if enemy.id == "audit_hound":
            enemy.apply_status("fortified", 4)
        elif enemy.id == "sentry_node":
            enemy.apply_status("fortified", 3)
        elif enemy.id == "compliance_engine_ax9":
            self.grant_block(enemy, 20, source=enemy, feedback_context={"source_status_id": "spawn_rule"})
            enemy.apply_status("fortified", 8)
        elif enemy.id == "junction_9_sentinel":
            enemy.apply_status("fortified", 6)

    def _apply_bleed_bonus(self, target: Any) -> int:
        if hasattr(target, "bleed") and getattr(target, "bleed", 0) > 0:
            bonus = int(target.bleed)
            target.bleed = max(0, target.bleed - 1)
            self.lose_hp_with_feedback(target, bonus, source=target, feedback_context={"source_status_id": "bleed"})
            return bonus
        if hasattr(target, "get_status") and target.get_status("bleed") > 0:
            bonus = target.get_status("bleed")
            target.consume_status("bleed", 1)
            self.lose_hp_with_feedback(target, bonus, source=target, feedback_context={"source_status_id": "bleed"})
            if hasattr(target, "id"):
                self._emit_runtime_event({"hook": "on_bleed_trigger", "target_id": target.id, "amount": bonus})
            if not target.is_alive():
                self._handle_enemy_defeat(target)
            return bonus
        return 0

    def _handle_enemy_phase_change(self, enemy: Any, phase_rule: dict[str, Any]) -> None:
        enemy.apply_status("mutated", 1)
        if enemy.id == "gland_brute":
            enemy.adjust_strength(3)
        elif enemy.id == "failed_saint":
            enemy.apply_status("regenerate", 3)
        elif enemy.id == "graft_saint":
            enemy.adjust_strength(3)
        elif enemy.id == "director_vale":
            enemy.adjust_strength(1)
        elif enemy.id == "furnace_hound":
            enemy.adjust_strength(2)
        bark_trigger = phase_rule.get("bark_trigger")
        if isinstance(bark_trigger, str):
            self._maybe_emit_bark(enemy, bark_trigger)

    def _handle_enemy_defeat(self, enemy: Any) -> None:
        if enemy.id in self._defeated_enemy_ids:
            return
        self._defeated_enemy_ids.add(enemy.id)
        self._emit_runtime_event(
            {
                "hook": "on_enemy_death",
                "enemy_id": enemy.id,
                "enemy_tags": list(getattr(enemy, "tags", [])),
            }
        )
        for effect in enemy.death_effects:
            target = self.player if effect.get("target") == "player" else enemy
            self._resolve_enemy_effect(enemy, effect, target, self.action_resolver)
        for ally in self._living_enemies():
            if ally is enemy or ally.faction_id != enemy.faction_id:
                continue
            if enemy.id in {"sludge_whelp", "patrol_drone", "scavver"} and ally.id == "miremother_vexa":
                ally.apply_status("biomass", 1)
            for effect in ally.ally_death_effects:
                target = ally if effect.get("target", "self") == "self" else self.player
                self._resolve_enemy_effect(ally, effect, target, self.action_resolver)
        speaker = next((ally for ally in self._living_enemies() if ally.faction_id == enemy.faction_id), None)
        if speaker is not None:
            self._maybe_emit_bark(speaker, "ally_death")

    def _emit_encounter_start_bark(self) -> None:
        speaker = next((enemy for enemy in self._living_enemies() if enemy.is_boss), None)
        if speaker is None:
            living = self._living_enemies()
            speaker = living[0] if living else None
        if speaker is not None:
            self._maybe_emit_bark(speaker, "start", force=True)

    def _maybe_emit_bark(self, speaker: Any, trigger: str, *, force: bool = False) -> None:
        if speaker is None:
            return
        speaker_key = f"{speaker.id}:{trigger}"
        limit = BARK_MAX_BOSS_PER_SPEAKER if speaker.is_boss else BARK_MAX_GENERIC_PER_SPEAKER
        if not force:
            if self._bark_cooldown_remaining > 0:
                return
            if self._speaker_bark_counts.get(speaker_key, 0) >= limit:
                return
        lines = self._bark_lines_for_speaker(speaker, trigger)
        if not lines:
            return
        line = self.rng.choice(lines)
        self._speaker_bark_counts[speaker_key] = self._speaker_bark_counts.get(speaker_key, 0) + 1
        self._bark_nonce += 1
        self.active_bark = {
            "id": self._bark_nonce,
            "speaker_id": speaker.id,
            "speaker_name": speaker.name,
            "text": line,
            "is_boss": bool(speaker.is_boss),
            "duration": BARK_BOSS_DURATION_SECONDS if speaker.is_boss else BARK_GENERIC_DURATION_SECONDS,
        }
        self._bark_cooldown_remaining = 0 if force else BARK_COOLDOWN_ACTIONS

    def _bark_lines_for_speaker(self, speaker: Any, trigger: str) -> list[str]:
        try:
            return self._bark_source.bark_lines(
                boss_id=speaker.id if speaker.is_boss else None,
                faction_id=speaker.faction_id if speaker.faction_id != "legacy" else None,
                trigger=trigger,
            )
        except Exception:
            return []

    def _advance_bark_cooldown(self) -> None:
        if self._bark_cooldown_remaining > 0:
            self._bark_cooldown_remaining -= 1
            if self._bark_cooldown_remaining == 0:
                self.active_bark = None

    def _start_player_turn(self) -> dict[str, Any]:
        turn_summary = self.turn_manager.start_player_turn(self.player)
        hook_logs = self._resolve_hook_sources(self.player.active_powers, "turn_start", {})
        if hook_logs:
            self.event_log.extend(hook_logs)
        self._clear_expired_player_statuses_for_turn_start()
        drawn_cards = self.draw_cards(self.player, self.player.draw_per_turn)
        turn_summary["drawn_cards"] = [card.id for card in drawn_cards]
        return turn_summary

    def _resolve_card_effect(
        self,
        *,
        effect: dict[str, Any],
        card: Any,
        explicit_target: Any | None,
        damage_bonus: int,
        block_penalty: int,
        echoed: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        effect_type = effect["type"]
        results: list[dict[str, Any]] = []

        if effect_type == "damage":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            base_value = self._player_effect_damage(card, effect["value"], damage_bonus)
            applied = self.apply_damage(
                self.player,
                target,
                base_value,
                feedback_context={"source_card_id": getattr(card, "id", None), "source_card_type": getattr(card, "type", None)},
            )
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "multi_damage":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            base_value = self._player_effect_damage(card, effect["value"], damage_bonus)
            for _ in range(effect["count"]):
                applied = self.apply_damage(
                    self.player,
                    target,
                    base_value,
                    feedback_context={"source_card_id": getattr(card, "id", None), "source_card_type": getattr(card, "type", None)},
                )
                results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "lifesteal_damage":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            base_value = self._player_effect_damage(card, effect["value"], damage_bonus)
            feedback_context = {"source_card_id": getattr(card, "id", None), "source_card_type": getattr(card, "type", None)}
            applied = self.apply_damage(self.player, target, base_value, feedback_context=feedback_context)
            healed = self.restore_health(self.player, applied, source=self.player, feedback_context=feedback_context)
            if healed > 0:
                self._emit_runtime_event(
                    {
                        "hook": "on_heal",
                        "amount": healed,
                        "source": getattr(card, "id", None),
                        "source_card_id": getattr(card, "id", None),
                    }
                )
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            results.append(self._resolution_record("heal", healed, healed, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "block":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            if target is self.player and self._player_positive_status_blocked("block", effect["value"]):
                results.append(self._resolution_record(effect_type, effect["value"], 0, target, echoed=echoed))
                return results, block_penalty
            value = effect["value"]
            if block_penalty > 0:
                reduction = min(block_penalty, value)
                value = max(0, value - reduction)
                block_penalty -= reduction
            applied = self.grant_block(
                target,
                value,
                source=self.player,
                feedback_context={"source_card_id": getattr(card, "id", None), "source_card_type": getattr(card, "type", None)},
            )
            if target is self.player and applied > 0:
                self._player_block_cards_this_turn += 1
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "heal":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            applied = self.restore_health(
                target,
                effect["value"],
                source=self.player,
                feedback_context={"source_card_id": getattr(card, "id", None), "source_card_type": getattr(card, "type", None)},
            )
            if target is self.player and applied > 0:
                self._emit_runtime_event(
                    {
                        "hook": "on_heal",
                        "amount": applied,
                        "source": getattr(card, "id", None),
                        "source_card_id": getattr(card, "id", None),
                    }
                )
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "draw":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            drawn = self.draw_cards(target, effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], len(drawn), target, echoed=echoed))
            return results, block_penalty

        if effect_type == "energy":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            applied = target.gain_energy(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "self_damage":
            applied = self.lose_hp_with_feedback(
                self.player,
                effect["value"],
                source=self.player,
                feedback_context={"source_card_id": getattr(card, "id", None), "source_card_type": getattr(card, "type", None)},
            )
            results.append(self._resolution_record(effect_type, effect["value"], applied, self.player, echoed=echoed))
            if applied > 0:
                self._emit_runtime_event(
                    {
                        "hook": "on_self_damage",
                        "amount": applied,
                        "self_damage": applied,
                        "source": getattr(card, "id", None),
                        "source_card_id": getattr(card, "id", None),
                    }
                )
            hook_logs = self._resolve_hook_sources(self.player.active_powers, "on_self_damage", {"self_damage": applied})
            self.event_log.extend(hook_logs)
            return results, block_penalty

        if effect_type == "gain_strength":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            if target is self.player and self._player_positive_status_blocked("gain_strength", effect["value"]):
                results.append(self._resolution_record(effect_type, effect["value"], 0, target, echoed=echoed))
                return results, block_penalty
            target.adjust_strength(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], effect["value"], target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_weak":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            applied = self._apply_status_to_enemy(target, "weak", effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_vulnerable":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            applied = self._apply_status_to_enemy(target, "vulnerable", effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_bleed":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            applied = self._apply_status_to_enemy(target, "bleed", effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_infect":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            applied = self._apply_status_to_enemy(target, "infect", effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_nullified":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            applied = self._apply_status_to_enemy(target, "nullified", effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "cleanse_status":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            status_id = str(effect.get("status_id", "")).strip().lower()
            if hasattr(target, "cleanse_combat_status"):
                applied = target.cleanse_combat_status(status_id, effect["value"])
            elif hasattr(target, "consume_status"):
                applied = target.consume_status(status_id, effect["value"])
            elif hasattr(target, "clear_status"):
                before = target.get_status(status_id) if hasattr(target, "get_status") else 0
                target.clear_status(status_id)
                applied = before
            else:
                applied = 0
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "remove_nullified":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            if hasattr(target, "remove_nullified"):
                applied = 1 if target.remove_nullified() else 0
            elif hasattr(target, "clear_status"):
                before = target.get_status("nullified") if hasattr(target, "get_status") else 0
                target.clear_status("nullified")
                applied = 1 if before > 0 else 0
            else:
                applied = 0
            results.append(self._resolution_record(effect_type, 1, applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "remove_one_player_status":
            applied = 0
            for status_id in effect.get("status_ids", []):
                key = str(status_id).strip().lower()
                if key == "nullified":
                    removed = 1 if self.player.remove_nullified() else 0
                else:
                    removed = self.player.cleanse_combat_status(key, 1)
                if removed > 0:
                    applied = removed
                    break
            results.append(
                self._resolution_record(effect_type, 1, applied, self.player, echoed=echoed)
            )
            return results, block_penalty

        if effect_type == "adjust_protocol_drift":
            self._emit_runtime_event(
                {
                    "hook": "adjust_protocol_drift_effect",
                    "amount": effect["value"],
                    "source_card_id": getattr(card, "id", None),
                    "source_chain": [getattr(card, "id", None)],
                }
            )
            results.append(self._resolution_record(effect_type, effect["value"], effect["value"], self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "exhaust_status_card_in_hand":
            target_status = next(
                (
                    hand_card
                    for hand_card in self.player.deck_manager.hand
                    if hand_card is not card and getattr(hand_card, "type", "") == "status"
                ),
                None,
            )
            if target_status is not None:
                self.player.deck_manager.exhaust_card(target_status)
                self._notify_card_exhausted(target_status)
                results.append(self._resolution_record(effect_type, 1, 1, self.player, echoed=echoed))
                return results, block_penalty
            fallback_results: list[dict[str, Any]] = []
            local_block_penalty = block_penalty
            for nested_effect in effect.get("fallback_effects", []):
                effect_results, local_block_penalty = self._resolve_card_effect(
                    effect=nested_effect,
                    card=card,
                    explicit_target=explicit_target,
                    damage_bonus=damage_bonus,
                    block_penalty=local_block_penalty,
                    echoed=echoed,
                )
                fallback_results.extend(effect_results)
            fallback_results.append(self._resolution_record(effect_type, 1, 0, self.player, echoed=echoed))
            return fallback_results, local_block_penalty

        if effect_type == "modify_next_card_cost":
            if self._player_positive_status_blocked("modify_next_card_cost", effect["value"]):
                results.append(self._resolution_record(effect_type, effect["value"], 0, self.player, echoed=echoed))
                return results, block_penalty
            previous_total = self.player.next_card_cost_delta
            total = self.player.adjust_next_card_cost(effect["value"])
            if effect["value"] < 0 and total < previous_total:
                self._emit_runtime_event(
                    {
                        "hook": "on_card_cost_reduced",
                        "old_cost": None,
                        "new_cost": None,
                        "source": getattr(card, "id", None),
                        "source_card_id": getattr(card, "id", None),
                    }
                )
            results.append(self._resolution_record(effect_type, effect["value"], total, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "modify_next_attack_damage":
            if self._player_positive_status_blocked("modify_next_attack_damage", effect["value"]):
                results.append(self._resolution_record(effect_type, effect["value"], 0, self.player, echoed=echoed))
                return results, block_penalty
            total = self.player.adjust_next_attack_damage(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], total, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "add_status_card":
            count = effect.get("count", 1)
            added = 0
            for _ in range(count):
                status_card = self._create_status_card(effect["card_id"])
                self.player.add_temporary_combat_card(status_card)
                pile = effect.get("pile", "discard")
                if pile == "draw":
                    self.player.deck_manager.add_to_draw_pile(status_card)
                else:
                    self.player.deck_manager.add_to_discard(status_card)
                    self._emit_runtime_event(
                        {
                            "hook": "on_status_card_added_to_discard",
                            "card_id": getattr(status_card, "id", None),
                            "card_type": getattr(status_card, "type", None),
                        }
                    )
                added += 1
            results.append(self._resolution_record(effect_type, count, added, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "random_one_of":
            option = self._choose_random_option(effect["options"])
            nested_results: list[dict[str, Any]] = []
            local_block_penalty = block_penalty
            for nested_effect in option["effects"]:
                effect_results, local_block_penalty = self._resolve_card_effect(
                    effect=nested_effect,
                    card=card,
                    explicit_target=explicit_target,
                    damage_bonus=damage_bonus,
                    block_penalty=local_block_penalty,
                    echoed=echoed,
                )
                nested_results.extend(effect_results)
            if option.get("summary"):
                nested_results.append(
                    {
                        "type": "summary",
                        "value": 0,
                        "applied": 0,
                        "target": "player",
                        "summary": option["summary"],
                        "echoed": echoed,
                    }
                )
            return nested_results, local_block_penalty

        if effect_type == "exhaust_drawn_card":
            drawn_card = explicit_target
            if drawn_card is not None and drawn_card in self.player.deck_manager.hand:
                self.player.deck_manager.exhaust_card(drawn_card)
                self._notify_card_exhausted(drawn_card)
                results.append(self._resolution_record(effect_type, 0, 1, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "noop":
            results.append(self._resolution_record(effect_type, effect["value"], 0, self.player, echoed=echoed))
            return results, block_penalty

        raise ValueError(f"Unsupported combat effect type: {effect_type}")

    def _process_drawn_cards(self, target: Any, drawn_cards: list[Any]) -> None:
        for card in drawn_cards:
            if card.type == "status":
                self._emit_runtime_event(
                    {
                        "hook": "on_status_drawn",
                        "card": card,
                        "card_id": getattr(card, "id", None),
                        "card_type": getattr(card, "type", None),
                        "exhausted_by_trigger": False,
                    }
                )
                status_logs = self._resolve_hook_sources(
                    self.player.active_powers,
                    "on_status_drawn",
                    {"drawn_card": card},
                    explicit_target=card,
                )
                if status_logs:
                    self.event_log.extend(status_logs)
                if card not in target.deck_manager.hand:
                    continue
            draw_logs = self._resolve_hook_sources([card], "on_draw", {"drawn_card": card}, explicit_target=card)
            if draw_logs:
                self.event_log.extend(draw_logs)
            if card.has_keyword("exhaust") and card in target.deck_manager.hand:
                target.deck_manager.exhaust_card(card)
                self._notify_card_exhausted(card)

    def _hook_sources_for_play(self, played_card: Any) -> list[Any]:
        sources = list(self.player.active_powers)
        if played_card.triggers and all(source is not played_card for source in sources):
            sources.append(played_card)
        return sources

    def _resolve_hook_sources(
        self,
        cards: list[Any],
        hook_name: str,
        context: dict[str, Any],
        *,
        explicit_target: Any | None = None,
    ) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        for card in cards:
            for trigger in card.triggers:
                if trigger["hook"] != hook_name:
                    continue
                if not self._trigger_conditions_met(trigger.get("conditions", {}), context):
                    continue
                trigger_resolutions: list[dict[str, Any]] = []
                for effect in trigger["effects"]:
                    effect_results, _ = self._resolve_card_effect(
                        effect=effect,
                        card=card,
                        explicit_target=explicit_target,
                        damage_bonus=0,
                        block_penalty=0,
                        echoed=False,
                    )
                    trigger_resolutions.extend(effect_results)
                logs.append(
                    {
                        "type": "trigger",
                        "source": "player",
                        "label": card.name,
                        "card_id": card.id,
                        "hook": hook_name,
                        "resolutions": trigger_resolutions,
                        "summary": self._summarize_event(label=f"{card.name} {hook_name}", resolutions=trigger_resolutions),
                    }
                )
        return logs

    def _trigger_conditions_met(self, conditions: dict[str, Any], context: dict[str, Any]) -> bool:
        for key, value in conditions.items():
            if key == "first_card_this_turn":
                if bool(context.get("first_card_this_turn", False)) != bool(value):
                    return False
            elif key == "played_card_type":
                played_card = context.get("played_card")
                if played_card is None or getattr(played_card, "type", None) != value:
                    return False
            elif key == "below_hp_ratio":
                if self.player.max_hp <= 0:
                    return False
                if (self.player.current_hp / self.player.max_hp) > float(value):
                    return False
        return True

    def _resolve_effect_target(
        self,
        effect: dict[str, Any],
        explicit_target: Any | None,
        *,
        default_target: str,
    ) -> Any:
        target_kind = effect.get("target", default_target)
        if target_kind == "self":
            return self.player
        if target_kind == "enemy":
            target = explicit_target if explicit_target is not None else self._first_living_enemy()
            if target is None:
                raise ValueError("No valid enemy target is available.")
            return target
        if target_kind == "all_enemies":
            raise ValueError("all_enemies is not supported in single-target resolution.")
        if target_kind == "drawn_card":
            return explicit_target
        return self.player

    def _adjust_attack_amount(self, source: Any, target: Any, amount: int) -> int:
        adjusted = max(0, amount + getattr(source, "strength", 0))
        if getattr(source, "weak", 0) > 0:
            adjusted = max(0, int(adjusted * 0.75))
        if getattr(target, "vulnerable", 0) > 0:
            adjusted = int(adjusted * 1.5)
        return adjusted

    def _player_effect_damage(self, card: Any, base_value: int, damage_bonus: int) -> int:
        adjusted = base_value + damage_bonus
        if getattr(card, "type", "") == "attack" and getattr(self.player, "suppressed", 0) > 0:
            multiplier = max(0.1, 1.0 - (0.15 * self.player.suppressed))
            adjusted = max(1, int(adjusted * multiplier))
        return adjusted

    def _player_positive_status_blocked(self, effect_type: str, value: int) -> bool:
        if not getattr(self.player, "nullified", False):
            return False
        blocked = (
            (effect_type == "block" and value > 0)
            or (effect_type == "gain_strength" and value > 0)
            or (effect_type == "modify_next_attack_damage" and value > 0)
            or (effect_type == "modify_next_card_cost" and value < 0)
        )
        if blocked:
            self._emit_runtime_event(
                {
                    "hook": "on_positive_gain_blocked_by_nullified",
                    "effect_type": effect_type,
                    "value": value,
                }
            )
            self.player.consume_nullified()
        return blocked

    def _create_status_card(self, card_id: str) -> Any:
        if self.player.deck_manager is None:
            raise ValueError("Cannot create status cards without a deck manager.")
        return self.player.deck_manager.starting_deck[0].__class__.from_dict(  # pragma: no cover - replaced by state manager snapshots
            self.player.deck_manager.starting_deck[0].to_dict()
        )

    def set_card_factory(self, factory: Any) -> None:
        self._card_factory = factory

    def _create_status_card(self, card_id: str) -> Any:  # type: ignore[override]
        factory = getattr(self, "_card_factory", None)
        if factory is None:
            raise ValueError("CombatManager requires a card factory before adding status cards.")
        return factory(card_id)

    def _choose_random_option(self, options: list[dict[str, Any]]) -> dict[str, Any]:
        total_weight = sum(option["weight"] for option in options)
        roll = self.rng.randint(1, total_weight)
        running_total = 0
        for option in options:
            running_total += option["weight"]
            if roll <= running_total:
                return option
        return options[-1]

    def _resolution_record(
        self,
        effect_type: str,
        value: int,
        applied: int,
        target: Any,
        *,
        echoed: bool,
    ) -> dict[str, Any]:
        record = {
            "type": effect_type,
            "value": value,
            "applied": applied,
            "target": getattr(target, "id", "player"),
        }
        if echoed:
            record["echoed"] = True
        return record

    def _living_enemies(self) -> list[Any]:
        return [enemy for enemy in self.enemies if enemy.is_alive()]

    def _first_living_enemy(self) -> Any | None:
        living = self._living_enemies()
        return living[0] if living else None

    def _enemy_event_entry(self, enemy: Any, intent: str, resolution: dict[str, Any]) -> dict[str, Any]:
        logged_resolution = {**resolution, "target": resolution.get("target", "player")}
        return {
            "type": "intent",
            "source": enemy.id,
            "label": enemy.name,
            "card_id": enemy.id,
            "intent": intent,
            "resolutions": resolution.get("resolutions", [logged_resolution]),
            "summary": resolution.get(
                "summary",
                self._summarize_event(label=f"{enemy.name} {intent}", resolutions=resolution.get("resolutions", [logged_resolution])),
            ),
        }

    def _summarize_event(
        self,
        label: str,
        resolutions: list[dict[str, Any]],
        hook_logs: list[dict[str, Any]] | None = None,
    ) -> str:
        parts: list[str] = []
        for resolution in resolutions:
            if resolution.get("type") == "summary" and resolution.get("summary"):
                parts.append(str(resolution["summary"]))
                continue
            parts.append(f"{resolution['type']} {resolution['applied']} -> {resolution['target']}")
        if hook_logs:
            parts.extend(log["summary"] for log in hook_logs if log.get("summary"))
        if not parts:
            return f"{label}: no effect."
        return f"{label}: {', '.join(parts)}"


def simulate_combat_manager() -> dict[str, Any]:
    import random

    from cards.card_library import CardLibrary
    from cards.deck_manager import DeckManager
    from entities.enemy_library import EnemyLibrary
    from entities.player import Player

    card_library = CardLibrary()
    deck = DeckManager(
        [
            card_library.create_card("strike_01"),
            card_library.create_card("defend_01"),
            card_library.create_card("operator_auto_tuner_01"),
        ],
        rng=random.Random(17),
    )
    player = Player(character_id="operator")
    player.attach_deck(deck)
    enemy = EnemyLibrary().create_enemy("enemy_basic_01")
    combat = CombatManager(player=player, enemies=[enemy], rng=random.Random(9))
    combat.set_card_factory(card_library.create_card)
    combat.start_combat()
    defend_card = next(card for card in player.deck_manager.hand if card.id == "defend_01")
    strike_card = next(card for card in player.deck_manager.hand if card.id == "strike_01")
    defend_resolution = combat.resolve_action({"card": defend_card})
    strike_resolution = combat.resolve_action({"card": strike_card, "target": enemy})
    return {
        "player_block_after_defend": player.block,
        "enemy_hp_after_strike": enemy.current_hp,
        "defend_resolution_count": len(defend_resolution["resolutions"]),
        "strike_resolution_count": len(strike_resolution["resolutions"]),
        "combat_state": combat.get_state(),
    }
