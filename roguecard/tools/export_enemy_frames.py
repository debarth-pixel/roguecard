from __future__ import annotations

import math
import os
import shutil
import sys
from collections import deque
from pathlib import Path
from typing import Any

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import ASSETS_ROOT  # noqa: E402

ENEMY_ASSETS_ROOT = ASSETS_ROOT / "enemies"
ENEMY_SOURCE_ARCHIVE_ROOT = ENEMY_ASSETS_ROOT / "_source"

GRID_3X2_LAYOUT = {
    "cell_width": 512,
    "cell_height": 512,
    "columns": 3,
    "rows": 2,
}

EDGE_SAMPLE_STEP = 24
EDGE_SAMPLE_INSET = 10
BG_LOCAL_TOLERANCE = 18
BG_GLOBAL_TOLERANCE = 80
BG_SEED_TOLERANCE = 36
BG_CHANNEL_SPREAD_TOLERANCE = 104
BG_ISLAND_TOLERANCE = 28
BG_ISLAND_NEIGHBOR_MIN = 2


def _enemy_export_definition(
    source_filename: str,
    frames: dict[str, int],
    *,
    layout: dict[str, int] | None = None,
    source_rects: list[tuple[int, int, int, int]] | None = None,
    extra_source_rects: list[tuple[int, int, int, int]] | None = None,
    frame_focus_points: dict[int, tuple[int, int]] | None = None,
    component_limits: dict[str, int] | None = None,
    cleanup_bright_islands: bool = False,
) -> dict[str, Any]:
    return {
        "source_filename": source_filename,
        "frames": dict(frames),
        "layout": dict(layout or GRID_3X2_LAYOUT),
        "source_rects": list(source_rects or []),
        "extra_source_rects": list(extra_source_rects or []),
        "frame_focus_points": dict(frame_focus_points or {}),
        "component_limits": dict(component_limits or {}),
        "cleanup_bright_islands": cleanup_bright_islands,
    }


ENEMY_EXPORTS = {
    "audit_hound": _enemy_export_definition(
        "audit_hound.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "trace_bite": 4,
            "ledger_sweep": 2,
            "compliance_leap": 3,
        },
    ),
    "compliance_engine_ax9": _enemy_export_definition(
        "AX-9.png",
        {
            "idle": 1,
            "damage": 1,
            "dead": 7,
            "barrier_cycle": 2,
            "pacify_burst": 3,
            "deploy_node": 4,
            "null_wave": 5,
            "overdrive_cannon": 6,
        },
        extra_source_rects=[(384, 640, 768, 352)],
        frame_focus_points={7: (384, 200)},
    ),
    "dune_raider": _enemy_export_definition(
        "dune_raider.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "shiv": 2,
            "sand_throw": 3,
        },
    ),
    "dust_saboteur": _enemy_export_definition(
        "dust_sabotuer.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "scrap_dump": 2,
            "cut_wire": 3,
            "duck_cover": 4,
        },
    ),
    "embersnout": _enemy_export_definition(
        "embersnout.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "cinder_spit": 2,
            "flare_hide": 3,
            "fire_up": 4,
        },
    ),
    "relay_vulture": _enemy_export_definition(
        "relay_vulture.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "sightline": 2,
            "dive_fire": 3,
            "peck": 4,
        },
        component_limits={"sightline": 2},
    ),
    "salvage_bulwark": _enemy_export_definition(
        "salvage_bulwark.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "brace_plate": 2,
            "ram": 3,
        },
    ),
    "sandpack_alpha": _enemy_export_definition(
        "sandpack_alpha.png",
        {
            "idle": 1,
            "damage": 6,
            "dead": 7,
            "call_hound": 2,
            "feral_focus": 2,
            "rake": 3,
            "alpha_maul": 4,
            "blood_surge": 5,
        },
        extra_source_rects=[(256, 672, 1024, 336)],
        frame_focus_points={5: (256, 112), 7: (512, 180)},
    ),
    "scrap_ticker": _enemy_export_definition(
        "scrap_ticker.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "target_ping": 2,
            "buzz_saw": 3,
        },
        component_limits={"target_ping": 2},
        cleanup_bright_islands=True,
    ),
    "signal_junker": _enemy_export_definition(
        "signal_junker.png",
        {
            "idle": 1,
            "damage": 5,
            "dead": 6,
            "dead_channel": 2,
            "lag_spike": 3,
            "paint_lock": 4,
        },
        component_limits={"dead_channel": 2, "paint_lock": 2},
        cleanup_bright_islands=True,
    ),
    "waste_leech": _enemy_export_definition(
        "waste_leech.png",
        {
            "idle": 1,
            "damage": 4,
            "dead": 6,
            "sip": 2,
            "coil": 3,
            "gorge": 5,
        },
    ),
    "wastes_colossus": _enemy_export_definition(
        "waste_colossus.png",
        {
            "idle": 1,
            "damage": 8,
            "dead": 9,
            "sand_plating": 2,
            "searchlight": 3,
            "grinding_tread": 4,
            "flare_vent": 5,
            "loose_tickers": 6,
        },
        source_rects=[
            (0, 0, 512, 341),
            (512, 0, 512, 341),
            (1024, 0, 512, 341),
            (0, 341, 512, 341),
            (512, 341, 512, 341),
            (1024, 341, 512, 341),
            (0, 682, 512, 342),
            (512, 682, 512, 342),
            (1024, 682, 512, 342),
        ],
    ),
}


