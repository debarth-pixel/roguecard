from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_asset_path

DEFAULT_AUDIO_CUES = {
    "node_select": "node_select.wav",
    "card_play": "card_play.wav",
    "turn_end": "turn_end.wav",
    "player_hit": "player_hit.wav",
    "enemy_hit": "enemy_hit.wav",
    "victory": "victory.wav",
    "defeat": "defeat.wav",
}


class AudioManager:
    def __init__(self) -> None:
        self.loaded_sounds: dict[str, Any] = {}
        self.trigger_history: list[str] = []

    def load_sound(self, sound_id: str, relative_path: str) -> None:
        asset_path = resolve_asset_path("audio", relative_path)
        if pygame is not None and self._mixer_ready() and asset_path.exists():
            try:
                self.loaded_sounds[sound_id] = pygame.mixer.Sound(str(asset_path))
                return
            except pygame.error:
                pass
        self.loaded_sounds[sound_id] = str(asset_path)

    def trigger(self, sound_id: str) -> None:
        self.trigger_history.append(sound_id)
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
                pygame.mixer.music.play(loops)
            except pygame.error:
                return

    def get_state(self) -> dict[str, Any]:
        return {
            "loaded_sounds": list(self.loaded_sounds),
            "trigger_history": list(self.trigger_history),
            "mixer_ready": self._mixer_ready(),
        }

    def _mixer_ready(self) -> bool:
        return pygame is not None and pygame.mixer.get_init() is not None


def simulate_audio_manager() -> dict[str, Any]:
    audio_manager = AudioManager()
    for sound_id, filename in DEFAULT_AUDIO_CUES.items():
        audio_manager.load_sound(sound_id, filename)
    audio_manager.trigger("card_play")
    return audio_manager.get_state()
