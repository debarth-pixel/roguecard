from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import PROJECT_ROOT, SCREEN_HEIGHT, SCREEN_SIZE, SCREEN_WIDTH, resolve_asset_path
from ui.render_utils import draw_screen_scrim

TABLET_ART_PATH = PROJECT_ROOT / "arts" / "map_ui_exterior_overlay.png"
TABLET_ART_SOURCE_SIZE = (1534, 1025)
# Swap the overlay art here if the foreground plate changes later.
# Update TABLET_SCREEN_RECT_ART to match the new screen opening in source-art coordinates.
TABLET_SCREEN_RECT_ART = (303, 167, 928, 676)
TABLET_SCREEN_SAFE_INSET = 18

TABLET_SWAY_X_AMPLITUDE = 3.0
TABLET_SWAY_Y_AMPLITUDE = 2.0
TABLET_SWAY_ROTATION_DEGREES = 0.35
TABLET_SWAY_X_SPEED = 0.62
TABLET_SWAY_Y_SPEED = 0.48
TABLET_SWAY_ROTATION_SPEED = 0.38
TABLET_SWAY_Y_PHASE = 0.95
TABLET_SWAY_ROTATION_PHASE = 1.7

MAP_TO_COMBAT_DURATION = 0.60
MAP_TO_COMBAT_SETTLE_END = 0.05
MAP_TO_COMBAT_SLIDE_END = 0.45
MAP_TO_COMBAT_BACKGROUND_FADE = (0.20, 0.50)
MAP_TO_COMBAT_FOREGROUND_FADE = (0.35, 0.60)
MAP_TO_COMBAT_OFFSET_DISTANCE = SCREEN_HEIGHT + 240

MAP_ENTER_DURATION = 0.48
MAP_ENTER_OFFSET_DISTANCE = SCREEN_HEIGHT + 140

MAP_TO_SHOP_DURATION = 2.05
MAP_TO_SHOP_TABLET_DROP_END = 0.48
MAP_TO_SHOP_APPROACH_START = 0.10
MAP_TO_SHOP_STEP_TIMES = (0.58, 1.02, 1.46)

