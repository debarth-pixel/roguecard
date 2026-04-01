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
            "next_nodes": list(self.next_nodes),
        }


def simulate_node() -> dict[str, Any]:
    node = Node(node_id="floor_0_node_0", node_type="combat", floor=0, column=0)
    node.connect_to("floor_1_node_0")
    node.connect_to("floor_1_node_0")
    return {"node": node.to_dict(), "next_node_count": len(node.next_nodes)}
