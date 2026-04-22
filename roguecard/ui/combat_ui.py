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
    PROJECT_ROOT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    resolve_asset_path,
)
from ui.card_renderer import card_summary_lines, draw_card
from ui.card_style import CARD_PORTRAIT_HEIGHT_RATIO
from ui.relic_assets import relic_assets
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.status_icon_assets import status_icon_assets

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
COMBAT_STATUS_ICON_SIZE = 20
COMBAT_STATUS_COUNT_GAP = 2
COMBAT_STATUS_ITEM_GAP = 6
COMBAT_STATUS_LIMIT = 6

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

STATUS_LABELS = {
    "strength": "Strength",
    "weak": "Weak",
    "vulnerable": "Vulnerable",
    "infect": "Infection",
    "burn": "Burn",
    "bleed": "Bleed",
    "marked": "Marked",
    "suppressed": "Suppressed",
    "nullified": "Nullified",
    "fortified": "Fortified",
    "regenerate": "Regenerate",
    "momentum": "Momentum",
    "overheat": "Overheat",
    "biomass": "Biomass",
    "mutated": "Mutated",
}

STATUS_DISPLAY_ORDER = (
    "strength",
    "fortified",
    "regenerate",
    "momentum",
    "biomass",
    "overheat",
    "weak",
    "vulnerable",
    "infect",
    "burn",
    "bleed",
    "marked",
    "suppressed",
    "nullified",
    "mutated",
)

PRIMARY_STATUS_KEYS = ("strength", "weak", "vulnerable")
SINGLE_STACK_DISPLAY_STATUSES = {"nullified", "mutated"}
INFECT_PREVIEW_FILL = (98, 220, 146)

STATUS_TOOLTIP_TEMPLATES = {
    "strength": "Attacks deal +{count} damage.",
    "weak": "Attack damage is reduced by 25% while active.",
    "vulnerable": "Attack damage taken is increased by 50% while active.",
    "infect": "This unit loses {count} HP on its next infect tick.",
    "burn": "This unit loses {count} HP at turn end. Burn then drops by 1.",
    "bleed": "The next hit deals +{count} damage, then Bleed drops by 1.",
    "marked": "Blackwire hits gain +{bonus} damage, then consume 1.",
    "suppressed": "Attack damage is reduced by about {percent}% while active.",
    "nullified": "Blocks the next positive combat gain.",
    "fortified": "Gains {count} Block at turn start.",
    "regenerate": "Heals {count} HP at turn start, then Regenerate drops by 1.",
    "momentum": "The next attack gains +{count} damage.",
    "overheat": "Stored heat resource: {count}.",
    "biomass": "Stored biomass resource: {count}.",
    "mutated": "Mutation is active.",
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
    "Burn Card": "Adds a Burn Card to the player's discard pile.",
    "Glitch Card": "Adds a Glitch Card to the player's discard pile.",
    "Junk Card": "Adds a Junk Card to the player's discard pile.",
    "Lag Card": "Adds a Lag Card to the player's discard pile.",
    "Strip Buff": "Removes player buffs.",
    "Burst": "Triggers infection burst damage.",
    "Steal Block": "Removes player block.",
    "Detonate": "Self-destructs after acting.",
}

ARTS_ROOT = PROJECT_ROOT / "arts"
DEFAULT_COMBAT_BACKGROUND_PATH = resolve_asset_path("ui", "bg_combat.png")
COMBAT_BACKGROUND_PATHS = {
    "outskirts": ARTS_ROOT / "map_1_combat.png",
    "city_streets": ARTS_ROOT / "map_2_combat.png",
    "blackwire_lockdown_sector": ARTS_ROOT / "map_3_blackwire.png",
    "cinder_jackals_edgeworks": ARTS_ROOT / "map_3_cinderjackal.png",
    "helix_ward_depths": ARTS_ROOT / "map_3_helixware.png",
}
COMBAT_BACKGROUND_FACTION_PATHS = {
    "blackwire_directorate": ARTS_ROOT / "map_3_blackwire.png",
    "cinder_jackals": ARTS_ROOT / "map_3_cinderjackal.png",
    "helix_ward": ARTS_ROOT / "map_3_helixware.png",
}
ENEMY_SPRITE_SCALE = 0.48
ENEMY_ACTION_HOLD_MS = 180
ENEMY_ACTION_RECOVER_MS = 100
ENEMY_ACTION_GAP_MS = 60
ENEMY_HIT_REACTION_HOLD_MS = 90
ENEMY_HIT_REACTION_RETURN_MS = 110
ENEMY_MELEE_LUNGE_PX = 16.0
ENEMY_RANGED_LEAN_PX = 6.0
ENEMY_HIT_RECOIL_PX = 12.0

def _enemy_sprite_definition(*move_ids: str) -> dict[str, Any]:
    return {
        "poses": {
            "idle": "idle.png",
            "damage": "damage.png",
            "dead": "dead.png",
        },
        "moves": {move_id: f"{move_id}.png" for move_id in move_ids},
    }


