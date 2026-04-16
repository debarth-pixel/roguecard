from __future__ import annotations

import copy
import random
from typing import Any

from config import MAP_BRANCHES, MAP_FLOOR_COUNT
from map.node import ALLOWED_NODE_TYPES, Node

MAP_CANVAS_WIDTH = 1036
MAP_TOP_PADDING = 116
MAP_BOTTOM_PADDING = 140
MAP_ROW_SPACING = 142


class MapGenerator:
    def __init__(
        self,
        branches: int = MAP_BRANCHES,
        rng: random.Random | None = None,
    ) -> None:
        self.branches = branches
        self.rng = rng or random.Random()

    def generate_map(
        self,
        map_definition: dict[str, Any],
        *,
        map_index: int,
        global_floor_offset: int,
        branch_faction: str | None = None,
        selected_boss: dict[str, Any],
    ) -> dict[str, Any]:
        route_floor_count = int(map_definition.get("route_floor_count", MAP_FLOOR_COUNT))
        if route_floor_count < 2:
            raise ValueError("Map generation requires at least two route floors.")
        if self.branches < 1:
            raise ValueError("Map generation requires at least one branch.")

        nodes: dict[str, Node] = {}
        floor_nodes: list[list[Node]] = []
        map_id = map_definition["id"]

        for floor in range(route_floor_count):
            current_floor = self._create_floor_nodes(
                map_definition=map_definition,
                map_index=map_index,
                global_floor_offset=global_floor_offset,
                floor=floor,
            )
            for node in current_floor:
                nodes[node.node_id] = node
            floor_nodes.append(current_floor)

        boss_floor = route_floor_count
        boss_node = Node(
            node_id=f"{map_id}_boss",
            node_type="boss",
            floor=boss_floor,
            column=0,
            map_id=map_id,
            route_floor=route_floor_count,
            campaign_floor=global_floor_offset + boss_floor,
            node_tier="boss",
            render_x=MAP_CANVAS_WIDTH // 2,
            render_y=self._row_y(boss_floor, route_floor_count),
            encounter_hook_id=selected_boss["id"],
            boss_slot_id=selected_boss["id"],
            enemy_ids=list(selected_boss.get("enemy_ids", map_definition["placeholder_enemy_ids"]["boss"])),
        )
        nodes[boss_node.node_id] = boss_node
        floor_nodes.append([boss_node])

        for floor_index in range(len(floor_nodes) - 1):
            self._connect_floor_pair(floor_nodes[floor_index], floor_nodes[floor_index + 1])

        self._validate_graph(floor_nodes)

        return {
            "map_id": map_id,
            "map_name": map_definition["name"],
            "map_index": map_index,
            "theme_tag": map_definition["theme_tag"],
            "branch_faction": branch_faction if branch_faction is not None else map_definition.get("branch_faction"),
            "route_floor_count": route_floor_count,
            "global_floor_offset": global_floor_offset,
            "selected_boss_id": selected_boss["id"],
            "selected_boss": copy.deepcopy(selected_boss),
            "nodes": nodes,
            "start_nodes": [node.node_id for node in floor_nodes[0]],
            "boss_node_id": boss_node.node_id,
            "canvas_width": MAP_CANVAS_WIDTH,
            "canvas_height": self._canvas_height(route_floor_count),
        }

    def _create_floor_nodes(
        self,
        *,
        map_definition: dict[str, Any],
        map_index: int,
        global_floor_offset: int,
        floor: int,
    ) -> list[Node]:
        map_id = map_definition["id"]
        current_floor: list[Node] = []
        for column in range(self.branches):
            node_type = "combat" if floor == 0 else self._weighted_regular_node_type(map_definition, floor)
            node_id = f"{map_id}_floor_{floor}_node_{column}"
            current_floor.append(
                Node(
                    node_id=node_id,
                    node_type=node_type,
                    floor=floor,
                    column=column,
                    map_id=map_id,
                    route_floor=floor + 1,
                    campaign_floor=global_floor_offset + floor,
                    node_tier=self._node_tier(node_type),
                    render_x=self._lane_x(column),
                    render_y=self._row_y(floor, map_definition["route_floor_count"])
                    + self._row_y_jitter(floor),
                    encounter_hook_id=f"{map_id}:{node_type}:f{floor + 1}:c{column}",
                    enemy_ids=list(map_definition["placeholder_enemy_ids"].get(node_type, [])),
                )
            )
        return current_floor

    def _weighted_regular_node_type(self, map_definition: dict[str, Any], floor: int) -> str:
        weights = dict(map_definition["regular_node_weights"])
        if floor <= 1:
            weights["elite"] *= 0.35
            weights["shop"] *= 0.85
        if floor >= max(2, map_definition["route_floor_count"] - 3):
            weights["elite"] *= 1.2
            weights["shop"] *= 0.8
        if floor >= max(1, map_definition["route_floor_count"] - 2):
            weights["event"] *= 0.9

        total_weight = sum(max(weight, 0.0) for weight in weights.values())
        if total_weight <= 0:
            return "combat"

        roll = self.rng.random() * total_weight
        running_total = 0.0
        for node_type, weight in weights.items():
            running_total += max(weight, 0.0)
            if roll <= running_total:
                return node_type
        return "combat"

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

    def _lane_x(self, column: int) -> int:
        if self.branches <= 1:
            return MAP_CANVAS_WIDTH // 2
        lane_spacing = (MAP_CANVAS_WIDTH - 220) / max(1, self.branches - 1)
        base_x = 110 + (column * lane_spacing)
        jitter = self.rng.randint(-36, 36)
        return int(base_x + jitter)

    def _row_y(self, floor: int, route_floor_count: int) -> int:
        del route_floor_count  # Layout is driven by the same shared vertical rhythm for every map.
        return MAP_TOP_PADDING + (floor * MAP_ROW_SPACING)

    def _row_y_jitter(self, floor: int) -> int:
        if floor == 0:
            return 0
        return self.rng.randint(-18, 18)

    def _canvas_height(self, route_floor_count: int) -> int:
        total_rows = route_floor_count + 1
        return MAP_TOP_PADDING + MAP_BOTTOM_PADDING + ((total_rows - 1) * MAP_ROW_SPACING)

    def _node_tier(self, node_type: str) -> str:
        if node_type == "elite":
            return "elite"
        if node_type == "boss":
            return "boss"
        if node_type in {"shop", "event"}:
            return "utility"
        return "normal"


