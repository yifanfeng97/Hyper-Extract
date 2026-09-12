"""Client Factory - Create OpenAI LLM and Embedder clients from config.

Provides three levels of API:
    - create_client(): Unified creation for both LLM and Embedder
    - create_llm() / create_embedder(): Separate creation for advanced use
    - get_client(): Read from config.toml (backward compatible)

String shorthand format: provider:model@url
    - "bailian"              → provider only, use preset defaults
    - "bailian:qwen-plus"    → provider + model, use preset URL
    - "vllm:Qwen3.5-9B@http://localhost:8000/v1" → full specification
"""

import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".he"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"

# Official OpenAI API base URL — only this endpoint accepts pre-tokenized input
OPENAI_API_URL = "https://api.openai.com/v1"

# Provider presets: base_url and default models for each provider
PROVIDER_PRESETS: dict[str, dict[str, str | None]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_llm": "gpt-4o-mini",
        "default_embedder": "text-embedding-3-small",
    },
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_llm": "qwen3.6-plus",
        "default_embedder": "text-embedding-v4",
    },
    "vllm": {
        "base_url": None,
        "default_llm": None,
        "default_embedder": None,
    },
    # DeepSeek. OpenAI-compatible endpoint. Current models are deepseek-v4-flash
    # and deepseek-v4-pro; both default to "thinking" mode, which rejects the
    # tool_choice that method="function_calling" relies on, so create_llm()
    # disables thinking for this provider by default (override via extra_body).
    # DeepSeek has no embeddings API — pair it with an OpenAI-compatible embedder.
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "default_llm": "deepseek-v4-flash",
        "default_embedder": None,
    },
    # OrcaRouter. OpenAI-compatible model routing gateway exposing 150+ models
    # from OpenAI, Anthropic, Google, DeepSeek, Qwen, MiniMax, xAI and others
    # behind a single endpoint and API key. Namespaced model ids such as
    # "orcarouter/auto" route to a matching upstream.
    "orcarouter": {
        "base_url": "https://api.orcarouter.ai/v1",
        "default_llm": "orcarouter/auto",
        "default_embedder": "openai/text-embedding-3-small",
    },
    # Anthropic (Claude). Uses the native ChatAnthropic client, so base_url is
    # left empty (the SDK targets api.anthropic.com by default). Anthropic has
    # no embeddings API, hence default_embedder is None — pair it with an
    # OpenAI-compatible embedder.
    "anthropic": {
        "base_url": "",
        "default_llm": "claude-opus-4-8",
        "default_embedder": None,
    },
    "claude": {
        "base_url": "",
        "default_llm": "claude-opus-4-8",
        "default_embedder": None,
    },
    # Google Gemini. Uses the native ChatGoogleGenerativeAI client
    # (langchain-google-genai), so base_url is empty. Gemini Developer API
    # has no mature embedder path in this repo — pair with an OpenAI-compatible
    # embedder. Default model is the current documented stable Flash id
    # (Gemini API models page, 2026-09-04): gemini-3.8-flash.
    "google": {
        "base_url": "",
        "default_llm": "gemini-3.8-flash",
        "default_embedder": None,
    },
    "gemini": {
        "base_url": "",
        "default_llm": "gemini-3.8-flash",
        "default_embedder": None,
    },
}

# Providers handled by the native langchain-anthropic client rather than the
# OpenAI-compatible path.
ANTHROPIC_PROVIDERS = ("anthropic", "claude")

# Providers handled by the native langchain-google-genai client.
GOOGLE_PROVIDERS = ("google", "gemini")

# Native (non-OpenAI-compatible) LLM providers — do not fall back to
# OPENAI_API_KEY when their own env vars are unset.
_NATIVE_LLM_PROVIDERS = ANTHROPIC_PROVIDERS + GOOGLE_PROVIDERS

# Environment variables checked (in order) for each provider's API key.
PROVIDER_API_KEY_ENV: dict[str, tuple[str, ...]] = {
    "anthropic": ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    "claude": ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    "google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "orcarouter": ("ORCAROUTER_API_KEY",),
}


