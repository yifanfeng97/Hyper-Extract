# he feed

增量地向现有知识库添加文档。

---

## 概要

```bash
he feed KA_PATH INPUT [OPTIONS]
```

## 参数

| 参数 | 描述 |
|----------|-------------|
| `KA_PATH` | 现有知识库目录的路径 |
| `INPUT` | 输入文件、目录，或 `-` 表示标准输入 |

支持的后缀：`.txt`/`.md` 始终支持；PDF、Word、PowerPoint、Excel、HTML、CSV、JSON、XML、EPUB 等需要可选的 ingest extra——`pip install "hyperextract[ingest]"`（完整表格见 [he parse](parse.md)）。扫描版（纯图片）PDF 没有文字层——请先做 OCR。标准输入（`-`）不检查后缀。

## 选项

| 选项 | 简写 | 描述 |
|--------|-------|-------------|
| `--template` | `-t` | 覆盖模板（如果省略则使用元数据） |
| `--lang` | `-l` | 覆盖语言（如果省略则使用元数据） |
| `--source` | — | 来源标注（文档 id）——之后可通过 `he remove --document` 按文档回滚 |

---

## 描述

`feed` 命令向现有知识库添加新文档，不会丢失现有数据：

1. **加载现有知识** — 读取当前知识库状态
2. **从新文档提取** — 处理新内容
3. **智能合并** — 合并新旧数据，处理重复
4. **更新元数据** — 记录更新时间戳

这非常适合：
- 随着时间构建知识库
- 向现有文档添加更新
- 组合多个来源的信息

---

## 示例

### 基本用法

```bash
# 初始提取
he parse sushi.md -t general/biography_graph -o ./sushi_kb/ -l zh

# 添加更多内容
he feed ./sushi_kb/ more_sushi.md
```

### 喂养多个文档

```bash
he feed ./ka/ doc1.md
he feed ./ka/ doc2.md
he feed ./ka/ doc3.md
```

也可以喂入目录（与 `he parse` 一致）：每个支持的文件单独入库，来源 id 默认为文件 stem，除非指定了 `--source`。不支持的扩展名会跳过并警告；目录里没有可读文件则非 0 退出。

```bash
he feed ./ka/ ./updates/
```

或使用循环：

```bash
for file in updates/*.md; do
    he feed ./ka/ "$file"
done
```

### 从标准输入

```bash
cat new_content.md | he feed ./ka/ -
```

---

## 合并行为

合并过程处理：

| 场景 | 行为 |
|----------|----------|
| 相同实体 | 合并，描述组合 |
| 相同关系 | 使用最新信息更新 |
| 新实体 | 添加到知识库 |
| 新关系 | 添加连接现有/新实体 |

---

## 来源标注

传入 `--source` 指定文档 id，为正在喂养的文档标注来源：

```bash
he feed ./ka/ doc1.md --source doc-1
```

标注会将该文档连同输入内容的哈希值一起记入知识库的**来源台账**，从而支持：

- **变更检测** — 同一来源再次喂养且内容未变化时，命令会输出 `unchanged (content hash matches) — nothing to do` 并直接跳过：**零 LLM 调用**。使用 `--refeed` 强制重新摄取：

    ```bash
    he feed ./ka/ doc1.md --source doc-1 --refeed
    ```

- **按文档回滚** — 该文档贡献的全部知识之后可用 [`he remove --document doc-1`](remove.md) 回滚

使用 [`he info --sources`](info.md) 或 Python 的 `ka.sources()` 查看台账。完整介绍见[来源标注与溯源](../../python/guides/provenance.md)指南。

---

## 工作流程示例

### 构建研究知识库

```bash
# 第 1 天：初始论文
he parse paper_v1.md -t general/concept_graph -o ./research_kb/ -l zh
he show ./research_kb/

# 第 7 天：更新版本
he feed ./research_kb/ paper_v2.md
he show ./research_kb/

# 第 14 天：相关工作
he feed ./research_kb/ related_work.md
he build-index ./research_kb/
he talk ./research_kb/ -q "所有论文中的关键概念是什么？"
```

### 增量传记

```bash
# 从早年生活开始
he parse early_life.md -t general/biography_graph -o ./bio_kb/ -l zh

# 添加职业生涯
he feed ./bio_kb/ career.md

# 添加晚年
he feed ./bio_kb/ later_years.md

# 最终可视化
he show ./bio_kb/
```

---

## 验证

检查 feed 是否成功：

```bash
he info ./ka/
```

查看：
- 节点数增加
- 边数增加
- 时间戳更新

---

## 最佳实践

1. **使用相同模板** — Feed 应使用兼容的模板
2. **匹配语言** — 为获得最佳效果，使用一致的语言
3. **之后重建索引** — 搜索/聊天需要 `he build-index ./ka/`
4. **可视化更改** — 使用 `he show ./ka/` 查看更新

---

## 错误处理

### "不是有效的知识库目录"

目录不包含有效的知识库。检查：

```bash
ls ./ka/
# 应该包含：data.json, metadata.json
```

### "模板不匹配"

Feed 最适合使用相同类型的模板。如有需要可以覆盖：

```bash
he feed ./ka/ doc.md -t general/biography_graph
```

---

## 另请参见

- [`he parse`](parse.md) — 创建新知识库
- [`he info`](info.md) — 查看知识库统计信息
- [`he build-index`](build-index.md) — Feed 后重建搜索索引

## 另请参阅

- [`he remove --document`](remove.md) — 回滚整份来源文档
- [`he tag`](tag.md) — 为来源打标签以启用范围检索
- [管理文档的生命周期](managing-documents.md) — 完整生命周期指南