def _source_path(filename: str) -> Path:
    direct_path = ENEMY_ASSETS_ROOT / filename
    if direct_path.exists():
        return direct_path
    archived_path = ENEMY_SOURCE_ARCHIVE_ROOT / filename
    return archived_path


def _grid_source_rects(sheet: pygame.Surface, layout: dict[str, int]) -> list[pygame.Rect]:
    cell_width = int(layout["cell_width"])
    cell_height = int(layout["cell_height"])
    columns = int(layout["columns"])
    rows = int(layout["rows"])
    required_width = cell_width * columns
    required_height = cell_height * rows
    if sheet.get_width() < required_width or sheet.get_height() < required_height:
        raise ValueError(
            f"Sheet {sheet.get_size()} is too small for layout {columns}x{rows} with cell {cell_width}x{cell_height}."
        )
    rects: list[pygame.Rect] = []
    for row in range(rows):
        for column in range(columns):
            rects.append(pygame.Rect(column * cell_width, row * cell_height, cell_width, cell_height))
    return rects


def _source_rects_for_export(sheet: pygame.Surface, config: dict[str, Any]) -> list[pygame.Rect]:
    if config["source_rects"]:
        return [pygame.Rect(*rect) for rect in config["source_rects"]]
    rects = _grid_source_rects(sheet, config["layout"])
    rects.extend(pygame.Rect(*rect) for rect in config["extra_source_rects"])
    return rects


def _background_sample_points(width: int, height: int) -> list[tuple[int, int]]:
    if width <= 0 or height <= 0:
        return []
    inset_x = min(EDGE_SAMPLE_INSET, max(0, width - 1))
    inset_y = min(EDGE_SAMPLE_INSET, max(0, height - 1))
    sample_points: set[tuple[int, int]] = {
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
        (inset_x, inset_y),
        (width - 1 - inset_x, inset_y),
        (inset_x, height - 1 - inset_y),
        (width - 1 - inset_x, height - 1 - inset_y),
    }
    for x in range(0, width, EDGE_SAMPLE_STEP):
        sample_points.add((x, 0))
        sample_points.add((x, height - 1))
    for y in range(0, height, EDGE_SAMPLE_STEP):
        sample_points.add((0, y))
        sample_points.add((width - 1, y))
    return sorted(sample_points)


def _has_authored_transparency(surface: pygame.Surface) -> bool:
    for x, y in _background_sample_points(surface.get_width(), surface.get_height()):
        if surface.get_at((x, y)).a == 0:
            return True
    return False


def _color_tuple(color: pygame.Color) -> tuple[int, int, int]:
    return color.r, color.g, color.b


def _color_delta(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]), abs(left[2] - right[2]))


def _channel_spread(color: tuple[int, int, int]) -> int:
    return max(color) - min(color)


def _within_global_background_range(
    color: tuple[int, int, int],
    background_palette: list[tuple[int, int, int]],
    tolerance: int,
) -> bool:
    return any(_color_delta(color, sample) <= tolerance for sample in background_palette)