MERCHANT_TRANSITION_SFX = {
    "walk_start": "merchant_walk_start",
    "walk_step": "merchant_walk_step",
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _ease_in_cubic(progress: float) -> float:
    progress = _clamp(progress, 0.0, 1.0)
    return progress * progress * progress


def _ease_out_cubic(progress: float) -> float:
    progress = _clamp(progress, 0.0, 1.0)
    inverse = 1.0 - progress
    return 1.0 - (inverse * inverse * inverse)


def _ease_in_out_cubic(progress: float) -> float:
    progress = _clamp(progress, 0.0, 1.0)
    if progress < 0.5:
        return 4.0 * progress * progress * progress
    inverse = -2.0 * progress + 2.0
    return 1.0 - ((inverse * inverse * inverse) / 2.0)


class MapTabletView:
    def __init__(self, map_ui: Any, combat_ui: Any, shop_ui: Any) -> None:
        self.map_ui = map_ui
        self.combat_ui = combat_ui
        self.shop_ui = shop_ui
        self._image_cache: dict[str, Any] = {}
        self._sway_time = 0.0
        self._last_pointer_pos = (-1, -1)
        self._transition: dict[str, Any] | None = None
        self._sfx_callback = None

    def preload_assets(self) -> None:
        if pygame is None:
            return
        for path in (TABLET_ART_PATH, resolve_asset_path("ui", "bg_map.png")):
            self._load_image(path)

    def update(self, delta_time: float) -> None:
        if delta_time <= 0:
            return
        if self._transition is None:
            self._sway_time += delta_time
            return
        previous_elapsed = float(self._transition.get("elapsed", 0.0))
        self._transition["elapsed"] = float(self._transition.get("elapsed", 0.0)) + delta_time
        if self._transition["kind"] == "map_to_shop":
            for index, trigger_time in enumerate(MAP_TO_SHOP_STEP_TIMES):
                if previous_elapsed < trigger_time <= float(self._transition["elapsed"]):
                    self._emit_sfx("walk_step")
                    self._transition["step_index"] = index + 1
        if self._transition["elapsed"] >= float(self._transition["duration"]):
            self._transition = None

    def build_layout(self, map_state: dict[str, Any] | None) -> dict[str, Any]:
        geometry = self._geometry_values()
        active_map_state = map_state
        if self._transition is not None and self._transition.get("map_state") is not None:
            active_map_state = self._transition["map_state"]
        screen_rect = geometry["screen_rect"]
        screen_state = None if active_map_state is None else self._screen_map_state(active_map_state, (screen_rect[2], screen_rect[3]))
        return {
            "art_rect": geometry["art_rect"],
            "screen_rect": geometry["screen_rect"],
            "screen_safe_bounds": geometry["safe_bounds"],
            "transition": None if self._transition is None else {
                "kind": self._transition["kind"],
                "elapsed": round(float(self._transition["elapsed"]), 3),
                "duration": round(float(self._transition["duration"]), 3),
            },
            "map_layout": None if screen_state is None else self.map_ui.build_layout(screen_state),
        }

    def handle_event(self, event: Any, map_state: dict[str, Any]) -> dict[str, Any] | None:
        if pygame is None or map_state is None or self._transition is not None:
            return None

        if getattr(event, "type", None) in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            self._last_pointer_pos = tuple(event.pos)

        geometry = self._geometry()
        transform = self._map_transform()
        local_map_state = self._screen_map_state(map_state, geometry["screen_rect"].size)

        if event.type == pygame.MOUSEWHEEL:
            local_pointer = self._pointer_to_screen_local(self._last_pointer_pos, geometry["screen_rect"], transform)
            if local_pointer is None:
                return None
            return self.map_ui.handle_event(event, local_map_state)

        if event.type in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            local_pointer = self._pointer_to_screen_local(tuple(event.pos), geometry["screen_rect"], transform)
            if local_pointer is None:
                if event.type == pygame.MOUSEMOTION:
                    motion_data = dict(event.dict)
                    motion_data["pos"] = (-1, -1)
                    motion_data["rel"] = (0, 0)
                    return self.map_ui.handle_event(pygame.event.Event(event.type, motion_data), local_map_state)
                return None
            event_data = dict(event.dict)
            event_data["pos"] = local_pointer
            if event.type == pygame.MOUSEMOTION:
                event_data["rel"] = (0, 0)
            return self.map_ui.handle_event(pygame.event.Event(event.type, event_data), local_map_state)

        return self.map_ui.handle_event(event, local_map_state)

    def render(
        self,
        surface: Any,
        map_state: dict[str, Any] | None,
        combat_state: dict[str, Any] | None = None,
        shop_state: dict[str, Any] | None = None,
    ) -> None:
        if pygame is None or surface is None:
            return
        if self._transition is None:
            if map_state is None:
                surface.fill((10, 12, 18))
                return
            self._render_map_mode(surface, map_state, transform=self._map_transform())
            return
        if self._transition["kind"] == "map_to_combat":
            self._render_map_to_combat_transition(surface, combat_state or self._transition.get("combat_state"))
            return
        if self._transition["kind"] == "map_to_shop":
            self._render_map_to_shop_transition(surface, shop_state or self._transition.get("shop_state"))
            return
        if self._transition["kind"] == "map_enter":
            active_map_state = map_state or self._transition.get("map_state")
            if active_map_state is None:
                surface.fill((10, 12, 18))
                return
            self._render_map_mode(surface, active_map_state, transform=self._enter_transform())
            return
        if map_state is not None:
            self._render_map_mode(surface, map_state, transform=self._map_transform())

    def begin_map_to_combat_transition(
        self,
        map_state: dict[str, Any],
        combat_state: dict[str, Any],
    ) -> None:
        self._transition = {
            "kind": "map_to_combat",
            "elapsed": 0.0,
            "duration": MAP_TO_COMBAT_DURATION,
            "map_state": copy.deepcopy(map_state),
            "combat_state": copy.deepcopy(combat_state),
        }

    def begin_map_to_shop_transition(
        self,
        map_state: dict[str, Any],
        shop_state: dict[str, Any],
    ) -> None:
        self._transition = {
            "kind": "map_to_shop",
            "elapsed": 0.0,
            "duration": MAP_TO_SHOP_DURATION,
            "map_state": copy.deepcopy(map_state),
            "shop_state": copy.deepcopy(shop_state),
            "step_index": 0,
        }
        self._emit_sfx("walk_start")

    def begin_map_enter_transition(self, map_state: dict[str, Any]) -> None:
        self._transition = {
            "kind": "map_enter",
            "elapsed": 0.0,
            "duration": MAP_ENTER_DURATION,
            "map_state": copy.deepcopy(map_state),
        }

    def is_transition_active(self) -> bool:
        return self._transition is not None

    def suppress_top_bar(self, current_state: str) -> bool:
        return current_state == "map" or self._transition is not None

    def _render_map_mode(
        self,
        surface: Any,
        map_state: dict[str, Any],
        *,
        transform: dict[str, float],
    ) -> None:
        self._render_world_background(surface)
        assembly = self._tablet_assembly(map_state)
        self._blit_transformed_assembly(surface, assembly, transform)

    def _render_map_to_combat_transition(self, surface: Any, combat_state: dict[str, Any] | None) -> None:
        transition = self._transition
        if transition is None:
            return

        self._render_world_background(surface)
        if combat_state is not None:
            background_alpha = self._window_alpha(float(transition["elapsed"]), *MAP_TO_COMBAT_BACKGROUND_FADE)
            if background_alpha > 0:
                background_surface = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
                background_surface.fill((0, 0, 0, 0))
                self.combat_ui.render_background(background_surface, combat_state)
                background_surface.set_alpha(background_alpha)
                surface.blit(background_surface, (0, 0))

        map_state = transition.get("map_state")
        if map_state is not None:
            assembly = self._tablet_assembly(map_state)
            self._blit_transformed_assembly(surface, assembly, self._map_to_combat_transform())

        if combat_state is not None:
            foreground_alpha = self._window_alpha(float(transition["elapsed"]), *MAP_TO_COMBAT_FOREGROUND_FADE)
            if foreground_alpha > 0:
                foreground_surface = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
                foreground_surface.fill((0, 0, 0, 0))
                self.combat_ui.render_foreground(foreground_surface, combat_state)
                foreground_surface.set_alpha(foreground_alpha)
                surface.blit(foreground_surface, (0, 0))

    def _render_map_to_shop_transition(self, surface: Any, shop_state: dict[str, Any] | None) -> None:
        transition = self._transition
        if transition is None:
            return
        active_shop_state = shop_state or transition.get("shop_state")
        if active_shop_state is None:
            surface.fill((10, 12, 18))
            return

        approach_progress = self._map_to_shop_approach_progress()
        sway_phase = approach_progress * math.pi * 3.5
        sway_decay = 1.0 - (approach_progress * 0.35)
        sway_x = math.sin(sway_phase) * 8.0 * sway_decay
        sway_y = abs(math.cos(sway_phase + 0.6)) * 6.0 * sway_decay
        self.shop_ui.render_transition_scene(surface, active_shop_state, approach_progress, sway_x=sway_x, sway_y=sway_y)

        map_state = transition.get("map_state")
        if map_state is not None:
            assembly = self._tablet_assembly(map_state)
            tablet_progress = _clamp(float(transition["elapsed"]) / MAP_TO_SHOP_TABLET_DROP_END, 0.0, 1.0)
            alpha = int(round(255 * (1.0 - _ease_out_cubic(tablet_progress))))
            self._blit_transformed_assembly(surface, assembly, self._map_to_shop_tablet_transform(), alpha=alpha)

        fade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(round(22 * (1.0 - approach_progress)))))
        surface.blit(fade, (0, 0))

    def _render_world_background(self, surface: Any) -> None:
        background = self._scaled_image(resolve_asset_path("ui", "bg_map.png"), surface.get_size())
        surface.blit(background, (0, 0))
        draw_screen_scrim(surface, alpha=112, color=(6, 8, 14))

    def _tablet_assembly(self, map_state: dict[str, Any]) -> Any:
        geometry = self._geometry()
        assembly = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        screen_surface = pygame.Surface(geometry["screen_rect"].size, pygame.SRCALPHA)
        screen_surface.fill((4, 8, 14, 255))
        self.map_ui.render(screen_surface, self._screen_map_state(map_state, geometry["screen_rect"].size))
        assembly.blit(screen_surface, geometry["screen_rect"].topleft)
        self._draw_tablet_shadow(assembly, geometry["screen_rect"])
        overlay = self._scaled_overlay_art(geometry["art_rect"].size)
        assembly.blit(overlay, geometry["art_rect"].topleft)
        return assembly

    def _draw_tablet_shadow(self, surface: Any, screen_rect: Any) -> None:
        shadow_rect = pygame.Rect(screen_rect).inflate(54, 42)
        shadow_surface = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow_surface, (0, 0, 0, 62), shadow_surface.get_rect(), border_radius=28)
        surface.blit(shadow_surface, shadow_rect.topleft)

    def _screen_map_state(self, map_state: dict[str, Any], screen_size: tuple[int, int]) -> dict[str, Any]:
        safe_inset = TABLET_SCREEN_SAFE_INSET
        width = max(1, int(screen_size[0]))
        height = max(1, int(screen_size[1]))
        render_context = {
            "bounds": (
                safe_inset,
                safe_inset,
                max(1, width - (safe_inset * 2)),
                max(1, height - (safe_inset * 2)),
            ),
            "draw_world_background": False,
            "draw_outer_panel": False,
            "scale_canvas_to_viewport": True,
        }
        return {
            **map_state,
            "render_context": render_context,
        }

    def _geometry(self) -> dict[str, Any]:
        geometry = self._geometry_values()
        if pygame is None:
            return geometry
        return {
            "art_rect": pygame.Rect(*geometry["art_rect"]),
            "screen_rect": pygame.Rect(*geometry["screen_rect"]),
            "safe_bounds": pygame.Rect(*geometry["safe_bounds"]),
        }

    def _geometry_values(self) -> dict[str, tuple[int, int, int, int]]:
        art_width, art_height = TABLET_ART_SOURCE_SIZE
        scale = max(SCREEN_WIDTH / art_width, SCREEN_HEIGHT / art_height)
        scaled_width = art_width * scale
        scaled_height = art_height * scale
        offset_x = (SCREEN_WIDTH - scaled_width) / 2.0
        offset_y = (SCREEN_HEIGHT - scaled_height) / 2.0
        art_rect = (
            int(round(offset_x)),
            int(round(offset_y)),
            int(round(scaled_width)),
            int(round(scaled_height)),
        )
        screen_x, screen_y, screen_w, screen_h = TABLET_SCREEN_RECT_ART
        screen_rect = (
            int(round(offset_x + (screen_x * scale))),
            int(round(offset_y + (screen_y * scale))),
            int(round(screen_w * scale)),
            int(round(screen_h * scale)),
        )
        safe_bounds = (
            screen_rect[0] + TABLET_SCREEN_SAFE_INSET,
            screen_rect[1] + TABLET_SCREEN_SAFE_INSET,
            max(1, screen_rect[2] - (TABLET_SCREEN_SAFE_INSET * 2)),
            max(1, screen_rect[3] - (TABLET_SCREEN_SAFE_INSET * 2)),
        )
        return {
            "art_rect": art_rect,
            "screen_rect": screen_rect,
            "safe_bounds": safe_bounds,
        }

    def _map_transform(self) -> dict[str, float]:
        return {
            "offset_x": math.sin(self._sway_time * TABLET_SWAY_X_SPEED) * TABLET_SWAY_X_AMPLITUDE,
            "offset_y": math.sin((self._sway_time * TABLET_SWAY_Y_SPEED) + TABLET_SWAY_Y_PHASE) * TABLET_SWAY_Y_AMPLITUDE,
            "rotation": math.sin((self._sway_time * TABLET_SWAY_ROTATION_SPEED) + TABLET_SWAY_ROTATION_PHASE) * TABLET_SWAY_ROTATION_DEGREES,
        }

    def _map_to_combat_transform(self) -> dict[str, float]:
        transition = self._transition
        if transition is None:
            return self._map_transform()
        elapsed = float(transition["elapsed"])
        settle_progress = _clamp(elapsed / MAP_TO_COMBAT_SETTLE_END, 0.0, 1.0)
        settle_offset = math.sin(settle_progress * math.pi) * 3.0 if elapsed < MAP_TO_COMBAT_SETTLE_END else 0.0
        slide_progress = _clamp(
            (elapsed - MAP_TO_COMBAT_SETTLE_END) / max(0.001, MAP_TO_COMBAT_SLIDE_END - MAP_TO_COMBAT_SETTLE_END),
            0.0,
            1.0,
        )
        slide_eased = _ease_in_cubic(slide_progress)
        return {
            "offset_x": 0.0,
            "offset_y": settle_offset + (slide_eased * MAP_TO_COMBAT_OFFSET_DISTANCE),
            "rotation": slide_eased * 0.35,
        }

    def _enter_transform(self) -> dict[str, float]:
        transition = self._transition
        if transition is None:
            return self._map_transform()
        progress = _ease_out_cubic(_clamp(float(transition["elapsed"]) / MAP_ENTER_DURATION, 0.0, 1.0))
        remaining = 1.0 - progress
        return {
            "offset_x": 0.0,
            "offset_y": remaining * MAP_ENTER_OFFSET_DISTANCE,
            "rotation": remaining * 0.3,
        }

    def _map_to_shop_tablet_transform(self) -> dict[str, float]:
        transition = self._transition
        if transition is None:
            return self._map_transform()
        drop_progress = _clamp(float(transition["elapsed"]) / MAP_TO_SHOP_TABLET_DROP_END, 0.0, 1.0)
        eased = _ease_in_cubic(drop_progress)
        settle = math.sin(min(1.0, drop_progress * 1.25) * math.pi) * 3.0 if drop_progress < 1.0 else 0.0
        return {
            "offset_x": 0.0,
            "offset_y": settle + (eased * (SCREEN_HEIGHT + 260)),
            "rotation": eased * 0.42,
        }

    def _map_to_shop_approach_progress(self) -> float:
        transition = self._transition
        if transition is None:
            return 0.0
        elapsed = float(transition["elapsed"])
        return _clamp(
            (elapsed - MAP_TO_SHOP_APPROACH_START) / max(0.001, MAP_TO_SHOP_DURATION - MAP_TO_SHOP_APPROACH_START),
            0.0,
            1.0,
        )

    def _window_alpha(self, elapsed: float, start: float, end: float) -> int:
        if elapsed <= start:
            return 0
        if elapsed >= end:
            return 255
        return int(round(_ease_in_out_cubic((elapsed - start) / max(0.001, end - start)) * 255))

    def _blit_transformed_assembly(self, surface: Any, assembly: Any, transform: dict[str, float], *, alpha: int = 255) -> None:
        offset_x = float(transform.get("offset_x", 0.0))
        offset_y = float(transform.get("offset_y", 0.0))
        rotation = float(transform.get("rotation", 0.0))
        source = assembly
        if alpha < 255:
            source = assembly.copy()
            source.set_alpha(max(0, min(255, alpha)))
        if abs(rotation) < 0.001:
            surface.blit(source, (int(round(offset_x)), int(round(offset_y))))
            return
        rotated = pygame.transform.rotozoom(source, rotation, 1.0)
        center = (int(round((SCREEN_WIDTH / 2) + offset_x)), int(round((SCREEN_HEIGHT / 2) + offset_y)))
        surface.blit(rotated, rotated.get_rect(center=center))

    def _pointer_to_screen_local(
        self,
        pointer: tuple[int, int],
        screen_rect: Any,
        transform: dict[str, float],
    ) -> tuple[int, int] | None:
        if pointer == (-1, -1):
            return None
        local_pointer = self._inverse_transform_position(pointer, transform)
        if local_pointer is None:
            return None
        assembly_point = (int(round(local_pointer[0])), int(round(local_pointer[1])))
        if not pygame.Rect(screen_rect).collidepoint(assembly_point):
            return None
        return (assembly_point[0] - int(screen_rect.x), assembly_point[1] - int(screen_rect.y))

    def _inverse_transform_position(
        self,
        position: tuple[int, int],
        transform: dict[str, float],
    ) -> tuple[float, float] | None:
        center_x = (SCREEN_WIDTH / 2.0) + float(transform.get("offset_x", 0.0))
        center_y = (SCREEN_HEIGHT / 2.0) + float(transform.get("offset_y", 0.0))
        dx = float(position[0]) - center_x
        dy = float(position[1]) - center_y
        radians = math.radians(float(transform.get("rotation", 0.0)))
        cosine = math.cos(radians)
        sine = math.sin(radians)
        local_dx = (cosine * dx) + (sine * dy)
        local_dy = (-sine * dx) + (cosine * dy)
        return ((SCREEN_WIDTH / 2.0) + local_dx, (SCREEN_HEIGHT / 2.0) + local_dy)

    def _scaled_image(self, path: Path, size: tuple[int, int]) -> Any:
        return pygame.transform.smoothscale(self._load_image(path), size)

    def _scaled_overlay_art(self, size: tuple[int, int]) -> Any:
        return pygame.transform.smoothscale(self._load_overlay_art(), size)

    def _load_image(self, path: Path) -> Any:
        cache_key = str(path)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            image = pygame.Surface((64, 64), pygame.SRCALPHA)
            image.fill((255, 0, 160, 180))
        self._image_cache[cache_key] = image
        return image

    def _load_overlay_art(self) -> Any:
        cache_key = f"{TABLET_ART_PATH}::screen_cutout"
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        overlay = self._load_image(TABLET_ART_PATH).copy()
        overlay.fill((0, 0, 0, 0), pygame.Rect(*TABLET_SCREEN_RECT_ART))
        self._image_cache[cache_key] = overlay
        return overlay

    def set_sfx_callback(self, callback: Any) -> None:
        self._sfx_callback = callback

    def _emit_sfx(self, cue_id: str) -> None:
        if self._sfx_callback is None:
            return
        self._sfx_callback(MERCHANT_TRANSITION_SFX.get(cue_id, cue_id))
