from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

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

BACKGROUND_COLOR = "#081321"
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


def _fit_cover(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(
        image.convert("RGBA"),
        target_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def _fit_contain(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", target_size, BACKGROUND_COLOR)
    contained = ImageOps.contain(
        image.convert("RGBA"),
        target_size,
        method=Image.Resampling.LANCZOS,
    )
    offset_x = (target_size[0] - contained.width) // 2
    offset_y = (target_size[1] - contained.height) // 2
    canvas.alpha_composite(contained, (offset_x, offset_y))
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
    current_atlas = Image.open(CARD_ART_ATLAS_PATH).convert("RGBA") if CARD_ART_ATLAS_PATH.exists() else None
    card_ids_by_name = _load_card_ids_by_name()
    output = Image.new("RGBA", _calc_canvas_size(entries), BACKGROUND_COLOR)
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
        panel: Image.Image | None = None
        if source_path.exists():
            panel = _fit_cover(Image.open(source_path), (width, height))
        elif current_atlas is not None:
            current_box = (x_pos, y_pos, x_pos + width, y_pos + height)
            if current_box[2] <= current_atlas.width and current_box[3] <= current_atlas.height:
                panel = current_atlas.crop(current_box)
        if panel is None:
            missing.append(card_id)
            continue
        output.alpha_composite(panel.convert("RGBA"), (x_pos, y_pos))

    output.save(CARD_ART_ATLAS_PATH)
    return missing


def _build_relic_sheet() -> list[str]:
    entries = _load_csv_rows(RELIC_SPRITE_COORDINATES_PATH)
    current_sheet = Image.open(RELIC_SPRITE_SHEET_PATH).convert("RGBA") if RELIC_SPRITE_SHEET_PATH.exists() else None
    relic_ids_by_name = _load_relic_ids_by_name()
    output = Image.new("RGBA", _calc_canvas_size(entries), BACKGROUND_COLOR)
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
        panel: Image.Image | None = None
        if source_path.exists():
            panel = _fit_contain(Image.open(source_path), (width, height))
        elif current_sheet is not None:
            current_box = (x_pos, y_pos, x_pos + width, y_pos + height)
            if current_box[2] <= current_sheet.width and current_box[3] <= current_sheet.height:
                panel = current_sheet.crop(current_box)
        if panel is None:
            missing.append(relic_id)
            continue
        output.alpha_composite(panel.convert("RGBA"), (x_pos, y_pos))

    output.save(RELIC_SPRITE_SHEET_PATH)
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
