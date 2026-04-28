from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from ui.card_rendering import draw_card, renderable_card_rule_entries


class CardRuleEntryTests(unittest.TestCase):
    def test_attack_damage_and_status_are_plain_rule_entries(self) -> None:
        card = {
            "id": "test_attack",
            "name": "Test Attack",
            "cost": 1,
            "type": "attack",
            "effects": [
                {"type": "damage", "value": 7},
                {"type": "apply_bleed", "value": 1},
            ],
        }

        entries = renderable_card_rule_entries(card)

        self.assertEqual([entry["text"] for entry in entries], ["Deal 7 damage.", "Apply 1 Bleed."])
        self.assertNotIn("DMG", " ".join(entry["text"] for entry in entries))

    def test_active_corruption_replaces_normal_rules(self) -> None:
        card = {
            "id": "test_corrupt",
            "name": "Test Corrupt",
            "cost": 1,
            "type": "attack",
            "effects": [{"type": "damage", "value": 7}],
            "dynamic_rule_entries": [{"text": "Cannot afford.", "tone": "danger"}],
            "corruption_display": [
                {"text": "Drift 25+: Deal 4 extra damage.", "active": True},
            ],
        }

        entries = renderable_card_rule_entries(card)

        self.assertEqual([entry["text"] for entry in entries], ["Drift 25+: Deal 4 extra damage."])
        self.assertEqual(entries[0]["tone"], "corruption_active")

    def test_inactive_corruption_does_not_append_to_normal_rules(self) -> None:
        card = {
            "id": "test_uncorrupt",
            "name": "Test Uncorrupt",
            "cost": 1,
            "type": "attack",
            "effects": [{"type": "damage", "value": 7}],
            "corruption_display": [
                {"text": "Drift 25+: Deal 4 extra damage.", "active": False},
            ],
        }

        entries = renderable_card_rule_entries(card)

        self.assertEqual([entry["text"] for entry in entries], ["Deal 7 damage."])


class CardRenderingSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if pygame is None:
            raise unittest.SkipTest("pygame is not available")
        pygame.init()
        if not pygame.display.get_init():
            pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        if pygame is not None:
            pygame.display.quit()
            pygame.quit()

    def test_attack_card_renders_without_effect_cue(self) -> None:
        assert pygame is not None
        surface = pygame.Surface((220, 320), pygame.SRCALPHA)
        font = pygame.font.SysFont("arial", 16)
        card = {
            "id": "test_attack",
            "name": "Test Attack",
            "cost": 1,
            "type": "attack",
            "effects": [
                {"type": "damage", "value": 9, "base_value": 7},
                {"type": "apply_bleed", "value": 1},
            ],
        }

        draw_card(
            surface,
            (0, 0, 220, 320),
            card,
            {"title": font, "body": font, "tiny": font},
            variant="full",
        )

        self.assertGreater(pygame.mask.from_surface(surface).count(), 0)


if __name__ == "__main__":
    unittest.main()
