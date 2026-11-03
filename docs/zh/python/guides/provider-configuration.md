# Provider 配置指南

将 Hyper-Extract 配置为使用 OpenAI、阿里云百炼或本地 vLLM 部署。

---

## 统一示例

以下三个平台运行**相同的提取任务**，仅客户端配置（前 3 行）不同。

### API Route

从 [API Route](https://www.api-route.com) 获取密钥并设置环境变量 `API_ROUTE_API_KEY`。
预设端点为 `https://global.api-route.com/v1`，默认模型为 `gpt-6.1-sol`，嵌入模型需单独配置：

```python
from hyperextract import create_client

# LLM 使用 API_ROUTE_API_KEY，嵌入模型使用 OPENAI_API_KEY。
llm, emb = create_client(
    llm="api-route",  # 可用 "api-route:<模型 ID>" 指定其他模型
    embedder="openai:text-embedding-3-small",
)
```

可用模型以[模型目录](https://www.api-route.com/pricing)或携带密钥调用
`GET https://global.api-route.com/v1/models` 的响应为准。CLI 配置示例：

```bash
he config llm -p api-route -m gpt-6.1-sol
he config embedder -p openai -m text-embedding-3-small
```

### CloudGPU

从 [CloudGPU](https://cloudgpu.app/?utm_source=hyper-extract&utm_medium=integration&utm_campaign=202611_seg04_codingagent_api) 获取密钥并设置环境变量 `CLOUDGPU_API_KEY`。
预设端点为 `https://cloudgpu.app/v1`，默认模型为 `deepseek-v4.1-flash`。
模型 id 不带厂商前缀，嵌入模型需单独配置：

```python
from hyperextract import create_client

# LLM 使用 CLOUDGPU_API_KEY，嵌入模型需单独选择提供商。
llm, emb = create_client(
    llm="cloudgpu",  # 可用 "cloudgpu:<模型 ID>" 指定其他模型
    embedder="openai",
)
```

可用模型以 [API 文档](https://cloudgpu.app/api/docs) 或携带密钥调用
`GET https://cloudgpu.app/v1/models` 的响应为准（如 `kimi-k2.6`、`glm-5.2`、`minimax-m3`）。
CLI 配置示例：

```bash
he config init -p cloudgpu -k your-cloudgpu-key
he config embedder -p openai
```

### OpenAI

```python
from hyperextract import create_client, AutoGraph

llm, emb = create_client("openai", api_key="sk-xxx")
```

### 阿里云百炼

```python
from hyperextract import create_client, AutoGraph

llm, emb = create_client("bailian", api_key="sk-xxx")
# 或换模型: create_client("bailian:qwen3.6-plus", api_key="sk-xxx")
```

### Anthropic (Claude)

```python
from hyperextract import create_client, AutoGraph

# Anthropic 仅提供 LLM——请搭配 OpenAI 兼容嵌入器。
# 密钥：LLM 使用 ANTHROPIC_API_KEY（或 CLAUDE_API_KEY），嵌入使用 OPENAI_API_KEY。
llm, emb = create_client(
    llm="anthropic",  # 默认模型：claude-opus-4-8（用 "anthropic:<model>" 覆盖）
    embedder="openai:text-embedding-3-small",
)
```

### DeepSeek

```python
from hyperextract import create_client, AutoGraph

# DeepSeek 兼容 OpenAI 协议，但无嵌入接口——请搭配 OpenAI 兼容嵌入器。
# V4 模型默认开启 "thinking" 模式，Hyper-Extract 会自动关闭以保证结构化抽取可用。
llm, emb = create_client(
    llm="deepseek",  # 默认：deepseek-v4-flash；用 "deepseek:deepseek-v4-pro" 覆盖
    embedder="openai:text-embedding-3-small",
)
```

### 本地 vLLM

```python
from hyperextract import create_client, AutoGraph

llm, emb = create_client(
    llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    embedder="vllm:bge-m3@http://localhost:8001/v1",
    api_key="dummy",
)
```

### 提取任务（三个平台共用）

```python
graph = AutoGraph(
    instruction="提取文本中的人物及其关系",
    llm_client=llm,
    embedder=emb,
    node_key_extractor=lambda n: n.name,
    edge_key_extractor=lambda e: (e.source, e.target, e.type),
    nodes_in_edge_extractor=lambda e: (e.source, e.target),
)

text = "张三创立了字节跳动，李四担任 CEO。"
graph.parse(text)
print(f"节点: {len(graph.nodes)}, 关系: {len(graph.edges)}")
```

---

## CLI 等价配置

| 平台 | 命令 |
|------|------|
| **OpenAI** | `he config init -p openai -k sk-xxx` |
| **百炼** | `he config init -p bailian -k sk-xxx` |
| **Anthropic** | `he config llm -p anthropic -k sk-ant-xxx` + `he config embedder -p openai -k sk-xxx` |
| **DeepSeek** | `he config llm -p deepseek -k sk-xxx` + `he config embedder -p openai -k sk-xxx` |
| **CloudGPU** | `he config init -p cloudgpu -k your-cloudgpu-key` + `he config embedder -p openai -k sk-xxx` |
| **vLLM** | `he config init` → 选择「本地 vLLM」 |
| **混合部署**（LLM=百炼 + Embedding=本地） | `he config llm -p bailian -k sk-xxx` + `he config embedder -p vllm -u http://localhost:8001/v1 -k dummy` |

---

## 字符串简写格式

`create_client()` 支持紧凑的字符串语法，快速配置：

| 格式 | 示例 | 结果 |
|------|------|------|
| `provider` | `"bailian"` | 使用预设的 LLM + Embedding 默认值 |
| `provider:model` | `"bailian:qwen3.6-plus"` | 覆盖 LLM 模型，保留预设 Embedding |
| `provider:model@url` | `"vllm:Qwen3.5-9B@localhost:8000/v1"` | 完整手动指定 |

---

## 使用配置文件

如果你偏好基于文件的配置，运行一次 `he config init`，然后使用 `Template.create()` 或 `get_client()`：

```python
from hyperextract import get_client, AutoGraph

llm, emb = get_client()  # 读取 ~/.he/config.toml
graph = AutoGraph(..., llm_client=llm, embedder=emb)
```

---

## 另请参阅

- [Provider 系统与本地模型支持](../../concepts/provider-system.md) — 完整兼容性表格和 vLLM 部署指南
- [CLI 配置参考](../../cli/configuration.md) — 完整的 `he config` 命令参考
