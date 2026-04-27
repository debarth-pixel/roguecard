from __future__ import annotations

import math
import logging
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    CARD_HOVER_LIFT,
    COMBAT_VISOR_OVERLAY_ALPHA,
    MAX_UI_SCALE,
    MIN_UI_SCALE,
    PROJECT_ROOT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    resolve_asset_path,
)
from ui.card_renderer import card_summary_lines, draw_card
from ui.card_style import CARD_PORTRAIT_HEIGHT_RATIO
from ui.combat_layout import CombatLayout, RectTuple, build_combat_layout
from ui.combat_ui_assets import combat_ui_assets
from ui.machine_hud import (
    CYAN,
    WARNING_ORANGE,
    YELLOW,
    draw_clipped_panel,
    draw_visor_overlay,
)
from ui.relic_assets import relic_assets
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect
from ui.status_icon_assets import status_icon_assets

LOGGER = logging.getLogger(__name__)

SELECT_ANIM_MS = 150
RESOLVE_ANIM_MS = 110
TOOLTIP_MAX_WIDTH = 260
HAND_CENTER_X = 532
HAND_CENTER_Y = 624
CARD_CENTER = (606, 302)
END_TURN_RECT = (1040, 636, 202, 56)
HELPER_PANEL_RECT = (836, 552, 406, 62)
TURN_HEADER_ORIGIN = (44, 70)
TURN_HEADER_LINE_WIDTH = 3
COMBAT_MODIFIER_ORIGIN = (44, 118)
COMBAT_MODIFIER_SLOT = 30
COMBAT_MODIFIER_GAP = 10
COMBAT_MODIFIER_LIMIT = 7
RELIC_RAIL_RECT = (250, 76, 818, 56)
RELIC_TRAY_ORIGIN = (274, 83)
RELIC_TRAY_SLOT = 42
RELIC_TRAY_GAP = 9
RELIC_TRAY_LIMIT = 15
TEMP_MODIFIER_SLOT = 28
TEMP_MODIFIER_GAP = 8
PROC_TICKER_ORIGIN = (44, 214)
PROC_TICKER_WIDTH = 296
DECK_STATS_ORIGIN = (44, 552)
DRAW_PILE_RECT = (48, 552, 82, 88)
DISCARD_PILE_RECT = (138, 552, 82, 88)
DRIFT_GAUGE_RECT = (18, 548, 24, 96)
EXHAUST_COUNTER_RECT = (858, 572, 92, 30)
FOREGROUND_PLATFORM_RECT = (244, 512, 700, 158)
GROUND_STRIP_RECT = (20, 384, 1240, 144)
DECK_STAT_WIDTH = 78
DECK_STAT_HEIGHT = 28
DECK_STAT_GAP = 10
CARD_FOCUS_LIFT = max(CARD_HOVER_LIFT, 40)
CARD_HOVER_SCALE = 1.1
CARD_DIMMED_ALPHA = 162
CARD_FOCUS_RECESS_PX = 12
RELIC_FLASH_TOTAL_MS = 360
RELIC_FLASH_RAMP_MS = 70
RELIC_FLASH_HOLD_MS = 140
RELIC_FLASH_STAGGER_MS = 80
FEEDBACK_NUMBER_MS = 760
SHIELD_FLASH_MS = 260
PROC_TICKER_MS = 1600
PLAYER_FOOT = (214, 466)
PLAYER_SCALE = 1.14
GROUND_RING_HEIGHT = 28
COMBAT_STATUS_ICON_SIZE = 24
COMBAT_STATUS_COUNT_GAP = 2
COMBAT_STATUS_ITEM_GAP = 6
COMBAT_STATUS_LIMIT = 7

