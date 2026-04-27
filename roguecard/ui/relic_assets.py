from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import RELIC_CUTOUTS_ROOT, RUN_MODIFIERS_DATA_PATH

LOGGER = logging.getLogger(__name__)


class RelicAssets:
    def __init__(
        self,
        *,
        data_path: Path | None = None,
        cutouts_root: Path | None = None,
    ) -> None:
        self._data_path = data_path or RUN_MODIFIERS_DATA_PATH
        self._cutouts_root = cutouts_root or RELIC_CUTOUTS_ROOT
        self._metadata_loaded = False
        self._validated = False
        self._paths_by_id: dict[str, Path] = {}
        self._ids_by_name: dict[str, str] = {}
        self._ids_by_normalized_name: dict[str, str] = {}
        self._base_surfaces: dict[str, Any] = {}
        self._scaled_cache: dict[tuple[str, int, int], Any] = {}
        self._missing_asset_ids: set[str] = set()
        self._unreadable_asset_ids: set[str] = set()
        self._reported_asset_issue_ids: set[str] = set()
        self._fallback_surface: Any | None = None

    def preload(self) -> None:
        self._ensure_metadata_loaded()
        self._validate_coverage()
        if pygame is not None:
            for relic_id in self._paths_by_id:
                self._load_surface(relic_id)

    def get_relic_art(self, relic_key: str, target_size: tuple[int, int]) -> Any | None:
        if pygame is None:
            return None
        relic_id = self._resolve_relic_id(relic_key)
        if relic_id is None:
            return None

        width = max(1, int(target_size[0]))
        height = max(1, int(target_size[1]))
        cache_key = (relic_id, width, height)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        surface = self._load_surface(relic_id)
        if surface is None:
            return None

        scaled = self._scale_contain(surface, (width, height))
        self._scaled_cache[cache_key] = scaled
        return scaled

    def _resolve_relic_id(self, relic_key: str) -> str | None:
        self._ensure_metadata_loaded()
        stripped = str(relic_key).strip()
        if stripped in self._paths_by_id:
            return stripped
        exact = self._ids_by_name.get(stripped)
        if exact is not None:
            return exact
        return self._ids_by_normalized_name.get(self._normalize_key(stripped))

    def _ensure_metadata_loaded(self) -> None:
        if self._metadata_loaded:
            return

        with self._data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("run_modifiers.json must contain a list when loading relic assets.")

        for entry in payload:
            if not isinstance(entry, dict) or str(entry.get("type", "")).lower() != "relic":
                continue
            relic_id = str(entry.get("id", "")).strip()
            relic_name = str(entry.get("name", "")).strip()
            if not relic_id or not relic_name:
                continue
            self._paths_by_id[relic_id] = self._cutouts_root / f"{relic_id}.png"
            self._ids_by_name[relic_name] = relic_id
            self._ids_by_normalized_name[self._normalize_key(relic_name)] = relic_id

        self._metadata_loaded = True

    def _validate_coverage(self) -> None:
        if self._validated:
            return

        missing_ids = [
            relic_id
            for relic_id, path in self._paths_by_id.items()
            if not path.exists()
        ]
        self._missing_asset_ids = set(missing_ids)

        if pygame is not None:
            unloadable_ids: list[str] = []
            for relic_id in self._paths_by_id:
                if relic_id in self._missing_asset_ids:
                    continue
                try:
                    pygame.image.load(str(self._paths_by_id[relic_id]))
                except (FileNotFoundError, pygame.error):
                    unloadable_ids.append(relic_id)
            self._unreadable_asset_ids = set(unloadable_ids)

        self._report_asset_issues()

        self._validated = True

    def _load_surface(self, relic_id: str) -> Any | None:
        cached = self._base_surfaces.get(relic_id)
        if cached is not None:
            return cached
        if pygame is None:
            return None

        path = self._paths_by_id.get(relic_id)
        if path is None:
            return None
        try:
            loaded = pygame.image.load(str(path))
            surface = loaded.convert_alpha() if pygame.display.get_surface() is not None else loaded.copy()
        except (FileNotFoundError, pygame.error):
            if path.exists():
                self._unreadable_asset_ids.add(relic_id)
            else:
                self._missing_asset_ids.add(relic_id)
            self._report_asset_issues()
            surface = self._fallback_relic_surface()

        self._base_surfaces[relic_id] = surface
        return surface

    def _report_asset_issues(self) -> None:
        issue_ids = self._missing_asset_ids.union(self._unreadable_asset_ids)
        new_issue_ids = sorted(issue_ids.difference(self._reported_asset_issue_ids))
        if not new_issue_ids:
            return
        LOGGER.warning(
            "Using fallback relic art for: %s",
            ", ".join(new_issue_ids),
        )
        self._reported_asset_issue_ids.update(new_issue_ids)

    def _fallback_relic_surface(self) -> Any | None:
        if pygame is None:
            return None
        if self._fallback_surface is not None:
            return self._fallback_surface.copy()

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
        pygame.draw.polygon(surface, (90, 104, 122), outer)
        pygame.draw.polygon(surface, (148, 166, 188), outer, 6)
        pygame.draw.circle(surface, (34, 42, 56), (98, 98), 52)
        pygame.draw.circle(surface, (180, 196, 214), (98, 98), 52, 3)
        pygame.draw.line(surface, (234, 196, 96), (58, 136), (138, 60), 7)
        pygame.draw.line(surface, (234, 196, 96), (62, 60), (90, 92), 7)
        pygame.draw.line(surface, (234, 196, 96), (106, 104), (134, 136), 7)
        if pygame.font.get_init():
            font = pygame.font.SysFont("georgia", 80, bold=True)
            small_font = pygame.font.SysFont("georgia", 28, bold=True)
            glyph = font.render("??", True, (244, 248, 255))
            label = small_font.render("GEN", True, (220, 230, 242))
            surface.blit(glyph, glyph.get_rect(center=(98, 88)))
            surface.blit(label, label.get_rect(center=(98, 152)))
        self._fallback_surface = surface
        return surface.copy()

    def _normalize_key(self, name: str) -> str:
        return " ".join(str(name).strip().lower().split())

    def _scale_contain(self, surface: Any, target_size: tuple[int, int]) -> Any:
        source_width, source_height = surface.get_size()
        target_width, target_height = target_size
        if source_width <= 0 or source_height <= 0:
            return surface.copy()
        scale = min(target_width / source_width, target_height / source_height)
        scaled_width = max(1, int(source_width * scale))
        scaled_height = max(1, int(source_height * scale))
        if (scaled_width, scaled_height) == (source_width, source_height):
            return surface.copy()
        return pygame.transform.smoothscale(surface, (scaled_width, scaled_height))


relic_assets = RelicAssets()
