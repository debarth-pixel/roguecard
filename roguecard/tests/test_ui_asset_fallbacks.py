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

from ui.combat_ui import CombatUI
from ui.relic_assets import RelicAssets


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


if __name__ == "__main__":
    unittest.main()