def _cleanup_background(frame_surface: pygame.Surface, *, cleanup_bright_islands: bool = False) -> pygame.Surface:
    if _has_authored_transparency(frame_surface):
        return frame_surface

    width = frame_surface.get_width()
    height = frame_surface.get_height()
    if width <= 0 or height <= 0:
        return frame_surface

    background_palette = [
        _color_tuple(frame_surface.get_at((x, y)))
        for x, y in _background_sample_points(width, height)
    ]
    if not background_palette:
        return frame_surface

    visited = bytearray(width * height)
    pending: deque[tuple[int, int, tuple[int, int, int]]] = deque()

    def enqueue_seed(px: int, py: int) -> None:
        color = frame_surface.get_at((px, py))
        color_tuple = _color_tuple(color)
        if (
            color.a != 0
            and _channel_spread(color_tuple) > BG_CHANNEL_SPREAD_TOLERANCE
            and not _within_global_background_range(color_tuple, background_palette, BG_SEED_TOLERANCE)
        ):
            return
        index = (py * width) + px
        if visited[index]:
            return
        visited[index] = 1
        pending.append((px, py, color_tuple))

    def enqueue_neighbor(px: int, py: int, previous_color: tuple[int, int, int]) -> None:
        index = (py * width) + px
        if visited[index]:
            return
        color = frame_surface.get_at((px, py))
        color_tuple = _color_tuple(color)
        if color.a != 0:
            if _channel_spread(color_tuple) > BG_CHANNEL_SPREAD_TOLERANCE:
                return
            if _color_delta(color_tuple, previous_color) > BG_LOCAL_TOLERANCE:
                return
            if not _within_global_background_range(color_tuple, background_palette, BG_GLOBAL_TOLERANCE):
                return
        visited[index] = 1
        pending.append((px, py, color_tuple))

    frame_surface.lock()
    try:
        for x in range(width):
            enqueue_seed(x, 0)
            enqueue_seed(x, height - 1)
        for y in range(height):
            enqueue_seed(0, y)
            enqueue_seed(width - 1, y)

        while pending:
            x, y, color_tuple = pending.popleft()
            frame_surface.set_at((x, y), (0, 0, 0, 0))
            if x > 0:
                enqueue_neighbor(x - 1, y, color_tuple)
            if x + 1 < width:
                enqueue_neighbor(x + 1, y, color_tuple)
            if y > 0:
                enqueue_neighbor(x, y - 1, color_tuple)
            if y + 1 < height:
                enqueue_neighbor(x, y + 1, color_tuple)
    finally:
        frame_surface.unlock()
    if cleanup_bright_islands:
        _remove_background_islands(frame_surface, background_palette)
    return frame_surface


def _remove_background_islands(
    frame_surface: pygame.Surface,
    background_palette: list[tuple[int, int, int]],
) -> None:
    width = frame_surface.get_width()
    height = frame_surface.get_height()
    pixels_to_clear: list[tuple[int, int]] = []

    def matches_background(px: int, py: int) -> bool:
        color = frame_surface.get_at((px, py))
        if color.a == 0:
            return False
        color_tuple = _color_tuple(color)
        if _channel_spread(color_tuple) > BG_CHANNEL_SPREAD_TOLERANCE:
            return False
        if max(color_tuple) < 180:
            return False
        return _within_global_background_range(color_tuple, background_palette, BG_ISLAND_TOLERANCE)

    frame_surface.lock()
    try:
        for y in range(height):
            for x in range(width):
                if not matches_background(x, y):
                    continue
                background_neighbors = 0
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    if matches_background(nx, ny) or frame_surface.get_at((nx, ny)).a == 0:
                        background_neighbors += 1
                if background_neighbors >= BG_ISLAND_NEIGHBOR_MIN:
                    pixels_to_clear.append((x, y))
        for x, y in pixels_to_clear:
            frame_surface.set_at((x, y), (0, 0, 0, 0))
    finally:
        frame_surface.unlock()


def _nearest_focus_pixel(surface: pygame.Surface, focus_point: tuple[int, int]) -> tuple[int, int] | None:
    width = surface.get_width()
    height = surface.get_height()
    if width <= 0 or height <= 0:
        return None

    focus_x = max(0, min(width - 1, int(focus_point[0])))
    focus_y = max(0, min(height - 1, int(focus_point[1])))
    if surface.get_at((focus_x, focus_y)).a > 0:
        return focus_x, focus_y

    nearest: tuple[int, int] | None = None
    nearest_distance: int | None = None
    surface.lock()
    try:
        for y in range(height):
            for x in range(width):
                if surface.get_at((x, y)).a == 0:
                    continue
                distance = ((x - focus_x) * (x - focus_x)) + ((y - focus_y) * (y - focus_y))
                if nearest_distance is None or distance < nearest_distance:
                    nearest = (x, y)
                    nearest_distance = distance
    finally:
        surface.unlock()
    return nearest


