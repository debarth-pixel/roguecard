from __future__ import annotations

import logging
from typing import Any, Callable

try:
    import pygame
except ImportError:  # pragma: no cover - pygame is optional for headless verification.
    pygame = None

from config import (
    ASSET_AUDIO_ROOT,
    DEFAULT_MASTER_VOLUME,
    DEFAULT_MUSIC_VOLUME,
    DIRECT_AUDIO_ROOT,
    MAX_VOLUME,
    MIN_VOLUME,
    resolve_audio_path,
)

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

CHOSEN_AUDIO_CUES = {
    "card_purged_burn": "card_purged_burn.wav",
    "merchant_terminal_boot": "merchant_terminal_turning_on.wav",
    "merchant_button_hover": "hover_over_merchant_tiles.ogg",
    "merchant_button_click": "main_merchant_computer_click.wav",
}

CHOSEN_MUSIC_TRACKS = {
    "title_song": "music/title_song.mp3",
    "map_event_audio": "music/map_event_audio.mp3",
    "to_combat_transition": "music/to_combat_transition.mp3",
    "combat_1_intense": "music/combat_1_intense.mp3",
    "combat_2_lowpulse": "music/combat_2_lowpulse.mp3",
    "combat_3_medium": "music/combat_3_medium.mp3",
}

TRACK_GAIN_MULTIPLIERS = {
    "title_song": 0.72,
    "map_event_audio": 0.62,
    "to_combat_transition": 0.66,
    "combat_1_intense": 0.58,
    "combat_2_lowpulse": 0.58,
    "combat_3_medium": 0.58,
}

COMBAT_TRACK_SEQUENCE = (
    "combat_1_intense",
    "combat_2_lowpulse",
    "combat_3_medium",
)

MUSIC_SCENES = {"title", "noncombat", "combat", "silence"}
NONCOMBAT_SCENE_STATES = {"character_select", "modifier_draft", "map", "shop", "event", "reward"}

LOGGER = logging.getLogger(__name__)


