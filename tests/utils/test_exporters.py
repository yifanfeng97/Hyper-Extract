"""Unit tests for GraphML and CSV exporters (hyperextract.utils.exporters).

Pure-function tests use Pydantic fixtures and extractors — no LLM. CLI tests
mock ``Template.create`` / ``load`` against a dumped KA directory.
"""

import csv
import json
import xml.etree.ElementTree as ET
from typing import List, Optional
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field
from typer.testing import CliRunner

from hyperextract.cli.cli import app
from hyperextract.utils.exporters import (
    HYPEREDGE_MEMBER_SEP,
    export_to_csv,
    export_to_graphml,
    export_to_jsonld,
)
from hyperextract.utils.exporters.graphml import GRAPHML_NS

runner = CliRunner()


class Entity(BaseModel):
    name: str
    type: str = "ENTITY"
    note: Optional[str] = None
    score: Optional[int] = None
    active: bool = True
    properties: dict = Field(default_factory=dict)


class Relation(BaseModel):
    source: str
    target: str
    relation_type: str
    description: Optional[str] = None
    weight: Optional[float] = None


class Event(BaseModel):
    label: str
    participants: List[str]


def _export_graphml(path, nodes, edges, **kwargs):
    return export_to_graphml(
        nodes,
        edges,
        node_id_extractor=lambda n: n.name,
        incident_nodes_extractor=lambda e: (e.source, e.target),
        file_path=path,
        **kwargs,
    )


def _export_csv(folder, nodes, edges, **kwargs):
    return export_to_csv(
        nodes,
        edges,
        node_id_extractor=lambda n: n.name,
        incident_nodes_extractor=lambda e: (e.source, e.target),
        folder_path=folder,
        **kwargs,
    )


def _parse_graphml(path):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"g": GRAPHML_NS}
    graph = root.find("g:graph", ns)
    if graph is None:
        graph = root.find("graph")
    return root, graph, ns


def _edge_endpoints(graph, ns):
    edges = graph.findall("g:edge", ns) or graph.findall("edge")
    return [(e.get("source"), e.get("target")) for e in edges]


def _node_data(root, graph, ns, node_id):
    keys = {}
    for key in root.findall("g:key", ns) or root.findall("key"):
        if key.get("for") == "node":
            keys[key.get("id")] = key.get("attr.name")
    for node in graph.findall("g:node", ns) or graph.findall("node"):
        if node.get("id") != node_id:
            continue
        data = {}
        for data_el in node.findall("g:data", ns) or node.findall("data"):
            name = keys.get(data_el.get("key"), data_el.get("key"))
            data[name] = data_el.text
        return data
    return None


# ---------------------------------------------------------------------------
# GraphML — pairwise direction, attributes, escaping
# ---------------------------------------------------------------------------


