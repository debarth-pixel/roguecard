from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_asset_path


class CombatUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._image_cache: dict[str, Any] = {}

    def preload_assets(self) -> None:
        if pygame is None:
            return

        for relative_path in (
            resolve_asset_path("ui", "bg_combat.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("cards", "card_placeholder.png"),
            resolve_asset_path("enemies", "enemy_placeholder.png"),
        ):
            self._load_image(relative_path)

    def handle_event(self, event: Any, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None or event.type != pygame.KEYDOWN:
            return None

        if pygame.K_1 <= event.key <= pygame.K_9:
            hand_index = event.key - pygame.K_1
            hand = combat_state["player_hand"]
            if hand_index < len(hand):
                return {"type": "play_card", "hand_index": hand_index}

        if event.key == pygame.K_e:
            return {"type": "end_turn"}

        return None

    def build_layout(self, combat_state: dict[str, Any]) -> dict[str, Any]:
        recent_summary = self._build_recent_summary(combat_state.get("event_log", []))
        return {
            "status_message": combat_state.get("status_message", ""),
            "player_summary": {
                "hp": f"HP {combat_state['player']['current_hp']}/{combat_state['player']['max_hp']}",
                "energy": f"Energy {combat_state['player']['energy']}",
                "block": f"Block {combat_state['player']['block']}",
            },
            "enemy_summaries": [
                {
                    "name": enemy["name"],
                    "hp": f"HP {enemy['current_hp']}/{enemy['max_hp']}",
                    "block": f"Block {enemy['block']}",
                    "intent": f"Intent {enemy['current_intent'] or 'waiting'}",
                }
                for enemy in combat_state["enemies"]
            ],
            "hand_labels": [
                f"{index + 1}. {card['name']}  Cost {card['cost']}"
                for index, card in enumerate(combat_state["player_hand"])
            ],
            "controls": ["1-9: play card", "E: end turn", "N: new run"],
            "recent_summary": recent_summary,
        }

    def render(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts()
        layout = self.build_layout(combat_state)

        background = self._scaled_image(resolve_asset_path("ui", "bg_combat.png"), surface.get_size())
        surface.blit(background, (0, 0))

        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (360, 170))
        wide_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (420, 170))
        card_panel = self._scaled_image(resolve_asset_path("cards", "card_placeholder.png"), (180, 240))
        enemy_panel = self._scaled_image(resolve_asset_path("enemies", "enemy_placeholder.png"), (160, 160))

        surface.blit(panel, (32, 70))
        surface.blit(wide_panel, (848, 70))

        self._draw_text(surface, layout["status_message"], (40, 34), self._small_font)
        self._draw_block(surface, "Player", layout["player_summary"], (56, 96))
        self._draw_text(surface, "Latest Outcome", (872, 96), self._font)
        self._draw_text(surface, layout["recent_summary"], (872, 136), self._small_font, width=372)

        for index, enemy in enumerate(layout["enemy_summaries"]):
            x = 260 + (index * 300)
            y = 270
            surface.blit(enemy_panel, (x, y))
            self._draw_text(surface, enemy["name"], (x + 12, y + 16), self._font)
            self._draw_text(surface, enemy["hp"], (x + 12, y + 56), self._small_font)
            self._draw_text(surface, enemy["block"], (x + 12, y + 86), self._small_font)
            self._draw_text(surface, enemy["intent"], (x + 12, y + 116), self._small_font, width=136)

        for index, label in enumerate(layout["hand_labels"]):
            x = 34 + (index * 190)
            y = 450
            surface.blit(card_panel, (x, y))
            self._draw_text(surface, label, (x + 12, y + 16), self._small_font, width=156)

        controls_y = 650
        for offset, control in enumerate(layout["controls"]):
            self._draw_text(surface, control, (42, controls_y + (offset * 26)), self._small_font)

    def _build_recent_summary(self, event_log: list[dict[str, Any]]) -> str:
        if not event_log:
            return "No actions resolved yet."

        latest_event = event_log[-1]
        resolution_parts = [
            f"{resolution['type']} {resolution['applied']} -> {resolution['target']}"
            for resolution in latest_event.get("resolutions", [])
        ]
        summary = ", ".join(resolution_parts) if resolution_parts else "No effect."
        return f"{latest_event['card_id']}: {summary}"

    def _draw_block(
        self,
        surface: Any,
        title: str,
        lines: dict[str, str],
        position: tuple[int, int],
    ) -> None:
        self._draw_text(surface, title, position, self._font)
        for index, value in enumerate(lines.values()):
            self._draw_text(
                surface,
                value,
                (position[0], position[1] + 38 + (index * 30)),
                self._small_font,
            )

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
            self._font = pygame.font.SysFont("consolas", 28)
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
            raise RuntimeError("Pygame is required to load combat UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((255, 0, 140, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_combat_ui() -> dict[str, Any]:
    ui = CombatUI()
    return ui.build_layout(
        {
            "status_message": "Entered combat encounter.",
            "player": {"current_hp": 70, "max_hp": 70, "energy": 3, "block": 5},
            "enemies": [
                {"name": "Street Punk", "current_hp": 40, "max_hp": 40, "block": 0, "current_intent": "attack"}
            ],
            "player_hand": [{"name": "Strike", "cost": 1}, {"name": "Defend", "cost": 1}],
            "event_log": [
                {
                    "card_id": "strike_01",
                    "resolutions": [{"type": "damage", "applied": 6, "target": "enemy_basic_01"}],
                }
            ],
        }
    )