def _env_api_key(provider: str) -> str:
    """Return the first non-empty API key from the provider's env vars.

    Falls back to OPENAI_API_KEY for OpenAI-compatible providers.
    """
    for var in PROVIDER_API_KEY_ENV.get(provider, ()):
        value = os.environ.get(var, "")
        if value:
            return value
    if provider not in _NATIVE_LLM_PROVIDERS:
        return os.environ.get("OPENAI_API_KEY", "")
    return ""


class CompatibleEmbeddings(Embeddings):
    """Embeddings for OpenAI-compatible providers that only accept string input.

    langchain_openai's OpenAIEmbeddings with tiktoken_enabled=True sends
    pre-tokenized integer lists to the API, which OpenAI supports but most
    OpenAI-compatible providers (Ollama, LiteLLM, etc.) do not. This class
    works around that by always sending strings, using tiktoken for chunking
    with a fallback encoding when the model name isn't tiktoken-compatible.
    """

    def __init__(
        self,
        model: str = "text-embedding-ada-002",
        api_key: str | None = None,
        base_url: str | None = None,
        max_batch_size: int = 10,
        chunk_size: int | None = None,
        max_retries: int = 2,
        **kwargs: Any,
    ):
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
            base_url=base_url,
            max_retries=max_retries,
        )
        self._model = model

        # max_batch_size caps how many inputs are sent per embeddings request.
        # Many OpenAI-compatible providers reject large batches (e.g. Bailian /
        # DashScope caps at 10), so the default is intentionally conservative.
        # `chunk_size` is the legacy name for this knob and is kept as an alias.
        self._max_batch_size = chunk_size if chunk_size is not None else max_batch_size

        # Determine the tiktoken encoding to use for chunking
        import tiktoken

        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Model not recognized by tiktoken; use cl100k_base (used by
            # text-embedding-ada-002, text-embedding-3-small, etc.)
            logger.debug(
                "Model '%s' not recognized by tiktoken, using cl100k_base encoding",
                model,
            )
            self._encoding = tiktoken.get_encoding("cl100k_base")

        # Max tokens per request (8191 is the limit for most OpenAI embedders)
        self._max_tokens = kwargs.get("embedding_ctx_length", 8191)

    def _split_texts(self, texts: list[str]) -> list[tuple[str, int]]:
        """Split texts into chunks that fit within token limits.

        Returns list of (text_chunk, original_index) tuples.
        """
        chunks: list[tuple[str, int]] = []
        for i, text in enumerate(texts):
            tokens = self._encoding.encode(text)
            if len(tokens) <= self._max_tokens:
                chunks.append((text, i))
            else:
                # Split into chunks
                for j in range(0, len(tokens), self._max_tokens):
                    chunk_tokens = tokens[j : j + self._max_tokens]
                    chunk_text = self._encoding.decode(chunk_tokens)
                    chunks.append((chunk_text, i))
        return chunks

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        chunks = self._split_texts(texts)
        if not chunks:
            return []

        # Group chunks into batches no larger than max_batch_size
        all_embeddings: list[list[float] | None] = [None] * len(texts)
        batch: list[tuple[str, int]] = []

        # Accumulate a running sum and count per text so multi-chunk texts get a
        # true mean. A pairwise (prev + curr) / 2 only yields the mean for two
        # chunks; for three or more it biases toward later chunks.
        sums: dict[int, list[float]] = {}
        counts: dict[int, int] = {}

        def _embed_batch(b: list[tuple[str, int]]) -> None:
            # Skip blank chunks: many OpenAI-compatible providers (e.g. Bailian /
            # DashScope) reject empty-string input with a 400. Blank texts are
            # backfilled with a zero vector after all batches complete.
            non_blank = [(text, idx) for text, idx in b if text.strip()]
            if not non_blank:
                return
            response = self._client.embeddings.create(
                input=[text for text, _ in non_blank],
                model=self._model,
            )
            for (text, orig_idx), emb_data in zip(
                non_blank, response.data, strict=False
            ):
                emb = emb_data.embedding
                if orig_idx not in sums:
                    sums[orig_idx] = list(emb)
                    counts[orig_idx] = 1
                else:
                    running = sums[orig_idx]
                    sums[orig_idx] = [a + b for a, b in zip(running, emb, strict=False)]
                    counts[orig_idx] += 1

        for chunk in chunks:
            batch.append(chunk)
            if len(batch) >= self._max_batch_size:
                _embed_batch(batch)
                batch = []

        if batch:
            _embed_batch(batch)

        # Divide each running sum by its chunk count to get the mean embedding.
        dim: int | None = None
        for orig_idx, running in sums.items():
            count = counts[orig_idx]
            mean = [v / count for v in running]
            all_embeddings[orig_idx] = mean
            dim = len(mean)

        # Backfill blank texts (which were skipped above) with a zero vector so
        # the output stays aligned with the input. We never send an empty string
        # to the API. If every input was blank we have no reference dimension, so
        # probe once with a non-empty placeholder to learn it.
        missing_indices = [i for i, e in enumerate(all_embeddings) if e is None]
        if missing_indices:
            if dim is None:
                # Non-whitespace placeholder: a single space can be stripped to
                # empty by strict providers and rejected like an empty string.
                response = self._client.embeddings.create(
                    input=".",
                    model=self._model,
                )
                dim = len(response.data[0].embedding)
            zero_vector = [0.0] * dim
            for i in missing_indices:
                all_embeddings[i] = list(zero_vector)

        return all_embeddings  # type: ignore[return-value]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def _parse_client_spec(
    spec: str | dict,
    *,
    api_key: str = "",
    default_kind: str = "llm",
) -> dict[str, Any]:
    """Parse a client specification string or dict into a config dict.

    String formats:
        - "bailian"              → provider only, use preset defaults
        - "bailian:qwen-plus"    → provider + model, use preset URL
        - "vllm:Qwen3.5-9B@http://localhost:8000/v1" → full specification

    Args:
        spec: String shorthand or dict config.
        api_key: Fallback API key.
        default_kind: "llm" or "embedder", used for default model selection.

    Returns:
        Dict with keys: provider, model, base_url, api_key
    """
    if isinstance(spec, dict):
        return {
            "provider": spec.get("provider", ""),
            "model": spec.get("model", ""),
            "base_url": spec.get("base_url", ""),
            "api_key": spec.get("api_key") or api_key,
            **{
                k: v
                for k, v in spec.items()
                if k not in ("provider", "model", "base_url", "api_key")
            },
        }

    # Parse string shorthand: provider:model@url
    provider = ""
    model = ""
    base_url = ""

    parts = spec.split(":", 1)
    provider = parts[0].strip()

    if len(parts) > 1:
        rest = parts[1].strip()
        if "@" in rest:
            model, base_url = rest.split("@", 1)
            model = model.strip()
            base_url = base_url.strip()
        else:
            model = rest.strip()

    # Fill defaults from preset
    preset = PROVIDER_PRESETS.get(provider, {})
    if not base_url:
        preset_url = preset.get("base_url")
        if preset_url is not None:
            base_url = preset_url
    if not model:
        default_key = f"default_{default_kind}"
        model = preset.get(default_key) or ""

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
    }


