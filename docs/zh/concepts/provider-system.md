# Provider 系统

Hyper-Extract 支持以下接入方式：**OpenAI**、**Anthropic**、**Google Gemini**、**阿里云百炼**、**DeepSeek**、**本地 vLLM**。统一使用 `create_client()` 接口，仅需修改第一行。

---

## 已验证模型兼容性

### 云端 API

| 平台 | 模型 | 函数调用 | 兼容性 | 备注 |
|------|------|:--------:|:------:|------|
| **OpenAI** | gpt-4o / gpt-4o-mini / gpt-5 | ✅ | ✅ | 官方原生支持，推荐 |
| **Anthropic** | claude-opus-4-8 / claude-sonnet-4-6 / claude-haiku-4-5 | ✅（工具调用） | ✅ | 仅 LLM——无嵌入接口（请搭配 OpenAI 兼容嵌入器）。需 `hyperextract[anthropic]` |
| **Google Gemini** | gemini-3.8-flash / gemini-2.5-flash / gemini-2.5-pro | ✅（工具调用） | ✅ | 仅 LLM——本仓库无成熟嵌入路径（请搭配 OpenAI 兼容嵌入器）。需 `hyperextract[google]`。密钥：`GOOGLE_API_KEY` 或 `GEMINI_API_KEY`。别名：`gemini` |
| **DeepSeek** | deepseek-v4-flash / deepseek-v4-pro | ✅ | ✅ | OpenAI 兼容。V4 模型默认开启"thinking"模式，Hyper-Extract 会自动关闭以保证结构化抽取可用。仅 LLM——无嵌入接口。密钥：`DEEPSEEK_API_KEY` |
| **阿里云百炼** | qwen-plus / qwen-turbo / qwen3.6-plus / deepseek-r1 | ✅ | ✅ | 直接使用，无需修改 |
| **阿里云百炼** | qwen-max / deepseek-v3 | ❌ | ❌ | 仅支持 `json_object`，不兼容 function calling 结构化输出 |

> **百炼用户注意**：qwen-max 和 deepseek-v3 仅支持 `json_object`，无法用于 Hyper-Extract 的 function calling 结构化输出。若遇到 `messages must contain the word 'json'` 错误或不返回 JSON，请切换到 qwen-plus、qwen-turbo 或 deepseek-r1。详见 [Issue #24](https://github.com/yifanfeng97/Hyper-Extract/issues/24)。

### 本地部署

| 服务 | 模型 | 量化方式 | 显存占用 | 验证状态 |
|------|------|---------|---------|---------|
| LLM | **Qwen3.5-9B** | GPTQ-Marlin 4bit | ~8GB | ✅ AutoList / AutoGraph |
| Embedding | **BAAI/bge-m3** | 无 | ~2GB | ✅ 语义搜索 |

### 云端 Embedding

| 平台 | 模型 | 维度 | 验证状态 |
|------|------|------|---------|
| **OpenAI** | text-embedding-3-small | 1536 | ✅ |
| **阿里云百炼** | text-embedding-v4 | 1024 | ✅ |

---

## 分平台快速启动

```python
from hyperextract import create_client

# OpenAI
llm, emb = create_client("openai", api_key="sk-xxx")

# 百炼
llm, emb = create_client("bailian", api_key="sk-xxx")

# Anthropic (Claude) —— 仅 LLM；Anthropic 无嵌入接口，请搭配 OpenAI 兼容嵌入器。
# 密钥：LLM 用 ANTHROPIC_API_KEY（或 CLAUDE_API_KEY），嵌入用 OPENAI_API_KEY。
llm, emb = create_client(
    llm="anthropic",  # 默认模型：claude-opus-4-8（用 "anthropic:<model>" 覆盖）
    embedder="openai:text-embedding-3-small",
)

# Google Gemini —— 原生 ChatGoogleGenerativeAI（不是 OrcaRouter 的 gemini/... 网关）。
# 仅 LLM；请搭配 OpenAI 兼容嵌入器。
# 密钥：GOOGLE_API_KEY（或 GEMINI_API_KEY）。别名："gemini"。
# 额外依赖：pip install 'hyperextract[google]'。
llm, emb = create_client(
    llm="google",  # 默认模型：gemini-3.8-flash（用 "google:<model>" 覆盖）
    embedder="openai:text-embedding-3-small",
)

# DeepSeek —— OpenAI 兼容，但无嵌入接口。V4 模型默认开启 "thinking" 模式，
# Hyper-Extract 会自动关闭以保证工具调用（function_calling）结构化抽取可用。
# 密钥：DEEPSEEK_API_KEY。用 "deepseek:deepseek-v4-pro" 覆盖模型。
llm, emb = create_client(
    llm="deepseek",
    embedder="openai:text-embedding-3-small",  # 或 vllm:bge-m3@localhost:8001/v1
)

# 本地 vLLM
llm, emb = create_client(
    llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    embedder="vllm:bge-m3@http://localhost:8001/v1",
    api_key="dummy",
)
```

完整配置选项见 [Provider 配置指南](../python/guides/provider-configuration.md)。

---

## vLLM 部署

### 启动 LLM 服务

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

### 启动 Embedding 服务

```bash
vllm serve BAAI/bge-m3 \
  --task embed \
  --dtype float16 \
  --max-model-len 8192 \
  --port 8001
```

### Docker 部署

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

## 使用建议

**本地 vLLM 部署推荐使用非 Thinking 模型。**

本地部署时，Thinking 模型（如 Qwen3.5 thinking 模式）会输出 `<think>...</think>` 标签，与约束解码要求的从首个 token 开始 JSON 合规冲突。部署 Qwen3.5-9B 时请关闭 thinking 模式：

```bash
--default-chat-template-kwargs '{"enable_thinking": false}'
```

**百炼渠道的 DeepSeek-R1 已验证可用** — 百炼平台在后端过滤了 `<think>` 标签输出，AutoGraph 和 `with_structured_output` 均可正常工作。若通过其他渠道接入 DeepSeek-R1，仍可能受 thinking 输出影响。

**量化模型推荐 GPTQ-Marlin**，AWQ 在 vLLM 0.21.0 中存在兼容性问题。

---

## 参考

- [vLLM Structured Outputs 文档](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [XGrammar 论文](https://arxiv.org/abs/2411.15100)
- [Issue #21: 国内模型支持讨论](https://github.com/yifanfeng97/Hyper-Extract/issues/21)
