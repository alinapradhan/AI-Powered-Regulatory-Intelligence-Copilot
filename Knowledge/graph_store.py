"""
Graph store for regulatory obligation relationships.

Regulations reference each other (Reg A depends on / conflicts with /
supersedes Reg B) and map to internal controls. A pure vector search
loses this structure, so relationships are modeled explicitly here.
This in-memory adjacency-list implementation mirrors the interface
you'd get from a real graph DB (e.g., Neo4j via py2neo) so it can be
swapped in later without changing calling code.
"""

from dataclasses import dataclass, field


@dataclass
class Node:
    node_id: str
    node_type: str          # "obligation" | "control" | "regulation"
    label: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Edge:
    source_id: str
    target_id: str
    relationship: str        # "references" | "supersedes" | "maps_to" | "conflicts_with"


class GraphStore:
    def __init__(self):
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []

    def add_node(self, node: Node) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            raise ValueError("Both source and target nodes must exist before adding an edge")
        self._edges.append(edge)

    def neighbors(self, node_id: str, relationship: str | None = None) -> list[Node]:
        out = []
        for edge in self._edges:
            if edge.source_id == node_id and (relationship is None or edge.relationship == relationship):
                out.append(self._nodes[edge.target_id])
        return out

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def find_by_type(self, node_type: str) -> list[Node]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def path_exists(self, source_id: str, target_id: str, _visited: set | None = None) -> bool:
        """Simple DFS to check whether an obligation transitively links to another."""
        visited = _visited or set()
        if source_id == target_id:
            return True
        visited.add(source_id)
        for neighbor in self.neighbors(source_id):
            if neighbor.node_id not in visited:
                if self.path_exists(neighbor.node_id, target_id, visited):
                    return True
        return False
