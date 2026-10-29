"""Unit tests for GraphML and CSV exporters (hyperextract.utils.exporters).

Pure-function tests use Pydantic fixtures and extractors — no LLM. CLI tests
mock ``Template.create`` / ``load`` against a dumped KA directory.
"""

import csv
import json
import re
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
    export_to_cypher,
)
from hyperextract.utils.exporters.common import default_edge_id, resolve_export_file
from hyperextract.utils.exporters.ka import (
    GRAPH_TYPE_ERROR,
    GraphTypeError,
    export_ka_csv,
    export_ka_cypher,
    export_ka_graphml,
    export_ka_jsonld,
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


class TestJSONLDStructuredValues:
    """JSON-LD is JSON: objects and arrays must not become Python reprs."""

    @staticmethod
    def _export(tmp_path, nodes):
        return _load_jsonld(
            export_to_jsonld(
                nodes,
                [],
                node_id_extractor=lambda n: n.name,
                incident_nodes_extractor=lambda e: (),
                file_path=tmp_path / "g.jsonld",
            )
        )

    def test_dict_field_stays_an_object(self, tmp_path):
        doc = self._export(
            tmp_path, [Entity(name="A", properties={"founded": 1976, "ceo": "Tim"})]
        )
        node = doc["@graph"][0]

        assert node["properties"] == {"founded": 1976, "ceo": "Tim"}

    def test_list_field_stays_an_array(self, tmp_path):
        class Aliased(BaseModel):
            name: str
            aliases: List[str]

        doc = self._export(
            tmp_path, [Aliased(name="A", aliases=["AAPL", "Apple Inc"])]
        )

        assert doc["@graph"][0]["aliases"] == ["AAPL", "Apple Inc"]

    def test_unserializable_value_falls_back_to_string(self, tmp_path):
        from datetime import datetime

        class Dated(BaseModel):
            name: str
            seen_at: datetime

        doc = self._export(
            tmp_path, [Dated(name="A", seen_at=datetime(2026, 1, 2, 3, 4))]
        )

        assert isinstance(doc["@graph"][0]["seen_at"], str)
        assert "2026-01-02" in doc["@graph"][0]["seen_at"]

    def test_empty_containers_are_still_omitted(self, tmp_path):
        doc = self._export(tmp_path, [Entity(name="A")])
        node = doc["@graph"][0]

        assert "properties" not in node
        assert "note" not in node
        assert node["active"] is True


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


class TestCommonHelpers:
    def test_default_edge_id_falls_back(self):
        def _boom(_edge):
            raise ValueError("no id")

        assert default_edge_id(object(), 3, None) == "e3"
        assert default_edge_id(object(), 1, lambda e: None) == "e1"
        assert default_edge_id(object(), 1, lambda e: "") == "e1"
        assert default_edge_id(object(), 1, _boom) == "e1"
        assert default_edge_id(object(), 1, lambda e: "rel") == "rel"

    def test_resolve_export_file_refuses_nonempty_without_overwrite(self, tmp_path):
        dest = tmp_path / "out.graphml"
        dest.write_text("KEEP", encoding="utf-8")
        with pytest.raises(FileExistsError):
            resolve_export_file(dest, overwrite=False)
        assert dest.read_text(encoding="utf-8") == "KEEP"
        resolved = resolve_export_file(dest, overwrite=True)
        assert resolved == dest

    def test_export_ka_graphml_and_csv_match_encoders(self, tmp_path):
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B")],
            [Relation(source="B", target="A", relation_type="leads_to")],
        )
        path = export_ka_graphml(fake, tmp_path / "g.graphml")
        _root, graph, ns = _parse_graphml(path)
        assert _edge_endpoints(graph, ns) == [("B", "A")]
        folder = export_ka_csv(fake, tmp_path / "csv")
        with (folder / "edges.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["source"] == "B"

    def test_export_ka_rejects_non_graph(self, tmp_path):
        with pytest.raises(GraphTypeError, match="graph-type"):
            export_ka_graphml(FakeListKA(), tmp_path / "g.graphml")
        with pytest.raises(GraphTypeError) as exc:
            export_ka_csv(FakeListKA(), tmp_path / "csv")
        assert str(exc.value) == GRAPH_TYPE_ERROR

    def test_export_ka_graphml_requires_overwrite(self, tmp_path):
        dest = tmp_path / "g.graphml"
        dest.write_text("KEEP", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with pytest.raises(FileExistsError):
            export_ka_graphml(fake, dest)
        assert dest.read_text(encoding="utf-8") == "KEEP"
        export_ka_graphml(fake, dest, overwrite=True)
        assert dest.read_text(encoding="utf-8") != "KEEP"

    def test_export_ka_cypher_keeps_nary_hyperedge(self, tmp_path):
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B"), Entity(name="C")],
            [Event(label="meeting", participants=["C", "A", "B"])],
            hypergraph=True,
        )
        via_adapter = export_ka_cypher(fake, tmp_path / "via_ka.cypher")
        via_encoder = export_to_cypher(
            fake.nodes,
            fake.edges,
            node_id_extractor=fake.node_key_extractor,
            incident_nodes_extractor=fake.nodes_in_edge_extractor,
            file_path=tmp_path / "via_enc.cypher",
            edge_id_extractor=fake.edge_key_extractor,
        )
        adapter_text = via_adapter.read_text(encoding="utf-8")
        assert adapter_text == via_encoder.read_text(encoding="utf-8")
        assert ":Hyperedge" in adapter_text
        assert "[:IN]" in adapter_text
        assert adapter_text.count("[:IN]") == 3
        assert "-[:REL]" not in adapter_text

    def test_export_ka_cypher_rejects_non_graph(self, tmp_path):
        with pytest.raises(GraphTypeError) as exc:
            export_ka_cypher(FakeListKA(), tmp_path / "g.cypher")
        assert str(exc.value) == GRAPH_TYPE_ERROR
        assert "Cypher" in GRAPH_TYPE_ERROR

    def test_export_ka_jsonld_matches_encoder(self, tmp_path):
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B")],
            [Relation(source="B", target="A", relation_type="leads_to")],
        )
        via_adapter = export_ka_jsonld(fake, tmp_path / "via_ka.jsonld")
        via_encoder = export_to_jsonld(
            fake.nodes,
            fake.edges,
            node_id_extractor=fake.node_key_extractor,
            incident_nodes_extractor=fake.nodes_in_edge_extractor,
            file_path=tmp_path / "via_enc.jsonld",
            edge_id_extractor=fake.edge_key_extractor,
        )
        assert _load_jsonld(via_adapter) == _load_jsonld(via_encoder)
        edges_out = [
            item
            for item in _load_jsonld(via_adapter)["@graph"]
            if item.get("@type") == "Edge"
        ]
        assert edges_out[0]["source"] == "B"
        assert edges_out[0]["target"] == "A"

        hyper = FakeGraphKA(
            [Entity(name="A"), Entity(name="B"), Entity(name="C")],
            [Event(label="meeting", participants=["C", "A", "B"])],
            hypergraph=True,
        )
        hyper_path = export_ka_jsonld(hyper, tmp_path / "hyper.jsonld")
        hypers = [
            item
            for item in _load_jsonld(hyper_path)["@graph"]
            if item.get("@type") == "Hyperedge"
        ]
        assert len(hypers) == 1
        assert hypers[0]["endpoint"] == ["C", "A", "B"]

    def test_export_ka_jsonld_rejects_non_graph(self, tmp_path):
        with pytest.raises(GraphTypeError) as exc:
            export_ka_jsonld(FakeListKA(), tmp_path / "g.jsonld")
        assert str(exc.value) == GRAPH_TYPE_ERROR


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

    def test_graphml_requires_force_for_existing_file(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "out.graphml"
        dest.write_text("KEEP-ME", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "graphml", str(ka_dir), "-o", str(dest)]
            )
        assert result.exit_code != 0
        assert "--force" in result.output or "-f" in result.output
        assert dest.read_text(encoding="utf-8") == "KEEP-ME"

    def test_graphml_force_overwrites_existing_file(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "out.graphml"
        dest.write_text("KEEP-ME", encoding="utf-8")
        fake = FakeGraphKA([Entity(name="A")], [])
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "graphml", str(ka_dir), "-o", str(dest), "--force"]
            )
        assert result.exit_code == 0, result.output
        assert dest.read_text(encoding="utf-8") != "KEEP-ME"

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




