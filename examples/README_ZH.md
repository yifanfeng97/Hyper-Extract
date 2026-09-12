# Hyper-Extract 示例

双语演示示例目录（英文和中文）。

## 快速开始

### Provider 配置（三选一）

```bash
cd examples

# OpenAI
python providers/openai_demo.py

# 百炼（阿里云）
python providers/bailian_demo.py

# DeepSeek
python providers/deepseek_demo.py

# 本地 vLLM
python providers/vllm_demo.py
```

### 完整 Auto-Type 演示

```bash
cd examples

# 英文
python en/autotypes/graph_demo.py

# 中文
python zh/autotypes/graph_demo.py
```

## 目录结构

```
examples/
├── README.md
├── README_ZH.md              # 本文件
├── providers/                   # Provider 配置示例
│   ├── openai_demo.py          # OpenAI 配置
│   ├── bailian_demo.py         # 百炼（阿里云）配置
│   ├── deepseek_demo.py        # DeepSeek 配置
│   └── vllm_demo.py            # 本地 vLLM 配置
├── en/                          # 英文演示
│   ├── tesla.md                # 特斯拉传记数据
│   ├── tesla_question.md       # 查询问题
│   ├── autotypes/             # 自动类型演示
│   │   ├── document_demo.py    # 原文分块
│   │   ├── graph_demo.py       # 知识图谱
│   │   ├── list_demo.py        # 列表提取
│   │   ├── set_demo.py         # 集合提取
│   │   ├── model_demo.py       # 模型提取
│   │   ├── temporal_graph_demo.py     # 时序图谱
│   │   ├── spatial_graph_demo.py      # 空间图谱
│   │   ├── spatio_temporal_graph_demo.py  # 时空图谱
│   │   └── hypergraph_demo.py  # 超图
│   ├── methods/               # RAG 方法演示
│   │   ├── atom_demo.py
│   │   ├── cog_rag_demo.py
│   │   ├── graph_rag_demo.py
│   │   ├── hyper_rag_demo.py
│   │   ├── hypergraph_rag_demo.py
│   │   ├── itext2kg_demo.py
│   │   ├── itext2kg_star_demo.py
│   │   ├── kg_gen_demo.py
│   │   └── light_rag_demo.py
│   └── templates/             # 模板演示
│       ├── finance_template.py
│       ├── general_template.py
│       ├── industry_template.py
│       ├── legal_template.py
│       ├── list_templates.py
│       ├── medicine_template.py
│       └── tcm_template.py
│
└── zh/                          # 中文演示
    ├── sushi.md               # 苏轼传记数据
    ├── sushi_question.md      # 查询问题
    ├── autotypes/             # 自动类型演示
    │   ├── document_demo.py
    │   ├── graph_demo.py
    │   ├── list_demo.py
    │   ├── set_demo.py
    │   ├── model_demo.py
    │   ├── temporal_graph_demo.py
    │   ├── spatial_graph_demo.py
    │   ├── spatio_temporal_graph_demo.py
    │   └── hypergraph_demo.py
    ├── methods/               # RAG 方法演示
    │   ├── atom_demo.py
    │   ├── cog_rag_demo.py
    │   ├── graph_rag_demo.py
    │   ├── hyper_rag_demo.py
    │   ├── hypergraph_rag_demo.py
    │   ├── itext2kg_demo.py
    │   ├── itext2kg_star_demo.py
    │   ├── kg_gen_demo.py
    │   └── light_rag_demo.py
    └── templates/             # 模板演示
        ├── finance_template.py
        ├── general_template.py
        ├── industry_template.py
        ├── legal_template.py
        ├── list_templates.py
        ├── medicine_template.py
        └── tcm_template.py
```

## 自动类型演示

每个演示展示特定的提取类型：

| 演示 | 描述 |
|------|------|
| `document_demo.py` | 存储可检索原文块（不跑 LLM 抽取） |
| `graph_demo.py` | 提取实体和关系（知识图谱） |
| `list_demo.py` | 提取项目列表 |
| `set_demo.py` | 提取去重集合 |
| `model_demo.py` | 提取结构化摘要 |
| `temporal_graph_demo.py` | 提取时间关系 |
| `spatial_graph_demo.py` | 提取空间关系 |
| `spatio_temporal_graph_demo.py` | 同时提取时间和空间 |
| `hypergraph_demo.py` | 提取多实体关系 |

## 数据文件

### Tesla (en/tesla.md)
尼古拉·特斯拉传记（1856-1943）：
- 早年生活与教育
- 与爱迪生共事
- 电流之战
- 科罗拉多斯普林斯实验
- 沃登克里夫塔

### Su Shi (zh/sushi.md)
苏轼传记（1037-1101）：
- 早年与家学
- 仕途与起伏
- 乌台诗案
- 与佛印的友谊
- 杭州岁月
- 晚年与贬谪

## 环境要求

```bash
# 安装 hyperextract（依赖项会自动安装）
uv pip install hyperextract

# 配置 API 密钥
# 选项 1：使用 .env 文件（推荐）
cp .env.example .env
# 然后用您的 OPENAI_API_KEY 和 OPENAI_BASE_URL 编辑 .env

# 选项 2：设置环境变量
export OPENAI_API_KEY=your-key
```
