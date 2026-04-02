from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAP_NODE_HIT_RADIUS, MAP_NODE_RADIUS, MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text


class MapUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_node_id: str | None = None
        self._pressed_node_id: str | None = None
        self._keyboard_selection_index = 0

    def preload_assets(self) -> None:
        if pygame is None:
            return

        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("ui", "node_combat.png"),
            resolve_asset_path("ui", "node_elite.png"),
            resolve_asset_path("ui", "node_shop.png"),
            resolve_asset_path("ui", "node_event.png"),
            resolve_asset_path("ui", "node_boss.png"),
        ):
            self._load_image(path)

    def handle_event(self, event: Any, map_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        available = map_state["available_node_ids"]
        self._clamp_keyboard_selection(available)

        if event.type == pygame.MOUSEMOTION:
            self._hovered_node_id = self._node_at_position(map_state, event.pos)
            if self._hovered_node_id in available:
                self._keyboard_selection_index = available.index(self._hovered_node_id)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed_node_id = self._node_at_position(map_state, event.pos)
            if self._pressed_node_id in available:
                self._keyboard_selection_index = available.index(self._pressed_node_id)
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            node_id = self._node_at_position(map_state, event.pos)
            pressed_node_id = self._pressed_node_id
            self._pressed_node_id = None
            if node_id is None or node_id != pressed_node_id:
                return None
            if node_id in available:
                return {"type": "select_node", "node_id": node_id}
            return {"type": "notice", "message": "That route is not available yet.", "level": "error"}

        if event.type != pygame.KEYDOWN:
            return None

        if pygame.K_1 <= event.key <= pygame.K_9:
            selection_index = event.key - pygame.K_1
            if selection_index < len(available):
                self._keyboard_selection_index = selection_index
                return {"type": "select_node", "node_id": available[selection_index]}
            return {"type": "notice", "message": "That route slot is empty.", "level": "error"}

        if event.key in {pygame.K_LEFT, pygame.K_UP} and available:
            self._keyboard_selection_index = (self._keyboard_selection_index - 1) % len(available)
            self._hovered_node_id = available[self._keyboard_selection_index]
            return None

        if event.key in {pygame.K_RIGHT, pygame.K_DOWN} and available:
            self._keyboard_selection_index = (self._keyboard_selection_index + 1) % len(available)
            self._hovered_node_id = available[self._keyboard_selection_index]
            return None

        if event.key in {pygame.K_RETURN, pygame.K_SPACE} and available:
            hovered = self._hovered_node_id if self._hovered_node_id in available else None
            target_node_id = hovered or available[self._keyboard_selection_index]
            return {"type": "select_node", "node_id": target_node_id}

        return None

    def build_layout(self, map_state: dict[str, Any]) -> dict[str, Any]:
        nodes = map_state["nodes"]
        available = list(map_state["available_node_ids"])
        available_set = set(available)
        visited = set(map_state.get("visited_node_ids", []))
        selected = map_state.get("selected_node_id")
        focused_node_id = self._focused_node_id(map_state)
        focus_node = nodes.get(focused_node_id) if focused_node_id is not None else None
        selected_node = nodes.get(selected) if selected is not None else None

        return {
            "status_message": map_state.get("status_message", ""),
            "available_labels": [
                f"{index + 1}. Floor {nodes[node_id]['floor'] + 1} {nodes[node_id]['node_type'].title()}"
                for index, node_id in enumerate(available)
            ],
            "selected_label": (
                "Current Position: Entrance"
                if selected_node is None
                else f"Current Position: Floor {selected_node['floor'] + 1} {selected_node['node_type'].title()}"
            ),
            "node_statuses": {
                node_id: self._node_status(node_id, available_set, visited, selected)
                for node_id in nodes
            },
            "focused_node_id": focused_node_id,
            "hovered_node_id": self._hovered_node_id,
            "available_numbers": {node_id: index + 1 for index, node_id in enumerate(available)},
            "node_count": len(nodes),
            "route_count": len(available),
            "selected_node_id": selected,
            "focus_lines": self._focus_lines(focus_node, focused_node_id, map_state),
            "focus_next_nodes": [] if focus_node is None else list(focus_node["next_nodes"]),
            "legend": [
                "Gold path: available now",
                "Green outline: already visited",
                "White ring: current position or focus",
                "Dim nodes: unreachable right now",
            ],
            "controls": [
                "Click or press 1-9 to choose a route",
                "Arrow keys move focus between routes",
                "Enter / Space confirms the focused route",
                "S opens settings",
            ],
            "next_action_hint": (
                "Next: choose one of the highlighted routes."
                if available
                else "No route is available from this position."
            ),
            "high_contrast": map_state.get("presentation", {}).get("high_contrast", False),
        }

    def render(self, surface: Any, map_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        presentation = map_state.get("presentation", {})
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(map_state)
        nodes = map_state["nodes"]
        positions = self._node_positions(nodes)
        focus_node_id = layout["focused_node_id"]
        available_set = set(map_state["available_node_ids"])
        selected_node_id = layout["selected_node_id"]
        high_contrast = layout["high_contrast"]

        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        summary_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 248))
        detail_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 304))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176)
        surface.blit(summary_panel, (24, 96))
        surface.blit(detail_panel, (24, 360))

        self._draw_text(surface, "Route Overview", (44, 118), self._font)
        self._draw_text(surface, layout["status_message"], (44, 156), self._small_font, width=320)
        self._draw_text(surface, layout["selected_label"], (44, 224), self._small_font, width=320)
        self._draw_text(surface, f"Reachable now: {layout['route_count']}", (44, 266), self._small_font)
        self._draw_text(surface, f"Total nodes: {layout['node_count']}", (44, 296), self._small_font)
        self._draw_text(surface, layout["next_action_hint"], (44, 324), self._tiny_font, width=320)

        self._draw_text(surface, "Available Now", (44, 382), self._font)
        available_y = 420
        if layout["available_labels"]:
            for label in layout["available_labels"][:4]:
                self._draw_text(surface, label, (44, available_y), self._tiny_font, width=320)
                available_y += 18
        else:
            self._draw_text(surface, "No immediate route choices.", (44, available_y), self._tiny_font, width=320)

        self._draw_text(surface, "Focused Node", (44, 492), self._font)
        for index, line in enumerate(layout["focus_lines"]):
            self._draw_text(surface, line, (44, 520 + (index * 16)), self._tiny_font, width=320)

        for node_id, node in nodes.items():
            start = positions[node_id]
            for next_node_id in node["next_nodes"]:
                line_color = (100, 108, 125)
                width = 3
                if next_node_id in available_set:
                    line_color = (255, 221, 105)
                    width = 5
                elif node_id == focus_node_id or next_node_id == focus_node_id:
                    line_color = (240, 245, 255) if high_contrast else (180, 196, 224)
                    width = 4
                elif node_id == selected_node_id:
                    line_color = (120, 244, 170)
                    width = 4
                pygame.draw.line(surface, line_color, start, positions[next_node_id], width)

        for node_id, node in nodes.items():
            center = positions[node_id]
            status = layout["node_statuses"][node_id]
            self._draw_node(
                surface=surface,
                node=node,
                center=center,
                status=status,
                is_hovered=node_id == layout["hovered_node_id"],
                is_focused=node_id == focus_node_id,
                is_pressed=node_id == self._pressed_node_id,
                shortcut_label=layout["available_numbers"].get(node_id),
                high_contrast=high_contrast,
            )

    def _draw_node(
        self,
        surface: Any,
        node: dict[str, Any],
        center: tuple[int, int],
        status: str,
        is_hovered: bool,
        is_focused: bool,
        is_pressed: bool,
        shortcut_label: int | None,
        high_contrast: bool,
    ) -> None:
        radius = MAP_NODE_RADIUS
        outline_color = {
            "selected": (255, 255, 255),
            "available": (255, 226, 112),
            "visited": (120, 244, 170),
            "inactive": (190, 205, 230) if high_contrast else (86, 90, 112),
        }[status]
        fill_color = {
            "selected": (255, 255, 255, 36),
            "available": (255, 226, 112, 30),
            "visited": (120, 244, 170, 26),
            "inactive": (70, 74, 88, 36) if high_contrast else (50, 54, 68, 20),
        }[status]

        pulse_radius = radius + (12 if is_hovered else 8)
        if is_focused:
            pulse_radius += 4
        pygame.draw.circle(surface, outline_color, center, pulse_radius, 4)

        glow = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, fill_color, (glow.get_width() // 2, glow.get_height() // 2), radius + 16)
        surface.blit(glow, (center[0] - glow.get_width() // 2, center[1] - glow.get_height() // 2))

        image_path = resolve_asset_path("ui", f"node_{node['node_type']}.png")
        node_image = self._scaled_image(image_path, (radius * 2, radius * 2))
        image_rect = node_image.get_rect(center=center)
        if status == "inactive":
            dim_overlay = pygame.Surface(node_image.get_size(), pygame.SRCALPHA)
            dim_overlay.fill((18, 20, 28, 140))
            node_image = node_image.copy()
            node_image.blit(dim_overlay, (0, 0))
        surface.blit(node_image, image_rect.topleft)

        if is_pressed:
            pygame.draw.circle(surface, (255, 255, 255), center, radius + 2, 2)
        if status == "selected":
            you_label = self._tiny_font.render("YOU", True, (255, 255, 255))
            you_rect = you_label.get_rect(center=(center[0], center[1] - 70))
            surface.blit(you_label, you_rect)

        label = self._small_font.render(node["node_type"].title(), True, (240, 245, 255))
        label_rect = label.get_rect(center=(center[0], center[1] + 66))
        surface.blit(label, label_rect)

        if shortcut_label is not None:
            badge_rect = pygame.Rect(center[0] + 26, center[1] - 56, 24, 24)
            pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=12)
            pygame.draw.rect(surface, (255, 226, 112), badge_rect, 2, border_radius=12)
            shortcut = self._tiny_font.render(str(shortcut_label), True, (255, 226, 112))
            shortcut_rect = shortcut.get_rect(center=badge_rect.center)
            surface.blit(shortcut, shortcut_rect)

    def _focus_lines(
        self,
        focus_node: dict[str, Any] | None,
        focused_node_id: str | None,
        map_state: dict[str, Any],
    ) -> list[str]:
        if focus_node is None:
            return [
                "Hover or focus a route to inspect it.",
                "Available routes are highlighted on the map.",
            ]

        available = set(map_state["available_node_ids"])
        visited = set(map_state.get("visited_node_ids", []))
        status = "Locked"
        if focused_node_id in available:
            status = "Available"
        elif focused_node_id in visited:
            status = "Visited"
        elif focused_node_id == map_state.get("selected_node_id"):
            status = "Current Position"

        next_types = [
            map_state["nodes"][node_id]["node_type"].title() for node_id in focus_node["next_nodes"]
        ]
        preview = ", ".join(next_types) if next_types else "No outgoing route"
        return [
            f"Node: {focus_node['node_type'].title()}",
            f"Floor {focus_node['floor'] + 1} | Column {focus_node['column'] + 1}",
            f"Status: {status}",
            f"Leads to: {preview}",
            "Press Enter or click to continue." if focused_node_id in available else "Hover a highlighted route to inspect it.",
        ]

    def _focused_node_id(self, map_state: dict[str, Any]) -> str | None:
        available = map_state["available_node_ids"]
        if available:
            self._clamp_keyboard_selection(available)
            if self._hovered_node_id in available:
                return self._hovered_node_id
            if self._pressed_node_id in available:
                return self._pressed_node_id
            return available[self._keyboard_selection_index]
        if map_state.get("selected_node_id") in map_state["nodes"]:
            return map_state["selected_node_id"]
        if self._hovered_node_id in map_state["nodes"]:
            return self._hovered_node_id
        return map_state.get("selected_node_id")

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
            x = 502 + (node["column"] * 212)
            y = 136 + (node["floor"] * 92)
            positions[node_id] = (x, y)
        return positions

    def _node_at_position(self, map_state: dict[str, Any], position: tuple[int, int]) -> str | None:
        nodes = map_state["nodes"]
        positions = self._node_positions(nodes)
        for node_id, center in positions.items():
            if (position[0] - center[0]) ** 2 + (position[1] - center[1]) ** 2 <= MAP_NODE_HIT_RADIUS ** 2:
                return node_id
        return None

    def _clamp_keyboard_selection(self, available: list[str]) -> None:
        if not available:
            self._keyboard_selection_index = 0
            return
        self._keyboard_selection_index = min(self._keyboard_selection_index, len(available) - 1)

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        width: int | None = None,
    ) -> None:
        draw_wrapped_text(surface, text, position, font, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return

        self._font_scale = scale
        self._font = pygame.font.SysFont("consolas", max(20, int(26 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(15, int(18 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(14 * scale)))

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
            "presentation": {"ui_scale": 1.0, "high_contrast": False},
        }
    )
