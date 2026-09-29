"""Identifier parser - generates extraction functions from YAML config."""

import re
from collections.abc import Callable
from typing import Any

from .schemas import (
    VALID_AUTOTYPES,
    GraphIdentifiersSchema,
    NaiveIdentifierSchema,
)


def _extractor(field_or_template: str) -> Callable[[Any], str]:
    """Field or template extractor.

    - Simple field: 'name' -> lambda x: x.name
    - Bracket template: '{source}|{type}' -> lambda x: f"{x.source}|{x.type}"

    Raises:
        AttributeError: if field does not exist on item
    """
    if "{" in field_or_template:
        fields = re.findall(r"\{(\w+)\}", field_or_template)

        def extractor(item: Any) -> str:
            missing = [f for f in fields if not hasattr(item, f)]
            if missing:
                raise AttributeError(f"Missing fields: {missing}")
            values = [getattr(item, f, None) for f in fields]
            return field_or_template.format(**dict(zip(fields, values)))

        return extractor

    def extractor(item: Any) -> str:
        if not hasattr(item, field_or_template):
            raise AttributeError(f"Missing field: {field_or_template}")
        value = getattr(item, field_or_template)
        return str(value)

    return extractor


def _members_extractor(
    members: dict[str, str] | str | list[str],
) -> Callable[[Any], tuple[str, ...]]:
    """Relation members extractor:
    Graph:    {source: 's', target: 't'} -> lambda x: (x.s, x.t)
    Hypergraph: 'members' -> lambda x: tuple(sorted(x.members)) or
                'members' -> lambda x: tuple(sorted(x.m) for m in x.members)
    """
    # Handle Graph: preserve (source, target) order for directed edges
    if isinstance(members, dict):
        source_field = members["source"]
        target_field = members["target"]

        def extractor(item: Any) -> tuple[str, str]:
            missing = [f for f in (source_field, target_field) if not hasattr(item, f)]
            if missing:
                raise AttributeError(f"Missing fields: {missing}")
            return (
                str(getattr(item, source_field)),
                str(getattr(item, target_field)),
            )

        return extractor

    # Handle Hypergraph
    if isinstance(members, str):

        def extractor(item: Any) -> tuple[str, ...]:
            return tuple(sorted(getattr(item, members)))

        return extractor

    def extractor(item: str | list[str]) -> tuple[str, ...]:
        result = []
        for m in members:
            result.append(tuple(sorted(getattr(item, m))))
        return tuple(result)

    return extractor


def _placeholders(field_or_template: str) -> list[str]:
    """Bracket placeholders of a template (simple field -> [itself])."""
    if "{" in field_or_template:
        return re.findall(r"\{(\w+)\}", field_or_template)
    return [field_or_template]


def validate_identifiers_fields(
    identifiers: NaiveIdentifierSchema | GraphIdentifiersSchema,
    autotype: VALID_AUTOTYPES,
    declared_fields: dict[str, set[str]],
) -> None:
    """Load-time check: identifiers must reference declared output fields.

    A template whose ``relation_id`` cites ``{type}`` while
    ``relations.fields`` never declares ``type`` previously loaded fine and
    crashed at first merge with an unrelated ``max()`` error (every key
    extraction failed). This check fails at ``Template.create`` instead.

    Args:
        identifiers: identifiers config from YAML.
        autotype: auto type of the template.
        declared_fields: declared output field names, keyed by
            ``"entities"`` / ``"relations"``.

    Raises:
        ValueError: naming each referenced-but-undeclared field.
    """
    if autotype == "set":
        return
    if autotype not in (
        "graph",
        "hypergraph",
        "temporal_graph",
        "spatial_graph",
        "spatio_temporal_graph",
    ):
        return

    entity_fields = declared_fields.get("entities", set())
    relation_fields = declared_fields.get("relations", set())

    problems: list[str] = []
    for field in _placeholders(identifiers.entity_id):
        if field not in entity_fields:
            problems.append(
                f"node_id references '{{{field}}}' but "
                f"entities.fields does not declare '{field}'"
            )
    for field in _placeholders(identifiers.relation_id):
        if field not in relation_fields:
            problems.append(
                f"relation_id references '{{{field}}}' but "
                f"relations.fields does not declare '{field}'"
            )
    if isinstance(identifiers.relation_members, dict):
        for role, field in identifiers.relation_members.items():
            if field not in relation_fields:
                problems.append(
                    f"relation_members['{role}'] references '{{{field}}}' but "
                    f"relations.fields does not declare '{field}'"
                )
    # time/location live on relations (see validator HE-T006 and the presets).
    for attr in ("time_field", "location_field"):
        value = getattr(identifiers, attr, None)
        if value:
            for field in _placeholders(value):
                if field not in relation_fields:
                    problems.append(
                        f"{attr} references '{{{field}}}' but "
                        f"relations.fields does not declare '{field}'"
                    )

    if problems:
        raise ValueError("; ".join(problems))


def parse_identifiers(
    identifiers: NaiveIdentifierSchema | GraphIdentifiersSchema,
    autotype: VALID_AUTOTYPES,
) -> (
    Callable[[Any], str]
    | tuple[
        Callable[[Any], str], Callable[[Any], str], Callable[[Any], tuple[str, ...]]
    ]
):
    """Parse identifiers config and return extractors based on autotype.

    Args:
        identifiers: identifiers config from YAML
        autotype: auto type (model, list, set, graph, hypergraph, ...)

    Returns:
        - For set: item_id_extractor
        - For graph types: (entity_key_extractor, relation_key_extractor, entities_in_relation_extractor)
    """

    if autotype == "set":
        return _extractor(identifiers.item_id)

    if autotype in (
        "graph",
        "hypergraph",
        "temporal_graph",
        "spatial_graph",
        "spatio_temporal_graph",
    ):
        entity_extractor = _extractor(identifiers.entity_id)
        relation_extractor = _extractor(identifiers.relation_id)
        members_extractor = _members_extractor(identifiers.relation_members)
        rets = [entity_extractor, relation_extractor, members_extractor]

        if autotype in ("temporal_graph", "spatio_temporal_graph"):
            time_extractor = _extractor(identifiers.time_field)
            rets.append(time_extractor)

        if autotype in ("spatial_graph", "spatio_temporal_graph"):
            location_extractor = _extractor(identifiers.location_field)
            rets.append(location_extractor)

        return tuple(rets)

    return None


__all__ = [
    "parse_identifiers",
]
