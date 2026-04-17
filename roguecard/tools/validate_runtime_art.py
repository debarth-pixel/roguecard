from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (  # noqa: E402
    CARD_ART_ATLAS_COORDINATES_PATH,
    CARD_ART_ATLAS_PATH,
    CARDS_DATA_PATH,
    RELIC_CUTOUTS_ROOT,
    RELIC_SPRITE_COORDINATES_PATH,
    RELIC_SPRITE_SHEET_PATH,
    RUN_MODIFIERS_DATA_PATH,
)


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load_json_list(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list payload in {path}.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _assert_in_bounds(image: Image.Image, entry: dict[str, str]) -> None:
    x_pos = int(float(entry["x"]))
    y_pos = int(float(entry["y"]))
    width = int(float(entry["width"]))
    height = int(float(entry["height"]))
    if x_pos < 0 or y_pos < 0 or x_pos + width > image.width or y_pos + height > image.height:
        raise ValueError(f"Out-of-bounds atlas entry: {entry['name']}")


def validate() -> None:
    cards = _load_json_list(CARDS_DATA_PATH)
    relics = [
        entry
        for entry in _load_json_list(RUN_MODIFIERS_DATA_PATH)
        if str(entry.get("type", "")).strip().lower() == "relic"
    ]
    card_entries = _load_csv_rows(CARD_ART_ATLAS_COORDINATES_PATH)
    relic_entries = _load_csv_rows(RELIC_SPRITE_COORDINATES_PATH)
    card_atlas = Image.open(CARD_ART_ATLAS_PATH).convert("RGBA")
    relic_sheet = Image.open(RELIC_SPRITE_SHEET_PATH).convert("RGBA")

    card_names = {str(entry.get("name", "")).strip() for entry in cards}
    relic_names = {str(entry.get("name", "")).strip() for entry in relics}
    atlas_card_names = {str(entry["name"]).strip() for entry in card_entries}
    atlas_relic_names = {str(entry["name"]).strip() for entry in relic_entries}

    missing_cards = sorted(card_names - atlas_card_names)
    missing_relics = sorted(relic_names - atlas_relic_names)
    if missing_cards:
        raise ValueError(f"Missing card atlas entries: {', '.join(missing_cards)}")
    if missing_relics:
        raise ValueError(f"Missing relic atlas entries: {', '.join(missing_relics)}")

    for entry in card_entries:
        _assert_in_bounds(card_atlas, entry)
    for entry in relic_entries:
        _assert_in_bounds(relic_sheet, entry)

    missing_cutouts = []
    for relic in relics:
        relic_id = str(relic.get("id", "")).strip()
        if relic_id and not (RELIC_CUTOUTS_ROOT / f"{relic_id}.png").exists():
            missing_cutouts.append(relic_id)
    if missing_cutouts:
        raise ValueError(f"Missing relic cutouts: {', '.join(missing_cutouts)}")

    print(
        f"Validated {len(card_entries)} card atlas entries, {len(relic_entries)} relic slots, and {len(relics)} relic cutouts."
    )


if __name__ == "__main__":
    validate()