ENEMY_SPRITE_METADATA = {
    "audit_hound": _enemy_sprite_definition("trace_bite", "ledger_sweep", "compliance_leap"),
    "compliance_engine_ax9": _enemy_sprite_definition(
        "barrier_cycle",
        "pacify_burst",
        "deploy_node",
        "null_wave",
        "overdrive_cannon",
    ),
    "dune_raider": _enemy_sprite_definition("shiv", "sand_throw"),
    "dust_saboteur": _enemy_sprite_definition("scrap_dump", "cut_wire", "duck_cover"),
    "embersnout": _enemy_sprite_definition("cinder_spit", "flare_hide", "fire_up"),
    "relay_vulture": _enemy_sprite_definition("sightline", "dive_fire", "peck"),
    "salvage_bulwark": _enemy_sprite_definition("brace_plate", "ram"),
    "sandpack_alpha": _enemy_sprite_definition("call_hound", "feral_focus", "rake", "alpha_maul", "blood_surge"),
    "scrap_ticker": _enemy_sprite_definition("target_ping", "buzz_saw"),
    "signal_junker": _enemy_sprite_definition("dead_channel", "lag_spike", "paint_lock"),
    "waste_leech": _enemy_sprite_definition("sip", "coil", "gorge"),
    "wastes_colossus": _enemy_sprite_definition(
        "sand_plating",
        "searchlight",
        "grinding_tread",
        "flare_vent",
        "loose_tickers",
    ),
}
ENEMY_MELEE_MOVES = {
    "shiv",
    "cut_wire",
    "trace_bite",
    "compliance_leap",
    "peck",
    "ram",
    "rake",
    "alpha_maul",
    "buzz_saw",
    "blood_surge",
    "sip",
    "gorge",
    "grinding_tread",
}
ENEMY_RANGED_MOVES = {
    "sand_throw",
    "scrap_dump",
    "cinder_spit",
    "brace_plate",
    "duck_cover",
    "flare_hide",
    "fire_up",
    "ledger_sweep",
    "target_ping",
    "sightline",
    "dive_fire",
    "dead_channel",
    "lag_spike",
    "paint_lock",
    "barrier_cycle",
    "pacify_burst",
    "deploy_node",
    "null_wave",
    "overdrive_cannon",
    "call_hound",
    "feral_focus",
    "coil",
    "sand_plating",
    "searchlight",
    "flare_vent",
    "loose_tickers",
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
        self._enemy_sprite_cache: dict[str, dict[str, Any]] = {}
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
        self._enemy_visual_state: dict[str, dict[str, Any]] = {}
        self._enemy_action_clip: dict[str, Any] | None = None
        self._resolved_enemy_phase_tokens: set[tuple[Any, ...]] = set()
        self._enemy_phase_queue_signature: tuple[str, ...] | None = None
        self._enemy_phase_gap_until = 0

    def preload_assets(self) -> None:
        if pygame is None:
            return
        for path in [DEFAULT_COMBAT_BACKGROUND_PATH, *COMBAT_BACKGROUND_PATHS.values()]:
            self._load_image(path)

    def poll_action(self, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        self._advance_enemy_phase_animation(combat_state)
        enemy_phase_action = self._poll_enemy_phase_action(combat_state)
        if enemy_phase_action is not None:
            return enemy_phase_action
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
        if pygame is not None:
            self._ensure_fonts(presentation.get("ui_scale", 1.0))
        hand = combat_state.get("player_hand", [])
        player = combat_state["player"]
        character = combat_state.get("character") or {}
        enemies = combat_state["enemies"]
        living_enemy_ids = list(combat_state.get("living_enemy_ids", []))
        self._sync_enemy_visual_registry(enemies)
        self._advance_enemy_phase_animation(combat_state)

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
        for enemy_actor in enemy_actors:
            enemy_actor.update(self._enemy_actor_animation_state(enemy_actor))
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
            "enemy_phase": combat_state.get("enemy_phase", {}),
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

    def _card_footer_label(self, card: dict[str, Any], target_mode: str) -> str | None:
        del card
        del target_mode
        return None

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
        combat_statuses = player.get("combat_statuses", {})
        infect_value = combat_statuses.get("infect", 0) if isinstance(combat_statuses, dict) else 0
        infect_preview = self._infect_preview(player.get("current_hp", 0), infect_value)
        return {
            "character_id": character.get("id", player.get("character_id", "runner")),
            "name": character.get("name", "Runner"),
            "accent": accent,
            "foot": PLAYER_FOOT,
            "actor_rect": actor_rect,
            "hud_rect": (46, 452, 286, 58),
            "status_origin": (56, 515),
            "player": player,
            "infect_preview_damage": infect_preview["damage"],
            "infect_preview_lethal": infect_preview["lethal"],
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
            enemy_ref = str(enemy.get("enemy_ref") or f"{enemy['id']}#{index}")
            width = int(92 * scale)
            height = int(146 * scale)
            top_y = int(foot_y - height)
            rect = pygame.Rect(int(foot_x - width / 2), top_y, width, height) if pygame is not None else None
            accent = FACTION_COLORS.get(str(enemy.get("faction_id", "legacy")), FACTION_COLORS["legacy"])
            raw_statuses = enemy.get("statuses", {})
            infect_value = raw_statuses.get("infect", 0) if isinstance(raw_statuses, dict) else 0
            infect_preview = self._infect_preview(enemy.get("current_hp", 0), infect_value)
            actors.append(
                {
                    "enemy": enemy,
                    "id": enemy["id"],
                    "enemy_ref": enemy_ref,
                    "name": enemy["name"],
                    "foot": (foot_x, foot_y),
                    "slot_scale": scale,
                    "actor_rect": rect,
                    "accent": accent,
                    "hp_bar_rect": (int(foot_x - 62), int(foot_y + 14), 124, 12),
                    "block_rect": (int(foot_x + 70), int(foot_y + 4), 42, 26),
                    "intent_rect": (int(foot_x - 68), int(top_y - 40), 136, 28),
                    "status_origin": (int(foot_x), int(foot_y + 34)),
                    "targeted": enemy["id"] == (selected_card["target_id"] if selected_card is not None else None),
                    "valid_target": enemy["id"] in valid_target_ids if selected_card is not None else True,
                    "dimmed": selected_card is not None and selected_card["target_mode"] in {"single_enemy", "all_enemies"} and enemy["id"] not in valid_target_ids,
                    "infect_preview_damage": infect_preview["damage"],
                    "infect_preview_lethal": infect_preview["lethal"],
                }
            )
        return actors

    def _status_items_for_player(self, player: dict[str, Any]) -> list[dict[str, Any]]:
        status_values: dict[str, int] = {}
        for status_id in PRIMARY_STATUS_KEYS:
            count = self._status_count(player.get(status_id, 0))
            if count > 0:
                status_values[status_id] = count

        combat_statuses = player.get("combat_statuses", {})
        if isinstance(combat_statuses, dict):
            for status_id in STATUS_DISPLAY_ORDER:
                if status_id in PRIMARY_STATUS_KEYS:
                    continue
                count = self._status_count(combat_statuses.get(status_id, 0))
                if count > 0:
                    status_values[status_id] = count

        return self._ordered_status_items(status_values)

    def _status_items_for_enemy(self, enemy: dict[str, Any]) -> list[dict[str, Any]]:
        status_values: dict[str, int] = {}
        for status_id in PRIMARY_STATUS_KEYS:
            count = self._status_count(enemy.get(status_id, 0))
            if count > 0:
                status_values[status_id] = count

        raw_statuses = enemy.get("statuses", {})
        if isinstance(raw_statuses, dict):
            for status_id in STATUS_DISPLAY_ORDER:
                if status_id in PRIMARY_STATUS_KEYS:
                    continue
                count = self._status_count(raw_statuses.get(status_id, 0))
                if count > 0:
                    status_values[status_id] = count

        return self._ordered_status_items(status_values)

    def _ordered_status_items(self, status_values: dict[str, int]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for status_id in STATUS_DISPLAY_ORDER:
            count = int(status_values.get(status_id, 0) or 0)
            if count > 0:
                items.append(self._status_item(status_id, count))
        return items[:COMBAT_STATUS_LIMIT]

    def _status_item(self, status_id: str, value: int) -> dict[str, Any]:
        label = STATUS_LABELS.get(status_id, status_id.replace("_", " ").title())
        count = max(1, int(value))
        if status_id in SINGLE_STACK_DISPLAY_STATUSES:
            count = 1
        return {"id": status_id, "icon_id": status_id, "label": label, "count": count}

    def _status_count(self, raw_value: Any) -> int:
        if isinstance(raw_value, bool):
            return 1 if raw_value else 0
        try:
            value = int(raw_value or 0)
        except (TypeError, ValueError):
            return 0
        return max(0, value)

    def _infect_preview(self, current_hp: Any, infect_value: Any) -> dict[str, Any]:
        try:
            hp = max(0, int(current_hp or 0))
        except (TypeError, ValueError):
            hp = 0
        infect = self._status_count(infect_value)
        preview_damage = min(hp, infect)
        return {
            "damage": preview_damage,
            "lethal": hp > 0 and infect >= hp,
        }

    def _status_tooltip_text(self, item: dict[str, Any]) -> str:
        status_id = str(item.get("id", "")).strip().lower()
        count = max(1, int(item.get("count", 1) or 1))
        template = STATUS_TOOLTIP_TEMPLATES.get(status_id)
        if template is None:
            return f"{item.get('label', 'Status')} is active."
        return template.format(
            count=count,
            bonus=count * 2,
            percent=count * 15,
        )

    def _status_regions(self, status_items: list[dict[str, Any]], origin: tuple[int, int], *, anchor: str) -> list[dict[str, Any]]:
        if not status_items:
            return []
        scale = self._font_scale or 1.0
        icon_size = max(16, int(COMBAT_STATUS_ICON_SIZE * scale))
        count_gap = max(2, int(COMBAT_STATUS_COUNT_GAP * scale))
        item_gap = max(4, int(COMBAT_STATUS_ITEM_GAP * scale))
        region_specs: list[dict[str, Any]] = []
        total_width = 0
        for item in status_items:
            count_label = str(item["count"])
            if self._tiny_font is None:
                count_width = max(8, len(count_label) * 7)
            else:
                count_width = self._tiny_font.size(count_label)[0]
            width = icon_size + count_gap + count_width
            region_specs.append(
                {
                    "item": item,
                    "count_label": count_label,
                    "width": width,
                    "icon_size": icon_size,
                    "count_gap": count_gap,
                }
            )
            total_width += width
        total_width += max(0, len(region_specs) - 1) * item_gap
        start_x = origin[0] - (total_width // 2) if anchor == "center" else origin[0]
        regions = []
        cursor_x = start_x
        for spec in region_specs:
            item = spec["item"]
            rect = (cursor_x, origin[1], spec["width"], spec["icon_size"])
            regions.append(
                {
                    "rect": rect,
                    "title": item["label"],
                    "text": self._status_tooltip_text(item),
                    "item": item,
                    "count_label": spec["count_label"],
                    "icon_size": spec["icon_size"],
                    "count_gap": spec["count_gap"],
                }
            )
            cursor_x += spec["width"] + item_gap
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
            return self._build_recent_summary(event_log)
        hovered = next((card for card in hand_cards if card["index"] == self._hovered_card_index), None)
        if hovered is not None:
            return hovered["summary"] or hovered["footer_label"]
        return self._build_recent_summary(event_log)

    def render(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        presentation = combat_state.get("presentation", {})
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(combat_state)
        self.render_background(surface, combat_state)
        self.render_foreground(surface, combat_state, layout=layout)

    def render_background(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        background = self._scaled_image(self._combat_background_path(combat_state), surface.get_size())
        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=124, color=(8, 8, 16))
        self._draw_stage_gradient(surface)

    def render_foreground(
        self,
        surface: Any,
        combat_state: dict[str, Any],
        *,
        layout: dict[str, Any] | None = None,
    ) -> None:
        if pygame is None or surface is None:
            return
        presentation = combat_state.get("presentation", {})
        high_contrast = presentation.get("high_contrast", False)
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(combat_state) if layout is None else layout
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
        width = surface.get_width()
        height = surface.get_height()
        for row in range(height):
            progress = row / max(1, height - 1)
            shadow_alpha = int(_lerp(6, 38, progress))
            glow_alpha = int(_lerp(42, 10, progress))
            pygame.draw.line(overlay, (16, 12, 24, shadow_alpha), (0, row), (width, row))
            pygame.draw.line(overlay, (74, 92, 118, glow_alpha), (0, row), (width, row))

        ambient_rect = pygame.Rect(0, 0, int(width * 0.84), int(height * 0.62))
        ambient_rect.center = (width // 2, int(height * 0.38))
        pygame.draw.ellipse(overlay, (132, 150, 182, 28), ambient_rect)
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
        self._draw_meter(
            surface,
            hp_bar_rect,
            current=int(player["current_hp"]),
            maximum=max(1, int(player["max_hp"])),
            fill=(232, 106, 112),
            background=(36, 18, 28),
            border=(252, 210, 214),
            label=f"HP {player['current_hp']}/{player['max_hp']}",
            label_font=self._tiny_font,
            preview_loss=int(actor.get("infect_preview_damage", 0) or 0),
            preview_fill=INFECT_PREVIEW_FILL,
            show_skull=bool(actor.get("infect_preview_lethal", False)),
        )
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

        body_offset = actor.get("body_offset", (0, 0))
        body_x = int(rect.x - 12 + body_offset[0])
        body_y = int(rect.y - 12 + body_offset[1])
        if actor.get("use_sprite"):
            self._draw_enemy_sprite(surface, actor, alpha=96 if actor["dimmed"] else 255)
        else:
            body_surface = pygame.Surface((rect.width + 24, rect.height + 24), pygame.SRCALPHA)
            self._draw_enemy_standee_body(
                body_surface,
                body_surface.get_rect().inflate(-24, -24).move(12, 12),
                enemy=enemy,
                accent=accent,
                alpha=96 if actor["dimmed"] else 255,
            )
            surface.blit(body_surface, (body_x, body_y))

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

    def apply_snapshot_feedback(
        self,
        action_type: str,
        before_combat: dict[str, Any] | None,
        after_combat: dict[str, Any] | None,
    ) -> None:
        del action_type
        if after_combat is None:
            self._enemy_action_clip = None
            self._enemy_visual_state.clear()
            self._resolved_enemy_phase_tokens.clear()
            self._enemy_phase_queue_signature = None
            self._enemy_phase_gap_until = 0
            return

        enemies = list(after_combat.get("enemies", []))
        self._sync_enemy_visual_registry(enemies)
        if before_combat is None:
            return

        before_lookup = {
            self._enemy_ref_from_snapshot(enemy, index): enemy
            for index, enemy in enumerate(before_combat.get("enemies", []))
        }
        now = self._now_ms()
        for index, enemy in enumerate(enemies):
            enemy_ref = self._enemy_ref_from_snapshot(enemy, index)
            state = self._ensure_enemy_visual_state(enemy_ref)
            current_hp = self._enemy_hp(enemy)
            state["is_dead_pose"] = current_hp <= 0
            before_enemy = before_lookup.get(enemy_ref)
            if before_enemy is None:
                continue
            if current_hp < self._enemy_hp(before_enemy):
                state["pending_hit_reaction"] = {
                    "started_at": now,
                    "lethal": current_hp <= 0,
                }
                if current_hp <= 0 and self._enemy_action_clip is not None and self._enemy_action_clip.get("enemy_ref") == enemy_ref:
                    self._enemy_action_clip = None

    def _enemy_ref_from_snapshot(self, enemy: dict[str, Any], index: int) -> str:
        return str(enemy.get("enemy_ref") or f"{enemy.get('id', 'enemy')}#{index}")

    def _enemy_hp(self, enemy: dict[str, Any]) -> int:
        try:
            return max(0, int(enemy.get("current_hp", 0) or 0))
        except (TypeError, ValueError):
            return 0

    def _new_enemy_visual_state(self) -> dict[str, Any]:
        return {
            "current_clip": None,
            "clip_time": 0,
            "base_offset": (0.0, 0.0),
            "render_offset": (0.0, 0.0),
            "pending_hit_reaction": None,
            "is_dead_pose": False,
        }

    def _ensure_enemy_visual_state(self, enemy_ref: str) -> dict[str, Any]:
        state = self._enemy_visual_state.get(enemy_ref)
        if state is None:
            state = self._new_enemy_visual_state()
            self._enemy_visual_state[enemy_ref] = state
        return state

    def _sync_enemy_visual_registry(self, enemies: list[dict[str, Any]]) -> None:
        active_refs: set[str] = set()
        for index, enemy in enumerate(enemies):
            enemy_ref = self._enemy_ref_from_snapshot(enemy, index)
            active_refs.add(enemy_ref)
            state = self._ensure_enemy_visual_state(enemy_ref)
            state["is_dead_pose"] = self._enemy_hp(enemy) <= 0
        for enemy_ref in list(self._enemy_visual_state):
            if enemy_ref not in active_refs:
                self._enemy_visual_state.pop(enemy_ref, None)
        if not enemies:
            self._enemy_action_clip = None
            self._resolved_enemy_phase_tokens.clear()
            self._enemy_phase_queue_signature = None
            self._enemy_phase_gap_until = 0

    def _advance_enemy_phase_animation(self, combat_state: dict[str, Any]) -> None:
        descriptor = self._active_enemy_phase_descriptor(combat_state)
        now = self._now_ms()

        if descriptor is None:
            self._enemy_action_clip = None
            self._resolved_enemy_phase_tokens.clear()
            self._enemy_phase_queue_signature = None
            return

        queue_signature = descriptor["queue_signature"]
        if queue_signature != self._enemy_phase_queue_signature:
            self._enemy_phase_queue_signature = queue_signature
            self._resolved_enemy_phase_tokens.clear()

        if self._enemy_action_clip is not None:
            clip_elapsed = max(0, now - int(self._enemy_action_clip["started_at"]))
            state = self._ensure_enemy_visual_state(self._enemy_action_clip["enemy_ref"])
            state["current_clip"] = dict(self._enemy_action_clip)
            state["clip_time"] = clip_elapsed
            if clip_elapsed >= int(self._enemy_action_clip["total_duration_ms"]):
                state["current_clip"] = None
                state["clip_time"] = 0
                self._enemy_action_clip = None
                self._enemy_phase_gap_until = now + self._enemy_animation_ms(ENEMY_ACTION_GAP_MS, combat_state)
            else:
                return

        if descriptor["token"] in self._resolved_enemy_phase_tokens:
            return
        if now < self._enemy_phase_gap_until or self._has_active_hit_reaction(now):
            return
        if descriptor["enemy"] is None or self._enemy_hp(descriptor["enemy"]) <= 0:
            return

        clip = self._build_enemy_action_clip(
            enemy=descriptor["enemy"],
            enemy_ref=descriptor["enemy_ref"],
            token=descriptor["token"],
            combat_state=combat_state,
        )
        self._enemy_action_clip = clip
        state = self._ensure_enemy_visual_state(descriptor["enemy_ref"])
        state["current_clip"] = dict(clip)
        state["clip_time"] = 0

    def _poll_enemy_phase_action(self, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        descriptor = self._active_enemy_phase_descriptor(combat_state)
        if descriptor is None:
            return None

        token = descriptor["token"]
        if descriptor["enemy"] is None or self._enemy_hp(descriptor["enemy"]) <= 0:
            if token in self._resolved_enemy_phase_tokens:
                return None
            self._resolved_enemy_phase_tokens.add(token)
            return {"type": "resolve_enemy_phase_step"}

        if self._enemy_action_clip is None or self._enemy_action_clip.get("token") != token:
            return None
        if self._enemy_action_clip.get("committed", False):
            return None
        if self._now_ms() < int(self._enemy_action_clip["commit_at"]):
            return None

        self._enemy_action_clip["committed"] = True
        self._resolved_enemy_phase_tokens.add(token)
        return {"type": "resolve_enemy_phase_step"}

    def _active_enemy_phase_descriptor(self, combat_state: dict[str, Any]) -> dict[str, Any] | None:
        if combat_state.get("turn_owner") != "enemy":
            return None
        enemy_phase = combat_state.get("enemy_phase", {})
        if not isinstance(enemy_phase, dict) or not enemy_phase.get("active"):
            return None
        pending_enemy_ids = tuple(
            enemy_ref
            for enemy_ref in enemy_phase.get("pending_enemy_ids", [])
            if isinstance(enemy_ref, str) and enemy_ref
        )
        if not pending_enemy_ids:
            return None
        current_index = enemy_phase.get("current_index", 0)
        if not isinstance(current_index, int) or not (0 <= current_index < len(pending_enemy_ids)):
            return None
        enemy_ref = pending_enemy_ids[current_index]
        enemy = next(
            (
                entry
                for index, entry in enumerate(combat_state.get("enemies", []))
                if self._enemy_ref_from_snapshot(entry, index) == enemy_ref
            ),
            None,
        )
        intent_id = "" if enemy is None else str(enemy.get("current_intent") or "")
        return {
            "queue_signature": pending_enemy_ids,
            "token": (pending_enemy_ids, current_index, enemy_ref, intent_id),
            "enemy_ref": enemy_ref,
            "enemy": enemy,
            "intent_id": intent_id,
        }

    def _enemy_animation_ms(self, base_ms: int, combat_state: dict[str, Any]) -> int:
        fast_mode = bool(combat_state.get("presentation", {}).get("fast_mode", False))
        scale = 0.65 if fast_mode else 1.0
        return max(1, int(base_ms * scale))

    def _build_enemy_action_clip(
        self,
        *,
        enemy: dict[str, Any],
        enemy_ref: str,
        token: tuple[Any, ...],
        combat_state: dict[str, Any],
    ) -> dict[str, Any]:
        enemy_id = str(enemy.get("id", ""))
        intent_id = str(enemy.get("current_intent") or "")
        idle_frame = self._enemy_pose_frame(enemy_id, "idle")
        action_frame = self._enemy_move_frame(enemy_id, intent_id)
        hold_ms = self._enemy_animation_ms(ENEMY_ACTION_HOLD_MS, combat_state)
        recover_ms = self._enemy_animation_ms(ENEMY_ACTION_RECOVER_MS, combat_state)
        melee_lunge = ENEMY_MELEE_LUNGE_PX if intent_id in ENEMY_MELEE_MOVES else ENEMY_RANGED_LEAN_PX
        if intent_id not in ENEMY_MELEE_MOVES and intent_id not in ENEMY_RANGED_MOVES and str(enemy.get("intent_category", "")) == "attack":
            melee_lunge = ENEMY_MELEE_LUNGE_PX

        segments = [
            {"duration_ms": hold_ms, "frame": action_frame, "start_offset_x": 0.0, "end_offset_x": -melee_lunge},
            {"duration_ms": recover_ms, "frame": idle_frame, "start_offset_x": -melee_lunge, "end_offset_x": 0.0},
        ]
        commit_at = max(1, hold_ms // 2)

        total_duration_ms = sum(segment["duration_ms"] for segment in segments)
        now = self._now_ms()
        return {
            "enemy_ref": enemy_ref,
            "enemy_id": enemy_id,
            "token": token,
            "started_at": now,
            "commit_at": now + commit_at,
            "total_duration_ms": total_duration_ms,
            "segments": segments,
            "committed": False,
        }

    def _enemy_actor_animation_state(self, actor: dict[str, Any]) -> dict[str, Any]:
        enemy = actor["enemy"]
        enemy_ref = actor["enemy_ref"]
        enemy_id = str(enemy.get("id", ""))
        slot_scale = float(actor.get("slot_scale", 1.0) or 1.0)
        state = self._ensure_enemy_visual_state(enemy_ref)
        now = self._now_ms()
        sprite_frame = None
        offset = (0.0, 0.0)

        hit_pose = self._hit_reaction_pose(state, enemy_id, slot_scale, now)
        if hit_pose is not None:
            sprite_frame = hit_pose["frame"]
            offset = hit_pose["offset"]
        elif self._enemy_action_clip is not None and self._enemy_action_clip.get("enemy_ref") == enemy_ref:
            clip_pose = self._clip_pose(self._enemy_action_clip, slot_scale, now)
            sprite_frame = clip_pose["frame"]
            offset = clip_pose["offset"]

        state["render_offset"] = offset
        use_sprite = self._supports_enemy_sprite(enemy)
        if use_sprite and sprite_frame is None:
            pose_name = "dead" if state.get("is_dead_pose") or self._enemy_hp(enemy) <= 0 else "idle"
            sprite_frame = self._enemy_pose_frame(enemy_id, pose_name)
        return {
            "use_sprite": use_sprite,
            "sprite_frame": sprite_frame,
            "body_offset": (int(round(offset[0])), int(round(offset[1]))),
        }

    def _clip_pose(self, clip: dict[str, Any], slot_scale: float, now: int) -> dict[str, Any]:
        elapsed = max(0, now - int(clip["started_at"]))
        remaining = elapsed
        current_segment = clip["segments"][-1]
        local_elapsed = current_segment["duration_ms"]
        for segment in clip["segments"]:
            duration_ms = max(1, int(segment["duration_ms"]))
            if remaining <= duration_ms:
                current_segment = segment
                local_elapsed = remaining
                break
            remaining -= duration_ms
        duration_ms = max(1, int(current_segment["duration_ms"]))
        progress = max(0.0, min(1.0, local_elapsed / duration_ms))
        offset_x = _lerp(current_segment["start_offset_x"], current_segment["end_offset_x"], progress) * slot_scale
        return {
            "frame": current_segment.get("frame"),
            "offset": (offset_x, 0.0),
        }

    def _has_active_hit_reaction(self, now: int) -> bool:
        return any(self._hit_reaction_pose(state, "", 1.0, now) is not None for state in self._enemy_visual_state.values())

    def _hit_reaction_pose(
        self,
        state: dict[str, Any],
        enemy_id: str,
        slot_scale: float,
        now: int,
    ) -> dict[str, Any] | None:
        hit_reaction = state.get("pending_hit_reaction")
        if not isinstance(hit_reaction, dict):
            return None
        elapsed = max(0, now - int(hit_reaction.get("started_at", 0)))
        hold_ms = ENEMY_HIT_REACTION_HOLD_MS
        return_ms = ENEMY_HIT_REACTION_RETURN_MS
        total_ms = hold_ms if hit_reaction.get("lethal") else hold_ms + return_ms
        if elapsed >= total_ms:
            state["pending_hit_reaction"] = None
            return None

        recoil_px = ENEMY_HIT_RECOIL_PX * slot_scale
        if hit_reaction.get("lethal"):
            progress = max(0.0, min(1.0, elapsed / max(1, hold_ms)))
            return {
                "frame": self._enemy_pose_frame(enemy_id, "dead"),
                "offset": (recoil_px * progress, 0.0),
            }
        if elapsed <= hold_ms:
            progress = max(0.0, min(1.0, elapsed / max(1, hold_ms)))
            offset_x = recoil_px * progress
        else:
            progress = max(0.0, min(1.0, (elapsed - hold_ms) / max(1, return_ms)))
            offset_x = recoil_px * (1.0 - progress)
        return {
            "frame": self._enemy_pose_frame(enemy_id, "damage"),
            "offset": (offset_x, 0.0),
        }

    def _supports_enemy_sprite(self, enemy: dict[str, Any]) -> bool:
        return str(enemy.get("id", "")) in ENEMY_SPRITE_METADATA

    def _enemy_pose_frame(self, enemy_id: str, pose: str) -> str | None:
        sprite_metadata = ENEMY_SPRITE_METADATA.get(enemy_id)
        if sprite_metadata is None:
            return None
        pose_map = sprite_metadata.get("poses", {})
        if pose in pose_map:
            return pose
        return "idle" if "idle" in pose_map else None

    def _enemy_move_frame(self, enemy_id: str, move_id: str) -> str | None:
        sprite_metadata = ENEMY_SPRITE_METADATA.get(enemy_id)
        if sprite_metadata is None:
            return None
        move_map = sprite_metadata.get("moves", {})
        if move_id in move_map:
            return move_id
        return self._enemy_pose_frame(enemy_id, "idle")

    def _draw_enemy_sprite(self, surface: Any, actor: dict[str, Any], *, alpha: int) -> None:
        enemy_id = str(actor["enemy"].get("id", ""))
        frames = self._enemy_sprite_frames(enemy_id)
        frame_key = actor.get("sprite_frame")
        if not frames or frame_key is None or frame_key not in frames:
            body_surface = pygame.Surface((actor["actor_rect"].width + 24, actor["actor_rect"].height + 24), pygame.SRCALPHA)
            self._draw_enemy_standee_body(
                body_surface,
                body_surface.get_rect().inflate(-24, -24).move(12, 12),
                enemy=actor["enemy"],
                accent=actor["accent"],
                alpha=alpha,
            )
            body_offset = actor.get("body_offset", (0, 0))
            surface.blit(body_surface, (int(actor["actor_rect"].x - 12 + body_offset[0]), int(actor["actor_rect"].y - 12 + body_offset[1])))
            return

        sprite_surface = frames[frame_key]
        scale = ENEMY_SPRITE_SCALE * float(actor.get("slot_scale", 1.0) or 1.0)
        target_size = (
            max(1, int(sprite_surface.get_width() * scale)),
            max(1, int(sprite_surface.get_height() * scale)),
        )
        scaled_sprite = pygame.transform.smoothscale(sprite_surface, target_size)
        if alpha < 255:
            scaled_sprite = scaled_sprite.copy()
            scaled_sprite.set_alpha(alpha)
        body_offset = actor.get("body_offset", (0, 0))
        foot_x, foot_y = actor["foot"]
        sprite_rect = scaled_sprite.get_rect(
            midbottom=(int(foot_x + body_offset[0]), int(foot_y + body_offset[1] + 10))
        )
        surface.blit(scaled_sprite, sprite_rect.topleft)

    def _enemy_sprite_frames(self, enemy_id: str) -> dict[str, Any]:
        frames = self._enemy_sprite_cache.get(enemy_id)
        if frames is not None:
            return frames
        sprite_metadata = ENEMY_SPRITE_METADATA.get(enemy_id)
        if pygame is None or sprite_metadata is None:
            return {}

        frames = {}
        for frame_key, filename in sprite_metadata.get("poses", {}).items():
            frame_path = resolve_asset_path("enemies", enemy_id, filename)
            if frame_path.exists():
                frames[frame_key] = self._load_image(frame_path)
        for frame_key, filename in sprite_metadata.get("moves", {}).items():
            frame_path = resolve_asset_path("enemies", enemy_id, filename)
            if frame_path.exists():
                frames[frame_key] = self._load_image(frame_path)

        idle_surface = frames.get("idle")
        if idle_surface is not None:
            frames.setdefault("damage", idle_surface)
            frames.setdefault("dead", idle_surface)
        self._enemy_sprite_cache[enemy_id] = frames
        return frames

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

    def _draw_meter(
        self,
        surface: Any,
        rect: Any,
        *,
        current: int,
        maximum: int,
        fill: tuple[int, int, int],
        background: tuple[int, int, int],
        border: tuple[int, int, int],
        label: str,
        label_font: Any,
        preview_loss: int = 0,
        preview_fill: tuple[int, int, int] = INFECT_PREVIEW_FILL,
        show_skull: bool = False,
    ) -> None:
        pygame.draw.rect(surface, background, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)
        maximum = max(1, maximum)
        current = max(0, min(current, maximum))
        preview_loss = max(0, min(preview_loss, current))
        inner_rect = pygame.Rect(rect.x + 2, rect.y + 2, max(0, rect.width - 4), max(0, rect.height - 4))
        current_width = max(0, int(inner_rect.width * (current / maximum)))
        if current_width > 0 and inner_rect.width > 0 and inner_rect.height > 0:
            fill_surface = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
            fill_rect = pygame.Rect(0, 0, current_width, inner_rect.height)
            radius = max(2, inner_rect.height // 2)
            pygame.draw.rect(fill_surface, fill, fill_rect, border_radius=radius)
            if preview_loss > 0:
                safe_hp = max(0, current - preview_loss)
                preview_start = max(0, int(inner_rect.width * (safe_hp / maximum)))
                preview_surface = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
                preview_surface.set_clip(pygame.Rect(preview_start, 0, inner_rect.width - preview_start, inner_rect.height))
                pygame.draw.rect(preview_surface, preview_fill, fill_rect, border_radius=radius)
                fill_surface.blit(preview_surface, (0, 0))
            surface.blit(fill_surface, inner_rect.topleft)
        if show_skull:
            skull_size = max(12, rect.height + 2)
            skull_rect = pygame.Rect(rect.x - skull_size - 4, rect.centery - (skull_size // 2), skull_size, skull_size)
            self._draw_skull_icon(surface, skull_rect, (242, 246, 255))
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
        self._draw_meter(
            surface,
            rect,
            current=current,
            maximum=maximum,
            fill=(232, 106, 112),
            background=(28, 16, 26),
            border=(248, 214, 218),
            label=f"{current}/{maximum}",
            label_font=self._tiny_font,
            preview_loss=int(actor.get("infect_preview_damage", 0) or 0),
            preview_fill=INFECT_PREVIEW_FILL,
            show_skull=bool(actor.get("infect_preview_lethal", False)),
        )

    def _draw_intent_banner(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool) -> None:
        intent = actor["enemy"].get("intent_display", {})
        rect = pygame.Rect(*actor["intent_rect"])
        border = (222, 236, 255) if high_contrast else actor["accent"]
        self._draw_panel(surface, rect, fill=(10, 18, 28, 236), border=border, radius=14)
        kind = intent.get("kind", "wait")
        icon_rect = pygame.Rect(rect.x + 8, rect.y + 4, 18, 18)
        icon_effects = [
            effect
            for effect in intent.get("icon_effects", [])
            if isinstance(effect, dict) and str(effect.get("icon_id", "")).strip()
        ]
        primary_icon_effect = icon_effects[0] if kind == "debuff" and icon_effects else None

        if kind in {"attack", "mixed"} and int(intent.get("hit_count", 0)) > 0:
            hit_count = int(intent.get("hit_count", 0))
            icon_count = min(3, hit_count)
            for index in range(icon_count):
                self._draw_sword_icon(surface, pygame.Rect(icon_rect.x + (index * 14), icon_rect.y, 16, 16), (255, 112, 112))
            damage_x = rect.x + 30 + ((icon_count - 1) * 14)
            self._draw_text(surface, str(intent.get("damage_per_hit", 0)), (damage_x, rect.y + 4), self._small_font)
            if hit_count > 1:
                self._draw_text(surface, f"x{hit_count}", (damage_x + 24, rect.y + 6), self._tiny_font)
        elif kind == "defend":
            self._draw_shield_icon(surface, icon_rect, (116, 198, 255))
            self._draw_text(surface, str(intent.get("block", 0)), (rect.x + 28, rect.y + 4), self._small_font)
        elif kind == "summon":
            self._draw_summon_icon(surface, icon_rect, (202, 146, 255))
            self._draw_text(surface, str(intent.get("summon_count", 0)), (rect.x + 28, rect.y + 4), self._small_font)
        elif kind == "buff":
            self._draw_buff_icon(surface, icon_rect, (106, 234, 170))
        elif primary_icon_effect is not None:
            self._blit_status_icon(surface, str(primary_icon_effect["icon_id"]), icon_rect)
            self._draw_text(surface, str(primary_icon_effect.get("count", 1)), (rect.x + 28, rect.y + 4), self._small_font)
        elif kind == "debuff":
            self._draw_debuff_icon(surface, icon_rect, (255, 156, 96))
        else:
            self._draw_wait_icon(surface, icon_rect, (176, 190, 214))

        chip_entries: list[dict[str, Any]] = []
        icon_queue = icon_effects[1:] if primary_icon_effect is not None else icon_effects
        for icon_effect in icon_queue:
            chip_entries.append(
                {
                    "chip_type": "icon",
                    "icon_id": str(icon_effect.get("icon_id", "")),
                    "count": max(1, int(icon_effect.get("count", 1) or 1)),
                }
            )

        if kind in {"attack", "mixed"} and int(intent.get("block", 0)) > 0:
            chip_entries.append({"chip_type": "glyph", "label": str(intent["block"]), "color": (116, 198, 255), "glyph_kind": "shield"})
        for label in intent.get("buffs", [])[:2]:
            chip_entries.append({"chip_type": "glyph", "label": label[:3].upper(), "color": (106, 234, 170), "glyph_kind": "buff"})

        icon_labels = {str(effect.get("label", "")).strip() for effect in icon_effects if str(effect.get("label", "")).strip()}
        for label in intent.get("debuffs", []):
            if label in icon_labels:
                continue
            chip_entries.append({"chip_type": "glyph", "label": label[:3].upper(), "color": (255, 156, 96), "glyph_kind": "debuff"})

        if kind == "mixed" and int(intent.get("summon_count", 0)) > 0:
            chip_entries.append({"chip_type": "glyph", "label": f"+{intent['summon_count']}", "color": (202, 146, 255), "glyph_kind": "summon"})

        chip_x = rect.right - 6
        for chip in reversed(chip_entries[:2]):
            if chip["chip_type"] == "icon":
                chip_width = max(30, 20 + self._tiny_font.size(str(chip["count"]))[0])
                chip_rect = pygame.Rect(chip_x - chip_width, rect.y + 5, chip_width, 18)
                self._draw_intent_icon_chip(surface, chip_rect, str(chip["icon_id"]), int(chip["count"]))
            else:
                label = str(chip["label"])
                chip_width = 34 if len(label) <= 2 else 40
                chip_rect = pygame.Rect(chip_x - chip_width, rect.y + 5, chip_width, 18)
                self._draw_intent_glyph_chip(surface, chip_rect, label, chip["color"], str(chip["glyph_kind"]))
            chip_x = chip_rect.x - 6

    def _draw_intent_icon_chip(self, surface: Any, rect: Any, icon_id: str, count: int) -> None:
        chip_rect = pygame.Rect(rect)
        pygame.draw.rect(surface, (18, 24, 36), chip_rect, border_radius=8)
        pygame.draw.rect(surface, (162, 190, 226), chip_rect, 2, border_radius=8)
        icon_rect = pygame.Rect(chip_rect.x + 4, chip_rect.y + 3, 12, 12)
        self._blit_status_icon(surface, icon_id, icon_rect)
        self._draw_count_label(surface, str(max(1, count)), (chip_rect.x + 18, chip_rect.y + 3), font=self._tiny_font)

    def _draw_intent_glyph_chip(
        self,
        surface: Any,
        rect: Any,
        label: str,
        color: tuple[int, int, int],
        glyph_kind: str,
    ) -> None:
        chip_rect = pygame.Rect(rect)
        pygame.draw.rect(surface, (18, 24, 36), chip_rect, border_radius=8)
        pygame.draw.rect(surface, color, chip_rect, 2, border_radius=8)
        glyph_rect = pygame.Rect(chip_rect.x + 4, chip_rect.y + 3, 12, 12)
        if glyph_kind == "shield":
            self._draw_shield_icon(surface, glyph_rect, color)
        elif glyph_kind == "buff":
            self._draw_buff_icon(surface, glyph_rect, color)
        elif glyph_kind == "debuff":
            self._draw_debuff_icon(surface, glyph_rect, color)
        else:
            self._draw_summon_icon(surface, glyph_rect, color)
        self._draw_text(surface, label, (chip_rect.x + 18, chip_rect.y + 3), self._tiny_font, width=chip_rect.width - 20)

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

    def _blit_status_icon(self, surface: Any, icon_id: str, rect: Any) -> None:
        target_rect = pygame.Rect(rect)
        icon = status_icon_assets.get_icon(icon_id, target_rect.size)
        if icon is not None:
            icon_rect = icon.get_rect(center=target_rect.center)
            surface.blit(icon, icon_rect.topleft)
            return
        pygame.draw.circle(surface, (184, 198, 224), target_rect.center, max(4, target_rect.width // 2 - 1), 1)
        fallback = self._tiny_font.render(STATUS_LABELS.get(icon_id, "?")[:1], True, (240, 244, 255))
        surface.blit(fallback, fallback.get_rect(center=target_rect.center))

    def _draw_count_label(
        self,
        surface: Any,
        label: str,
        position: tuple[int, int],
        *,
        font: Any,
        color: tuple[int, int, int] = (240, 244, 255),
    ) -> None:
        shadow = font.render(label, True, (0, 0, 0))
        shadow.set_alpha(168)
        surface.blit(shadow, (position[0] + 1, position[1] + 1))
        surface.blit(font.render(label, True, color), position)

    def _draw_status_row(self, surface: Any, regions: list[dict[str, Any]]) -> None:
        for region in regions:
            rect = pygame.Rect(*region["rect"])
            item = region["item"]
            icon_size = int(region["icon_size"])
            icon_rect = pygame.Rect(rect.x, rect.y, icon_size, icon_size)
            self._blit_status_icon(surface, item["icon_id"], icon_rect)
            count_text = region["count_label"]
            count_width, count_height = self._tiny_font.size(count_text)
            count_x = icon_rect.right + int(region["count_gap"])
            count_y = rect.y + max(0, (rect.height - count_height) // 2) - 1
            self._draw_count_label(surface, count_text, (count_x, count_y), font=self._tiny_font)

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

    def _draw_skull_icon(self, surface: Any, rect: Any, color: tuple[int, int, int]) -> None:
        icon_rect = pygame.Rect(rect)
        skull_surface = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
        shadow_color = (0, 0, 0, 104)
        face_color = (*color, 255)
        cutout_color = (14, 18, 28, 255)
        jaw_top = max(1, icon_rect.height // 2)
        cranium = pygame.Rect(1, 0, max(4, icon_rect.width - 2), max(4, icon_rect.height - 5))
        jaw = pygame.Rect(3, jaw_top, max(4, icon_rect.width - 6), max(3, icon_rect.height - jaw_top))

        pygame.draw.ellipse(skull_surface, shadow_color, cranium.move(1, 1))
        pygame.draw.rect(skull_surface, shadow_color, jaw.move(1, 1), border_radius=3)
        pygame.draw.ellipse(skull_surface, face_color, cranium)
        pygame.draw.rect(skull_surface, face_color, jaw, border_radius=3)

        eye_radius = max(1, icon_rect.width // 8)
        eye_y = max(3, jaw_top - 2)
        left_eye = (max(3, icon_rect.centerx - eye_radius - 2), eye_y)
        right_eye = (min(icon_rect.width - 4, icon_rect.centerx + eye_radius + 1), eye_y)
        pygame.draw.circle(skull_surface, cutout_color, left_eye, eye_radius + 1)
        pygame.draw.circle(skull_surface, cutout_color, right_eye, eye_radius + 1)
        nose = [
            (icon_rect.centerx, jaw_top - 1),
            (icon_rect.centerx - 2, jaw_top + 3),
            (icon_rect.centerx + 2, jaw_top + 3),
        ]
        pygame.draw.polygon(skull_surface, cutout_color, nose)
        tooth_top = jaw_top + 2
        pygame.draw.line(skull_surface, cutout_color, (4, tooth_top), (icon_rect.width - 4, tooth_top), 1)
        pygame.draw.line(skull_surface, cutout_color, (icon_rect.centerx, tooth_top), (icon_rect.centerx, icon_rect.height - 3), 1)
        surface.blit(skull_surface, icon_rect.topleft)

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

    def _combat_background_path(self, combat_state: dict[str, Any]) -> Path:
        map_id = combat_state.get("map_id")
        if isinstance(map_id, str):
            background_path = COMBAT_BACKGROUND_PATHS.get(map_id)
            if background_path is not None and background_path.exists():
                return background_path
        branch_faction = combat_state.get("branch_faction")
        if isinstance(branch_faction, str):
            background_path = COMBAT_BACKGROUND_FACTION_PATHS.get(branch_faction)
            if background_path is not None and background_path.exists():
                return background_path
        return DEFAULT_COMBAT_BACKGROUND_PATH

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
                "combat_statuses": {"marked": 2, "infect": 3},
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
                    "statuses": {"marked": 1, "bleed": 2, "infect": 3},
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
