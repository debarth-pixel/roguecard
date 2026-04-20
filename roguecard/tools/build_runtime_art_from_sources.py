from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (  # noqa: E402
    ASSETS_ROOT,
    CARD_ART_ATLAS_COORDINATES_PATH,
    CARD_ART_ATLAS_PATH,
    CARDS_DATA_PATH,
    RELIC_SPRITE_COORDINATES_PATH,
    RELIC_SPRITE_SHEET_PATH,
    RUN_MODIFIERS_DATA_PATH,
)

BACKGROUND_COLOR = (8, 19, 33, 255)
CARD_SOURCE_ROOT = ASSETS_ROOT / "generated" / "card_panels"
RELIC_SOURCE_ROOT = ASSETS_ROOT / "generated" / "relic_slots"


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load_json_list(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list payload in {path}.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _load_surface(path: Path) -> pygame.Surface:
    return pygame.image.load(str(path))


def _new_canvas(size: tuple[int, int]) -> pygame.Surface:
    canvas = pygame.Surface(size, pygame.SRCALPHA)
    canvas.fill(BACKGROUND_COLOR)
    return canvas


def _fit_cover(image: pygame.Surface, target_size: tuple[int, int]) -> pygame.Surface:
    src_width, src_height = image.get_size()
    target_width, target_height = target_size
    scale = max(target_width / src_width, target_height / src_height)
    scaled_width = max(1, round(src_width * scale))
    scaled_height = max(1, round(src_height * scale))
    scaled = pygame.transform.smoothscale(image, (scaled_width, scaled_height))
    canvas = pygame.Surface(target_size, pygame.SRCALPHA)
    canvas.blit(
        scaled,
        ((target_width - scaled_width) // 2, (target_height - scaled_height) // 2),
    )
    return canvas


def _fit_contain(image: pygame.Surface, target_size: tuple[int, int]) -> pygame.Surface:
    src_width, src_height = image.get_size()
    target_width, target_height = target_size
    scale = min(target_width / src_width, target_height / src_height)
    scaled_width = max(1, round(src_width * scale))
    scaled_height = max(1, round(src_height * scale))
    scaled = pygame.transform.smoothscale(image, (scaled_width, scaled_height))
    canvas = _new_canvas(target_size)
    canvas.blit(
        scaled,
        ((target_width - scaled_width) // 2, (target_height - scaled_height) // 2),
    )
    return canvas


def _calc_canvas_size(entries: list[dict[str, str]]) -> tuple[int, int]:
    width = max(int(float(entry["x"])) + int(float(entry["width"])) for entry in entries) + 10
    height = max(int(float(entry["y"])) + int(float(entry["height"])) for entry in entries) + 10
    return width, height


def _load_card_ids_by_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in _load_json_list(CARDS_DATA_PATH):
        name = str(entry.get("name", "")).strip()
        card_id = str(entry.get("id", "")).strip()
        if name and card_id:
            mapping[name] = card_id
    return mapping


def _load_relic_ids_by_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in _load_json_list(RUN_MODIFIERS_DATA_PATH):
        if str(entry.get("type", "")).strip().lower() != "relic":
            continue
        name = str(entry.get("name", "")).strip()
        relic_id = str(entry.get("id", "")).strip()
        if name and relic_id:
            mapping[name] = relic_id
    return mapping


def _build_card_atlas() -> list[str]:
    entries = _load_csv_rows(CARD_ART_ATLAS_COORDINATES_PATH)
    current_atlas = _load_surface(CARD_ART_ATLAS_PATH) if CARD_ART_ATLAS_PATH.exists() else None
    card_ids_by_name = _load_card_ids_by_name()
    output = _new_canvas(_calc_canvas_size(entries))
    missing: list[str] = []

    for entry in entries:
        name = str(entry["name"]).strip()
        card_id = card_ids_by_name.get(name)
        if not card_id:
            missing.append(name)
            continue
        x_pos = int(float(entry["x"]))
        y_pos = int(float(entry["y"]))
        width = int(float(entry["width"]))
        height = int(float(entry["height"]))
        source_path = CARD_SOURCE_ROOT / f"{card_id}.png"
        panel: pygame.Surface | None = None
        if source_path.exists():
            panel = _fit_cover(_load_surface(source_path), (width, height))
        elif current_atlas is not None:
            current_box = pygame.Rect(x_pos, y_pos, width, height)
            if current_box.right <= current_atlas.get_width() and current_box.bottom <= current_atlas.get_height():
                panel = current_atlas.subsurface(current_box).copy()
        if panel is None:
            missing.append(card_id)
            continue
        output.blit(panel, (x_pos, y_pos))

    pygame.image.save(output, str(CARD_ART_ATLAS_PATH))
    return missing


def _build_relic_sheet() -> list[str]:
    entries = _load_csv_rows(RELIC_SPRITE_COORDINATES_PATH)
    current_sheet = _load_surface(RELIC_SPRITE_SHEET_PATH) if RELIC_SPRITE_SHEET_PATH.exists() else None
    relic_ids_by_name = _load_relic_ids_by_name()
    output = _new_canvas(_calc_canvas_size(entries))
    missing: list[str] = []

    for entry in entries:
        name = str(entry["name"]).strip()
        relic_id = relic_ids_by_name.get(name)
        if not relic_id:
            missing.append(name)
            continue
        x_pos = int(float(entry["x"]))
        y_pos = int(float(entry["y"]))
        width = int(float(entry["width"]))
        height = int(float(entry["height"]))
        source_path = RELIC_SOURCE_ROOT / f"{relic_id}.png"
        panel: pygame.Surface | None = None
        if source_path.exists():
            panel = _fit_contain(_load_surface(source_path), (width, height))
        elif current_sheet is not None:
            current_box = pygame.Rect(x_pos, y_pos, width, height)
            if current_box.right <= current_sheet.get_width() and current_box.bottom <= current_sheet.get_height():
                panel = current_sheet.subsurface(current_box).copy()
        if panel is None:
            missing.append(relic_id)
            continue
        output.blit(panel, (x_pos, y_pos))

    pygame.image.save(output, str(RELIC_SPRITE_SHEET_PATH))
    return missing


def main() -> int:
    card_missing = _build_card_atlas()
    relic_missing = _build_relic_sheet()
    if card_missing or relic_missing:
        print("Missing card art sources:", ", ".join(card_missing) if card_missing else "none")
        print("Missing relic art sources:", ", ".join(relic_missing) if relic_missing else "none")
        return 1
    print("Runtime atlases rebuilt successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
