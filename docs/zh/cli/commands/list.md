# he list

列出可用的模板和方法。

---

## 概要

```bash
he list [COMMAND]
```

## 命令

| 命令 | 描述 |
|---------|-------------|
| `template` | 列出知识模板 |
| `method` | 列出提取方法 |

---

## he list template

显示所有可用的知识模板。

```bash
he list template
```

**输出：**
```
Available Templates:

Path                          Type              Description
general/model            model             Basic model extraction
general/list             list              Basic list extraction
general/graph            graph             Basic graph extraction
general/biography_graph       temporal_graph    Biography graph with timeline
finance/earnings_summary      model             Financial earnings summary
finance/ownership_graph       graph             Company ownership structure
legal/contract_obligation     list              Contract obligations
medicine/drug_interaction     graph             Drug interaction network
...
```

### 按类型筛选

模板按输出类型组织：

| 类型 | 模板 |
|------|-----------|
| `document` | 分块原文，不跑 LLM 抽取 |
| `model` | 结构化数据提取 |
| `list` | 有序集合 |
| `set` | 去重集合 |
| `graph` | 实体关系网络 |
| `hypergraph` | 多实体关系 |
| `temporal_graph` | 基于时间的关系 |
| `spatial_graph` | 基于位置的关系 |
| `spatio_temporal_graph` | 时间 + 空间组合 |

---

## he list method

显示所有可用的提取方法。

```bash
he list method
```

**输出：**
```
Available Methods:

Name              Type         Description
graph_rag         graph        Graph-RAG with Community detection
light_rag         graph        Lightweight Graph-based RAG
hyper_rag         hypergraph   Hypergraph-based RAG
hypergraph_rag    hypergraph   Advanced Hypergraph RAG
cog_rag           hypergraph   Cognitive RAG
itext2kg          graph        iText2KG: Triple-based extraction
itext2kg_star     graph        Enhanced iText2KG
kg_gen            graph        Knowledge Graph Generator
atom              graph        Temporal knowledge graph
```

### 方法类别

| 类别 | 方法 | 最佳用途 |
|----------|---------|----------|
| **基于 RAG** | `graph_rag`, `light_rag`, `hyper_rag` | 大型文档、检索增强 |
| **典型方法** | `itext2kg`, `kg_gen`, `atom` | 直接提取、特定功能 |

---

## 用例

### 查找模板

```bash
# 查看所有选项
he list template

# 然后使用一个
he parse doc.md -t general/biography_graph -o ./out/ -l zh
```

### 选择方法

```bash
# 查看可用方法
he list method

# 使用一个而不是模板
he parse doc.md -m light_rag -o ./out/
```

### 脚本

```bash
# 统计可用模板数量
he list template | wc -l

# 按领域筛选模板
he list template | grep finance

# 检查特定方法是否存在
he list method | grep -q light_rag && echo "Available"
```

---

## 模板 vs 方法

| 功能 | 模板 | 方法 |
|---------|-----------|---------|
| **目的** | 特定领域提取 | 通用算法 |
| **配置** | 预配置提示 | 算法参数 |
| **语言** | 多语言支持 | 仅英文 |
| **用例** | 快速开始、领域任务 | 研究、定制 |
| **示例** | `finance/earnings_summary` | `light_rag` |

---

## 另请参见

- [`he parse`](parse.md) — 使用模板/方法
- [`he template validate`](template.md) — 校验模板 YAML 文件
- [模板库](../../templates/index.md) — 详细模板文档
- [选择方法](../../concepts/methods.md) — 方法选择指南
