"""Tests for the MCP server (hyperextract.mcp_server).

The tool functions are tested directly. The FastMCP wiring is smoke-tested and
skipped if the optional `mcp` package is not installed. The `mcp` package is not
required to import the module or test the tool logic.
"""

import json

import pytest
from pydantic import BaseModel, Field

from hyperextract import mcp_server
from hyperextract.types import AutoGraph
from tests.mocks import MockChatModel, MockEmbeddings


class Entity(BaseModel):
    name: str
    type: str = "ENTITY"
    properties: dict = Field(default_factory=dict)


class Relation(BaseModel):
    source: str
    target: str
    relation_type: str


def _graph_with_index():
    g = AutoGraph(
        node_schema=Entity,
        edge_schema=Relation,
        node_key_extractor=lambda x: x.name,
        edge_key_extractor=lambda x: f"{x.source}-{x.relation_type}-{x.target}",
        nodes_in_edge_extractor=lambda x: (x.source, x.target),
        llm_client=MockChatModel(),
        embedder=MockEmbeddings(),
    )
    g._node_memory.add([Entity(name="Apple", type="ORG"), Entity(name="Steve Jobs")])
    g._edge_memory.add(
        [Relation(source="Apple", target="Steve Jobs", relation_type="founded_by")]
    )
    g.build_index()
    g.metadata["template"] = "general/base_graph"
    g.metadata["lang"] = "en"
    return g


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


def test_list_templates_returns_json():
    out = json.loads(mcp_server.list_templates())
    assert isinstance(out, list)
    assert len(out) > 0
    assert {"name", "type", "description"} <= set(out[0].keys())


def test_list_templates_includes_methods_by_default():
    out = json.loads(mcp_server.list_templates())
    names = {item["name"] for item in out}
    assert any(name.startswith("method/") for name in names)
    assert "method/graph_rag" in names or "method/chunk_rag" in names


def test_list_templates_can_hide_methods():
    out = json.loads(mcp_server.list_templates(include_methods=False))
    names = {item["name"] for item in out}
    assert all(not name.startswith("method/") for name in names)


# ---------------------------------------------------------------------------
# info (no client needed — reads json directly)
# ---------------------------------------------------------------------------


def test_info_reports_counts(tmp_path):
    g = _graph_with_index()
    ka = tmp_path / "ka"
    g.dump(ka)

    out = json.loads(mcp_server.info(str(ka)))
    assert out["nodes"] == 2
    assert out["edges"] == 1
    assert out["index_built"] is True
    assert out["template"] == "general/base_graph"


def test_info_rejects_non_ka(tmp_path):
    out = mcp_server.info(str(tmp_path / "nope"))
    assert "Not a knowledge abstract" in out


# ---------------------------------------------------------------------------
# search / ask / export — _load_ka monkeypatched to skip the Template reload
# ---------------------------------------------------------------------------


def test_search_returns_nodes_and_edges(monkeypatch):
    g = _graph_with_index()
    monkeypatch.setattr(mcp_server, "_load_ka", lambda p: g)

    out = json.loads(mcp_server.search("x", "technology company", top_k=2))
    assert "nodes" in out and "edges" in out
    assert isinstance(out["nodes"], list)


def test_search_without_index_is_handled(monkeypatch):
    g = AutoGraph(
        node_schema=Entity,
        edge_schema=Relation,
        node_key_extractor=lambda x: x.name,
        edge_key_extractor=lambda x: f"{x.source}-{x.relation_type}-{x.target}",
        nodes_in_edge_extractor=lambda x: (x.source, x.target),
        llm_client=MockChatModel(),
        embedder=MockEmbeddings(),
    )
    g._node_memory.add([Entity(name="Apple")])
    monkeypatch.setattr(mcp_server, "_load_ka", lambda p: g)

    out = mcp_server.search("x", "anything")
    assert "Cannot search" in out
    assert "build-index" in out


class _StubKA:
    """Stub KA to test the MCP tool wiring independently of chat/export internals
    (those are covered by their own modules; this isolates the MCP layer)."""

    def chat(self, question, top_k=5):
        return type(
            "Resp", (), {"content": f"answer to: {question}", "additional_kwargs": {}}
        )()

    def export_obsidian(self, output, vault_name="", overwrite=False):
        from pathlib import Path

        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "Note.md").write_text("x", encoding="utf-8")
        return out


def test_ask_returns_answer(monkeypatch):
    monkeypatch.setattr(mcp_server, "_load_ka", lambda p: _StubKA())
    out = mcp_server.ask("x", "Who founded Apple?", top_k=2)
    assert out == "answer to: Who founded Apple?"


def test_export_obsidian(monkeypatch, tmp_path):
    monkeypatch.setattr(mcp_server, "_load_ka", lambda p: _StubKA())
    vault = tmp_path / "vault"
    out = mcp_server.export_obsidian("x", str(vault), vault_name="KB", overwrite=True)
    assert "Exported 1 notes" in out
    assert (vault / "Note.md").exists()


def test_export_graphml(monkeypatch, tmp_path):
    g = _graph_with_index()
    monkeypatch.setattr(mcp_server, "_load_ka", lambda p: g)
    dest = tmp_path / "out.graphml"
    out = mcp_server.export_graphml("x", str(dest))
    assert dest.exists()
    xml = dest.read_text(encoding="utf-8")
    assert "<edge" in xml
    assert str(dest) in out


def test_export_csv(monkeypatch, tmp_path):
    g = _graph_with_index()
    monkeypatch.setattr(mcp_server, "_load_ka", lambda p: g)
    dest = tmp_path / "csv_out"
    out = mcp_server.export_csv("x", str(dest))
    assert (dest / "nodes.csv").exists()
    assert (dest / "edges.csv").exists()
    assert "nodes.csv + edges.csv" in out


# ---------------------------------------------------------------------------
# FastMCP wiring (needs the optional `mcp` package)
# ---------------------------------------------------------------------------


def test_build_server_registers_tools():
    pytest.importorskip("mcp")
    server = mcp_server.build_server()
    assert server is not None
    assert server.name == "hyper-extract"
