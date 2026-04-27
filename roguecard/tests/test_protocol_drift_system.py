from __future__ import annotations

import random
import unittest

from cards.card_base import CardBase
from cards.card_library import CardLibrary
from core.event_selector import EventSelector
from core.protocol_drift import drift_snapshot
from core.run_modifier_library import RunModifierLibrary
from core.state_manager import StateManager
from entities.player import Player


class ProtocolDriftSnapshotTests(unittest.TestCase):
    def test_six_tier_snapshot_and_next_threshold(self) -> None:
        cases = {
            0: ("Stable", 20, "Signal Noise"),
            20: ("Signal Noise", 40, "Surge"),
            40: ("Surge", 60, "Fracture"),
            60: ("Fracture", 80, "Eclipse"),
            80: ("Eclipse", 100, "Full Drift"),
            100: ("Full Drift", None, None),
        }
        for pct, expected in cases.items():
            with self.subTest(protocol_drift_pct=pct):
                snapshot = drift_snapshot(pct)
                self.assertEqual(snapshot["tier_label"], expected[0])
                self.assertEqual(snapshot["next_threshold_pct"], expected[1])
                self.assertEqual(snapshot["next_threshold_label"], expected[2])


class PlayerUnstableEnergyTests(unittest.TestCase):
    def test_spend_energy_uses_unstable_first(self) -> None:
        player = Player(energy=3, unstable_energy=2)
        player.spend_energy(4)
        self.assertEqual(player.unstable_energy, 0)
        self.assertEqual(player.energy, 1)


class StateManagerProtocolDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.card_library = CardLibrary()
        cls.modifier_library = RunModifierLibrary(card_library=cls.card_library)
        cls.modifier_library.load_modifiers()

    def setUp(self) -> None:
        self.manager = StateManager(card_library=self.card_library, modifier_library=self.modifier_library)
        self.manager.run_seed = 77
        self.manager.selected_node_id = "test:node"
        self.manager.player = self.manager._create_player("enforcer", 77)

    def test_prepare_turn_runtime_grants_unstable_energy_and_feedback_threshold(self) -> None:
        self.manager.run_state["protocol_drift_pct"] = 80
        drift_runtime = self.manager._drift_runtime()
        drift_runtime["feedback_pressure_next_turn"] = 1
        self.manager._prepare_protocol_drift_turn_start(turn_number=2)
        self.assertEqual(self.manager.player.unstable_energy, 1)
        self.assertEqual(self.manager._drift_runtime()["feedback_safe_threshold_this_turn"], 3)
        self.assertEqual(self.manager._drift_runtime()["feedback_pressure_next_turn"], 0)

    def test_finalize_turn_end_records_leftover_unstable_energy_as_pressure(self) -> None:
        self.manager.run_state["protocol_drift_pct"] = 100
        self.manager.player.unstable_energy = 2
        self.manager._finalize_protocol_drift_turn_end()
        self.assertEqual(self.manager.player.unstable_energy, 0)
        self.assertEqual(self.manager._drift_runtime()["leftover_unstable_energy_last_turn"], 2)
        self.assertEqual(self.manager._drift_runtime()["feedback_pressure_next_turn"], 1)

    def test_resolved_combat_card_payload_matches_drift_scaling(self) -> None:
        self.manager.run_state["protocol_drift_pct"] = 60
        attack = self.card_library.create_card("strike_01")
        defend = self.card_library.create_card("defend_01")
        attack_payload = self.manager._resolve_combat_card_payload(attack)["card"]
        defend_payload = self.manager._resolve_combat_card_payload(defend)["card"]
        self.assertEqual(
            attack_payload["effects"][0]["value"],
            attack.to_dict()["effects"][0]["value"] + 3,
        )
        self.assertEqual(
            defend_payload["effects"][0]["value"],
            defend.to_dict()["effects"][0]["value"] + 3,
        )

    def test_drift_override_caps_loop_prone_effects(self) -> None:
        self.manager.run_state["protocol_drift_pct"] = 100
        card = CardBase.from_dict(
            {
                "id": "drift_override_test",
                "name": "Override Test",
                "cost": 1,
                "type": "skill",
                "owners": ["shared"],
                "shop_price": 0,
                "effects": [
                    {"type": "draw", "value": 1, "target": "self"},
                    {"type": "energy", "value": 1, "target": "self"},
                    {"type": "modify_next_card_cost", "value": -1, "target": "self"},
                    {"type": "add_status_card", "card_id": "status_glitch_01", "count": 1, "pile": "discard", "target": "self"},
                ],
                "drift_override": {
                    "draw_bonus": 5,
                    "energy_bonus": 5,
                    "cost_reduction_bonus": 5,
                    "card_creation_bonus": 5,
                },
            }
        )
        payload = self.manager._resolve_combat_card_payload(card)["card"]
        self.assertEqual(payload["effects"][0]["value"], 2)
        self.assertEqual(payload["effects"][1]["value"], 3)
        self.assertEqual(payload["effects"][2]["value"], -1)
        self.assertEqual(payload["effects"][3]["count"], 2)

    def test_full_drift_reward_always_appends_full_drift_signal(self) -> None:
        self.manager.run_state["protocol_drift_pct"] = 100
        reward = self.manager._generate_reward_state("elite", 25)
        self.assertIsNotNone(reward)
        self.assertIn("full_drift_signal", reward["sections"])
        self.assertIn("full_drift_signal", reward["section_order"])
        self.assertEqual(len(reward["sections"]["full_drift_signal"]["options"]), 3)

    def test_event_preview_rows_include_drift_card_eclipse_and_notes(self) -> None:
        rows = self.manager._event_choice_preview_rows(
            {
                "choice_type": "effect",
                "effects": [
                    {"type": "adjust_protocol_drift", "amount": 6},
                    {"type": "gain_card", "card_id": "drift_black_ice_bloom_01"},
                    {
                        "type": "gain_random_modifier",
                        "source_type": "event",
                        "rarity_profile": "positive",
                        "allow_categories": ["rare_relic", "boss_relic"],
                        "include_tags": ["corruption"],
                    },
                ],
                "preview_notes": ["Backlash: Nullified on zero-cost spikes"],
            }
        )
        labels = [row["label"] for row in rows]
        self.assertIn("+6% Drift", labels)
        self.assertTrue(any("hidden Drift card" in label for label in labels))
        self.assertIn("Gain Eclipse relic", labels)
        self.assertIn("Backlash: Nullified on zero-cost spikes", labels)


