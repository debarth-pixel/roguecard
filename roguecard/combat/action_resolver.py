from __future__ import annotations

from typing import Any


class ActionResolver:
    def resolve(
        self,
        action: dict[str, Any],
        source: Any,
        target: Any,
        combat_manager: Any = None,
    ) -> dict[str, Any]:
        if not isinstance(action, dict):
            raise ValueError("Resolved actions must be dictionaries.")

        action_type = action.get("type")
        value = action.get("value")

        if not isinstance(action_type, str) or not action_type:
            raise ValueError("Resolved actions require a non-empty type string.")
        if not isinstance(value, int):
            raise ValueError("Resolved actions require an integer value.")

        if action_type == "damage":
            if not hasattr(target, "take_damage"):
                raise ValueError("Damage actions require a target with take_damage().")
            amount = target.take_damage(value)
            return {"type": action_type, "value": value, "applied": amount}

        if action_type == "block":
            if not hasattr(target, "gain_block"):
                raise ValueError("Block actions require a target with gain_block().")
            target.gain_block(value)
            return {"type": action_type, "value": value, "applied": value}

        if action_type == "heal":
            if not hasattr(target, "heal"):
                raise ValueError("Heal actions require a target with heal().")
            target.heal(value)
            return {"type": action_type, "value": value, "applied": value}

        if action_type == "draw":
            if not hasattr(target, "deck_manager") or target.deck_manager is None:
                raise ValueError("Draw actions require a target with an attached deck manager.")
            drawn = target.deck_manager.draw_cards(value)
            return {"type": action_type, "value": value, "applied": len(drawn)}

        if action_type == "energy":
            if not hasattr(target, "energy"):
                raise ValueError("Energy actions require a target with energy.")
            target.energy += value
            return {"type": action_type, "value": value, "applied": value}

        raise ValueError(f"Unsupported action type: {action_type}")


def simulate_action_resolver() -> dict[str, Any]:
    from entities.enemy import Enemy
    from entities.player import Player

    resolver = ActionResolver()
    player = Player()
    enemy = Enemy(
        id="enemy_basic_01",
        name="Street Punk",
        max_hp=40,
        intent_pattern=["attack", "defend"],
    )
    damage_resolution = resolver.resolve({"type": "damage", "value": 6}, source=player, target=enemy)
    block_resolution = resolver.resolve({"type": "block", "value": 5}, source=player, target=player)
    return {
        "damage_resolution": damage_resolution,
        "block_resolution": block_resolution,
        "enemy_hp": enemy.current_hp,
        "player_block": player.block,
    }