class AudioManager:
    def __init__(self) -> None:
        self.loaded_sounds: dict[str, Any] = {}
        self.trigger_history: list[str] = []
        self.master_volume = DEFAULT_MASTER_VOLUME
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.muted = False
        self.current_scene = "silence"
        self.requested_track_id: str | None = None
        self.requested_track_path: str | None = None
        self.current_track_id: str | None = None
        self.current_track_path: str | None = None
        self._current_track_gain = 1.0
        self._current_music_scale = 0.0
        self._fade_state: dict[str, Any] | None = None
        self._combat_track_index = 0
        self._combat_transition_target: str | None = None

    def load_sound(self, sound_id: str, relative_path: str) -> None:
        asset_path = resolve_audio_path(relative_path)
        self._log_audio_resolution(sound_id, asset_path)
        if not asset_path.exists():
            LOGGER.warning("Audio cue '%s' is missing: %s", sound_id, asset_path)
            self.loaded_sounds[sound_id] = str(asset_path)
            return
        if pygame is not None and self._mixer_ready() and asset_path.exists():
            try:
                sound = pygame.mixer.Sound(str(asset_path))
                sound.set_volume(self._effective_volume(self.master_volume))
                self.loaded_sounds[sound_id] = sound
                return
            except pygame.error as exc:
                LOGGER.warning("Failed to load sound cue '%s' from %s: %s", sound_id, asset_path, exc)
        self.loaded_sounds[sound_id] = str(asset_path)

    def trigger(self, sound_id: str) -> None:
        self.trigger_history.append(sound_id)
        if self.muted:
            return
        sound = self.loaded_sounds.get(sound_id)
        if sound is None:
            LOGGER.debug("Audio cue '%s' was triggered before loading.", sound_id)
            return
        if pygame is not None and hasattr(sound, "play"):
            try:
                sound.play()
            except pygame.error as exc:
                LOGGER.warning("Failed to play sound cue '%s': %s", sound_id, exc)
                return

    def play_music(self, relative_path: str, loops: int = -1) -> None:
        asset_path = resolve_audio_path(relative_path)
        self.requested_track_id = relative_path
        self.requested_track_path = str(asset_path)
        self._log_audio_resolution(relative_path, asset_path)
        if not asset_path.exists():
            LOGGER.warning("Music track is missing: %s", asset_path)
            return
        if pygame is None or not self._mixer_ready():
            LOGGER.debug("Music track '%s' requested but mixer is not ready.", asset_path)
            return
        try:
            pygame.mixer.music.load(str(asset_path))
            pygame.mixer.music.set_volume(self._effective_volume(self.music_volume))
            pygame.mixer.music.play(loops)
            self.current_track_id = relative_path
            self.current_track_path = str(asset_path)
            self._current_track_gain = 1.0
            self._current_music_scale = 1.0
        except pygame.error as exc:
            LOGGER.warning("Failed to load/play music track from %s: %s", asset_path, exc)
            self.current_track_id = None
            self.current_track_path = None

    def set_master_volume(self, volume: float) -> float:
        self.master_volume = self._clamp_volume(volume)
        self._refresh_sound_volumes()
        return self.master_volume

    def adjust_master_volume(self, delta: float) -> float:
        return self.set_master_volume(self.master_volume + delta)

    def set_music_volume(self, volume: float) -> float:
        self.music_volume = self._clamp_volume(volume)
        self._apply_music_volume()
        return self.music_volume

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        self._refresh_sound_volumes()
        self._apply_music_volume()
        return self.muted

    def set_muted(self, muted: bool) -> bool:
        self.muted = bool(muted)
        self._refresh_sound_volumes()
        self._apply_music_volume()
        return self.muted

    def apply_settings(self, settings: dict[str, Any]) -> None:
        self.master_volume = self._clamp_volume(settings.get("master_volume", self.master_volume))
        self.music_volume = self._clamp_volume(settings.get("music_volume", self.music_volume))
        self.muted = bool(settings.get("muted", self.muted))
        self._refresh_sound_volumes()
        self._apply_music_volume()

    def update(self, delta_time: float) -> None:
        self._advance_fade(max(0.0, float(delta_time)))

        if pygame is None or not self._mixer_ready():
            return

        if self.current_track_id is None or self._fade_state is not None:
            return

        try:
            track_playing = pygame.mixer.music.get_busy()
        except pygame.error:
            return

        if not track_playing:
            self._handle_track_end()

    def set_scene(self, scene_id: str, *, resume_existing_combat: bool = False, force: bool = False) -> None:
        if scene_id not in MUSIC_SCENES:
            raise ValueError(f"Unsupported music scene: {scene_id}")

        if not force and scene_id == self.current_scene:
            if scene_id != "combat" or not resume_existing_combat:
                return

        if scene_id == "title":
            self.current_scene = "title"
            self._combat_transition_target = None
            self._switch_standard_track("title_song", fade_out_duration=0.35, fade_in_duration=0.45)
            return

        if scene_id == "noncombat":
            prior_scene = self.current_scene
            self.current_scene = "noncombat"
            self._combat_transition_target = None
            fade_out = 0.30 if prior_scene == "combat" or self.current_track_id == "to_combat_transition" else 0.35
            self._switch_standard_track("map_event_audio", fade_out_duration=fade_out, fade_in_duration=0.45)
            return

        if scene_id == "combat":
            self.current_scene = "combat"
            if resume_existing_combat:
                self._start_combat_loop_entry(with_transition=False, fade_in_duration=0.40)
            else:
                self._start_combat_loop_entry(with_transition=True, fade_in_duration=1.20)
            return

        self.current_scene = "silence"
        self._combat_transition_target = None
        self._fade_out_and_stop(0.50)

    def get_state(self) -> dict[str, Any]:
        return {
            "loaded_sounds": list(self.loaded_sounds),
            "trigger_history": list(self.trigger_history),
            "mixer_ready": self._mixer_ready(),
            "master_volume": round(self.master_volume, 2),
            "music_volume": round(self.music_volume, 2),
            "muted": self.muted,
            "current_scene": self.current_scene,
            "requested_track_id": self.requested_track_id,
            "requested_track_path": self.requested_track_path,
            "current_track_id": self.current_track_id,
            "current_track_path": self.current_track_path,
            "combat_track_index": self._combat_track_index,
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

    def _switch_standard_track(
        self,
        track_id: str,
        *,
        fade_out_duration: float,
        fade_in_duration: float,
    ) -> None:
        if self.current_track_id == track_id and self._combat_transition_target is None:
            return
        if self.current_track_id is None:
            self._play_track(track_id, loops=-1, start_scale=0.0)
            self._start_fade(0.0, 1.0, fade_in_duration)
            return
        self._fade_out_and_then(
            fade_out_duration,
            lambda: self._play_track(track_id, loops=-1, start_scale=0.0) or self._start_fade(0.0, 1.0, fade_in_duration),
        )

    def _start_combat_loop_entry(self, *, with_transition: bool, fade_in_duration: float) -> None:
        self._fade_state = None
        if with_transition:
            self._combat_transition_target = "combat_entry"
            self._play_track("to_combat_transition", loops=0, start_scale=1.0)
            return
        combat_track_id = COMBAT_TRACK_SEQUENCE[self._combat_track_index % len(COMBAT_TRACK_SEQUENCE)]
        self._combat_transition_target = None
        self._play_track(combat_track_id, loops=0, start_scale=0.15)
        self._start_fade(0.15, 1.0, fade_in_duration)

    def _fade_out_and_stop(self, duration: float) -> None:
        if self.current_track_id is None:
            return
        self._fade_out_and_then(duration, self._stop_music)

    def _fade_out_and_then(self, duration: float, callback: Callable[[], None]) -> None:
        if self.current_track_id is None:
            callback()
            return
        self._start_fade(self._current_music_scale, 0.0, duration, on_complete=callback)

    def _start_fade(
        self,
        start_scale: float,
        end_scale: float,
        duration: float,
        *,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        if duration <= 0:
            self._current_music_scale = end_scale
            self._apply_music_volume()
            if on_complete is not None:
                on_complete()
            return
        self._fade_state = {
            "start_scale": start_scale,
            "end_scale": end_scale,
            "duration": max(0.01, duration),
            "elapsed": 0.0,
            "on_complete": on_complete,
        }
        self._current_music_scale = start_scale
        self._apply_music_volume()

    def _advance_fade(self, delta_time: float) -> None:
        if self._fade_state is None:
            return
        fade_state = self._fade_state
        fade_state["elapsed"] = min(fade_state["duration"], fade_state["elapsed"] + delta_time)
        progress = fade_state["elapsed"] / fade_state["duration"]
        start_scale = float(fade_state["start_scale"])
        end_scale = float(fade_state["end_scale"])
        self._current_music_scale = start_scale + ((end_scale - start_scale) * progress)
        self._apply_music_volume()
        if progress < 1.0:
            return
        callback = fade_state.get("on_complete")
        self._fade_state = None
        if callback is not None:
            callback()

    def _handle_track_end(self) -> None:
        if self.current_track_id == "to_combat_transition":
            target = self._combat_transition_target
            self._combat_transition_target = None
            if self.current_scene != "combat":
                self._stop_music()
                return
            if target == "combat_entry":
                combat_track_id = COMBAT_TRACK_SEQUENCE[self._combat_track_index % len(COMBAT_TRACK_SEQUENCE)]
                self._play_track(combat_track_id, loops=0, start_scale=0.15)
                self._start_fade(0.15, 1.0, 1.20)
                return
            if target == "combat_rotate":
                self._combat_track_index = (self._combat_track_index + 1) % len(COMBAT_TRACK_SEQUENCE)
                combat_track_id = COMBAT_TRACK_SEQUENCE[self._combat_track_index]
                self._play_track(combat_track_id, loops=0, start_scale=0.15)
                self._start_fade(0.15, 1.0, 1.20)
                return
            self._stop_music()
            return

        if self.current_track_id in COMBAT_TRACK_SEQUENCE and self.current_scene == "combat":
            self._combat_transition_target = "combat_rotate"
            self._play_track("to_combat_transition", loops=0, start_scale=1.0)
            return

        if self.current_scene == "silence":
            self._stop_music()

    def _play_track(self, track_id: str, *, loops: int, start_scale: float) -> None:
        relative_path = CHOSEN_MUSIC_TRACKS[track_id]
        asset_path = resolve_audio_path(relative_path)
        self._fade_state = None
        self.requested_track_id = track_id
        self.requested_track_path = str(asset_path)
        self._current_track_gain = TRACK_GAIN_MULTIPLIERS.get(track_id, 1.0)
        self._current_music_scale = start_scale
        self._log_audio_resolution(track_id, asset_path)
        if not asset_path.exists():
            LOGGER.warning("Music track '%s' is missing: %s", track_id, asset_path)
            self.current_track_id = None
            self.current_track_path = None
            return
        if pygame is None or not self._mixer_ready():
            LOGGER.debug("Music track '%s' requested but mixer is not ready.", track_id)
            self.current_track_id = None
            self.current_track_path = None
            return
        try:
            pygame.mixer.music.load(str(asset_path))
            pygame.mixer.music.play(loops)
            self.current_track_id = track_id
            self.current_track_path = str(asset_path)
            self._apply_music_volume()
        except pygame.error as exc:
            LOGGER.warning("Failed to load/play music track '%s' from %s: %s", track_id, asset_path, exc)
            self.current_track_id = None
            self.current_track_path = None

    def _stop_music(self) -> None:
        if pygame is not None and self._mixer_ready():
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        self.current_track_id = None
        self.current_track_path = None
        self._current_track_gain = 1.0
        self._current_music_scale = 0.0
        self._fade_state = None

    def _log_audio_resolution(self, audio_id: str, resolved_path: Any) -> None:
        try:
            path = resolved_path.resolve()
        except Exception:
            path = resolved_path
        if isinstance(resolved_path, type(DIRECT_AUDIO_ROOT)) and resolved_path.is_relative_to(DIRECT_AUDIO_ROOT):
            LOGGER.debug("Audio '%s' resolved from direct audio root: %s", audio_id, path)
        elif isinstance(resolved_path, type(ASSET_AUDIO_ROOT)) and resolved_path.is_relative_to(ASSET_AUDIO_ROOT):
            LOGGER.debug("Audio '%s' resolved from assets/audio fallback: %s", audio_id, path)
        else:
            LOGGER.debug("Audio '%s' resolved to %s", audio_id, path)

    def _apply_music_volume(self) -> None:
        if pygame is None or not self._mixer_ready():
            return
        track_volume = self.music_volume * self._current_track_gain * self._current_music_scale
        try:
            pygame.mixer.music.set_volume(self._effective_volume(track_volume))
        except pygame.error:
            pass


def simulate_audio_manager() -> dict[str, Any]:
    audio_manager = AudioManager()
    for sound_id, filename in {**DEFAULT_AUDIO_CUES, **CHOSEN_AUDIO_CUES}.items():
        audio_manager.load_sound(sound_id, filename)
    audio_manager.set_scene("title", force=True)
    audio_manager.trigger("card_purged_burn")
    title_track_path = resolve_audio_path(CHOSEN_MUSIC_TRACKS["title_song"])
    state = audio_manager.get_state()
    state["title_track_exists"] = title_track_path.exists()
    state["title_track_resolved_path"] = str(title_track_path)
    return state