def _isolate_focus_component(surface: pygame.Surface, focus_point: tuple[int, int]) -> pygame.Surface:
    seed = _nearest_focus_pixel(surface, focus_point)
    if seed is None:
        return surface

    width = surface.get_width()
    height = surface.get_height()
    visited = bytearray(width * height)
    pending: deque[tuple[int, int]] = deque([seed])
    visited[(seed[1] * width) + seed[0]] = 1
    isolated = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    surface.lock()
    isolated.lock()
    try:
        while pending:
            x, y = pending.popleft()
            color = surface.get_at((x, y))
            if color.a == 0:
                continue
            isolated.set_at((x, y), color)
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                index = (ny * width) + nx
                if visited[index]:
                    continue
                visited[index] = 1
                if surface.get_at((nx, ny)).a > 0:
                    pending.append((nx, ny))
    finally:
        isolated.unlock()
        surface.unlock()
    return isolated


def _retain_largest_components(
    surface: pygame.Surface,
    limit: int,
    *,
    focus_point: tuple[float, float] | None = None,
) -> pygame.Surface:
    if limit <= 0:
        return pygame.Surface(surface.get_size(), pygame.SRCALPHA)

    width = surface.get_width()
    height = surface.get_height()
    visited = bytearray(width * height)
    components: list[dict[str, Any]] = []

    surface.lock()
    try:
        for y in range(height):
            for x in range(width):
                index = (y * width) + x
                if visited[index]:
                    continue
                visited[index] = 1
                if surface.get_at((x, y)).a == 0:
                    continue
                pending: deque[tuple[int, int]] = deque([(x, y)])
                component_pixels: list[tuple[int, int]] = []
                min_x = x
                min_y = y
                max_x = x
                max_y = y
                while pending:
                    px, py = pending.popleft()
                    if surface.get_at((px, py)).a == 0:
                        continue
                    component_pixels.append((px, py))
                    min_x = min(min_x, px)
                    min_y = min(min_y, py)
                    max_x = max(max_x, px)
                    max_y = max(max_y, py)
                    for nx, ny in (
                        (px - 1, py),
                        (px + 1, py),
                        (px, py - 1),
                        (px, py + 1),
                        (px - 1, py - 1),
                        (px + 1, py - 1),
                        (px - 1, py + 1),
                        (px + 1, py + 1),
                    ):
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        neighbor_index = (ny * width) + nx
                        if visited[neighbor_index]:
                            continue
                        visited[neighbor_index] = 1
                        if surface.get_at((nx, ny)).a > 0:
                            pending.append((nx, ny))
                if component_pixels:
                    components.append(
                        {
                            "pixels": component_pixels,
                            "size": len(component_pixels),
                            "bounds": pygame.Rect(min_x, min_y, (max_x - min_x) + 1, (max_y - min_y) + 1),
                        }
                    )
    finally:
        surface.unlock()

    if len(components) <= limit:
        return surface

    if focus_point is None:
        focus_point = (width / 2.0, height * 0.45)

    def primary_component_score(component: dict[str, Any]) -> float:
        bounds: pygame.Rect = component["bounds"]
        center_x = bounds.centerx
        center_y = bounds.centery
        distance = math.hypot(center_x - focus_point[0], center_y - focus_point[1])
        return float(component["size"]) - (distance * 6.0)

    primary_component = max(components, key=primary_component_score)
    kept_components = [primary_component]
    if limit > 1:
        extras = [component for component in components if component is not primary_component]
        extras.sort(key=lambda component: int(component["size"]), reverse=True)
        kept_components.extend(extras[: limit - 1])

    kept_pixels = set()
    for component in kept_components:
        kept_pixels.update(component["pixels"])

    isolated = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    surface.lock()
    isolated.lock()
    try:
        for x, y in kept_pixels:
            isolated.set_at((x, y), surface.get_at((x, y)))
    finally:
        isolated.unlock()
        surface.unlock()
    return isolated


