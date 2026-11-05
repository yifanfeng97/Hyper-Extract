# he parse

从文档中提取知识并保存到知识库。

---

## 概要

```bash
he parse INPUT [OPTIONS]
```

## 参数

| 参数 | 描述 |
|----------|-------------|
| `INPUT` | 输入文件、目录或 `-` 表示标准输入 |

### 支持的输入格式

纯文本始终支持；文档格式需要可选的 ingest 后端（由 [MarkItDown](https://github.com/microsoft/markitdown) 驱动）：

```bash
pip install "hyperextract[ingest]"
```

| 格式 | 后缀 | 要求 |
|--------|----------|-------------|
| 纯文本 / Markdown | `.txt` `.md` | 始终支持 |
| PDF（文字层） | `.pdf` | ingest extra |
| Word | `.docx` | ingest extra |
| PowerPoint | `.pptx` | ingest extra |
| Excel | `.xlsx` | ingest extra |
| HTML | `.html` `.htm` | ingest extra |
| CSV / JSON / XML | `.csv` `.json` `.xml` | ingest extra |
| EPUB / ZIP | `.epub` `.zip` | ingest extra |
| 邮件 | `.eml` `.msg` | ingest extra |

后缀匹配大小写不敏感。扫描版（纯图片）PDF 没有文字层——请先做 OCR。目录模式递归遍历嵌套子目录：读取目录树下所有受支持的文件；其它常规文件会 warning 并跳过。`--flat` 可退回仅扫描顶层。标准输入（`-`）不检查后缀。

## 选项

| 选项 | 简写 | 描述 |
|--------|-------|-------------|
| `--output` | `-o` | 输出目录（必填） |
| `--template` | `-t` | 要使用的模板（省略以进行交互式选择） |
| `--method` | `-m` | 方法模板（例如 `light_rag`、`graph_rag`） |
| `--lang` | `-l` | 语言：`zh` 或 `en`（知识模板必填） |
| `--source` | — | 来源标注（文档 id）——之后可通过 `he remove --document` 按文档回滚 |
| `--force` | `-f` | 强制覆盖现有输出 |
| `--no-index` | — | 跳过构建搜索索引 |

---

## 示例

### 基本用法

从单个文件提取：

```bash
he parse document.md -t general/biography_graph -o ./output/ -l zh
```

使用 `--source` 标注来源，之后可用 [`he remove --document`](remove.md) 按文档回滚。

### 交互式模板选择

省略 `-t` 以从可用模板中选择：

```bash
he parse document.md -o ./output/ -l zh

# 您将看到：
# Select a template:
#   [1] general/biography_graph
#   [2] general/graph
#   [3] finance/earnings_summary
#   ...
# Enter number or search keyword: 
```

### 处理目录

目录模式递归遍历嵌套子目录，读取其中所有受支持的文件（`.txt`/`.md` 始终支持；安装 `hyperextract[ingest]` 后还包括 PDF/DOCX 等）；其它常规文件会 warning 并跳过。使用 `--flat` 仅扫描顶层。

逐文件来源 id 为相对遍历根目录的路径（如 `sub/overview.md`），因此不同子目录下的同名文件在溯源账本中不会冲突：

```bash
he parse ./documents/ -t general/concept_graph -o ./output/ -l zh
```

文件按字母顺序组合后进行提取。

### 使用方法而非模板

使用底层提取方法：

```bash
he parse document.md -m light_rag -o ./output/
```

方法始终使用英文提示。

### 用 chunk_rag 做零提取基线

完全跳过知识结构化——文本块直接向量化，检索返回原文（零 LLM 提取成本）：

```bash
he parse ./documents/ -m chunk_rag -o ./corpus_kb/
he search ./corpus_kb/ "这个语料库讲什么？"
```

### 强制覆盖

覆盖现有输出目录：

```bash
he parse document.md -t general/biography_graph -o ./output/ -l zh -f
```

### 跳过索引构建

如果您不需要搜索/聊天，可以加快提取速度：

```bash
he parse document.md -t general/biography_graph -o ./output/ -l zh --no-index
```

之后使用 `he build-index` 构建索引。

### 从标准输入读取

```bash
cat document.md | he parse - -t general/biography_graph -o ./output/ -l zh
```

---

## 输出结构

```
./output/
├── data.json           # 提取的知识（实体、关系等）
├── metadata.json       # 提取元数据
│   ├── template        # 使用的模板
│   ├── lang           # 语言
│   ├── created_at     # 创建时间戳
│   └── updated_at     # 最后更新时间戳
└── index/             # 向量搜索索引（如已构建）
```

索引文件取决于 Auto-Type：

**AutoModel / AutoList**（自 v0.10.1 起为无 pickle 的 JSON）：`index/index.json`。

**图谱家族 / AutoSet / AutoDocument**（仍由 OMem 落盘）：`index/index.faiss` + `index/docstore.json`。

---

## 语言支持

模板支持多种语言：

```bash
# 英文
he parse doc.md -t general/biography_graph -o ./output/ -l zh -o ./output/

# 中文
he parse doc.md -t general/biography_graph -l zh -o ./output/
```

选择与文档匹配的语言以获得最佳效果。

---

## 常见用例

### 研究论文

```bash
he parse paper.md -t general/concept_graph -o ./paper_kb/ -l zh
```

### 传记

```bash
he parse biography.md -t general/biography_graph -o ./output/ -l zh
```

### 法律合同

```bash
he parse contract.md -t legal/contract_obligation -o ./contract_kb/ -l zh
```

### 财务报告

```bash
he parse earnings.md -t finance/earnings_summary -o ./finance_kb/ -l zh
```

---

## 错误处理

### "输出目录已存在"

输出目录存在且不为空。解决方案：

1. 使用 `-f` 强制覆盖
2. 选择不同的输出路径
3. 先删除现有目录

### "模板未找到"

指定的模板不存在。解决方案：

1. 列出可用模板：`he list template`
2. 使用交互式选择（省略 `-t`）
3. 检查模板路径拼写

### "需要语言"

知识模板需要语言参数。方法不需要：

```bash
# 模板 - 需要 -l
he parse doc.md -t general/biography_graph -o ./output/ -l zh

# 方法 - 不需要 -l
he parse doc.md -m light_rag -o ./out/
```

---

## 最佳实践

1. **选择正确的模板** — 匹配您的文档类型
2. **使用正确的语言** — 提高提取质量
3. **组织输出** — 使用描述性目录名
4. **批量处理时跳过索引** — 使用 `--no-index`，最后统一构建

---

## 另请参见

- [`he feed`](feed.md) — 增量添加文档
- [`he build-index`](build-index.md) — 构建搜索索引
- [`he list`](list.md) — 列出可用模板
- [模板库](../../templates/index.md)
