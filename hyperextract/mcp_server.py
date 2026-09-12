"""MCP server exposing Hyper-Extract knowledge abstracts.

Lets MCP-capable assistants query and export existing Knowledge Abstracts over
the Model Context Protocol. Read + export only — it never creates, mutates, or
deletes a KA.

Tools:
    - list_templates  : list available extraction templates
    - info            : stats for a knowledge abstract (chunks, timestamps,
                        optional sources; no LLM needed)
    - search          : semantic retrieval over a KA (needs an index)
    - ask             : RAG question-answering over a KA (needs an index)
    - export_obsidian : export a KA to an Obsidian vault
    - export_graphml  : export a KA to GraphML (same as `he export graphml`)
    - export_csv      : export a KA to CSV tables (same as `he export csv`)

Run it (stdio transport):

    he-mcp
    # or
    python -m hyperextract.mcp_server

LLM/embedder come from ``~/.he/config.toml`` (same as the CLI). Requires the
optional extra: ``pip install 'hyperextract[mcp]'``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

SERVER_NAME = "hyper-extract"


# ---------------------------------------------------------------------------
# Internal helpers (kept module-level so they can be monkeypatched in tests)
# ---------------------------------------------------------------------------


def _get_clients() -> tuple[BaseChatModel, Embeddings]:
    """Return (llm, embedder) from the user's ~/.he/config.toml."""
    from hyperextract.utils.client import get_client

    return get_client()