def simulate_map_generator() -> dict[str, Any]:
    generator = MapGenerator(rng=random.Random(23))
    map_definition = {
        "id": "outskirts",
        "name": "Outskirts",
        "theme_tag": "outskirts",
        "route_floor_count": 15,
        "regular_node_weights": {"combat": 2.8, "event": 1.0, "shop": 0.9, "elite": 0.6},
        "placeholder_enemy_ids": {
            "combat": ["enemy_basic_01"],
            "elite": ["enemy_elite_01"],
            "boss": ["enemy_boss_01"],
        },
    }
    generated_map = generator.generate_map(
        map_definition,
        map_index=1,
        global_floor_offset=0,
        branch_faction=None,
        selected_boss={
            "id": "outskirts_raider_lord",
            "name": "Raider Warlord",
            "branch_faction": None,
            "enemy_ids": ["enemy_boss_01"],
        },
    )
    start_node_types = {
        generated_map["nodes"][node_id].node_type for node_id in generated_map["start_nodes"]
    }
    return {
        "node_count": len(generated_map["nodes"]),
        "start_nodes": list(generated_map["start_nodes"]),
        "boss_node_id": generated_map["boss_node_id"],
        "start_node_types": sorted(start_node_types),
        "route_floor_count": generated_map["route_floor_count"],
        "selected_boss_id": generated_map["selected_boss_id"],
    }
