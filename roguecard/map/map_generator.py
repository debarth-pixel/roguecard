from __future__ import annotations

import random
from typing import Any

from config import MAP_BRANCHES, MAP_FLOORS
from map.node import ALLOWED_NODE_TYPES, Node

REGULAR_NODE_TYPES = ("combat", "combat", "event", "shop", "elite")


class MapGenerator:
    def __init__(
        self,
        floors: int = MAP_FLOORS,
        branches: int = MAP_BRANCHES,
        rng: random.Random | None = None,
    ) -> None:
        self.floors = floors
        self.branches = branches
        self.rng = rng or random.Random()

    def generate_map(self) -> dict[str, Any]:
        if self.floors < 2:
            raise ValueError("Map generation requires at least two floors.")
        if self.branches < 1:
            raise ValueError("Map generation requires at least one branch.")

        nodes: dict[str, Node] = {}
        floor_nodes: list[list[Node]] = []

        for floor in range(self.floors - 1):
            current_floor = self._create_floor_nodes(floor)
            for node in current_floor:
                nodes[node.node_id] = node
            floor_nodes.append(current_floor)

        boss_floor = self.floors - 1
        boss_node = Node(
            node_id=f"floor_{boss_floor}_node_0",
            node_type="boss",
            floor=boss_floor,
            column=0,
        )
        nodes[boss_node.node_id] = boss_node
        floor_nodes.append([boss_node])

        for floor_index in range(len(floor_nodes) - 1):
            self._connect_floor_pair(floor_nodes[floor_index], floor_nodes[floor_index + 1])

        self._validate_graph(floor_nodes)

        return {
            "nodes": nodes,
            "start_nodes": [node.node_id for node in floor_nodes[0]],
            "boss_node_id": boss_node.node_id,
        }

    def _create_floor_nodes(self, floor: int) -> list[Node]:
        current_floor: list[Node] = []
        for column in range(self.branches):
            node_type = "combat" if floor == 0 else self.rng.choice(REGULAR_NODE_TYPES)
            node_id = f"floor_{floor}_node_{column}"
            current_floor.append(Node(node_id=node_id, node_type=node_type, floor=floor, column=column))
        return current_floor

    def _connect_floor_pair(self, current_floor: list[Node], next_floor: list[Node]) -> None:
        for node in current_floor:
            candidate_columns = {min(node.column, len(next_floor) - 1)}
            if len(next_floor) > 1 and node.column + 1 < len(next_floor):
                candidate_columns.add(node.column + 1)
            if len(next_floor) > 1 and node.column - 1 >= 0:
                candidate_columns.add(node.column - 1)

            candidates = [next_floor[column] for column in sorted(candidate_columns)]
            self.rng.shuffle(candidates)
            connection_count = 1 if len(candidates) == 1 else self.rng.randint(1, min(2, len(candidates)))
            for target_node in candidates[:connection_count]:
                node.connect_to(target_node.node_id)

        for target_node in next_floor:
            has_incoming = any(target_node.node_id in node.next_nodes for node in current_floor)
            if has_incoming:
                continue

            source_node = min(current_floor, key=lambda node: abs(node.column - target_node.column))
            source_node.connect_to(target_node.node_id)

    def _validate_graph(self, floor_nodes: list[list[Node]]) -> None:
        for floor_index, current_floor in enumerate(floor_nodes):
            for node in current_floor:
                if node.node_type not in ALLOWED_NODE_TYPES:
                    raise ValueError(f"Generated unsupported node type: {node.node_type}")
                if floor_index == 0 and node.node_type != "combat":
                    raise ValueError("Start floor nodes must all be combat nodes.")
                if floor_index == len(floor_nodes) - 1 and node.node_type != "boss":
                    raise ValueError("Final floor must contain only a boss node.")
                if floor_index < len(floor_nodes) - 1 and not node.next_nodes:
                    raise ValueError(f"Node {node.node_id} has no outgoing connections.")
                if floor_index > 0:
                    previous_floor = floor_nodes[floor_index - 1]
                    has_incoming = any(node.node_id in previous.next_nodes for previous in previous_floor)
                    if not has_incoming:
                        raise ValueError(f"Node {node.node_id} has no incoming connections.")


def simulate_map_generator() -> dict[str, Any]:
    generator = MapGenerator(rng=random.Random(23))
    generated_map = generator.generate_map()
    start_node_types = {
        generated_map["nodes"][node_id].node_type for node_id in generated_map["start_nodes"]
    }
    return {
        "node_count": len(generated_map["nodes"]),
        "start_nodes": list(generated_map["start_nodes"]),
        "boss_node_id": generated_map["boss_node_id"],
        "start_node_types": sorted(start_node_types),
    }
