"""CLI rendering of `he search` across AutoType return shapes."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydantic import BaseModel
from typer.testing import CliRunner

from hyperextract.cli.cli import app

runner = CliRunner()


class _Node(BaseModel):
    name: str


class _Edge(BaseModel):
    source: str
    target: str


class _Theme(BaseModel):
    title: str


def _ka_dir(tmp_path: Path) -> Path:
    ka = tmp_path / "ka"
    ka.mkdir()
    (ka / "data.json").write_text("{}", encoding="utf-8")
    (ka / "metadata.json").write_text(
        json.dumps({"template": "general/graph", "lang": "en"}),
        encoding="utf-8",
    )
    index = ka / "index"
    index.mkdir()
    (index / "dummy").write_text("x", encoding="utf-8")
    return ka


def _invoke_search(tmp_path, search_return):
    ka_dir = _ka_dir(tmp_path)
    fake = MagicMock()
    fake.search.return_value = search_return
    fake.load = MagicMock()
    with (
        patch("hyperextract.cli.cli.validate_config"),
        patch("hyperextract.cli.cli.Template.create", return_value=fake),
    ):
        return runner.invoke(app, ["search", str(ka_dir), "query"])


def test_search_pair_tuple_prints_nodes_and_edges(tmp_path):
    nodes = [_Node(name="Alice")]
    edges = [_Edge(source="Alice", target="Bob")]
    result = _invoke_search(tmp_path, (nodes, edges))

    assert result.exit_code == 0, result.output
    assert "Nodes" in result.output
    assert "Edges" in result.output
    assert "Alice" in result.output
    assert "Result 1:" not in result.output
    assert "Found 2 result(s)" in result.output


def test_search_triple_prints_community_when_present(tmp_path):
    nodes = [_Node(name="Alice")]
    edges = [_Edge(source="Alice", target="Bob")]
    community = {"summary": "a cluster"}
    result = _invoke_search(tmp_path, (nodes, edges, community))

    assert result.exit_code == 0, result.output
    assert "Nodes" in result.output
    assert "Edges" in result.output
    assert "Community" in result.output
    assert "a cluster" in result.output
    assert "Result 1:" not in result.output


def test_search_triple_omits_none_community(tmp_path):
    nodes = [_Node(name="Alice")]
    edges = []
    result = _invoke_search(tmp_path, (nodes, edges, None))

    assert result.exit_code == 0, result.output
    assert "Nodes" in result.output
    assert "Community" not in result.output


def test_search_list_keeps_numbered_results(tmp_path):
    result = _invoke_search(tmp_path, [_Node(name="Alice"), _Node(name="Bob")])

    assert result.exit_code == 0, result.output
    assert "Found 2 result(s)" in result.output
    assert "Result 1:" in result.output
    assert "Result 2:" in result.output
    assert "Alice" in result.output


def test_search_dict_sections_themes_and_entities(tmp_path):
    payload = {
        "themes": [_Theme(title="power")],
        "entities": [_Node(name="Tesla")],
    }
    result = _invoke_search(tmp_path, payload)

    assert result.exit_code == 0, result.output
    assert "themes" in result.output.lower() or "Themes" in result.output
    assert "entities" in result.output.lower() or "Entities" in result.output
    assert "Tesla" in result.output
    assert "Result 1:" not in result.output


def test_search_empty_list_prints_no_results(tmp_path):
    result = _invoke_search(tmp_path, [])

    assert result.exit_code == 0, result.output
    assert "No results found." in result.output
