"""Tests for client factory functions."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from hyperextract.utils.client import (
    _parse_client_spec,
    create_llm,
    create_embedder,
    create_client,
    CompatibleEmbeddings,
    get_client,
    PROVIDER_PRESETS,
)


# =============================================================================
# _parse_client_spec
# =============================================================================


class TestParseClientSpec:
    """Tests for _parse_client_spec string parser."""

    def test_provider_only(self):
        """Provider string only — use all defaults."""
        result = _parse_client_spec("bailian", api_key="sk-test")
        assert result["provider"] == "bailian"
        assert result["model"] == "qwen3.6-plus"  # default_llm preset
        assert result["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert result["api_key"] == "sk-test"

    def test_provider_and_model(self):
        """Provider:model format — override model, keep preset URL."""
        result = _parse_client_spec("bailian:qwen-plus", api_key="sk-test")
        assert result["provider"] == "bailian"
        assert result["model"] == "qwen-plus"
        assert result["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def test_full_spec(self):
        """Provider:model@url format — full manual specification."""
        result = _parse_client_spec(
            "vllm:Qwen3.5-9B@http://localhost:8000/v1",
            api_key="dummy",
        )
        assert result["provider"] == "vllm"
        assert result["model"] == "Qwen3.5-9B"
        assert result["base_url"] == "http://localhost:8000/v1"
        assert result["api_key"] == "dummy"

    def test_embedder_defaults(self):
        """Embedder default kind uses embedder preset."""
        result = _parse_client_spec(
            "bailian", api_key="sk-test", default_kind="embedder"
        )
        assert result["model"] == "text-embedding-v4"  # default_embedder preset

    def test_provider_orcarouter(self):
        """OrcaRouter preset defaults (OpenAI-compatible gateway)."""
        result = _parse_client_spec("orcarouter", api_key="sk-test")
        assert result["provider"] == "orcarouter"
        assert result["model"] == "orcarouter/auto"  # default_llm preset
        assert result["base_url"] == "https://api.orcarouter.ai/v1"

    def test_provider_orcarouter_embedder(self):
        """OrcaRouter embedder default uses the namespaced embedder model."""
        result = _parse_client_spec(
            "orcarouter", api_key="sk-test", default_kind="embedder"
        )
        assert result["model"] == "openai/text-embedding-3-small"

    def test_dict_input(self):
        """Dict input is passed through with api_key fallback."""
        result = _parse_client_spec(
            {"provider": "custom", "model": "my-model", "base_url": "http://test/v1"},
            api_key="fallback-key",
        )
        assert result["provider"] == "custom"
        assert result["model"] == "my-model"
        assert result["base_url"] == "http://test/v1"
        assert result["api_key"] == "fallback-key"

    def test_unknown_provider(self):
        """Unknown provider falls through without defaults."""
        result = _parse_client_spec("unknown", api_key="sk-test")
        assert result["provider"] == "unknown"
        assert result["model"] == ""
        assert result["base_url"] == ""

    def test_vllm_no_defaults(self):
        """vLLM provider has None defaults — no URL or model auto-filled."""
        result = _parse_client_spec("vllm", api_key="dummy")
        assert result["provider"] == "vllm"
        assert result["model"] == ""
        assert result["base_url"] == ""


# =============================================================================
# create_llm / create_embedder
# =============================================================================


class TestCreateLLM:
    """Tests for create_llm factory."""

    def test_create_llm_bailian(self):
        """Create LLM with bailian preset."""
        llm = create_llm("bailian", api_key="sk-test")
        assert llm.model_name == "qwen3.6-plus"

    def test_create_llm_openai(self):
        """Create LLM with openai preset."""
        llm = create_llm("openai", api_key="sk-test")
        assert llm.model_name == "gpt-4o-mini"

    def test_create_llm_deepseek(self):
        """Create LLM with deepseek preset (OpenAI-compatible)."""
        llm = create_llm("deepseek", api_key="sk-test")
        assert llm.model_name == "deepseek-v4-flash"
        assert llm.openai_api_base == "https://api.deepseek.com"
        # Thinking is auto-disabled so function_calling structured output works.
        assert llm.extra_body == {"thinking": {"type": "disabled"}}

    def test_create_llm_deepseek_thinking_override(self):
        """User-supplied extra_body overrides the default thinking-disable."""
        llm = create_llm(
            "deepseek",
            api_key="sk-test",
            extra_body={"thinking": {"type": "enabled"}},
        )
        assert llm.extra_body == {"thinking": {"type": "enabled"}}

    def test_create_llm_orcarouter(self):
        """Create LLM with orcarouter preset (OpenAI-compatible gateway)."""
        llm = create_llm("orcarouter", api_key="sk-test")
        assert llm.model_name == "orcarouter/auto"
        assert llm.openai_api_base == "https://api.orcarouter.ai/v1"

    def test_create_llm_orcarouter_env_key(self, monkeypatch):
        """OrcaRouter key is read from ORCAROUTER_API_KEY when api_key is omitted."""
        monkeypatch.setenv("ORCAROUTER_API_KEY", "sk-orca-test")
        llm = create_llm("orcarouter")
        assert llm.openai_api_key.get_secret_value() == "sk-orca-test"

    def test_create_llm_deepseek_reads_provider_env_key(self, monkeypatch):
        """create_llm('deepseek') uses DEEPSEEK_API_KEY when api_key is omitted."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
        llm = create_llm("deepseek")
        assert llm.openai_api_key.get_secret_value() == "sk-deepseek-test"

    def test_create_llm_deepseek_prefers_provider_env_over_openai(self, monkeypatch):
        """DeepSeek prefers DEEPSEEK_API_KEY when both provider and OpenAI keys are set."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        llm = create_llm("deepseek")
        assert llm.openai_api_key.get_secret_value() == "sk-deepseek-test"

    def test_create_llm_openai_still_uses_openai_env_key(self, monkeypatch):
        """OpenAI shorthand still resolves OPENAI_API_KEY (regression)."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        llm = create_llm("openai:gpt-4o-mini")
        assert llm.model_name == "gpt-4o-mini"
        assert llm.openai_api_key.get_secret_value() == "sk-openai-test"

    def test_create_llm_explicit_api_key_wins(self, monkeypatch):
        """Explicit api_key= takes priority over provider and OpenAI env vars."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        llm = create_llm("deepseek", api_key="sk-explicit")
        assert llm.openai_api_key.get_secret_value() == "sk-explicit"

    def test_create_llm_deepseek_falls_back_to_openai_env_key(self, monkeypatch):
        """DeepSeek still falls back to OPENAI_API_KEY when DEEPSEEK_API_KEY is unset."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        llm = create_llm("deepseek")
        assert llm.openai_api_key.get_secret_value() == "sk-openai-test"

    def test_create_llm_custom_model(self):
        """Override model via string shorthand."""
        llm = create_llm("bailian:qwen-plus", api_key="sk-test")
        assert llm.model_name == "qwen-plus"

    def test_create_llm_from_dict(self):
        """Create LLM from dict config."""
        llm = create_llm(
            {"provider": "custom", "model": "gpt-4", "base_url": "http://test/v1"},
            api_key="sk-test",
            temperature=0.5,
        )
        assert llm.model_name == "gpt-4"


