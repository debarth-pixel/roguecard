from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAP_NODE_HIT_RADIUS, MAP_NODE_RADIUS, MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text

MAP_PANEL_BOUNDS = (104, 84, 1036, 620)
MAP_HEADER_HEIGHT = 94
MAP_VIEWPORT_PADDING = 26
MAP_SCROLL_STEP = 120


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
        self._scroll_offset = 0

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
        layout = self.build_layout(map_state)

        if event.type == pygame.MOUSEWHEEL:
            self._adjust_scroll(-event.y * MAP_SCROLL_STEP, layout["max_scroll"])
            return None

        if event.type == pygame.MOUSEMOTION:
            self._hovered_node_id = self._node_at_position(layout, event.pos)
            if self._hovered_node_id in available:
                self._keyboard_selection_index = available.index(self._hovered_node_id)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._pressed_node_id = self._node_at_position(layout, event.pos)
                if self._pressed_node_id in available:
                    self._keyboard_selection_index = available.index(self._pressed_node_id)
                return None
            if event.button == 4:
                self._adjust_scroll(-MAP_SCROLL_STEP, layout["max_scroll"])
                return None
            if event.button == 5:
                self._adjust_scroll(MAP_SCROLL_STEP, layout["max_scroll"])
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            node_id = self._node_at_position(layout, event.pos)
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

        if event.key in {pygame.K_PAGEUP, pygame.K_HOME}:
            self._scroll_offset = 0 if event.key == pygame.K_HOME else max(0, self._scroll_offset - (MAP_SCROLL_STEP * 2))
            return None

        if event.key in {pygame.K_PAGEDOWN, pygame.K_END}:
            self._scroll_offset = (
                layout["max_scroll"]
                if event.key == pygame.K_END
                else min(layout["max_scroll"], self._scroll_offset + (MAP_SCROLL_STEP * 2))
            )
            return None

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
        viewport_rect = self._viewport_rect()
        canvas_height = max(viewport_rect[3], int(map_state.get("canvas_height", viewport_rect[3])))
        max_scroll = max(0, canvas_height - viewport_rect[3])
        if focused_node_id is not None and focused_node_id in nodes:
            self._ensure_focus_visible(nodes[focused_node_id], viewport_rect[3], max_scroll)
        else:
            self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))

        return {
            "map_state": map_state,
            "status_message": map_state.get("status_message", ""),
            "node_statuses": {
                node_id: self._node_status(node_id, available_set, visited, selected)
                for node_id in nodes
            },
            "focused_node_id": focused_node_id,
            "hovered_node_id": self._hovered_node_id,
            "available_numbers": {node_id: index + 1 for index, node_id in enumerate(available)},
            "selected_node_id": selected,
            "focused_node_label": self._focused_node_label(focused_node_id, nodes),
            "map_bounds": self._map_bounds(),
            "viewport_rect": viewport_rect,
            "high_contrast": map_state.get("presentation", {}).get("high_contrast", False),
            "map_name": map_state.get("map_name", "Map"),
            "map_index": map_state.get("map_index", 0),
            "branch_faction": map_state.get("branch_faction"),
            "route_floor_count": map_state.get("route_floor_count", 0),
            "selected_boss_id": map_state.get("selected_boss_id"),
            "scroll_offset": self._scroll_offset,
            "max_scroll": max_scroll,
            "canvas_height": canvas_height,
            "canvas_width": map_state.get("canvas_width", viewport_rect[2]),
        }

    def render(self, surface: Any, map_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        presentation = map_state.get("presentation", {})
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(map_state)
        nodes = map_state["nodes"]
        positions = self._screen_positions(nodes, layout)
        focus_node_id = layout["focused_node_id"]
        available_set = set(map_state["available_node_ids"])
        selected_node_id = layout["selected_node_id"]
        high_contrast = layout["high_contrast"]

        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        map_bounds = pygame.Rect(*layout["map_bounds"])
        viewport_rect = pygame.Rect(*layout["viewport_rect"])
        header_rect = pygame.Rect(map_bounds.x + 18, map_bounds.y + 16, map_bounds.width - 36, MAP_HEADER_HEIGHT - 24)

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=148)
        map_panel = pygame.Surface(map_bounds.size, pygame.SRCALPHA)
        map_panel.fill((12, 18, 28, 132))
        surface.blit(map_panel, map_bounds.topleft)
        pygame.draw.rect(surface, (104, 118, 146), map_bounds, 2, border_radius=28)
        pygame.draw.rect(surface, (10, 16, 26, 220), header_rect, border_radius=18)
        pygame.draw.rect(surface, (92, 198, 240), header_rect, 2, border_radius=18)

        self._draw_text(surface, layout["map_name"], (header_rect.x + 20, header_rect.y + 14), self._font)
        subtitle = f"Map {layout['map_index']} | {self._progress_label(layout, map_state)}"
        if layout["branch_faction"]:
            subtitle = f"{subtitle} | {str(layout['branch_faction']).title()} route"
        self._draw_text(surface, subtitle, (header_rect.x + 20, header_rect.y + 48), self._small_font, width=620)
        self._draw_text(
            surface,
            f"Scroll {int(layout['scroll_offset'])}/{int(layout['max_scroll'])}",
            (header_rect.right - 168, header_rect.y + 18),
            self._tiny_font,
            width=146,
        )

        viewport_surface = pygame.Surface(viewport_rect.size, pygame.SRCALPHA)
        viewport_surface.fill((8, 12, 20, 74))
        surface.blit(viewport_surface, viewport_rect.topleft)
        pygame.draw.rect(surface, (56, 70, 94), viewport_rect, 1, border_radius=22)

        clip_previous = surface.get_clip()
        surface.set_clip(viewport_rect)

        for node_id, node in nodes.items():
            if node_id not in positions:
                continue
            start = positions[node_id]
            for next_node_id in node["next_nodes"]:
                if next_node_id not in positions:
                    continue
                line_color = (108, 114, 128)
                width = 3
                if next_node_id in available_set:
                    line_color = (255, 214, 110)
                    width = 4
                elif node_id == selected_node_id or next_node_id == selected_node_id:
                    line_color = (240, 245, 255)
                    width = 4
                elif node_id in map_state.get("visited_node_ids", []) or next_node_id in map_state.get("visited_node_ids", []):
                    line_color = (120, 244, 170)
                    width = 3
                elif node_id == focus_node_id or next_node_id == focus_node_id:
                    line_color = (190, 205, 230) if high_contrast else (146, 164, 194)
                    width = 4
                pygame.draw.line(surface, line_color, start, positions[next_node_id], width)

        for node_id, node in nodes.items():
            center = positions.get(node_id)
            if center is None:
                continue
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

        if focus_node_id is not None and layout["focused_node_label"] and focus_node_id in positions:
            label = layout["focused_node_label"]
            label_width = max(108, self._small_font.size(label)[0] + 22)
            center = positions[focus_node_id]
            pill_y = max(viewport_rect.y + 10, center[1] - 94)
            pill_rect = pygame.Rect(center[0] - (label_width // 2), pill_y, label_width, 26)
            pygame.draw.rect(surface, (14, 20, 32), pill_rect, border_radius=13)
            pygame.draw.rect(surface, (255, 214, 110), pill_rect, 2, border_radius=13)
            self._draw_text(surface, label, (pill_rect.x + 12, pill_rect.y + 6), self._tiny_font, width=pill_rect.width - 24)

        surface.set_clip(clip_previous)

        self._draw_scrollbar(surface, viewport_rect, layout["scroll_offset"], layout["max_scroll"])
        self._draw_text(surface, layout["status_message"], (map_bounds.x + 28, map_bounds.bottom - 36), self._tiny_font, width=map_bounds.width - 56)

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

        if shortcut_label is not None:
            badge_rect = pygame.Rect(center[0] + 26, center[1] - 56, 24, 24)
            pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=12)
            pygame.draw.rect(surface, (255, 226, 112), badge_rect, 2, border_radius=12)
            shortcut = self._tiny_font.render(str(shortcut_label), True, (255, 226, 112))
            shortcut_rect = shortcut.get_rect(center=badge_rect.center)
            surface.blit(shortcut, shortcut_rect)

    def _focused_node_label(
        self,
        focused_node_id: str | None,
        nodes: dict[str, dict[str, Any]],
    ) -> str | None:
        if focused_node_id is None or focused_node_id not in nodes:
            return None
        node = nodes[focused_node_id]
        if node["node_type"] == "boss":
            return "Boss"
        return f"{node['node_type'].title()} F{node['route_floor']}"

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

    def _screen_positions(
        self,
        nodes: dict[str, dict[str, Any]],
        layout: dict[str, Any],
    ) -> dict[str, tuple[int, int]]:
        viewport_rect = layout["viewport_rect"]
        positions: dict[str, tuple[int, int]] = {}
        for node_id, node in nodes.items():
            positions[node_id] = (
                viewport_rect[0] + int(node["render_x"]),
                viewport_rect[1] + int(node["render_y"]) - int(layout["scroll_offset"]),
            )
        return positions

    def _map_bounds(self) -> tuple[int, int, int, int]:
        return MAP_PANEL_BOUNDS

    def _viewport_rect(self) -> tuple[int, int, int, int]:
        bounds = self._map_bounds()
        return (
            bounds[0] + MAP_VIEWPORT_PADDING,
            bounds[1] + MAP_HEADER_HEIGHT,
            bounds[2] - (MAP_VIEWPORT_PADDING * 2),
            bounds[3] - MAP_HEADER_HEIGHT - 54,
        )

    def _ensure_focus_visible(self, node: dict[str, Any], viewport_height: int, max_scroll: int) -> None:
        target_y = int(node["render_y"])
        visible_top = self._scroll_offset + 72
        visible_bottom = self._scroll_offset + viewport_height - 72
        if target_y < visible_top:
            self._scroll_offset = max(0, min(max_scroll, target_y - 72))
        elif target_y > visible_bottom:
            self._scroll_offset = max(0, min(max_scroll, target_y - (viewport_height - 72)))
        else:
            self._scroll_offset = max(0, min(max_scroll, self._scroll_offset))

    def _adjust_scroll(self, delta: int, max_scroll: int) -> None:
        self._scroll_offset = max(0, min(max_scroll, self._scroll_offset + delta))

    def _progress_label(self, layout: dict[str, Any], map_state: dict[str, Any]) -> str:
        nodes = map_state.get("nodes", {})
        selected_node_id = map_state.get("selected_node_id")
        selected_node = nodes.get(selected_node_id) if isinstance(nodes, dict) and selected_node_id is not None else None
        if selected_node is None:
            return f"Entrance | F0/{layout['route_floor_count']}"
        if selected_node["node_type"] == "boss":
            return f"Boss | F{layout['route_floor_count']}/{layout['route_floor_count']}"
        return f"F{selected_node['route_floor']}/{layout['route_floor_count']} | {selected_node['node_type'].title()}"

    def _draw_scrollbar(self, surface: Any, viewport_rect: pygame.Rect, scroll_offset: int, max_scroll: int) -> None:
        if max_scroll <= 0:
            return
        track_rect = pygame.Rect(viewport_rect.right + 8, viewport_rect.y, 10, viewport_rect.height)
        pygame.draw.rect(surface, (18, 26, 38), track_rect, border_radius=5)
        pygame.draw.rect(surface, (72, 88, 112), track_rect, 1, border_radius=5)
        thumb_height = max(48, int((viewport_rect.height / (viewport_rect.height + max_scroll)) * viewport_rect.height))
        thumb_range = track_rect.height - thumb_height
        thumb_y = track_rect.y + int((scroll_offset / max_scroll) * thumb_range)
        thumb_rect = pygame.Rect(track_rect.x + 1, thumb_y, track_rect.width - 2, thumb_height)
        pygame.draw.rect(surface, (92, 198, 240), thumb_rect, border_radius=5)

    def _node_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:  # type: ignore[override]
        viewport_rect = pygame.Rect(*layout["viewport_rect"])
        if not viewport_rect.collidepoint(position):
            return None
        nodes = layout["map_state"]["nodes"]
        positions = self._screen_positions(nodes, layout)
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
    state = {
        "status_message": "Select the next node.",
        "map_id": "outskirts",
        "map_name": "Outskirts",
        "map_index": 1,
        "branch_faction": None,
        "route_floor_count": 15,
        "canvas_width": 1036,
        "canvas_height": 2400,
        "nodes": {
            "outskirts_floor_0_node_0": {
                "node_id": "outskirts_floor_0_node_0",
                "node_type": "combat",
                "floor": 0,
                "column": 0,
                "map_id": "outskirts",
                "route_floor": 1,
                "campaign_floor": 0,
                "node_tier": "normal",
                "render_x": 220,
                "render_y": 116,
                "encounter_hook_id": "outskirts:combat:f1:c0",
                "boss_slot_id": None,
                "enemy_ids": ["enemy_basic_01"],
                "next_nodes": ["outskirts_floor_1_node_0"],
            },
            "outskirts_floor_1_node_0": {
                "node_id": "outskirts_floor_1_node_0",
                "node_type": "shop",
                "floor": 1,
                "column": 0,
                "map_id": "outskirts",
                "route_floor": 2,
                "campaign_floor": 1,
                "node_tier": "utility",
                "render_x": 232,
                "render_y": 258,
                "encounter_hook_id": "outskirts:shop:f2:c0",
                "boss_slot_id": None,
                "enemy_ids": [],
                "next_nodes": [],
            },
        },
        "available_node_ids": ["outskirts_floor_0_node_0"],
        "visited_node_ids": [],
        "selected_node_id": None,
        "presentation": {"ui_scale": 1.0, "high_contrast": False},
    }
    layout = ui.build_layout(state)
    return {
        "focused_node_label": layout["focused_node_label"],
        "map_name": layout["map_name"],
        "route_floor_count": layout["route_floor_count"],
        "max_scroll": layout["max_scroll"],
    }
