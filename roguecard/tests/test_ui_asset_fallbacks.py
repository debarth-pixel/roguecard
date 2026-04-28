from __future__ import annotations

import json
import os
import shutil
import unittest
import uuid
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from ui.combat_ui import (
    ENEMY_SOURCE_MAX_HEIGHT_RATIO,
    ENEMY_SOURCE_MAX_WIDTH_RATIO,
    ENEMY_SOURCE_ROOT,
    ENEMY_SPRITE_METADATA,
    CombatUI,
)
from ui.combat_layout import build_combat_layout
from ui.relic_assets import RelicAssets
from ui.ui_manager import UIManager


class _PygameTestCase(unittest.TestCase):
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

    def _write_cutout(self, path: Path, glyph: str) -> None:
        assert pygame is not None
        surface = pygame.Surface((196, 196), pygame.SRCALPHA)
        outer = [
            (98, 18),
            (162, 40),
            (182, 98),
            (162, 156),
            (98, 178),
            (34, 156),
            (14, 98),
            (34, 40),
        ]
        pygame.draw.polygon(surface, (76, 92, 112), outer)
        pygame.draw.polygon(surface, (168, 188, 214), outer, 6)
        pygame.draw.circle(surface, (24, 34, 46), (98, 98), 52)
        pygame.draw.circle(surface, (208, 220, 238), (98, 98), 52, 3)
        font = pygame.font.SysFont("georgia", 76, bold=True)
        glyph_surface = font.render(glyph, True, (244, 248, 255))
        surface.blit(glyph_surface, glyph_surface.get_rect(center=(98, 94)))
        pygame.image.save(surface, str(path))


class RelicAssetsTests(_PygameTestCase):
    def test_missing_cutout_uses_fallback_instead_of_raising(self) -> None:
        root = Path(__file__).resolve().parent / f"_tmp_ui_assets_{uuid.uuid4().hex}"
        cutouts_root = root / "relics"
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        cutouts_root.mkdir(parents=True, exist_ok=True)
        data_path = root / "run_modifiers.json"
        payload = [
            {"id": "present_test", "name": "Present Test", "type": "relic"},
            {"id": "missing_test", "name": "Missing Test", "type": "relic"},
        ]
        data_path.write_text(json.dumps(payload), encoding="utf-8")
        self._write_cutout(cutouts_root / "present_test.png", "PT")

        assets = RelicAssets(data_path=data_path, cutouts_root=cutouts_root)
        assets.preload()

        self.assertIn("missing_test", assets._missing_asset_ids)
        present = assets.get_relic_art("present_test", (64, 64))
        missing = assets.get_relic_art("missing_test", (64, 64))
        self.assertIsNotNone(present)
        self.assertIsNotNone(missing)
        self.assertLessEqual(missing.get_width(), 64)
        self.assertLessEqual(missing.get_height(), 64)
        self.assertNotEqual(
            pygame.image.tobytes(present, "RGBA"),
            pygame.image.tobytes(missing, "RGBA"),
        )

    def test_attack_cadence_and_guard_ledger_have_real_cutouts(self) -> None:
        assets = RelicAssets()
        assets.preload()
        for relic_id in ("attack_cadence", "guard_ledger"):
            with self.subTest(relic_id=relic_id):
                self.assertTrue(assets._paths_by_id[relic_id].exists())
                self.assertNotIn(relic_id, assets._missing_asset_ids)
                art = assets.get_relic_art(relic_id, (72, 72))
                self.assertIsNotNone(art)


