from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import MAX_UI_SCALE, MIN_UI_SCALE, resolve_asset_path
from ui.render_utils import clamp_scale, draw_wrapped_text, point_in_rect


class GrayspineIntelUI:
    def __init__(self) -> None:
        self._font = None
        self._small_font = None
        self._tiny_font = None
        self._title_font = None
        self._font_scale = None
        self._image_cache: dict[str, Any] = {}
        self._hovered_action: str | None = None
        self._pressed_action: str | None = None

    def preload_assets(self) -> None:
        if pygame is None:
            return
        self._load_image(resolve_asset_path("ui", "panel.png"))

    def build_layout(self, intel_state: dict[str, Any]) -> dict[str, Any]:
        selected_faction_id = intel_state.get("selected_faction_id")
        factions = list(intel_state.get("factions", []))
        if factions and not any(faction["id"] == selected_faction_id for faction in factions):
            selected_faction_id = factions[0]["id"]
        selected_faction = next(
            (faction for faction in factions if faction["id"] == selected_faction_id),
            factions[0] if factions else None,
        )

        selector_buttons = []
        for index, faction in enumerate(factions):
            selector_buttons.append(
                {
                    "id": faction["id"],
                    "name": faction["name"],
                    "accent": tuple(faction.get("accent_color", [160, 180, 210])),
                    "rect": (116 + (index * 344), 216, 304, 72),
                    "selected": faction["id"] == selected_faction_id,
                }
            )

        return {
            "city": intel_state.get("city", {}),
            "selected_faction": selected_faction,
            "selector_buttons": selector_buttons,
            "spine_core": intel_state.get("spine_core", {}),
            "close_rect": (1124, 86, 92, 40),
            "content_rect": (72, 66, 1136, 596),
            "selected_faction_id": selected_faction_id,
        }

    def handle_event(self, event: Any, intel_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None:
            return None
        layout = self.build_layout(intel_state)

        if event.type == pygame.MOUSEMOTION:
            self._hovered_action = None
            if point_in_rect(event.pos, layout["close_rect"]):
                self._hovered_action = "close"
                return None
            for button in layout["selector_buttons"]:
                if point_in_rect(event.pos, button["rect"]):
                    self._hovered_action = f"select:{button['id']}"
                    return None
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed_action = self._hovered_action
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            released_action = self._hovered_action
            pressed_action = self._pressed_action
            self._pressed_action = None
            if released_action is None or released_action != pressed_action:
                return None
            if released_action == "close":
                return {"type": "intel_close"}
            if released_action.startswith("select:"):
                return {"type": "intel_select_faction", "faction_id": released_action.split(":", 1)[1]}
            return None

        if event.type != pygame.KEYDOWN:
            return None

        if event.key in {pygame.K_ESCAPE, pygame.K_i}:
            return {"type": "intel_close"}
        if event.key in {pygame.K_LEFT, pygame.K_a}:
            return self._keyboard_cycle(layout, -1)
        if event.key in {pygame.K_RIGHT, pygame.K_d}:
            return self._keyboard_cycle(layout, 1)
        return None

    def render(self, surface: Any, intel_state: dict[str, Any]) -> None:
        if pygame is None or surface is None:
            return
        self._ensure_fonts(intel_state.get("presentation", {}).get("ui_scale", 1.0))
        layout = self.build_layout(intel_state)
        city = layout["city"]
        faction = layout["selected_faction"]
        spine_core = layout["spine_core"]

        backdrop = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        backdrop.fill((3, 8, 14, 224))
        surface.blit(backdrop, (0, 0))

        panel = self._scaled_image(resolve_asset_path("ui", "panel.png"), (layout["content_rect"][2], layout["content_rect"][3]))
        panel_rect = pygame.Rect(*layout["content_rect"])
        surface.blit(panel, panel_rect.topleft)
        pygame.draw.rect(surface, (196, 214, 240), panel_rect, 2, border_radius=18)

        self._draw_text(surface, city.get("name", "Grayspine"), (102, 96), self._title_font)
        self._draw_text(surface, city.get("tagline", ""), (104, 142), self._tiny_font, width=820)

        close_rect = pygame.Rect(*layout["close_rect"])
        close_fill = (30, 42, 58) if self._hovered_action == "close" else (18, 28, 42)
        pygame.draw.rect(surface, close_fill, close_rect, border_radius=12)
        pygame.draw.rect(surface, (230, 236, 246), close_rect, 2, border_radius=12)
        self._draw_text(surface, "Close", (close_rect.x + 18, close_rect.y + 11), self._small_font, width=56)

        self._draw_text(surface, city.get("summary", ""), (104, 178), self._small_font, width=1040)

        for button in layout["selector_buttons"]:
            rect = pygame.Rect(*button["rect"])
            accent = button["accent"]
            selected = button["selected"]
            hovered = self._hovered_action == f"select:{button['id']}"
            fill = (14, 24, 36)
            if hovered:
                fill = (24, 38, 54)
            if selected:
                fill = tuple(min(255, int(channel * 0.28) + 10) for channel in accent)
            pygame.draw.rect(surface, fill, rect, border_radius=16)
            pygame.draw.rect(surface, accent if not selected else (255, 214, 110), rect, 2, border_radius=16)
            pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 12, rect.y + 12, 8, rect.height - 24), border_radius=4)
            self._draw_text(surface, button["name"], (rect.x + 30, rect.y + 12), self._small_font, width=220)
            slogan = next(
                (f["slogan"] for f in intel_state.get("factions", []) if f["id"] == button["id"]),
                "",
            )
            self._draw_text(surface, slogan, (rect.x + 30, rect.y + 38), self._tiny_font, width=250)

        if faction is None:
            return

        accent = tuple(faction.get("accent_color", [160, 180, 210]))
        detail_rect = pygame.Rect(92, 314, 720, 316)
        spine_rect = pygame.Rect(834, 314, 354, 316)
        pygame.draw.rect(surface, (10, 18, 28), detail_rect, border_radius=16)
        pygame.draw.rect(surface, accent, detail_rect, 2, border_radius=16)
        pygame.draw.rect(surface, (8, 14, 22), spine_rect, border_radius=16)
        pygame.draw.rect(surface, (255, 214, 110) if spine_core.get("unlocked") else (104, 124, 154), spine_rect, 2, border_radius=16)

        self._draw_text(surface, faction["name"], (114, 336), self._font)
        self._draw_text(surface, faction.get("theme", ""), (114, 370), self._tiny_font, width=660)
        self._draw_text(surface, f"Territory: {faction.get('territory', '')}", (114, 414), self._small_font, width=660)
        self._draw_text(surface, f"Doctrine: {faction.get('goal', '')}", (114, 454), self._small_font, width=660)
        self._draw_text(surface, f"Combat: {faction.get('combat_style', '')}", (114, 496), self._small_font, width=660)
        boss_names = ", ".join(boss["name"] for boss in faction.get("bosses", []))
        self._draw_text(surface, f"Bosses: {boss_names}", (114, 550), self._small_font, width=660)

        self._draw_text(surface, spine_core.get("name", "Spine Core"), (854, 336), self._font)
        self._draw_text(surface, spine_core.get("display_summary", ""), (854, 382), self._small_font, width=314)
        self._draw_text(surface, spine_core.get("importance", ""), (854, 468), self._small_font, width=314)
        state_label = "Unlocked" if spine_core.get("unlocked") else "Signal Obscured"
        self._draw_text(surface, state_label, (854, 566), self._tiny_font, width=160)

    def _keyboard_cycle(self, layout: dict[str, Any], step: int) -> dict[str, Any] | None:
        buttons = layout["selector_buttons"]
        if not buttons:
            return None
        current_id = layout["selected_faction_id"]
        current_index = next((index for index, button in enumerate(buttons) if button["id"] == current_id), 0)
        next_index = (current_index + step) % len(buttons)
        return {"type": "intel_select_faction", "faction_id": buttons[next_index]["id"]}

    def _draw_text(
        self,
        surface: Any,
        text: str,
        position: tuple[int, int],
        font: Any,
        *,
        width: int | None = None,
    ) -> None:
        draw_wrapped_text(surface, text, position, font, width=width)

    def _ensure_fonts(self, scale: float) -> None:
        scale = clamp_scale(scale, MIN_UI_SCALE, MAX_UI_SCALE)
        if self._font_scale == scale and self._font is not None:
            return
        self._font_scale = scale
        self._title_font = pygame.font.SysFont("consolas", max(26, int(34 * scale)), bold=True)
        self._font = pygame.font.SysFont("consolas", max(20, int(24 * scale)))
        self._small_font = pygame.font.SysFont("consolas", max(15, int(18 * scale)))
        self._tiny_font = pygame.font.SysFont("consolas", max(12, int(14 * scale)))

    def _scaled_image(self, path: Any, size: tuple[int, int]) -> Any:
        image = self._load_image(path)
        return pygame.transform.smoothscale(image, size)

    def _load_image(self, path: Any) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        image = pygame.image.load(str(path)).convert_alpha()
        self._image_cache[cache_key] = image
        return image


