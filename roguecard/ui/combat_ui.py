from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import CARD_HOVER_LIFT, MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.card_style import CARD_PORTRAIT_HEIGHT_RATIO, fit_portrait_card
from ui.card_renderer import draw_card
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


class CombatUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_card_index: int | None = None
        self._pressed_card_index: int | None = None
        self._hovered_enemy_id: str | None = None
        self._pressed_end_turn = False
        self._hovered_end_turn = False

    def preload_assets(self) -> None:
        if pygame is None:
            return

        for path in (
            resolve_asset_path("ui", "bg_combat.png"),
            resolve_asset_path("ui", "panel.png"),
            resolve_asset_path("enemies", "enemy_placeholder.png"),
        ):
            self._load_image(path)

    def handle_event(self, event: Any, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(combat_state)
        if combat_state.get("turn_owner") != "player":
            if event.type == pygame.KEYDOWN and event.key in {
                pygame.K_1,
                pygame.K_2,
                pygame.K_3,
                pygame.K_4,
                pygame.K_5,
                pygame.K_6,
                pygame.K_7,
                pygame.K_8,
                pygame.K_9,
                pygame.K_e,
                pygame.K_RETURN,
                pygame.K_SPACE,
            }:
                return {
                    "type": "notice",
                    "message": "Enemy actions are still resolving.",
                    "level": "error",
                }
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if (
                    self._card_index_at_position(layout, event.pos) is not None
                    or point_in_rect(event.pos, layout["end_turn_rect"])
                ):
                    return {
                        "type": "notice",
                        "message": "Enemy actions are still resolving.",
                        "level": "error",
                    }

        if event.type == pygame.MOUSEMOTION:
            self._hovered_card_index = self._card_index_at_position(layout, event.pos)
            self._hovered_enemy_id = self._enemy_id_at_position(layout, event.pos)
            self._hovered_end_turn = point_in_rect(event.pos, layout["end_turn_rect"])
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed_card_index = self._card_index_at_position(layout, event.pos)
            self._pressed_end_turn = point_in_rect(event.pos, layout["end_turn_rect"])
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            released_card_index = self._card_index_at_position(layout, event.pos)
            pressed_card_index = self._pressed_card_index
            pressed_end_turn = self._pressed_end_turn
            self._pressed_card_index = None
            self._pressed_end_turn = False

            if pressed_end_turn and point_in_rect(event.pos, layout["end_turn_rect"]):
                return {"type": "end_turn"}

            if released_card_index is None or released_card_index != pressed_card_index:
                return None

            card_layout = layout["hand_cards"][released_card_index]
            if not card_layout["playable"]:
                return {"type": "notice", "message": card_layout["disabled_reason"], "level": "error"}
            action = {"type": "play_card", "hand_index": released_card_index}
            if card_layout["target_id"] is not None:
                action["target_id"] = card_layout["target_id"]
            return action

        if event.type != pygame.KEYDOWN:
            return None

        if pygame.K_1 <= event.key <= pygame.K_9:
            hand_index = event.key - pygame.K_1
            if hand_index >= len(layout["hand_cards"]):
                return {"type": "notice", "message": "That card slot is empty.", "level": "error"}
            card_layout = layout["hand_cards"][hand_index]
            if not card_layout["playable"]:
                return {"type": "notice", "message": card_layout["disabled_reason"], "level": "error"}
            action = {"type": "play_card", "hand_index": hand_index}
            if card_layout["target_id"] is not None:
                action["target_id"] = card_layout["target_id"]
            return action

        if event.key in {pygame.K_e, pygame.K_RETURN, pygame.K_SPACE}:
            return {"type": "end_turn"}

        return None

    def build_layout(self, combat_state: dict[str, Any]) -> dict[str, Any]:
        presentation = combat_state.get("presentation", {})
        hand_size = len(combat_state["player_hand"])
        if self._hovered_card_index is not None and self._hovered_card_index >= hand_size:
            self._hovered_card_index = None
        if self._pressed_card_index is not None and self._pressed_card_index >= hand_size:
            self._pressed_card_index = None

        player = combat_state["player"]
        enemies = combat_state["enemies"]
        enemy_lookup = {enemy["id"]: enemy["name"] for enemy in enemies}
        living_enemy_ids = combat_state.get("living_enemy_ids", [])
        recent_summary = self._build_recent_summary(combat_state.get("event_log", []))
        card_rects = self._card_rects(hand_size)
        hand_cards = []
        preview_card = None
        preview_target_id = None

        for index, card in enumerate(combat_state["player_hand"]):
            playable, disabled_reason = self._card_playability(
                card,
                player,
                living_enemy_ids,
                combat_state.get("turn_owner", "player"),
            )
            target_id = self._preview_target_id(card, living_enemy_ids)
            card_layout = {
                "index": index,
                "card": card,
                "card_id": card["id"],
                "name": card["name"],
                "type": card["type"].title(),
                "cost": card["cost"],
                "playable": playable,
                "disabled_reason": disabled_reason,
                "target_label": self._target_label(card, target_id, enemy_lookup),
                "target_id": target_id,
                "preview_lines": self._preview_lines(
                    card=card,
                    player=player,
                    target_id=target_id,
                    enemy_lookup=enemy_lookup,
                    playable=playable,
                    disabled_reason=disabled_reason,
                ),
                "rect": card_rects[index],
            }
            hand_cards.append(card_layout)
            if preview_card is None and self._hovered_card_index == index:
                preview_card = card_layout
                preview_target_id = target_id

        if preview_card is None and hand_cards:
            first_playable = next((card for card in hand_cards if card["playable"]), hand_cards[0])
            preview_card = first_playable
            preview_target_id = first_playable["target_id"]

        enemy_summaries = []
        for index, enemy in enumerate(enemies):
            enemy_rect = self._enemy_rect(index)
            targeted = enemy["id"] == preview_target_id
            enemy_summaries.append(
                {
                    "id": enemy["id"],
                    "name": enemy["name"],
                    "hp": f"HP {enemy['current_hp']}/{enemy['max_hp']}",
                    "block": f"Block {enemy['block']}",
                    "intent": enemy.get("intent_summary") or f"Intent {enemy['current_intent'] or 'waiting'}",
                    "intent_value": enemy.get("intent_value"),
                    "rect": enemy_rect,
                    "targeted": targeted,
                }
            )

        return {
            "status_message": combat_state.get("status_message", ""),
            "turn_label": f"Turn {combat_state.get('turn_number', 0)}",
            "turn_owner_label": combat_state.get("turn_owner", "player").title(),
            "player_lines": [
                f"HP {player['current_hp']}/{player['max_hp']} | Block {player['block']}",
                f"Energy {player['energy']}/{player['max_energy']}",
                f"Draw {player.get('draw_pile', 0)} | Discard {player.get('discard_pile', 0)} | Exhaust {player.get('exhaust_pile', 0)}",
            ],
            "enemy_summaries": enemy_summaries,
            "hand_cards": hand_cards,
            "recent_summary": recent_summary,
            "preview_card": preview_card,
            "preview_target_id": preview_target_id,
            "preview_lines": [] if preview_card is None else list(preview_card["preview_lines"]),
            "preview_title": "Preview",
            "end_turn_rect": (1060, 614, 168, 54),
            "end_turn_hovered": self._hovered_end_turn,
            "any_playable": any(card["playable"] for card in hand_cards),
            "end_turn_hint": "No playable cards left." if not any(card["playable"] for card in hand_cards) else "End turn when ready.",
            "high_contrast": presentation.get("high_contrast", False),
        }

    def render(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        presentation = combat_state.get("presentation", {})
        high_contrast = presentation.get("high_contrast", False)
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(combat_state)
        preview_card = layout["preview_card"]

        background = self._scaled_image(resolve_asset_path("ui", "bg_combat.png"), surface.get_size())
        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=160, color=(10, 6, 12))

        player_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (300, 170))
        preview_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (326, 404))
        enemy_panel = self._scaled_image(resolve_asset_path("enemies", "enemy_placeholder.png"), (178, 178))

        surface.blit(player_panel, (32, 92))
        surface.blit(preview_panel, (934, 92))

        self._draw_text(surface, layout["turn_label"], (44, 110), self._font)
        self._draw_text(surface, layout["turn_owner_label"], (176, 112), self._small_font, width=120)
        for index, line in enumerate(layout["player_lines"]):
            self._draw_text(surface, line, (44, 150 + (index * 28)), self._small_font, width=264)

        self._draw_text(surface, layout["preview_title"], (952, 110), self._font)
        if preview_card is None:
            self._draw_text(surface, "Hover a card to inspect it.", (952, 154), self._small_font, width=280)
        else:
            preview_card_rect = fit_portrait_card((952, 144, 286, 294))
            draw_card(
                surface,
                preview_card_rect,
                preview_card["card"],
                {"title": self._small_font, "body": self._tiny_font, "tiny": self._tiny_font},
                variant="full",
                footer_label=preview_card["target_label"],
                note_label=None if preview_card["playable"] else preview_card["disabled_reason"],
                selected=True,
                high_contrast=high_contrast,
            )
            preview_text_y = 448
            self._draw_text(surface, preview_card["target_label"], (952, preview_text_y), self._tiny_font, width=286)
            preview_text_y += 20
            self._draw_text(surface, f"Recent: {layout['recent_summary']}", (952, preview_text_y), self._tiny_font, width=286)
            preview_text_y += 20
            if not preview_card["playable"]:
                self._draw_text(surface, preview_card["disabled_reason"], (952, preview_text_y), self._tiny_font, width=286)
        if preview_card is None:
            self._draw_text(surface, f"Recent: {layout['recent_summary']}", (952, 178), self._tiny_font, width=286)

        if preview_card is not None and preview_card["target_id"] is not None:
            target_rect = next(
                (
                    enemy["rect"]
                    for enemy in layout["enemy_summaries"]
                    if enemy["id"] == preview_card["target_id"]
                ),
                None,
            )
            if target_rect is not None:
                pygame.draw.line(surface, (255, 214, 110), (1234, 292), self._rect_center(target_rect), 3)

        for enemy in layout["enemy_summaries"]:
            x, y, width, height = enemy["rect"]
            surface.blit(enemy_panel, (x, y))
            outline_color = (255, 214, 110) if enemy["targeted"] else (190, 205, 230) if high_contrast else (126, 140, 168)
            if enemy["id"] == self._hovered_enemy_id:
                outline_color = (255, 255, 255)
            pygame.draw.rect(surface, outline_color, pygame.Rect(x, y, width, height), 3, border_radius=14)
            self._draw_text(surface, enemy["name"], (x + 12, y + 12), self._font)
            self._draw_text(surface, enemy["hp"], (x + 12, y + 54), self._small_font)
            self._draw_text(surface, enemy["block"], (x + 12, y + 80), self._small_font)
            self._draw_text(surface, enemy["intent"], (x + 12, y + 108), self._small_font, width=154)
            if enemy["targeted"] and preview_card is not None:
                preview_value = self._preview_damage_value(preview_card)
                if preview_value is not None:
                    self._draw_text(surface, f"Preview -{preview_value}", (x + 12, y + 144), self._tiny_font)

        for card in layout["hand_cards"]:
            x, y, width, height = card["rect"]
            card_y = y - CARD_HOVER_LIFT if card["index"] == self._hovered_card_index else y
            draw_card(
                surface,
                (x, card_y, width, height),
                card["card"],
                {"title": self._small_font, "body": self._tiny_font, "tiny": self._tiny_font},
                variant="full",
                shortcut_label=str(card["index"] + 1),
                footer_label=card["target_label"],
                note_label=None if card["playable"] else card["disabled_reason"],
                hovered=card["index"] == self._hovered_card_index,
                pressed=card["index"] == self._pressed_card_index,
                disabled=not card["playable"],
                high_contrast=high_contrast,
            )

        button_rect = pygame.Rect(*layout["end_turn_rect"])
        button_color = (60, 120, 200) if layout["end_turn_hovered"] else (32, 64, 102) if layout["any_playable"] else (44, 96, 154)
        if self._pressed_end_turn:
            button_color = (255, 214, 110)
        pygame.draw.rect(surface, button_color, button_rect, border_radius=14)
        pygame.draw.rect(surface, (230, 240, 255), button_rect, 2, border_radius=14)
        button_label = self._small_font.render("End Turn", True, (240, 245, 255))
        label_rect = button_label.get_rect(center=button_rect.center)
        surface.blit(button_label, label_rect)
        self._draw_text(surface, layout["end_turn_hint"], (930, 676), self._tiny_font, width=300)

    def _build_recent_summary(self, event_log: list[dict[str, Any]]) -> str:
        if not event_log:
            return "No actions resolved yet."

        latest_event = event_log[-1]
        if "summary" in latest_event:
            return latest_event["summary"]

        resolution_parts = [
            f"{resolution['type']} {resolution['applied']} -> {resolution['target']}"
            for resolution in latest_event.get("resolutions", [])
        ]
        summary = ", ".join(resolution_parts) if resolution_parts else "No effect."
        return f"{latest_event['card_id']}: {summary}"

    def _card_playability(
        self,
        card: dict[str, Any],
        player: dict[str, Any],
        living_enemy_ids: list[str],
        turn_owner: str,
    ) -> tuple[bool, str]:
        if turn_owner != "player":
            return False, "Wait for enemy actions"
        if card["cost"] > player["energy"]:
            missing = card["cost"] - player["energy"]
            return False, f"Need {missing} more energy"
        if any(effect["type"] == "damage" for effect in card.get("effects", [])) and not living_enemy_ids:
            return False, "No living target"
        return True, "Ready"

    def _target_label(
        self,
        card: dict[str, Any],
        target_id: str | None,
        enemy_lookup: dict[str, str],
    ) -> str:
        if any(effect["type"] == "damage" for effect in card.get("effects", [])):
            if target_id is None:
                return "Target: none"
            return f"Target: {enemy_lookup.get(target_id, target_id)}"
        return "Target: self"

    def _preview_lines(
        self,
        card: dict[str, Any],
        player: dict[str, Any],
        target_id: str | None,
        enemy_lookup: dict[str, str],
        playable: bool,
        disabled_reason: str,
    ) -> list[str]:
        lines: list[str] = []
        for effect in card.get("effects", []):
            if effect["type"] == "damage":
                target_name = enemy_lookup.get(target_id, "no target") if target_id is not None else "no target"
                lines.append(f"Deal {effect['value']} damage to {target_name}.")
            elif effect["type"] == "block":
                lines.append(f"Gain {effect['value']} Block.")
            elif effect["type"] == "heal":
                lines.append(f"Heal {effect['value']}.")
            elif effect["type"] == "draw":
                lines.append(f"Draw {effect['value']}.")
            elif effect["type"] == "energy":
                lines.append(f"Gain {effect['value']} Energy.")
            else:
                lines.append(f"{effect['type'].title()} {effect['value']}.")

        lines.append(f"After play: {max(0, player['energy'] - card['cost'])} Energy.")
        if not playable:
            lines.append(disabled_reason)
        return lines[:4]

    def _preview_target_id(self, card: dict[str, Any], living_enemy_ids: list[str]) -> str | None:
        if any(effect["type"] == "damage" for effect in card.get("effects", [])):
            if self._hovered_enemy_id in living_enemy_ids:
                return self._hovered_enemy_id
            return None if not living_enemy_ids else living_enemy_ids[0]
        return None

    def _preview_damage_value(self, card_layout: dict[str, Any]) -> int | None:
        if card_layout is None:
            return None
        for effect in card_layout["card"].get("effects", []):
            if effect.get("type") == "damage" and isinstance(effect.get("value"), int):
                return effect["value"]
        return None

    def _card_rects(self, hand_count: int) -> list[tuple[int, int, int, int]]:
        if hand_count <= 0:
            return []

        gap = 10 if hand_count <= 6 else 8
        available_width = 990
        card_width = min(174, max(116, (available_width - (gap * (hand_count - 1))) // hand_count))
        card_height = int(card_width * CARD_PORTRAIT_HEIGHT_RATIO)
        row_width = (card_width * hand_count) + (gap * (hand_count - 1))
        start_x = 26 + max(0, (available_width - row_width) // 2)
        y = 682 - card_height
        return [
            (start_x + (index * (card_width + gap)), y, card_width, card_height)
            for index in range(hand_count)
        ]

    def _enemy_rect(self, index: int) -> tuple[int, int, int, int]:
        return (300 + (index * 236), 176, 178, 178)

    def _card_index_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> int | None:
        for card in layout["hand_cards"]:
            rect = card["rect"]
            hover_rect = (
                rect[0],
                rect[1] - (CARD_HOVER_LIFT if card["index"] == self._hovered_card_index else 0),
                rect[2],
                rect[3],
            )
            if point_in_rect(position, hover_rect):
                return card["index"]
        return None

    def _enemy_id_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for enemy in layout["enemy_summaries"]:
            if point_in_rect(position, enemy["rect"]):
                return enemy["id"]
        return None

    def _rect_center(self, rect: tuple[int, int, int, int]) -> tuple[int, int]:
        return rect[0] + (rect[2] // 2), rect[1] + (rect[3] // 2)

    def _draw_badge(self, surface: Any, text: str, position: tuple[int, int], color: tuple[int, int, int]) -> None:
        badge_rect = pygame.Rect(position[0], position[1], 24, 24)
        pygame.draw.rect(surface, (12, 18, 28), badge_rect, border_radius=12)
        pygame.draw.rect(surface, color, badge_rect, 2, border_radius=12)
        label = self._tiny_font.render(text, True, color)
        label_rect = label.get_rect(center=badge_rect.center)
        surface.blit(label, label_rect)

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
            "player": {
                "current_hp": 70,
                "max_hp": 70,
                "energy": 3,
                "max_energy": 3,
                "block": 5,
                "draw_pile": 3,
                "discard_pile": 1,
                "exhaust_pile": 0,
            },
            "turn_number": 1,
            "turn_owner": "player",
            "living_enemy_ids": ["enemy_basic_01"],
            "enemies": [
                {
                    "id": "enemy_basic_01",
                    "name": "Street Punk",
                    "current_hp": 40,
                    "max_hp": 40,
                    "block": 0,
                    "current_intent": "attack",
                    "intent_value": 6,
                    "intent_summary": "Attack for 6",
                }
            ],
            "player_hand": [
                {
                    "id": "strike_01",
                    "name": "Strike",
                    "cost": 1,
                    "type": "attack",
                    "effects": [{"type": "damage", "value": 6}],
                },
                {
                    "id": "defend_01",
                    "name": "Defend",
                    "cost": 1,
                    "type": "skill",
                    "effects": [{"type": "block", "value": 5}],
                },
            ],
            "event_log": [
                {
                    "card_id": "strike_01",
                    "summary": "Strike: damage 6 -> enemy_basic_01",
                    "resolutions": [{"type": "damage", "applied": 6, "target": "enemy_basic_01"}],
                }
            ],
            "presentation": {"ui_scale": 1.0, "high_contrast": False},
        }
    )
