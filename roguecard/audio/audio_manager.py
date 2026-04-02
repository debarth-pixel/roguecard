from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import DEFAULT_MASTER_VOLUME, DEFAULT_MUSIC_VOLUME, MAX_VOLUME, MIN_VOLUME, resolve_asset_path

DEFAULT_AUDIO_CUES = {
    "node_select": "node_select.wav",
    "card_play": "card_play.wav",
    "turn_end": "turn_end.wav",
    "player_hit": "player_hit.wav",
    "enemy_hit": "enemy_hit.wav",
    "block": "block.wav",
    "heal": "heal.wav",
    "deny": "deny.wav",
    "menu_open": "menu_open.wav",
    "victory": "victory.wav",
    "defeat": "defeat.wav",
}


class AudioManager:
    def __init__(self) -> None:
        self.loaded_sounds: dict[str, Any] = {}
        self.trigger_history: list[str] = []
        self.master_volume = DEFAULT_MASTER_VOLUME
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.muted = False

    def load_sound(self, sound_id: str, relative_path: str) -> None:
        asset_path = resolve_asset_path("audio", relative_path)
        if pygame is not None and self._mixer_ready() and asset_path.exists():
            try:
                sound = pygame.mixer.Sound(str(asset_path))
                sound.set_volume(self._effective_volume(self.master_volume))
                self.loaded_sounds[sound_id] = sound
                return
            except pygame.error:
                pass
        self.loaded_sounds[sound_id] = str(asset_path)

    def trigger(self, sound_id: str) -> None:
        self.trigger_history.append(sound_id)
        if self.muted:
            return
        sound = self.loaded_sounds.get(sound_id)
        if pygame is not None and hasattr(sound, "play"):
            try:
                sound.play()
            except pygame.error:
                return

    def play_music(self, relative_path: str, loops: int = -1) -> None:
        asset_path = resolve_asset_path("audio", relative_path)
        if pygame is not None and self._mixer_ready() and asset_path.exists():
            try:
                pygame.mixer.music.load(str(asset_path))
                pygame.mixer.music.set_volume(self._effective_volume(self.music_volume))
                pygame.mixer.music.play(loops)
            except pygame.error:
                return

    def set_master_volume(self, volume: float) -> float:
        self.master_volume = self._clamp_volume(volume)
        self._refresh_sound_volumes()
        return self.master_volume

    def adjust_master_volume(self, delta: float) -> float:
        return self.set_master_volume(self.master_volume + delta)

    def set_music_volume(self, volume: float) -> float:
        self.music_volume = self._clamp_volume(volume)
        if pygame is not None and self._mixer_ready():
            try:
                pygame.mixer.music.set_volume(self._effective_volume(self.music_volume))
            except pygame.error:
                pass
        return self.music_volume

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        self._refresh_sound_volumes()
        if pygame is not None and self._mixer_ready():
            try:
                pygame.mixer.music.set_volume(self._effective_volume(self.music_volume))
            except pygame.error:
                pass
        return self.muted

    def set_muted(self, muted: bool) -> bool:
        self.muted = bool(muted)
        self._refresh_sound_volumes()
        if pygame is not None and self._mixer_ready():
            try:
                pygame.mixer.music.set_volume(self._effective_volume(self.music_volume))
            except pygame.error:
                pass
        return self.muted

    def apply_settings(self, settings: dict[str, Any]) -> None:
        self.master_volume = self._clamp_volume(settings.get("master_volume", self.master_volume))
        self.music_volume = self._clamp_volume(settings.get("music_volume", self.music_volume))
        self.muted = bool(settings.get("muted", self.muted))
        self._refresh_sound_volumes()
        if pygame is not None and self._mixer_ready():
            try:
                pygame.mixer.music.set_volume(self._effective_volume(self.music_volume))
            except pygame.error:
                pass

    def get_state(self) -> dict[str, Any]:
        return {
            "loaded_sounds": list(self.loaded_sounds),
            "trigger_history": list(self.trigger_history),
            "mixer_ready": self._mixer_ready(),
            "master_volume": round(self.master_volume, 2),
            "music_volume": round(self.music_volume, 2),
            "muted": self.muted,
        }

    def _mixer_ready(self) -> bool:
        return pygame is not None and pygame.mixer.get_init() is not None

    def _refresh_sound_volumes(self) -> None:
        if pygame is None:
            return
        volume = self._effective_volume(self.master_volume)
        for sound in self.loaded_sounds.values():
            if hasattr(sound, "set_volume"):
                try:
                    sound.set_volume(volume)
                except pygame.error:
                    continue

    def _effective_volume(self, volume: float) -> float:
        return 0.0 if self.muted else self._clamp_volume(volume)

    def _clamp_volume(self, volume: float) -> float:
        try:
            numeric_volume = float(volume)
        except (TypeError, ValueError):
            numeric_volume = DEFAULT_MASTER_VOLUME
        return max(MIN_VOLUME, min(MAX_VOLUME, numeric_volume))


def simulate_audio_manager() -> dict[str, Any]:
    audio_manager = AudioManager()
    for sound_id, filename in DEFAULT_AUDIO_CUES.items():
        audio_manager.load_sound(sound_id, filename)
    audio_manager.trigger("card_play")
    return audio_manager.get_state()