def create_llm(
    spec: str | dict,
    *,
    api_key: str = "",
    **kwargs: Any,
) -> BaseChatModel:
    """Create an LLM client from a specification string or dict.

    Args:
        spec: String shorthand (e.g. "bailian:qwen-plus") or dict config.
        api_key: API key fallback.
        **kwargs: Extra args forwarded to ChatOpenAI (e.g. temperature).

    Returns:
        Configured ChatOpenAI instance.

    Examples:
        >>> llm = create_llm("bailian:qwen-plus", api_key="sk-xxx")
        >>> llm = create_llm("vllm:Qwen3.5-9B@localhost:8000/v1", api_key="dummy")
        >>> llm = create_llm({"provider": "bailian", "model": "qwen-plus", "temperature": 0.5})
    """
    config = _parse_client_spec(spec, api_key=api_key, default_kind="llm")
    config.update(kwargs)

    provider = config.get("provider", "")

    if provider in ANTHROPIC_PROVIDERS:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as e:
            raise ImportError(
                "The Anthropic provider requires 'langchain-anthropic'. "
                "Install it with: pip install 'hyperextract[anthropic]'"
            ) from e

        resolved_key = config["api_key"] or _env_api_key(provider)
        if not resolved_key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY (or CLAUDE_API_KEY), "
                "or pass api_key=..."
            )

        return ChatAnthropic(
            model=config["model"],
            api_key=resolved_key,
            temperature=config.get("temperature", 0),
            # Anthropic requires max_tokens; default low (1024) truncates large
            # structured extractions, so use a more generous default.
            max_tokens=config.get("max_tokens", 4096),
        )

    if provider in GOOGLE_PROVIDERS:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise ImportError(
                "The Google / Gemini provider requires 'langchain-google-genai'. "
                "Install it with: pip install 'hyperextract[google]'"
            ) from e

        resolved_key = config["api_key"] or _env_api_key(provider)
        if not resolved_key:
            raise ValueError(
                "No Google API key found. Set GOOGLE_API_KEY (or GEMINI_API_KEY), "
                "or pass api_key=..."
            )

        return ChatGoogleGenerativeAI(
            model=config["model"],
            api_key=resolved_key,
            temperature=config.get("temperature", 0),
        )

    from langchain_openai import ChatOpenAI

    # DeepSeek V4 models default to "thinking" mode, which rejects the
    # tool_choice that method="function_calling" sends for structured output
    # (HTTP 400: "Thinking mode does not support this tool_choice"). Disable it
    # by default so Hyper-Extract's structured extraction works out of the box.
    # Users who want thinking can override: extra_body={"thinking": {"type": "enabled"}}.
    extra_body = dict(config.get("extra_body") or {})
    if provider == "deepseek" and "thinking" not in extra_body:
        extra_body["thinking"] = {"type": "disabled"}

    chat_kwargs: dict[str, Any] = {
        "model": config["model"],
        "api_key": config["api_key"] or _env_api_key(provider),
        "base_url": config.get("base_url") or None,
        "temperature": config.get("temperature", 0),
    }
    if extra_body:
        chat_kwargs["extra_body"] = extra_body
    return ChatOpenAI(**chat_kwargs)


