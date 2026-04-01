from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None


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
        available = map_state["available_node_ids"]
        return {
            "available_labels": [f"{index + 1}. {node_id}" for index, node_id in enumerate(available)],
            "node_count": len(map_state["nodes"]),
        }

    def render(self, surface: Any, map_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 22)

        nodes = map_state["nodes"]
        positions: dict[str, tuple[int, int]] = {}
        for node_id, node in nodes.items():
            x = 160 + (node["column"] * 240)
            y = 90 + (node["floor"] * 95)
            positions[node_id] = (x, y)

        for node_id, node in nodes.items():
            start = positions[node_id]
            for next_node_id in node["next_nodes"]:
                pygame.draw.line(surface, (110, 110, 110), start, positions[next_node_id], 2)

        for node_id, node in nodes.items():
            color = self.NODE_COLORS.get(node["node_type"], (180, 180, 180))
            if node_id in map_state["available_node_ids"]:
                color = tuple(min(channel + 30, 255) for channel in color)
            pygame.draw.circle(surface, color, positions[node_id], 24)

            label = self._font.render(node["node_type"], True, (245, 245, 245))
            surface.blit(label, (positions[node_id][0] - 36, positions[node_id][1] - 42))

        for index, node_id in enumerate(map_state["available_node_ids"]):
            label = self._font.render(f"{index + 1}: {node_id}", True, (245, 245, 245))
            surface.blit(label, (24, 500 + (index * 28)))


def simulate_map_ui() -> dict[str, Any]:
    ui = MapUI()
    return ui.build_layout(
        {
            "nodes": {
                "floor_0_node_0": {
                    "node_id": "floor_0_node_0",
                    "node_type": "combat",
                    "floor": 0,
                    "column": 0,
                    "next_nodes": ["floor_1_node_0"],
                }
            },
            "available_node_ids": ["floor_0_node_0"],
        }
    )