ENEMY_SLOT_MAP = {
    1: [(1016, 464, 1.14)],
    2: [(936, 464, 1.06), (1096, 452, 1.0)],
    3: [(858, 466, 0.98), (1016, 444, 1.1), (1164, 464, 0.96)],
    4: [(818, 468, 0.96), (942, 452, 1.02), (1070, 444, 1.06), (1188, 464, 0.92)],
    5: [(792, 470, 0.92), (902, 454, 0.96), (1014, 438, 1.08), (1124, 452, 0.94), (1218, 470, 0.88)],
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
ENEMY_SPRITE_SCALE = 0.48
ENEMY_ACTION_HOLD_MS = 180
ENEMY_ACTION_RECOVER_MS = 100
ENEMY_ACTION_GAP_MS = 60
ENEMY_HIT_REACTION_HOLD_MS = 90
ENEMY_HIT_REACTION_RETURN_MS = 110
ENEMY_MELEE_LUNGE_PX = 16.0
ENEMY_RANGED_LEAN_PX = 6.0
ENEMY_HIT_RECOIL_PX = 12.0
PLAYER_ART_REFS = {
    "bio_hacker": {
        "path": ARTS_ROOT / "refs" / "Biohacker_Combat_Ref.png",
        "crop": (34, 86, 302, 562),
        "scale": 1.06,
        "colorkey": None,
    },
    "operator": {
        "path": ARTS_ROOT / "refs" / "Operator_Combat_Ref.png",
        "crop": (34, 72, 548, 882),
        "scale": 1.02,
        "colorkey": None,
    },
    "enforcer": {
        "path": ARTS_ROOT / "refs" / "Enforcer_Combat_Ref.png",
        "crop": (0, 0, 470, 860),
        "scale": 1.02,
        "colorkey": (255, 255, 255),
    },
}
HOOK_LABELS = {
    "combat_start": "Start of combat",
    "turn_one": "Turn one",
    "on_turn_start": "Turn start",
    "turn_end": "Turn end",
    "after_card_played": "After any card",
    "on_attack_hit": "After attack hit",
    "on_enemy_status_applied": "When enemy status lands",
    "on_player_status_applied": "When player status lands",
    "on_card_cost_reduced": "When card cost drops",
    "on_card_exhausted": "When a card exhausts",
    "on_self_damage": "When you lose HP",
    "on_heal": "When you heal",
    "on_bleed_trigger": "When bleed triggers",
    "on_infect_burst": "When infection bursts",
    "on_player_burn_tick": "When burn ticks",
    "on_positive_gain_blocked_by_nullified": "When nullified blocks a gain",
    "on_status_card_added_to_discard": "When a status card is added",
    "on_enemy_death": "On enemy defeat",
    "on_status_drawn": "When a status card is drawn",
}

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
        self._last_feedback_sequence = 0
        self._relic_flash_registry: dict[str, list[dict[str, int]]] = {}
        self._shield_flash_registry: dict[str, list[dict[str, int]]] = {}
        self._floating_feedback: list[dict[str, Any]] = []
        self._proc_ticker_entries: list[dict[str, Any]] = []
        self._last_layout_warning_signature: tuple[str, ...] | None = None
        self._last_surface_size: tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT)

    def preload_assets(self) -> None:
        if pygame is None:
            return
        combat_ui_assets.preload()
        for path in [
            *(entry["path"] for entry in PLAYER_ART_REFS.values()),
        ]:
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

    def handle_event(
        self,
        event: Any,
        combat_state: dict[str, Any],
        surface_size: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self.build_layout(combat_state, surface_size)

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

    def build_layout(self, combat_state: dict[str, Any], surface_size: tuple[int, int] | None = None) -> dict[str, Any]:
        presentation = combat_state.get("presentation", {})
        if pygame is not None:
            self._ensure_fonts(presentation.get("ui_scale", 1.0))
        resolved_surface_size = self._resolve_surface_size(surface_size)
        combat_layout = build_combat_layout(resolved_surface_size)
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

        hand_geometries = self._hand_card_geometries(len(hand), combat_layout)
        hand_cards: list[dict[str, Any]] = []
        for index, card in enumerate(hand):
            target_mode = self._card_target_mode(card)
            playable, disabled_reason = self._card_playability(
                card,
                player,
                living_enemy_ids,
                combat_state.get("turn_owner", "player"),
            )
            geometry = hand_geometries[index]
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
                    "draw_center": geometry["draw_center"],
                    "draw_scale": geometry["draw_scale"],
                    "draw_alpha": geometry["draw_alpha"],
                    "size": geometry["size"],
                    "angle": geometry["angle"],
                    "hit_rect": geometry["hit_rect"],
                }
            )

        selected_card = None
        if self._selected_card_index is not None and 0 <= self._selected_card_index < len(hand_cards):
            source_card = hand_cards[self._selected_card_index]
            if source_card["playable"]:
                if source_card["target_mode"] == "single_enemy" and self._selected_target_id not in source_card["valid_target_ids"]:
                    self._selected_target_id = source_card["default_target_id"]
                progress = 1.0 if self._pending_action is not None else _ease_out(self._animation_progress(self._selected_started_at, SELECT_ANIM_MS))
                target_center, target_size = self._selected_card_target_geometry(combat_layout)
                source_center = source_card.get("draw_center", source_card["center"])
                center_x = _lerp(source_center[0], target_center[0], progress)
                center_y = _lerp(source_center[1], target_center[1], progress)
                if self._pending_action is not None:
                    drift = _ease_out(self._animation_progress(int(self._pending_action["started_at"]), RESOLVE_ANIM_MS))
                    center_x = _lerp(center_x, center_x + 18, drift)
                    center_y = _lerp(center_y, center_y - 12, drift)
                selected_rect = _rect_from_center((center_x, center_y), target_size)
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

        player_actor = self._player_actor_layout(
            player,
            character,
            combat_state.get("run_state"),
            combat_state.get("drift_runtime"),
            combat_layout,
        )
        enemy_actors = self._enemy_actor_layout(enemies, selected_card, combat_layout)
        for enemy_actor in enemy_actors:
            enemy_actor.update(self._enemy_actor_animation_state(enemy_actor))
        self._prune_feedback_state()
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
        modifier_layout = self._combat_modifier_layout(combat_state.get("run_modifiers", []), combat_layout)
        tooltip_regions.extend(
            {
                "rect": modifier["rect"],
                "title": modifier["name"],
                "text": self._modifier_tooltip_text(modifier),
            }
            for modifier in modifier_layout["items"]
        )
        deck_stats = self._deck_stat_layout(player, combat_layout)

        layout = {
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
            "end_turn_rect": combat_layout.end_turn_rect,
            "end_turn_hovered": self._hovered_end_turn,
            "any_playable": any(card["playable"] for card in hand_cards),
            "living_enemy_ids": living_enemy_ids,
            "enemy_phase": combat_state.get("enemy_phase", {}),
            "high_contrast": presentation.get("high_contrast", False),
            "combat_layout_debug": presentation.get("combat_layout_debug", False),
            "tooltip": self._tooltip_at_position(tooltip_regions, self._mouse_pos),
            "targeting_active": selected_card is not None,
            "relic_tray": modifier_layout["relics"],
            "relic_rail_rect": modifier_layout["rail_rect"],
            "relic_overflow_count": modifier_layout["overflow_count"],
            "temp_modifier_tray": modifier_layout["temporary"],
            "deck_stats": deck_stats,
            "combat_layout": combat_layout,
            "layout_regions": combat_layout.debug_rects(),
            "card_platform_rect": combat_layout.card_platform_rect,
        }
        self._validate_layout(layout)
        return layout

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
        available_energy = int(player.get("total_energy", int(player.get("energy", 0) or 0)) or 0)
        if card["cost"] > available_energy:
            missing = card["cost"] - available_energy
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

    def _hand_card_geometries(self, hand_count: int, layout: CombatLayout) -> list[dict[str, Any]]:
        if hand_count <= 0:
            return []
        hand_rect = layout.hand_rect
        focus_active = self._hovered_card_index is not None and self._selected_card_index is None
        width = self._starting_hand_card_width(hand_count, layout)
        best: list[dict[str, Any]] = []
        for _attempt in range(18):
            height = int(width * CARD_PORTRAIT_HEIGHT_RATIO)
            step_ratio = 0.56 if hand_count <= 5 else max(0.30, 0.54 - ((hand_count - 5) * 0.04))
            if hand_count > 1:
                maximum_step = max(0.30, (hand_rect[2] - width) / (width * max(1, hand_count - 1)))
                step_ratio = min(step_ratio, maximum_step)
            angle_decay = max(0.0, (_attempt - 7) * 0.65)
            max_angle = 8.0 if hand_count <= 5 else max(3.0, 8.0 - ((hand_count - 5) * 0.8))
            max_angle = max(1.5, max_angle - angle_decay)
            if _attempt >= 10:
                step_ratio = max(0.24, step_ratio - ((_attempt - 9) * 0.015))
            candidate = self._candidate_hand_geometries(hand_count, hand_rect, width, height, step_ratio, max_angle)
            finalized = self._finalize_hand_geometries(candidate, layout, focus_active=focus_active)
            if self._hand_layout_fits(finalized, layout):
                best = finalized
                break
            best = finalized
            width = max(86, int(width * 0.94))

        return best

    def _starting_hand_card_width(self, hand_count: int, layout: CombatLayout) -> int:
        surface_width, surface_height = layout.surface_size
        screen_scale = min(surface_width / SCREEN_WIDTH, surface_height / SCREEN_HEIGHT)
        height_cap = int(layout.hand_rect[3] / (CARD_PORTRAIT_HEIGHT_RATIO * 1.04))
        comfortable_width = int(150 * max(0.76, min(1.10, screen_scale)))
        if hand_count == 5 and surface_width <= SCREEN_WIDTH and surface_height <= SCREEN_HEIGHT:
            comfortable_width = min(comfortable_width, 142)
        count_cap = int(layout.hand_rect[2] / max(1.0, 1.0 + (max(0, hand_count - 1) * 0.34)))
        return max(86, min(comfortable_width, height_cap, count_cap, 176))

    def _candidate_hand_geometries(
        self,
        hand_count: int,
        hand_rect: RectTuple,
        width: int,
        height: int,
        step_ratio: float,
        max_angle: float,
    ) -> list[dict[str, Any]]:
        spread = max(0.0, (hand_count - 1) * width * step_ratio)
        center_y = hand_rect[1] + int(round(hand_rect[3] * 0.55))
        cards: list[dict[str, Any]] = []
        for index in range(hand_count):
            offset = 0.0 if hand_count == 1 else (index / max(1, hand_count - 1)) * 2.0 - 1.0
            center_x = hand_rect[0] + (hand_rect[2] / 2) + (offset * (spread / 2))
            card_y = center_y + ((abs(offset) ** 1.5) * min(18, max(8, hand_rect[3] * 0.06)))
            angle = -max_angle * offset
            bounds = self._hand_card_hit_rect((center_x, card_y), (width, height), angle, scale=1.0)
            cards.append(
                {
                    "index": index,
                    "center": (center_x, card_y),
                    "draw_center": (center_x, card_y),
                    "draw_scale": 1.0,
                    "draw_alpha": 255,
                    "size": (width, height),
                    "angle": angle,
                    "bounds_rect": bounds,
                    "hit_rect": bounds,
                }
            )
        return cards

    def _finalize_hand_geometries(
        self,
        cards: list[dict[str, Any]],
        layout: CombatLayout,
        *,
        focus_active: bool,
    ) -> list[dict[str, Any]]:
        if not cards:
            return []
        hand_rect = layout.hand_rect
        safe_rect = layout.safe_rect
        union = self._rect_union([card["bounds_rect"] for card in cards])
        dx, dy = self._shift_needed_to_contain(union, hand_rect)
        union = self._shift_rect(union, dx, dy)
        safe_dx, safe_dy = self._shift_needed_to_contain(union, safe_rect)
        dx += safe_dx
        dy += safe_dy

        finalized: list[dict[str, Any]] = []
        for card in cards:
            center = (card["center"][0] + dx, card["center"][1] + dy)
            scale = self._hand_card_scale(card["index"])
            draw_center = center
            alpha = 255
            if card["index"] == self._hovered_card_index and card["index"] != self._selected_card_index:
                draw_center = (center[0], center[1] - self._hover_lift_for_layout(layout))
            elif focus_active:
                draw_center = (center[0], center[1] + min(CARD_FOCUS_RECESS_PX, max(4, hand_rect[3] // 24)))
                alpha = CARD_DIMMED_ALPHA
            draw_rect = self._hand_card_hit_rect(draw_center, card["size"], card["angle"], scale=scale)
            draw_dx, draw_dy = self._shift_needed_to_contain(draw_rect, safe_rect)
            if draw_dx != 0 or draw_dy != 0:
                draw_center = (draw_center[0] + draw_dx, draw_center[1] + draw_dy)
                draw_rect = self._hand_card_hit_rect(draw_center, card["size"], card["angle"], scale=scale)
            finalized.append(
                {
                    **card,
                    "center": center,
                    "draw_center": draw_center,
                    "draw_scale": scale,
                    "draw_alpha": alpha,
                    "hit_rect": draw_rect,
                }
            )

        all_rects = [tuple(card["hit_rect"]) for card in finalized]
        final_union = self._rect_union(all_rects)
        adjust_x, adjust_y = self._shift_needed_to_contain(final_union, safe_rect)
        if adjust_x != 0 or adjust_y != 0:
            adjusted: list[dict[str, Any]] = []
            for card in finalized:
                center = (card["center"][0] + adjust_x, card["center"][1] + adjust_y)
                draw_center = (card["draw_center"][0] + adjust_x, card["draw_center"][1] + adjust_y)
                draw_rect = self._shift_rect(tuple(card["hit_rect"]), adjust_x, adjust_y)
                adjusted.append({**card, "center": center, "draw_center": draw_center, "hit_rect": draw_rect})
            finalized = adjusted
        return finalized

    def _hand_layout_fits(self, cards: list[dict[str, Any]], layout: CombatLayout) -> bool:
        if not cards:
            return True
        safe_rect = layout.safe_rect
        steady_cards = [
            tuple(card["hit_rect"])
            for card in cards
            if card["index"] != self._hovered_card_index and card["index"] != self._selected_card_index
        ]
        if not steady_cards:
            steady_cards = [tuple(card["hit_rect"]) for card in cards]
        if not all(self._rect_contains(safe_rect, tuple(card["hit_rect"])) for card in cards):
            return False
        steady_union = self._rect_union(steady_cards)
        if not self._rect_contains(layout.hand_rect, steady_union):
            return False
        for rect in steady_cards:
            for reserved in (
                layout.player_status_rect,
                layout.deck_discard_rect,
                layout.exhaust_rect,
                layout.end_turn_rect,
            ):
                if self._rects_intersect(rect, reserved):
                    return False
        return True

    def _hover_lift_for_layout(self, layout: CombatLayout) -> int:
        top_limit = max(
            layout.top_hud_rect[1] + layout.top_hud_rect[3] + 18,
            layout.enemy_status_area_rect[1] + layout.enemy_status_area_rect[3] + 10,
        )
        hand_top = layout.hand_rect[1]
        available = max(0, hand_top - top_limit - 8)
        if available <= 0:
            return 0
        return min(CARD_FOCUS_LIFT, available)

    def _hand_card_scale(self, index: int) -> float:
        if index == self._hovered_card_index and index != self._selected_card_index:
            hover_progress = _ease_out(self._animation_progress(self._hover_started_at, 90))
            return _lerp(1.0, CARD_HOVER_SCALE, hover_progress)
        if index == self._selected_card_index:
            return 0.9
        if self._hovered_card_index is not None and self._selected_card_index is None:
            return 0.97
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
        return _rect_from_center(center, (rotated_width, rotated_height))

    def _selected_card_target_geometry(self, layout: CombatLayout) -> tuple[tuple[float, float], tuple[int, int]]:
        arena = layout.arena_rect
        hand = layout.hand_rect
        safe = layout.safe_rect
        width = max(142, min(214, int(hand[3] / CARD_PORTRAIT_HEIGHT_RATIO), int(arena[2] * 0.18)))
        height = int(width * CARD_PORTRAIT_HEIGHT_RATIO)
        center_x = hand[0] + (hand[2] / 2)
        center_y = hand[1] - (height / 2) - max(10, int(layout.surface_size[1] * 0.018))
        min_y = max(
            arena[1] + (height / 2) + 10,
            layout.enemy_status_area_rect[1] + layout.enemy_status_area_rect[3] + (height / 2) + 8,
        )
        max_y = hand[1] - (height / 2) - 8
        if max_y < min_y:
            max_y = min_y
        center_y = max(min_y, min(max_y, center_y))
        center_x = max(safe[0] + (width / 2), min(safe[0] + safe[2] - (width / 2), center_x))
        return (center_x, center_y), (width, height)

    def _rect_union(self, rects: list[RectTuple]) -> RectTuple:
        if not rects:
            return (0, 0, 0, 0)
        left = min(rect[0] for rect in rects)
        top = min(rect[1] for rect in rects)
        right = max(rect[0] + rect[2] for rect in rects)
        bottom = max(rect[1] + rect[3] for rect in rects)
        return (left, top, max(0, right - left), max(0, bottom - top))

    def _rect_contains(self, outer: RectTuple, inner: RectTuple) -> bool:
        return (
            inner[0] >= outer[0]
            and inner[1] >= outer[1]
            and inner[0] + inner[2] <= outer[0] + outer[2]
            and inner[1] + inner[3] <= outer[1] + outer[3]
        )

    def _rects_intersect(self, first: RectTuple, second: RectTuple) -> bool:
        return not (
            first[0] + first[2] <= second[0]
            or second[0] + second[2] <= first[0]
            or first[1] + first[3] <= second[1]
            or second[1] + second[3] <= first[1]
        )

    def _shift_needed_to_contain(self, rect: RectTuple, bounds: RectTuple) -> tuple[int, int]:
        dx = 0
        dy = 0
        if rect[0] < bounds[0]:
            dx = bounds[0] - rect[0]
        elif rect[0] + rect[2] > bounds[0] + bounds[2]:
            dx = (bounds[0] + bounds[2]) - (rect[0] + rect[2])
        if rect[1] < bounds[1]:
            dy = bounds[1] - rect[1]
        elif rect[1] + rect[3] > bounds[1] + bounds[3]:
            dy = (bounds[1] + bounds[3]) - (rect[1] + rect[3])
        return dx, dy

    def _shift_rect(self, rect: RectTuple, dx: int, dy: int) -> RectTuple:
        return (rect[0] + dx, rect[1] + dy, rect[2], rect[3])

    def _player_actor_layout(
        self,
        player: dict[str, Any],
        character: dict[str, Any],
        run_state: dict[str, Any] | None,
        drift_runtime: dict[str, Any] | None,
        layout: CombatLayout,
    ) -> dict[str, Any]:
        accent = tuple(character.get("accent_color", [232, 88, 72]))
        surface_scale = min(layout.surface_size[0] / SCREEN_WIDTH, layout.surface_size[1] / SCREEN_HEIGHT)
        actor_scale = PLAYER_SCALE * max(0.92, min(1.16, surface_scale))
        actor_width = int(96 * actor_scale)
        actor_height = int(156 * actor_scale)
        foot_x = int(layout.arena_rect[0] + (layout.arena_rect[2] * 0.15))
        foot_y = min(layout.arena_rect[1] + layout.arena_rect[3] - 8, layout.player_status_rect[1] - 8)
        foot = (foot_x, int(foot_y))
        actor_rect = pygame.Rect(int(foot[0] - actor_width / 2), int(foot[1] - actor_height), actor_width, actor_height) if pygame is not None else None
        hud_rect = layout.player_status_rect
        block_rect = (
            hud_rect[0] + max(236, hud_rect[2] - 86),
            hud_rect[1] + max(34, int(hud_rect[3] * 0.48)),
            72,
            28,
        )
        deck_rect = layout.deck_discard_rect
        drift_rect = (
            deck_rect[0],
            deck_rect[1] + 2,
            min(28, max(18, int(deck_rect[2] * 0.08))),
            max(76, min(104, deck_rect[3] - 4)),
        )
        combat_statuses = player.get("combat_statuses", {})
        infect_value = combat_statuses.get("infect", 0) if isinstance(combat_statuses, dict) else 0
        infect_preview = self._infect_preview(player.get("current_hp", 0), infect_value)
        protocol_drift_pct = 0
        protocol_drift_band_index = 0
        protocol_drift_band_label = "Stable"
        if isinstance(run_state, dict):
            protocol_drift_pct = max(0, min(100, int(run_state.get("protocol_drift_pct", 0) or 0)))
            protocol_drift_band_index = max(0, min(5, int(run_state.get("tier_index", run_state.get("band_index", 0)) or 0)))
            protocol_drift_band_label = str(run_state.get("tier_label", run_state.get("band_label", "Stable")))
        feedback_safe_threshold = None if not isinstance(drift_runtime, dict) else drift_runtime.get("feedback_safe_threshold_this_turn")
        feedback_triggers = 0 if not isinstance(drift_runtime, dict) else int(drift_runtime.get("feedback_triggers_this_turn", 0) or 0)
        return {
            "character_id": character.get("id", player.get("character_id", "runner")),
            "name": character.get("name", "Runner"),
            "accent": accent,
            "foot": foot,
            "actor_rect": actor_rect,
            "hud_rect": hud_rect,
            "block_rect": block_rect,
            "drift_rect": drift_rect,
            "feedback_key": "player",
            "feedback_anchor": (foot[0] + 6, foot[1] - 118),
            "block_anchor": (block_rect[0] + (block_rect[2] // 2), block_rect[1] + (block_rect[3] // 2)),
            "status_origin": (hud_rect[0] + 26, hud_rect[1] + max(44, hud_rect[3] - 24)),
            "player": player,
            "infect_preview_damage": infect_preview["damage"],
            "infect_preview_lethal": infect_preview["lethal"],
            "protocol_drift_pct": protocol_drift_pct,
            "protocol_drift_band_index": protocol_drift_band_index,
            "protocol_drift_band_label": protocol_drift_band_label,
            "feedback_safe_threshold": feedback_safe_threshold,
            "feedback_triggers": feedback_triggers,
        }

    def _enemy_actor_layout(
        self,
        enemies: list[dict[str, Any]],
        selected_card: dict[str, Any] | None,
        layout: CombatLayout,
    ) -> list[dict[str, Any]]:
        valid_target_ids = set(selected_card["valid_target_ids"]) if selected_card is not None else set()
        actors: list[dict[str, Any]] = []
        count = max(1, len(enemies))
        arena = layout.arena_rect
        lane_left = arena[0] + int(round(arena[2] * 0.54))
        lane_right = arena[0] + arena[2] - max(38, int(round(layout.surface_size[0] * 0.03)))
        lane_width = max(120, lane_right - lane_left)
        base_foot_y = min(arena[1] + arena[3] - 12, layout.hand_rect[1] - 38)
        surface_scale = min(layout.surface_size[0] / SCREEN_WIDTH, layout.surface_size[1] / SCREEN_HEIGHT)
        base_scale = max(0.86, min(1.14, surface_scale))
        for index, enemy in enumerate(enemies):
            if count == 1:
                foot_x = lane_left + int(round(lane_width * 0.58))
            else:
                foot_x = lane_left + int(round((lane_width * index) / max(1, count - 1)))
            foot_y = int(base_foot_y - (10 if count > 2 and index % 2 == 1 else 0))
            scale = base_scale * (0.98 if count >= 3 else 1.04)
            if enemy.get("tier") == "boss":
                scale *= 1.12
            elif enemy.get("tier") == "elite":
                scale *= 1.06
            enemy_ref = str(enemy.get("enemy_ref") or f"{enemy['id']}#{index}")
            hp_width = max(84, min(140, int((lane_width / count) * 0.78)))
            width = int(92 * scale)
            height = int(146 * scale)
            top_y = int(foot_y - height)
            rect = pygame.Rect(int(foot_x - width / 2), top_y, width, height) if pygame is not None else None
            accent = FACTION_COLORS.get(str(enemy.get("faction_id", "legacy")), FACTION_COLORS["legacy"])
            status_top = min(int(foot_y + 8), layout.hand_rect[1] - 48)
            status_top -= 10 if count > 2 and index % 2 == 1 else 0
            status_top = max(layout.enemy_status_area_rect[1], status_top)
            name_rect = (int(foot_x - hp_width / 2), status_top, hp_width, 18)
            hp_bar_rect = (int(foot_x - hp_width / 2), status_top + 20, hp_width, 14)
            block_rect = (int(foot_x + (hp_width / 2) + 8), status_top + 10, 48, 30)
            intent_w = max(118, min(166, hp_width + 38))
            intent_rect = (
                int(foot_x - intent_w / 2),
                max(layout.top_resource_bar_rect[1] + layout.top_resource_bar_rect[3] + 10, int(top_y - 50)),
                intent_w,
                38,
            )
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
                    "name_rect": name_rect,
                    "hp_bar_rect": hp_bar_rect,
                    "block_rect": block_rect,
                    "intent_rect": intent_rect,
                    "feedback_key": enemy_ref,
                    "feedback_anchor": (int(foot_x), int(top_y + 24)),
                    "block_anchor": (block_rect[0] + (block_rect[2] // 2), block_rect[1] + (block_rect[3] // 2)),
                    "status_origin": (int(foot_x), int(min(hp_bar_rect[1] + hp_bar_rect[3] + 6, layout.hand_rect[1] - 32))),
                    "targeted": enemy["id"] == (selected_card["target_id"] if selected_card is not None else None),
                    "valid_target": enemy["id"] in valid_target_ids if selected_card is not None else True,
                    "dimmed": selected_card is not None and selected_card["target_mode"] in {"single_enemy", "all_enemies"} and enemy["id"] not in valid_target_ids,
                    "infect_preview_damage": infect_preview["damage"],
                    "infect_preview_lethal": infect_preview["lethal"],
                }
            )
        return self._resolve_enemy_status_layout(actors, layout)

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

    def _resolve_enemy_status_layout(
        self,
        actors: list[dict[str, Any]],
        layout: CombatLayout,
    ) -> list[dict[str, Any]]:
        if len(actors) <= 1:
            return actors
        sorted_actors = sorted(actors, key=lambda actor: actor["foot"][0])
        area = layout.enemy_status_area_rect
        area_left = area[0]
        area_right = area[0] + area[2]
        min_width = 72
        max_status_top = max(area[1], layout.hand_rect[1] - 48)
        min_status_top = area[1]

        for index, actor in enumerate(sorted_actors):
            foot_x = int(actor["foot"][0])
            left_bound = area_left if index == 0 else int((sorted_actors[index - 1]["foot"][0] + foot_x) / 2) + 8
            right_bound = area_right if index == len(sorted_actors) - 1 else int((foot_x + sorted_actors[index + 1]["foot"][0]) / 2) - 8
            available_width = max(min_width, right_bound - left_bound - 56)
            hp_width = max(min_width, min(int(actor["hp_bar_rect"][2]), available_width))
            base_top = max(min_status_top, min(max_status_top, int(actor["name_rect"][1])))
            intent_width = max(96, min(int(actor["intent_rect"][2]), max(104, right_bound - left_bound - 8)))
            status_candidates = [base_top, base_top - 12, base_top + 12, base_top - 24, base_top + 24]

            for candidate_top in status_candidates:
                status_top = max(min_status_top, min(max_status_top, candidate_top))
                name_rect = (int(foot_x - hp_width / 2), status_top, hp_width, actor["name_rect"][3])
                hp_bar_rect = (int(foot_x - hp_width / 2), status_top + 20, hp_width, actor["hp_bar_rect"][3])
                block_x = min(area_right - actor["block_rect"][2], hp_bar_rect[0] + hp_width + 8)
                block_x = max(left_bound, block_x)
                block_rect = (block_x, status_top + 10, actor["block_rect"][2], actor["block_rect"][3])
                group_rect = self._rect_union([name_rect, hp_bar_rect, block_rect])
                if all(
                    not self._rects_intersect(group_rect, self._rect_union([other["name_rect"], other["hp_bar_rect"], other["block_rect"]]))
                    for other in sorted_actors[:index]
                ):
                    intent_rect = (
                        int(max(left_bound, min(right_bound - intent_width, foot_x - (intent_width / 2)))),
                        actor["intent_rect"][1],
                        intent_width,
                        actor["intent_rect"][3],
                    )
                    actor["name_rect"] = name_rect
                    actor["hp_bar_rect"] = hp_bar_rect
                    actor["block_rect"] = block_rect
                    actor["intent_rect"] = intent_rect
                    actor["block_anchor"] = (block_rect[0] + (block_rect[2] // 2), block_rect[1] + (block_rect[3] // 2))
                    actor["status_origin"] = (foot_x, int(min(hp_bar_rect[1] + hp_bar_rect[3] + 6, layout.hand_rect[1] - 32)))
                    break
        return actors

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

    def _combat_modifier_layout(self, run_modifiers: list[dict[str, Any]], layout: CombatLayout) -> dict[str, Any]:
        rail_rect = layout.top_resource_bar_rect
        if not isinstance(run_modifiers, list):
            return {"items": [], "relics": [], "temporary": [], "rail_rect": rail_rect, "overflow_count": 0}

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

        relics: list[dict[str, Any]] = []
        temporary: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []
        all_relic_modifiers = [modifier for modifier in filtered if modifier.get("type") == "relic"]
        relic_modifiers = all_relic_modifiers[:RELIC_TRAY_LIMIT]
        overflow_count = max(0, len(all_relic_modifiers) - len(relic_modifiers))
        temporary_modifiers = [modifier for modifier in filtered if modifier.get("type") != "relic"][:6]

        rail_margin = max(14, int(round(rail_rect[3] * 0.28)))
        rail_gap = max(5, min(RELIC_TRAY_GAP, int(round(rail_rect[2] * 0.012))))
        slot_limit_width = rail_rect[2] - (rail_margin * 2) - ((RELIC_TRAY_LIMIT - 1) * rail_gap)
        slot_size = max(28, min(RELIC_TRAY_SLOT, rail_rect[3] - 12, slot_limit_width // RELIC_TRAY_LIMIT))
        start_x = rail_rect[0] + rail_margin
        start_y = rail_rect[1] + ((rail_rect[3] - slot_size) // 2)
        for index in range(RELIC_TRAY_LIMIT):
            slot_x = start_x + (index * (slot_size + rail_gap))
            rect = (slot_x, start_y, slot_size, slot_size)
            if index >= len(relic_modifiers):
                relics.append(
                    {
                        "rect": rect,
                        "tray": "relic",
                        "empty": True,
                        "slot_index": index,
                        "accent": (104, 216, 255),
                    }
                )
                continue
            modifier = relic_modifiers[index]
            item = {
                **modifier,
                "rect": rect,
                "accent": self._modifier_accent(modifier.get("type", modifier.get("kind", "status"))),
                "abbrev": self._modifier_abbrev(str(modifier.get("name", "?"))),
                "tray": "relic",
                "empty": False,
                "slot_index": index,
            }
            relics.append(item)
            items.append(item)

        temp_start_x = layout.turn_label_rect[0]
        temp_y = min(layout.arena_rect[1] - TEMP_MODIFIER_SLOT - 4, layout.turn_label_rect[1] + layout.turn_label_rect[3] + 8)
        for index, modifier in enumerate(temporary_modifiers):
            slot_x = temp_start_x + (index * (TEMP_MODIFIER_SLOT + TEMP_MODIFIER_GAP))
            item = {
                **modifier,
                "rect": (slot_x, temp_y, TEMP_MODIFIER_SLOT, TEMP_MODIFIER_SLOT),
                "accent": self._modifier_accent(modifier.get("type", modifier.get("kind", "status"))),
                "abbrev": self._modifier_abbrev(str(modifier.get("name", "?"))),
                "tray": "temporary",
            }
            temporary.append(item)
            items.append(item)

        return {
            "items": items,
            "relics": relics,
            "temporary": temporary,
            "rail_rect": rail_rect,
            "overflow_count": overflow_count,
        }

    def _deck_stat_layout(self, player: dict[str, Any], layout: CombatLayout) -> list[dict[str, Any]]:
        deck_rect = layout.deck_discard_rect
        drift_w = min(28, max(18, int(deck_rect[2] * 0.08)))
        gap = max(8, int(layout.surface_size[0] * 0.008))
        pile_area_x = deck_rect[0] + drift_w + gap
        pile_area_w = max(120, deck_rect[2] - drift_w - gap)
        pile_w = max(62, min(88, (pile_area_w - gap) // 2))
        pile_h = max(66, min(deck_rect[3] - 4, int(pile_w * 1.08)))
        pile_y = deck_rect[1] + max(2, (deck_rect[3] - pile_h) // 2)
        draw_rect = (pile_area_x, pile_y, pile_w, pile_h)
        discard_rect = (pile_area_x + pile_w + gap, pile_y, pile_w, pile_h)
        stats = [
            ("draw", "Draw", int(player.get("draw_pile", 0) or 0), (104, 216, 255), draw_rect),
            ("discard", "Discard", int(player.get("discard_pile", 0) or 0), (139, 77, 255), discard_rect),
            ("exhaust", "Exhaust", int(player.get("exhaust_pile", 0) or 0), (255, 154, 36), layout.exhaust_rect),
        ]
        entries: list[dict[str, Any]] = []
        for stat_id, label, value, accent, rect in stats:
            entries.append(
                {
                    "id": stat_id,
                    "label": label,
                    "value": value,
                    "accent": accent,
                    "rect": rect,
                }
            )
        return entries

    def _modifier_tooltip_text(self, modifier: dict[str, Any]) -> str:
        parts = [str(modifier.get("description", ""))]
        trigger_text = self._modifier_trigger_text(modifier)
        if trigger_text:
            parts.append(f"Trigger: {trigger_text}")
        duration_label = modifier.get("duration_label")
        if duration_label:
            parts.append(str(duration_label))
        downside = modifier.get("downside")
        if downside:
            parts.append(f"Tradeoff: {downside}")
        return " ".join(part for part in parts if part).strip()

    def _modifier_trigger_text(self, modifier: dict[str, Any]) -> str:
        hooks = modifier.get("hooks", {})
        if not isinstance(hooks, dict):
            return ""
        labels = [
            HOOK_LABELS.get(str(hook_name), str(hook_name).replace("_", " ").title())
            for hook_name, effects in hooks.items()
            if effects
        ]
        if not labels:
            return ""
        if len(labels) <= 2:
            return ", ".join(labels)
        return ", ".join(labels[:2]) + ", ..."

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

    def _prune_feedback_state(self) -> None:
        now = self._now_ms()
        self._floating_feedback = [
            entry for entry in self._floating_feedback if (now - int(entry.get("started_at", now))) <= FEEDBACK_NUMBER_MS
        ]
        self._proc_ticker_entries = [
            entry for entry in self._proc_ticker_entries if (now - int(entry.get("started_at", now))) <= PROC_TICKER_MS
        ]
        self._shield_flash_registry = {
            key: [pulse for pulse in pulses if (now - int(pulse.get("started_at", now))) <= SHIELD_FLASH_MS]
            for key, pulses in self._shield_flash_registry.items()
            if any((now - int(pulse.get("started_at", now))) <= SHIELD_FLASH_MS for pulse in pulses)
        }
        self._relic_flash_registry = {
            key: [pulse for pulse in pulses if (now - int(pulse.get("started_at", now))) <= RELIC_FLASH_TOTAL_MS]
            for key, pulses in self._relic_flash_registry.items()
            if any((now - int(pulse.get("started_at", now))) <= RELIC_FLASH_TOTAL_MS for pulse in pulses)
        }

    def render(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        presentation = combat_state.get("presentation", {})
        self._ensure_fonts(presentation.get("ui_scale", 1.0))
        layout = self.build_layout(combat_state, surface.get_size())
        self.render_background(surface, combat_state)
        self.render_foreground(surface, combat_state, layout=layout)

    def render_background(self, surface: Any, combat_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        del combat_state
        combat_ui_assets.blit_cover(surface, "background", surface.get_rect())
        draw_screen_scrim(surface, alpha=56, color=(3, 6, 12))
        draw_visor_overlay(surface, alpha=COMBAT_VISOR_OVERLAY_ALPHA)

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
        layout = self.build_layout(combat_state, surface.get_size()) if layout is None else layout
        if layout["selected_card"] is not None:
            self._draw_target_focus_scrim(surface)
        self._draw_mid_plane(surface)

        player_targeted = layout["selected_card"] is not None and layout["selected_card"]["target_mode"] == "immediate_self"
        self._draw_player_body(surface, layout["player_actor"], high_contrast=high_contrast, targeted=player_targeted)

        for enemy_actor in layout["enemy_actors"]:
            self._draw_enemy_body(surface, enemy_actor, high_contrast=high_contrast)

        self._draw_combat_foreground_plane(surface)

        if layout["selected_card"] is not None:
            self._draw_target_guides(surface, layout)

        self._draw_turn_header(surface, layout, high_contrast=high_contrast)
        self._draw_combat_modifier_trays(surface, layout, high_contrast=high_contrast)
        self._draw_proc_ticker(surface, high_contrast=high_contrast)
        self._draw_player_hud(surface, layout["player_actor"], high_contrast=high_contrast, targeted=player_targeted)
        for enemy_actor in layout["enemy_actors"]:
            self._draw_enemy_overlay(surface, enemy_actor, high_contrast=high_contrast)

        if layout["active_bark"] is not None:
            self._render_bark(surface, layout["active_bark"], layout["enemy_actors"])

        self._draw_floating_feedback(surface, layout)
        self._draw_foreground_card_platform(surface, layout)
        self._draw_deck_stats(surface, layout)
        self._draw_end_turn_button(surface, layout)
        self._draw_hand(surface, layout, high_contrast=high_contrast)
        if layout["selected_card"] is not None:
            self._draw_selected_card(surface, layout["selected_card"], high_contrast=high_contrast)
        if layout.get("combat_layout_debug"):
            self._draw_layout_debug(surface, layout)
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

    def _draw_mid_plane(self, surface: Any) -> None:
        combat_ui_assets.blit_cover(surface, "midplane", surface.get_rect())

    def _draw_combat_foreground_plane(self, surface: Any) -> None:
        combat_ui_assets.blit_cover(surface, "foreground", surface.get_rect())

    def _draw_foreground_card_platform(self, surface: Any, layout: dict[str, Any]) -> None:
        combat_ui_assets.blit(surface, "card_platform", layout.get("card_platform_rect", FOREGROUND_PLATFORM_RECT))

    def _draw_target_focus_scrim(self, surface: Any) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((6, 8, 14, 64))
        surface.blit(overlay, (0, 0))

    def _draw_turn_header(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        del high_contrast
        turn_rect = layout.get("layout_regions", {}).get("turn_label_rect")
        if turn_rect is None:
            origin_x, origin_y = TURN_HEADER_ORIGIN
            width = 150
        else:
            origin_x, origin_y, width, _height = turn_rect
        owner_color = (255, 214, 110) if layout["turn_owner_label"] == "Player" else (232, 106, 112)
        pygame.draw.rect(surface, owner_color, pygame.Rect(origin_x + 2, origin_y + 4, TURN_HEADER_LINE_WIDTH, 34), border_radius=2)
        shadow_color = (0, 0, 0)

        turn_shadow = self._font.render(layout["turn_label"], True, shadow_color)
        turn_shadow.set_alpha(150)
        surface.blit(turn_shadow, (origin_x + 13, origin_y - 1))
        turn_label = self._font.render(layout["turn_label"], True, (236, 244, 255))
        surface.blit(turn_label, (origin_x + 11, origin_y - 3))

        owner_shadow = self._small_font.render(f"{layout['turn_owner_label']} Turn", True, shadow_color)
        owner_shadow.set_alpha(140)
        surface.blit(owner_shadow, (origin_x + 13, origin_y + 24))
        owner_text = self._fit_single_line(f"{layout['turn_owner_label']} Turn", self._small_font, width - 18)
        owner_label = self._small_font.render(owner_text, True, owner_color)
        surface.blit(owner_label, (origin_x + 11, origin_y + 22))

    def _draw_combat_modifier_trays(self, surface: Any, layout: dict[str, Any], *, high_contrast: bool) -> None:
        relics = list(layout.get("relic_tray", []))
        temporary = list(layout.get("temp_modifier_tray", []))
        rail_rect = pygame.Rect(*layout.get("relic_rail_rect", RELIC_RAIL_RECT))
        combat_ui_assets.blit(surface, "relic_tray_rail", rail_rect)

        if temporary:
            temp_y = temporary[0]["rect"][1] - 16
            self._draw_text(surface, "ACTIVE EFFECTS", (44, temp_y), self._tiny_font, width=180)

        for modifier in relics:
            rect = pygame.Rect(*modifier["rect"])
            accent = modifier["accent"]
            if high_contrast:
                accent = tuple(min(255, channel + 18) for channel in accent)

            is_empty = bool(modifier.get("empty"))
            flash_intensity = 0.0 if is_empty else self._relic_flash_intensity(str(modifier.get("id", "")))
            scale_boost = 1.0 + (0.08 * flash_intensity)
            animated_rect = pygame.Rect(0, 0, max(1, int(rect.width * scale_boost)), max(1, int(rect.height * scale_boost)))
            animated_rect.center = rect.center

            hovered = self._mouse_pos != (-1, -1) and point_in_rect(self._mouse_pos, modifier["rect"])
            if is_empty:
                continue
            if hovered:
                pygame.draw.rect(surface, YELLOW, animated_rect, 1, border_radius=8)
            if not is_empty:
                art = relic_assets.get_relic_art(str(modifier.get("id", "")), animated_rect.size)
                if art is not None:
                    art_rect = art.get_rect(center=animated_rect.center)
                    surface.blit(art, art_rect.topleft)
                else:
                    label = self._small_font.render(modifier["abbrev"], True, accent)
                    surface.blit(label, label.get_rect(center=animated_rect.center))
                if flash_intensity > 0.0:
                    flash_overlay = pygame.Surface(animated_rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(
                        flash_overlay,
                        (255, 255, 255, int(_lerp(0, 148, flash_intensity))),
                        flash_overlay.get_rect(),
                        border_radius=14,
                    )
                    surface.blit(flash_overlay, animated_rect.topleft)

        overflow_count = int(layout.get("relic_overflow_count", 0) or 0)
        if overflow_count > 0:
            badge_rect = pygame.Rect(rail_rect.right - 58, rail_rect.centery - 12, 42, 24)
            draw_clipped_panel(surface, badge_rect, fill=(8, 12, 18, 236), border=YELLOW, cut=8, shadow=False)
            badge = self._tiny_font.render(f"+{overflow_count}", True, YELLOW)
            surface.blit(badge, badge.get_rect(center=badge_rect.center))

        for modifier in temporary:
            rect = pygame.Rect(*modifier["rect"])
            accent = modifier["accent"]
            if high_contrast:
                accent = tuple(min(255, channel + 18) for channel in accent)
            hovered = self._mouse_pos != (-1, -1) and point_in_rect(self._mouse_pos, modifier["rect"])
            label = self._tiny_font.render(modifier["abbrev"], True, accent)
            surface.blit(label, label.get_rect(center=rect.center))
            if hovered:
                pygame.draw.line(surface, YELLOW, (rect.x + 5, rect.bottom - 4), (rect.right - 5, rect.bottom - 4), 2)
            else:
                pygame.draw.line(surface, accent, (rect.x + 5, rect.bottom - 4), (rect.right - 5, rect.bottom - 4), 1)
            if modifier.get("temporary") and isinstance(modifier.get("remaining"), int):
                badge_rect = pygame.Rect(rect.right - 10, rect.y - 5, 18, 18)
                pygame.draw.rect(surface, YELLOW, badge_rect, border_radius=9)
                badge = self._tiny_font.render(str(modifier["remaining"]), True, (18, 24, 36))
                surface.blit(badge, badge.get_rect(center=badge_rect.center))

    def _draw_proc_ticker(self, surface: Any, *, high_contrast: bool) -> None:
        del high_contrast
        now = self._now_ms()
        visible_entries = [
            entry
            for entry in self._proc_ticker_entries
            if int(entry.get("started_at", now)) <= now and (now - int(entry.get("started_at", now))) <= PROC_TICKER_MS
        ]
        if not visible_entries:
            return
        visible_entries = visible_entries[-3:]
        origin_x, origin_y = PROC_TICKER_ORIGIN
        for index, entry in enumerate(visible_entries):
            elapsed = max(0, now - int(entry.get("started_at", now)))
            progress = max(0.0, min(1.0, elapsed / max(1, PROC_TICKER_MS)))
            alpha = int(_lerp(255, 0, progress ** 1.45))
            row_y = origin_y + (index * 42) - int(_lerp(0, 8, progress))
            row_rect = pygame.Rect(origin_x, row_y, PROC_TICKER_WIDTH, 36)
            panel = pygame.Surface(row_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (10, 16, 26, min(208, alpha)), panel.get_rect(), border_radius=12)
            pygame.draw.rect(panel, (132, 170, 220, min(230, alpha)), panel.get_rect(), 1, border_radius=12)
            surface.blit(panel, row_rect.topleft)

            combo_index = max(0, int(entry.get("combo_index", 0) or 0))
            if combo_index > 0:
                badge_rect = pygame.Rect(row_rect.x + 8, row_rect.y + 8, 22, 20)
                badge = pygame.Surface(badge_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(badge, (104, 216, 255, min(220, alpha)), badge.get_rect(), border_radius=8)
                surface.blit(badge, badge_rect.topleft)
                badge_text = self._tiny_font.render(str(combo_index), True, (12, 18, 28))
                badge_text.set_alpha(alpha)
                surface.blit(badge_text, badge_text.get_rect(center=badge_rect.center))

            label_x = row_rect.x + (40 if combo_index > 0 else 12)
            label_surface = self._small_font.render(str(entry.get("label", "")), True, (244, 248, 255))
            label_surface.set_alpha(alpha)
            surface.blit(label_surface, (label_x, row_rect.y + 4))
            detail_surface = self._tiny_font.render(str(entry.get("detail", "")), True, (176, 194, 220))
            detail_surface.set_alpha(alpha)
            surface.blit(detail_surface, (label_x, row_rect.y + 20))

    def _draw_floating_feedback(self, surface: Any, layout: dict[str, Any]) -> None:
        now = self._now_ms()
        actor_lookup = self._feedback_actor_lookup(layout)
        for entry in self._floating_feedback:
            started_at = int(entry.get("started_at", now))
            if started_at > now:
                continue
            elapsed = max(0, now - started_at)
            progress = max(0.0, min(1.0, elapsed / max(1, FEEDBACK_NUMBER_MS)))
            anchor = self._feedback_anchor(actor_lookup, str(entry.get("target_key", "")))
            if anchor is None:
                continue
            drift_phase = float(entry.get("phase", 0.0) or 0.0)
            drift_x = math.sin((elapsed / 95.0) + drift_phase) * 10.0 * (1.0 - progress)
            drift_y = _lerp(0.0, -48.0, _ease_out(progress))
            alpha = int(_lerp(255, 0, progress ** 1.5))
            label = str(entry.get("label", ""))
            color = entry.get("color", (240, 244, 255))
            shadow = self._small_font.render(label, True, (0, 0, 0))
            shadow.set_alpha(max(0, int(alpha * 0.65)))
            glyph = self._small_font.render(label, True, color)
            glyph.set_alpha(alpha)
            draw_pos = (
                int(anchor[0] + drift_x - (glyph.get_width() / 2)),
                int(anchor[1] + drift_y),
            )
            surface.blit(shadow, (draw_pos[0] + 2, draw_pos[1] + 2))
            surface.blit(glyph, draw_pos)

    def _draw_deck_stats(self, surface: Any, layout: dict[str, Any]) -> None:
        player_actor = layout.get("player_actor", {})
        drift_rect = player_actor.get("drift_rect")
        if drift_rect is not None:
            self._draw_asset_drift_gauge(
                surface,
                pygame.Rect(*drift_rect),
                protocol_drift_pct=int(player_actor.get("protocol_drift_pct", 0) or 0),
                band_index=int(player_actor.get("protocol_drift_band_index", 0) or 0),
            )
            safe_threshold = player_actor.get("feedback_safe_threshold")
            if safe_threshold is not None:
                cards_played = int(player_actor.get("player", {}).get("cards_played_this_turn", 0) or 0)
                triggers = int(player_actor.get("feedback_triggers", 0) or 0)
                info_rect = pygame.Rect(drift_rect[0] + 30, drift_rect[1] + 6, 164, 34)
                self._draw_text(surface, f"Feedback {cards_played}/{safe_threshold}", (info_rect.x, info_rect.y), self._micro_font, width=info_rect.width)
                self._draw_text(surface, f"Triggers {triggers}", (info_rect.x, info_rect.y + 14), self._micro_font, width=info_rect.width)
        for entry in layout.get("deck_stats", []):
            rect = pygame.Rect(*entry["rect"])
            accent = entry["accent"]
            if entry.get("id") == "draw":
                self._draw_asset_pile_holder(surface, rect, label="DRAW", value=int(entry["value"]), asset_name="draw_pile_holder", accent=accent)
                continue
            if entry.get("id") == "discard":
                self._draw_asset_pile_holder(surface, rect, label="DISCARD", value=int(entry["value"]), asset_name="discard_holder", accent=accent)
                continue
            label_surface = self._tiny_font.render(str(entry["label"]).upper(), True, accent)
            value_surface = self._small_font.render(str(entry["value"]), True, (244, 248, 255))
            surface.blit(label_surface, (rect.x, rect.y + 1))
            surface.blit(value_surface, (rect.x + label_surface.get_width() + 8, rect.y - 1))

    def _draw_asset_drift_gauge(
        self,
        surface: Any,
        rect: Any,
        *,
        protocol_drift_pct: int,
        band_index: int,
    ) -> None:
        gauge_rect = pygame.Rect(rect)
        base = combat_ui_assets.get("drift_gauge_low", gauge_rect.size)
        if base is not None:
            surface.blit(base, gauge_rect.topleft)
        segment_rects = self._drift_gauge_segment_rects(gauge_rect)
        if not segment_rects:
            return

        palette = self._protocol_drift_palette(band_index)
        empty_fill = tuple(
            max(16, min(255, int((background * 0.78) + (border * 0.22))))
            for background, border in zip(palette["background"], palette["border"])
        )
        active_fill = self._protocol_drift_bar_color(band_index)
        active_segments = self._protocol_drift_segment_count(protocol_drift_pct)
        border_radius = max(1, min(3, segment_rects[0].height // 2))

        for index, segment_rect in enumerate(segment_rects):
            is_active = index < active_segments
            color = active_fill if is_active else empty_fill
            pygame.draw.rect(surface, color, segment_rect, border_radius=border_radius)
            if is_active:
                pygame.draw.rect(surface, palette["border"], segment_rect, 1, border_radius=border_radius)

    def _protocol_drift_segment_count(self, protocol_drift_pct: int, *, segment_total: int = 20) -> int:
        if segment_total <= 0:
            return 0
        clamped_pct = max(0, min(100, int(protocol_drift_pct)))
        if clamped_pct <= 0:
            return 0
        return min(segment_total, max(1, math.ceil((clamped_pct / 100.0) * segment_total)))

    def _drift_gauge_inner_rect(self, gauge_rect: Any) -> Any:
        rect = pygame.Rect(gauge_rect)
        pad_x = max(3, int(round(rect.width * 0.18)))
        pad_top = max(6, int(round(rect.height * 0.09)))
        pad_bottom = max(8, int(round(rect.height * 0.12)))
        inner_rect = pygame.Rect(
            rect.x + pad_x,
            rect.y + pad_top,
            max(1, rect.width - (pad_x * 2)),
            max(1, rect.height - pad_top - pad_bottom),
        )
        return inner_rect

    def _drift_gauge_segment_rects(self, gauge_rect: Any, *, segment_total: int = 20) -> list[Any]:
        inner_rect = self._drift_gauge_inner_rect(gauge_rect)
        if segment_total <= 0 or inner_rect.width <= 0 or inner_rect.height <= 0:
            return []
        gap = max(1, int(round(inner_rect.height * 0.012)))
        usable_height = inner_rect.height - (gap * (segment_total - 1))
        if usable_height < segment_total:
            gap = 0
            usable_height = inner_rect.height
        segment_height = max(1, usable_height // segment_total)
        total_drawn_height = (segment_height * segment_total) + (gap * (segment_total - 1))
        start_y = inner_rect.bottom - total_drawn_height
        rects: list[Any] = []
        for index in range(segment_total):
            rects.append(
                pygame.Rect(
                    inner_rect.x,
                    start_y + ((segment_total - 1 - index) * (segment_height + gap)),
                    inner_rect.width,
                    segment_height,
                )
            )
        return rects

    def _protocol_drift_bar_color(self, band_index: int) -> tuple[int, int, int]:
        palette = self._protocol_drift_palette(band_index)
        return palette["fill"]

    def _draw_asset_pile_holder(
        self,
        surface: Any,
        rect: Any,
        *,
        label: str,
        value: int,
        asset_name: str,
        accent: tuple[int, int, int],
    ) -> None:
        holder_rect = pygame.Rect(rect)
        combat_ui_assets.blit(surface, asset_name, holder_rect)
        value_surface = self._font.render(str(value), True, (226, 242, 255))
        shadow = self._font.render(str(value), True, (0, 0, 0))
        shadow.set_alpha(150)
        center = (holder_rect.centerx, holder_rect.y + int(holder_rect.height * 0.46))
        surface.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 2)))
        surface.blit(value_surface, value_surface.get_rect(center=center))
        label_surface = self._tiny_font.render(label, True, accent)
        surface.blit(label_surface, label_surface.get_rect(center=(holder_rect.centerx, holder_rect.bottom - 17)))

    def _draw_player_actor(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool, targeted: bool) -> None:
        self._draw_player_body(surface, actor, high_contrast=high_contrast, targeted=targeted)
        self._draw_player_hud(surface, actor, high_contrast=high_contrast, targeted=targeted)

    def _draw_player_body(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool, targeted: bool) -> None:
        accent = actor["accent"]
        rect = actor["actor_rect"]
        foot_x, foot_y = actor["foot"]
        pulse = 0.76 + (0.12 * math.sin(self._now_ms() / 180.0))
        ring_color = tuple(min(255, int(channel * (1.15 if targeted else pulse))) for channel in accent)
        self._draw_ground_plate(surface, foot=(foot_x, foot_y), accent=ring_color, targeted=targeted)
        art_surface = self._player_reference_art(actor["character_id"])
        if art_surface is not None:
            base_scale = float(PLAYER_ART_REFS.get(actor["character_id"], {}).get("scale", 1.0) or 1.0)
            target_height = max(1, int(rect.height * 1.26 * base_scale))
            target_width = max(1, int(art_surface.get_width() * (target_height / max(1, art_surface.get_height()))))
            scaled_art = pygame.transform.smoothscale(art_surface, (target_width, target_height))
            if high_contrast:
                glow_rect = scaled_art.get_rect(midbottom=(foot_x + 8, foot_y + 8)).inflate(24, 18)
                glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
                pygame.draw.ellipse(glow, (*accent, 34), glow.get_rect())
                surface.blit(glow, glow_rect.topleft)
            art_rect = scaled_art.get_rect(midbottom=(foot_x - 2, foot_y + 10))
            surface.blit(scaled_art, art_rect.topleft)
        else:
            body_surface = pygame.Surface((rect.width + 22, rect.height + 22), pygame.SRCALPHA)
            self._draw_player_standee_body(body_surface, body_surface.get_rect().inflate(-22, -22).move(11, 11), actor["character_id"], accent=accent)
            surface.blit(body_surface, (rect.x - 11, rect.y - 11))

    def _draw_player_standee_body(self, surface: Any, rect: Any, character_id: str, *, accent: tuple[int, int, int]) -> None:
        outline = tuple(max(74, min(210, int((channel * 0.52) + 28))) for channel in accent)
        shadow = (18, 26, 38, 88)
        pygame.draw.ellipse(surface, shadow, pygame.Rect(rect.x + 12, rect.y + rect.height - 26, rect.width - 24, 20))
        body_color = (20, 26, 36)
        panel_color = tuple(max(42, min(124, int((channel * 0.24) + 18))) for channel in accent)

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

    def _player_reference_art(self, character_id: str) -> Any | None:
        ref = PLAYER_ART_REFS.get(character_id)
        if pygame is None or ref is None:
            return None
        path = ref.get("path")
        if not isinstance(path, Path) or not path.exists():
            return None
        cache_key = f"player_ref::{character_id}"
        cached = self._image_cache.get(cache_key)
        if cached is not None:
            return cached
        image = self._load_image(path).copy()
        crop = ref.get("crop")
        if isinstance(crop, tuple) and len(crop) == 4:
            crop_rect = pygame.Rect(*crop)
            crop_rect.clamp_ip(image.get_rect())
            image = image.subsurface(crop_rect).copy()
        colorkey = ref.get("colorkey")
        if isinstance(colorkey, tuple) and len(colorkey) == 3:
            image.set_colorkey(colorkey)
        self._strip_reference_background(image)
        self._image_cache[cache_key] = image
        return image

    def _strip_reference_background(self, image: Any) -> None:
        if pygame is None or image is None:
            return
        width, height = image.get_size()
        for x in range(width):
            for y in range(height):
                color = image.get_at((x, y))
                if color.a <= 0:
                    continue
                brightness_floor = min(color.r, color.g, color.b)
                brightness_ceiling = max(color.r, color.g, color.b)
                if brightness_floor >= 180 and (brightness_ceiling - brightness_floor) <= 40:
                    image.set_at((x, y), (color.r, color.g, color.b, 0))

    def _draw_player_hud(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool, targeted: bool) -> None:
        player = actor["player"]
        hud_rect = pygame.Rect(*actor["hud_rect"])
        accent = actor["accent"]
        del high_contrast
        combat_ui_assets.blit(surface, "hud_data_capsule", hud_rect)
        if targeted:
            pygame.draw.rect(surface, accent, hud_rect.inflate(6, 6), 2, border_radius=10)

        meter_width = max(170, min(268, hud_rect.width - 116))
        hp_bar_rect = pygame.Rect(hud_rect.x + 28, hud_rect.y + 16, meter_width, 14)
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
        self._draw_energy_row(
            surface,
            rect=(hud_rect.x + 28, hud_rect.y + 40, max(160, min(236, meter_width)), 28),
            current=int(player["energy"]),
            maximum=max(1, int(player["max_energy"])),
            unstable_current=int(player.get("unstable_energy", 0) or 0),
        )

        if int(player.get("block", 0) or 0) > 0:
            self._draw_block_chip(
                surface,
                rect=actor["block_rect"],
                value=int(player["block"]),
                accent=(104, 190, 255),
                flash_key=actor.get("feedback_key"),
            )
        self._draw_text(
            surface,
            actor["name"],
            (hud_rect.x + 28, hud_rect.y + 60),
            self._tiny_font,
            width=meter_width,
        )
        self._draw_status_row(surface, actor["status_regions"])

    def _draw_protocol_drift_meter(
        self,
        surface: Any,
        *,
        rect: tuple[int, int, int, int],
        protocol_drift_pct: int,
        band_index: int,
        band_label: str,
        high_contrast: bool,
    ) -> None:
        drift_rect = pygame.Rect(*rect)
        palette = self._protocol_drift_palette(band_index)
        background = palette["background"]
        border = (224, 236, 255) if high_contrast else palette["border"]
        fill = palette["fill"]
        self._draw_panel(surface, drift_rect, fill=background, border=border, radius=10)
        inner_rect = drift_rect.inflate(-4, -4)
        if inner_rect.width > 0 and inner_rect.height > 0 and protocol_drift_pct > 0:
            fill_width = max(1, int(inner_rect.width * (protocol_drift_pct / 100.0)))
            pygame.draw.rect(
                surface,
                fill,
                pygame.Rect(inner_rect.x, inner_rect.y, fill_width, inner_rect.height),
                border_radius=max(2, inner_rect.height // 2),
            )
        label = f"DRIFT {protocol_drift_pct}%"
        if protocol_drift_pct <= 0:
            label = "DRIFT 0%"
        label_surface = self._tiny_font.render(label, True, (236, 242, 250))
        surface.blit(label_surface, label_surface.get_rect(center=drift_rect.center))
        del band_label

    def _protocol_drift_palette(self, band_index: int) -> dict[str, tuple[int, int, int]]:
        palettes = (
            {"fill": (86, 112, 140), "border": (128, 152, 178), "background": (18, 26, 40)},
            {"fill": (82, 170, 186), "border": (112, 206, 220), "background": (14, 30, 40)},
            {"fill": (98, 156, 224), "border": (126, 188, 246), "background": (14, 24, 42)},
            {"fill": (224, 152, 86), "border": (242, 186, 114), "background": (30, 20, 16)},
            {"fill": (236, 104, 122), "border": (255, 148, 168), "background": (38, 14, 24)},
            {"fill": (255, 76, 108), "border": (255, 138, 158), "background": (42, 10, 18)},
        )
        return palettes[max(0, min(len(palettes) - 1, band_index))]

    def _draw_enemy_actor(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool) -> None:
        self._draw_enemy_body(surface, actor, high_contrast=high_contrast)
        self._draw_enemy_overlay(surface, actor, high_contrast=high_contrast)

    def _draw_enemy_body(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool) -> None:
        del high_contrast
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

    def _draw_enemy_overlay(self, surface: Any, actor: dict[str, Any], *, high_contrast: bool) -> None:
        enemy = actor["enemy"]
        self._draw_intent_banner(surface, actor, high_contrast=high_contrast)
        name_rect = actor.get("name_rect")
        if name_rect is not None:
            self._draw_text(surface, actor["name"], (name_rect[0], name_rect[1]), self._small_font, width=name_rect[2])
        else:
            rect = actor["actor_rect"]
            self._draw_text(surface, actor["name"], (rect.x - 12, actor["hp_bar_rect"][1] - 18), self._small_font, width=rect.width + 24)
        self._draw_enemy_hp(surface, actor)
        if int(enemy.get("block", 0) or 0) > 0:
            self._draw_block_chip(
                surface,
                rect=actor["block_rect"],
                value=int(enemy["block"]),
                accent=(112, 188, 255),
                flash_key=actor.get("feedback_key"),
            )
        self._draw_status_row(surface, actor["status_regions"])

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
            self._reset_feedback_state()
            return

        enemies = list(after_combat.get("enemies", []))
        self._sync_enemy_visual_registry(enemies)

        feedback_events = [
            event for event in after_combat.get("feedback_events", [])
            if isinstance(event, dict)
        ]
        max_sequence = max((int(event.get("sequence", 0) or 0) for event in feedback_events), default=0)
        if before_combat is None or max_sequence < self._last_feedback_sequence:
            self._reset_feedback_state()
        new_feedback = [
            event
            for event in feedback_events
            if int(event.get("sequence", 0) or 0) > self._last_feedback_sequence
        ]
        self._consume_feedback_events(new_feedback)
        self._last_feedback_sequence = max_sequence
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

    def _reset_feedback_state(self) -> None:
        self._last_feedback_sequence = 0
        self._relic_flash_registry.clear()
        self._shield_flash_registry.clear()
        self._floating_feedback.clear()
        self._proc_ticker_entries.clear()

    def _consume_feedback_events(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        ordered_events = sorted(events, key=lambda event: int(event.get("sequence", 0) or 0))
        now = self._now_ms()
        pending_relic_start = self._latest_relic_flash_start(now)

        for event in ordered_events:
            event_type = str(event.get("type", "")).strip().lower()
            if event_type == "relic_triggered":
                if pending_relic_start < now:
                    start_at = now
                else:
                    start_at = pending_relic_start + RELIC_FLASH_STAGGER_MS
                pending_relic_start = start_at
                self._queue_relic_flash(event, start_at)
                self._queue_proc_ticker(event, start_at)
                continue

            if event_type == "damage_applied":
                hp_damage = max(0, int(event.get("hp_damage", event.get("amount", 0)) or 0))
                blocked_amount = max(0, int(event.get("blocked_amount", 0) or 0))
                if hp_damage > 0:
                    self._queue_floating_feedback(
                        target_key=self._feedback_actor_key(event, "target"),
                        label=f"-{hp_damage}",
                        color=(236, 92, 106),
                        started_at=now,
                        sequence=int(event.get("sequence", 0) or 0),
                    )
                elif blocked_amount > 0:
                    self._queue_floating_feedback(
                        target_key=self._feedback_actor_key(event, "target"),
                        label=f"-{blocked_amount}",
                        color=(172, 178, 192),
                        started_at=now,
                        sequence=int(event.get("sequence", 0) or 0),
                    )
                continue

            if event_type == "heal_applied":
                amount = max(0, int(event.get("amount", 0) or 0))
                if amount > 0:
                    self._queue_floating_feedback(
                        target_key=self._feedback_actor_key(event, "target"),
                        label=f"+{amount}",
                        color=(110, 230, 150),
                        started_at=now,
                        sequence=int(event.get("sequence", 0) or 0),
                    )
                continue

            if event_type == "block_gained":
                amount = max(0, int(event.get("amount", 0) or 0))
                if amount > 0:
                    self._queue_floating_feedback(
                        target_key=self._feedback_actor_key(event, "target"),
                        label=f"+{amount}",
                        color=(108, 196, 255),
                        started_at=now,
                        sequence=int(event.get("sequence", 0) or 0),
                    )
                continue

            if event_type == "block_spent" and str(event.get("reason", "")) != "damage_absorbed":
                amount = max(0, int(event.get("amount", 0) or 0))
                if amount > 0:
                    self._queue_floating_feedback(
                        target_key=self._feedback_actor_key(event, "target"),
                        label=f"-{amount}",
                        color=(172, 178, 192),
                        started_at=now,
                        sequence=int(event.get("sequence", 0) or 0),
                    )
                continue

            if event_type == "shield_flash":
                self._queue_shield_flash(self._feedback_actor_key(event, "target"), started_at=now)

    def _latest_relic_flash_start(self, default_start: int) -> int:
        latest = default_start - RELIC_FLASH_STAGGER_MS
        for pulses in self._relic_flash_registry.values():
            for pulse in pulses:
                latest = max(latest, int(pulse.get("started_at", latest)))
        return latest

    def _queue_relic_flash(self, event: dict[str, Any], started_at: int) -> None:
        relic_id = str(event.get("relic_id", "")).strip()
        if not relic_id:
            return
        self._relic_flash_registry.setdefault(relic_id, []).append(
            {
                "started_at": int(started_at),
                "sequence": int(event.get("sequence", 0) or 0),
            }
        )

    def _queue_proc_ticker(self, event: dict[str, Any], started_at: int) -> None:
        relic_name = str(event.get("relic_name", "Relic")).strip() or "Relic"
        trigger_hook = str(event.get("trigger_hook", "")).strip()
        trigger_text = HOOK_LABELS.get(trigger_hook, trigger_hook.replace("_", " ").title()).strip() if trigger_hook else "Trigger"
        detail = trigger_text
        card_id = str(event.get("card_id", "")).strip()
        if card_id:
            detail = f"{detail} · {card_id.replace('_', ' ').title()}"
        self._proc_ticker_entries.append(
            {
                "label": relic_name,
                "detail": detail,
                "combo_index": max(0, int(event.get("combo_index", 0) or 0)),
                "started_at": int(started_at),
            }
        )

    def _queue_floating_feedback(
        self,
        *,
        target_key: str | None,
        label: str,
        color: tuple[int, int, int],
        started_at: int,
        sequence: int,
    ) -> None:
        if target_key is None or not label:
            return
        self._floating_feedback.append(
            {
                "target_key": target_key,
                "label": label,
                "color": color,
                "started_at": int(started_at),
                "sequence": int(sequence),
                "phase": (int(sequence) % 7) * 0.58,
            }
        )

    def _queue_shield_flash(self, target_key: str | None, *, started_at: int) -> None:
        if target_key is None:
            return
        self._shield_flash_registry.setdefault(target_key, []).append({"started_at": int(started_at)})

    def _feedback_actor_key(self, event: dict[str, Any], prefix: str) -> str | None:
        enemy_ref = event.get(f"{prefix}_enemy_ref")
        if isinstance(enemy_ref, str) and enemy_ref:
            return enemy_ref
        actor_id = event.get(f"{prefix}_id")
        actor_type = event.get(f"{prefix}_type")
        if actor_type == "player" or actor_id == "player":
            return "player"
        if isinstance(actor_id, str) and actor_id:
            return actor_id
        return None

    def _feedback_actor_lookup(self, layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        player_actor = layout.get("player_actor")
        if isinstance(player_actor, dict):
            lookup["player"] = player_actor
        for actor in layout.get("enemy_actors", []):
            if not isinstance(actor, dict):
                continue
            enemy_ref = actor.get("enemy_ref")
            enemy_id = actor.get("id")
            feedback_key = actor.get("feedback_key")
            for key in (feedback_key, enemy_ref, enemy_id):
                if isinstance(key, str) and key and key not in lookup:
                    lookup[key] = actor
        return lookup

    def _feedback_anchor(self, actor_lookup: dict[str, dict[str, Any]], actor_key: str) -> tuple[int, int] | None:
        actor = actor_lookup.get(actor_key)
        if actor is None and "#" in actor_key:
            actor = actor_lookup.get(actor_key.split("#", 1)[0])
        if actor is None:
            return None
        anchor = actor.get("feedback_anchor")
        if isinstance(anchor, tuple) and len(anchor) == 2:
            return int(anchor[0]), int(anchor[1])
        actor_rect = actor.get("actor_rect")
        if actor_rect is not None:
            return actor_rect.centerx, actor_rect.y
        return None

    def _shield_flash_intensity(self, actor_key: str) -> float:
        now = self._now_ms()
        intensity = 0.0
        for pulse in self._shield_flash_registry.get(actor_key, []):
            elapsed = now - int(pulse.get("started_at", now))
            if elapsed < 0 or elapsed > SHIELD_FLASH_MS:
                continue
            if elapsed <= 90:
                local_intensity = elapsed / 90.0
            else:
                local_intensity = 1.0 - ((elapsed - 90) / max(1, SHIELD_FLASH_MS - 90))
            intensity = max(intensity, max(0.0, min(1.0, local_intensity)))
        return intensity

    def _relic_flash_intensity(self, relic_id: str) -> float:
        now = self._now_ms()
        intensity = 0.0
        for pulse in self._relic_flash_registry.get(relic_id, []):
            elapsed = now - int(pulse.get("started_at", now))
            if elapsed < 0 or elapsed > RELIC_FLASH_TOTAL_MS:
                continue
            if elapsed <= RELIC_FLASH_RAMP_MS:
                local_intensity = elapsed / max(1, RELIC_FLASH_RAMP_MS)
            elif elapsed <= RELIC_FLASH_HOLD_MS:
                local_intensity = 1.0
            else:
                local_intensity = 1.0 - (
                    (elapsed - RELIC_FLASH_HOLD_MS) / max(1, RELIC_FLASH_TOTAL_MS - RELIC_FLASH_HOLD_MS)
                )
            intensity = max(intensity, max(0.0, min(1.0, local_intensity)))
        return intensity

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
        core_alpha = 44 if dimmed else 78
        pygame.draw.ellipse(ring_surface, (0, 0, 0, 118), ring_surface.get_rect().inflate(-6, -4))
        pygame.draw.ellipse(ring_surface, (*accent, core_alpha), ring_surface.get_rect())
        outline_color = (255, 88, 88) if targeted else accent
        outline_alpha = 200 if targeted else (130 if not dimmed else 64)
        pygame.draw.ellipse(ring_surface, (*outline_color, outline_alpha), ring_surface.get_rect(), 3)
        pygame.draw.line(ring_surface, (*outline_color, outline_alpha), (8, rect.height // 2), (28, rect.height // 2), 2)
        pygame.draw.line(ring_surface, (*outline_color, outline_alpha), (rect.width - 28, rect.height // 2), (rect.width - 8, rect.height // 2), 2)
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
        pygame.draw.rect(surface, background, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, 2, border_radius=4)
        maximum = max(1, maximum)
        current = max(0, min(current, maximum))
        preview_loss = max(0, min(preview_loss, current))
        inner_rect = pygame.Rect(rect.x + 2, rect.y + 2, max(0, rect.width - 4), max(0, rect.height - 4))
        current_width = max(0, int(inner_rect.width * (current / maximum)))
        if current_width > 0 and inner_rect.width > 0 and inner_rect.height > 0:
            fill_surface = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
            fill_rect = pygame.Rect(0, 0, current_width, inner_rect.height)
            radius = 3
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

    def _draw_energy_row(
        self,
        surface: Any,
        *,
        rect: tuple[int, int, int, int],
        current: int,
        maximum: int,
        unstable_current: int = 0,
    ) -> None:
        row_rect = pygame.Rect(*rect)
        self._draw_text(surface, "ENERGY", (row_rect.x, row_rect.y + 2), self._tiny_font, width=60)
        pip_x = row_rect.x + 66
        for index in range(maximum):
            pip_rect = pygame.Rect(pip_x + (index * 18), row_rect.y + 1, 14, 14)
            filled = index < current
            color = (104, 216, 255) if filled else (32, 54, 72)
            border = (182, 228, 255) if filled else (94, 112, 136)
            points = [
                (pip_rect.centerx, pip_rect.y),
                (pip_rect.right - 2, pip_rect.y + 4),
                (pip_rect.right - 2, pip_rect.bottom - 4),
                (pip_rect.centerx, pip_rect.bottom),
                (pip_rect.x + 2, pip_rect.bottom - 4),
                (pip_rect.x + 2, pip_rect.y + 4),
            ]
            if filled:
                glow = pygame.Surface((pip_rect.width + 10, pip_rect.height + 10), pygame.SRCALPHA)
                pygame.draw.polygon(glow, (*color, 62), [(x - pip_rect.x + 5, y - pip_rect.y + 5) for x, y in points])
                surface.blit(glow, (pip_rect.x - 5, pip_rect.y - 5))
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, border, points, 2)
        if unstable_current > 0:
            unstable_label = self._micro_font.render("UNSTABLE", True, (255, 170, 110))
            surface.blit(unstable_label, (row_rect.x, row_rect.y + 15))
            unstable_x = pip_x
            for index in range(unstable_current):
                pip_rect = pygame.Rect(unstable_x + (index * 18), row_rect.y + 15, 14, 10)
                points = [
                    (pip_rect.centerx, pip_rect.y),
                    (pip_rect.right - 2, pip_rect.y + 3),
                    (pip_rect.right - 2, pip_rect.bottom - 2),
                    (pip_rect.centerx, pip_rect.bottom),
                    (pip_rect.x + 2, pip_rect.bottom - 2),
                    (pip_rect.x + 2, pip_rect.y + 3),
                ]
                pygame.draw.polygon(surface, (255, 118, 92), points)
                pygame.draw.polygon(surface, (255, 202, 130), points, 2)

    def _draw_block_chip(
        self,
        surface: Any,
        *,
        rect: tuple[int, int, int, int],
        value: int,
        accent: tuple[int, int, int],
        flash_key: str | None = None,
    ) -> None:
        chip_rect = pygame.Rect(*rect)
        flash_intensity = 0.0 if flash_key is None else self._shield_flash_intensity(flash_key)
        if flash_intensity > 0.0:
            glow_rect = chip_rect.inflate(14, 12)
            glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            glow_alpha = int(_lerp(0, 130, flash_intensity))
            pygame.draw.ellipse(glow, (120, 204, 255, glow_alpha), glow.get_rect())
            surface.blit(glow, glow_rect.topleft)
        fill = (
            int(_lerp(12, 68, flash_intensity)),
            int(_lerp(18, 108, flash_intensity)),
            int(_lerp(28, 166, flash_intensity)),
            232,
        )
        border = tuple(min(255, int(_lerp(channel, 255, flash_intensity * 0.75))) for channel in accent)
        draw_clipped_panel(surface, chip_rect, fill=fill, border=border, cut=9, border_width=2, shadow=False)
        icon_color = tuple(min(255, int(_lerp(channel, 248, flash_intensity * 0.65))) for channel in accent)
        self._draw_shield_icon(surface, pygame.Rect(chip_rect.x + 8, chip_rect.y + 6, 18, 18), icon_color)
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
        del high_contrast
        intent = actor["enemy"].get("intent_display", {})
        rect = pygame.Rect(*actor["intent_rect"])
        kind = intent.get("kind", "wait")
        icon_rect = pygame.Rect(rect.x + 13, rect.y + 8, 18, 18)
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
                self._draw_sword_icon(surface, pygame.Rect(icon_rect.x + (index * 15), icon_rect.y + 1, 17, 17), (255, 112, 112))
            damage_x = rect.x + 44 + ((icon_count - 1) * 15)
            self._draw_text(surface, str(intent.get("damage_per_hit", 0)), (damage_x, rect.y + 5), self._small_font)
            if hit_count > 1:
                self._draw_text(surface, f"x{hit_count}", (damage_x + 28, rect.y + 8), self._tiny_font)
        elif kind == "defend":
            self._draw_shield_icon(surface, icon_rect, (116, 198, 255))
            self._draw_text(surface, str(intent.get("block", 0)), (rect.x + 44, rect.y + 5), self._small_font)
        elif kind == "summon":
            self._draw_summon_icon(surface, icon_rect, (202, 146, 255))
            self._draw_text(surface, str(intent.get("summon_count", 0)), (rect.x + 44, rect.y + 5), self._small_font)
        elif kind == "buff":
            self._draw_buff_icon(surface, icon_rect, (106, 234, 170))
        elif primary_icon_effect is not None:
            self._blit_status_icon(surface, str(primary_icon_effect["icon_id"]), icon_rect)
            self._draw_text(surface, str(primary_icon_effect.get("count", 1)), (rect.x + 44, rect.y + 5), self._small_font)
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

        chip_x = rect.right - 8
        for chip in reversed(chip_entries[:3]):
            if chip["chip_type"] == "icon":
                chip_width = max(34, 22 + self._tiny_font.size(str(chip["count"]))[0])
                chip_rect = pygame.Rect(chip_x - chip_width, rect.y + 7, chip_width, 20)
                self._draw_intent_icon_chip(surface, chip_rect, str(chip["icon_id"]), int(chip["count"]))
            else:
                label = str(chip["label"])
                chip_width = 36 if len(label) <= 2 else 42
                chip_rect = pygame.Rect(chip_x - chip_width, rect.y + 7, chip_width, 20)
                self._draw_intent_glyph_chip(surface, chip_rect, label, chip["color"], str(chip["glyph_kind"]))
            chip_x = chip_rect.x - 6

    def _draw_intent_icon_chip(self, surface: Any, rect: Any, icon_id: str, count: int) -> None:
        chip_rect = pygame.Rect(rect)
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
            scale = float(card.get("draw_scale", 1.0))
            center = card.get("draw_center", card["center"])
            alpha = 128 if layout["selected_card"] is not None else int(card.get("draw_alpha", 255))
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
                alpha=alpha,
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
            pill_rect = rect.inflate(10, 6)
            pill = pygame.Surface(pill_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(pill, (10, 16, 26, 168), pill.get_rect(), border_radius=10)
            pygame.draw.rect(pill, (98, 120, 154, 152), pill.get_rect(), 1, border_radius=10)
            surface.blit(pill, pill_rect.topleft)
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
        label_color = (255, 230, 122) if self._pressed_end_turn else (234, 244, 255)
        if bool(layout["end_turn_hovered"]):
            label_color = (255, 246, 190)
            pygame.draw.line(surface, WARNING_ORANGE, (button_rect.x + 28, button_rect.bottom - 8), (button_rect.right - 28, button_rect.bottom - 8), 2)
        shadow = self._font.render("END TURN", True, (0, 0, 0))
        shadow.set_alpha(180)
        label = self._font.render("END TURN", True, label_color)
        surface.blit(shadow, shadow.get_rect(center=(button_rect.centerx + 2, button_rect.centery - 4)))
        surface.blit(label, label.get_rect(center=(button_rect.centerx, button_rect.centery - 6)))
        hint = self._tiny_font.render("SPACE", True, CYAN)
        surface.blit(hint, hint.get_rect(center=(button_rect.centerx, button_rect.centery + 18)))

    def _draw_layout_debug(self, surface: Any, layout: dict[str, Any]) -> None:
        regions = layout.get("layout_regions", {})
        if not isinstance(regions, dict):
            return
        palette = [
            (104, 216, 255),
            (255, 214, 110),
            (232, 106, 112),
            (110, 230, 150),
            (188, 162, 255),
            (255, 154, 36),
        ]
        for index, (name, rect_tuple) in enumerate(regions.items()):
            rect = pygame.Rect(*rect_tuple)
            color = palette[index % len(palette)]
            pygame.draw.rect(surface, color, rect, 1)
            label = self._tiny_font.render(name, True, color)
            label_bg = pygame.Surface((label.get_width() + 6, label.get_height() + 4), pygame.SRCALPHA)
            label_bg.fill((2, 6, 12, 190))
            surface.blit(label_bg, (rect.x + 2, rect.y + 2))
            surface.blit(label, (rect.x + 5, rect.y + 4))

        for card in layout.get("hand_cards", []):
            pygame.draw.rect(surface, (255, 255, 255), pygame.Rect(*card["hit_rect"]), 1)

    def _validate_layout(self, layout: dict[str, Any]) -> None:
        combat_layout = layout.get("combat_layout")
        if not isinstance(combat_layout, CombatLayout):
            return
        warnings = self._layout_warnings(layout)
        signature = tuple(sorted(set(warnings)))
        if signature and signature != self._last_layout_warning_signature:
            LOGGER.warning("Combat layout warnings: %s", " | ".join(signature))
        self._last_layout_warning_signature = signature or None

    def _layout_warnings(self, layout: dict[str, Any]) -> list[str]:
        combat_layout = layout.get("combat_layout")
        if not isinstance(combat_layout, CombatLayout):
            return []
        warnings: list[str] = []
        safe_rect = combat_layout.safe_rect
        hand_rect = combat_layout.hand_rect
        card_rects = [tuple(card["hit_rect"]) for card in layout.get("hand_cards", []) if "hit_rect" in card]
        if card_rects:
            hand_union = self._rect_union(card_rects)
            if not self._rect_contains(safe_rect, hand_union):
                warnings.append("card hand leaves safe_rect")
            for index, rect in enumerate(card_rects):
                if not self._rect_contains(safe_rect, rect):
                    warnings.append(f"card {index} leaves safe_rect")
            for name, rect in (
                ("player_status_rect", combat_layout.player_status_rect),
                ("deck_discard_rect", combat_layout.deck_discard_rect),
                ("end_turn_rect", combat_layout.end_turn_rect),
                ("exhaust_rect", combat_layout.exhaust_rect),
            ):
                if self._rects_intersect(hand_union, rect):
                    warnings.append(f"card hand intersects {name}")
        if self._rects_intersect(combat_layout.end_turn_rect, hand_rect):
            warnings.append("end_turn_rect intersects hand_rect")
        for enemy in layout.get("enemy_actors", []):
            for name in ("name_rect", "hp_bar_rect"):
                rect = enemy.get(name)
                if rect is not None and self._rects_intersect(tuple(rect), hand_rect):
                    warnings.append(f"enemy {enemy.get('id', '?')} {name} intersects hand_rect")
                if rect is not None:
                    for index, card_rect in enumerate(card_rects):
                        if self._rects_intersect(tuple(rect), card_rect):
                            warnings.append(f"enemy {enemy.get('id', '?')} {name} intersects card {index}")
        selected_card = layout.get("selected_card")
        if isinstance(selected_card, dict):
            selected_rect = tuple(selected_card.get("center_rect", (0, 0, 0, 0)))
            if not self._rect_contains(safe_rect, selected_rect):
                warnings.append("selected_card leaves safe_rect")
            if self._rects_intersect(selected_rect, combat_layout.top_hud_rect):
                warnings.append("selected_card intersects top_hud_rect")
        return warnings

    def _resolve_surface_size(self, surface_size: tuple[int, int] | None) -> tuple[int, int]:
        if surface_size is None:
            return self._last_surface_size
        width = max(640, int(surface_size[0]))
        height = max(360, int(surface_size[1]))
        self._last_surface_size = (width, height)
        return self._last_surface_size

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
            actor_rect = enemy["actor_rect"].inflate(30, 34)
            if point_in_rect(position, (actor_rect.x, actor_rect.y, actor_rect.width, actor_rect.height)):
                return enemy["id"]
            if (
                point_in_rect(position, enemy["intent_rect"])
                or point_in_rect(position, enemy["hp_bar_rect"])
                or point_in_rect(position, enemy["block_rect"])
            ):
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

    def _fit_single_line(self, text: str, font: Any, width: int) -> str:
        text = str(text)
        if font is None or width <= 0 or font.size(text)[0] <= width:
            return text
        ellipsis = "..."
        if font.size(ellipsis)[0] > width:
            return ""
        fitted = text
        while fitted and font.size(f"{fitted}{ellipsis}")[0] > width:
            fitted = fitted[:-1]
        return f"{fitted.rstrip()}{ellipsis}" if fitted else ellipsis

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