class FullDriftEventSelectorTests(unittest.TestCase):
    def test_full_drift_prefers_tagged_pool(self) -> None:
        selector = EventSelector()
        events = [
            {
                "id": "normal_event",
                "title": "Normal",
                "body": "Normal",
                "rarity": "common",
                "base_weight": 1.0,
                "tags": ["recovery"],
                "primary_tag": "recovery",
                "exclusion_tags": [],
                "requirements": {},
                "choices": [{"id": "ok", "label": "OK", "description": "OK", "choice_type": "effect", "requirements": {}, "effects": [], "outcomes": [], "ui_role": "normal"}],
            },
            {
                "id": "full_drift_event",
                "title": "Drift",
                "body": "Drift",
                "rarity": "common",
                "base_weight": 1.0,
                "tags": ["corruption", "full_drift_pool"],
                "primary_tag": "corruption",
                "exclusion_tags": [],
                "requirements": {},
                "choices": [{"id": "ok", "label": "OK", "description": "OK", "choice_type": "effect", "requirements": {}, "effects": [], "outcomes": [], "ui_role": "normal"}],
            },
        ]
        context = {
            "protocol_drift_pct": 100,
            "event_history": [],
            "current_floor": 1,
            "route_floor_count": 10,
            "current_act": 1,
            "current_hp": 50,
            "max_hp": 50,
            "credits": 0,
            "deck_size": 5,
            "status_count": 0,
            "active_modifier_ids": [],
        }
        weighted = selector.weighted_candidates(events, context)
        self.assertEqual([entry["event"]["id"] for entry in weighted], ["full_drift_event"])


if __name__ == "__main__":
    unittest.main()
