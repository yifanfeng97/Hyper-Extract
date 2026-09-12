# Provider System

Hyper-Extract supports these ways to connect to LLMs: **OpenAI**, **Anthropic**, **Google Gemini**, **Alibaba Bailian**, **DeepSeek**, **OrcaRouter**, and **local vLLM**. All use the same `create_client()` interface — only the first line changes.

---

## Verified Model Compatibility

### Cloud API

| Platform | Model | Function calling | Compatible | Notes |
|----------|-------|:----------------:|:----------:|-------|
| **OpenAI** | gpt-4o / gpt-4o-mini / gpt-5 | ✅ | ✅ | Native support, recommended |
| **Anthropic** | claude-opus-4-8 / claude-sonnet-4-6 / claude-haiku-4-5 | ✅ (tool calling) | ✅ | LLM only — no embeddings API (pair with an OpenAI-compatible embedder). Needs `hyperextract[anthropic]` |
| **Google Gemini** | gemini-3.8-flash / gemini-2.5-flash / gemini-2.5-pro | ✅ (tool calling) | ✅ | LLM only — no embedder path in this repo (pair with an OpenAI-compatible embedder). Needs `hyperextract[google]`. Keys: `GOOGLE_API_KEY` or `GEMINI_API_KEY`. Alias: `gemini` |
| **DeepSeek** | deepseek-v4-flash / deepseek-v4-pro | ✅ | ✅ | OpenAI-compatible. V4 models default to "thinking" mode, which Hyper-Extract auto-disables (`extra_body`) so structured extraction works. LLM only — no embeddings API. Keys: `DEEPSEEK_API_KEY` |
| **OrcaRouter** | `orcarouter/auto`, `openai/gpt-4o-mini`, `anthropic/claude-haiku-4-5`, `deepseek/...`, `gemini/...` | ✅ | ✅ | OpenAI-compatible gateway routing 150+ models from OpenAI, Anthropic, Google, DeepSeek, Qwen, MiniMax, xAI behind one endpoint and key. Keys: `ORCAROUTER_API_KEY` |
| **Alibaba Bailian** | qwen-plus / qwen-turbo / qwen3.6-plus / deepseek-r1 | ✅ | ✅ | Works out of the box |
| **Alibaba Bailian** | qwen-max / deepseek-v3 | ❌ | ❌ | Only `json_object`; not compatible with function-calling structured output |

> **Bailian users**: qwen-max and deepseek-v3 only support `json_object` and are not compatible with Hyper-Extract's function-calling structured output. If you hit `messages must contain the word 'json'` or get non-JSON output, switch to qwen-plus, qwen-turbo, or deepseek-r1. See [Issue #24](https://github.com/yifanfeng97/Hyper-Extract/issues/24).

### Local Deployment

| Service | Model | Quantization | VRAM | Verified |
|---------|-------|-------------|------|----------|
| LLM | **Qwen3.5-9B** | GPTQ-Marlin 4bit | ~8GB | ✅ AutoList / AutoGraph |
| Embedding | **BAAI/bge-m3** | None | ~2GB | ✅ Semantic search |

### Cloud Embedding

| Platform | Model | Dimensions | Verified |
|----------|-------|------------|----------|
| **OpenAI** | text-embedding-3-small | 1536 | ✅ |
| **Alibaba Bailian** | text-embedding-v4 | 1024 | ✅ |

---

## Quick Start by Platform

```python
from hyperextract import create_client

# OpenAI
llm, emb = create_client("openai", api_key="sk-xxx")

# Bailian
llm, emb = create_client("bailian", api_key="sk-xxx")

# Anthropic (Claude) — LLM only; Anthropic has no embeddings API, so
# pair it with an OpenAI-compatible embedder.
# Keys: ANTHROPIC_API_KEY (or CLAUDE_API_KEY) for the LLM, OPENAI_API_KEY for embeddings.
llm, emb = create_client(
    llm="anthropic",  # default model: claude-opus-4-8 (override with "anthropic:<model>")
    embedder="openai:text-embedding-3-small",
)

# Google Gemini — native ChatGoogleGenerativeAI (not the OrcaRouter gemini/...
# gateway). LLM only; pair with an OpenAI-compatible embedder.
# Keys: GOOGLE_API_KEY (or GEMINI_API_KEY). Alias: "gemini".
# Extra: pip install 'hyperextract[google]'.
llm, emb = create_client(
    llm="google",  # default model: gemini-3.8-flash (override with "google:<model>")
    embedder="openai:text-embedding-3-small",
)

# DeepSeek — OpenAI-compatible, but no embeddings API. The V4 models
# default to "thinking" mode, which Hyper-Extract auto-disables so that
# tool-calling (function_calling) structured extraction works out of the box.
# Key: DEEPSEEK_API_KEY. Override model with "deepseek:deepseek-v4-pro".
llm, emb = create_client(
    llm="deepseek",
    embedder="openai:text-embedding-3-small",  # or vllm:bge-m3@localhost:8001/v1
)

# OrcaRouter — OpenAI-compatible gateway routing 150+ models (OpenAI,
# Anthropic, Google, DeepSeek, Qwen, MiniMax, xAI) behind one key. The default
# "orcarouter/auto" model routes to a suitable upstream; override with
# namespaced ids like "openai:gpt-4o-mini" or "anthropic:claude-haiku-4-5".
# Key: ORCAROUTER_API_KEY (fallback: OPENAI_API_KEY).
llm, emb = create_client("orcarouter")

# Local vLLM
llm, emb = create_client(
    llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    embedder="vllm:bge-m3@http://localhost:8001/v1",
    api_key="dummy",
)
```

Full configuration options: [Provider Configuration Guide](../python/guides/provider-configuration.md).

---

## vLLM Deployment

### Start LLM Service

```bash
vllm serve /path/to/qwen3.5-9b-gptq-marlin \
  --served-model-name Qwen/Qwen3.5-9B \
  --trust-remote-code \
  --quantization gptq_marlin \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --port 8000 \
  --api-key dummy
```

### Start Embedding Service

```bash
vllm serve BAAI/bge-m3 \
  --task embed \
  --dtype float16 \
  --max-model-len 8192 \
  --port 8001
```

### Docker

```bash
docker run --runtime nvidia --gpus all \
  --ipc=host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3.5-9B \
  --trust-remote-code
```

---

## Recommendations

**Use non-thinking models for local vLLM deployment.**

When deploying locally, thinking models (e.g. Qwen3.5 thinking mode) output `<think>...</think>` tags, which conflict with constrained decoding's requirement for JSON from the first token. Disable thinking mode when deploying Qwen3.5-9B:

```bash
--default-chat-template-kwargs '{"enable_thinking": false}'
```

**DeepSeek-R1 via Bailian is verified to work** — Bailian filters out `<think>` tags on the backend, so AutoGraph and `with_structured_output` work correctly. If accessing DeepSeek-R1 through other channels, thinking output may still cause issues.

**Prefer GPTQ-Marlin over AWQ** for quantization — AWQ has compatibility issues with vLLM 0.21.0.

---

## References

- [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [XGrammar Paper](https://arxiv.org/abs/2411.15100)
- [Issue #21: Domestic Model Support](https://github.com/yifanfeng97/Hyper-Extract/issues/21)
