from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KnowledgeGraph:
    """Loads and indexes nodes, edges, and issue neighborhoods deterministically."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.raw: dict[str, Any] = data
        self.meta: dict[str, Any] = data.get("graph_meta", {})
        self.nodes: list[dict[str, Any]] = data.get("nodes", [])
        self.edges: list[dict[str, Any]] = data.get("edges", [])

        self.nodes_by_id: dict[str, dict[str, Any]] = {}
        self.nodes_by_type: dict[str, list[dict[str, Any]]] = {}
        self.outgoing_edges: dict[str, list[dict[str, Any]]] = {}
        self.incoming_edges: dict[str, list[dict[str, Any]]] = {}
        self.anomalies: list[dict[str, Any]] = []

        self._index()

    @classmethod
    def from_json_file(cls, path: str | Path) -> "KnowledgeGraph":
        graph_path = Path(path)
        with graph_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Knowledge graph root JSON must be an object.")
        return cls(data)

    def _index(self) -> None:
        for node in self.nodes:
            node_id = node.get("id")
            if not node_id:
                self.anomalies.append({"type": "missing_node_id", "node": node})
                continue
            if node_id in self.nodes_by_id:
                self.anomalies.append({"type": "duplicate_node_id", "node_id": node_id})
                continue

            self.nodes_by_id[node_id] = node
            node_type = node.get("type", "unknown")
            self.nodes_by_type.setdefault(node_type, []).append(node)

        for edge in self.edges:
            src = edge.get("source") or edge.get("from")
            dst = edge.get("target") or edge.get("to")
            if not src or not dst:
                self.anomalies.append({"type": "malformed_edge", "edge": edge})
                continue
            if src not in self.nodes_by_id:
                self.anomalies.append({"type": "dangling_source", "source": src, "edge": edge})
            if dst not in self.nodes_by_id:
                self.anomalies.append({"type": "dangling_target", "target": dst, "edge": edge})

            self.outgoing_edges.setdefault(src, []).append(edge)
            self.incoming_edges.setdefault(dst, []).append(edge)

    def get_issues(self) -> list[dict[str, Any]]:
        """Returns issue nodes from the graph (supports common type names)."""
        for candidate_type in ("issue", "risk_issue", "finding_issue", "Issue"):
            if candidate_type in self.nodes_by_type:
                return self.nodes_by_type[candidate_type]
        return [
            node for node in self.nodes
            if "issue" in str(node.get("type", "")).lower()
        ]

    def get_issue_context(self, issue_id: str) -> dict[str, Any]:
        """Collects directly connected nodes and edges around an issue node."""
        issue_node = self.nodes_by_id.get(issue_id)
        if issue_node is None:
            raise KeyError(f"Unknown issue ID: {issue_id}")

        related_edges = self.outgoing_edges.get(issue_id, []) + self.incoming_edges.get(issue_id, [])
        neighbor_ids: list[str] = []
        seen_neighbors: set[str] = set()

        for edge in related_edges:
            src = edge.get("source") or edge.get("from")
            dst = edge.get("target") or edge.get("to")
            for other_id in (src, dst):
                if other_id and other_id != issue_id and other_id not in seen_neighbors:
                    seen_neighbors.add(other_id)
                    neighbor_ids.append(other_id)

        neighbors = [
            self.nodes_by_id[nid] for nid in neighbor_ids if nid in self.nodes_by_id
        ]

        return {
            "issue": issue_node,
            "edges": related_edges,
            "neighbors": neighbors,
            "graph_meta": self.meta,
        }