def simulate_grayspine_intel_ui() -> dict[str, Any]:
    ui = GrayspineIntelUI()
    return ui.build_layout(
        {
            "selected_faction_id": "helix_ward",
            "city": {"name": "Grayspine", "tagline": "A city of failed systems."},
            "factions": [
                {
                    "id": "helix_ward",
                    "name": "Helix Ward",
                    "slogan": "They rewrite it.",
                    "theme": "Biotech",
                    "territory": "Sewer vaults",
                    "goal": "Rewrite survival",
                    "combat_style": "Infection and mutation.",
                    "accent_color": [98, 214, 138],
                    "bosses": [{"name": "Miremother Vexa"}, {"name": "The Graft Saint"}],
                },
                {
                    "id": "blackwire_directorate",
                    "name": "Blackwire Directorate",
                    "slogan": "Order by code.",
                    "theme": "Suppression",
                    "territory": "Data halls",
                    "goal": "Enforce control",
                    "combat_style": "Marks and denial.",
                    "accent_color": [104, 206, 238],
                    "bosses": [{"name": "Director Vale"}],
                },
            ],
            "spine_core": {
                "name": "Spine Core",
                "display_summary": "The buried machine that remembers.",
                "importance": "Whoever controls it shapes the city.",
                "unlocked": False,
            },
            "presentation": {},
        }
    )