def create_embedder(
    spec: str | dict,
    *,
    api_key: str = "",
    **kwargs: Any,
) -> Embeddings:
    """Create an Embedder client from a specification string or dict.

    Args:
        spec: String shorthand (e.g. "bailian:text-embedding-v4") or dict config.
        api_key: API key fallback.
        **kwargs: Extra args forwarded to the embedder class.

    Returns:
        Configured OpenAIEmbeddings or CompatibleEmbeddings instance.

    Examples:
        >>> emb = create_embedder("bailian", api_key="sk-xxx")
        >>> emb = create_embedder("vllm:bge-m3@localhost:8001/v1", api_key="dummy")
    """
    config = _parse_client_spec(spec, api_key=api_key, default_kind="embedder")

    provider = config.get("provider", "")
    if provider in ANTHROPIC_PROVIDERS:
        raise ValueError(
            "Anthropic does not provide an embeddings API. Configure a separate "
            "OpenAI-compatible embedder, e.g. "
            'create_client(llm="anthropic", embedder="openai:text-embedding-3-small", ...) '
            "or a local vLLM/bge-m3 endpoint."
        )
    if provider in GOOGLE_PROVIDERS:
        raise ValueError(
            "Google / Gemini has no mature embeddings path in this repo. Configure a "
            "separate OpenAI-compatible embedder, e.g. "
            'create_client(llm="google", embedder="openai:text-embedding-3-small", ...) '
            "or a local vLLM/bge-m3 endpoint."
        )

    base_url = config.get("base_url", "")
    uses_custom = bool(base_url and base_url.rstrip("/") != OPENAI_API_URL)

    resolved_key = config["api_key"] or _env_api_key(config.get("provider", ""))

    if uses_custom:
        return CompatibleEmbeddings(
            model=config["model"],
            api_key=resolved_key,
            base_url=base_url,
            **kwargs,
        )
    else:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config["model"],
            api_key=resolved_key,
            **kwargs,
        )


