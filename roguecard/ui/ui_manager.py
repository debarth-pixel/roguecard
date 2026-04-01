from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_asset_path
from ui.combat_ui import CombatUI
from ui.map_ui import MapUI


class UIManager:
    def __init__(self) -> None:
        self.combat_ui = CombatUI()
        self.map_ui = MapUI()
        self._font = None
        self._small_font = None
        self._image_cache: dict[str, Any] = {}

    def preload_assets(self) -> None:
        self.map_ui.preload_assets()
        self.combat_ui.preload_assets()
        if pygame is None:
            return
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("ui", "banner_victory.png"),
            resolve_asset_path("ui", "banner_game_over.png"),
        ):
            self._load_image(path)

    def handle_event(self, event: Any, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        current_state = state_snapshot["current_state"]

        if current_state == "combat" and state_snapshot["combat"] is not None:
            action = self.combat_ui.handle_event(event, self._combat_view_state(state_snapshot))
            if action is not None:
                return action

        if current_state == "map" and state_snapshot["map"] is not None:
            action = self.map_ui.handle_event(event, self._map_view_state(state_snapshot))
            if action is not None:
                return action

        if pygame is not None and event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            return {"type": "new_run"}

        return None

    def render(self, surface: Any, state_snapshot: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts()

        current_state = state_snapshot["current_state"]
        if current_state == "combat" and state_snapshot["combat"] is not None:
            self.combat_ui.render(surface, self._combat_view_state(state_snapshot))
        elif current_state == "map" and state_snapshot["map"] is not None:
            self.map_ui.render(surface, self._map_view_state(state_snapshot))
        elif current_state in {"victory", "game_over"}:
            self._render_status_screen(surface, self._status_screen_layout(state_snapshot))
        else:
            surface.fill((18, 21, 28))

        status = self._small_font.render(state_snapshot["status_message"], True, (245, 245, 245))
        surface.blit(status, (24, 24))

    def simulate_ui(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        if state_snapshot["current_state"] == "combat" and state_snapshot["combat"] is not None:
            return self.combat_ui.build_layout(self._combat_view_state(state_snapshot))
        if state_snapshot["current_state"] == "map" and state_snapshot["map"] is not None:
            return self.map_ui.build_layout(self._map_view_state(state_snapshot))
        if state_snapshot["current_state"] in {"victory", "game_over"}:
            return self._status_screen_layout(state_snapshot)
        return {"status_message": state_snapshot["status_message"]}

    def _combat_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        combat_state = state_snapshot["combat"]
        player_hand = []
        if state_snapshot["player"] is not None and state_snapshot["current_state"] == "combat":
            hand = state_snapshot.get("player_hand")
            if hand is None:
                hand = []
            player_hand = hand

        return {
            "status_message": state_snapshot["status_message"],
            "player": combat_state["player"],
            "enemies": combat_state["enemies"],
            "event_log": combat_state.get("event_log", []),
            "player_hand": player_hand,
        }

    def _map_view_state(self, state_snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            **state_snapshot["map"],
            "status_message": state_snapshot["status_message"],
        }

    def _status_screen_layout(self, state_snapshot: dict[str, Any]) -> dict[str, str]:
        is_victory = state_snapshot["current_state"] == "victory"
        return {
            "title": "RUN COMPLETE" if is_victory else "RUN FAILED",
            "subtitle": state_snapshot["status_message"],
            "prompt": "Press N to start a new run.",
            "banner": "banner_victory.png" if is_victory else "banner_game_over.png",
        }

    def _render_status_screen(self, surface: Any, layout: dict[str, str]) -> None:
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (720, 260))
        banner = self._scaled_image(resolve_asset_path("ui", layout["banner"]), (720, 180))

        surface.blit(background, (0, 0))
        surface.blit(panel, (280, 220))
        surface.blit(banner, (280, 70))

        self._draw_text(surface, layout["title"], (470, 286), self._font)
        self._draw_text(surface, layout["subtitle"], (360, 346), self._small_font, width=560)
        self._draw_text(surface, layout["prompt"], (390, 420), self._small_font)

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
            self._font = pygame.font.SysFont("consolas", 36)
        if self._small_font is None:
            self._small_font = pygame.font.SysFont("consolas", 20)

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((90, 10, 150, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_ui_manager() -> dict[str, Any]:
    manager = UIManager()
    return manager.simulate_ui(
        {
            "current_state": "victory",
            "status_message": "Run completed.",
            "map": None,
            "combat": None,
            "player": None,
            "player_hand": [],
        }
    )