def _template_and_lang(path: Path) -> tuple[str, str]:
    """Read the template name and language from a KA's metadata.json."""
    meta_path = path / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No metadata.json in {path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    template = meta.get("template")
    if not template:
        raise ValueError(f"No template recorded in {meta_path}")
    return template, meta.get("lang", "en")


def _load_ka(ka_path: str):
    """Load a Knowledge Abstract from disk (needs LLM/embedder clients)."""
    from hyperextract.utils.template_engine import Template

    path = Path(ka_path)
    if not (path / "data.json").exists():
        raise FileNotFoundError(f"Not a knowledge abstract (no data.json): {ka_path}")
    template, lang = _template_and_lang(path)
    llm, emb = _get_clients()
    ka = Template.create(template, lang, llm_client=llm, embedder=emb)
    ka.load(path)
    return ka


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool implementations (registered with FastMCP in build_server)
# ---------------------------------------------------------------------------


def list_templates() -> str:
    """List the available knowledge-extraction templates.

    Returns a JSON array of {name, type, description}.
    """
    from hyperextract.utils.template_engine import Template

    templates = Template.list(include_methods=False)
    out = []
    for name, cfg in sorted(templates.items()):
        desc = getattr(cfg, "description", "") or ""
        if isinstance(desc, dict):
            desc = desc.get("en") or desc.get("zh") or ""
        out.append(
            {"name": name, "type": getattr(cfg, "type", None), "description": desc}
        )
    return _dump(out)


def info(ka_path: str, include_sources: bool = False) -> str:
    """Show information and statistics for a knowledge abstract.

    Args:
        ka_path: Path to the knowledge abstract directory.
        include_sources: When true, include source-ledger rows (same files
            ``he info --sources`` reads). Default false.

    Returns JSON with template, language, node/edge counts, optional chunks,
    created/updated timestamps, index status, and optional sources.
    Does not require LLM/embedder configuration.
    """
    path = Path(ka_path)
    data_file = path / "data.json"
    if not data_file.exists():
        return f"Not a knowledge abstract (no data.json): {ka_path}"

    data = json.loads(data_file.read_text(encoding="utf-8"))
    chunks = 0
    if isinstance(data, dict):
        nodes = len(data.get("nodes", data.get("entities", [])))
        edges = len(data.get("edges", data.get("relations", [])))
        chunks = len(data.get("chunks", []))
    elif isinstance(data, list):
        nodes, edges = len(data), 0
    else:
        nodes, edges = 0, 0

    meta: dict = {}
    meta_path = path / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    index_dir = path / "index"
    index_built = index_dir.exists() and any(index_dir.iterdir())

    payload: dict[str, Any] = {
        "path": str(path),
        "template": meta.get("template"),
        "lang": meta.get("lang"),
        "nodes": nodes,
        "edges": edges,
        "index_built": index_built,
    }
    if chunks:
        payload["chunks"] = chunks
    if meta.get("created_at"):
        payload["created"] = meta["created_at"]
    if meta.get("updated_at"):
        payload["updated"] = meta["updated_at"]
    if include_sources:
        payload["sources"] = _source_ledger_rows(path)
    return _dump(payload)


def _source_ledger_rows(path: Path) -> list[dict[str, Any]]:
    """Collect source-ledger rows using the same files as ``he info --sources``."""
    ledger_files = (
        path / "sources_nodes.json",
        path / "sources_edges.json",
        path / "sources_chunks.json",
        path / "sources_items.json",
    )
    combined: dict[str, dict[str, Any]] = {}
    for ledger_path in ledger_files:
        if not ledger_path.exists():
            continue
        try:
            entries = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            sid = entry.get("source_id")
            if sid is None:
                continue
            record = combined.setdefault(
                str(sid),
                {
                    "source_id": str(sid),
                    "raw_items": 0,
                    "content_hash": entry.get("content_hash"),
                },
            )
            record["raw_items"] += len(entry.get("raw_items", []))
            if record.get("content_hash") is None:
                record["content_hash"] = entry.get("content_hash")
    return [combined[key] for key in sorted(combined)]


def search(ka_path: str, query: str, top_k: int = 5) -> str:
    """Semantic search over a knowledge abstract.

    Args:
        ka_path: Path to the knowledge abstract directory.
        query: Natural-language search query.
        top_k: Maximum number of results (for graphs: nodes and edges each).

    Returns matching nodes/edges as JSON. The KA must have an index
    (build it with `he build-index`).
    """
    ka = _load_ka(ka_path)
    try:
        results = ka.search(query, top_k=top_k)
    except ValueError as e:
        return f"Cannot search: {e}. Build the index first with `he build-index {ka_path}`."

    if isinstance(results, tuple):
        nodes, edges = results
        return _dump(
            {
                "nodes": [_model_to_dict(n) for n in nodes],
                "edges": [_model_to_dict(e) for e in edges],
            }
        )
    return _dump({"results": [_model_to_dict(r) for r in results]})


def ask(ka_path: str, question: str, top_k: int = 5) -> str:
    """Answer a question using retrieval-augmented generation over a KA.

    Args:
        ka_path: Path to the knowledge abstract directory.
        question: The question to answer.
        top_k: Number of context items to retrieve.

    Returns the generated answer. The KA must have an index.
    """
    ka = _load_ka(ka_path)
    try:
        response = ka.chat(question, top_k=top_k)
    except ValueError as e:
        return f"Cannot answer: {e}. Build the index first with `he build-index {ka_path}`."
    return getattr(response, "content", str(response))


def export_obsidian(
    ka_path: str,
    output: str,
    vault_name: str = "",
    overwrite: bool = False,
) -> str:
    """Export a knowledge abstract to an Obsidian vault.

    Args:
        ka_path: Path to the knowledge abstract directory.
        output: Destination vault directory.
        vault_name: Vault name for the index note (defaults to the output dir name).
        overwrite: Allow writing into an existing, non-empty directory.

    Returns a summary of how many notes were written.
    """
    ka = _load_ka(ka_path)
    if not hasattr(ka, "export_obsidian"):
        return (
            "Obsidian export is only supported for graph-type knowledge abstracts "
            "(graph, hypergraph, temporal/spatial graphs)."
        )
    name = vault_name or Path(output).name or "Knowledge Vault"
    try:
        vault = ka.export_obsidian(output, vault_name=name, overwrite=overwrite)
    except FileExistsError as e:
        return f"{e} Pass overwrite=true to write into it."
    count = len(list(Path(vault).glob("*.md")))
    return f"Exported {count} notes to {vault}"


def _is_hypergraph_ka(ka) -> bool:
    """True for AutoHypergraph; temporal/spatial graphs are pairwise."""
    if type(ka).__name__ == "AutoHypergraph":
        return True
    meta = getattr(ka, "metadata", None)
    return isinstance(meta, dict) and meta.get("type") == "hypergraph"


def _require_graph_ka(ka) -> str | None:
    if hasattr(ka, "export_obsidian"):
        return None
    return (
        "GraphML/CSV export is only supported for graph-type knowledge abstracts "
        "(graph, hypergraph, temporal/spatial graphs)."
    )


def export_graphml(ka_path: str, output: str) -> str:
    """Export a knowledge abstract to GraphML.

    Args:
        ka_path: Path to the knowledge abstract directory.
        output: Destination ``.graphml`` file.

    Uses the same ``export_to_graphml`` implementation as ``he export graphml``.
    Does not create, mutate, or delete the KA.
    """
    from hyperextract.utils.exporters import GraphMLHypergraphError, export_to_graphml

    ka = _load_ka(ka_path)
    err = _require_graph_ka(ka)
    if err:
        return err
    try:
        dest = export_to_graphml(
            ka.nodes,
            ka.edges,
            node_id_extractor=ka.node_key_extractor,
            incident_nodes_extractor=ka.nodes_in_edge_extractor,
            file_path=output,
            edge_id_extractor=getattr(ka, "edge_key_extractor", None),
        )
    except GraphMLHypergraphError as e:
        return str(e)
    return f"Wrote GraphML to {dest}"


def export_csv(ka_path: str, output: str, overwrite: bool = False) -> str:
    """Export a knowledge abstract to CSV tables.

    Args:
        ka_path: Path to the knowledge abstract directory.
        output: Destination directory.
        overwrite: Allow writing into an existing, non-empty directory.

    Uses the same ``export_to_csv`` implementation as ``he export csv``.
    Does not create, mutate, or delete the KA.
    """
    from hyperextract.utils.exporters import export_to_csv

    ka = _load_ka(ka_path)
    err = _require_graph_ka(ka)
    if err:
        return err
    hypergraph = _is_hypergraph_ka(ka)
    try:
        dest = export_to_csv(
            ka.nodes,
            ka.edges,
            node_id_extractor=ka.node_key_extractor,
            incident_nodes_extractor=ka.nodes_in_edge_extractor,
            folder_path=output,
            edge_id_extractor=getattr(ka, "edge_key_extractor", None),
            hypergraph=hypergraph,
            overwrite=overwrite,
        )
    except FileExistsError as e:
        return f"{e} Pass overwrite=true to write into it."
    written = "nodes.csv + hyperedges.csv" if hypergraph else "nodes.csv + edges.csv"
    return f"Wrote {written} to {dest}"


def _model_to_dict(item: Any) -> Any:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return item


# ---------------------------------------------------------------------------
# Server wiring
# ---------------------------------------------------------------------------


def build_server():
    """Build the MCP server with all tools registered."""
    try:  # mcp 1.x
        from mcp.server.fastmcp import FastMCP

        server = FastMCP(SERVER_NAME)
    except ImportError:  # mcp 2.x: FastMCP was renamed to MCPServer
        from mcp.server.mcpserver import MCPServer

        server = MCPServer(SERVER_NAME)
    for fn in (
        list_templates,
        info,
        search,
        ask,
        export_obsidian,
        export_graphml,
        export_csv,
    ):
        server.tool()(fn)
    return server


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
