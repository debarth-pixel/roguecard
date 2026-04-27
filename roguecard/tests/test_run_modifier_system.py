from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from cards.card_library import CardLibrary
from core.event_library import EventLibrary
from core.run_modifier_engine import RunModifierEngine
from core.run_modifier_library import RunModifierLibrary
from core.state_manager import StateManager

TEST_ROOT = Path(__file__).resolve().parent


def _workspace_temp_file(name: str) -> Path:
    return TEST_ROOT / name


class RunModifierLibraryTests(unittest.TestCase):
    def test_dangerous_loop_effect_requires_bounded_scope(self) -> None:
        payload = [
            {
                "id": "unsafe_draw_test",
                "name": "Unsafe Draw Test",
                "type": "relic",
                "category": "common_relic",
                "draft_eligible": False,
                "description": "Bad loop guard.",
                "rarity": "common",
                "base_weight": 1,
                "tags": ["draw"],
                "source_types": ["elite_reward", "shop"],
                "hooks": {
                    "after_card_played": [
                        {
                            "type": "draw_cards",
                            "value": 1,
                            "trigger_scope": {"mode": "once"},
                        }
                    ]
                },
            }
        ]
        path = _workspace_temp_file("_run_modifiers_validation_test.json")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(json.dumps(payload), encoding="utf-8")
        library = RunModifierLibrary(data_path=path, card_library=CardLibrary())
        with self.assertRaisesRegex(ValueError, "loop-safe trigger_scope"):
            library.load_modifiers()


class EventLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.card_library = CardLibrary()
        self.modifier_library = RunModifierLibrary(card_library=self.card_library)
        self.modifier_library.load_modifiers()

    def test_gain_random_modifier_backfills_event_relic_category(self) -> None:
        payload = [
            {
                "id": "event_modifier_backfill_test",
                "title": "Backfill",
                "body": "Backfill categories.",
                "rarity": "special",
                "base_weight": 1,
                "tags": ["relic"],
                "requirements": {"credits_at_least": 0},
                "choices": [
                    {
                        "id": "take_it",
                        "label": "Take it",
                        "description": "Gain a random event relic.",
                        "choice_type": "effect",
                        "effects": [
                            {
                                "type": "gain_random_modifier",
                                "source_type": "event",
                                "rarity_profile": "positive",
                                "allow_types": ["relic"],
                                "include_tags": ["economy"],
                            }
                        ],
                    }
                ],
            }
        ]
        path = _workspace_temp_file("_events_backfill_test.json")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(json.dumps(payload), encoding="utf-8")
        library = EventLibrary(
            data_path=path,
            card_library=self.card_library,
            modifier_library=self.modifier_library,
        )
        event = library.get_event("event_modifier_backfill_test")
        effect = event["choices"][0]["effects"][0]
        self.assertEqual(effect["allow_categories"], ["event_relic"])

    def test_gain_random_modifier_preserves_explicit_categories(self) -> None:
        payload = [
            {
                "id": "event_modifier_explicit_test",
                "title": "Explicit",
                "body": "Keep explicit categories.",
                "rarity": "special",
                "base_weight": 1,
                "tags": ["boss_relic"],
                "requirements": {"credits_at_least": 0},
                "choices": [
                    {
                        "id": "take_it",
                        "label": "Take it",
                        "description": "Gain a boss relic.",
                        "choice_type": "effect",
                        "effects": [
                            {
                                "type": "gain_random_modifier",
                                "source_type": "event",
                                "rarity_profile": "positive",
                                "allow_types": ["relic"],
                                "allow_categories": ["boss_relic"],
                                "include_tags": ["energy"],
                            }
                        ],
                    }
                ],
            }
        ]
        path = _workspace_temp_file("_events_explicit_test.json")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(json.dumps(payload), encoding="utf-8")
        library = EventLibrary(
            data_path=path,
            card_library=self.card_library,
            modifier_library=self.modifier_library,
        )
        event = library.get_event("event_modifier_explicit_test")
        effect = event["choices"][0]["effects"][0]
        self.assertEqual(effect["allow_categories"], ["boss_relic"])


class StateManagerTriggerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.card_library = CardLibrary()
        cls.modifier_library = RunModifierLibrary(card_library=cls.card_library)
        cls.modifier_library.load_modifiers()
        cls.engine = RunModifierEngine(cls.modifier_library)

    def setUp(self) -> None:
        self.manager = StateManager(card_library=self.card_library, modifier_library=self.modifier_library)

    def test_start_player_turn_keeps_per_target_counts(self) -> None:
        self.manager._apply_combat_modifier_effects = lambda hook_name: None  # type: ignore[method-assign]
        combat_flags = self.manager._combat_runtime_flags()
        combat_flags["pending_energy_next_turn"] = 0
        combat_flags["modifier_triggers"]["per_target_counts"] = {
            "modifier:on_attack_hit:shared": {"enemy_alpha": 1}
        }
        self.manager._start_player_turn_runtime()
        self.assertEqual(
            self.manager._modifier_triggers()["per_target_counts"],
            {"modifier:on_attack_hit:shared": {"enemy_alpha": 1}},
        )

    def test_once_per_combat_trigger_scope(self) -> None:
        effect = {"modifier_id": "test", "type": "gain_block", "trigger_scope": {"mode": "once_per_combat"}}
        event = {"hook": "on_block_gained"}
        self.assertTrue(self.manager._effect_trigger_available(effect, "on_block_gained", event))
        self.manager._record_effect_trigger(effect, "on_block_gained", event)
        self.assertFalse(self.manager._effect_trigger_available(effect, "on_block_gained", event))

    def test_max_n_per_turn_trigger_scope(self) -> None:
        effect = {"modifier_id": "test", "type": "gain_block", "trigger_scope": {"mode": "max_n_per_turn", "count": 2}}
        event = {"hook": "on_block_gained"}
        self.assertTrue(self.manager._effect_trigger_available(effect, "on_block_gained", event))
        self.manager._record_effect_trigger(effect, "on_block_gained", event)
        self.assertTrue(self.manager._effect_trigger_available(effect, "on_block_gained", event))
        self.manager._record_effect_trigger(effect, "on_block_gained", event)
        self.assertFalse(self.manager._effect_trigger_available(effect, "on_block_gained", event))

    def test_per_card_type_each_turn_scope(self) -> None:
        effect = {"modifier_id": "test", "type": "gain_block", "trigger_scope": {"mode": "per_card_type_each_turn"}}
        attack_event = {"hook": "after_card_played", "card_type": "attack"}
        skill_event = {"hook": "after_card_played", "card_type": "skill"}
        self.assertTrue(self.manager._effect_trigger_available(effect, "after_card_played", attack_event))
        self.manager._record_effect_trigger(effect, "after_card_played", attack_event)
        self.assertFalse(self.manager._effect_trigger_available(effect, "after_card_played", attack_event))
        self.assertTrue(self.manager._effect_trigger_available(effect, "after_card_played", skill_event))

    def test_per_target_each_turn_scope_and_target_death_reset(self) -> None:
        effect = {"modifier_id": "test", "type": "gain_block", "trigger_scope": {"mode": "per_target_each_turn"}}
        enemy_a = {"hook": "on_attack_hit", "target": "enemy_a"}
        enemy_b = {"hook": "on_attack_hit", "target": "enemy_b"}
        self.assertTrue(self.manager._effect_trigger_available(effect, "on_attack_hit", enemy_a))
        self.manager._record_effect_trigger(effect, "on_attack_hit", enemy_a)
        self.assertFalse(self.manager._effect_trigger_available(effect, "on_attack_hit", enemy_a))
        self.assertTrue(self.manager._effect_trigger_available(effect, "on_attack_hit", enemy_b))
        self.manager._clear_modifier_target_counters("enemy_a")
        self.assertTrue(self.manager._effect_trigger_available(effect, "on_attack_hit", enemy_a))

    def test_shared_key_multi_effect_gating_with_reaper_census(self) -> None:
        modifier = self.modifier_library.get_modifier("reaper_census")
        first_effect, second_effect = modifier["hooks"]["on_enemy_death"]
        event = {"hook": "on_enemy_death", "enemy_id": "enemy_alpha", "target": "enemy_alpha"}
        self.assertTrue(self.manager._effect_trigger_available(first_effect, "on_enemy_death", event))
        self.assertTrue(self.manager._effect_trigger_available(second_effect, "on_enemy_death", event))
        self.manager._record_effect_trigger(first_effect, "on_enemy_death", event)
        next_event = {"hook": "on_enemy_death", "enemy_id": "enemy_beta", "target": "enemy_beta"}
        self.assertFalse(self.manager._effect_trigger_available(first_effect, "on_enemy_death", next_event))
        self.assertFalse(self.manager._effect_trigger_available(second_effect, "on_enemy_death", next_event))

    def test_turn_interval_matching(self) -> None:
        effect = {"modifier_id": "test", "type": "gain_block", "turn_interval": 3}
        self.assertFalse(self.manager._modifier_effect_matches_event(effect, {"turn_number": 2}))
        self.assertTrue(self.manager._modifier_effect_matches_event(effect, {"turn_number": 3}))
        self.assertTrue(self.manager._modifier_effect_matches_event(effect, {"turn_number": 6}))

    def test_every_n_this_turn_matching_with_attack_cadence(self) -> None:
        effect = self.modifier_library.get_modifier("attack_cadence")["hooks"]["after_card_played"][0]
        self.assertFalse(
            self.manager._modifier_effect_matches_event(
                effect,
                {"card_type": "attack", "played_card_type_count_this_turn": 2},
            )
        )
        self.assertTrue(
            self.manager._modifier_effect_matches_event(
                effect,
                {"card_type": "attack", "played_card_type_count_this_turn": 3},
            )
        )

    def test_quarantine_vault_gates_hostile_status_response(self) -> None:
        reduce_effect, draw_effect = self.modifier_library.get_modifier("quarantine_vault")["hooks"]["on_player_status_applied"]
        burn_event = {"hook": "on_player_status_applied", "status_id": "burn"}
        weak_event = {"hook": "on_player_status_applied", "status_id": "weak"}
        self.assertTrue(self.manager._modifier_effect_matches_event(reduce_effect, burn_event))
        self.assertTrue(self.manager._modifier_effect_matches_event(draw_effect, burn_event))
        self.assertFalse(self.manager._modifier_effect_matches_event(reduce_effect, weak_event))
        self.assertTrue(self.manager._effect_trigger_available(reduce_effect, "on_player_status_applied", burn_event))
        self.manager._record_effect_trigger(reduce_effect, "on_player_status_applied", burn_event)
        self.assertFalse(self.manager._effect_trigger_available(draw_effect, "on_player_status_applied", burn_event))

    def test_cost_reduction_payload_normalization(self) -> None:
        normalized = self.manager._normalize_modifier_runtime_event(
            {
                "hook": "on_card_cost_reduced",
                "old_cost_value": 3,
                "new_cost_value": 1,
                "source_card_id": "strike_01",
            }
        )
        self.assertEqual(normalized["old_cost"], 3)
        self.assertEqual(normalized["new_cost"], 1)
        self.assertEqual(normalized["source"], "strike_01")

    def test_restore_modifier_runtime_flags_backfills_legacy_trigger_lists(self) -> None:
        restored = self.manager._restore_modifier_runtime_flags(
            {
                "combat": {
                    "triggered_modifier_ids_this_turn": ["turn_gate"],
                    "triggered_modifier_ids_this_combat": ["combat_gate"],
                }
            }
        )
        modifier_triggers = restored["combat"]["modifier_triggers"]
        self.assertEqual(modifier_triggers["per_turn_counts"]["turn_gate"], 1)
        self.assertEqual(modifier_triggers["per_combat_counts"]["combat_gate"], 1)


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.card_library = CardLibrary()
        cls.modifier_library = RunModifierLibrary(card_library=cls.card_library)
        cls.modifier_library.load_modifiers()
        cls.engine = RunModifierEngine(cls.modifier_library)

    def test_starter_offers_only_use_starter_relics(self) -> None:
        offer_ids = self.engine.generate_starter_offers(random.Random(19))
        self.assertEqual(len(offer_ids), 3)
        categories = {self.modifier_library.get_modifier(modifier_id)["category"] for modifier_id in offer_ids}
        self.assertEqual(categories, {"starter_relic"})

    def test_elite_boss_and_shop_candidate_pools_respect_categories(self) -> None:
        expectations = {
            "elite_reward": {"common_relic", "uncommon_relic", "rare_relic"},
            "boss_reward": {"boss_relic"},
            "shop": {"common_relic", "uncommon_relic", "rare_relic", "shop_relic"},
        }
        for source_type, expected_categories in expectations.items():
            with self.subTest(source_type=source_type):
                candidates = self.engine.weighted_modifier_candidates(
                    [],
                    source_type=source_type,
                    rarity_profile="positive",
                    allow_categories=sorted(expected_categories),
                )
                self.assertTrue(candidates)
                self.assertTrue(
                    all(candidate["modifier"]["category"] in expected_categories for candidate in candidates)
                )

    def test_shop_selection_excludes_owned_seen_sold_and_unsold_relics(self) -> None:
        manager = StateManager(card_library=self.card_library, modifier_library=self.modifier_library)
        manager.run_seed = 29
        manager.selected_node_id = "shop:test"
        manager.run_modifiers = [manager.run_modifier_engine.create_modifier_record("market_key", source="test")]
        selected = manager._select_offer_relic_ids(
            slot_count=3,
            label="shop_relic_inventory:test",
            source_type="shop",
            seen_relic_ids=["clean_slate"],
            sold_out_relic_ids=["signal_router"],
            current_unsold_ids=["carbon_weave"],
        )
        blocked = {"market_key", "clean_slate", "signal_router", "carbon_weave"}
        self.assertFalse(blocked.intersection(selected))
        for relic_id in selected:
            self.assertIn(
                self.modifier_library.get_modifier(relic_id)["category"],
                {"common_relic", "uncommon_relic", "rare_relic", "shop_relic"},
            )

    def test_event_random_modifier_selection_honors_explicit_categories(self) -> None:
        chosen = self.engine.choose_weighted_modifier(
            rng=random.Random(7),
            active_modifiers=[],
            source_type="event",
            rarity_profile="positive",
            allow_types=["blessing"],
            allow_categories=["blessing"],
        )
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen["category"], "blessing")


if __name__ == "__main__":
    unittest.main()