def _prepare_frame_surface(
    sheet: pygame.Surface,
    source_rect: pygame.Rect,
    *,
    focus_point: tuple[int, int] | None = None,
    component_limit: int = 1,
    cleanup_bright_islands: bool = False,
) -> dict[str, Any]:
    full_surface = pygame.Surface(source_rect.size, pygame.SRCALPHA)
    full_surface.blit(sheet, (0, 0), source_rect)
    _cleanup_background(full_surface, cleanup_bright_islands=cleanup_bright_islands)
    if focus_point is not None:
        full_surface = _isolate_focus_component(full_surface, focus_point)
    full_surface = pygame.transform.flip(full_surface, True, False)
    full_surface = _retain_largest_components(full_surface, component_limit)
    bounds = full_surface.get_bounding_rect()
    if bounds.width <= 0 or bounds.height <= 0:
        bounds = pygame.Rect(max(0, full_surface.get_width() // 2), max(0, full_surface.get_height() - 1), 1, 1)
    return {
        "surface": full_surface,
        "bounds": bounds,
        "anchor_x": full_surface.get_width() / 2.0,
        "anchor_y": float(full_surface.get_height()),
    }


def _aligned_canvas_size(frame_data: dict[str, dict[str, Any]]) -> tuple[int, int, float, float]:
    min_left = 0.0
    min_top = 0.0
    max_right = 1.0
    max_bottom = 1.0
    first = True
    for data in frame_data.values():
        bounds: pygame.Rect = data["bounds"]
        anchor_x = float(data["anchor_x"])
        anchor_y = float(data["anchor_y"])
        left = bounds.left - anchor_x
        top = bounds.top - anchor_y
        right = bounds.right - anchor_x
        bottom = bounds.bottom - anchor_y
        if first:
            min_left = left
            min_top = top
            max_right = right
            max_bottom = bottom
            first = False
        else:
            min_left = min(min_left, left)
            min_top = min(min_top, top)
            max_right = max(max_right, right)
            max_bottom = max(max_bottom, bottom)
    width = max(1, int(math.ceil(max_right - min_left)))
    height = max(1, int(math.ceil(max_bottom - min_top)))
    return width, height, min_left, min_top


def _clear_output_dir(enemy_dir: Path) -> None:
    if not enemy_dir.exists():
        enemy_dir.mkdir(parents=True, exist_ok=True)
        return
    for png_path in enemy_dir.glob("*.png"):
        png_path.unlink()


def _export_enemy(enemy_id: str, config: dict[str, Any]) -> int:
    source_path = _source_path(config["source_filename"])
    if not source_path.exists():
        raise FileNotFoundError(f"Missing source sheet for {enemy_id}: {source_path}")

    sheet = pygame.image.load(str(source_path))
    source_rects = _source_rects_for_export(sheet, config)
    focus_points = config["frame_focus_points"]
    component_limits = config["component_limits"]
    cleanup_bright_islands = bool(config.get("cleanup_bright_islands", False))

    prepared_by_output: dict[str, dict[str, Any]] = {}
    for output_name, frame_index in config["frames"].items():
        zero_based_index = int(frame_index) - 1
        if zero_based_index < 0 or zero_based_index >= len(source_rects):
            raise IndexError(f"{enemy_id}:{output_name} requested missing frame index {frame_index}.")
        prepared_by_output[output_name] = _prepare_frame_surface(
            sheet,
            source_rects[zero_based_index],
            focus_point=focus_points.get(int(frame_index)),
            component_limit=int(component_limits.get(output_name, 1)),
            cleanup_bright_islands=cleanup_bright_islands,
        )

    canvas_width, canvas_height, min_left, min_top = _aligned_canvas_size(prepared_by_output)
    enemy_dir = ENEMY_ASSETS_ROOT / enemy_id
    _clear_output_dir(enemy_dir)

    exported = 0
    for output_name, data in prepared_by_output.items():
        canvas = pygame.Surface((canvas_width, canvas_height), pygame.SRCALPHA)
        bounds: pygame.Rect = data["bounds"]
        trimmed = data["surface"].subsurface(bounds).copy()
        x_pos = int(round((bounds.left - float(data["anchor_x"])) - min_left))
        y_pos = int(round((bounds.top - float(data["anchor_y"])) - min_top))
        canvas.blit(trimmed, (x_pos, y_pos))
        pygame.image.save(canvas, str(enemy_dir / f"{output_name}.png"))
        exported += 1
    return exported


def _archive_source_sheets() -> int:
    ENEMY_SOURCE_ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    moved = 0
    for config in ENEMY_EXPORTS.values():
        filename = str(config["source_filename"])
        current_path = ENEMY_ASSETS_ROOT / filename
        archived_path = ENEMY_SOURCE_ARCHIVE_ROOT / filename
        if not current_path.exists():
            continue
        archived_path.parent.mkdir(parents=True, exist_ok=True)
        if archived_path.exists():
            archived_path.unlink()
        shutil.move(str(current_path), str(archived_path))
        moved += 1
    return moved


def main() -> int:
    pygame.init()
    total_exported = 0
    for enemy_id, config in ENEMY_EXPORTS.items():
        exported = _export_enemy(enemy_id, config)
        total_exported += exported
        print(f"Exported {exported:2d} frames for {enemy_id}.")
    moved = _archive_source_sheets()
    print(f"Archived {moved} source sheets to {ENEMY_SOURCE_ARCHIVE_ROOT}.")
    print(f"Exported {total_exported} runtime enemy frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
