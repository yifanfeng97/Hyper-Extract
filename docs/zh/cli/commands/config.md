# he config

管理 Hyper-Extract 的 LLM 和嵌入模型配置。

---

## 概要

```bash
he config [COMMAND] [OPTIONS]
```

## 命令

| 命令 | 描述 |
|---------|-------------|
| `init` | 初始化配置（使用 provider preset 自动填充模型和地址） |
| `show` | 显示当前配置 |
| `llm` | 配置 LLM 设置 |
| `embedder` | 配置嵌入模型设置 |

---

## he config init

初始化配置。这是**懒人一键配置** —— 只要传入 `-p` 和 `-k`，就会自动使用内置 preset 默认值，无需任何交互：

- **OpenAI preset**: `gpt-4o-mini` + `text-embedding-3-small`
- **百炼 preset**: `qwen3.6-plus` + `text-embedding-v4`
- **DeepSeek preset**: `deepseek-v4-flash`（仅 LLM —— 无嵌入预设）
- **Anthropic preset**: `claude-opus-4-8`（仅 LLM —— 无嵌入预设，请搭配 OpenAI 兼容嵌入器）
- **Google Gemini preset**: `gemini-3.8-flash`（仅 LLM —— 无嵌入预设，请搭配 OpenAI 兼容嵌入器；别名 `gemini`）

```bash
he config init [OPTIONS]
```

### 选项

| 选项 | 简写 | 描述 |
|--------|-------|-------------|
| `--provider` | `-p` | 提供商 preset (`openai` / `anthropic` / `google` / `deepseek` / `bailian` / `vllm`) |
| `--api-key` | `-k` | LLM 和嵌入模型的 API 密钥 |
| `--base-url` | `-u` | 自定义 API 基础 URL（可选） |

### 示例

#### 懒人一键配置（推荐）

```bash
# OpenAI
he config init -p openai -k sk-your-api-key-here

# 百炼（阿里云）
he config init -p bailian -k sk-your-api-key-here

# DeepSeek（仅 LLM —— 请搭配 OpenAI 兼容嵌入器）
he config llm -p deepseek -k sk-your-deepseek-key
he config embedder -p openai -k sk-your-openai-key

# Anthropic（仅 LLM —— 请搭配 OpenAI 兼容嵌入器）
he config llm -p anthropic -k sk-your-anthropic-key
he config embedder -p openai -k sk-your-openai-key

# Google Gemini（仅 LLM —— 请搭配 OpenAI 兼容嵌入器）
he config llm -p google -k your-google-api-key
he config embedder -p openai -k sk-your-openai-key
```

执行后会自动保存对应 preset 的默认模型和 API 地址。

#### 使用自定义基础 URL

```bash
he config init -p openai -k sk-your-key -u https://api.openai.com/v1
```

#### 交互式初始化

```bash
he config init
# 按步骤交互式输入模型名称和 API 密钥
```

---

## he config show

显示当前配置。

```bash
he config show
```

**输出示例：**

```
┌──────────────────────────────────────────────────────────────────┐
│                Hyper-Extract Configuration                       │
├──────────┬──────────┬─────────────────────┬──────────┬───────────┤
│ Service  │ Provider │ Model               │ API Key  │ Base URL  │
├──────────┼──────────┼─────────────────────┼──────────┼───────────┤
│ LLM      │ bailian  │ qwen3.6-plus        │ sk-xx... │ dashsc... │
│ Embedder │ bailian  │ text-embedding-v4   │ sk-xx... │ dashsc... │
└──────────┴──────────┴─────────────────────┴──────────┴───────────┘
```

---

## he config llm

单独配置 LLM 设置。

```bash
he config llm [OPTIONS]
```

### 选项

| 选项 | 简写 | 描述 |
|--------|-------|-------------|
| `--provider` | `-p` | 提供商 preset（如 `openai`、`anthropic`、`google`、`deepseek`、`bailian`、`vllm`） |
| `--api-key` | `-k` | LLM API 密钥 |
| `--model` | `-m` | LLM 模型名称 |
| `--base-url` | `-u` | 自定义 API 基础 URL |
| `--show` | — | 查看当前 LLM 配置 |
| `--unset` | — | 清除 LLM 配置 |

### 示例

```bash
# 查看 LLM 配置
he config llm --show

# 修改 LLM 模型（OpenAI）
he config llm -p openai --model gpt-4o

# 修改 LLM 模型（百炼）
he config llm -p bailian --model qwen-plus

# 配置本地 vLLM
he config llm -p vllm \
  --api-key dummy \
  --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3.5-9B

# 重置 LLM 配置
he config llm --unset
```

---

## he config embedder

单独配置嵌入模型设置。

```bash
he config embedder [OPTIONS]
```

### 选项

| 选项 | 简写 | 描述 |
|--------|-------|-------------|
| `--provider` | `-p` | 提供商 preset（如 `openai`、`anthropic`、`google`、`deepseek`、`bailian`、`vllm`） |
| `--api-key` | `-k` | 嵌入模型 API 密钥 |
| `--model` | `-m` | 嵌入模型名称 |
| `--base-url` | `-u` | 自定义 API 基础 URL |
| `--show` | — | 查看当前嵌入模型配置 |
| `--unset` | — | 清除嵌入模型配置 |

### 示例

```bash
# 查看嵌入模型配置
he config embedder --show

# 使用 OpenAI 更大的嵌入模型
he config embedder -p openai --model text-embedding-3-large

# 配置本地 vLLM 嵌入
he config embedder -p vllm \
  --api-key dummy \
  --base-url http://localhost:8001/v1 \
  --model BAAI/bge-m3

# 重置嵌入模型配置
he config embedder --unset
```

---

## 配置文件

配置存储在：

- **Linux/macOS**: `~/.he/config.toml`
- **Windows**: `%USERPROFILE%\.he\config.toml`

### 配置示例

=== "百炼 (阿里云)"

    ```toml
    [llm]
    provider = "bailian"
    model = "qwen3.6-plus"
    api_key = "sk-your-api-key"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    [embedder]
    provider = "bailian"
    model = "text-embedding-v4"
    api_key = ""
    base_url = ""
    ```

=== "本地 vLLM"

    ```toml
    [llm]
    provider = "vllm"
    model = "Qwen/Qwen3.5-9B"
    api_key = "dummy"
    base_url = "http://localhost:8000/v1"

    [embedder]
    provider = "vllm"
    model = "BAAI/bge-m3"
    api_key = "dummy"
    base_url = "http://localhost:8001/v1"
    ```

## 环境变量

| 变量 | 描述 |
|----------|-------------|
| `OPENAI_API_KEY` | LLM 和嵌入模型的 API 密钥备用方案 |
| `OPENAI_BASE_URL` | 自定义 API 基础 URL 备用方案 |

**优先级（从高到低）：** 命令行参数 → 环境变量 → 配置文件 → 默认值。

---

## 故障排除

### "未找到 API 密钥"

```bash
he config init -k your-api-key
```

或：

```bash
export OPENAI_API_KEY=your-api-key
```

### "未找到配置文件"

```bash
he config init -k your-api-key
```

---

## 另请参见

- [配置参考](../configuration.md) — 详细配置选项说明
- [安装指南](../../getting-started/installation.md) — 初始安装步骤
