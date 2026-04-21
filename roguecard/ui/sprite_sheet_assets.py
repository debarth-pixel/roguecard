from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    CARD_ART_ATLAS_COORDINATES_PATH,
    CARD_ART_ATLAS_PATH,
    CARDS_DATA_PATH,
    RELIC_SPRITE_COORDINATES_PATH,
    RELIC_SPRITE_SHEET_PATH,
    RUN_MODIFIERS_DATA_PATH,
)


class SpriteSheetAssets:
    def __init__(self) -> None:
        self._metadata_loaded = False
        self._validated = False
        self._card_entries_by_name: dict[str, dict[str, Any]] = {}
        self._card_entries_by_normalized: dict[str, dict[str, Any]] = {}
        self._relic_entries_by_name: dict[str, dict[str, Any]] = {}
        self._relic_entries_by_normalized: dict[str, dict[str, Any]] = {}
        self._sheet_surfaces: dict[str, Any] = {}
        self._crop_cache: dict[tuple[str, str], Any] = {}
        self._scaled_cache: dict[tuple[str, str, int, int], Any] = {}

    def preload(self) -> None:
        self._ensure_metadata_loaded()
        self._validate_coverage()
        if pygame is not None:
            self._ensure_sheet_loaded("card")
            self._ensure_sheet_loaded("relic")

    def get_card_art(self, card_name: str, target_size: tuple[int, int]) -> Any | None:
        return self._get_scaled_sprite("card", card_name, target_size)

    def get_card_art_crop(self, card_name: str) -> Any | None:
        if pygame is None:
            return None
        entry = self._lookup_entry("card", card_name)
        if entry is None:
            return None
        return self._get_crop("card", entry)

    def get_relic_art(self, relic_name: str, target_size: tuple[int, int]) -> Any | None:
        return self._get_scaled_sprite("relic", relic_name, target_size)

    def _get_scaled_sprite(self, sheet_key: str, name: str, target_size: tuple[int, int]) -> Any | None:
        if pygame is None:
            return None

        width = max(1, int(target_size[0]))
        height = max(1, int(target_size[1]))
        entry = self._lookup_entry(sheet_key, name)
        if entry is None:
            return None

        cache_key = (sheet_key, entry["name"], width, height)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        crop = self._get_crop(sheet_key, entry)
        if crop is None:
            return None

        scaled = self._scale_contain(crop, (width, height))
        self._scaled_cache[cache_key] = scaled
        return scaled

    def _get_crop(self, sheet_key: str, entry: dict[str, Any]) -> Any | None:
        if pygame is None:
            return None

        cache_key = (sheet_key, entry["name"])
        cached = self._crop_cache.get(cache_key)
        if cached is not None:
            return cached

        sheet = self._ensure_sheet_loaded(sheet_key)
        rect = pygame.Rect(entry["x"], entry["y"], entry["width"], entry["height"])
        sheet_rect = sheet.get_rect()
        if not sheet_rect.contains(rect):
            raise ValueError(
                f"Sprite crop is out of bounds for {sheet_key} atlas: "
                f"{entry['name']} needs {rect.width}x{rect.height} at ({rect.x}, {rect.y}) "
                f"but atlas size is {sheet_rect.width}x{sheet_rect.height}."
            )
        crop = sheet.subsurface(rect).copy()
        self._crop_cache[cache_key] = crop
        return crop

    def _lookup_entry(self, sheet_key: str, name: str) -> dict[str, Any] | None:
        self._ensure_metadata_loaded()
        if sheet_key == "card":
            exact = self._card_entries_by_name.get(name)
            if exact is not None:
                return exact
            return self._card_entries_by_normalized.get(self._normalize_key(name))

        exact = self._relic_entries_by_name.get(name)
        if exact is not None:
            return exact
        return self._relic_entries_by_normalized.get(self._normalize_key(name))

    def _ensure_metadata_loaded(self) -> None:
        if self._metadata_loaded:
            return

        self._card_entries_by_name, self._card_entries_by_normalized = self._load_coordinates(
            CARD_ART_ATLAS_COORDINATES_PATH
        )
        self._relic_entries_by_name, self._relic_entries_by_normalized = self._load_coordinates(
            RELIC_SPRITE_COORDINATES_PATH
        )
        self._metadata_loaded = True

    def _validate_coverage(self) -> None:
        if self._validated:
            return

        self._validated = True

    def _ensure_sheet_loaded(self, sheet_key: str) -> Any:
        cached = self._sheet_surfaces.get(sheet_key)
        if cached is not None:
            return cached

        if pygame is None:
            raise RuntimeError("Pygame is required to load sprite sheet art.")

        path = CARD_ART_ATLAS_PATH if sheet_key == "card" else RELIC_SPRITE_SHEET_PATH
        try:
            image = pygame.image.load(str(path))
        except (FileNotFoundError, pygame.error) as error:
            raise ValueError(f"Unable to load sprite sheet: {path}") from error

        try:
            image = image.convert_alpha()
        except pygame.error:
            image = image.copy()

        self._sheet_surfaces[sheet_key] = image
        return image

    def _load_coordinates(self, csv_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        if not csv_path.exists():
            raise ValueError(f"Missing sprite sheet coordinates CSV: {csv_path}")

        by_name: dict[str, dict[str, Any]] = {}
        by_normalized: dict[str, dict[str, Any]] = {}
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required_columns = {"name", "x", "y", "width", "height"}
            if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
                raise ValueError(f"Sprite sheet coordinates CSV is missing required columns: {csv_path}")

            for row in reader:
                name = str(row.get("name", "")).strip()
                if not name:
                    continue
                entry = {
                    "name": name,
                    "x": int(float(row["x"])),
                    "y": int(float(row["y"])),
                    "width": int(float(row["width"])),
                    "height": int(float(row["height"])),
                }
                by_name[name] = entry
                by_normalized[self._normalize_key(name)] = entry

        return by_name, by_normalized

    def _load_expected_card_names(self) -> list[str]:
        with CARDS_DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("cards.json must contain a list when validating sprite coverage.")
        names = [str(entry.get("name", "")).strip() for entry in payload if isinstance(entry, dict)]
        return [name for name in names if name]

    def _load_expected_relic_names(self) -> list[str]:
        with RUN_MODIFIERS_DATA_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("run_modifiers.json must contain a list when validating sprite coverage.")
        names = [
            str(entry.get("name", "")).strip()
            for entry in payload
            if isinstance(entry, dict) and str(entry.get("type", "")).strip().lower() == "relic"
        ]
        return [name for name in names if name]

    def _normalize_key(self, name: str) -> str:
        return " ".join(str(name).strip().lower().split())

    def _scale_contain(self, surface: Any, target_size: tuple[int, int]) -> Any:
        src_width, src_height = surface.get_size()
        target_width, target_height = target_size
        if src_width <= 0 or src_height <= 0:
            return surface.copy()

        scale = min(target_width / src_width, target_height / src_height)
        scaled_width = max(1, int(src_width * scale))
        scaled_height = max(1, int(src_height * scale))
        if (scaled_width, scaled_height) == (src_width, src_height):
            return surface.copy()
        return pygame.transform.smoothscale(surface, (scaled_width, scaled_height))


sprite_sheet_assets = SpriteSheetAssets()
