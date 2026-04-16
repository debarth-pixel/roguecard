from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    CARD_HOVER_LIFT,
    MAX_UI_SCALE,
    MIN_UI_SCALE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    resolve_asset_path,
)
from ui.card_renderer import card_summary_lines, draw_card
from ui.card_style import CARD_PORTRAIT_HEIGHT_RATIO
from ui.relic_assets import relic_assets
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect

SELECT_ANIM_MS = 150
RESOLVE_ANIM_MS = 110
TOOLTIP_MAX_WIDTH = 260
HAND_CENTER_X = 532
HAND_CENTER_Y = 624
CARD_CENTER = (606, 302)
END_TURN_RECT = (1048, 636, 184, 52)
HELPER_PANEL_RECT = (836, 552, 406, 62)
TURN_HEADER_ORIGIN = (44, 70)
TURN_HEADER_LINE_WIDTH = 3
COMBAT_MODIFIER_ORIGIN = (44, 118)
COMBAT_MODIFIER_SLOT = 30
COMBAT_MODIFIER_GAP = 10
COMBAT_MODIFIER_LIMIT = 7
PLAYER_FOOT = (214, 466)
PLAYER_SCALE = 1.14
GROUND_RING_HEIGHT = 28

ENEMY_SLOT_MAP = {
    1: [(1016, 430, 1.14)],
    2: [(936, 432, 1.06), (1096, 418, 1.0)],
    3: [(858, 434, 0.98), (1016, 410, 1.1), (1164, 432, 0.96)],
    4: [(818, 436, 0.96), (942, 418, 1.02), (1070, 410, 1.06), (1188, 432, 0.92)],
    5: [(792, 438, 0.92), (902, 422, 0.96), (1014, 404, 1.08), (1124, 420, 0.94), (1218, 438, 0.88)],
}

FACTION_COLORS = {
    "helix_ward": (98, 220, 146),
    "blackwire_directorate": (104, 216, 255),
    "cinder_jackals": (255, 150, 84),
    "legacy": (192, 172, 220),
}

STATUS_META = {
    "strength": {"label": "Strength", "short": "STR", "color": (232, 100, 92)},
    "weak": {"label": "Weak", "short": "W", "color": (255, 206, 118)},
    "vulnerable": {"label": "Vulnerable", "short": "V", "color": (224, 126, 92)},
    "infect": {"label": "Infection", "short": "INF", "color": (104, 230, 154)},
    "burn": {"label": "Burn", "short": "BRN", "color": (255, 132, 78)},
    "bleed": {"label": "Bleed", "short": "BLD", "color": (240, 84, 114)},
    "marked": {"label": "Marked", "short": "MRK", "color": (118, 190, 255)},
    "suppressed": {"label": "Suppressed", "short": "SUP", "color": (174, 182, 220)},
    "nullified": {"label": "Nullified", "short": "NUL", "color": (196, 156, 255)},
    "fortified": {"label": "Fortified", "short": "FOR", "color": (92, 168, 255)},
    "regenerate": {"label": "Regenerate", "short": "REG", "color": (112, 236, 170)},
    "momentum": {"label": "Momentum", "short": "MOM", "color": (255, 156, 84)},
    "overheat": {"label": "Overheat", "short": "HT", "color": (255, 132, 68)},
    "biomass": {"label": "Biomass", "short": "BIO", "color": (118, 214, 126)},
    "mutated": {"label": "Mutated", "short": "MUT", "color": (154, 255, 162)},
}

BUFF_LABELS = {
    "Heal": "Restores health.",
    "Cleanse": "Removes allied debuffs.",
    "Strength": "Increases outgoing damage.",
    "Regenerate": "Heals at turn start.",
    "Fortify": "Builds repeated block.",
    "Momentum": "Boosts the next attack.",
    "Rally": "Buffs allied tempo.",
    "Team Block": "Grants allied block.",
    "Heat": "Charges stronger attacks.",
    "Biomass": "Builds Helix boss resources.",
}

DEBUFF_LABELS = {
    "Infect": "Applies lingering infection damage.",
    "Marked": "Amplifies Blackwire focus fire.",
    "Suppress": "Reduces attack-card damage.",
    "Burn": "Applies decaying burn damage.",
    "Bleed": "Triggers damage on later hits.",
    "Nullify": "Blocks the next positive status.",
    "Strip Buff": "Removes player buffs.",
    "Burst": "Triggers infection burst damage.",
    "Steal Block": "Removes player block.",
    "Detonate": "Self-destructs after acting.",
}


def _lerp(start: float, end: float, progress: float) -> float:
    return start + ((end - start) * progress)


def _ease_out(progress: float) -> float:
    progress = max(0.0, min(1.0, progress))
    return 1.0 - ((1.0 - progress) * (1.0 - progress))


def _rect_from_center(center: tuple[float, float], size: tuple[float, float]) -> tuple[int, int, int, int]:
    width = max(1, int(size[0]))
    height = max(1, int(size[1]))
    x = int(center[0] - (width / 2))
    y = int(center[1] - (height / 2))
    return x, y, width, height


class CombatUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_card_index: int | None = None
        self._hover_started_at = 0
        self._pressed_card_index: int | None = None
        self._selected_card_index: int | None = None
        self._selected_card_id: str | None = None
        self._selected_target_id: str | None = None
        self._target_mode: str | None = None
        self._selected_started_at = 0
        self._hovered_enemy_id: str | None = None
        self._hovered_end_turn = False
        self._pressed_end_turn = False
        self._mouse_pos: tuple[int, int] = (-1, -1)
        self._pending_action: dict[str, Any] | None = None

    def preload_assets(self) -> None:
        if pygame is None:
            return
        self._load_image(resolve_asset_path("ui", "bg_combat.png"))

    def poll_action(self, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        if self._pending_action is None:
            return None
        hand = combat_state.get("player_hand", [])
        hand_index = int(self._pending_action.get("hand_index", -1))
        expected_card_id = self._pending_action.get("card_id")
        if hand_index < 0 or hand_index >= len(hand):
            self._clear_selection()
            return None
        if expected_card_id is not None and hand[hand_index].get("id") != expected_card_id:
            self._clear_selection()
            return None
        if self._now_ms() < int(self._pending_action["ready_at"]):
            return None
        action = dict(self._pending_action["action"])
        self._clear_selection()
        return action

    def handle_event(self, event: Any, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self.build_layout(combat_state)

        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
            hovered_card = self._card_index_at_position(layout, event.pos)
            if hovered_card != self._hovered_card_index:
                self._hover_started_at = self._now_ms()
            self._hovered_card_index = hovered_card
            self._hovered_enemy_id = self._enemy_id_at_position(layout, event.pos)
            self._hovered_end_turn = point_in_rect(event.pos, layout["end_turn_rect"])
            if (
                layout["selected_card"] is not None
                and layout["selected_card"]["target_mode"] == "single_enemy"
                and self._hovered_enemy_id in layout["selected_card"]["valid_target_ids"]
            ):
                self._selected_target_id = self._hovered_enemy_id
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._pending_action is None:
                self._pressed_card_index = self._card_index_at_position(layout, event.pos)
                self._pressed_end_turn = point_in_rect(event.pos, layout["end_turn_rect"])
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if layout["selected_card"] is not None and self._pending_action is None:
                self._clear_selection()
            return None

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
                return {"type": "notice", "message": "Enemy actions are still resolving.", "level": "error"}
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._card_index_at_position(layout, event.pos) is not None or point_in_rect(event.pos, layout["end_turn_rect"]):
                    return {"type": "notice", "message": "Enemy actions are still resolving.", "level": "error"}
            return None

        if self._pending_action is not None:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._clear_selection()
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            released_card_index = self._card_index_at_position(layout, event.pos)
            pressed_card_index = self._pressed_card_index
            pressed_end_turn = self._pressed_end_turn
            self._pressed_card_index = None
            self._pressed_end_turn = False

            if layout["selected_card"] is not None:
                selected_card = layout["selected_card"]
                clicked_enemy_id = self._enemy_id_at_position(layout, event.pos)
                if selected_card["target_mode"] == "single_enemy" and clicked_enemy_id in selected_card["valid_target_ids"]:
                    if clicked_enemy_id == self._selected_target_id:
                        self._queue_card_action(
                            selected_card["source_card"]["index"],
                            clicked_enemy_id,
                            selected_card["source_card"]["card_id"],
                            targeted=True,
                            fast_mode=combat_state.get("presentation", {}).get("fast_mode", False),
                        )
                    else:
                        self._selected_target_id = clicked_enemy_id
                    return None
                if released_card_index is not None and released_card_index != self._selected_card_index:
                    return self._activate_card(layout, released_card_index, combat_state)
                return None

            if pressed_end_turn and point_in_rect(event.pos, layout["end_turn_rect"]):
                return {"type": "end_turn"}
            if released_card_index is None or released_card_index != pressed_card_index:
                return None
            return self._activate_card(layout, released_card_index, combat_state)

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            if layout["selected_card"] is not None:
                self._clear_selection()
            return None

        if pygame.K_1 <= event.key <= pygame.K_9:
            hand_index = event.key - pygame.K_1
            if hand_index >= len(layout["hand_cards"]):
                return {"type": "notice", "message": "That card slot is empty.", "level": "error"}
            return self._activate_card(layout, hand_index, combat_state)

        if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            selected_card = layout["selected_card"]
            if selected_card is not None and selected_card["target_mode"] == "single_enemy":
                if self._selected_target_id is None:
                    return {"type": "notice", "message": "No valid target is available.", "level": "error"}
                self._queue_card_action(
                    selected_card["source_card"]["index"],
                    self._selected_target_id,
                    selected_card["source_card"]["card_id"],
                    targeted=True,
                    fast_mode=combat_state.get("presentation", {}).get("fast_mode", False),
                )
                return None
            return {"type": "end_turn"}

        if event.key in {pygame.K_e, pygame.K_SPACE}:
            if layout["selected_card"] is not None:
                return {"type": "notice", "message": "Confirm or cancel the selected card first.", "level": "error"}
            return {"type": "end_turn"}

        return None

    def _activate_card(self, layout: dict[str, Any], hand_index: int, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        card_layout = layout["hand_cards"][hand_index]
        if not card_layout["playable"]:
            return {"type": "notice", "message": card_layout["disabled_reason"], "level": "error"}
        self._selected_card_index = hand_index
        self._selected_card_id = card_layout["card_id"]
        self._target_mode = card_layout["target_mode"]
        self._selected_started_at = self._now_ms()
        self._selected_target_id = card_layout["default_target_id"]

        if card_layout["target_mode"] == "single_enemy":
            return None

        self._queue_card_action(
            hand_index,
            None,
            card_layout["card_id"],
            targeted=False,
            fast_mode=combat_state.get("presentation", {}).get("fast_mode", False),
        )
        return None

    def _queue_card_action(
        self,
        hand_index: int,
        target_id: str | None,
        card_id: str,
        *,
        targeted: bool,
        fast_mode: bool,
    ) -> None:
        now = self._now_ms()
        duration = 72 if fast_mode else RESOLVE_ANIM_MS
        action = {"type": "play_card", "hand_index": hand_index}
        if target_id is not None:
            action["target_id"] = target_id
        self._pending_action = {
            "action": action,
            "ready_at": now + duration,
            "started_at": now,
            "hand_index": hand_index,
            "card_id": card_id,
            "targeted": targeted,
        }

    def _clear_selection(self, *, keep_hover: bool = False) -> None:
        self._selected_card_index = None
        self._selected_card_id = None
        self._selected_target_id = None
        self._target_mode = None
        self._selected_started_at = 0
        self._pending_action = None
        if not keep_hover:
            self._hovered_enemy_id = None

    def build_layout(self, combat_state: dict[str, Any]) -> dict[str, Any]:
        presentation = combat_state.get("presentation", {})
        hand = combat_state.get("player_hand", [])
        player = combat_state["player"]
        character = combat_state.get("character") or {}
        enemies = combat_state["enemies"]
        living_enemy_ids = list(combat_state.get("living_enemy_ids", []))

        if self._hovered_card_index is not None and self._hovered_card_index >= len(hand):
            self._hovered_card_index = None
        if self._pressed_card_index is not None and self._pressed_card_index >= len(hand):
            self._pressed_card_index = None
        if self._selected_card_index is not None:
            if self._selected_card_index >= len(hand):
                self._clear_selection()
            elif hand[self._selected_card_index].get("id") != self._selected_card_id:
                self._clear_selection()
        if combat_state.get("turn_owner") != "player" and self._pending_action is None:
            self._clear_selection(keep_hover=True)

        hand_cards: list[dict[str, Any]] = []
        for index, card in enumerate(hand):
            target_mode = self._card_target_mode(card)
            playable, disabled_reason = self._card_playability(
                card,
                player,
                living_enemy_ids,
                combat_state.get("turn_owner", "player"),
            )
            geometry = self._hand_card_geometry(index, len(hand))
            hand_cards.append(
                {
                    "index": index,
                    "card": card,
                    "card_id": card["id"],
                    "playable": playable,
                    "disabled_reason": disabled_reason,
                    "target_mode": target_mode,
                    "valid_target_ids": list(living_enemy_ids) if target_mode in {"single_enemy", "all_enemies"} else [],
                    "default_target_id": self._weakest_enemy_id(enemies, list(living_enemy_ids)) if target_mode == "single_enemy" else None,
                    "footer_label": self._card_footer_label(card, target_mode),
                    "summary": " ".join(card_summary_lines(card, max_lines=2)),
                    "center": geometry["center"],
                    "size": geometry["size"],
                    "angle": geometry["angle"],
                    "hit_rect": self._hand_card_hit_rect(
                        geometry["center"],
                        geometry["size"],
                        geometry["angle"],
                        scale=self._hand_card_scale(index),
                    ),
                }
            )

        selected_card = None
        if self._selected_card_index is not None and 0 <= self._selected_card_index < len(hand_cards):
            source_card = hand_cards[self._selected_card_index]
            if source_card["playable"]:
                if source_card["target_mode"] == "single_enemy" and self._selected_target_id not in source_card["valid_target_ids"]:
                    self._selected_target_id = source_card["default_target_id"]
                progress = 1.0 if self._pending_action is not None else _ease_out(self._animation_progress(self._selected_started_at, SELECT_ANIM_MS))
                center_x = _lerp(source_card["center"][0], CARD_CENTER[0], progress)
                center_y = _lerp(source_card["center"][1], CARD_CENTER[1], progress)
                if self._pending_action is not None:
                    drift = _ease_out(self._animation_progress(int(self._pending_action["started_at"]), RESOLVE_ANIM_MS))
                    center_x = _lerp(center_x, center_x + 18, drift)
                    center_y = _lerp(center_y, center_y - 12, drift)
                selected_rect = _rect_from_center((center_x, center_y), (214, int(214 * CARD_PORTRAIT_HEIGHT_RATIO)))
                selected_card = {
                    "source_card": source_card,
                    "target_mode": source_card["target_mode"],
                    "target_id": self._selected_target_id,
                    "valid_target_ids": list(source_card["valid_target_ids"]),
                    "center": (center_x, center_y),
                    "center_rect": selected_rect,
                }
            else:
                self._clear_selection(keep_hover=True)

        player_actor = self._player_actor_layout(player, character)
        enemy_actors = self._enemy_actor_layout(enemies, selected_card)
        tooltip_regions = []
        player_status_items = self._status_items_for_player(player)
        player_actor["status_regions"] = self._status_regions(player_status_items, player_actor["status_origin"], anchor="left")
        tooltip_regions.extend(player_actor["status_regions"])
        for enemy_actor in enemy_actors:
            enemy_status_items = self._status_items_for_enemy(enemy_actor["enemy"])
            enemy_actor["status_regions"] = self._status_regions(enemy_status_items, enemy_actor["status_origin"], anchor="center")
            tooltip_regions.extend(enemy_actor["status_regions"])
            tooltip_regions.append(
                {
                    "rect": enemy_actor["intent_rect"],
                    "title": f"{enemy_actor['name']} intent",
                    "text": self._intent_tooltip(enemy_actor["enemy"]),
                }
            )
        combat_modifiers = self._combat_modifier_items(combat_state.get("run_modifiers", []))
        tooltip_regions.extend(
            {
                "rect": modifier["rect"],
                "title": modifier["name"],
                "text": self._modifier_tooltip_text(modifier),
            }
            for modifier in combat_modifiers
        )

        return {
            "status_message": combat_state.get("status_message", ""),
            "turn_label": f"Turn {combat_state.get('turn_number', 0)}",
            "turn_owner_label": combat_state.get("turn_owner", "player").title(),
            "player": player,
            "character": character,
            "player_actor": player_actor,
            "enemy_actors": enemy_actors,
            "hand_cards": hand_cards,
            "selected_card": selected_card,
            "active_bark": combat_state.get("active_bark"),
            "end_turn_rect": END_TURN_RECT,
            "end_turn_hovered": self._hovered_end_turn,
            "any_playable": any(card["playable"] for card in hand_cards),
            "helper_panel_rect": HELPER_PANEL_RECT,
            "helper_summary": self._helper_summary(hand_cards, selected_card, combat_state.get("event_log", [])),
            "helper_recent": self._build_recent_summary(combat_state.get("event_log", [])),
            "living_enemy_ids": living_enemy_ids,
            "high_contrast": presentation.get("high_contrast", False),
            "tooltip": self._tooltip_at_position(tooltip_regions, self._mouse_pos),
            "targeting_active": selected_card is not None,
            "combat_modifiers": combat_modifiers,
        }

    def _build_recent_summary(self, event_log: list[dict[str, Any]]) -> str:
        if not event_log:
            return "No actions resolved yet."
        latest_event = event_log[-1]
        if "summary" in latest_event:
            return str(latest_event["summary"])
        resolution_parts = [
            f"{resolution['type']} {resolution['applied']} -> {resolution['target']}"
            for resolution in latest_event.get("resolutions", [])
        ]
        summary = ", ".join(resolution_parts) if resolution_parts else "No effect."
        return f"{latest_event.get('card_id', 'action')}: {summary}"

    def _card_playability(
        self,
        card: dict[str, Any],
        player: dict[str, Any],
        living_enemy_ids: list[str],
        turn_owner: str,
    ) -> tuple[bool, str]:
        if turn_owner != "player":
            return False, "Wait for enemy actions"
        if card.get("type") == "status":
            return False, "Status cards cannot be played"
        if card["cost"] > player["energy"]:
            missing = card["cost"] - player["energy"]
            return False, f"Need {missing} more energy"
        target_mode = self._card_target_mode(card)
        if target_mode in {"single_enemy", "all_enemies"} and not living_enemy_ids:
            return False, "No living target"
        return True, "Ready"

    def _card_target_mode(self, card: dict[str, Any]) -> str:
        has_enemy = False
        has_all_enemies = False
        has_self = False
        for effect in card.get("effects", []):
            target_kind = self._effect_target_kind(effect)
            if target_kind == "all_enemies":
                has_all_enemies = True
            elif target_kind == "enemy":
                has_enemy = True
            elif target_kind == "self":
                has_self = True
        if has_all_enemies:
            return "all_enemies"
        if has_enemy:
            return "single_enemy"
        if has_self:
            return "immediate_self"
        return "immediate_none"

    def _effect_target_kind(self, effect: dict[str, Any]) -> str:
        explicit = effect.get("target")
        if explicit in {"enemy", "self", "all_enemies"}:
            return str(explicit)
        effect_type = effect.get("type")
        if effect_type in {"damage", "multi_damage", "lifesteal_damage", "apply_weak", "apply_vulnerable"}:
            return "enemy"
        return "self"

    def _card_footer_label(self, card: dict[str, Any], target_mode: str) -> str:
        if target_mode == "single_enemy":
            return "Target: enemy"
        if target_mode == "all_enemies":
            return "Target: all enemies"
        if target_mode == "immediate_self":
            return "Target: self"
        return "Play instantly"

    def _weakest_enemy_id(self, enemies: list[dict[str, Any]], valid_ids: list[str]) -> str | None:
        ranked = [
            (enemy["current_hp"], index, enemy["id"])
            for index, enemy in enumerate(enemies)
            if enemy["id"] in valid_ids
        ]
        if not ranked:
            return None
        ranked.sort(key=lambda item: (item[0], item[1]))
        return ranked[0][2]

    def _hand_card_geometry(self, index: int, hand_count: int) -> dict[str, Any]:
        if hand_count <= 5:
            width = 160
        elif hand_count <= 7:
            width = 152
        elif hand_count <= 9:
            width = 142
        else:
            width = 134
        height = int(width * CARD_PORTRAIT_HEIGHT_RATIO)
        spread = min(760, max(0, hand_count - 1) * (width * 0.58))
        offset = 0.0 if hand_count == 1 else (index / max(1, hand_count - 1)) * 2.0 - 1.0
        center_x = HAND_CENTER_X + (offset * (spread / 2))
        center_y = HAND_CENTER_Y + (abs(offset) ** 1.45) * 28
        angle = -11.5 * offset
        return {"center": (center_x, center_y), "size": (width, height), "angle": angle}

    def _hand_card_scale(self, index: int) -> float:
        if index == self._hovered_card_index and index != self._selected_card_index:
            hover_progress = _ease_out(self._animation_progress(self._hover_started_at, 90))
            return 1.0 + (0.08 * hover_progress)
        if index == self._selected_card_index:
            return 0.9
        return 1.0

    def _hand_card_hit_rect(
        self,
        center: tuple[float, float],
        size: tuple[float, float],
        angle: float,
        *,
        scale: float,
    ) -> tuple[int, int, int, int]:
        width = size[0] * scale
        height = size[1] * scale
        radians = math.radians(abs(angle))
        rotated_width = abs(math.cos(radians) * width) + abs(math.sin(radians) * height)
        rotated_height = abs(math.cos(radians) * height) + abs(math.sin(radians) * width)
        y_lift = CARD_HOVER_LIFT if scale > 1.0 else 0
        return _rect_from_center((center[0], center[1] - y_lift), (rotated_width, rotated_height))

    def _player_actor_layout(self, player: dict[str, Any], character: dict[str, Any]) -> dict[str, Any]:
        accent = tuple(character.get("accent_color", [232, 88, 72]))
        actor_width = int(96 * PLAYER_SCALE)
        actor_height = int(156 * PLAYER_SCALE)
        actor_rect = pygame.Rect(int(PLAYER_FOOT[0] - actor_width / 2), int(PLAYER_FOOT[1] - actor_height), actor_width, actor_height) if pygame is not None else None
        return {
            "character_id": character.get("id", player.get("character_id", "runner")),
            "name": character.get("name", "Runner"),
            "accent": accent,
            "foot": PLAYER_FOOT,
            "actor_rect": actor_rect,
            "hud_rect": (46, 452, 286, 58),
            "status_origin": (56, 515),
            "player": player,
        }

    def _enemy_actor_layout(self, enemies: list[dict[str, Any]], selected_card: dict[str, Any] | None) -> list[dict[str, Any]]:
        slots = ENEMY_SLOT_MAP.get(len(enemies), ENEMY_SLOT_MAP[5])
        valid_target_ids = set(selected_card["valid_target_ids"]) if selected_card is not None else set()
        actors: list[dict[str, Any]] = []
        for index, enemy in enumerate(enemies):
            foot_x, foot_y, scale = slots[min(index, len(slots) - 1)]
            if enemy.get("tier") == "boss":
                scale *= 1.12
            elif enemy.get("tier") == "elite":
                scale *= 1.06
            width = int(92 * scale)
            height = int(146 * scale)
            top_y = int(foot_y - height)
            rect = pygame.Rect(int(foot_x - width / 2), top_y, width, height) if pygame is not None else None
            accent = FACTION_COLORS.get(str(enemy.get("faction_id", "legacy")), FACTION_COLORS["legacy"])
            actors.append(
                {
                    "enemy": enemy,
                    "id": enemy["id"],
                    "name": enemy["name"],
                    "foot": (foot_x, foot_y),
                    "actor_rect": rect,
                    "accent": accent,
                    "hp_bar_rect": (int(foot_x - 62), int(foot_y + 14), 124, 12),
                    "block_rect": (int(foot_x + 70), int(foot_y + 4), 42, 26),
                    "intent_rect": (int(foot_x - 68), int(top_y - 40), 136, 28),
                    "status_origin": (int(foot_x), int(foot_y + 34)),
                    "targeted": enemy["id"] == (selected_card["target_id"] if selected_card is not None else None),
                    "valid_target": enemy["id"] in valid_target_ids if selected_card is not None else True,
                    "dimmed": selected_card is not None and selected_card["target_mode"] in {"single_enemy", "all_enemies"} and enemy["id"] not in valid_target_ids,
                }
            )
        return actors

    def _status_items_for_player(self, player: dict[str, Any]) -> list[dict[str, Any]]:
        statuses: list[dict[str, Any]] = []
        for stat_key in ("strength", "weak", "vulnerable"):
            value = int(player.get(stat_key, 0) or 0)
            if value > 0:
                statuses.append(self._status_item(stat_key, value))
        combat_statuses = player.get("combat_statuses", {})
        if isinstance(combat_statuses, dict):
            for key in ("infect", "burn", "bleed", "marked", "suppressed"):
                value = int(combat_statuses.get(key, 0) or 0)
                if value > 0:
                    statuses.append(self._status_item(key, value))
            if combat_statuses.get("nullified"):
                statuses.append(self._status_item("nullified", 1, show_count=False))
        return statuses[:6]

    def _status_items_for_enemy(self, enemy: dict[str, Any]) -> list[dict[str, Any]]:
        statuses: list[dict[str, Any]] = []
        for stat_key in ("strength", "weak", "vulnerable"):
            value = int(enemy.get(stat_key, 0) or 0)
            if value > 0:
                statuses.append(self._status_item(stat_key, value))
        raw_statuses = enemy.get("statuses", {})
        if isinstance(raw_statuses, dict):
            for key in ("infect", "burn", "fortified", "regenerate", "momentum", "overheat", "biomass"):
                value = int(raw_statuses.get(key, 0) or 0)
                if value > 0:
                    statuses.append(self._status_item(key, value))
            if int(raw_statuses.get("mutated", 0) or 0) > 0:
                statuses.append(self._status_item("mutated", 1, show_count=False))
        return statuses[:6]

    def _status_item(self, status_id: str, value: int, *, show_count: bool = True) -> dict[str, Any]:
        meta = STATUS_META.get(status_id, {"label": status_id.replace("_", " ").title(), "short": status_id[:3].upper(), "color": (186, 198, 224)})
        count = max(1, int(value))
        return {"id": status_id, "label": meta["label"], "short": meta["short"], "color": meta["color"], "count": count, "show_count": show_count and count > 1}

    def _status_regions(self, status_items: list[dict[str, Any]], origin: tuple[int, int], *, anchor: str) -> list[dict[str, Any]]:
        if not status_items:
            return []
        chip_width = 34
        total_width = (len(status_items) * chip_width) + (max(0, len(status_items) - 1) * 6)
        start_x = origin[0] - (total_width // 2) if anchor == "center" else origin[0]
        regions = []
        for index, item in enumerate(status_items):
            rect = (start_x + (index * (chip_width + 6)), origin[1], chip_width, 26)
            count_text = f" x{item['count']}" if item["show_count"] else ""
            regions.append({"rect": rect, "title": item["label"], "text": f"{item['label']}{count_text}".strip(), "item": item})
        return regions

    def _combat_modifier_items(self, run_modifiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(run_modifiers, list):
            return []

        filtered = [
            modifier
            for modifier in run_modifiers
            if modifier.get("type") == "relic" or modifier.get("temporary") or modifier.get("duration_label")
        ]
        filtered.sort(
            key=lambda modifier: (
                0 if modifier.get("type") == "relic" else 1,
                str(modifier.get("name", "")),
            )
        )

        items: list[dict[str, Any]] = []
        start_x, start_y = COMBAT_MODIFIER_ORIGIN
        for index, modifier in enumerate(filtered[:COMBAT_MODIFIER_LIMIT]):
            slot_x = start_x + (index * (COMBAT_MODIFIER_SLOT + COMBAT_MODIFIER_GAP))
            items.append(
                {
                    **modifier,
                    "rect": (slot_x, start_y, COMBAT_MODIFIER_SLOT, COMBAT_MODIFIER_SLOT),
                    "accent": self._modifier_accent(modifier.get("type", modifier.get("kind", "status"))),
                    "abbrev": self._modifier_abbrev(str(modifier.get("name", "?"))),
                }
            )
        return items

    def _modifier_tooltip_text(self, modifier: dict[str, Any]) -> str:
        parts = [str(modifier.get("description", ""))]
        duration_label = modifier.get("duration_label")
        if duration_label:
            parts.append(str(duration_label))
        downside = modifier.get("downside")
        if downside:
            parts.append(f"Tradeoff: {downside}")
        return " ".join(part for part in parts if part).strip()

    def _modifier_accent(self, modifier_type: str) -> tuple[int, int, int]:
        palettes = {
            "relic": (104, 216, 255),
            "blessing": (110, 220, 164),
            "curse": (232, 106, 112),
            "status": (188, 162, 255),
        }
        return palettes.get(modifier_type, (164, 176, 204))

    def _modifier_abbrev(self, name: str) -> str:
        words = [part for part in name.split() if part]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return f"{words[0][0]}{words[1][0]}".upper()

    def _helper_summary(self, hand_cards: list[dict[str, Any]], selected_card: dict[str, Any] | None, event_log: list[dict[str, Any]]) -> str:
        if selected_card is not None:
            source = selected_card["source_card"]
            if source["target_mode"] == "single_enemy":
                return "Select a target. Hover or click another enemy to retarget, then click again to confirm."
            if source["target_mode"] == "all_enemies":
                return "Armed for all-enemy hit. Action will resolve immediately."
            if source["target_mode"] == "immediate_self":
                return "Self-targeted card armed. Action will resolve immediately."
            return "Immediate card armed. Action will resolve immediately."
        hovered = next((card for card in hand_cards if card["index"] == self._hovered_card_index), None)
        if hovered is not None:
            return hovered["summary"] or hovered["footer_label"]
        return self._build_recent_summary(event_log)

    def render(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        presentation = combat_state.get("presentation", {})
        high_contrast = presentation.get("high_contrast", False)
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(combat_state)

        background = self._scaled_image(resolve_asset_path("ui", "bg_combat.png"), surface.get_size())
        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176, color=(8, 8, 16))
        self._draw_stage_gradient(surface)
        if layout["selected_card"] is not None:
            self._draw_target_focus_scrim(surface)

        self._draw_turn_header(surface, layout, high_contrast=high_contrast)
        self._draw_combat_modifier_strip(surface, layout, high_contrast=high_contrast)

        self._draw_player_actor(surface, layout["player_actor"], high_contrast=high_contrast, targeted=layout["selected_card"] is not None and layout["selected_card"]["target_mode"] == "immediate_self")

        if layout["selected_card"] is not None:
            self._draw_target_guides(surface, layout)

        for enemy_actor in layout["enemy_actors"]:
            self._draw_enemy_actor(surface, enemy_actor, high_contrast=high_contrast)

        if layout["active_bark"] is not None:
            self._render_bark(surface, layout["active_bark"], layout["enemy_actors"])

        self._draw_helper_panel(surface, layout, high_contrast=high_contrast)
        self._draw_end_turn_button(surface, layout)
        self._draw_hand(surface, layout, high_contrast=high_contrast)
        if layout["selected_card"] is not None:
            self._draw_selected_card(surface, layout["selected_card"], high_contrast=high_contrast)
        if layout["tooltip"] is not None:
            self._draw_tooltip(surface, layout["tooltip"])

    def _draw_stage_gradient(self, surface: Any) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for row in range(surface.get_height()):
            alpha = int(_lerp(12, 72, row / max(1, surface.get_height() - 1)))
            pygame.draw.line(overlay, (18, 12, 28, alpha), (0, row), (surface.get_width(), row))
        surface.blit(overlay, (0, 0))

    def _draw_target_focus_scrim(self, surface: Any) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((6, 8, 14, 64))
        surface.blit(overlay, (0, 0))

    def _draw_turn_header(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        del high_contrast
        origin_x, origin_y = TURN_HEADER_ORIGIN
        owner_color = (255, 214, 110) if layout["turn_owner_label"] == "Player" else (232, 106, 112)
        line_color = (132, 206, 252)
        shadow_color = (0, 0, 0)

        pygame.draw.rect(
            surface,
            line_color,
            pygame.Rect(origin_x, origin_y + 2, TURN_HEADER_LINE_WIDTH, 40),
            border_radius=2,
        )

        turn_shadow = self._font.render(layout["turn_label"], True, shadow_color)
        turn_shadow.set_alpha(150)
        surface.blit(turn_shadow, (origin_x + 13, origin_y - 1))
        turn_label = self._font.render(layout["turn_label"], True, (236, 244, 255))
        surface.blit(turn_label, (origin_x + 11, origin_y - 3))

        owner_shadow = self._small_font.render(f"{layout['turn_owner_label']} Turn", True, shadow_color)
        owner_shadow.set_alpha(140)
        surface.blit(owner_shadow, (origin_x + 13, origin_y + 24))
        owner_label = self._small_font.render(f"{layout['turn_owner_label']} Turn", True, owner_color)
        surface.blit(owner_label, (origin_x + 11, origin_y + 22))

    def _draw_combat_modifier_strip(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        for modifier in layout["combat_modifiers"]:
            rect = pygame.Rect(*modifier["rect"])
            accent = modifier["accent"]
            if high_contrast:
                accent = tuple(min(255, channel + 16) for channel in accent)
            if modifier.get("type") == "relic":
                art = relic_assets.get_relic_art(modifier["id"], rect.size)
                if art is not None:
                    art_rect = art.get_rect(center=rect.center)
                    surface.blit(art, art_rect.topleft)
                else:
                    label = self._tiny_font.render(modifier["abbrev"], True, accent)
                    surface.blit(label, label.get_rect(center=rect.center))
            else:
                label = self._tiny_font.render(modifier["abbrev"], True, accent)
                surface.blit(label, label.get_rect(center=rect.center))
                pygame.draw.line(surface, accent, (rect.x + 4, rect.bottom - 3), (rect.right - 4, rect.bottom - 3), 2)

            if modifier.get("temporary") and isinstance(modifier.get("remaining"), int):
                badge_rect = pygame.Rect(rect.right - 9, rect.y - 3, 16, 16)
                pygame.draw.rect(surface, (255, 214, 110), badge_rect, border_radius=8)
                badge = self._tiny_font.render(str(modifier["remaining"]), True, (18, 24, 36))
                surface.blit(badge, badge.get_rect(center=badge_rect.center))
            if self._mouse_pos != (-1, -1) and point_in_rect(self._mouse_pos, modifier["rect"]):
                underline_y = rect.bottom + 4
                pygame.draw.line(surface, (255, 214, 110), (rect.x + 2, underline_y), (rect.right - 2, underline_y), 2)

    def _draw_player_actor(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool, targeted: bool) -> None:
        accent = actor["accent"]
        rect = actor["actor_rect"]
        foot_x, foot_y = actor["foot"]
        pulse = 0.76 + (0.12 * math.sin(self._now_ms() / 180.0))
        ring_color = tuple(min(255, int(channel * (1.15 if targeted else pulse))) for channel in accent)
        self._draw_ground_plate(surface, foot=(foot_x, foot_y), accent=ring_color, targeted=targeted)

        body_surface = pygame.Surface((rect.width + 22, rect.height + 22), pygame.SRCALPHA)
        self._draw_player_standee_body(body_surface, body_surface.get_rect().inflate(-22, -22).move(11, 11), actor["character_id"], accent=accent)
        surface.blit(body_surface, (rect.x - 11, rect.y - 11))
        self._draw_player_hud(surface, actor, high_contrast=high_contrast, targeted=targeted)

    def _draw_player_standee_body(self, surface: Any, rect: Any, character_id: str, *, accent: tuple[int, int, int]) -> None:
        outline = tuple(min(255, int(channel * 1.18)) for channel in accent)
        shadow = (*accent, 90)
        pygame.draw.ellipse(surface, shadow, pygame.Rect(rect.x + 12, rect.y + rect.height - 26, rect.width - 24, 20))
        body_color = (28, 34, 46)
        panel_color = tuple(max(44, int(channel * 0.38)) for channel in accent)

        if character_id == "operator":
            torso = [(rect.centerx, rect.y + 20), (rect.x + rect.width - 14, rect.y + 74), (rect.centerx + 18, rect.bottom - 8), (rect.centerx - 24, rect.bottom - 18), (rect.x + 16, rect.y + 82)]
            visor_rect = pygame.Rect(rect.centerx - 16, rect.y + 14, 32, 10)
            pygame.draw.polygon(surface, body_color, torso)
            pygame.draw.polygon(surface, outline, torso, 3)
            pygame.draw.rect(surface, panel_color, visor_rect, border_radius=5)
            pygame.draw.rect(surface, outline, visor_rect, 2, border_radius=5)
            pygame.draw.line(surface, outline, (rect.centerx + 22, rect.y + 68), (rect.right - 4, rect.y + 116), 5)
        elif character_id == "bio_hacker":
            torso = [(rect.centerx - 10, rect.y + 20), (rect.right - 10, rect.y + 64), (rect.centerx + 18, rect.bottom - 6), (rect.x + 18, rect.bottom - 12), (rect.x + 6, rect.y + 76)]
            pygame.draw.polygon(surface, body_color, torso)
            pygame.draw.polygon(surface, outline, torso, 3)
            tube_color = (124, 255, 158)
            pygame.draw.line(surface, tube_color, (rect.x + 18, rect.y + 68), (rect.centerx + 16, rect.bottom - 30), 4)
            pygame.draw.circle(surface, tube_color, (rect.centerx + 18, rect.bottom - 28), 7)
        else:
            torso = [(rect.centerx - 22, rect.y + 26), (rect.right - 18, rect.y + 70), (rect.centerx + 20, rect.bottom - 10), (rect.x + 16, rect.bottom - 18), (rect.x + 10, rect.y + 74)]
            pygame.draw.polygon(surface, body_color, torso)
            pygame.draw.polygon(surface, outline, torso, 3)
            pygame.draw.line(surface, outline, (rect.centerx + 26, rect.y + 62), (rect.right + 6, rect.y + 18), 5)

        head_center = (rect.centerx - (5 if character_id == "bio_hacker" else 0), rect.y + 10)
        pygame.draw.circle(surface, body_color, head_center, 16)
        pygame.draw.circle(surface, outline, head_center, 16, 3)
        pygame.draw.line(surface, panel_color, (head_center[0] - 10, head_center[1] + 2), (head_center[0] + 10, head_center[1] + 2), 3)
        pygame.draw.line(surface, outline, (rect.centerx - 10, rect.bottom - 16), (rect.centerx - 22, rect.bottom + 10), 4)
        pygame.draw.line(surface, outline, (rect.centerx + 4, rect.bottom - 12), (rect.centerx + 18, rect.bottom + 10), 4)

    def _draw_player_hud(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool, targeted: bool) -> None:
        player = actor["player"]
        hud_rect = pygame.Rect(*actor["hud_rect"])
        accent = actor["accent"]
        border = tuple(min(255, channel + 24) for channel in accent) if high_contrast else tuple(min(255, channel + 10) for channel in accent)
        self._draw_panel(surface, hud_rect, fill=(9, 14, 22, 212), border=border, radius=16)
        if targeted:
            pygame.draw.rect(surface, (*accent, 56), hud_rect.inflate(6, 6), 1, border_radius=18)

        hp_bar_rect = pygame.Rect(hud_rect.x + 12, hud_rect.y + 10, 168, 14)
        self._draw_meter(surface, hp_bar_rect, current=int(player["current_hp"]), maximum=max(1, int(player["max_hp"])), fill=(232, 106, 112), background=(36, 18, 28), border=(252, 210, 214), label=f"HP {player['current_hp']}/{player['max_hp']}", label_font=self._tiny_font)
        self._draw_energy_row(surface, rect=(hud_rect.x + 12, hud_rect.y + 30, 168, 16), current=int(player["energy"]), maximum=max(1, int(player["max_energy"])))

        if int(player.get("block", 0) or 0) > 0:
            self._draw_block_chip(surface, rect=(hud_rect.right - 82, hud_rect.y + 10, 68, 34), value=int(player["block"]), accent=(104, 190, 255))
        self._draw_text(surface, actor["name"], (hud_rect.right - 150, hud_rect.y + 36), self._tiny_font, width=138)
        self._draw_status_row(surface, actor["status_regions"])

    def _draw_enemy_actor(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool) -> None:
        enemy = actor["enemy"]
        accent = actor["accent"]
        foot_x, foot_y = actor["foot"]
        rect = actor["actor_rect"]
        self._draw_ground_plate(surface, foot=(foot_x, foot_y), accent=accent, targeted=actor["targeted"], dimmed=actor["dimmed"])

        body_surface = pygame.Surface((rect.width + 24, rect.height + 24), pygame.SRCALPHA)
        self._draw_enemy_standee_body(body_surface, body_surface.get_rect().inflate(-24, -24).move(12, 12), enemy=enemy, accent=accent, alpha=96 if actor["dimmed"] else 255)
        surface.blit(body_surface, (rect.x - 12, rect.y - 12))

        self._draw_intent_banner(surface, actor, high_contrast=high_contrast)
        self._draw_text(surface, actor["name"], (rect.x - 12, actor["hp_bar_rect"][1] - 16), self._tiny_font, width=rect.width + 24)
        self._draw_enemy_hp(surface, actor)
        if int(enemy.get("block", 0) or 0) > 0:
            self._draw_block_chip(surface, rect=actor["block_rect"], value=int(enemy["block"]), accent=(112, 188, 255))
        self._draw_status_row(surface, actor["status_regions"])

        if actor["targeted"]:
            pulse_alpha = 120 + int(32 * math.sin(self._now_ms() / 100.0))
            ring_rect = pygame.Rect(int(foot_x - 64), int(foot_y - 9), 128, 18)
            ring_surface = pygame.Surface((ring_rect.width, ring_rect.height), pygame.SRCALPHA)
            pygame.draw.ellipse(ring_surface, (255, 88, 88, max(60, min(180, pulse_alpha))), ring_surface.get_rect(), 4)
            surface.blit(ring_surface, ring_rect.topleft)
        elif actor["valid_target"]:
            soft_rect = pygame.Rect(int(foot_x - 56), int(foot_y - 7), 112, 14)
            soft_surface = pygame.Surface((soft_rect.width, soft_rect.height), pygame.SRCALPHA)
            pygame.draw.ellipse(soft_surface, (*accent, 46), soft_surface.get_rect(), 2)
            surface.blit(soft_surface, soft_rect.topleft)

    def _draw_enemy_standee_body(self, surface: Any, rect: Any, *, enemy: dict[str, Any], accent: tuple[int, int, int], alpha: int) -> None:
        body_color = (30, 36, 48, alpha)
        outline = (*tuple(min(255, int(channel * 1.1)) for channel in accent), alpha)
        panel = (*tuple(max(40, int(channel * 0.34)) for channel in accent), alpha)
        faction = str(enemy.get("faction_id", "legacy"))

        shadow_rect = pygame.Rect(rect.x + 10, rect.bottom - 22, rect.width - 20, 18)
        pygame.draw.ellipse(surface, (*accent, max(48, alpha // 3)), shadow_rect)
        if faction == "blackwire_directorate":
            torso = [(rect.centerx, rect.y + 8), (rect.right - 14, rect.y + 58), (rect.centerx + 16, rect.bottom - 8), (rect.x + 12, rect.y + 66)]
            pygame.draw.polygon(surface, body_color, torso)
            pygame.draw.polygon(surface, outline, torso, 3)
            visor = pygame.Rect(rect.centerx - 18, rect.y + 18, 36, 10)
            pygame.draw.rect(surface, panel, visor, border_radius=4)
            pygame.draw.rect(surface, outline, visor, 2, border_radius=4)
            pygame.draw.rect(surface, panel, pygame.Rect(rect.right - 16, rect.y + 34, 12, 12), border_radius=3)
        elif faction == "helix_ward":
            torso = [(rect.centerx - 8, rect.y + 14), (rect.right - 8, rect.y + 60), (rect.centerx + 10, rect.bottom - 4), (rect.x + 12, rect.bottom - 18), (rect.x + 6, rect.y + 72)]
            pygame.draw.polygon(surface, body_color, torso)
            pygame.draw.polygon(surface, outline, torso, 3)
            pygame.draw.circle(surface, panel, (rect.right - 18, rect.y + 34), 9)
            pygame.draw.circle(surface, outline, (rect.right - 18, rect.y + 34), 9, 2)
            pygame.draw.line(surface, outline, (rect.x + 16, rect.y + 64), (rect.centerx + 18, rect.bottom - 26), 4)
        else:
            torso = [(rect.centerx - 12, rect.y + 10), (rect.right - 8, rect.y + 58), (rect.centerx + 10, rect.bottom - 8), (rect.x + 10, rect.bottom - 20), (rect.x + 2, rect.y + 64)]
            pygame.draw.polygon(surface, body_color, torso)
            pygame.draw.polygon(surface, outline, torso, 3)
            pygame.draw.line(surface, outline, (rect.right - 18, rect.y + 30), (rect.right + 4, rect.y + 6), 5)

        head_center = (rect.centerx, rect.y + 6)
        pygame.draw.circle(surface, body_color, head_center, 14)
        pygame.draw.circle(surface, outline, head_center, 14, 3)
        pygame.draw.line(surface, panel, (head_center[0] - 8, head_center[1] + 1), (head_center[0] + 8, head_center[1] + 1), 3)
        pygame.draw.line(surface, outline, (rect.centerx - 8, rect.bottom - 14), (rect.centerx - 18, rect.bottom + 8), 4)
        pygame.draw.line(surface, outline, (rect.centerx + 6, rect.bottom - 12), (rect.centerx + 18, rect.bottom + 8), 4)

    def _draw_ground_plate(self, surface: Any, *, foot: tuple[int, int], accent: tuple[int, int, int], targeted: bool, dimmed: bool = False) -> None:
        width = 118 if not targeted else 130
        rect = pygame.Rect(int(foot[0] - width / 2), int(foot[1] - GROUND_RING_HEIGHT / 2), width, GROUND_RING_HEIGHT)
        ring_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        core_alpha = 54 if dimmed else 92
        pygame.draw.ellipse(ring_surface, (*accent, core_alpha), ring_surface.get_rect())
        outline_color = (255, 88, 88) if targeted else accent
        outline_alpha = 200 if targeted else (130 if not dimmed else 64)
        pygame.draw.ellipse(ring_surface, (*outline_color, outline_alpha), ring_surface.get_rect(), 3)
        surface.blit(ring_surface, rect.topleft)

    def _draw_meter(self, surface: Any, rect: Any, *, current: int, maximum: int, fill: tuple[int, int, int], background: tuple[int, int, int], border: tuple[int, int, int], label: str, label_font: Any) -> None:
        pygame.draw.rect(surface, background, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)
        fill_ratio = max(0.0, min(1.0, current / max(1, maximum)))
        inner_width = max(0, int((rect.width - 4) * fill_ratio))
        if inner_width > 0:
            fill_rect = pygame.Rect(rect.x + 2, rect.y + 2, inner_width, rect.height - 4)
            pygame.draw.rect(surface, fill, fill_rect, border_radius=6)
        label_surface = label_font.render(label, True, (244, 248, 255))
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_energy_row(self, surface: Any, *, rect: tuple[int, int, int, int], current: int, maximum: int) -> None:
        row_rect = pygame.Rect(*rect)
        self._draw_text(surface, "ENERGY", (row_rect.x, row_rect.y + 2), self._tiny_font, width=60)
        pip_x = row_rect.x + 66
        for index in range(maximum):
            pip_rect = pygame.Rect(pip_x + (index * 18), row_rect.y + 1, 14, 14)
            filled = index < current
            color = (104, 216, 255) if filled else (32, 54, 72)
            border = (182, 228, 255) if filled else (94, 112, 136)
            pygame.draw.ellipse(surface, color, pip_rect)
            pygame.draw.ellipse(surface, border, pip_rect, 2)

    def _draw_block_chip(self, surface: Any, *, rect: tuple[int, int, int, int], value: int, accent: tuple[int, int, int]) -> None:
        chip_rect = pygame.Rect(*rect)
        self._draw_panel(surface, chip_rect, fill=(12, 18, 28, 232), border=accent, radius=14)
        self._draw_shield_icon(surface, pygame.Rect(chip_rect.x + 8, chip_rect.y + 6, 18, 18), accent)
        self._draw_text(surface, str(value), (chip_rect.x + 30, chip_rect.y + 6), self._small_font, width=chip_rect.width - 34)

    def _draw_enemy_hp(self, surface: Any, actor: dict[str, Any]) -> None:
        rect = pygame.Rect(*actor["hp_bar_rect"])
        enemy = actor["enemy"]
        current = int(enemy["current_hp"])
        maximum = max(1, int(enemy["max_hp"]))
        self._draw_meter(surface, rect, current=current, maximum=maximum, fill=(232, 106, 112), background=(28, 16, 26), border=(248, 214, 218), label=f"{current}/{maximum}", label_font=self._tiny_font)

    def _draw_intent_banner(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool) -> None:
        intent = actor["enemy"].get("intent_display", {})
        rect = pygame.Rect(*actor["intent_rect"])
        border = (222, 236, 255) if high_contrast else actor["accent"]
        self._draw_panel(surface, rect, fill=(10, 18, 28, 236), border=border, radius=14)
        kind = intent.get("kind", "wait")
        cursor_x = rect.x + 8
        icon_rect = pygame.Rect(cursor_x, rect.y + 4, 18, 18)

        if kind in {"attack", "mixed"} and int(intent.get("hit_count", 0)) > 0:
            hit_count = int(intent.get("hit_count", 0))
            icon_count = min(3, hit_count)
            for index in range(icon_count):
                self._draw_sword_icon(surface, pygame.Rect(icon_rect.x + (index * 14), icon_rect.y, 16, 16), (255, 112, 112))
            cursor_x += 16 + ((icon_count - 1) * 14) + 6
            self._draw_text(surface, str(intent.get("damage_per_hit", 0)), (cursor_x, rect.y + 4), self._small_font)
            cursor_x += 24
            if hit_count > 1:
                self._draw_text(surface, f"x{hit_count}", (cursor_x, rect.y + 6), self._tiny_font)
                cursor_x += 22
        elif kind == "defend":
            self._draw_shield_icon(surface, icon_rect, (116, 198, 255))
            self._draw_text(surface, str(intent.get("block", 0)), (rect.x + 28, rect.y + 4), self._small_font)
            cursor_x = rect.x + 62
        elif kind == "summon":
            self._draw_summon_icon(surface, icon_rect, (202, 146, 255))
            self._draw_text(surface, str(intent.get("summon_count", 0)), (rect.x + 28, rect.y + 4), self._small_font)
            cursor_x = rect.x + 58
        elif kind == "buff":
            self._draw_buff_icon(surface, icon_rect, (106, 234, 170))
            cursor_x = rect.x + 28
        elif kind == "debuff":
            self._draw_debuff_icon(surface, icon_rect, (255, 156, 96))
            cursor_x = rect.x + 28
        else:
            self._draw_wait_icon(surface, icon_rect, (176, 190, 214))
            cursor_x = rect.x + 28

        chip_values: list[tuple[str, tuple[int, int, int], str]] = []
        if kind in {"attack", "mixed"} and int(intent.get("block", 0)) > 0:
            chip_values.append((str(intent["block"]), (116, 198, 255), "shield"))
        for label in intent.get("buffs", [])[:2]:
            chip_values.append((label[:3].upper(), (106, 234, 170), "buff"))
        for label in intent.get("debuffs", [])[:2]:
            chip_values.append((label[:3].upper(), (255, 156, 96), "debuff"))
        if kind == "mixed" and int(intent.get("summon_count", 0)) > 0:
            chip_values.append((f"+{intent['summon_count']}", (202, 146, 255), "summon"))
        chip_x = rect.right - 6
        for label, color, chip_kind in reversed(chip_values[:2]):
            width = 34 if len(label) <= 2 else 40
            chip_rect = pygame.Rect(chip_x - width, rect.y + 5, width, 18)
            pygame.draw.rect(surface, (18, 24, 36), chip_rect, border_radius=8)
            pygame.draw.rect(surface, color, chip_rect, 2, border_radius=8)
            glyph_rect = pygame.Rect(chip_rect.x + 4, chip_rect.y + 3, 12, 12)
            if chip_kind == "shield":
                self._draw_shield_icon(surface, glyph_rect, color)
            elif chip_kind == "buff":
                self._draw_buff_icon(surface, glyph_rect, color)
            elif chip_kind == "debuff":
                self._draw_debuff_icon(surface, glyph_rect, color)
            else:
                self._draw_summon_icon(surface, glyph_rect, color)
            self._draw_text(surface, label, (chip_rect.x + 18, chip_rect.y + 3), self._tiny_font, width=chip_rect.width - 20)
            chip_x = chip_rect.x - 6

    def _draw_hand(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        cards = list(layout["hand_cards"])
        cards.sort(key=lambda card: (card["index"] == self._hovered_card_index, card["index"]))
        for card in cards:
            if card["index"] == self._selected_card_index:
                continue
            scale = self._hand_card_scale(card["index"])
            center = card["center"]
            if card["index"] == self._hovered_card_index:
                center = (center[0], center[1] - CARD_HOVER_LIFT)
            self._draw_card_sprite(
                surface,
                card["card"],
                center=center,
                size=card["size"],
                angle=card["angle"],
                scale=scale,
                shortcut_label=str(card["index"] + 1),
                footer_label=card["footer_label"],
                note_label=None if card["playable"] else card["disabled_reason"],
                hovered=card["index"] == self._hovered_card_index,
                pressed=card["index"] == self._pressed_card_index,
                disabled=not card["playable"],
                selected=False,
                high_contrast=high_contrast,
                alpha=128 if layout["selected_card"] is not None else 255,
            )

    def _draw_selected_card(self, surface: Any, selected_card: dict[str, Any], *, high_contrast: bool) -> None:
        source = selected_card["source_card"]
        self._draw_card_sprite(
            surface,
            source["card"],
            center=selected_card["center"],
            size=(selected_card["center_rect"][2], selected_card["center_rect"][3]),
            angle=0.0,
            scale=1.0,
            shortcut_label=str(source["index"] + 1),
            footer_label=source["footer_label"],
            note_label=None if source["playable"] else source["disabled_reason"],
            hovered=False,
            pressed=False,
            disabled=not source["playable"],
            selected=True,
            high_contrast=high_contrast,
            alpha=255,
        )
        if selected_card["target_mode"] == "single_enemy" and selected_card["target_id"] is not None:
            caption = "Target locked. Click the highlighted enemy to confirm."
        elif selected_card["target_mode"] == "all_enemies":
            caption = "All enemies highlighted."
        elif selected_card["target_mode"] == "immediate_self":
            caption = "Self-target locked."
        else:
            caption = "Playing immediately."
        caption_rect = pygame.Rect(selected_card["center_rect"][0] - 8, selected_card["center_rect"][1] + selected_card["center_rect"][3] + 10, selected_card["center_rect"][2] + 16, 28)
        self._draw_panel(surface, caption_rect, fill=(10, 15, 24, 226), border=(88, 156, 228), radius=14)
        self._draw_text(surface, caption, (caption_rect.x + 12, caption_rect.y + 6), self._tiny_font, width=caption_rect.width - 24)

    def _draw_card_sprite(
        self,
        surface: Any,
        card: dict[str, Any],
        *,
        center: tuple[float, float],
        size: tuple[float, float],
        angle: float,
        scale: float,
        shortcut_label: str | None,
        footer_label: str | None,
        note_label: str | None,
        hovered: bool,
        pressed: bool,
        disabled: bool,
        selected: bool,
        high_contrast: bool,
        alpha: int,
    ) -> None:
        width = max(1, int(size[0] * scale))
        height = max(1, int(size[1] * scale))
        card_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        draw_card(
            card_surface,
            (0, 0, width, height),
            card,
            {"title": self._small_font, "body": self._tiny_font, "tiny": self._tiny_font},
            variant="full",
            shortcut_label=shortcut_label,
            footer_label=footer_label,
            note_label=note_label,
            selected=selected,
            hovered=hovered,
            pressed=pressed,
            disabled=disabled,
            high_contrast=high_contrast,
        )
        if alpha < 255:
            card_surface.set_alpha(alpha)
        rotated = pygame.transform.rotozoom(card_surface, angle, 1.0) if abs(angle) > 0.01 else card_surface
        surface.blit(rotated, rotated.get_rect(center=(int(center[0]), int(center[1]))))

    def _draw_target_guides(self, surface: Any, layout: dict[str, Any]) -> None:
        selected_card = layout["selected_card"]
        if selected_card is None:
            return
        if selected_card["target_mode"] == "single_enemy" and selected_card["target_id"] is not None:
            target_actor = next((enemy for enemy in layout["enemy_actors"] if enemy["id"] == selected_card["target_id"]), None)
            if target_actor is None:
                return
            start = (int(selected_card["center"][0] + 74), int(selected_card["center"][1] - 18))
            end = (target_actor["foot"][0] - 28, target_actor["foot"][1] - 12)
            self._draw_target_line(surface, start, end, (255, 88, 88))
        elif selected_card["target_mode"] == "all_enemies":
            for enemy_actor in layout["enemy_actors"]:
                soft_rect = pygame.Rect(int(enemy_actor["foot"][0] - 52), int(enemy_actor["foot"][1] - 6), 104, 12)
                soft_surface = pygame.Surface((soft_rect.width, soft_rect.height), pygame.SRCALPHA)
                pygame.draw.ellipse(soft_surface, (255, 98, 98, 110), soft_surface.get_rect(), 2)
                surface.blit(soft_surface, soft_rect.topleft)

    def _draw_target_line(self, surface: Any, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
        distance = max(1.0, math.hypot(end[0] - start[0], end[1] - start[1]))
        steps = max(8, int(distance / 14))
        for step in range(steps):
            t = step / max(1, steps - 1)
            if step % 2 == 1:
                continue
            seg_start = (_lerp(start[0], end[0], t), _lerp(start[1], end[1], t))
            seg_end = (_lerp(start[0], end[0], min(1.0, t + (0.6 / steps))), _lerp(start[1], end[1], min(1.0, t + (0.6 / steps))))
            pygame.draw.line(surface, color, seg_start, seg_end, 3)

    def _draw_status_row(self, surface: Any, regions: list[dict[str, Any]]) -> None:
        for region in regions:
            rect = pygame.Rect(*region["rect"])
            item = region["item"]
            panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(panel, (*item["color"], 44), panel.get_rect(), border_radius=10)
            pygame.draw.rect(panel, item["color"], panel.get_rect(), 2, border_radius=10)
            surface.blit(panel, rect.topleft)
            self._draw_text(surface, item["short"], (rect.x + 5, rect.y + 4), self._tiny_font, width=rect.width - 10)
            if item["show_count"]:
                count_label = self._tiny_font.render(str(item["count"]), True, (244, 248, 255))
                surface.blit(count_label, count_label.get_rect(bottomright=(rect.right - 4, rect.bottom - 3)))

    def _draw_helper_panel(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        rect = pygame.Rect(*layout["helper_panel_rect"])
        border = (220, 232, 255) if high_contrast else (92, 126, 170)
        self._draw_panel(surface, rect, fill=(8, 12, 20, 210), border=border, radius=16)
        player = layout["player"]
        self._draw_text(surface, layout["helper_summary"], (rect.x + 14, rect.y + 10), self._tiny_font, width=rect.width - 28)
        stats_line = f"Draw {player.get('draw_pile', 0)}  |  Discard {player.get('discard_pile', 0)}  |  Exhaust {player.get('exhaust_pile', 0)}"
        self._draw_text(surface, stats_line, (rect.x + 14, rect.y + 34), self._tiny_font, width=rect.width - 28)

    def _draw_end_turn_button(self, surface: Any, layout: dict[str, Any]) -> None:
        button_rect = pygame.Rect(*layout["end_turn_rect"])
        fill = (30, 58, 92) if layout["any_playable"] else (42, 78, 118)
        if layout["end_turn_hovered"]:
            fill = (48, 94, 148)
        if self._pressed_end_turn:
            fill = (255, 214, 110)
        border = (180, 198, 224) if not self._pressed_end_turn else (255, 214, 110)
        self._draw_panel(surface, button_rect, fill=fill, border=border, radius=16)
        label_color = (240, 245, 255) if not self._pressed_end_turn else (20, 28, 40)
        surface.blit(self._small_font.render("End Turn", True, label_color), self._small_font.render("End Turn", True, label_color).get_rect(center=button_rect.center))

    def _render_bark(self, surface: Any, bark: dict[str, Any], enemy_actors: list[dict[str, Any]]) -> None:
        speaker = next((enemy for enemy in enemy_actors if enemy["id"] == bark.get("speaker_id")), None)
        bubble_anchor = (974, 140) if speaker is None else (speaker["actor_rect"].centerx, speaker["actor_rect"].top - 10)
        text = bark.get("text", "")
        width = min(340, max(180, self._small_font.size(text)[0] + 34))
        bubble_rect = pygame.Rect(0, 0, width, 54 if bark.get("is_boss") else 48)
        bubble_rect.midbottom = bubble_anchor
        bubble_rect.x = max(24, min(surface.get_width() - bubble_rect.width - 24, bubble_rect.x))
        bubble_rect.y = max(76, bubble_rect.y)
        fill = (24, 30, 42, 232) if not bark.get("is_boss") else (38, 24, 46, 234)
        outline = (188, 208, 232) if not bark.get("is_boss") else (214, 156, 255)
        self._draw_panel(surface, bubble_rect, fill=fill, border=outline, radius=16)
        self._draw_text(surface, text, (bubble_rect.x + 14, bubble_rect.y + 13), self._small_font, width=bubble_rect.width - 28)

    def _draw_tooltip(self, surface: Any, tooltip: dict[str, Any]) -> None:
        mouse_x, mouse_y = self._mouse_pos
        width = TOOLTIP_MAX_WIDTH
        title = tooltip.get("title", "")
        text = tooltip.get("text", "")
        line_count = max(1, len(self._wrap_lines(text, self._tiny_font, TOOLTIP_MAX_WIDTH - 24)))
        height = 18 + (18 if title else 0) + (line_count * 16) + 12
        rect = pygame.Rect(mouse_x + 14, mouse_y - height - 10, width, height)
        rect.x = min(surface.get_width() - rect.width - 16, max(16, rect.x))
        rect.y = min(surface.get_height() - rect.height - 16, max(76, rect.y))
        self._draw_panel(surface, rect, fill=(6, 10, 18, 236), border=(130, 170, 220), radius=14)
        cursor_y = rect.y + 10
        if title:
            self._draw_text(surface, title, (rect.x + 12, cursor_y), self._small_font, width=rect.width - 24)
            cursor_y += 18
        self._draw_text(surface, text, (rect.x + 12, cursor_y), self._tiny_font, width=rect.width - 24)

    def _draw_panel(self, surface: Any, rect: Any, *, fill: tuple[int, int, int] | tuple[int, int, int, int], border: tuple[int, int, int], radius: int) -> None:
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
        pygame.draw.rect(panel, border, panel.get_rect(), 2, border_radius=radius)
        surface.blit(panel, rect.topleft)

    def _draw_sword_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        blade = [(rect.x + 3, rect.bottom - 2), (rect.centerx, rect.y + 1), (rect.right - 3, rect.y + 5), (rect.centerx + 1, rect.bottom - 3)]
        pygame.draw.polygon(surface, color, blade)
        pygame.draw.line(surface, (246, 246, 252), (rect.centerx - 3, rect.y + 8), (rect.centerx + 3, rect.y + 3), 2)
        pygame.draw.line(surface, color, (rect.x + 4, rect.bottom - 3), (rect.right - 2, rect.bottom - 6), 2)

    def _draw_shield_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        points = [(rect.centerx, rect.y + 1), (rect.right - 3, rect.y + 5), (rect.right - 5, rect.bottom - 5), (rect.centerx, rect.bottom - 1), (rect.x + 4, rect.bottom - 5), (rect.x + 2, rect.y + 5)]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (246, 248, 255), points, 2)

    def _draw_buff_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        pygame.draw.circle(surface, color, rect.center, max(4, rect.width // 2 - 2))
        pygame.draw.line(surface, (248, 250, 255), (rect.centerx, rect.y + 3), (rect.centerx, rect.bottom - 3), 2)
        pygame.draw.line(surface, (248, 250, 255), (rect.x + 3, rect.centery), (rect.right - 3, rect.centery), 2)

    def _draw_debuff_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        pygame.draw.circle(surface, color, rect.center, max(4, rect.width // 2 - 2))
        pygame.draw.line(surface, (248, 250, 255), (rect.x + 3, rect.centery), (rect.right - 3, rect.centery), 2)

    def _draw_summon_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        center = rect.center
        points = [(center[0], rect.y + 1), (center[0] + 4, center[1] - 2), (rect.right - 1, center[1]), (center[0] + 4, center[1] + 3), (center[0], rect.bottom - 1), (center[0] - 4, center[1] + 3), (rect.x + 1, center[1]), (center[0] - 4, center[1] - 2)]
        pygame.draw.polygon(surface, color, points)

    def _draw_wait_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        pygame.draw.circle(surface, color, rect.center, max(4, rect.width // 2 - 2), 2)
        pygame.draw.circle(surface, color, rect.center, 2)

    def _intent_tooltip(self, enemy: dict[str, Any]) -> str:
        intent = enemy.get("intent_display", {})
        lines = [str(intent.get("tooltip", enemy.get("intent_summary", "Waiting")))]
        if int(intent.get("hit_count", 0)) > 1:
            lines.append(f"{intent['hit_count']} hits for {intent['damage_per_hit']} each ({intent['total_damage']} total).")
        elif int(intent.get("total_damage", 0)) > 0:
            lines.append(f"Attack damage: {intent['total_damage']}.")
        if int(intent.get("block", 0)) > 0:
            lines.append(f"Gains {intent['block']} Block.")
        for label in intent.get("buffs", []):
            lines.append(BUFF_LABELS.get(label, label))
        for label in intent.get("debuffs", []):
            lines.append(DEBUFF_LABELS.get(label, label))
        if int(intent.get("summon_count", 0)) > 0:
            lines.append(f"Summons {intent['summon_count']} support unit(s).")
        return " ".join(lines[:4])

    def _card_index_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> int | None:
        cards = sorted(layout["hand_cards"], key=lambda card: (card["index"] == self._hovered_card_index, card["index"]))
        for card in reversed(cards):
            if point_in_rect(position, card["hit_rect"]):
                return card["index"]
        return None

    def _enemy_id_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for enemy in layout["enemy_actors"]:
            actor_rect = enemy["actor_rect"].inflate(24, 28)
            if point_in_rect(position, (actor_rect.x, actor_rect.y, actor_rect.width, actor_rect.height)):
                return enemy["id"]
            if point_in_rect(position, enemy["intent_rect"]) or point_in_rect(position, enemy["hp_bar_rect"]):
                return enemy["id"]
        return None

    def _tooltip_at_position(self, regions: list[dict[str, Any]], position: tuple[int, int]) -> dict[str, Any] | None:
        for region in reversed(regions):
            if point_in_rect(position, region["rect"]):
                return {"title": region["title"], "text": region["text"]}
        return None

    def _animation_progress(self, started_at: int, duration_ms: int) -> float:
        if started_at <= 0:
            return 1.0
        return max(0.0, min(1.0, (self._now_ms() - started_at) / max(1, duration_ms)))

    def _wrap_lines(self, text: str, font: Any, width: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= width:
                current = candidate
                continue
            lines.append(current)
            current = word
        if current:
            lines.append(current)
        return lines

    def _draw_text(self, surface: Any, text: str, position: tuple[int, int], font: Any, width: int | None = None) -> None:
        draw_wrapped_text(surface, text, position, font, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return
        self._font_scale = scale
        self._font = pygame.font.SysFont("consolas", max(20, int(26 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(15, int(18 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(13 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        return pygame.transform.smoothscale(self._load_image(path), size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((255, 0, 140, 180))
        self._image_cache[cache_key] = image
        return image

    def _now_ms(self) -> int:
        return int(pygame.time.get_ticks()) if pygame is not None else 0


def simulate_combat_ui() -> dict[str, Any]:
    ui = CombatUI()
    return ui.build_layout(
        {
            "status_message": "Entered combat encounter.",
            "character": {"id": "enforcer", "name": "The Enforcer", "accent_color": [232, 88, 72]},
            "player": {
                "current_hp": 70,
                "max_hp": 70,
                "energy": 3,
                "max_energy": 3,
                "block": 5,
                "draw_pile": 3,
                "discard_pile": 1,
                "exhaust_pile": 0,
                "strength": 1,
                "weak": 0,
                "vulnerable": 0,
                "combat_statuses": {"marked": 2},
            },
            "turn_number": 1,
            "turn_owner": "player",
            "living_enemy_ids": ["enemy_basic_01"],
            "enemies": [
                {
                    "id": "enemy_basic_01",
                    "name": "Street Punk",
                    "faction_id": "legacy",
                    "tier": "normal",
                    "current_hp": 40,
                    "max_hp": 40,
                    "block": 0,
                    "strength": 0,
                    "weak": 0,
                    "vulnerable": 0,
                    "current_intent": "attack",
                    "intent_value": 6,
                    "intent_summary": "Attack for 6",
                    "intent_display": {"kind": "attack", "damage_per_hit": 6, "hit_count": 1, "total_damage": 6, "block": 0, "buffs": [], "debuffs": [], "summon_count": 0, "tooltip": "Attack for 6"},
                    "statuses": {"marked": 1},
                }
            ],
            "player_hand": [
                {"id": "strike_01", "name": "Strike", "cost": 1, "type": "attack", "effects": [{"type": "damage", "value": 6}]},
                {"id": "defend_01", "name": "Defend", "cost": 1, "type": "skill", "effects": [{"type": "block", "value": 5}]},
            ],
            "event_log": [{"card_id": "strike_01", "summary": "Strike: damage 6 -> enemy_basic_01", "resolutions": [{"type": "damage", "applied": 6, "target": "enemy_basic_01"}]}],
            "presentation": {"ui_scale": 1.0, "high_contrast": False, "fast_mode": False},
        }
    )
