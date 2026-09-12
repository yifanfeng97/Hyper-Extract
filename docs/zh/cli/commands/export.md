# he export obsidian

将知识摘要导出为 [Obsidian](https://obsidian.md) 知识库——一个由 `[[双向链接]]` 关联的 Markdown 笔记文件夹。

`export` 是一个命令组。目前支持的格式：`obsidian`、`graphml`、`jsonld`、`csv`。

---

## 用法

```bash
he export obsidian KA_PATH -o VAULT_PATH [选项]
```

## 参数

| 参数 | 说明 |
|----------|-------------|
| `KA_PATH` | 知识摘要目录路径（由 `he parse` 生成） |

## 选项

| 选项 | 别名 | 默认值 | 说明 |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(必填)* | 输出知识库目录 |
| `--name` | | 输出目录名 | 索引笔记使用的知识库名称 |
| `--no-index` | | 关闭 | 跳过生成索引 / 目录笔记 |
| `--force` | `-f` | 关闭 | 写入已存在且非空的目录 |

---

## 说明

`he export obsidian` 将提取出的知识图谱转换为一个可在 Obsidian 图谱视图中浏览的知识库：

- **每个节点 → 一篇 Markdown 笔记。** 节点字段写入 YAML front-matter，随后是 `# 标题` 以及（如有）描述。
- **每条边 → 一个 `[[双向链接]]`。** 关系渲染在源笔记的 `## Relationships` 区块中，包含关系标签与描述。
- **索引笔记**（以 `--name` 命名）按类型分组列出所有笔记，作为知识库目录。

导出器无额外依赖，生成的是纯 Markdown，因此结果是一个标准 Obsidian 知识库：在 Obsidian 中用 **"Open folder as vault"** 打开该文件夹，或之后用 [`he parse`](parse.md) 重新导入。

---

## 示例

### 基本用法

```bash
# 先提取，再导出
he parse tesla.md -t general/biography_graph -o ./tesla_kb/ -l zh
he export obsidian ./tesla_kb/ -o ./tesla_vault/
```

### 自定义知识库名称

```bash
he export obsidian ./tesla_kb/ -o ./tesla_vault/ --name "Tesla 知识库"
```

### 覆盖已存在目录

```bash
he export obsidian ./tesla_kb/ -o ./tesla_vault/ --force
```

### 不生成索引笔记

```bash
he export obsidian ./tesla_kb/ -o ./tesla_vault/ --no-index
```

---

## 输出结构

```
tesla_vault/
├── Tesla 知识库.md          # 索引（按类型分组）
├── Nikola Tesla.md
├── Alternating Current.md
└── ...
```

一篇笔记的样子：

```markdown
---
name: Nikola Tesla
type: Person
description: "Serbian-American inventor and electrical engineer"
---

# Nikola Tesla

Serbian-American inventor and electrical engineer

## Relationships

- **developed** → [[Alternating Current]] — Pioneered the AC system.
- **rivaled** → [[Thomas Edison]] — The War of the Currents.
```

说明：

- 文件名会针对 Obsidian / 文件系统做净化；原始 id/标题保留为 front-matter 的 `alias`，双向链接使用 `[[stem|display]]` 形式以确保始终可解析。
- 同名冲突会自动去重（例如 `Tesla coil (2)`）。

---

## 支持的 Auto-Type

导出支持图谱家族：

| Auto-Type | 导出 |
|-----------|--------|
| `AutoGraph` | ✓ 每个节点一篇笔记，边为双向链接 |
| `AutoHypergraph` | ✓ N 元边链接所有成员 |
| `AutoTemporalGraph` | ✓（继承自 `AutoGraph`） |
| `AutoSpatialGraph` | ✓（继承自 `AutoGraph`） |
| `AutoSpatioTemporalGraph` | ✓（继承自 `AutoGraph`） |

非图谱类型（`AutoList`、`AutoSet`、`AutoModel`）不支持；命令会给出明确的错误提示。

---

## he export graphml

将知识图谱导出为 [GraphML](http://graphml.graphdrawing.org/)——Gephi、yEd 等桌面工具可打开的 XML 图谱格式。

二元（2 端点）边写成普通的 `<edge source="…" target="…">`。**三个及以上**端点的边写成 GraphML 1.0 的 `<hyperedge>`，子元素为 `<endpoint node="…"/>`，顺序与抽取器返回顺序一致。

### 用法

```bash
he export graphml KA_PATH -o FILE.graphml
```

### 参数

| 参数 | 说明 |
|----------|-------------|
| `KA_PATH` | 知识摘要目录路径（由 `he parse` 生成） |

### 选项

| 选项 | 别名 | 默认值 | 说明 |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(必填)* | 输出 GraphML 文件 |

### 说明

- **有向二元边。** 文档使用 `graph edgedefault="directed"`。边 `B → A` 写作 `source="B"` `target="A"`；端点不会被排序。
- **N 元超边。** 3 个及以上端点的边写成 `<hyperedge>`，并按 `incident_nodes_extractor` 的返回顺序写出 `<endpoint node="…"/>`。端点不会被排序。
- **属性。** 节点 / 边 `model_dump()` 中的标量字段（`str` / `int` / `float` / `bool`）成为 GraphML `<data>` 键。嵌套值转为字符串。XML 特殊字符（`& < > " '`）会被转义。
- **悬空边。** 源或目标节点缺失的二元边（或任一端点缺失的超边）会被跳过（并记录 warning），不会导致崩溃。

支持的 Auto-Type：`AutoGraph`、`AutoHypergraph` 及其时空子类。非图谱类型（`AutoList`、`AutoSet`、`AutoModel`）不支持。

### 示例

```bash
he parse tesla.md -t general/biography_graph -o ./tesla_kb/ -l zh
he export graphml ./tesla_kb/ -o ./tesla.graphml
```

---

## he export jsonld

将知识图谱导出为 JSON-LD（标准库 `json`，不引入 RDFLib）。二元边为 `@type: Edge`，带 `source` / `target`。三个及以上端点的边为 `@type: Hyperedge`，`endpoint` 列表保持抽取器顺序（不排序）。0/1 个端点或缺失端点的边会跳过并记 warning，与 GraphML 一致。

目标文件已存在且非空时需要 `--force` / `-f`。

### 用法

```bash
he export jsonld KA_PATH -o FILE.jsonld [--force]
```

### 选项

| 选项 | 别名 | 默认值 | 说明 |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(必填)* | 输出 JSON-LD 文件 |
| `--force` | `-f` | 关闭 | 覆盖已存在的非空文件 |

### 示例

```bash
he export jsonld ./tesla_kb/ -o ./tesla.jsonld
he export jsonld ./tesla_kb/ -o ./tesla.jsonld --force
```

---

## he export csv

将节点和边导出为 CSV 表，便于电子表格以及读取边列表的图谱工具使用。

### 用法

```bash
he export csv KA_PATH -o OUT_DIR [选项]
```

### 参数

| 参数 | 说明 |
|----------|-------------|
| `KA_PATH` | 知识摘要目录路径（由 `he parse` 生成） |

### 选项

| 选项 | 别名 | 默认值 | 说明 |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(必填)* | 输出目录 |
| `--force` | `-f` | 关闭 | 写入已存在且非空的目录 |

### 说明

**二元图** 会写出：

```
OUT_DIR/
├── nodes.csv     # id + schema 标量字段
└── edges.csv     # source, target + 边标量字段
```

端点顺序被保留（`B → A` 仍是 `B,A`）。含逗号、引号或换行的字段由标准库 `csv` 模块正确加引号。

**超图** 写出 `nodes.csv` 和 `hyperedges.csv`（而不是 `edges.csv`）。`members` 列用 `|` 连接参与者 id，并按字典序**排序**以保证输出稳定。（二元 `edges.csv` 不会对端点排序。）

缺失端点的边会被跳过（并记录 warning）。非空输出目录需要 `--force`。

### 示例

```bash
he export csv ./tesla_kb/ -o ./tesla_csv/
he export csv ./tesla_kb/ -o ./tesla_csv/ --force
```

---

## Python API

Obsidian 导出是图谱 Auto-Type 上的方法；GraphML / CSV / JSON-LD 是独立纯函数（不会加到 AutoType 上）：

```python
ka.export_obsidian("./tesla_vault/", vault_name="Tesla KB", overwrite=True)

from hyperextract.utils.exporters import export_to_graphml, export_to_csv, export_to_jsonld

export_to_graphml(
    ka.nodes,
    ka.edges,
    node_id_extractor=ka.node_key_extractor,
    incident_nodes_extractor=ka.nodes_in_edge_extractor,
    file_path="./tesla.graphml",
)

export_to_csv(
    ka.nodes,
    ka.edges,
    node_id_extractor=ka.node_key_extractor,
    incident_nodes_extractor=ka.nodes_in_edge_extractor,
    folder_path="./tesla_csv/",
    overwrite=True,
)

export_to_jsonld(
    ka.nodes,
    ka.edges,
    node_id_extractor=ka.node_key_extractor,
    incident_nodes_extractor=ka.nodes_in_edge_extractor,
    file_path="./tesla.jsonld",
)
```

---

## 另请参阅

- [`he parse`](parse.md) — 提取知识（也可导入已有的知识库文件夹）
- [`he show`](show.md) — 使用 OntoSight 可视化图谱
- [`he info`](info.md) — 查看知识摘要统计