# ---------------------------------------------------------------------------
# Cypher — pairwise REL, N-ary Hyperedge (no clique)
# ---------------------------------------------------------------------------


class TypedRel(BaseModel):
    source: str
    target: str
    type: str


class TestCypherExport:
    def test_pairwise_uses_rel_and_direction(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B")]
        edges = [Relation(source="B", target="A", relation_type="leads_to")]
        path = export_to_cypher(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: (e.source, e.target),
            file_path=tmp_path / "g.cypher",
        )
        text = path.read_text(encoding="utf-8")
        assert 'MERGE (n:Node {id: "A"})' in text
        assert 'MERGE (n:Node {id: "B"})' in text
        assert ":REL" in text
        assert 'id: "B"' in text
        assert ']->(b)' in text
        assert text.index('MERGE (a:Node {id: "B"})') < text.index(
            'MERGE (b:Node {id: "A"})'
        )

    def test_legal_type_becomes_rel_ident(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B")]
        edges = [TypedRel(source="A", target="B", type="KNOWS")]
        path = export_to_cypher(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: (e.source, e.target),
            file_path=tmp_path / "g.cypher",
        )
        assert ":KNOWS" in path.read_text(encoding="utf-8")

    def test_nary_is_hyperedge_not_clique(self, tmp_path):
        nodes = [Entity(name="A"), Entity(name="B"), Entity(name="C")]
        edges = [Event(label="meeting", participants=["C", "A", "B"])]
        path = export_to_cypher(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: tuple(e.participants),
            file_path=tmp_path / "g.cypher",
            edge_id_extractor=lambda e: e.label,
        )
        text = path.read_text(encoding="utf-8")
        assert ":Hyperedge" in text
        assert "[:IN]" in text
        assert text.count("[:IN]") == 3
        member_ids = [
            line.split('id: "')[1].split('"')[0]
            for line in text.splitlines()
            if re.match(r'MERGE \(n\d+:Node \{id: "', line)
        ]
        # Membership MERGEs after the Hyperedge, in extractor order C, A, B
        assert member_ids == ["C", "A", "B"]
        assert "-[:REL]" not in text
        assert not any(
            pair in text
            for pair in (
                '(a)-[r:REL {id: "C-A"}]',
                '(a)-[r:REL {id: "A-B"}]',
                '(a)-[r:REL {id: "C-B"}]',
            )
        )

    def test_statements_are_terminated_and_variables_unique(self, tmp_path):
        """cypher-shell splits on ``;`` and Cypher rejects re-declaring a
        variable inside one statement, so every node/edge must be its own
        ``;``-terminated statement with no duplicate MERGE variable."""
        nodes = [Entity(name="A"), Entity(name="B"), Entity(name="C")]
        edges = [
            Relation(source="A", target="B", relation_type="knows"),
            Event(label="meeting", participants=["A", "B", "C"]),
        ]
        path = export_to_cypher(
            nodes,
            edges,
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: (
                (e.source, e.target)
                if isinstance(e, Relation)
                else tuple(e.participants)
            ),
            file_path=tmp_path / "g.cypher",
        )
        text = path.read_text(encoding="utf-8")
        statements = [s.strip() for s in text.split(";") if s.strip()]
        assert text.rstrip().endswith(";")
        # 3 nodes + 1 relationship + 1 hyperedge
        assert len(statements) == 5
        for statement in statements:
            declared = re.findall(r"MERGE \((\w+)[:{]", statement)
            assert len(declared) == len(set(declared)), statement

    def test_escapes_backslash_and_quote(self, tmp_path):
        nodes = [Entity(name='say "hi"\\')]
        path = export_to_cypher(
            nodes,
            [],
            node_id_extractor=lambda n: n.name,
            incident_nodes_extractor=lambda e: (),
            file_path=tmp_path / "g.cypher",
        )
        text = path.read_text(encoding="utf-8")
        assert r"say \"hi\"\\" in text


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

    def test_cypher_writes_hyperedge_membership(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        fake = FakeGraphKA(
            [Entity(name="A"), Entity(name="B"), Entity(name="C")],
            [Event(label="meeting", participants=["C", "A", "B"])],
            hypergraph=True,
        )
        out = tmp_path / "out.cypher"
        with (
            patch("hyperextract.cli.cli.validate_config"),
            patch(
                "hyperextract.cli.cli.get_template_from_ka", return_value=("t", "en")
            ),
            patch("hyperextract.cli.cli.Template.create", return_value=fake),
        ):
            result = runner.invoke(
                app, ["export", "cypher", str(ka_dir), "-o", str(out)]
            )
        assert result.exit_code == 0, result.output
        text = out.read_text(encoding="utf-8")
        assert ":Hyperedge" in text
        assert "[:IN]" in text
        assert "-[:REL]->" not in text

    def test_cypher_requires_force_for_existing_file(self, tmp_path):
        ka_dir = _ka_dir(tmp_path)
        dest = tmp_path / "out.cypher"
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
                app, ["export", "cypher", str(ka_dir), "-o", str(dest)]
            )
        assert result.exit_code != 0
        assert "--force" in result.output or "-f" in result.output
        assert dest.read_text(encoding="utf-8") == "SENTINEL"
