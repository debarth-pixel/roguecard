from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_art_path


COMBAT_UI_ASSET_ROOT = resolve_art_path("combat_ui")

COMBAT_UI_ASSETS = {
    "background": "combat_background.png",
    "foreground": "combat_foreground.png",
    "midplane": "combat_midplane.png",
    "draw_pile_holder": "draw_pile_holder.png",
    "drift_gauge_full": "drift_gauge_full.png",
    "drift_gauge_low": "drift_gauge_low.png",
    "card_platform": "foregroud_card_platform.png",
    "hud_data_capsule": "hud_data_capsule.png",
    "pause_button_normal": "pause_button_normal.png",
    "pause_button_pressed": "pause_button_pressed.png",
    "relic_tray_rail": "relic_tray_rail.png",
    "top_machine_hud_frame": "top_machine_hud_frame.png",
    "discard_holder": "used_cards_discard_holder.png",
}


class CombatUIAssets:
    def __init__(self) -> None:
        self._source_cache: dict[str, Any] = {}
        self._trim_cache: dict[str, Any] = {}
        self._scaled_cache: dict[tuple[str, int, int, bool], Any] = {}
        self._cover_cache: dict[tuple[str, int, int], Any] = {}

    def preload(self) -> None:
        if pygame is None:
            return
        for asset_name in COMBAT_UI_ASSETS:
            self._source(asset_name)

    def validate(self) -> dict[str, Any]:
        missing = []
        for filename in COMBAT_UI_ASSETS.values():
            path = COMBAT_UI_ASSET_ROOT / filename
            if not path.exists():
                missing.append(str(path))
        return {
            "asset_count": len(COMBAT_UI_ASSETS),
            "missing": missing,
        }

    def get(self, asset_name: str, target_size: tuple[int, int] | None = None, *, trim: bool = True) -> Any | None:
        if pygame is None:
            return None
        source = self._trimmed(asset_name) if trim else self._source(asset_name)
        if target_size is None:
            return source.copy()
        width = max(1, int(target_size[0]))
        height = max(1, int(target_size[1]))
        cache_key = (asset_name, width, height, trim)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached.copy()
        scaled = pygame.transform.smoothscale(source, (width, height))
        self._scaled_cache[cache_key] = scaled
        return scaled.copy()

    def blit(
        self,
        surface: Any,
        asset_name: str,
        rect: Any,
        *,
        trim: bool = True,
        alpha: int | None = None,
    ) -> None:
        if pygame is None or surface is None:
            return
        target_rect = pygame.Rect(rect)
        if target_rect.width <= 0 or target_rect.height <= 0:
            return
        image = self.get(asset_name, target_rect.size, trim=trim)
        if image is None:
            return
        if alpha is not None:
            image.set_alpha(max(0, min(255, int(alpha))))
        surface.blit(image, target_rect.topleft)

    def blit_cover(self, surface: Any, asset_name: str, rect: Any, *, alpha: int | None = None) -> None:
        if pygame is None or surface is None:
            return
        target_rect = pygame.Rect(rect)
        if target_rect.width <= 0 or target_rect.height <= 0:
            return
        image = self._cover(asset_name, target_rect.size)
        if alpha is not None:
            image = image.copy()
            image.set_alpha(max(0, min(255, int(alpha))))
        surface.blit(image, target_rect.topleft)

    def _source(self, asset_name: str) -> Any:
        cached = self._source_cache.get(asset_name)
        if cached is not None:
            return cached
        if pygame is None:
            raise RuntimeError("Pygame is required to load combat UI assets.")
        filename = COMBAT_UI_ASSETS.get(asset_name)
        if filename is None:
            raise ValueError(f"Unknown combat UI asset: {asset_name}")
        path = COMBAT_UI_ASSET_ROOT / filename
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (FileNotFoundError, pygame.error) as error:
            raise ValueError(f"Unable to load combat UI asset: {path}") from error
        self._source_cache[asset_name] = image
        return image

    def _trimmed(self, asset_name: str) -> Any:
        cached = self._trim_cache.get(asset_name)
        if cached is not None:
            return cached
        source = self._source(asset_name)
        bounds = source.get_bounding_rect()
        if bounds.width <= 0 or bounds.height <= 0:
            trimmed = source.copy()
        else:
            trimmed = source.subsurface(bounds).copy()
        self._trim_cache[asset_name] = trimmed
        return trimmed

    def _cover(self, asset_name: str, size: tuple[int, int]) -> Any:
        width = max(1, int(size[0]))
        height = max(1, int(size[1]))
        cache_key = (asset_name, width, height)
        cached = self._cover_cache.get(cache_key)
        if cached is not None:
            return cached.copy()
        source = self._source(asset_name)
        source_width, source_height = source.get_size()
        scale = max(width / max(1, source_width), height / max(1, source_height))
        scaled_size = (
            max(1, int(round(source_width * scale))),
            max(1, int(round(source_height * scale))),
        )
        scaled = pygame.transform.smoothscale(source, scaled_size)
        crop_rect = pygame.Rect(0, 0, width, height)
        crop_rect.center = scaled.get_rect().center
        covered = scaled.subsurface(crop_rect).copy()
        self._cover_cache[cache_key] = covered
        return covered.copy()


combat_ui_assets = CombatUIAssets()
