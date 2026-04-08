from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.card_renderer import compact_card_summary, draw_card
from ui.render_utils import clamp_scale, draw_screen_scrim, draw_wrapped_text, point_in_rect


class RewardUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None

    def preload_assets(self) -> None:
        if pygame is None:
            return
        for path in (
            resolve_asset_path("ui", "bg_map.png"),
            resolve_asset_path("ui", "panel.png"),
        ):
            self._load_image(path)

    def handle_event(self, event: Any, reward_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None

        layout = self.build_layout(reward_state)
        active_section = layout["active_section"]

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
            return {"type": "continue_from_reward"}

        if event.key == pygame.K_x and active_section is not None and active_section["can_skip"]:
            return {"type": "skip_reward_section", "section": active_section["id"]}

        if event.key in {pygame.K_RETURN, pygame.K_SPACE}:
            if active_section is not None and active_section["selected_option_id"] is not None and not active_section["resolved"]:
                return {"type": "confirm_reward_selection", "section": active_section["id"]}
            if layout["can_continue"]:
                return {"type": "continue_from_reward"}
            return {"type": "notice", "message": "Choose or skip the remaining rewards first.", "level": "error"}

        if pygame.K_1 <= event.key <= pygame.K_9 and active_section is not None:
            option_index = event.key - pygame.K_1
            if option_index >= len(active_section["options"]):
                return {"type": "notice", "message": "That reward slot is empty.", "level": "error"}
            option = active_section["options"][option_index]
            return {
                "type": "select_reward_option",
                "section": active_section["id"],
                "option_id": option["option_id"],
            }

        return None

    def build_layout(self, reward_state: dict[str, Any]) -> dict[str, Any]:
        reward = reward_state["reward"]
        sections = []
        section_width = 1232
        base_x = 24
        base_y = 198
        active_section_id = next((section["id"] for section in reward["sections"] if not section["resolved"]), None)
        cursor_y = base_y

        for section in reward["sections"]:
            expanded = (not section["resolved"]) and section["id"] == active_section_id
            section_height = 170 if expanded and section["type"] == "card_offer" else 134 if expanded else 76
            panel_rect = (base_x, cursor_y, section_width, section_height)
            option_entries = self._option_entries(section, panel_rect) if expanded else []
            sections.append(
                {
                    **section,
                    "expanded": expanded,
                    "panel_rect": panel_rect,
                    "option_entries": option_entries,
                    "confirm_rect": (panel_rect[0] + 980, panel_rect[1] + 20, 104, 34),
                    "skip_rect": (panel_rect[0] + 1096, panel_rect[1] + 20, 104, 34),
                }
            )
            cursor_y += section_height + 16

        active_section = next((section for section in sections if not section["resolved"]), None)
        continue_rect = (1056, min(650, cursor_y + 8), 168, 48)
        return {
            "credits_granted": reward["credits_granted"],
            "player_credits": reward_state["player"]["credits"],
            "deck_size": reward["deck_size"],
            "sections": sections,
            "active_section": active_section,
            "can_continue": reward["can_continue"],
            "continue_rect": continue_rect,
            "controls": [
                "Click or 1-9: select reward",
                "Enter / Space: confirm",
                "X: skip section",
                "C: continue",
                "S: settings",
            ],
        }

    def render(self, surface: Any, reward_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return

        self._ensure_fonts(reward_state.get("presentation", {}).get("ui_scale", 1.0))
        high_contrast = reward_state.get("presentation", {}).get("high_contrast", False)
        layout = self.build_layout(reward_state)
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (1232, 78))

        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=176)
        surface.blit(panel, (24, 96))
        self._draw_text(surface, "Post-Combat Reward", (44, 116), self._font)
        self._draw_text(
            surface,
            f"Credits earned: +{layout['credits_granted']} | Total credits: {layout['player_credits']} | Deck size: {layout['deck_size']}",
            (44, 146),
            self._small_font,
            width=1120,
        )

        for section in layout["sections"]:
            panel_rect = pygame.Rect(*section["panel_rect"])
            section_panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), panel_rect.size)
            surface.blit(section_panel, panel_rect.topleft)
            outline = (255, 214, 110) if section is layout["active_section"] else (190, 205, 230) if high_contrast else (108, 122, 148)
            if section["resolved"]:
                outline = (120, 244, 170)
            pygame.draw.rect(surface, outline, panel_rect, 2, border_radius=16)
            self._draw_text(surface, section["title"], (panel_rect.x + 18, panel_rect.y + 16), self._small_font)
            self._draw_text(surface, section["description"], (panel_rect.x + 18, panel_rect.y + 42), self._tiny_font, width=520)

            if section["resolved"]:
                summary = "Resolved." if section["resolution"] is None else section["resolution"]["summary"]
                self._draw_text(surface, summary, (panel_rect.x + 18, panel_rect.y + 44), self._small_font, width=980)
            elif not section["expanded"]:
                self._draw_text(
                    surface,
                    "Resolve the current reward first.",
                    (panel_rect.x + 18, panel_rect.y + 44),
                    self._tiny_font,
                    width=420,
                )
            else:
                for option in section["option_entries"]:
                    option_rect = pygame.Rect(*option["rect"])
                    if option["kind"] != "card":
                        pygame.draw.rect(surface, (24, 34, 50), option_rect, border_radius=12)

                    selected = section["selected_option_id"] == option["option_id"]
                    hovered = self._hovered_action == option["action_id"]
                    pressed = self._pressed_action == option["action_id"]
                    if option["kind"] == "card":
                        draw_card(
                            surface,
                            option["rect"],
                            option["card"],
                            {"title": self._tiny_font, "body": self._tiny_font, "tiny": self._tiny_font},
                            variant="compact",
                            shortcut_label=str(option["shortcut"]) if option["shortcut"] is not None else None,
                            selected=selected,
                            hovered=hovered,
                            pressed=pressed,
                            high_contrast=high_contrast,
                        )
                    else:
                        border = (255, 214, 110) if selected else (255, 255, 255) if hovered else (190, 205, 230) if high_contrast else (104, 118, 146)
                        if pressed:
                            border = (255, 236, 140)
                        pygame.draw.rect(surface, border, option_rect, 3, border_radius=14)
                        self._draw_text(surface, option["title"], (option_rect.x + 12, option_rect.y + 12), self._tiny_font, width=option_rect.width - 24)
                        self._draw_text(surface, option["subtitle"], (option_rect.x + 12, option_rect.y + 42), self._tiny_font, width=option_rect.width - 24)
                        if option["shortcut"] is not None:
                            badge_rect = pygame.Rect(option_rect.x + option_rect.width - 30, option_rect.y + 8, 22, 22)
                            pygame.draw.rect(surface, (18, 24, 36), badge_rect, border_radius=11)
                            pygame.draw.rect(surface, (255, 214, 110), badge_rect, 2, border_radius=11)
                            badge = self._tiny_font.render(str(option["shortcut"]), True, (255, 214, 110))
                            surface.blit(badge, badge.get_rect(center=badge_rect.center))

                self._draw_button(surface, section["confirm_rect"], "Confirm", self._hovered_action == f"confirm:{section['id']}", self._pressed_action == f"confirm:{section['id']}", enabled=section["selected_option_id"] is not None)
                self._draw_button(surface, section["skip_rect"], "Skip", self._hovered_action == f"skip:{section['id']}", self._pressed_action == f"skip:{section['id']}", enabled=section["can_skip"])

        if layout["can_continue"]:
            self._draw_button(
                surface,
                layout["continue_rect"],
                "Continue",
                self._hovered_action == "continue",
                self._pressed_action == "continue",
                enabled=True,
            )

    def _option_entries(self, section: dict[str, Any], panel_rect: tuple[int, int, int, int]) -> list[dict[str, Any]]:
        entries = []
        if section["type"] == "card_offer":
            for index, option in enumerate(section["options"]):
                entries.append(
                    {
                        "action_id": f"option:{section['id']}:{option['option_id']}",
                        "option_id": option["option_id"],
                        "kind": "card",
                        "card": option["card"],
                        "rect": (panel_rect[0] + 332 + (index * 206), panel_rect[1] + 26, 184, 108),
                        "title": option["card"]["name"],
                        "subtitle": self._card_summary(option["card"]),
                        "shortcut": index + 1,
                    }
                )
        else:
            for index, option in enumerate(section["options"]):
                row = index // 4
                column = index % 4
                entries.append(
                    {
                        "action_id": f"option:{section['id']}:{option['option_id']}",
                        "option_id": option["option_id"],
                        "kind": "purge",
                        "rect": (panel_rect[0] + 320 + (column * 170), panel_rect[1] + 22 + (row * 38), 156, 30),
                        "title": option["card"]["name"],
                        "subtitle": "",
                        "shortcut": index + 1 if index < 9 else None,
                    }
                )
        return entries

    def _card_summary(self, card: dict[str, Any]) -> str:
        return compact_card_summary(card)

    def _event_for_action(self, action_id: str, layout: dict[str, Any]) -> dict[str, Any]:
        if action_id == "continue":
            if not layout["can_continue"]:
                return {"type": "notice", "message": "Resolve or skip every reward section first.", "level": "error"}
            return {"type": "continue_from_reward"}

        action_type, _, payload = action_id.partition(":")
        if action_type in {"confirm", "skip"}:
            section_id = payload
            return {
                "type": "confirm_reward_selection" if action_type == "confirm" else "skip_reward_section",
                "section": section_id,
            }

        if action_type == "option":
            section_id, _, option_id = payload.partition(":")
            return {"type": "select_reward_option", "section": section_id, "option_id": option_id}

        return {"type": "notice", "message": "Unknown reward action.", "level": "error"}

    def _action_at_position(self, layout: dict[str, Any], position: tuple[int, int]) -> str | None:
        for section in layout["sections"]:
            if section["expanded"]:
                for option in section["option_entries"]:
                    if point_in_rect(position, option["rect"]):
                        return option["action_id"]
            if (
                section["expanded"]
                and section["selected_option_id"] is not None
                and point_in_rect(position, section["confirm_rect"])
            ):
                return f"confirm:{section['id']}"
            if (
                section["expanded"]
                and section["can_skip"]
                and point_in_rect(position, section["skip_rect"])
            ):
                return f"skip:{section['id']}"
        if layout["can_continue"] and point_in_rect(position, layout["continue_rect"]):
            return "continue"
        return None

    def _draw_button(
        self,
        surface: Any,
        rect_tuple: tuple[int, int, int, int],
        label: str,
        hovered: bool,
        pressed: bool,
        enabled: bool,
    ) -> None:
        rect = pygame.Rect(*rect_tuple)
        fill = (36, 78, 138) if enabled else (26, 34, 48)
        border = (230, 240, 255) if enabled else (110, 118, 136)
        if hovered and enabled:
            fill = (52, 104, 184)
        if pressed and enabled:
            fill = (255, 214, 110)
            border = (255, 214, 110)
        pygame.draw.rect(surface, fill, rect, border_radius=12)
        pygame.draw.rect(surface, border, rect, 2, border_radius=12)
        text_color = (240, 245, 255) if enabled and not pressed else (18, 24, 36) if pressed else (160, 170, 190)
        label_surface = self._tiny_font.render(label, True, text_color)
        surface.blit(label_surface, label_surface.get_rect(center=rect.center))

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
        self._font = pygame.font.SysFont("consolas", max(22, int(28 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(16, int(20 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(15 * scale)))

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        if pygame is None:
            raise RuntimeError("Pygame is required to load reward UI assets.")

        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((120, 90, 220, 180))

        self._image_cache[cache_key] = image
        return image


def simulate_reward_ui() -> dict[str, Any]:
    ui = RewardUI()
    return ui.build_layout(
        {
            "reward": {
                "credits_granted": 40,
                "deck_size": 10,
                "can_continue": False,
                "sections": [
                    {
                        "id": "card_offer",
                        "type": "card_offer",
                        "title": "Card Reward",
                        "description": "Choose a card to add.",
                        "options": [
                            {
                                "option_id": "surge_strike_01",
                                "card": {
                                    "id": "surge_strike_01",
                                    "name": "Surge Strike",
                                    "cost": 2,
                                    "type": "attack",
                                    "effects": [{"type": "damage", "value": 12}],
                                },
                            }
                        ],
                        "selected_option_id": None,
                        "resolved": False,
                        "resolution": None,
                        "can_skip": True,
                    }
                ],
            },
            "player": {"credits": 40},
            "presentation": {"ui_scale": 1.0},
        }
    )
