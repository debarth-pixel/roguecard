from __future__ import annotations

import random
from typing import Any

from combat.action_resolver import ActionResolver
from combat.turn_manager import TurnManager

DIRECT_DAMAGE_TYPES = {"damage", "multi_damage", "lifesteal_damage"}


class CombatManager:
    def __init__(self, player: Any, enemies: list[Any], rng: random.Random | None = None) -> None:
        self.player = player
        self.enemies = enemies
        self.rng = rng or random.Random()
        self.action_resolver = ActionResolver()
        self.turn_manager = TurnManager()
        self.combat_active = False
        self.event_log: list[dict[str, Any]] = []

    def start_combat(self) -> dict[str, Any]:
        if self.player.deck_manager is None:
            raise ValueError("Combat requires a player with an attached deck manager.")
        if not self.enemies:
            raise ValueError("Combat requires at least one enemy.")

        self.turn_manager = TurnManager()
        self.player.start_combat()
        for enemy in self.enemies:
            enemy.reset_for_combat()
            enemy.choose_intent()

        self.combat_active = True
        self.event_log.clear()
        opening_turn = self._start_player_turn()
        return {"combat_active": self.combat_active, "opening_turn": opening_turn}

    def end_turn(self) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot end a turn outside of active combat.")

        self.turn_manager.end_player_turn(self.player)
        turn_end_logs = self._resolve_hook_sources(
            self.player.active_powers,
            "turn_end",
            {"played_card": None, "first_card_this_turn": False},
        )
        if turn_end_logs:
            self.event_log.extend(turn_end_logs)

        enemy_results: list[dict[str, Any]] = []
        for enemy in self._living_enemies():
            self.turn_manager.start_enemy_turn(enemy)
            intent = enemy.current_intent or enemy.choose_intent()
            resolution = enemy.execute_intent(self.action_resolver, self.player, combat_manager=self)
            enemy_results.append({"enemy_id": enemy.id, "resolution": resolution})
            self.event_log.append(self._enemy_event_entry(enemy=enemy, intent=intent, resolution=resolution))
            if not self.player.is_alive():
                self.combat_active = False
                return {"combat_active": self.combat_active, "enemy_results": enemy_results}

        if not self._living_enemies():
            self.combat_active = False
            return {"combat_active": self.combat_active, "enemy_results": enemy_results}

        for enemy in self._living_enemies():
            enemy.choose_intent()

        next_turn = self._start_player_turn()
        return {
            "combat_active": self.combat_active,
            "enemy_results": enemy_results,
            "next_turn": next_turn,
        }

    def resolve_action(self, action: dict[str, Any]) -> dict[str, Any]:
        if not self.combat_active:
            raise ValueError("Cannot resolve actions outside of active combat.")
        if not isinstance(action, dict):
            raise ValueError("Combat actions must be dictionaries.")

        card = action.get("card")
        explicit_target = action.get("target")
        energy_cost = action.get("cost")
        damage_bonus = action.get("damage_bonus", 0)
        repeat_count = action.get("repeat_count", 0)
        remaining_block_penalty = action.get("block_penalty", 0)

        if card is None:
            raise ValueError("Combat actions require a card instance.")
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

        for resolve_index in range(1 + repeat_count):
            for effect in card.effects:
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
        if card.type == "power":
            self.player.add_active_power(moved_card)
        elif card.has_keyword("exhaust"):
            self.player.deck_manager.exhaust_pile.append(moved_card)
        else:
            self.player.deck_manager.discard_pile.append(moved_card)

        hook_context = {
            "played_card": card,
            "first_card_this_turn": first_card_this_turn,
            "played_card_type": card.type,
        }
        hook_logs = self._resolve_hook_sources(self._hook_sources_for_play(card), "after_card_played", hook_context)
        if card.type == "attack":
            hook_logs.extend(self._resolve_hook_sources(self._hook_sources_for_play(card), "after_attack_played", hook_context))

        self.player.consume_next_card_cost_delta()
        if card.type == "attack":
            self.player.consume_next_attack_bonus()

        self.player.first_card_played = True
        if card.type == "attack":
            self.player.first_attack_played = True

        event_entry = {
            "type": "card",
            "source": "player",
            "label": card.name,
            "card_id": card.id,
            "card_type": card.type,
            "resolutions": logged_resolutions,
            "summary": self._summarize_event(label=card.name, resolutions=logged_resolutions, hook_logs=hook_logs),
        }
        self.event_log.append(event_entry)
        self.event_log.extend(hook_logs)

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

    def apply_damage(self, source: Any, target: Any, amount: int) -> int:
        adjusted = self._adjust_attack_amount(source, target, amount)
        return target.take_damage(adjusted)

    def get_state(self) -> dict[str, Any]:
        return {
            "combat_active": self.combat_active,
            "turn_number": self.turn_manager.turn_number,
            "turn_owner": self.turn_manager.turn_owner,
            "player": self.player.get_state(),
            "enemies": [enemy.get_state() for enemy in self.enemies],
            "living_enemy_ids": [enemy.id for enemy in self._living_enemies()],
            "event_log": list(self.event_log),
        }

    def get_enemy(self, enemy_id: str) -> Any | None:
        for enemy in self.enemies:
            if enemy.id == enemy_id and enemy.is_alive():
                return enemy
        return None

    def _start_player_turn(self) -> dict[str, Any]:
        turn_summary = self.turn_manager.start_player_turn(self.player)
        hook_logs = self._resolve_hook_sources(self.player.active_powers, "turn_start", {})
        if hook_logs:
            self.event_log.extend(hook_logs)
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
            base_value = effect["value"] + damage_bonus
            applied = self.apply_damage(self.player, target, base_value)
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "multi_damage":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            base_value = effect["value"] + damage_bonus
            for _ in range(effect["count"]):
                applied = self.apply_damage(self.player, target, base_value)
                results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "lifesteal_damage":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            base_value = effect["value"] + damage_bonus
            applied = self.apply_damage(self.player, target, base_value)
            healed = self.player.heal(applied)
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            results.append(self._resolution_record("heal", healed, healed, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "block":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            value = effect["value"]
            if block_penalty > 0:
                reduction = min(block_penalty, value)
                value = max(0, value - reduction)
                block_penalty -= reduction
            applied = target.gain_block(value)
            results.append(self._resolution_record(effect_type, effect["value"], applied, target, echoed=echoed))
            return results, block_penalty

        if effect_type == "heal":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            applied = target.heal(effect["value"])
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
            applied = self.player.lose_hp(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], applied, self.player, echoed=echoed))
            hook_logs = self._resolve_hook_sources(self.player.active_powers, "on_self_damage", {"self_damage": applied})
            self.event_log.extend(hook_logs)
            return results, block_penalty

        if effect_type == "gain_strength":
            target = self._resolve_effect_target(effect, explicit_target, default_target="self")
            target.adjust_strength(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], effect["value"], target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_weak":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            target.apply_weak(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], effect["value"], target, echoed=echoed))
            return results, block_penalty

        if effect_type == "apply_vulnerable":
            target = self._resolve_effect_target(effect, explicit_target, default_target="enemy")
            target.apply_vulnerable(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], effect["value"], target, echoed=echoed))
            return results, block_penalty

        if effect_type == "modify_next_card_cost":
            total = self.player.adjust_next_card_cost(effect["value"])
            results.append(self._resolution_record(effect_type, effect["value"], total, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "modify_next_attack_damage":
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
                results.append(self._resolution_record(effect_type, 0, 1, self.player, echoed=echoed))
            return results, block_penalty

        if effect_type == "noop":
            results.append(self._resolution_record(effect_type, effect["value"], 0, self.player, echoed=echoed))
            return results, block_penalty

        raise ValueError(f"Unsupported combat effect type: {effect_type}")

    def _process_drawn_cards(self, target: Any, drawn_cards: list[Any]) -> None:
        for card in drawn_cards:
            draw_logs = self._resolve_hook_sources([card], "on_draw", {"drawn_card": card}, explicit_target=card)
            if draw_logs:
                self.event_log.extend(draw_logs)
            if card.type == "status":
                status_logs = self._resolve_hook_sources(
                    self.player.active_powers,
                    "on_status_drawn",
                    {"drawn_card": card},
                    explicit_target=card,
                )
                if status_logs:
                    self.event_log.extend(status_logs)
            if card.has_keyword("exhaust") and card in target.deck_manager.hand:
                target.deck_manager.exhaust_card(card)

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
        target_id = "player" if intent == "attack" else enemy.id
        logged_resolution = {**resolution, "target": target_id}
        return {
            "type": "intent",
            "source": enemy.id,
            "label": enemy.name,
            "card_id": enemy.id,
            "intent": intent,
            "resolutions": [logged_resolution],
            "summary": self._summarize_event(label=f"{enemy.name} {intent}", resolutions=[logged_resolution]),
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
