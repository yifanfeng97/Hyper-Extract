"""Cypher exporter for Neo4j-compatible MERGE scripts.

Pairwise edges become relationships. N-ary edges become ``(:Hyperedge)``
nodes with ``-[:IN]->`` membership — never exploded into a pairwise clique.
Endpoint order is preserved. Stdlib only; no neo4j driver.
"""

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from hyperextract.utils.logging import get_logger

from .common import incident_ids, resolve_nodes, scalar_fields

logger = get_logger(__name__)

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Unquoted relationship types that would parse as Cypher keywords.
_RESERVED = frozenset(
    {
        "AND",
        "AS",
        "CONTAINS",
        "CREATE",
        "DELETE",
        "DETACH",
        "FALSE",
        "IN",
        "IS",
        "MATCH",
        "MERGE",
        "NOT",
        "NULL",
        "OR",
        "REMOVE",
        "RETURN",
        "SET",
        "TRUE",
        "WHERE",
        "WITH",
        "XOR",
    }
)


def export_to_cypher(
    nodes: Sequence[BaseModel],
    edges: Sequence[BaseModel],
    *,
    node_id_extractor: Callable[[Any], str],
    incident_nodes_extractor: Callable[[Any], Sequence[str]],
    file_path: str | Path,
    edge_id_extractor: Callable[[Any], str] | None = None,
) -> Path:
    """Export a graph to a Cypher MERGE script.

    Args:
        nodes: Node/entity models to export.
        edges: Edge models to export (pairwise or N-ary).
        node_id_extractor: Maps a node to its unique key (matches edge endpoints).
        incident_nodes_extractor: Maps an edge to incident node keys in order.
            Two endpoints become a relationship; three or more become a
            ``Hyperedge`` node plus ``IN`` membership.
        file_path: Destination ``.cypher`` file.
        edge_id_extractor: Optional edge -> Cypher id. Defaults to
            ``e0``, ``e1``, ...

    Returns:
        The written file :class:`~pathlib.Path`.

    Raises:
        IsADirectoryError: If ``file_path`` exists and is a directory.
    """
    dest = Path(file_path)
    if dest.exists() and dest.is_dir():
        raise IsADirectoryError(
            f"Destination '{dest}' is a directory; pass a Cypher file path."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)

    by_id = resolve_nodes(nodes, node_id_extractor)
    lines: list[str] = []
    for node_id, node in by_id.items():
        lines.append(f"MERGE (n:Node {{id: {_cypher_str(node_id)}}})")
        assignments = _set_assignments("n", scalar_fields(node))
        if assignments:
            lines.append(f"SET {assignments}")

    skipped = 0
    pairwise = 0
    hyper = 0
    for index, edge in enumerate(edges):
        members = incident_ids(edge, incident_nodes_extractor)
        if members is None:
            skipped += 1
            continue
        if len(members) <= 1:
            skipped += 1
            logger.warning(
                "export.cypher: skipping edge with %d endpoint(s) members=%s",
                len(members),
                members,
            )
            continue
        missing = [member for member in members if member not in by_id]
        if missing:
            skipped += 1
            logger.warning(
                "export.cypher: skipping edge with missing endpoint(s) %s",
                missing,
            )
            continue
        edge_id = _edge_id(edge, index, edge_id_extractor)
        fields = scalar_fields(edge)
        if len(members) == 2:
            rel_type = _relationship_type(fields)
            source, target = members[0], members[1]
            lines.append(f"MERGE (a:Node {{id: {_cypher_str(source)}}})")
            lines.append(f"MERGE (b:Node {{id: {_cypher_str(target)}}})")
            lines.append(
                f"MERGE (a)-[r:{rel_type} {{id: {_cypher_str(edge_id)}}}]->(b)"
            )
            assignments = _set_assignments("r", fields)
            if assignments:
                lines.append(f"SET {assignments}")
            pairwise += 1
            continue
        lines.append(f"MERGE (h:Hyperedge {{id: {_cypher_str(edge_id)}}})")
        assignments = _set_assignments("h", fields)
        if assignments:
            lines.append(f"SET {assignments}")
        for member in members:
            lines.append(f"MERGE (n:Node {{id: {_cypher_str(member)}}})")
            lines.append("MERGE (n)-[:IN]->(h)")
        hyper += 1

    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    logger.info(
        "cypher: exported nodes=%d edges=%d hyperedges=%d skipped_edges=%d path=%s",
        len(by_id),
        pairwise,
        hyper,
        skipped,
        dest,
    )
    return dest


def _cypher_str(value: Any) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _cypher_literal(value: str | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return _cypher_str(value)


def _set_assignments(alias: str, fields: dict[str, str | int | float | bool]) -> str:
    parts = []
    for key, value in fields.items():
        if key == "id":
            continue
        parts.append(f"{alias}.{key} = {_cypher_literal(value)}")
    return ", ".join(parts)


def _relationship_type(fields: dict[str, str | int | float | bool]) -> str:
    for key in ("type", "label"):
        raw = fields.get(key)
        if isinstance(raw, str) and _is_legal_ident(raw):
            return raw
    return "REL"


def _is_legal_ident(name: str) -> bool:
    return bool(_IDENT.match(name)) and name.upper() not in _RESERVED


def _edge_id(edge: Any, index: int, extractor: Callable[[Any], str] | None) -> str:
    if extractor is None:
        return f"e{index}"
    try:
        value = extractor(edge)
    except Exception as exc:
        logger.debug("export.cypher: edge_id_extractor raised %s", exc)
        return f"e{index}"
    if value in (None, ""):
        return f"e{index}"
    return str(value)