class CombatUIDriftGaugeTests(_PygameTestCase):
    def setUp(self) -> None:
        self.ui = CombatUI()

    def test_segment_count_thresholds(self) -> None:
        expectations = {
            0: 0,
            1: 1,
            5: 1,
            19: 4,
            20: 4,
            39: 8,
            40: 8,
            59: 12,
            60: 12,
            79: 16,
            80: 16,
            100: 20,
        }
        for value, expected in expectations.items():
            with self.subTest(protocol_drift_pct=value):
                self.assertEqual(self.ui._protocol_drift_segment_count(value), expected)

    def test_segment_geometry_stays_inside_gauge_bounds(self) -> None:
        for gauge_rect in (pygame.Rect(0, 0, 18, 76), pygame.Rect(0, 0, 24, 96), pygame.Rect(0, 0, 28, 104)):
            with self.subTest(gauge_rect=gauge_rect):
                inner_rect = self.ui._drift_gauge_inner_rect(gauge_rect)
                segment_rects = self.ui._drift_gauge_segment_rects(gauge_rect)
                self.assertEqual(len(segment_rects), 20)
                for segment_rect in segment_rects:
                    self.assertTrue(inner_rect.contains(segment_rect))

    def test_band_colors_change_with_corruption_state(self) -> None:
        colors = [self.ui._protocol_drift_bar_color(index) for index in range(6)]
        self.assertEqual(len(set(colors)), 6)

    def test_configured_enemy_source_sheets_are_readable(self) -> None:
        for enemy_id, metadata in ENEMY_SPRITE_METADATA.items():
            source = metadata.get("source")
            if not source:
                continue
            with self.subTest(enemy_id=enemy_id):
                source_path = ENEMY_SOURCE_ROOT / source
                self.assertTrue(source_path.exists())
                source_surface = pygame.image.load(str(source_path)).convert_alpha()
                self.assertGreater(source_surface.get_width(), 0)
                self.assertGreater(source_surface.get_height(), 0)

    def test_source_sheets_are_not_used_as_runtime_enemy_frames(self) -> None:
        for enemy_id, metadata in ENEMY_SPRITE_METADATA.items():
            source = metadata.get("source")
            if not source:
                continue
            with self.subTest(enemy_id=enemy_id):
                source_surface = pygame.image.load(str(ENEMY_SOURCE_ROOT / source)).convert_alpha()
                source_size = source_surface.get_size()
                frames = self.ui._enemy_sprite_frames(enemy_id)
                if not frames:
                    continue
                self.assertIn("idle", frames)
                self.assertIn("damage", frames)
                self.assertIn("dead", frames)
                for frame in frames.values():
                    self.assertGreater(frame.get_width(), 0)
                    self.assertGreater(frame.get_height(), 0)
                    self.assertNotEqual(frame.get_size(), source_size)

    def test_enemy_sprite_sizes_stay_within_actor_bounds(self) -> None:
        actor_rect = pygame.Rect(0, 0, 92, 146)
        tier_height_bonus = {"normal": 1.0, "elite": 1.08, "boss": 1.16}
        tier_width_bonus = {"normal": 1.0, "elite": 1.04, "boss": 1.08}

        for enemy_id, metadata in ENEMY_SPRITE_METADATA.items():
            frames = self.ui._enemy_sprite_frames(enemy_id)
            if not frames:
                continue
            sprite_surface = frames["idle"]
            for tier in ("normal", "elite", "boss"):
                with self.subTest(enemy_id=enemy_id, tier=tier):
                    actor = {"actor_rect": actor_rect, "enemy": {"tier": tier}}
                    target_width, target_height = self.ui._enemy_sprite_target_size(sprite_surface, actor, metadata)
                    max_height = int(actor_rect.height * float(metadata.get("max_height_ratio", ENEMY_SOURCE_MAX_HEIGHT_RATIO)) * tier_height_bonus[tier])
                    max_width = int(actor_rect.width * float(metadata.get("max_width_ratio", ENEMY_SOURCE_MAX_WIDTH_RATIO)) * tier_width_bonus[tier])
                    self.assertLessEqual(target_height, max_height + 1)
                    self.assertLessEqual(target_width, max_width + 1)

    def test_combat_top_hud_and_floating_relic_row_anchor_left(self) -> None:
        layout = build_combat_layout((1280, 720))
        safe_rect = pygame.Rect(*layout.safe_rect)
        self.assertEqual(layout.top_hud_rect[0], layout.safe_rect[0])
        self.assertEqual(layout.top_resource_bar_rect, layout.relic_row_rect)
        self.assertGreaterEqual(layout.relic_row_rect[1], layout.top_hud_rect[1] + layout.top_hud_rect[3])
        self.assertGreater(layout.turn_label_rect[2], 0)
        self.assertGreater(layout.turn_label_rect[3], 0)
        self.assertTrue(safe_rect.contains(pygame.Rect(*layout.top_hud_rect)))
        self.assertTrue(safe_rect.contains(pygame.Rect(*layout.top_pause_rect)))
        if layout.top_intel_rect is not None:
            self.assertTrue(safe_rect.contains(pygame.Rect(*layout.top_intel_rect)))

    def test_relic_icons_are_contained_in_floating_row(self) -> None:
        layout = build_combat_layout((1280, 720))
        modifiers = [{"id": f"test_relic_{index}", "name": f"Test Relic {index}", "type": "relic"} for index in range(4)]
        modifier_layout = self.ui._combat_modifier_layout(modifiers, layout)
        row_rect = pygame.Rect(*layout.relic_row_rect)
        self.assertEqual(len(modifier_layout["relics"]), len(modifiers))
        for relic in modifier_layout["relics"]:
            with self.subTest(slot_index=relic["slot_index"]):
                self.assertFalse(relic.get("empty", False))
                self.assertTrue(row_rect.contains(pygame.Rect(*relic["rect"])))
                self.assertTrue(row_rect.contains(pygame.Rect(*relic["icon_rect"])))

    def test_relic_overflow_count_tracks_hidden_floating_icons(self) -> None:
        layout = build_combat_layout((1280, 720))
        modifiers = [{"id": f"test_relic_{index}", "name": f"Test Relic {index}", "type": "relic"} for index in range(20)]
        modifier_layout = self.ui._combat_modifier_layout(modifiers, layout)
        self.assertGreater(modifier_layout["overflow_count"], 0)
        self.assertLess(len(modifier_layout["relics"]), len(modifiers))

    def test_combat_top_bar_segments_stay_inside_sleek_hud(self) -> None:
        layout = build_combat_layout((1280, 720))
        manager = UIManager()
        manager._ensure_fonts(1.0)
        specs = [
            {"label": "The Enforcer", "sublabel": "HP 70/70", "accent": (0, 0, 0)},
            {"label": "M1 Outskirts", "sublabel": "Sector", "accent": (0, 0, 0)},
            {"label": "0 cr", "sublabel": "Credits", "accent": (0, 0, 0)},
        ]
        summary_rect = (layout.top_hud_rect[0] + 250, layout.top_hud_rect[1], layout.top_hud_rect[2] - 250, layout.top_hud_rect[3])
        hud_rect = pygame.Rect(*summary_rect)
        for segment in manager._combat_sleek_segment_layout(specs, summary_rect):
            with self.subTest(label=segment["label"]):
                self.assertTrue(hud_rect.contains(pygame.Rect(*segment["rect"])))


if __name__ == "__main__":
    unittest.main()