class TestGraphMLPairwise:
    def test_preserves_direction_b_to_a(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B")]
        edges = [Relation(source="B", target="A", relation_type="leads_to")]
        path = _export_graphml(tmp_path / "g.graphml", nodes, edges)

        xml = path.read_text(encoding="utf-8")
        assert 'edgedefault="directed"' in xml

        _root, graph, ns = _parse_graphml(path)
        endpoints = _edge_endpoints(graph, ns)
        assert endpoints == [("B", "A")]
        assert ("A", "B") not in endpoints

    def test_custom_fields_appear_as_data_keys(self, tmp_path):
        nodes = [
            Entity(name="Apple", type="ORG", score=7, active=True),
            Entity(name="Jobs", type="PERSON", note="founder"),
        ]
        edges = [
            Relation(
                source="Apple",
                target="Jobs",
                relation_type="founded_by",
                weight=1.5,
            )
        ]
        path = _export_graphml(tmp_path / "g.graphml", nodes, edges)
        xml = path.read_text(encoding="utf-8")
        assert 'attr.name="type"' in xml
        assert 'attr.name="score"' in xml
        assert 'attr.name="active"' in xml
        assert 'attr.name="weight"' in xml
        assert 'attr.name="relation_type"' in xml

        root, graph, ns = _parse_graphml(path)
        apple = _node_data(root, graph, ns, "Apple")
        assert apple["type"] == "ORG"
        assert apple["score"] == "7"
        assert apple["active"] == "true"
        jobs = _node_data(root, graph, ns, "Jobs")
        assert jobs["note"] == "founder"

    def test_xml_special_characters_escaped(self, tmp_path):
        nasty = "A&B<C>\"'"
        nodes = [Entity(name=nasty, note='x & y <z> "q" \''), Entity(name="Z")]
        edges = [Relation(source=nasty, target="Z", relation_type="mentions")]
        path = _export_graphml(tmp_path / "g.graphml", nodes, edges)
        xml = path.read_text(encoding="utf-8")

        assert "&amp;" in xml
        assert "&lt;" in xml
        assert "&gt;" in xml
        assert "&quot;" in xml
        assert "&apos;" in xml

        ET.parse(path)
        _root, graph, ns = _parse_graphml(path)
        endpoints = _edge_endpoints(graph, ns)
        assert endpoints == [(nasty, "Z")]

    def test_missing_endpoint_is_skipped(self, tmp_path):
        nodes = [Entity(name="Apple")]
        edges = [Relation(source="Apple", target="Ghost", relation_type="x")]
        path = _export_graphml(tmp_path / "g.graphml", nodes, edges)
        _root, graph, ns = _parse_graphml(path)
        assert _edge_endpoints(graph, ns) == []
        node_ids = [
            n.get("id") for n in (graph.findall("g:node", ns) or graph.findall("node"))
        ]
        assert node_ids == ["Apple"]

    def test_nary_edge_writes_hyperedge(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B"), Entity(name="C")]
        edges = [Event(label="meeting", participants=["C", "A", "B"])]
        path = export_to_graphml(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: tuple(e.participants),
            file_path=tmp_path / "g.graphml",
        )
        xml = path.read_text(encoding="utf-8")
        assert "hyperedge" in xml
        assert f'xmlns="{GRAPHML_NS}"' in xml

        root, graph, ns = _parse_graphml(path)
        assert root.tag == f"{{{GRAPHML_NS}}}graphml" or root.get("xmlns") == GRAPHML_NS
        hyperedges = graph.findall("g:hyperedge", ns) or graph.findall("hyperedge")
        assert len(hyperedges) == 1
        endpoints = [
            ep.get("node")
            for ep in (
                hyperedges[0].findall("g:endpoint", ns)
                or hyperedges[0].findall("endpoint")
            )
        ]
        assert endpoints == ["C", "A", "B"]
        assert _edge_endpoints(graph, ns) == []


# ---------------------------------------------------------------------------
# JSON-LD — pairwise source/target, N-ary Hyperedge order
# ---------------------------------------------------------------------------


def _load_jsonld(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestJSONLDExport:
    def test_pairwise_has_source_target(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B")]
        edges = [Relation(source="B", target="A", relation_type="leads_to")]
        path = export_to_jsonld(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: (e.source, e.target),
            file_path=tmp_path / "g.jsonld",
        )
        doc = _load_jsonld(path)
        assert "source" in doc["@context"]
        assert doc["@context"]["source"]["@type"] == "@id"
        assert doc["@context"]["endpoint"]["@container"] == "@list"
        edges_out = [item for item in doc["@graph"] if item.get("@type") == "Edge"]
        assert len(edges_out) == 1
        assert edges_out[0]["source"] == "B"
        assert edges_out[0]["target"] == "A"
        assert edges_out[0]["@type"] == "Edge"
        assert not any(item.get("@type") == "Hyperedge" for item in doc["@graph"])

    def test_nary_writes_hyperedge_in_extractor_order(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B"), Entity(name="C")]
        edges = [Event(label="meeting", participants=["C", "A", "B"])]
        path = export_to_jsonld(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: tuple(e.participants),
            file_path=tmp_path / "g.jsonld",
            edge_id_extractor=lambda e: e.label,
        )
        doc = _load_jsonld(path)
        hypers = [item for item in doc["@graph"] if item.get("@type") == "Hyperedge"]
        assert len(hypers) == 1
        assert hypers[0]["@type"] == "Hyperedge"
        assert hypers[0]["endpoint"] == ["C", "A", "B"]
        assert hypers[0]["endpoint"] != sorted(hypers[0]["endpoint"])
        assert not any(item.get("@type") == "Edge" for item in doc["@graph"])

    def test_unary_and_missing_endpoints_are_skipped(self, tmp_path):
        nodes = [Entity(name="Apple")]
        edges = [
            Event(label="solo", participants=["Apple"]),
            Relation(source="Apple", target="Ghost", relation_type="x"),
        ]

        def _incident(edge):
            if isinstance(edge, Event):
                return tuple(edge.participants)
            return (edge.source, edge.target)

        path = export_to_jsonld(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=_incident,
            file_path=tmp_path / "g.jsonld",
        )
        doc = _load_jsonld(path)
        typed = [
            item
            for item in doc["@graph"]
            if item.get("@type") in ("Edge", "Hyperedge")
        ]
        nodes_out = [
            item["@id"] for item in doc["@graph"] if item.get("@type") == "Node"
        ]
        assert typed == []
        assert nodes_out == ["Apple"]


# ---------------------------------------------------------------------------
# CSV — round-trip, quoting, direction, dangling, hypergraph
# ---------------------------------------------------------------------------


class TestCSVPairwise:
    def test_round_trip_and_quoting(self, tmp_path):
        nodes = [
            Entity(name="Apple, Inc.", type="ORG", note='He said "hi"'),
            Entity(name="Jobs", type="PERSON", note="line1\nline2"),
        ]
        edges = [
            Relation(
                source="Apple, Inc.",
                target="Jobs",
                relation_type="founded_by",
                description="a, b",
            )
        ]
        folder = _export_csv(tmp_path / "csv", nodes, edges)

        with (folder / "nodes.csv").open(encoding="utf-8", newline="") as handle:
            node_rows = list(csv.DictReader(handle))
        with (folder / "edges.csv").open(encoding="utf-8", newline="") as handle:
            edge_rows = list(csv.DictReader(handle))

        assert [row["id"] for row in node_rows] == ["Apple, Inc.", "Jobs"]
        assert node_rows[0]["name"] == "Apple, Inc."
        assert node_rows[0]["note"] == 'He said "hi"'
        assert node_rows[1]["note"] == "line1\nline2"

        assert edge_rows[0]["source"] == "Apple, Inc."
        assert edge_rows[0]["target"] == "Jobs"
        assert edge_rows[0]["description"] == "a, b"
        header = (folder / "nodes.csv").read_text(encoding="utf-8").splitlines()[0]
        assert header.startswith("id,")

    def test_preserves_direction_b_to_a(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B")]
        edges = [Relation(source="B", target="A", relation_type="leads_to")]
        folder = _export_csv(tmp_path / "csv", nodes, edges)
        with (folder / "edges.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["source"] == "B"
        assert rows[0]["target"] == "A"

    def test_missing_endpoint_is_skipped(self, tmp_path):
        nodes = [Entity(name="Apple")]
        edges = [Relation(source="Apple", target="Ghost", relation_type="x")]
        folder = _export_csv(tmp_path / "csv", nodes, edges)
        with (folder / "edges.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows == []
        with (folder / "nodes.csv").open(encoding="utf-8", newline="") as handle:
            assert [r["id"] for r in csv.DictReader(handle)] == ["Apple"]

    def test_raises_on_nonempty_dir(self, tmp_path):
        dest = tmp_path / "csv"
        dest.mkdir()
        (dest / "keep.txt").write_text("keep", encoding="utf-8")
        with pytest.raises(FileExistsError):
            _export_csv(dest, [Entity(name="Apple")], [])

    def test_overwrite_allows_nonempty_dir(self, tmp_path):
        dest = tmp_path / "csv"
        dest.mkdir()
        (dest / "keep.txt").write_text("keep", encoding="utf-8")
        _export_csv(dest, [Entity(name="Apple")], [], overwrite=True)
        assert (dest / "nodes.csv").exists()
        assert (dest / "keep.txt").exists()


class TestCSVHypergraph:
    def test_members_sorted_stable_delimiter(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B"), Entity(name="C")]
        edges = [Event(label="meeting", participants=["C", "A", "B"])]
        folder = export_to_csv(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: tuple(e.participants),
            folder_path=tmp_path / "csv",
            edge_id_extractor=lambda e: e.label,
            hypergraph=True,
        )
        assert (folder / "hyperedges.csv").exists()
        assert not (folder / "edges.csv").exists()
        with (folder / "hyperedges.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["id"] == "meeting"
        assert rows[0]["members"] == HYPEREDGE_MEMBER_SEP.join(["A", "B", "C"])
        assert rows[0]["label"] == "meeting"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class FakeGraphKA:
    def __init__(self, nodes, edges, hypergraph=False):
        self.nodes = nodes
        self.edges = edges
        self.node_key_extractor = lambda n: n.name
        if hypergraph:
            self.nodes_in_edge_extractor = lambda e: tuple(e.participants)
            self.edge_key_extractor = lambda e: e.label
            self.metadata = {"type": "hypergraph"}
        else:
            self.nodes_in_edge_extractor = lambda e: (e.source, e.target)
            self.edge_key_extractor = lambda e: (
                f"{e.source}-{e.relation_type}-{e.target}"
            )
            self.metadata = {"type": "graph"}

    def export_obsidian(self, *args, **kwargs):
        return None

    def load(self, path):
        return None


class FakeListKA:
    def load(self, path):
        return None


def _ka_dir(tmp_path):
    ka = tmp_path / "ka"
    ka.mkdir()
    (ka / "data.json").write_text(
        json.dumps({"nodes": [], "edges": []}), encoding="utf-8"
    )
    (ka / "metadata.json").write_text(
        json.dumps({"template": "general/biography_graph", "lang": "en"}),
        encoding="utf-8",
    )
    return ka


class TestCLIExport:
    def test_graphml_writes_directed_edge(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B")],
            [Relation(source="B", target="A", relation_type="leads_to")],
        )
        out = tmp_path / "out.graphml"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "graphml", str(ka_dir), "-o", str(out)]
            )
        assert result.exit_code == 0, result.output
        _root, graph, ns = _parse_graphml(out)
        assert _edge_endpoints(graph, ns) == [("B", "A")]

    def test_graphml_exports_hypergraph(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B"), Entity(name="C")],
            [Event(label="meeting", participants=["A", "B", "C"])],
            hypergraph=True,
        )
        out = tmp_path / "out.graphml"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "graphml", str(ka_dir), "-o", str(out)]
            )
        assert result.exit_code == 0, result.output
        xml = out.read_text(encoding="utf-8")
        assert "hyperedge" in xml
        assert f'xmlns="{GRAPHML_NS}"' in xml

    def test_csv_writes_tables(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B")],
            [Relation(source="B", target="A", relation_type="leads_to")],
        )
        out = tmp_path / "csv_out"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(app, ["export", "csv", str(ka_dir), "-o", str(out)])
        assert result.exit_code == 0, result.output
        with (out / "edges.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["source"] == "B"
        assert rows[0]["target"] == "A"

    def test_csv_hypergraph_writes_hyperedges(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B"), Entity(name="C")],
            [Event(label="meeting", participants=["C", "A", "B"])],
            hypergraph=True,
        )
        out = tmp_path / "csv_out"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(app, ["export", "csv", str(ka_dir), "-o", str(out)])
        assert result.exit_code == 0, result.output
        assert (out / "hyperedges.csv").exists()
        assert not (out / "edges.csv").exists()

    def test_csv_requires_force_for_nonempty_dir(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "csv_out"
        dest.mkdir()
        (dest / "existing.txt").write_text("x", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(app, ["export", "csv", str(ka_dir), "-o", str(dest)])
        assert result.exit_code == 1
        assert "--force" in result.output or "not empty" in result.output

    def test_csv_force_writes_nonempty_dir(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "csv_out"
        dest.mkdir()
        (dest / "existing.txt").write_text("x", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "csv", str(ka_dir), "-o", str(dest), "--force"]
            )
        assert result.exit_code == 0, result.output
        assert (dest / "nodes.csv").exists()

    def test_rejects_non_graph_ka(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeListKA()
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app,
                ["export", "graphml", str(ka_dir), "-o", str(tmp_path / "g.graphml")],
            )
        assert result.exit_code == 1
        assert "graph" in result.output.lower()

    def test_jsonld_writes_pairwise_and_hyperedge(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B")],
            [Relation(source="B", target="A", relation_type="leads_to")],
        )
        out = tmp_path / "out.jsonld"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "jsonld", str(ka_dir), "-o", str(out)]
            )
        assert result.exit_code == 0, result.output
        doc = _load_jsonld(out)
        edges_out = [item for item in doc["@graph"] if item.get("@type") == "Edge"]
        assert edges_out[0]["source"] == "B"
        assert edges_out[0]["target"] == "A"

        fake_h = FakeGraphKA(
            [Entity(name="A"), Entity(name="B"), Entity(name="C")],
            [Event(label="meeting", participants=["C", "A", "B"])],
            hypergraph=True,
        )
        out_h = tmp_path / "h.jsonld"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake_h),
        ):
            result = runner.invoke(
                app, ["export", "jsonld", str(ka_dir), "-o", str(out_h)]
            )
        assert result.exit_code == 0, result.output
        doc_h = _load_jsonld(out_h)
        hypers = [item for item in doc_h["@graph"] if item.get("@type") == "Hyperedge"]
        assert hypers[0]["endpoint"] == ["C", "A", "B"]

    def test_jsonld_requires_force_for_existing_file(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "out.jsonld"
        dest.write_text("SENTINEL", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "jsonld", str(ka_dir), "-o", str(dest)]
            )
        assert result.exit_code != 0
        assert "--force" in result.output or "-f" in result.output
        assert dest.read_text(encoding="utf-8") == "SENTINEL"

    def test_jsonld_force_overwrites_existing_file(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "out.jsonld"
        dest.write_text("SENTINEL", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "jsonld", str(ka_dir), "-o", str(dest), "--force"]
            )
        assert result.exit_code == 0, result.output
        doc = _load_jsonld(dest)
        assert any(item.get("@type") == "Node" for item in doc["@graph"])
