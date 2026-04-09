from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALLOWED_NODE_TYPES = {"combat", "elite", "shop", "event", "boss"}


@dataclass
class Node:
    node_id: str
    node_type: str
    floor: int
    column: int
    map_id: str = ""
    route_floor: int = 0
    campaign_floor: int = 0
    node_tier: str = "normal"
    render_x: int = 0
    render_y: int = 0
    encounter_hook_id: str | None = None
    boss_slot_id: str | None = None
    enemy_ids: list[str] = field(default_factory=list)
    next_nodes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id:
            raise ValueError("Node id must be a non-empty string.")
        if self.node_type not in ALLOWED_NODE_TYPES:
            raise ValueError(f"Unsupported node type: {self.node_type}")
        if not isinstance(self.floor, int) or self.floor < 0:
            raise ValueError("Node floor must be a non-negative integer.")
        if not isinstance(self.column, int) or self.column < 0:
            raise ValueError("Node column must be a non-negative integer.")
        if not isinstance(self.map_id, str) or not self.map_id:
            raise ValueError("Node map_id must be a non-empty string.")
        if not isinstance(self.route_floor, int) or self.route_floor < 0:
            raise ValueError("Node route_floor must be a non-negative integer.")
        if not isinstance(self.campaign_floor, int) or self.campaign_floor < 0:
            raise ValueError("Node campaign_floor must be a non-negative integer.")
        if not isinstance(self.node_tier, str) or not self.node_tier:
            raise ValueError("Node node_tier must be a non-empty string.")
        if not isinstance(self.render_x, int) or not isinstance(self.render_y, int):
            raise ValueError("Node render coordinates must be integers.")
        if self.encounter_hook_id is not None and (
            not isinstance(self.encounter_hook_id, str) or not self.encounter_hook_id
        ):
            raise ValueError("Node encounter_hook_id must be a non-empty string when provided.")
        if self.boss_slot_id is not None and (
            not isinstance(self.boss_slot_id, str) or not self.boss_slot_id
        ):
            raise ValueError("Node boss_slot_id must be a non-empty string when provided.")
        if not isinstance(self.enemy_ids, list) or not all(
            isinstance(enemy_id, str) and enemy_id for enemy_id in self.enemy_ids
        ):
            raise ValueError("Node enemy_ids must be a list of non-empty strings.")
        if not isinstance(self.next_nodes, list) or not all(
            isinstance(node_id, str) and node_id for node_id in self.next_nodes
        ):
            raise ValueError("Node next_nodes must be a list of non-empty strings.")

    def connect_to(self, node_id: str) -> None:
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Connected node id must be a non-empty string.")
        if node_id not in self.next_nodes:
            self.next_nodes.append(node_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "floor": self.floor,
            "column": self.column,
            "map_id": self.map_id,
            "route_floor": self.route_floor,
            "campaign_floor": self.campaign_floor,
            "node_tier": self.node_tier,
            "render_x": self.render_x,
            "render_y": self.render_y,
            "encounter_hook_id": self.encounter_hook_id,
            "boss_slot_id": self.boss_slot_id,
            "enemy_ids": list(self.enemy_ids),
            "next_nodes": list(self.next_nodes),
        }


def simulate_node() -> dict[str, Any]:
    node = Node(
        node_id="outskirts_floor_0_node_0",
        node_type="combat",
        floor=0,
        column=0,
        map_id="outskirts",
        route_floor=1,
        campaign_floor=0,
        node_tier="normal",
        render_x=320,
        render_y=120,
        encounter_hook_id="outskirts:combat:f1:c0",
        enemy_ids=["enemy_basic_01"],
    )
    node.connect_to("floor_1_node_0")
    node.connect_to("floor_1_node_0")
    return {"node": node.to_dict(), "next_node_count": len(node.next_nodes)}