class TestCreateEmbedder:
    """Tests for create_embedder factory."""

    def test_create_embedder_openai(self):
        """OpenAI embedder uses native OpenAIEmbeddings."""
        emb = create_embedder("openai", api_key="sk-test")
        from langchain_openai import OpenAIEmbeddings

        assert isinstance(emb, OpenAIEmbeddings)

    def test_create_embedder_bailian(self):
        """Bailian embedder uses CompatibleEmbeddings (custom base_url)."""
        emb = create_embedder("bailian", api_key="sk-test")
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._model == "text-embedding-v4"

    def test_create_embedder_vllm(self):
        """vLLM embedder uses CompatibleEmbeddings."""
        emb = create_embedder(
            "vllm:bge-m3@http://localhost:8001/v1",
            api_key="dummy",
        )
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._model == "bge-m3"

    def test_create_embedder_orcarouter(self):
        """OrcaRouter embedder uses CompatibleEmbeddings (custom base_url)."""
        emb = create_embedder("orcarouter", api_key="sk-test")
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._model == "openai/text-embedding-3-small"

    def test_create_embedder_orcarouter_env_key(self, monkeypatch):
        """OrcaRouter embedder reads ORCAROUTER_API_KEY when api_key is omitted."""
        monkeypatch.setenv("ORCAROUTER_API_KEY", "sk-orca-test")
        emb = create_embedder("orcarouter")
        assert emb._client.api_key == "sk-orca-test"

    def test_create_embedder_reads_openai_env_key(self, monkeypatch):
        """create_embedder uses _env_api_key so OPENAI_API_KEY is picked up."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-emb")
        emb = create_embedder("openai")
        assert emb.openai_api_key.get_secret_value() == "sk-openai-emb"

    def test_create_embedder_explicit_api_key_wins(self, monkeypatch):
        """Explicit api_key= still wins for embedders (regression)."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-emb")
        emb = create_embedder("openai", api_key="sk-explicit-emb")
        assert emb.openai_api_key.get_secret_value() == "sk-explicit-emb"

    def test_create_embedder_custom_url_reads_openai_env_key(self, monkeypatch):
        """CompatibleEmbeddings path also resolves the env key via the factory."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-emb")
        emb = create_embedder("bailian")
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._client.api_key == "sk-openai-emb"


# =============================================================================
# create_client (unified API)
# =============================================================================


class TestCreateClient:
    """Tests for create_client unified factory."""

    def test_pattern_a_single_provider(self):
        """Pattern A: Single provider string for both LLM and embedder."""
        llm, emb = create_client("bailian", api_key="sk-test")
        assert llm.model_name == "qwen3.6-plus"
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._model == "text-embedding-v4"

    def test_pattern_b_separate_specs(self):
        """Pattern B: Separate llm and embedder specs (vLLM)."""
        llm, emb = create_client(
            llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
            embedder="vllm:bge-m3@http://localhost:8001/v1",
            api_key="dummy",
        )
        assert llm.model_name == "Qwen3.5-9B"
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._model == "bge-m3"

    def test_pattern_c_mixed(self):
        """Pattern C: Mixed deployment (Bailian LLM + local embedder)."""
        llm, emb = create_client(
            llm="bailian:qwen-plus",
            embedder="vllm:bge-m3@http://localhost:8001/v1",
            api_key="sk-test",
        )
        assert llm.model_name == "qwen-plus"
        assert isinstance(emb, CompatibleEmbeddings)
        assert emb._model == "bge-m3"

    def test_no_args_raises(self):
        """Calling with no arguments raises ValueError."""
        with pytest.raises(ValueError, match="Must provide"):
            create_client()

    def test_temperature_forwarded(self):
        """Extra kwargs like temperature are forwarded to LLM."""
        llm, _ = create_client("bailian", api_key="sk-test", temperature=0.5)
        assert llm.temperature == 0.5


# =============================================================================
# CompatibleEmbeddings
# =============================================================================


class TestCompatibleEmbeddings:
    """Tests for CompatibleEmbeddings wrapper."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client that returns deterministic embeddings."""
        mock = MagicMock()
        mock.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        )
        return mock

    def test_embed_query(self, mock_openai_client):
        """embed_query sends string input and returns vector."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_query("hello world")
            assert len(result) == 3
            assert result == [0.1, 0.2, 0.3]

    def test_embed_documents(self, mock_openai_client):
        """embed_documents sends batch string input."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[
                MagicMock(embedding=[0.1, 0.2]),
                MagicMock(embedding=[0.3, 0.4]),
            ]
        )
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_documents(["hello", "world"])
            assert len(result) == 2
            assert result[0] == [0.1, 0.2]
            assert result[1] == [0.3, 0.4]

    def test_empty_texts(self):
        """Empty input returns empty list."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        assert emb.embed_documents([]) == []

    def test_chunking(self, mock_openai_client):
        """Long texts are split into chunks that fit token limits."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
            chunk_size=1,  # Force batching into single-item calls
        )
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.5, 0.5])]
        )
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_documents(["short", "also short"])
            assert len(result) == 2
            # Should have been called twice due to chunk_size=1
            assert mock_openai_client.embeddings.create.call_count == 2

    def test_max_batch_size_splits_requests(self, mock_openai_client):
        """Inputs are split so no request exceeds max_batch_size (issue #33).

        Providers like Bailian/DashScope reject batches larger than 10. With
        25 inputs and max_batch_size=10, embed_documents must issue 3 requests
        (10 + 10 + 5) and never send more than 10 inputs in a single call.
        """
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
            max_batch_size=10,
        )

        def fake_create(input, model):
            # Echo back one embedding per input so indexing stays aligned.
            return MagicMock(data=[MagicMock(embedding=[0.1, 0.2]) for _ in input])

        mock_openai_client.embeddings.create.side_effect = fake_create
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_documents([f"text-{i}" for i in range(25)])

        assert len(result) == 25
        assert mock_openai_client.embeddings.create.call_count == 3
        for call in mock_openai_client.embeddings.create.call_args_list:
            assert len(call.kwargs["input"]) <= 10

    def test_default_batch_size_is_conservative(self):
        """Default max_batch_size stays within the strictest known provider cap."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        assert emb._max_batch_size <= 10

    def test_chunk_size_alias_back_compat(self):
        """Legacy `chunk_size` keyword still controls the batch size."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
            chunk_size=5,
        )
        assert emb._max_batch_size == 5

    def test_multichunk_uses_true_mean(self, mock_openai_client):
        """A text split into 3+ chunks is reduced to the true mean embedding.

        The old pairwise (prev + curr) / 2 produced [6.75, ...] for chunk
        vectors 3/6/9; the correct mean is (3 + 6 + 9) / 3 = 6.
        """
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[
                MagicMock(embedding=[3.0, 3.0, 3.0]),
                MagicMock(embedding=[6.0, 6.0, 6.0]),
                MagicMock(embedding=[9.0, 9.0, 9.0]),
            ]
        )
        # Force the single input text to split into three chunks.
        with (
            patch.object(
                emb, "_split_texts", return_value=[("c1", 0), ("c2", 0), ("c3", 0)]
            ),
            patch.object(emb, "_client", mock_openai_client),
        ):
            result = emb.embed_documents(["a long text"])

        assert result == [[6.0, 6.0, 6.0]]

    def test_single_chunk_embedding_unchanged(self, mock_openai_client):
        """A single-chunk text returns its embedding unchanged (regression guard)."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        )
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_documents(["hi"])

        assert result == [[0.1, 0.2, 0.3]]

    def test_blank_text_not_sent_and_zero_filled(self, mock_openai_client):
        """Blank texts are never sent to the API and backfill as a zero vector.

        Providers like Bailian/DashScope reject empty-string input, so a blank
        document must not appear in the request and must still keep the output
        aligned with the input.
        """
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[
                MagicMock(embedding=[0.1, 0.2, 0.3]),
                MagicMock(embedding=[0.4, 0.5, 0.6]),
            ]
        )
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_documents(["hello", "", "world"])

        # Output aligns with input; blank index is a zero vector.
        assert len(result) == 3
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.0, 0.0, 0.0]
        assert result[2] == [0.4, 0.5, 0.6]

        # The blank string was never included in any API request.
        assert mock_openai_client.embeddings.create.call_count == 1
        sent = mock_openai_client.embeddings.create.call_args.kwargs["input"]
        assert sent == ["hello", "world"]

    def test_all_blank_probes_with_non_empty_input(self, mock_openai_client):
        """When every input is blank, the dimension probe uses non-empty input."""
        emb = CompatibleEmbeddings(
            model="test-model",
            api_key="sk-test",
            base_url="http://test/v1",
        )
        mock_openai_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.0, 0.0])]
        )
        with patch.object(emb, "_client", mock_openai_client):
            result = emb.embed_documents(["", "   "])

        assert result == [[0.0, 0.0], [0.0, 0.0]]
        # Exactly one (probe) call, and its input is non-empty.
        assert mock_openai_client.embeddings.create.call_count == 1
        probe_input = mock_openai_client.embeddings.create.call_args.kwargs["input"]
        assert isinstance(probe_input, str) and probe_input.strip()


# =============================================================================
# get_client (config file)
# =============================================================================


class TestGetClient:
    """Tests for get_client reading from config file."""

    def test_get_client_from_file(self, tmp_path: Path):
        """Read client config from TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[llm]\n"
            'provider = "bailian"\n'
            'model = "qwen-plus"\n'
            'api_key = "sk-from-file"\n'
            'base_url = ""\n'
            "[embedder]\n"
            'provider = "bailian"\n'
            'model = "text-embedding-v4"\n'
            'api_key = "sk-from-file"\n'
            'base_url = ""\n'
        )
        llm, emb = get_client(config_file)
        assert llm.model_name == "qwen-plus"
        assert isinstance(emb, CompatibleEmbeddings)

    def test_get_client_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Missing config file returns default configs."""
        # Ensure consistent environment for default OpenAI fallback
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        config_file = tmp_path / "nonexistent.toml"
        llm, emb = get_client(config_file)
        assert llm.model_name == "gpt-4o-mini"  # default fallback
        from langchain_openai import OpenAIEmbeddings

        assert isinstance(emb, OpenAIEmbeddings)


# =============================================================================
# PROVIDER_PRESETS consistency
# =============================================================================


class TestProviderPresets:
    """Tests for PROVIDER_PRESETS data consistency."""

    def test_bailian_defaults(self):
        """Bailian preset has expected defaults."""
        preset = PROVIDER_PRESETS["bailian"]
        assert preset["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert preset["default_llm"] == "qwen3.6-plus"
        assert preset["default_embedder"] == "text-embedding-v4"

    def test_openai_defaults(self):
        """OpenAI preset has expected defaults."""
        preset = PROVIDER_PRESETS["openai"]
        assert preset["base_url"] == "https://api.openai.com/v1"
        assert preset["default_llm"] == "gpt-4o-mini"
        assert preset["default_embedder"] == "text-embedding-3-small"

    def test_vllm_no_defaults(self):
        """vLLM preset has None defaults (must be specified explicitly)."""
        preset = PROVIDER_PRESETS["vllm"]
        assert preset["base_url"] is None
        assert preset["default_llm"] is None
        assert preset["default_embedder"] is None

    def test_deepseek_provider(self):
        """DeepSeek has its own preset (OpenAI-compatible, no embeddings)."""
        assert "deepseek" in PROVIDER_PRESETS
        preset = PROVIDER_PRESETS["deepseek"]
        assert preset["base_url"] == "https://api.deepseek.com"
        assert preset["default_llm"] == "deepseek-v4-flash"
        assert preset["default_embedder"] is None

    def test_orcarouter_provider(self):
        """OrcaRouter has its own preset (OpenAI-compatible, named models)."""
        assert "orcarouter" in PROVIDER_PRESETS
        preset = PROVIDER_PRESETS["orcarouter"]
        assert preset["base_url"] == "https://api.orcarouter.ai/v1"
        assert preset["default_llm"] == "orcarouter/auto"
        assert preset["default_embedder"] == "openai/text-embedding-3-small"

    def test_all_presets_have_base_url_or_none(self):
        """Every preset has either a base_url or None (for vLLM)."""
        for name, preset in PROVIDER_PRESETS.items():
            assert "base_url" in preset
            assert "default_llm" in preset
            assert "default_embedder" in preset

    def test_google_provider(self):
        """Native Gemini extra is wired (not OrcaRouter)."""
        assert "google" in PROVIDER_PRESETS
        preset = PROVIDER_PRESETS["google"]
        assert preset["base_url"] == ""
        assert preset["default_llm"] == "gemini-3.8-flash"
        assert preset["default_embedder"] is None
        assert PROVIDER_PRESETS["gemini"] == preset


class TestGoogleGeminiProvider:
    """Google / Gemini native client — no live API calls."""

    def test_parse_google_defaults(self):
        result = _parse_client_spec("google", api_key="sk-google")
        assert result["provider"] == "google"
        assert result["model"] == "gemini-3.8-flash"
        assert result["base_url"] == ""

    def test_parse_gemini_alias(self):
        result = _parse_client_spec("gemini:gemini-2.5-flash", api_key="sk-google")
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-2.5-flash"

    def test_env_prefers_google_then_gemini(self, monkeypatch):
        from hyperextract.utils.client import _env_api_key

        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "sk-gemini-only")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-must-not-win")
        assert _env_api_key("google") == "sk-gemini-only"

        monkeypatch.setenv("GOOGLE_API_KEY", "sk-google-first")
        assert _env_api_key("gemini") == "sk-google-first"

    def test_env_does_not_fall_back_to_openai(self, monkeypatch):
        from hyperextract.utils.client import _env_api_key

        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-must-not-win")
        assert _env_api_key("google") == ""

    def test_create_llm_uses_chat_google(self):
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as MockChat:
            create_llm("google:gemini-3.8-flash", api_key="sk-google-1")
            MockChat.assert_called_once()
            kwargs = MockChat.call_args.kwargs
            assert kwargs["model"] == "gemini-3.8-flash"
            assert kwargs["api_key"] == "sk-google-1"
            assert kwargs["temperature"] == 0

    def test_create_llm_env_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "sk-google-env")
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as MockChat:
            create_llm("google")
            assert MockChat.call_args.kwargs["api_key"] == "sk-google-env"

    def test_create_llm_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("langchain_google_genai.ChatGoogleGenerativeAI"):
            with pytest.raises(ValueError, match="Google API key"):
                create_llm("google")

    def test_create_llm_missing_extra_import_error(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "langchain_google_genai" or name.startswith(
                "langchain_google_genai."
            ):
                raise ImportError("simulated missing extra")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ImportError, match="hyperextract\\[google\\]"):
                create_llm("google", api_key="sk-google-1")

    def test_create_embedder_raises(self):
        with pytest.raises(ValueError, match="embeddings"):
            create_embedder("google", api_key="sk-google")
        with pytest.raises(ValueError, match="embeddings"):
            create_embedder("gemini", api_key="sk-google")
