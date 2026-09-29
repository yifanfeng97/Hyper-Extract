"""Unit tests for template parsers - identifiers."""

import pytest
from pydantic import BaseModel

from hyperextract.utils.template_engine.parsers import parse_identifiers
from hyperextract.utils.template_engine.parsers.identifiers import (
    validate_identifiers_fields,
)
from hyperextract.utils.template_engine.parsers.schemas import (
    GraphIdentifiersSchema,
)


class Entity(BaseModel):
    name: str


class Relation(BaseModel):
    source: str
    target: str
    type: str


class CustomRelation(BaseModel):
    """Relation whose endpoint fields are not named source/target."""

    subject: str
    object: str
    type: str


class NumericRelation(BaseModel):
    source: int
    target: int
    type: str


class HyperRelation(BaseModel):
    name: str
    participants: list[str]


class NestedHyperRelation(BaseModel):
    name: str
    group_a: list[str]
    group_b: list[str]


def _graph_members_extractor(relation_members):
    """Build the members extractor via the public parse_identifiers API."""
    identifiers = GraphIdentifiersSchema(
        entity_id="name",
        relation_id="{type}",
        relation_members=relation_members,
    )
    _, _, members_extractor = parse_identifiers(identifiers, "graph")
    return members_extractor


class TestGraphRelationMembers:
    """Dict-based relation_members for binary graph types."""

    def test_default_source_target_mapping(self):
        """Standard {source: source, target: target} mapping works."""
        extractor = _graph_members_extractor({"source": "source", "target": "target"})
        edge = Relation(source="A", target="B", type="knows")

        assert extractor(edge) == ("A", "B")

    def test_direction_is_preserved(self):
        """Directed edges must keep (source, target) order, not sorted order."""
        extractor = _graph_members_extractor({"source": "source", "target": "target"})
        edge = Relation(source="B", target="A", type="manages")

        assert extractor(edge) == ("B", "A")

    def test_custom_field_mapping(self):
        """Dict values map to custom edge field names, per documented contract."""
        extractor = _graph_members_extractor({"source": "subject", "target": "object"})
        edge = CustomRelation(subject="Alice", object="Bob", type="mentors")

        assert extractor(edge) == ("Alice", "Bob")

    def test_custom_field_mapping_preserves_direction(self):
        """Custom-mapped endpoints also keep source -> target order."""
        extractor = _graph_members_extractor({"source": "subject", "target": "object"})
        edge = CustomRelation(subject="Zoe", object="Adam", type="mentors")

        assert extractor(edge) == ("Zoe", "Adam")

    def test_missing_mapped_field_raises(self):
        """Mapping to a field absent from the edge schema raises AttributeError."""
        extractor = _graph_members_extractor({"source": "src", "target": "dst"})
        edge = Relation(source="A", target="B", type="knows")

        with pytest.raises(AttributeError, match="src"):
            extractor(edge)

    def test_non_string_values_coerced_to_str(self):
        """Endpoint values are coerced to strings for key comparison."""
        extractor = _graph_members_extractor({"source": "source", "target": "target"})
        edge = NumericRelation(source=2, target=1, type="links")

        assert extractor(edge) == ("2", "1")


class TestHypergraphRelationMembers:
    """String and list relation_members for hypergraph types."""

    def test_string_members_returns_sorted_participants(self):
        """Unordered hyperedge participants are sorted for a stable key."""
        identifiers = GraphIdentifiersSchema(
            entity_id="name",
            relation_id="{name}",
            relation_members="participants",
        )
        _, _, extractor = parse_identifiers(identifiers, "hypergraph")
        edge = HyperRelation(name="meeting", participants=["Carol", "Alice", "Bob"])

        assert extractor(edge) == ("Alice", "Bob", "Carol")

    def test_list_members_returns_sorted_groups(self):
        """Nested hyperedge groups are each sorted for a stable key."""
        identifiers = GraphIdentifiersSchema(
            entity_id="name",
            relation_id="{name}",
            relation_members=["group_a", "group_b"],
        )
        _, _, extractor = parse_identifiers(identifiers, "hypergraph")
        edge = NestedHyperRelation(name="match", group_a=["Y", "X"], group_b=["B", "A"])

        assert extractor(edge) == (("X", "Y"), ("A", "B"))


class TestValidateHypergraphMembers:
    """Hypergraph relation_members (string / list) must be field-checked too."""

    @staticmethod
    def _identifiers(members):
        return GraphIdentifiersSchema(
            entity_id="name",
            relation_id="{name}|{type}",
            relation_members=members,
        )

    @staticmethod
    def _declared(relations):
        return {"entities": {"name"}, "relations": set(relations)}

    def test_string_members_must_be_declared(self):
        with pytest.raises(ValueError, match="attendees"):
            validate_identifiers_fields(
                self._identifiers("attendees"),
                "hypergraph",
                self._declared(["name", "type", "participants"]),
            )

    def test_list_members_must_be_declared(self):
        with pytest.raises(ValueError, match="group_b"):
            validate_identifiers_fields(
                self._identifiers(["group_a", "group_b"]),
                "hypergraph",
                self._declared(["name", "type", "group_a"]),
            )

    def test_declared_string_members_accepted(self):
        validate_identifiers_fields(
            self._identifiers("participants"),
            "hypergraph",
            self._declared(["name", "type", "participants"]),
        )

    def test_declared_list_members_accepted(self):
        validate_identifiers_fields(
            self._identifiers(["group_a", "group_b"]),
            "hypergraph",
            self._declared(["name", "type", "group_a", "group_b"]),
        )