def create_client(
    llm: str | dict | None = None,
    embedder: str | dict | None = None,
    *,
    provider: str = "",
    api_key: str = "",
    **kwargs: Any,
) -> tuple[BaseChatModel, Embeddings]:
    """Create both LLM and Embedder clients in one call.

    Supports three patterns:

    **Pattern A: Single provider string (cloud API, simplest)**
    >>> llm, emb = create_client("bailian", api_key="sk-xxx")
    # Uses preset defaults: qwen3.6-plus + text-embedding-v4

    **Pattern B: Separate specs (vLLM, two independent services)**
    >>> llm, emb = create_client(
    ...     llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    ...     embedder="vllm:bge-m3@http://localhost:8001/v1",
    ...     api_key="dummy",
    ... )

    **Pattern C: Mixed deployment**
    >>> llm = create_client(
    ...     llm="bailian:qwen-plus",
    ...     embedder="vllm:bge-m3@localhost:8001/v1",
    ...     api_key="sk-xxx",
    ... )

    Args:
        llm: LLM spec string/dict, or None to auto-infer from provider.
        embedder: Embedder spec string/dict, or None to auto-infer from provider.
        provider: Fallback provider when llm/embedder are bare strings without provider prefix.
        api_key: Shared API key for both services.
        **kwargs: Extra args forwarded to ChatOpenAI (e.g. temperature).

    Returns:
        (llm_client, embedder_client) tuple.
    """
    # Pattern A: Single provider shorthand
    if llm is None and embedder is None:
        if not provider:
            raise ValueError(
                "Must provide llm=, embedder=, or provider= argument.\n"
                "Examples:\n"
                '  create_client("bailian", api_key="...")\n'
                '  create_client(llm="bailian:qwen-plus", embedder="bailian", api_key="...")\n'
                '  create_client(llm="vllm:Qwen3.5-9B@localhost:8000", '
                'embedder="vllm:bge-m3@localhost:8001", api_key="dummy")'
            )
        # Use provider preset defaults for both
        llm = provider
        embedder = provider

    # Parse llm config
    llm_config = _parse_client_spec(
        llm or provider, api_key=api_key, default_kind="llm"
    )
    llm_config.update(kwargs)

    # Parse embedder config
    # For cloud providers, embedder defaults to llm's provider
    embedder_spec = embedder or llm_config.get("provider", "")
    emb_config = _parse_client_spec(
        embedder_spec, api_key=api_key, default_kind="embedder"
    )

    # Build clients
    llm_client = create_llm(llm_config, api_key=api_key)
    embedder_client = create_embedder(emb_config, api_key=api_key)

    return llm_client, embedder_client


def get_client(
    config_path: str | Path | None = None,
) -> tuple[BaseChatModel, Embeddings]:
    """Get OpenAI LLM client and Embedder from config.

    Backward-compatible: reads ~/.he/config.toml.

    Args:
        config_path: Config file path, default ~/.he/config.toml

    Returns:
        (llm_client, embedder) tuple

    Examples:
        >>> from hyperextract.utils import get_client
        >>> llm, emb = get_client()
        >>> # Or with custom config path
        >>> llm, emb = get_client("/path/to/config.toml")
    """
    from hyperextract.cli.config import ConfigManager

    path = Path(config_path) if config_path else DEFAULT_CONFIG_FILE
    manager = ConfigManager(path)

    llm_config = manager.get_llm_config()
    emb_config = manager.get_embedder_config()

    # Build LLM client
    llm_client = create_llm(
        {
            "provider": llm_config.provider,
            "model": llm_config.model,
            "base_url": llm_config.base_url,
            "api_key": llm_config.api_key,
        }
    )

    # Build embedder client
    embedder_client = create_embedder(
        {
            "provider": emb_config.provider,
            "model": emb_config.model,
            "base_url": emb_config.base_url,
            "api_key": emb_config.api_key,
        }
    )

    return llm_client, embedder_client
