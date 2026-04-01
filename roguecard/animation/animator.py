from __future__ import annotations

from typing import Any


class Animator:
    def __init__(self) -> None:
        self.current_state = "idle"
        self.time_in_state = 0.0
        self.history: list[str] = ["idle"]

    def trigger(self, state: str) -> None:
        if not isinstance(state, str) or not state:
            raise ValueError("Animation state must be a non-empty string.")

        self.current_state = state
        self.time_in_state = 0.0
        self.history.append(state)

    def update(self, delta_time: float) -> None:
        if delta_time < 0:
            raise ValueError("Animation delta time cannot be negative.")
        self.time_in_state += delta_time

    def get_state(self) -> dict[str, Any]:
        return {
            "current_state": self.current_state,
            "time_in_state": round(self.time_in_state, 3),
            "history": list(self.history),
        }


def simulate_animator() -> dict[str, Any]:
    animator = Animator()
    animator.trigger("attack")
    animator.update(0.25)
    return animator.get_state()
