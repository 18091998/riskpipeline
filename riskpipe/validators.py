from __future__ import annotations

import json
import re
from typing import Any


NODE_ID_PATTERN = re.compile(r"\b[A-Z]{2,10}-[A-Z0-9_-]+\b")


def collect_valid_node_ids(nodes: list[dict[str, Any]]) -> set[str]:
    """Collects all valid node IDs present in the graph."""
    return {str(n["id"]) for n in nodes if n.get("id")}


def find_cited_node_ids(data: Any) -> list[str]:
    """Extracts candidate node IDs mentioned anywhere inside a response structure."""
    text = json.dumps(data, default=str)
    return sorted(set(NODE_ID_PATTERN.findall(text)))


def validate_grounded_ids(
    response_data: dict[str, Any],
    valid_node_ids: set[str],
    context_node_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Checks whether cited IDs exist in the graph and in the issue's local context."""
    cited_ids = find_cited_node_ids(response_data)
    unknown_graph_ids = [cid for cid in cited_ids if cid not in valid_node_ids]
    outside_context_ids = (
        [cid for cid in cited_ids if cid in valid_node_ids and cid not in context_node_ids]
        if context_node_ids is not None
        else []
    )

    return {
        "cited_ids": cited_ids,
        "unknown_graph_ids": unknown_graph_ids,
        "outside_context_ids": outside_context_ids,
        "is_valid": len(unknown_graph_ids) == 0,
    }