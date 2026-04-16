from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import RELIC_CUTOUTS_ROOT, RUN_MODIFIERS_DATA_PATH


class RelicAssets:
    def __init__(self) -> None:
        self._metadata_loaded = False
        self._validated = False
        self._paths_by_id: dict[str, Path] = {}
        self._ids_by_name: dict[str, str] = {}
        self._ids_by_normalized_name: dict[str, str] = {}
        self._base_surfaces: dict[str, Any] = {}
        self._scaled_cache: dict[tuple[str, int, int], Any] = {}

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

        with RUN_MODIFIERS_DATA_PATH.open("r", encoding="utf-8") as handle:
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
            self._paths_by_id[relic_id] = RELIC_CUTOUTS_ROOT / f"{relic_id}.png"
            self._ids_by_name[relic_name] = relic_id
            self._ids_by_normalized_name[self._normalize_key(relic_name)] = relic_id

        self._metadata_loaded = True

    def _validate_coverage(self) -> None:
        if self._validated:
            return

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
            surface = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return None

        self._base_surfaces[relic_id] = surface
        return surface

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
