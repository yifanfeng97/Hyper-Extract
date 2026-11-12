# Provider Configuration Guide

Configure Hyper-Extract to work with OpenAI, Bailian (Alibaba Cloud), DeepSeek, OrcaRouter, Atlas Cloud, Runcrate, Cerebras, Mistral AI, Moonshot (Kimi), Cheaper Inference, CloudGPU, or local vLLM deployments. For embeddings it also supports Jina AI.

---

## Unified Example

All three platforms run the **same extraction task** below. Only the client setup (first 3 lines) changes.

### OpenAI

```python
from hyperextract import create_client, AutoGraph

llm, emb = create_client("openai", api_key="sk-xxx")
```

### Alibaba Bailian

```python
from hyperextract import create_client, AutoGraph

llm, emb = create_client("bailian", api_key="sk-xxx")
# Or override model: create_client("bailian:qwen3.6-plus", api_key="sk-xxx")
```

### Anthropic (Claude)

```python
from hyperextract import create_client, AutoGraph

# Anthropic is LLM only — pair it with an OpenAI-compatible embedder.
# Keys: ANTHROPIC_API_KEY (or CLAUDE_API_KEY) for the LLM, OPENAI_API_KEY for embeddings.
llm, emb = create_client(
    llm="anthropic",  # default model: claude-opus-4-8 (override with "anthropic:<model>")
    embedder="openai:text-embedding-3-small",
)
```

### DeepSeek

```python
from hyperextract import create_client, AutoGraph

# DeepSeek is OpenAI-compatible but has no embeddings API — pair it with an
# OpenAI-compatible embedder. The V4 models default to "thinking" mode, which
# Hyper-Extract auto-disables so structured extraction works out of the box.
llm, emb = create_client(
    llm="deepseek",  # default: deepseek-v4-flash; override with "deepseek:deepseek-v4-pro"
    embedder="openai:text-embedding-3-small",
)
```

### OrcaRouter

```python
from hyperextract import create_client, AutoGraph

# OrcaRouter is an OpenAI-compatible gateway routing 150+ models (OpenAI,
# Anthropic, Google, DeepSeek, Qwen, MiniMax, xAI) behind one endpoint and key.
# Key: ORCAROUTER_API_KEY (fallback: OPENAI_API_KEY).
llm, emb = create_client("orcarouter")
# Or override the model: create_client("orcarouter:openai/gpt-4o-mini", ...)
```

### Atlas Cloud

```python
from hyperextract import create_client, AutoGraph

# Atlas Cloud is an OpenAI-compatible gateway (DeepSeek, Z.ai, Moonshot, Qwen,
# MiniMax, OpenAI, Anthropic, Google) with vendor-prefixed model ids.
# LLM only — pair it with an OpenAI-compatible embedder.
# Key: ATLASCLOUD_API_KEY (fallback: OPENAI_API_KEY).
llm, emb = create_client(
    llm="atlascloud",
    embedder="openai:text-embedding-3-small",
)
# Or override the model: create_client(llm="atlascloud:moonshotai/kimi-k3", ...)
```

### Runcrate

```python
from hyperextract import create_client

# Runcrate is an OpenAI-compatible API for open models with vendor-prefixed ids.
# It also serves embeddings, so one key covers the LLM and the embedder.
# Key: RUNCRATE_API_KEY.
llm, emb = create_client(
    llm="runcrate",  # default model: deepseek-ai/DeepSeek-V4.1-Flash
    embedder="runcrate",  # default embedder: BAAI/bge-m3
)
# Or override the model: create_client(llm="runcrate:openai/gpt-oss-120b", ...)
```

### CloudGPU

