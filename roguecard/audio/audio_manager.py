from __future__ import annotations

from typing import Any

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import resolve_asset_path


class AudioManager:
    def __init__(self) -> None:
        self.loaded_sounds: dict[str, Any] = {}
        self.trigger_history: list[str] = []

    def load_sound(self, sound_id: str, relative_path: str) -> None:
        asset_path = resolve_asset_path("audio", relative_path)
        if pygame is not None and pygame.mixer.get_init():
            self.loaded_sounds[sound_id] = pygame.mixer.Sound(str(asset_path))
        else:
            self.loaded_sounds[sound_id] = str(asset_path)

    def trigger(self, sound_id: str) -> None:
        self.trigger_history.append(sound_id)
        sound = self.loaded_sounds.get(sound_id)
        if pygame is not None and hasattr(sound, "play"):
            sound.play()

    def play_music(self, relative_path: str, loops: int = -1) -> None:
        asset_path = resolve_asset_path("audio", relative_path)
        if pygame is not None and pygame.mixer.get_init():
            pygame.mixer.music.load(str(asset_path))
            pygame.mixer.music.play(loops)

    def get_state(self) -> dict[str, Any]:
        return {
            "loaded_sounds": list(self.loaded_sounds),
            "trigger_history": list(self.trigger_history),
        }


def simulate_audio_manager() -> dict[str, Any]:
    audio_manager = AudioManager()
    audio_manager.load_sound("attack", "attack.wav")
    audio_manager.trigger("attack")
    return audio_manager.get_state()
