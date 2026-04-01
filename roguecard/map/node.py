from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    node_id: str
    node_type: str
    floor: int
    column: int
    next_nodes: list[str] = field(default_factory=list)

    def connect_to(self, node_id: str) -> None:
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
    return node.to_dict()
