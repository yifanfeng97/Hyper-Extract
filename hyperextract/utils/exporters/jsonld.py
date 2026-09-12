"""JSON-LD exporter for pairwise edges and GraphML-style hyperedges.

Produces a JSON-LD 1.1 document (stdlib ``json``, no RDFLib). Binary edges
are ``@type: Edge`` with ``source`` / ``target``. Edges with three or more
endpoints are ``@type: Hyperedge`` with an ``endpoint`` list in
``incident_nodes_extractor`` order. Endpoints are never sorted.
"""

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from hyperextract.utils.logging import get_logger

from .common import incident_ids, resolve_nodes, scalar_fields

logger = get_logger(__name__)

# Inline context: only the keys the CLI / interop contract documents.
JSONLD_CONTEXT: dict[str, Any] = {
    "Node": "Node",
    "Edge": "Edge",
    "Hyperedge": "Hyperedge",
    "source": {"@type": "@id"},
    "target": {"@type": "@id"},
    "endpoint": {"@container": "@list"},
}

_RESERVED_KEYS = frozenset({"@id", "@type", "source", "target", "endpoint"})


def export_to_jsonld(
    nodes: Sequence[BaseModel],
    edges: Sequence[BaseModel],
    *,
    node_id_extractor: Callable[[Any], str],
    incident_nodes_extractor: Callable[[Any], Sequence[str]],
    file_path: str | Path,
    edge_id_extractor: Callable[[Any], str] | None = None,
) -> Path:
    """Export a graph to a JSON-LD file.

    Args:
        nodes: Node/entity models to export.
        edges: Edge models to export (pairwise or N-ary).
        node_id_extractor: Maps a node to its unique key (matches edge endpoints).
        incident_nodes_extractor: Maps an edge to incident node keys in order.
            Two endpoints become ``Edge``; three or more become ``Hyperedge``.
        file_path: Destination ``.jsonld`` file.
        edge_id_extractor: Optional edge -> ``@id``. Defaults to ``e0``, ``e1``, ...

    Returns:
        The written file :class:`~pathlib.Path`.

    Raises:
        IsADirectoryError: If ``file_path`` exists and is a directory.
    """
    dest = Path(file_path)
    if dest.exists() and dest.is_dir():
        raise IsADirectoryError(
            f"Destination '{dest}' is a directory; pass a JSON-LD file path."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)

    by_id = resolve_nodes(nodes, node_id_extractor)
    graph: list[dict[str, Any]] = []
    for node_id, node in by_id.items():
        item: dict[str, Any] = {"@id": node_id, "@type": "Node"}
        item.update(_public_fields(node))
        graph.append(item)

    skipped = 0
    for index, edge in enumerate(edges):
        members = incident_ids(edge, incident_nodes_extractor)
        if members is None:
            skipped += 1
            continue
        if len(members) <= 1:
            skipped += 1
            logger.warning(
                "export.jsonld: skipping edge with %d endpoint(s) members=%s",
                len(members),
                members,
            )
            continue
        missing = [member for member in members if member not in by_id]
        if missing:
            skipped += 1
            logger.warning(
                "export.jsonld: skipping edge with missing endpoint(s) %s",
                missing,
            )
            continue
        edge_id = _edge_id(edge, index, edge_id_extractor)
        fields = _public_fields(edge)
        if len(members) == 2:
            item = {
                "@id": edge_id,
                "@type": "Edge",
                "source": members[0],
                "target": members[1],
            }
            item.update(fields)
            graph.append(item)
            continue
        item = {
            "@id": edge_id,
            "@type": "Hyperedge",
            "endpoint": list(members),
        }
        item.update(fields)
        graph.append(item)

    document = {"@context": JSONLD_CONTEXT, "@graph": graph}
    dest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    edge_count = sum(1 for item in graph if item.get("@type") == "Edge")
    hyper_count = sum(1 for item in graph if item.get("@type") == "Hyperedge")
    logger.info(
        "jsonld: exported nodes=%d edges=%d hyperedges=%d skipped_edges=%d path=%s",
        len(by_id),
        edge_count,
        hyper_count,
        skipped,
        dest,
    )
    return dest


def _public_fields(model: BaseModel) -> dict[str, str | int | float | bool]:
    return {
        key: value
        for key, value in scalar_fields(model).items()
        if key not in _RESERVED_KEYS
    }


def _edge_id(edge: Any, index: int, extractor: Callable[[Any], str] | None) -> str:
    if extractor is None:
        return f"e{index}"
    try:
        value = extractor(edge)
    except Exception as exc:
        logger.debug("export.jsonld: edge_id_extractor raised %s", exc)
        return f"e{index}"
    if value in (None, ""):
        return f"e{index}"
    return str(value)
