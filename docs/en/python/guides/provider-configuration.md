# Provider Configuration Guide

Configure Hyper-Extract to work with OpenAI, Bailian (Alibaba Cloud), DeepSeek, OrcaRouter, Atlas Cloud, or local vLLM deployments.

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
# Avoid glm-5.x here: it rejects the forced tool_choice that extraction uses.
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
| **Atlas Cloud** | `he config llm -p atlascloud -k xxx` + `he config embedder -p openai -k sk-xxx` |
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
