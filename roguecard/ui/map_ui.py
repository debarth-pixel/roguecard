from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_asset_path


class MapUI:
    NODE_COLORS = {
        "combat": (210, 70, 70),
        "elite": (220, 140, 40),
        "shop": (60, 180, 140),
        "event": (70, 120, 220),
        "boss": (180, 60, 180),
    }

    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._image_cache: dict[str, Any] = {}

    def preload_assets(self) -> None:
        if pygame is None:
            return

        asset_paths = [
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("ui", "node_combat.png"),
            resolve_asset_path("ui", "node_elite.png"),
            resolve_asset_path("ui", "node_shop.png"),
            resolve_asset_path("ui", "node_event.png"),
            resolve_asset_path("ui", "node_boss.png"),
        ]
        for path in asset_paths:
            self._load_image(path)

    def handle_event(self, event: Any, map_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None or event.type != pygame.KEYDOWN:
            return None

        if pygame.K_1 <= event.key <= pygame.K_9:
            selection_index = event.key - pygame.K_1
            available = map_state["available_node_ids"]
            if selection_index < len(available):
                return {"type": "select_node", "node_id": available[selection_index]}

        return None

    def build_layout(self, map_state: dict[str, Any]) -> dict[str, Any]:
        nodes = map_state["nodes"]
        available = set(map_state["available_node_ids"])
        visited = set(map_state.get("visited_node_ids", []))
        selected = map_state.get("selected_node_id")

        return {
            "status_message": map_state.get("status_message", ""),
            "available_labels": [
                f"{index + 1}. {node_id} ({nodes[node_id]['node_type']})"
                for index, node_id in enumerate(map_state["available_node_ids"])
            ],
            "selected_label": None if selected is None else f"Selected: {selected}",
            "node_statuses": {
                node_id: self._node_status(node_id, available, visited, selected)
                for node_id in nodes
            },
            "node_count": len(nodes),
        }

    def render(self, surface: Any, map_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts()
        layout = self.build_layout(map_state)

        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 220))
        info_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 180))

        surface.blit(background, (0, 0))
        surface.blit(panel, (24, 24))
        surface.blit(info_panel, (24, 520))

        self._draw_text(surface, layout["status_message"], (44, 46), self._small_font, width=320)
        self._draw_text(surface, f"Reachable Nodes: {layout['node_count']}", (44, 128), self._font)
        if layout["selected_label"] is not None:
            self._draw_text(surface, layout["selected_label"], (44, 166), self._small_font, width=320)

        nodes = map_state["nodes"]
        positions = self._node_positions(nodes)

        for node_id, node in nodes.items():
            start = positions[node_id]
            for next_node_id in node["next_nodes"]:
                pygame.draw.line(surface, (110, 110, 130), start, positions[next_node_id], 3)

        for node_id, node in nodes.items():
            center = positions[node_id]
            status = layout["node_statuses"][node_id]
            self._draw_node(surface, node, center, status)

        self._draw_text(surface, "Available Routes", (44, 544), self._font)
        for index, label in enumerate(layout["available_labels"]):
            self._draw_text(surface, label, (44, 584 + (index * 24)), self._small_font, width=320)

    def _draw_node(
        self,
        surface: Any,
        node: dict[str, Any],
        center: tuple[int, int],
        status: str,
    ) -> None:
        radius = 48
        outline_color = {
            "selected": (255, 255, 255),
            "available": (255, 230, 110),
            "visited": (120, 255, 170),
            "inactive": (90, 95, 115),
        }[status]
        pygame.draw.circle(surface, outline_color, center, radius + 6, 4)

        image_path = resolve_asset_path("ui", f"node_{node['node_type']}.png")
        node_image = self._scaled_image(image_path, (radius * 2, radius * 2))
        surface.blit(node_image, (center[0] - radius, center[1] - radius))

        label = self._small_font.render(node["node_type"], True, (240, 245, 255))
        label_rect = label.get_rect(center=(center[0], center[1] + 62))
        surface.blit(label, label_rect)

    def _node_status(
        self,
        node_id: str,
        available: set[str],
        visited: set[str],
        selected: str | None,
    ) -> str:
        if node_id == selected:
            return "selected"
        if node_id in available:
            return "available"
        if node_id in visited:
            return "visited"
        return "inactive"

    def _node_positions(self, nodes: dict[str, dict[str, Any]]) -> dict[str, tuple[int, int]]:
        positions: dict[str, tuple[int, int]] = {}
        for node_id, node in nodes.items():
            x = 470 + (node["column"] * 220)
            y = 100 + (node["floor"] * 95)
            positions[node_id] = (x, y)
        return positions

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
    ) -> None:
        if width is None:
            rendered = font.render(text, True, (240, 245, 255))
            surface.blit(rendered, position)
            return

        words = text.split()
        line = ""
        x, y = position
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if font.size(candidate)[0] <= width:
                line = candidate
                continue
            rendered = font.render(line, True, (240, 245, 255))
            surface.blit(rendered, (x, y))
            y += font.get_linesize()
            line = word

        if line:
            rendered = font.render(line, True, (240, 245, 255))
            surface.blit(rendered, (x, y))

    def _ensure_fonts(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 26)
        if self._small_font is None:
            self._small_font = pygame.font.SysFont("consolas", 18)

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load map UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((0, 180, 255, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_map_ui() -> dict[str, Any]:
    ui = MapUI()
    return ui.build_layout(
        {
            "status_message": "Select the next node.",
            "nodes": {
                "floor_0_node_0": {
                    "node_id": "floor_0_node_0",
                    "node_type": "combat",
                    "floor": 0,
                    "column": 0,
                    "next_nodes": ["floor_1_node_0"],
                },
                "floor_1_node_0": {
                    "node_id": "floor_1_node_0",
                    "node_type": "shop",
                    "floor": 1,
                    "column": 0,
                    "next_nodes": [],
                },
            },
            "available_node_ids": ["floor_0_node_0"],
            "visited_node_ids": [],
            "selected_node_id": None,
        }
    )
