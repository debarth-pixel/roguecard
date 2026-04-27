from __future__ import annotations

import json
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_asset_path


EVENT_UI_ASSET_ROOT = resolve_asset_path("ui", "events")
EVENT_UI_MANIFEST_PATH = EVENT_UI_ASSET_ROOT / "event_ui_manifest.json"


class EventUIAssets:
    def __init__(self) -> None:
        self._metadata_loaded = False
        self._entries: dict[str, dict[str, Any]] = {}
        self._source_surfaces: dict[str, Any] = {}
        self._crop_cache: dict[str, Any] = {}
        self._scaled_cache: dict[tuple[str, int, int], Any] = {}

    def preload(self) -> None:
        self._ensure_metadata_loaded()
        if pygame is None:
            return
        for asset_name in self._entries:
            self.get(asset_name)

    def validate(self) -> dict[str, Any]:
        self._ensure_metadata_loaded()
        missing: list[str] = []
        invalid: list[str] = []
        for asset_name, entry in self._entries.items():
            source_path = EVENT_UI_ASSET_ROOT / entry["source"]
            if not source_path.exists():
                missing.append(str(source_path))
                continue
            if pygame is None:
                continue
            surface = self._ensure_source_loaded(entry["source"])
            rect = pygame.Rect(entry["rect"])
            if rect.width <= 0 or rect.height <= 0 or not surface.get_rect().contains(rect):
                invalid.append(asset_name)
        return {"asset_count": len(self._entries), "missing": missing, "invalid": invalid}

    def get(self, asset_name: str, target_size: tuple[int, int] | None = None) -> Any | None:
        if pygame is None:
            return None
        crop = self._crop(asset_name)
        if crop is None:
            return None
        if target_size is None:
            return crop.copy()
        width = max(1, int(target_size[0]))
        height = max(1, int(target_size[1]))
        cache_key = (asset_name, width, height)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached.copy()
        scaled = pygame.transform.smoothscale(crop, (width, height))
        self._scaled_cache[cache_key] = scaled
        return scaled.copy()

    def blit(
        self,
        surface: Any,
        asset_name: str,
        rect: Any,
        *,
        alpha: int | None = None,
        nine_slice: bool | tuple[int, int, int, int] = False,
    ) -> None:
        if pygame is None:
            return
        target_rect = pygame.Rect(rect)
        if target_rect.width <= 0 or target_rect.height <= 0:
            return
        source = self._crop(asset_name)
        if source is None:
            return
        if alpha is not None:
            source = source.copy()
            source.set_alpha(max(0, min(255, int(alpha))))
        if nine_slice:
            border = self._nine_slice_border(asset_name, nine_slice)
            self._blit_nine_slice(surface, source, target_rect, border)
            return
        scaled = pygame.transform.smoothscale(source, target_rect.size)
        surface.blit(scaled, target_rect.topleft)

    def _ensure_metadata_loaded(self) -> None:
        if self._metadata_loaded:
            return
        if not EVENT_UI_MANIFEST_PATH.exists():
            raise ValueError(f"Missing event UI manifest: {EVENT_UI_MANIFEST_PATH}")
        with EVENT_UI_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        raw_assets = payload.get("assets", {})
        if not isinstance(raw_assets, dict):
            raise ValueError("Event UI manifest must contain an assets object.")
        entries: dict[str, dict[str, Any]] = {}
        for asset_name, entry in raw_assets.items():
            if not isinstance(entry, dict):
                continue
            source = str(entry.get("source", "")).strip()
            rect = entry.get("rect", [])
            if not source or not isinstance(rect, list) or len(rect) != 4:
                continue
            entries[str(asset_name)] = {
                "source": source,
                "rect": [int(value) for value in rect],
                "nine_slice": [int(value) for value in entry.get("nine_slice", [])[:4]],
            }
        self._entries = entries
        self._metadata_loaded = True

    def _ensure_source_loaded(self, source_name: str) -> Any:
        cached = self._source_surfaces.get(source_name)
        if cached is not None:
            return cached
        if pygame is None:
            raise RuntimeError("Pygame is required to load event UI assets.")
        path = EVENT_UI_ASSET_ROOT / source_name
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error) as error:
            raise ValueError(f"Unable to load event UI asset source: {path}") from error
        self._source_surfaces[source_name] = image
        return image

    def _crop(self, asset_name: str) -> Any | None:
        cached = self._crop_cache.get(asset_name)
        if cached is not None:
            return cached
        self._ensure_metadata_loaded()
        entry = self._entries.get(asset_name)
        if entry is None or pygame is None:
            return None
        source = self._ensure_source_loaded(entry["source"])
        rect = pygame.Rect(entry["rect"])
        if not source.get_rect().contains(rect):
            raise ValueError(
                f"Event UI crop out of bounds: {asset_name} needs {rect} "
                f"inside {entry['source']} sized {source.get_size()}."
            )
        crop = source.subsurface(rect).copy()
        self._crop_cache[asset_name] = crop
        return crop

    def _nine_slice_border(
        self,
        asset_name: str,
        border: bool | tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:
        if border is not True:
            return border
        self._ensure_metadata_loaded()
        entry = self._entries.get(asset_name, {})
        values = entry.get("nine_slice", [])
        if len(values) == 4:
            return tuple(values)  # type: ignore[return-value]
        return (18, 18, 18, 18)

    def _blit_nine_slice(
        self,
        target: Any,
        source: Any,
        rect: Any,
        border: tuple[int, int, int, int],
    ) -> None:
        target_rect = pygame.Rect(rect)
        sw, sh = source.get_size()
        left, top, right, bottom = border
        left = max(1, min(left, sw // 2 - 1, target_rect.width // 2))
        right = max(1, min(right, sw // 2 - 1, target_rect.width // 2))
        top = max(1, min(top, sh // 2 - 1, target_rect.height // 2))
        bottom = max(1, min(bottom, sh // 2 - 1, target_rect.height // 2))

        src_x = [0, left, sw - right, sw]
        src_y = [0, top, sh - bottom, sh]
        dst_x = [target_rect.x, target_rect.x + left, target_rect.right - right, target_rect.right]
        dst_y = [target_rect.y, target_rect.y + top, target_rect.bottom - bottom, target_rect.bottom]
        for row in range(3):
            for col in range(3):
                src_rect = pygame.Rect(
                    src_x[col],
                    src_y[row],
                    src_x[col + 1] - src_x[col],
                    src_y[row + 1] - src_y[row],
                )
                dst_rect = pygame.Rect(
                    dst_x[col],
                    dst_y[row],
                    dst_x[col + 1] - dst_x[col],
                    dst_y[row + 1] - dst_y[row],
                )
                if src_rect.width <= 0 or src_rect.height <= 0 or dst_rect.width <= 0 or dst_rect.height <= 0:
                    continue
                tile = source.subsurface(src_rect)
                if src_rect.size != dst_rect.size:
                    tile = pygame.transform.smoothscale(tile, dst_rect.size)
                target.blit(tile, dst_rect.topleft)


event_ui_assets = EventUIAssets()
