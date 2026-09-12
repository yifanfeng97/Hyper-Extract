"""Unit tests for TemplateFactory."""

from pathlib import Path

import pytest
import yaml

from hyperextract.utils.template_engine import Gallery, TemplateFactory


class TestTemplateFactoryCreate:
    """Test cases for TemplateFactory create methods."""

    def test_get_existing_template(self):
        """Test getting an existing template from gallery."""
        template = Gallery.get("general/model")

        assert template is not None
        assert template.name == "model"
        assert template.type in ["model", "list", "set", "graph"]

    def test_get_nonexistent_template(self):
        """Test getting a nonexistent template returns None."""
        template = Gallery.get("nonexistent/template")

        assert template is None


class TestTemplateFactoryCreateMethod:
    """Test cases for TemplateFactory create method."""

    def test_create_with_language(self, llm_client, embedder):
        """Test create() with language parameter."""
        result = TemplateFactory.create(
            source="general/model",
            language="en",
            llm_client=llm_client,
            embedder=embedder,
        )

        assert result is not None
        assert result.metadata.get("lang") == "en"

    def test_create_without_source_raises(self, llm_client, embedder):
        """Test that create() raises error without source."""
        with pytest.raises((ValueError, TypeError)):
            TemplateFactory.create(
                llm_client=llm_client,
                embedder=embedder,
            )

    def test_create_from_templatecfg_instance(self, llm_client, embedder):
        """create() accepts a TemplateCfg instance (documented + typed source)."""
        cfg = Gallery.get("general/model")

        result = TemplateFactory.create(cfg, "en", llm_client, embedder)

        assert result is not None
        assert result.metadata["template"] == cfg.name
        assert result.metadata["lang"] == "en"

    def test_create_method_template(self, llm_client, embedder):
        """Test creating a method template."""
        result = TemplateFactory.create(
            source="method/light_rag",
            llm_client=llm_client,
            embedder=embedder,
        )

        assert result is not None


class TestTemplateFactoryCreateAllTypes:
    """Test cases for creating all AutoType types."""

    def test_create_model_type(self, llm_client, embedder):
        """Test create() with model type template."""
        result = TemplateFactory.create(
            source="general/model",
            language="en",
            llm_client=llm_client,
            embedder=embedder,
        )

        from hyperextract.types import AutoModel

        assert isinstance(result, AutoModel)
        assert result.metadata.get("type") == "model"

    def test_create_list_type(self, llm_client, embedder):
        """Test create() with list type template."""
        result = TemplateFactory.create(
            source="general/list",
            language="en",
            llm_client=llm_client,
            embedder=embedder,
        )

        from hyperextract.types import AutoList

        assert isinstance(result, AutoList)
        assert result.metadata.get("type") == "list"

    def test_create_set_type(self, llm_client, embedder):
        """Test create() with set type template."""
        result = TemplateFactory.create(
            source="general/set",
            language="en",
            llm_client=llm_client,
            embedder=embedder,
        )

        from hyperextract.types import AutoSet

        assert isinstance(result, AutoSet)
        assert result.metadata.get("type") == "set"

    def test_create_graph_type(self, llm_client, embedder):
        """Test create() with graph type template."""
        result = TemplateFactory.create(
            source="general/graph",
            language="en",
            llm_client=llm_client,
            embedder=embedder,
        )

        from hyperextract.types import AutoGraph

        assert isinstance(result, AutoGraph)
        assert result.metadata.get("type") == "graph"


class TestTemplateFactoryUnknownType:
    """Unknown AutoType must fail closed with ValueError, not UnboundLocalError."""

    def test_unknown_type_yaml_raises_valueerror(self, tmp_path, llm_client, embedder):
        repo_root = Path(__file__).resolve().parents[2]
        src = (repo_root / "hyperextract/templates/presets/general/base_model.yaml").read_text(
            encoding="utf-8"
        )
        yaml_path = tmp_path / "not_a_type.yaml"
        yaml_path.write_text(
            src.replace("\ntype: model\n", "\ntype: not_a_type\n"),
            encoding="utf-8",
        )
        raw_type = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["type"]
        assert raw_type == "not_a_type"

        # Parser Literal rejects unknown types at load; assignment reaches the
        # factory match the same way an unbound type would after a looser schema.
        cfg = Gallery.get("general/model").model_copy(deep=True)
        cfg.type = raw_type

        with pytest.raises(ValueError, match="not_a_type") as exc_info:
            TemplateFactory.create(cfg, "en", llm_client, embedder)

        assert not isinstance(exc_info.value, UnboundLocalError)
        message = str(exc_info.value)
        assert "Allowed types:" in message
        assert "model" in message
        assert "graph" in message
        assert "hypergraph" in message


_DOCUMENT_YAML = """
language: en
name: document_fixture
type: document
tags: [test]
description: Minimal AutoDocument fixture (chunk corpus, no LLM extraction).
output:
  description: Unused; AutoDocument stores raw chunks.
  fields:
  - name: content
    type: str
    description: Placeholder required by TemplateCfg.
guideline:
  target: Unused; AutoDocument does not extract.
  rules:
  - Chunk text only; do not invent graph schema.
display:
  label: '{content}'
"""


class TestTemplateFactoryDocumentType:
    def test_create_document_yaml_type(self, tmp_path, llm_client, embedder):
        yaml_path = tmp_path / "document.yaml"
        yaml_path.write_text(_DOCUMENT_YAML, encoding="utf-8")

        from hyperextract.utils.template_engine import Template

        result = Template.create(
            str(yaml_path),
            "en",
            llm_client,
            embedder,
        )

        from hyperextract import AutoDocument

        assert isinstance(result, AutoDocument)
        assert result.metadata["type"] == "document"

    def test_public_import_autodocument(self):
        from hyperextract import AutoDocument as Exported
        from hyperextract.types import AutoDocument as Canonical

        assert Exported is Canonical

    def test_create_gallery_base_document_preset(self, llm_client, embedder):
        from hyperextract import AutoDocument
        from hyperextract.utils.template_engine import Gallery, Template

        assert Gallery.get("general/base_document") is not None
        result = Template.create(
            "general/base_document",
            "en",
            llm_client,
            embedder,
        )
        assert isinstance(result, AutoDocument)
        assert result.metadata.get("type") == "document"