Set `CLOUDGPU_API_KEY` to a key from [CloudGPU](https://cloudgpu.app/?utm_source=hyper-extract&utm_medium=integration&utm_campaign=202611_seg04_codingagent_api).
The preset uses `https://cloudgpu.app/v1` and defaults to `deepseek-v4.1-flash`.
Model ids have no vendor prefix. Configure an embedding provider separately:

```python
from hyperextract import create_client

# Key: CLOUDGPU_API_KEY. CloudGPU does not serve embeddings.
llm, emb = create_client(
    llm="cloudgpu",  # override with "cloudgpu:<model-id>"
    embedder="openai",
)
```

Use a model id from the [API docs](https://cloudgpu.app/api/docs) or
the authenticated `GET https://cloudgpu.app/v1/models` response
(`kimi-k2.6`, `glm-5.2`, `minimax-m3`, and others).
For CLI configuration:

```bash
he config init -p cloudgpu -k your-cloudgpu-key
he config embedder -p openai
```

### API Route

Set `API_ROUTE_API_KEY` to a key from [API Route](https://www.api-route.com).
The preset uses `https://global.api-route.com/v1` and defaults to `gpt-6.1-sol`.
Configure an embedding provider separately:

```python
from hyperextract import create_client

# Keys: API_ROUTE_API_KEY for the LLM, OPENAI_API_KEY for embeddings.
llm, emb = create_client(
    llm="api-route",  # override with "api-route:<model-id>"
    embedder="openai:text-embedding-3-small",
)
```

Use a model ID from the [model catalog](https://www.api-route.com/pricing) or
the authenticated `GET https://global.api-route.com/v1/models` response.
For CLI configuration:

```bash
he config llm -p api-route -m gpt-6.1-sol
he config embedder -p openai -m text-embedding-3-small
```

### Ollama (local)
### Cerebras

```python
from hyperextract import create_client

# Ollama serves an OpenAI-compatible subset on http://localhost:11434/v1,
# /v1/embeddings included, so one endpoint covers the LLM and the embedder.
# The local server requires an api_key field but ignores its value.
llm, emb = create_client(
    llm="ollama",  # default model: gpt-oss:20b
    embedder="ollama",  # default embedder: embeddinggemma
    api_key="ollama",
)
# Or override the model: create_client(llm="ollama:qwen3:8b", ...)
# Model tags keep their colon; serve from another host with
# "ollama:qwen3:8b@http://box.local:11434/v1".
# Cerebras exposes an OpenAI-compatible inference endpoint with bare model ids.
# It has no embeddings API, so pair it with an OpenAI-compatible embedder.
# Key: CEREBRAS_API_KEY.
llm, emb = create_client(
    llm="cerebras",  # default model: qwen-3.8-27b
    embedder="openai:text-embedding-3-small",
)
# Or override the model: create_client(llm="cerebras:gpt-oss-120b", ...)
# Some ids are dedicated-inference only; check your plan before pinning one.
```

### Mistral AI

```python
from hyperextract import create_client

# Mistral serves OpenAI-shaped /v1/chat/completions and /v1/embeddings, so one
# key covers both halves. Key: MISTRAL_API_KEY.
llm, emb = create_client(
    llm="mistral",  # default model: mistral-large-latest
    embedder="mistral",  # default embedder: mistral-embed (1024 dims)
)
# Or override the model: create_client(llm="mistral:mistral-small-latest", ...)
# The *-latest ids are rolling aliases; pin a dated id to keep results stable.
```

### Moonshot (Kimi)

```python
from hyperextract import create_client

# Moonshot exposes an OpenAI-compatible chat endpoint with bare model ids.
# It has no embeddings API, so pair it with an OpenAI-compatible embedder.
# Key: MOONSHOT_API_KEY.
llm, emb = create_client(
    llm="moonshot",  # default model: kimi-k3.1-pro
    embedder="openai:text-embedding-3-small",
)
# Or override the model: create_client(llm="moonshot:kimi-k3", ...)
```

### Jina AI (embeddings only)

```python
from hyperextract import create_client

# Jina's /v1/embeddings matches OpenAI's embeddings schema, so it drops
# straight into this repo's embedder. It serves no chat model usable for
# extraction, so the LLM comes from another provider.
# Key: JINA_API_KEY.
llm, emb = create_client(
    llm="openai:gpt-4o-mini",
    embedder="jina",  # default embedder: jina-embeddings-v5-text-small
)
# Or override the model: create_client(embedder="jina:jina-embeddings-v3", ...)
# create_llm("jina") raises: there is no chat model to fall back to.
# The v5 ids accept a Jina-specific "task" field this repo does not send,
# so Jina applies its default; jina-embeddings-v3 predates that field.
```

### Cheaper Inference

```python
from hyperextract import create_client

# Cheaper Inference is an OpenAI-compatible gateway with one key for models
# from several labs. It has no embeddings API, so pair it with another embedder.
# Key: CHEAPER_INFERENCE_API_KEY.
llm, emb = create_client(
    llm="cheaperinference",  # default model: gpt-5.4-mini
    embedder="openai:text-embedding-3-small",
)
```

### Local vLLM

```python
from hyperextract import create_client, AutoGraph

llm, emb = create_client(
    llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    embedder="vllm:bge-m3@http://localhost:8001/v1",
    api_key="dummy",
)
```

### Extraction Task (same for all)

```python
graph = AutoGraph(
    instruction="Extract people and their relationships",
    llm_client=llm,
    embedder=emb,
    node_key_extractor=lambda n: n.name,
    edge_key_extractor=lambda e: (e.source, e.target, e.type),
    nodes_in_edge_extractor=lambda e: (e.source, e.target),
)

text = "Zhang San founded ByteDance. Li Si serves as CEO."
graph.parse(text)
print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
```

---

## CLI Equivalents

| Platform | Command |
|----------|---------|
| **OpenAI** | `he config init -p openai -k sk-xxx` |
| **Bailian** | `he config init -p bailian -k sk-xxx` |
| **Anthropic** | `he config llm -p anthropic -k sk-ant-xxx` + `he config embedder -p openai -k sk-xxx` |
| **DeepSeek** | `he config llm -p deepseek -k sk-xxx` + `he config embedder -p openai -k sk-xxx` |
| **OrcaRouter** | `he config init -p orcarouter -k sk-orca-xxx` |
| **Cheaper Inference** | `he config llm -p cheaperinference -m gpt-5.4-mini -k ci_live_xxx` + `he config embedder -p openai -k sk-xxx` |
| **Atlas Cloud** | `he config llm -p atlascloud -k xxx` + `he config embedder -p openai -k sk-xxx` |
| **Runcrate** | `he config init -p runcrate -k rc_live_xxx` |
| **Ollama** | `he config init -p ollama -k ollama` (key value ignored) |
| **Cerebras** | `he config llm -p cerebras -k csk-xxx` + `he config embedder -p openai -k sk-xxx` |
| **Mistral AI** | `he config init -p mistral -k your-mistral-key` |
| **Moonshot (Kimi)** | `he config llm -p moonshot -k sk-moonshot-xxx` + `he config embedder -p openai -k sk-xxx` |
| **CloudGPU** | `he config init -p cloudgpu -k your-cloudgpu-key` + `he config embedder -p openai -k sk-xxx` |
| **Jina AI** (embedder) | `he config llm -p openai -k sk-xxx` + `he config embedder -p jina -k jina-xxx` |
| **vLLM** | `he config init` → select "local vLLM" |
| **Mixed** (LLM=Bailian, Embedder=vLLM) | `he config llm -p bailian -k sk-xxx` + `he config embedder -p vllm -u http://localhost:8001/v1 -k dummy` |

---

## String Shorthand Format

`create_client()` supports a compact string syntax for quick configuration:

| Format | Example | Result |
|--------|---------|--------|
| `provider` | `"bailian"` | Uses preset defaults for LLM + embedder |
| `provider:model` | `"bailian:qwen3.6-plus"` | Overrides LLM model, keeps preset embedder |
| `provider:model@url` | `"vllm:Qwen3.5-9B@localhost:8000/v1"` | Full manual specification |
| `provider:model` with a tag | `"ollama:qwen3:8b"` | Only the first colon splits; the tag is kept |

---

## Using Config File Instead

If you prefer file-based configuration, run `he config init` once and then use `Template.create()` or `get_client()`:

```python
from hyperextract import get_client, AutoGraph

llm, emb = get_client()  # Reads ~/.he/config.toml
graph = AutoGraph(..., llm_client=llm, embedder=emb)
```

---

## See Also

- [Provider System & Model Compatibility](../../concepts/provider-system.md) — Full compatibility table and vLLM deployment guide
- [CLI Configuration Reference](../../cli/configuration.md) — Complete `he config` command reference
