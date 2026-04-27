from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.card_renderer import draw_card
from ui.event_assets import EVENT_UI_ASSET_ROOT, event_ui_assets
from ui.render_utils import clamp_scale, point_in_rect
from ui.ui_system import draw_background_stage


EVENT_LAYOUT = {
    "shell_rect": (74, 94, 1132, 596),
    "purge_columns": 2,
    "purge_gap_x": 10,
    "purge_gap_y": 8,
}

COLOR_TEXT = (232, 241, 250)
COLOR_TEXT_DIM = (135, 148, 164)
COLOR_TEXT_MUTED = (166, 187, 205)
COLOR_CYAN = (55, 211, 255)
COLOR_GOLD = (255, 209, 90)
COLOR_RED = (255, 74, 95)
COLOR_GREEN = (104, 224, 112)
COLOR_BLUE = (72, 180, 232)
COLOR_PURPLE = (177, 88, 255)
COLOR_ORANGE = (255, 154, 36)
COLOR_RELIC = (183, 244, 255)


class EventGlyphResolver:
    TAG_GLYPHS = (
        ({"corruption", "anomaly"}, "corruption"),
        ({"curse", "debt", "marked"}, "curse"),
        ({"attack", "strength", "bleed", "burn", "self_damage"}, "damage"),
        ({"recovery", "heal", "cleanse"}, "healing"),
        ({"defense", "block", "enemy_status"}, "defense"),
        ({"economy", "shop", "merchant_style", "tradeoff"}, "credits"),
        ({"relic", "boss_relic"}, "relic"),
        ({"deck_edit", "draw", "discard", "exhaust", "zero_cost"}, "deck"),
        ({"gamble", "risk"}, "gamble"),
        ({"blessing"}, "blessing"),
        ({"chain", "special", "narrative"}, "chain"),
        ({"infect", "status_risk"}, "curse"),
    )

    def category_for_choice(self, choice: dict[str, Any], event_tags: list[str]) -> str:
        text = f"{choice.get('label', '')} {choice.get('description', '')}".lower()
        effect_types = self._effect_types(choice)
        if choice.get("choice_type") == "risk":
            return "gamble"
        if choice.get("choice_type") == "purge":
            return "deck"
        if "protocol drift" in text or "corruption" in text or "glitch" in text or "adjust_protocol_drift" in effect_types:
            return "corruption"
        if {"damage", "lose_hp", "self_damage"}.intersection(effect_types) or any(word in text for word in ("damage", "bleed", "burn", "overheat")):
            return "damage"
        if {"gain_credits", "lose_credits"}.intersection(effect_types) or "credit" in text or "spend" in text:
            return "credits"
        if "heal" in effect_types or "heal" in text or "restore" in text:
            return "healing"
        if "gain_block" in effect_types or "block" in text or "plating" in text:
            return "defense"
        if {"gain_card", "remove_card_from_deck_by_id", "purge_card"}.intersection(effect_types) or any(word in text for word in ("card", "deck", "draw", "discard")):
            return "deck"
        if {"gain_modifier", "gain_random_modifier", "remove_modifier"}.intersection(effect_types) or "relic" in text:
            return "relic"
        for tag_group, glyph in self.TAG_GLYPHS:
            if tag_group.intersection(event_tags):
                return glyph
        return "chain"

    def _effect_types(self, choice: dict[str, Any]) -> set[str]:
        types: set[str] = set()
        for effect in list(choice.get("effects") or []):
            if not isinstance(effect, dict):
                continue
            effect_type = str(effect.get("type", ""))
            if effect_type:
                types.add(effect_type)
            queued = effect.get("effect")
            if isinstance(queued, dict):
                queued_type = str(queued.get("type", ""))
                if queued_type:
                    types.add(queued_type)
        for outcome in list(choice.get("outcomes") or []):
            if not isinstance(outcome, dict):
                continue
            for effect in list(outcome.get("effects") or []):
                if isinstance(effect, dict) and effect.get("type"):
                    types.add(str(effect["type"]))
        return types


