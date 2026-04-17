from __future__ import annotations

import csv
import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    RELIC_CUTOUTS_ROOT,
    RELIC_SPRITE_COORDINATES_PATH,
    RELIC_SPRITE_SHEET_PATH,
    RUN_MODIFIERS_DATA_PATH,
)

YELLOW_BORDER_MIN = (180, 140, 0)
SEARCH_TOP_MARGIN = 88
SEARCH_BOTTOM_MARGIN = 28
SEARCH_SIDE_MARGIN = 10
FOREGROUND_THRESHOLD = 36
SOFT_ALPHA_THRESHOLD = 16
INCLUSION_PADDING = 42
OUTPUT_PADDING = 6
TEXT_COMPONENT_MAX_AREA = 650
BACKGROUND_COLOR = (13, 20, 33)


def _is_yellow_border(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, _alpha = pixel
    return red > YELLOW_BORDER_MIN[0] and green > YELLOW_BORDER_MIN[1] and blue < 120


def _distance_from_background(pixel: tuple[int, int, int, int]) -> float:
    red, green, blue, _alpha = pixel
    return (
        ((red - BACKGROUND_COLOR[0]) ** 2)
        + ((green - BACKGROUND_COLOR[1]) ** 2)
        + ((blue - BACKGROUND_COLOR[2]) ** 2)
    ) ** 0.5


def _connected_components(mask: list[list[bool]]) -> list[dict[str, object]]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    seen = [[False] * width for _ in range(height)]
    components: list[dict[str, object]] = []

    for y_pos in range(height):
        for x_pos in range(width):
            if not mask[y_pos][x_pos] or seen[y_pos][x_pos]:
                continue
            queue = deque([(x_pos, y_pos)])
            seen[y_pos][x_pos] = True
            area = 0
            min_x = max_x = x_pos
            min_y = max_y = y_pos
            while queue:
                current_x, current_y = queue.popleft()
                area += 1
                min_x = min(min_x, current_x)
                max_x = max(max_x, current_x)
                min_y = min(min_y, current_y)
                max_y = max(max_y, current_y)
                for next_x, next_y in (
                    (current_x + 1, current_y),
                    (current_x - 1, current_y),
                    (current_x, current_y + 1),
                    (current_x, current_y - 1),
                ):
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    if not mask[next_y][next_x] or seen[next_y][next_x]:
                        continue
                    seen[next_y][next_x] = True
                    queue.append((next_x, next_y))

            component_width = max_x - min_x + 1
            component_height = max_y - min_y + 1
            components.append(
                {
                    "area": area,
                    "bbox": (min_x, min_y, max_x, max_y),
                    "width": component_width,
                    "height": component_height,
                    "cx": (min_x + max_x) / 2,
                    "cy": (min_y + max_y) / 2,
                }
            )

    return components


def _load_sorted_relic_entries() -> list[dict[str, str]]:
    if not RELIC_SPRITE_COORDINATES_PATH.exists():
        raise ValueError(f"Missing relic coordinates CSV: {RELIC_SPRITE_COORDINATES_PATH}")

    with RELIC_SPRITE_COORDINATES_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        entries = [dict(row) for row in reader]

    required = {"name", "x", "y", "width", "height"}
    if not entries or not required.issubset(entries[0].keys()):
        raise ValueError("Relic coordinates CSV is missing required columns.")

    return sorted(entries, key=lambda entry: (int(float(entry["y"])), int(float(entry["x"]))))


def _load_relic_id_by_name() -> dict[str, str]:
    with RUN_MODIFIERS_DATA_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    mapping: dict[str, str] = {}
    for entry in payload:
        if not isinstance(entry, dict) or str(entry.get("type", "")).lower() != "relic":
            continue
        name = str(entry.get("name", "")).strip()
        modifier_id = str(entry.get("id", "")).strip()
        if name and modifier_id:
            mapping[name] = modifier_id
    return mapping


def _extract_cutout(sheet: Image.Image, slot_rect: tuple[int, int, int, int]) -> Image.Image:
    slot_left, slot_top, slot_right, slot_bottom = slot_rect
    crop = sheet.crop((slot_left, slot_top, slot_right + 1, slot_bottom + 1)).convert("RGBA")
    crop_width, crop_height = crop.size
    crop_pixels = crop.load()

    foreground_mask = [[False] * crop_width for _ in range(crop_height)]
    for y_pos in range(SEARCH_TOP_MARGIN, crop_height - SEARCH_BOTTOM_MARGIN):
        for x_pos in range(SEARCH_SIDE_MARGIN, crop_width - SEARCH_SIDE_MARGIN):
            pixel = crop_pixels[x_pos, y_pos]
            if _is_yellow_border(pixel):
                continue
            if _distance_from_background(pixel) > FOREGROUND_THRESHOLD:
                foreground_mask[y_pos][x_pos] = True

    components = [
        component
        for component in _connected_components(foreground_mask)
        if int(component["area"]) >= 15
    ]
    if not components:
        raise ValueError("Unable to isolate a relic silhouette from its slot.")

    target_x = crop_width / 2
    target_y = crop_height * 0.62
    primary = max(
        components,
        key=lambda component: float(component["area"])
        - (
            ((float(component["cx"]) - target_x) ** 2)
            + (((float(component["cy"]) - target_y) * 1.2) ** 2)
        )
        ** 0.5,
    )
    primary_left, primary_top, primary_right, primary_bottom = (
        int(value) for value in primary["bbox"]
    )

    included_components: list[dict[str, object]] = []
    for component in components:
        area = int(component["area"])
        bbox_left, bbox_top, bbox_right, bbox_bottom = (int(value) for value in component["bbox"])
        component_width = int(component["width"])
        component_height = int(component["height"])
        center_y = float(component["cy"])

        if center_y > crop_height - 42 and area < 500:
            continue
        if center_y < 96 and area < 500:
            continue
        if component_width > (component_height * 2.0) and component_height < 24 and area < TEXT_COMPONENT_MAX_AREA:
            continue
        if (
            bbox_left <= primary_right + INCLUSION_PADDING
            and bbox_right >= primary_left - INCLUSION_PADDING
            and bbox_top <= primary_bottom + INCLUSION_PADDING
            and bbox_bottom >= primary_top - INCLUSION_PADDING
        ):
            included_components.append(component)

    alpha_mask = Image.new("L", (crop_width, crop_height), 0)
    alpha_pixels = alpha_mask.load()
    for component in included_components:
        bbox_left, bbox_top, bbox_right, bbox_bottom = (
            int(value) for value in component["bbox"]
        )
        for y_pos in range(max(0, bbox_top - 2), min(crop_height, bbox_bottom + 3)):
            for x_pos in range(max(0, bbox_left - 2), min(crop_width, bbox_right + 3)):
                if y_pos < 84 or y_pos > crop_height - 22:
                    continue
                pixel = crop_pixels[x_pos, y_pos]
                if _is_yellow_border(pixel):
                    continue
                if _distance_from_background(pixel) > SOFT_ALPHA_THRESHOLD:
                    alpha_pixels[x_pos, y_pos] = 255

    cutout = Image.new("RGBA", (crop_width, crop_height), (0, 0, 0, 0))
    cutout_pixels = cutout.load()
    bbox: tuple[int, int, int, int] | None = None
    for y_pos in range(crop_height):
        for x_pos in range(crop_width):
            if alpha_pixels[x_pos, y_pos] == 0:
                continue
            cutout_pixels[x_pos, y_pos] = crop_pixels[x_pos, y_pos]
            if bbox is None:
                bbox = (x_pos, y_pos, x_pos, y_pos)
            else:
                bbox = (
                    min(bbox[0], x_pos),
                    min(bbox[1], y_pos),
                    max(bbox[2], x_pos),
                    max(bbox[3], y_pos),
                )

    if bbox is None:
        raise ValueError("Relic cutout alpha mask is empty.")

    left = max(0, bbox[0] - OUTPUT_PADDING)
    top = max(0, bbox[1] - OUTPUT_PADDING)
    right = min(crop_width, bbox[2] + OUTPUT_PADDING + 1)
    bottom = min(crop_height, bbox[3] + OUTPUT_PADDING + 1)
    return cutout.crop((left, top, right, bottom))


def export_relic_cutouts() -> list[Path]:
    sheet = Image.open(RELIC_SPRITE_SHEET_PATH).convert("RGBA")
    relic_entries = _load_sorted_relic_entries()
    relic_ids_by_name = _load_relic_id_by_name()

    RELIC_CUTOUTS_ROOT.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    for entry in relic_entries:
        relic_name = entry["name"]
        modifier_id = relic_ids_by_name.get(relic_name)
        if modifier_id is None:
            raise ValueError(f"No relic id found for sheet entry: {relic_name}")
        slot_rect = (
            int(float(entry["x"])),
            int(float(entry["y"])),
            int(float(entry["x"])) + int(float(entry["width"])) - 1,
            int(float(entry["y"])) + int(float(entry["height"])) - 1,
        )
        cutout = _extract_cutout(sheet, slot_rect)
        output_path = RELIC_CUTOUTS_ROOT / f"{modifier_id}.png"
        cutout.save(output_path)
        written_paths.append(output_path)

    return written_paths


if __name__ == "__main__":
    paths = export_relic_cutouts()
    for path in paths:
        print(path)
