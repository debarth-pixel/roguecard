from __future__ import annotations

import json
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import STATUS_ICON_MANIFEST_PATH, STATUS_ICON_SPRITE_SHEET_PATH


class StatusIconAssets:
    def __init__(self) -> None:
        self._metadata_loaded = False
        self._entries_by_id: dict[str, dict[str, Any]] = {}
        self._sheet_surface: Any | None = None
        self._crop_cache: dict[str, Any] = {}
        self._scaled_cache: dict[tuple[str, int, int], Any] = {}

    def preload(self) -> None:
        self._ensure_metadata_loaded()
        if pygame is not None:
            self._ensure_sheet_loaded()

    def has_icon(self, icon_id: str) -> bool:
        self._ensure_metadata_loaded()
        return str(icon_id).strip() in self._entries_by_id

    def get_icon(self, icon_id: str, target_size: tuple[int, int]) -> Any | None:
        if pygame is None:
            return None

        icon_key = str(icon_id).strip()
        if not icon_key:
            return None

        width = max(1, int(target_size[0]))
        height = max(1, int(target_size[1]))
        cache_key = (icon_key, width, height)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        crop = self.get_icon_crop(icon_key)
        if crop is None:
            return None

        scaled = self._scale_contain(crop, (width, height))
        self._scaled_cache[cache_key] = scaled
        return scaled

    def get_icon_crop(self, icon_id: str) -> Any | None:
        if pygame is None:
            return None

        icon_key = str(icon_id).strip()
        if not icon_key:
            return None

        cached = self._crop_cache.get(icon_key)
        if cached is not None:
            return cached

        self._ensure_metadata_loaded()
        entry = self._entries_by_id.get(icon_key)
        if entry is None:
            return None

        sheet = self._ensure_sheet_loaded()
        rect = pygame.Rect(entry["x"], entry["y"], entry["w"], entry["h"])
        if not sheet.get_rect().contains(rect):
            raise ValueError(
                f"Status icon crop is out of bounds: {icon_key} needs "
                f"{rect.width}x{rect.height} at ({rect.x}, {rect.y}) but sheet size is "
                f"{sheet.get_width()}x{sheet.get_height()}."
            )

        crop = sheet.subsurface(rect).copy()
        self._crop_cache[icon_key] = crop
        return crop

    def _ensure_metadata_loaded(self) -> None:
        if self._metadata_loaded:
            return
        if not STATUS_ICON_MANIFEST_PATH.exists():
            raise ValueError(f"Missing status icon manifest: {STATUS_ICON_MANIFEST_PATH}")

        with STATUS_ICON_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        icons = payload.get("icons", [])
        if not isinstance(icons, list):
            raise ValueError("Status icon manifest must contain an 'icons' list.")

        self._entries_by_id = {}
        for icon in icons:
            if not isinstance(icon, dict):
                continue
            icon_id = str(icon.get("id", "")).strip()
            if not icon_id:
                continue
            self._entries_by_id[icon_id] = {
                "id": icon_id,
                "category": str(icon.get("category", "")).strip(),
                "display_name": str(icon.get("display_name", icon_id)).strip(),
                "x": int(icon.get("x", 0)),
                "y": int(icon.get("y", 0)),
                "w": int(icon.get("w", 0)),
                "h": int(icon.get("h", 0)),
            }

        self._metadata_loaded = True

    def _ensure_sheet_loaded(self) -> Any:
        if self._sheet_surface is not None:
            return self._sheet_surface
        if pygame is None:
            raise RuntimeError("Pygame is required to load status icon assets.")

        try:
            image = pygame.image.load(str(STATUS_ICON_SPRITE_SHEET_PATH))
        except (FileNotFoundError, pygame.error) as error:
            raise ValueError(f"Unable to load status icon sheet: {STATUS_ICON_SPRITE_SHEET_PATH}") from error

        try:
            image = image.convert_alpha()
        except pygame.error:
            image = image.copy()

        self._sheet_surface = image
        return image

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


status_icon_assets = StatusIconAssets()