class EventChoiceTextFormatter:
    PATTERNS: tuple[tuple[re.Pattern[str], tuple[int, int, int]], ...] = (
        (
            re.compile(
                r"(?:Increase|Reduce|Apply|Gain)?\s*Protocol Drift(?:\s*(?:by)?\s*\d+%?)?|\b[+-]?\d+%?\s*Drift\b|\bSystem Corruption\b|\bCorruption\b|\bGlitch(?:es)?\b",
                re.IGNORECASE,
            ),
            COLOR_PURPLE,
        ),
        (re.compile(r"\b(?:Gain|Spend|Lose|Pay)\s+\d+\s*(?:credits?|cr)\b|\b\d+\s*(?:credits?|cr)\b", re.IGNORECASE), COLOR_GOLD),
        (re.compile(r"\b(?:Heal|Restore|Recover)\s+\d+(?:\s*HP)?\b", re.IGNORECASE), COLOR_GREEN),
        (re.compile(r"\b(?:Take|Lose|Suffer)\s+\d+(?:\s*(?:damage|HP))?\b|\b\d+\s*damage\b", re.IGNORECASE), COLOR_RED),
        (re.compile(r"\b(?:Gain|start with|with)\s+\d+\s*Block\b|\b\d+\s*Block\b", re.IGNORECASE), COLOR_CYAN),
        (re.compile(r"\b(?:Draw|Discard|Purge|Remove|Add)\s+(?:\d+\s+)?(?:deck\s+)?cards?\b|\bdeck\b|\bcards?\b", re.IGNORECASE), COLOR_BLUE),
        (re.compile(r"\b(?:Burn|Infect|Marked|Suppressed|Nullified|Bleed|Overheat|Debt Mark|Debt Spike)\b", re.IGNORECASE), COLOR_ORANGE),
        (re.compile(r"\b(?:Blessing|Favor)\b", re.IGNORECASE), (235, 222, 154)),
        (re.compile(r"\b(?:Gain|Install|Refresh|Remove)\s+(?!\d)(?:[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\b"), COLOR_RELIC),
    )

    def draw(
        self,
        surface: Any,
        text: str,
        rect: Any,
        font: Any,
        *,
        enabled: bool,
        base_color: tuple[int, int, int] = COLOR_TEXT_MUTED,
        max_lines: int = 2,
    ) -> None:
        if pygame is None or not text:
            return
        target_rect = pygame.Rect(rect)
        if target_rect.width <= 0 or target_rect.height <= 0:
            return
        spans = self._spans(text, base_color, enabled=enabled)
        line_height = max(12, font.get_linesize())
        x = target_rect.x
        y = target_rect.y
        lines = 1
        for span_text, color in spans:
            for token in re.findall(r"\S+\s*|\s+", span_text):
                if not token:
                    continue
                token_width = font.size(token)[0]
                if x > target_rect.x and x + token_width > target_rect.right:
                    lines += 1
                    if lines > max_lines:
                        return
                    x = target_rect.x
                    y += line_height
                if y + line_height > target_rect.bottom:
                    return
                rendered = font.render(token, True, color)
                surface.blit(rendered, (x, y))
                x += rendered.get_width()

    def _spans(
        self,
        text: str,
        base_color: tuple[int, int, int],
        *,
        enabled: bool,
    ) -> list[tuple[str, tuple[int, int, int]]]:
        spans: list[tuple[str, tuple[int, int, int]]] = []
        index = 0
        while index < len(text):
            match_data: tuple[re.Match[str], tuple[int, int, int]] | None = None
            for pattern, color in self.PATTERNS:
                candidate = pattern.search(text, index)
                if candidate is None:
                    continue
                if match_data is None or candidate.start() < match_data[0].start():
                    match_data = (candidate, color)
            if match_data is None:
                spans.append((text[index:], self._maybe_dim(base_color, enabled)))
                break
            match, color = match_data
            if match.start() > index:
                spans.append((text[index:match.start()], self._maybe_dim(base_color, enabled)))
            spans.append((match.group(0), self._maybe_dim(color, enabled)))
            index = match.end()
        return spans

    def _maybe_dim(self, color: tuple[int, int, int], enabled: bool) -> tuple[int, int, int]:
        if enabled:
            return color
        return tuple(max(70, int(channel * 0.55)) for channel in color)


class EventUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._micro_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None
        self._glyph_resolver = EventGlyphResolver()
        self._text_formatter = EventChoiceTextFormatter()

    def preload_assets(self) -> None:
        if pygame is None:
            return
        event_ui_assets.preload()
        self._load_image(resolve_asset_path("ui", "bg_map.png"))

    def handle_event(self, event: Any, event_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self.build_layout(event_state)

        if event.type == pygame.MOUSEMOTION:
            self._hovered_action = self._action_at_position(layout, event.pos)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed_action = self._action_at_position(layout, event.pos)
            return None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            action_id = self._action_at_position(layout, event.pos)
            pressed_action = self._pressed_action
            self._pressed_action = None
            if action_id is None or action_id != pressed_action:
                return None
            return self._event_for_action(action_id, layout)
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_c and layout["can_continue"]:
            return {"type": "continue_from_event"}
        if pygame.K_1 <= event.key <= pygame.K_9:
            choice_index = event.key - pygame.K_1
            shortcut_choices = layout["shortcut_choices"]
            if choice_index >= len(shortcut_choices):
                return {"type": "notice", "message": "That event option is empty.", "level": "error"}
            choice = shortcut_choices[choice_index]
            if not choice["available"]:
                return {"type": "notice", "message": choice["disabled_reason"], "level": "error"}
            return {"type": "select_event_choice", "choice_id": choice["id"]}
        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if layout["can_continue"]:
                return {"type": "continue_from_event"}
            if layout["selected_choice"] is None:
                return {"type": "notice", "message": "Select an event choice before confirming it.", "level": "error"}
            if not layout["selected_choice"]["available"]:
                return {"type": "notice", "message": layout["selected_choice"]["disabled_reason"], "level": "error"}
            if not layout["can_confirm"]:
                return {"type": "notice", "message": "Choose a deck card target before confirming this choice.", "level": "error"}
            return {"type": "confirm_event_choice"}
        return None

    def build_layout(self, event_state: dict[str, Any]) -> dict[str, Any]:
        event = event_state["event"]
        shell_rect = pygame.Rect(*EVENT_LAYOUT["shell_rect"]) if pygame is not None else _Rect(*EVENT_LAYOUT["shell_rect"])
        dossier_rect = self._relative_rect(shell_rect, 0.0, 0.0, 0.515, 1.0)
        art_frame_rect = self._relative_rect(shell_rect, 0.515, 0.0, 0.485, 0.745)
        art_inner_rect = self._relative_rect(shell_rect, 0.548, 0.060, 0.415, 0.610)
        confirm_rect = self._relative_rect(shell_rect, 0.790, 0.812, 0.170, 0.083)
        secret_rect = self._relative_rect(shell_rect, 0.785, 0.905, 0.182, 0.066)
        hint_rect = self._relative_rect(dossier_rect, 0.115, 0.875, 0.775, 0.060)
        title_rect = self._relative_rect(dossier_rect, 0.115, 0.088, 0.765, 0.080)
        body_rect = self._relative_rect(dossier_rect, 0.120, 0.390, 0.760, 0.110)
        accent_yellow_rect = self._relative_rect(dossier_rect, 0.145, 0.255, 0.360, 0.022)
        accent_cyan_rect = self._relative_rect(dossier_rect, 0.145, 0.290, 0.270, 0.018)

        event_tags = list(event.get("tags") or [])
        choices = []
        secret_choice_id = self._secret_choice_id(event)
        normal_source_choices = [
            choice for choice in event["choices"] if choice["id"] != secret_choice_id
        ]
        normal_count = max(1, len(normal_source_choices))
        choice_area_top = dossier_rect.y + int(dossier_rect.height * 0.505)
        choice_area_bottom = hint_rect.y - 8
        choice_gap = 10 if normal_count <= 3 else 8
        available_choice_height = max(1, choice_area_bottom - choice_area_top - (choice_gap * (normal_count - 1)))
        choice_height = max(44, min(84, available_choice_height // normal_count))
        choice_width = int(dossier_rect.width * 0.775)
        choice_x = dossier_rect.x + int(dossier_rect.width * 0.115)
        shortcut_choices: list[dict[str, Any]] = []
        normal_index = 0
        for source_index, choice in enumerate(event["choices"]):
            preview_rows = list(choice.get("preview_rows") or [])
            is_secret = choice["id"] == secret_choice_id
            hidden = is_secret and not choice.get("available", False)
            if is_secret:
                rect = tuple(secret_rect)
            elif hidden:
                rect = (0, 0, 0, 0)
            else:
                rect = (
                    choice_x,
                    choice_area_top + (normal_index * (choice_height + choice_gap)),
                    choice_width,
                    choice_height,
                )
                normal_index += 1
            entry = {
                **choice,
                "preview_rows": preview_rows,
                "rect": rect,
                "hidden": hidden,
                "is_secret": is_secret,
                "glyph": self._glyph_resolver.category_for_choice(choice, event_tags),
                "shortcut": None,
                "source_index": source_index,
            }
            choices.append(entry)
            if not hidden:
                entry["shortcut"] = len(shortcut_choices) + 1 if len(shortcut_choices) < 9 else None
                shortcut_choices.append(entry)

        selected_choice = next((choice for choice in choices if choice["id"] == event["selected_choice_id"]), None)
        purge_targets: list[dict[str, Any]] = []
        if selected_choice is not None and selected_choice["choice_type"] == "purge" and not event["resolved"]:
            target_area = art_inner_rect.inflate(-18, -24)
            chip_width = (target_area.width - EVENT_LAYOUT["purge_gap_x"]) // EVENT_LAYOUT["purge_columns"]
            chip_height = max(54, min(74, (target_area.height - 34) // 5))
            start_y = target_area.y + 34
            for index, target in enumerate(event["purge_targets"]):
                row = index // EVENT_LAYOUT["purge_columns"]
                col = index % EVENT_LAYOUT["purge_columns"]
                purge_targets.append(
                    {
                        **target,
                        "rect": (
                            target_area.x + (col * (chip_width + EVENT_LAYOUT["purge_gap_x"])),
                            start_y + (row * (chip_height + EVENT_LAYOUT["purge_gap_y"])),
                            chip_width,
                            chip_height,
                        ),
                    }
                )

        can_confirm = (
            not event["resolved"]
            and selected_choice is not None
            and selected_choice["available"]
            and (selected_choice["choice_type"] != "purge" or event["selected_target_id"] is not None)
        )
        return {
            "event_id": event["event_id"],
            "title": event["title"],
            "body": event["body"],
            "tags": event_tags,
            "primary_tag": event.get("primary_tag"),
            "player_hp": event_state["player"]["current_hp"],
            "player_max_hp": event_state["player"]["max_hp"],
            "player_credits": event_state["player"]["credits"],
            "deck_size": event["deck_size"],
            "choices": choices,
            "shortcut_choices": shortcut_choices,
            "selected_choice": selected_choice,
            "selected_choice_id": event["selected_choice_id"],
            "secret_choice": next((choice for choice in choices if choice["is_secret"]), None),
            "purge_targets": purge_targets,
            "resolved": event["resolved"],
            "resolution_summary": event["resolution_summary"],
            "resolution_details": event["resolution_details"],
            "can_continue": event["can_continue"],
            "can_confirm": can_confirm,
            "shell_rect": tuple(shell_rect),
            "dossier_rect": tuple(dossier_rect),
            "art_frame_rect": tuple(art_frame_rect),
            "art_inner_rect": tuple(art_inner_rect),
            "confirm_rect": tuple(confirm_rect),
            "continue_rect": tuple(confirm_rect),
            "secret_rect": tuple(secret_rect),
            "hint_rect": tuple(hint_rect),
            "title_rect": tuple(title_rect),
            "body_rect": tuple(body_rect),
            "accent_yellow_rect": tuple(accent_yellow_rect),
            "accent_cyan_rect": tuple(accent_cyan_rect),
        }

    def render(self, surface: Any, event_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        self._ensure_fonts(event_state.get("presentation", {}).get("ui_scale", 1.0))
        layout = self.build_layout(event_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        draw_background_stage(surface, background, veil_alpha=188, top_band_height=78, bottom_band_height=88, line_step=48, line_alpha=5)
        self._draw_background_scan(surface)
        event_ui_assets.blit(surface, "window_shell_combined", layout["shell_rect"])
        self._draw_event_art(surface, layout)
        self._draw_title_block(surface, layout)
        self._draw_body(surface, layout)
        if layout["resolved"]:
            self._draw_resolution(surface, layout)
        else:
            for choice in layout["choices"]:
                if choice.get("hidden") or choice.get("is_secret"):
                    continue
                self._draw_choice(surface, choice, layout)
        if layout["purge_targets"]:
            self._draw_purge_targets(surface, layout)
        self._draw_hint_bar(surface, layout)
        self._draw_secret_slot(surface, layout)
        if layout["can_continue"]:
            self._draw_confirm_button(surface, layout["continue_rect"], "Continue", "C", self._hovered_action == "continue", self._pressed_action == "continue", True)
        else:
            self._draw_confirm_button(surface, layout["confirm_rect"], "Confirm", "Enter", self._hovered_action == "confirm", self._pressed_action == "confirm", layout["can_confirm"])

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "confirm":
            if not layout["can_confirm"]:
                if layout["selected_choice"] is None:
                    return {"type": "notice", "message": "Select an event choice before confirming it.", "level": "error"}
                if layout["selected_choice"]["choice_type"] == "purge":
                    return {"type": "notice", "message": "Choose a deck card target before confirming this choice.", "level": "error"}
                return {"type": "notice", "message": "That event choice is unavailable right now.", "level": "error"}
            return {"type": "confirm_event_choice"}
        if action_id == "continue":
            if not layout["can_continue"]:
                return {"type": "notice", "message": "Resolve the event before continuing.", "level": "error"}
            return {"type": "continue_from_event"}
        if action_id.startswith("choice:"):
            choice_id = action_id.removeprefix("choice:")
            choice = next(choice for choice in layout["choices"] if choice["id"] == choice_id)
            if not choice["available"]:
                return {"type": "notice", "message": choice["disabled_reason"], "level": "error"}
            return {"type": "select_event_choice", "choice_id": choice_id}
        if action_id.startswith("target:"):
            return {"type": "select_event_target", "target_id": action_id.removeprefix("target:")}
        return {"type": "notice", "message": "Unknown event action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        if not layout["resolved"]:
            for choice in layout["choices"]:
                if choice.get("hidden"):
                    continue
                if point_in_rect(position, choice["rect"]):
                    return f"choice:{choice['id']}"
        for target in layout["purge_targets"]:
            if point_in_rect(position, target["rect"]):
                return f"target:{target['option_id']}"
        if layout["can_continue"] and point_in_rect(position, layout["continue_rect"]):
            return "continue"
        if point_in_rect(position, layout["confirm_rect"]):
            return "confirm"
        return None

    def _draw_background_scan(self, surface: Any) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for y in range(0, surface.get_height(), 4):
            pygame.draw.line(overlay, (35, 135, 170, 10), (0, y), (surface.get_width(), y), 1)
        pygame.draw.rect(overlay, (2, 8, 14, 58), overlay.get_rect(), width=18)
        surface.blit(overlay, (0, 0))

    def _draw_event_art(self, surface: Any, layout: dict[str, Any]) -> None:
        inner_rect = pygame.Rect(*layout["art_inner_rect"])
        art = self._event_art_surface(layout, inner_rect.size)
        surface.blit(art, inner_rect.topleft)
        overlay = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
        overlay.fill((0, 12, 20, 34))
        for y in range(0, inner_rect.height, 5):
            pygame.draw.line(overlay, (60, 210, 255, 18), (0, y), (inner_rect.width, y), 1)
        for inset in (0, 7):
            color = (41, 200, 255, 85 if inset == 0 else 45)
            pygame.draw.line(overlay, color, (10 + inset, 8 + inset), (48 + inset, 8 + inset), 1)
            pygame.draw.line(overlay, color, (10 + inset, 8 + inset), (10 + inset, 42 + inset), 1)
            pygame.draw.line(overlay, color, (inner_rect.width - 50 - inset, inner_rect.height - 9 - inset), (inner_rect.width - 12 - inset, inner_rect.height - 9 - inset), 1)
            pygame.draw.line(overlay, color, (inner_rect.width - 12 - inset, inner_rect.height - 42 - inset), (inner_rect.width - 12 - inset, inner_rect.height - 9 - inset), 1)
        surface.blit(overlay, inner_rect.topleft)

    def _event_art_surface(self, layout: dict[str, Any], size: tuple[int, int]) -> Any:
        candidates = [f"event_art_{layout['event_id']}.png"]
        tags = set(layout.get("tags") or [])
        if tags.intersection({"merchant_style", "shop", "economy"}):
            candidates.append("event_art_generic_vendor.png")
        if tags.intersection({"recovery", "cleanse", "heal"}):
            candidates.append("event_art_generic_clinic.png")
        if tags.intersection({"corruption", "anomaly"}):
            candidates.append("event_art_generic_corruption.png")
        if tags.intersection({"combat_prep", "attack", "defense"}):
            candidates.append("event_art_generic_combat_prep.png")
        if tags.intersection({"curse", "debt"}):
            candidates.append("event_art_generic_debt.png")
        if tags.intersection({"relic", "boss_relic"}):
            candidates.append("event_art_generic_relic.png")
        candidates.append("event_art_generic_street.png")
        for filename in candidates:
            path = EVENT_UI_ASSET_ROOT / "art" / filename
            if path.exists():
                return self._scale_cover(self._load_image(path), size)
        fallback = self._scale_cover(self._load_image(resolve_asset_path("ui", "bg_map.png")), size)
        tint = pygame.Surface(size, pygame.SRCALPHA)
        category = self._glyph_resolver.category_for_choice({"label": "", "description": " ".join(tags), "effects": []}, list(tags))
        tint_color = {
            "damage": (120, 20, 28, 70),
            "healing": (20, 100, 62, 62),
            "defense": (18, 86, 120, 66),
            "credits": (120, 82, 16, 60),
            "corruption": (74, 24, 120, 78),
            "curse": (118, 34, 24, 70),
            "relic": (18, 88, 110, 70),
            "deck": (18, 76, 112, 68),
        }.get(category, (12, 42, 62, 64))
        tint.fill(tint_color)
        fallback.blit(tint, (0, 0))
        glyph = event_ui_assets.get(f"glyph_{category}", (104, 104))
        if glyph is not None:
            glyph.set_alpha(42)
            fallback.blit(glyph, glyph.get_rect(center=(size[0] // 2, size[1] // 2)))
        return fallback

    def _draw_title_block(self, surface: Any, layout: dict[str, Any]) -> None:
        title_rect = pygame.Rect(*layout["title_rect"])
        self._draw_shadowed_text(surface, layout["title"], title_rect, self._title_font, COLOR_TEXT, max_lines=1, fit=True)
        event_ui_assets.blit(surface, "title_accent_bar_yellow", layout["accent_yellow_rect"], nine_slice=True)
        event_ui_assets.blit(surface, "title_accent_bar_cyan", layout["accent_cyan_rect"], nine_slice=True)

    def _draw_body(self, surface: Any, layout: dict[str, Any]) -> None:
        body_rect = pygame.Rect(*layout["body_rect"])
        self._draw_shadowed_text(surface, layout["body"], body_rect, self._small_font, (218, 230, 241), max_lines=3)

    def _draw_choice(self, surface: Any, choice: dict[str, Any], layout: dict[str, Any]) -> None:
        rect = pygame.Rect(*choice["rect"])
        selected = layout["selected_choice_id"] == choice["id"]
        hovered = self._hovered_action == f"choice:{choice['id']}"
        pressed = self._pressed_action == f"choice:{choice['id']}"
        available = choice["available"] and not layout["resolved"]
        asset_name = "choice_button_locked"
        if available:
            asset_name = "choice_button_pressed" if pressed else "choice_button_selected" if selected or hovered else "choice_button_normal"
        event_ui_assets.blit(surface, asset_name, rect, nine_slice=True)
        icon_rect = pygame.Rect(rect.x + 12, rect.y + max(8, (rect.height - 52) // 2), 52, 52)
        event_ui_assets.blit(surface, "choice_icon_plate_hex", icon_rect)
        glyph = event_ui_assets.get(f"glyph_{choice['glyph']}", (38, 38))
        if glyph is not None:
            if not available:
                glyph.set_alpha(126)
            surface.blit(glyph, glyph.get_rect(center=icon_rect.center))
        text_color = COLOR_TEXT if available else COLOR_TEXT_DIM
        title_rect = pygame.Rect(rect.x + 78, rect.y + 13, rect.width - 128, 23)
        self._draw_shadowed_text(surface, choice["label"], title_rect, self._small_font, text_color, max_lines=1, fit=True)
        detail_text = choice["description"] if available else choice.get("disabled_reason") or choice["description"]
        detail_rect = pygame.Rect(rect.x + 78, rect.y + 39, rect.width - 136, max(22, rect.height - 44))
        self._text_formatter.draw(surface, detail_text, detail_rect, self._tiny_font, enabled=available, max_lines=2)
        if choice.get("preview_rows") and rect.height >= 72:
            self._draw_preview_rows(surface, choice["preview_rows"], pygame.Rect(rect.x + 78, rect.bottom - 26, rect.width - 154, 20), enabled=available)
        if not available:
            self._draw_requirement_strip(surface, rect, detail_text)
        if choice.get("shortcut") is not None:
            badge_rect = pygame.Rect(rect.right - 38, rect.y + max(10, (rect.height - 30) // 2), 30, 30)
            event_ui_assets.blit(surface, "choice_number_badge", badge_rect)
            self._draw_centered_text(surface, str(choice["shortcut"]), badge_rect, self._tiny_font, COLOR_TEXT_DIM if not available else COLOR_TEXT)

    def _draw_requirement_strip(self, surface: Any, choice_rect: Any, text: str) -> None:
        rect = pygame.Rect(choice_rect)
        if rect.height < 70:
            return
        strip_rect = pygame.Rect(rect.x + 82, rect.bottom - 26, min(rect.width - 126, 260), 22)
        event_ui_assets.blit(surface, "requirement_strip", strip_rect, alpha=178, nine_slice=True)
        self._text_formatter.draw(surface, text, strip_rect.inflate(-16, -4), self._micro_font, enabled=False, max_lines=1)

    def _draw_preview_rows(self, surface: Any, preview_rows: list[dict[str, Any]], rect: Any, *, enabled: bool) -> None:
        x = rect.x
        for preview in preview_rows[:2]:
            label = str(preview.get("label", ""))
            if not label:
                continue
            width = min(rect.right - x, max(90, self._micro_font.size(label)[0] + 18))
            chip_rect = pygame.Rect(x, rect.y, width, rect.height)
            event_ui_assets.blit(surface, "requirement_strip", chip_rect, alpha=210 if enabled else 145, nine_slice=True)
            self._text_formatter.draw(surface, label, chip_rect.inflate(-12, -3), self._micro_font, enabled=enabled, max_lines=1)
            x += width + 8
            if x > rect.right - 82:
                break

    def _draw_purge_targets(self, surface: Any, layout: dict[str, Any]) -> None:
        art_inner_rect = pygame.Rect(*layout["art_inner_rect"])
        veil = pygame.Surface(art_inner_rect.size, pygame.SRCALPHA)
        veil.fill((2, 8, 14, 176))
        surface.blit(veil, art_inner_rect.topleft)
        self._draw_shadowed_text(surface, "Select Deck Card", pygame.Rect(art_inner_rect.x + 16, art_inner_rect.y + 10, art_inner_rect.width - 32, 24), self._small_font, COLOR_TEXT, max_lines=1)
        for target in layout["purge_targets"]:
            self._draw_purge_target(surface, target)

    def _draw_purge_target(self, surface: Any, target: dict[str, Any]) -> None:
        rect = pygame.Rect(*target["rect"])
        hovered = self._hovered_action == f"target:{target['option_id']}"
        pressed = self._pressed_action == f"target:{target['option_id']}"
        draw_card(
            surface,
            rect,
            target["card"],
            {"title": self._tiny_font, "body": self._micro_font, "tiny": self._micro_font},
            variant="mini",
            selected=target["selected"],
            hovered=hovered,
            pressed=pressed,
            high_contrast=False,
        )

    def _draw_resolution(self, surface: Any, layout: dict[str, Any]) -> None:
        dossier = pygame.Rect(*layout["dossier_rect"])
        panel_rect = pygame.Rect(dossier.x + int(dossier.width * 0.115), dossier.y + int(dossier.height * 0.555), int(dossier.width * 0.775), 126)
        event_ui_assets.blit(surface, "choice_button_selected", panel_rect, nine_slice=True)
        self._draw_shadowed_text(surface, "Resolved", pygame.Rect(panel_rect.x + 24, panel_rect.y + 18, panel_rect.width - 48, 28), self._small_font, COLOR_TEXT, max_lines=1)
        summary = layout["resolution_summary"] or "Event resolved."
        self._text_formatter.draw(surface, summary, pygame.Rect(panel_rect.x + 24, panel_rect.y + 48, panel_rect.width - 48, 34), self._tiny_font, enabled=True, max_lines=2)
        detail_y = panel_rect.y + 82
        for detail in list(layout["resolution_details"] or [])[:2]:
            self._text_formatter.draw(surface, str(detail), pygame.Rect(panel_rect.x + 24, detail_y, panel_rect.width - 48, 22), self._micro_font, enabled=True, max_lines=1)
            detail_y += 20

    def _draw_hint_bar(self, surface: Any, layout: dict[str, Any]) -> None:
        rect = pygame.Rect(*layout["hint_rect"])
        event_ui_assets.blit(surface, "input_hint_bar", rect, nine_slice=True)
        hints = "1-9 choose  |  Enter confirm  |  C continue"
        self._draw_shadowed_text(surface, hints, rect.inflate(-24, -8), self._tiny_font, (168, 194, 214), max_lines=1)

    def _draw_secret_slot(self, surface: Any, layout: dict[str, Any]) -> None:
        secret = layout.get("secret_choice")
        rect = pygame.Rect(*layout["secret_rect"])
        if secret is not None and secret.get("available") and not layout["resolved"]:
            hovered = self._hovered_action == f"choice:{secret['id']}"
            pressed = self._pressed_action == f"choice:{secret['id']}"
            event_ui_assets.blit(surface, "secret_option_unlocked", rect, alpha=245 if hovered or pressed else 224, nine_slice=True)
            icon_rect = pygame.Rect(rect.x + 12, rect.y + 8, 34, 34)
            glyph = event_ui_assets.get("glyph_corruption", (30, 30))
            if glyph is not None:
                surface.blit(glyph, glyph.get_rect(center=icon_rect.center))
            self._draw_shadowed_text(surface, secret["label"], pygame.Rect(rect.x + 52, rect.y + 8, rect.width - 86, 20), self._tiny_font, (228, 188, 255), max_lines=1, fit=True)
            self._text_formatter.draw(surface, secret["description"], pygame.Rect(rect.x + 52, rect.y + 28, rect.width - 74, 20), self._micro_font, enabled=True, base_color=(204, 165, 230), max_lines=1)
            if secret.get("shortcut") is not None:
                badge_rect = pygame.Rect(rect.right - 32, rect.y + 13, 24, 24)
                event_ui_assets.blit(surface, "choice_number_badge", badge_rect)
                self._draw_centered_text(surface, str(secret["shortcut"]), badge_rect, self._micro_font, (231, 204, 255))
            return
        event_ui_assets.blit(surface, "secret_option_hidden", rect, alpha=118, nine_slice=True)

    def _draw_confirm_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        sublabel: str,
        hovered: bool,
        pressed: bool,
        enabled: bool,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        if not enabled:
            asset_name = "confirm_button_inactive"
        elif pressed:
            asset_name = "confirm_button_pressed"
        else:
            asset_name = "confirm_button_active"
        event_ui_assets.blit(surface, asset_name, rect, alpha=255 if enabled else 198, nine_slice=True)
        if hovered and enabled:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (39, 200, 255, 38), glow.get_rect(), border_radius=10)
            surface.blit(glow, rect.topleft)
        text_color = (85, 105, 120) if not enabled else (190, 238, 255)
        self._draw_centered_text(surface, label, pygame.Rect(rect.x, rect.y + 9, rect.width, 22), self._small_font, text_color)
        self._draw_centered_text(surface, sublabel, pygame.Rect(rect.x, rect.y + 32, rect.width, 18), self._micro_font, (105, 195, 230) if enabled else (76, 92, 104))

    def _secret_choice_id(self, event: dict[str, Any]) -> str | None:
        for choice in event.get("choices", []):
            if choice.get("ui_role") == "secret_corruption":
                return str(choice["id"])
        return None

    def _relative_rect(self, parent: Any, rx: float, ry: float, rw: float, rh: float) -> Any:
        if pygame is not None:
            rect = pygame.Rect(parent)
            return pygame.Rect(
                rect.x + int(round(rect.width * rx)),
                rect.y + int(round(rect.height * ry)),
                int(round(rect.width * rw)),
                int(round(rect.height * rh)),
            )
        rect = _Rect.from_rect_like(parent)
        return _Rect(
            rect.x + int(round(rect.width * rx)),
            rect.y + int(round(rect.height * ry)),
            int(round(rect.width * rw)),
            int(round(rect.height * rh)),
        )

    def _scale_cover(self, image: Any, size: tuple[int, int]) -> Any:
        target_width, target_height = size
        source_width, source_height = image.get_size()
        if source_width <= 0 or source_height <= 0:
            return pygame.Surface(size, pygame.SRCALPHA)
        scale = max(target_width / source_width, target_height / source_height)
        scaled_size = (max(1, int(source_width * scale)), max(1, int(source_height * scale)))
        scaled = pygame.transform.smoothscale(image, scaled_size)
        crop_rect = pygame.Rect(0, 0, target_width, target_height)
        crop_rect.center = scaled.get_rect().center
        return scaled.subsurface(crop_rect).copy()

    def _draw_shadowed_text(
        self,
        surface: Any,
        text: str,
        rect: Any,
        font: Any,
        color: tuple[int, int, int],
        *,
        max_lines: int = 1,
        fit: bool = False,
    ) -> None:
        target_rect = pygame.Rect(rect)
        draw_font = font
        if fit:
            draw_font = self._font_that_fits(str(text), target_rect.width, font)
        shadow_color = (0, 4, 8)
        if max_lines == 1:
            shadow = draw_font.render(str(text), True, shadow_color)
            surface.blit(shadow, (target_rect.x + 2, target_rect.y + 2))
            rendered = draw_font.render(str(text), True, color)
            surface.blit(rendered, (target_rect.x, target_rect.y))
            return
        shadow_rect = target_rect.move(2, 2)
        self._draw_limited_wrapped_text(surface, text, shadow_rect, draw_font, shadow_color, max_lines=max_lines)
        self._draw_limited_wrapped_text(surface, text, target_rect, draw_font, color, max_lines=max_lines)

    def _draw_limited_wrapped_text(self, surface: Any, text: str, rect: Any, font: Any, color: tuple[int, int, int], *, max_lines: int) -> None:
        words = str(text).split()
        line = ""
        y = rect.y
        lines = 0
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if font.size(candidate)[0] <= rect.width:
                line = candidate
                continue
            if line:
                surface.blit(font.render(line, True, color), (rect.x, y))
                lines += 1
                if lines >= max_lines:
                    return
                y += font.get_linesize()
            line = word
        if line and lines < max_lines:
            surface.blit(font.render(line, True, color), (rect.x, y))

    def _font_that_fits(self, text: str, width: int, font: Any) -> Any:
        if font.size(text)[0] <= width:
            return font
        size = max(18, font.get_height() - 4)
        while size >= 18:
            candidate = pygame.font.SysFont("consolas", size, bold=True)
            if candidate.size(text)[0] <= width:
                return candidate
            size -= 2
        return pygame.font.SysFont("consolas", 18, bold=True)

    def _draw_centered_text(self, surface: Any, text: str, rect: Any, font: Any, color: tuple[int, int, int]) -> None:
        label = font.render(str(text), True, color)
        surface.blit(label, label.get_rect(center=pygame.Rect(rect).center))

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return
        self._font_scale = scale
        self._font = pygame.font.SysFont("consolas", max(22, int(28 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(16, int(19 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(14 * scale)))
        self._micro_font = pygame.font.SysFont("consolas", max(10, int(12 * scale)))
        self._title_font = pygame.font.SysFont("consolas", max(30, int(42 * scale)), bold=True)

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        if pygame is None:
            raise RuntimeError("Pygame is required to load event UI assets.")
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((10, 24, 36, 255))
        self._image_cache[cache_key] = image
        return image


class _Rect(tuple):
    def __new__(cls, x: int, y: int, width: int, height: int) -> "_Rect":
        return tuple.__new__(cls, (x, y, width, height))

    @classmethod
    def from_rect_like(cls, rect: Any) -> "_Rect":
        if isinstance(rect, cls):
            return rect
        return cls(int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))

    @property
    def x(self) -> int:
        return int(self[0])

    @property
    def y(self) -> int:
        return int(self[1])

    @property
    def width(self) -> int:
        return int(self[2])

    @property
    def height(self) -> int:
        return int(self[3])

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def inflate(self, x_delta: int, y_delta: int) -> "_Rect":
        return _Rect(
            self.x - (int(x_delta) // 2),
            self.y - (int(y_delta) // 2),
            max(0, self.width + int(x_delta)),
            max(0, self.height + int(y_delta)),
        )


def simulate_event_ui() -> dict[str, Any]:
    ui = EventUI()
    return ui.build_layout(
        {
            "event": {
                "event_id": "riot_drill_square_01",
                "title": "Riot Drill Square",
                "body": "A fenced training square used by riot units to sharpen response drills.",
                "tags": ["combat_prep", "defense", "corruption"],
                "primary_tag": "combat_prep",
                "choices": [
                    {
                        "id": "attack_cadence",
                        "label": "Run the attack cadence",
                        "description": "Take 9 damage. Gain Riot Gyro.",
                        "preview_rows": [],
                        "choice_type": "effect",
                        "requirements": {},
                        "effects": [{"type": "damage", "value": 9}, {"type": "gain_modifier", "modifier_id": "riot_gyro"}],
                        "outcomes": [],
                        "available": True,
                        "disabled_reason": None,
                        "selected": False,
                    },
                    {
                        "id": "train_under_plating",
                        "label": "Train under plating",
                        "description": "Spend 18 credits. Next combat: start with 5 Block.",
                        "preview_rows": [{"kind": "next_combat", "label": "Next combat: +5 Block"}],
                        "choice_type": "effect",
                        "requirements": {"credits_at_least": 18},
                        "effects": [{"type": "lose_credits", "value": 18}],
                        "outcomes": [],
                        "available": True,
                        "disabled_reason": None,
                        "selected": False,
                    },
                ],
                "selected_choice_id": "attack_cadence",
                "selected_choice_type": "effect",
                "selected_target_id": None,
                "purge_targets": [],
                "resolved": False,
                "resolution_summary": None,
                "resolution_details": [],
                "deck_size": 10,
                "can_continue": False,
            },
            "player": {"current_hp": 64, "max_hp": 70, "credits": 20},
            "presentation": {"ui_scale": 1.0},
        }
    )
