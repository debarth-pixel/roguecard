from __future__ import annotations

import random
from typing import Any

from config import MAP_BRANCHES, MAP_FLOORS
from map.node import Node


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

        regular_types = ("combat", "combat", "event", "shop", "elite")
        for floor in range(self.floors - 1):
            current_floor: list[Node] = []
            for column in range(self.branches):
                node_type = "combat" if floor == 0 else self.rng.choice(regular_types)
                node_id = f"floor_{floor}_node_{column}"
                node = Node(node_id=node_id, node_type=node_type, floor=floor, column=column)
                current_floor.append(node)
                nodes[node_id] = node
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
            current_floor = floor_nodes[floor_index]
            next_floor = floor_nodes[floor_index + 1]
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

        return {
            "nodes": nodes,
            "start_nodes": [node.node_id for node in floor_nodes[0]],
            "boss_node_id": boss_node.node_id,
        }


def simulate_map_generator() -> dict[str, Any]:
    generator = MapGenerator(rng=random.Random(23))
    generated_map = generator.generate_map()
    return {
        "node_count": len(generated_map["nodes"]),
        "start_nodes": list(generated_map["start_nodes"]),
        "boss_node_id": generated_map["boss_node_id"],
    }
