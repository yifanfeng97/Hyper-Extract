# MCP 服务器

Hyper-Extract 提供了一个 [MCP](https://modelcontextprotocol.io) 服务器，让支持 MCP 的助手（Claude Desktop、IDE 智能体等）通过 Model Context Protocol **查询和导出你的知识摘要**。

它是**只读 + 导出**的——不会创建、修改或删除任何 KA。

---

## 安装与运行

```bash
pip install 'hyperextract[mcp]'

# 启动服务器（stdio 传输）
he-mcp
# 等价于：
python -m hyperextract.mcp_server
```

服务器从 `~/.he/config.toml` 读取 LLM/嵌入器配置——与 CLI 相同，因此请先运行 `he config init ...`（见 [配置](cli/configuration.md)）。

---

## 接入 MCP 客户端

让你的 MCP 客户端指向 `he-mcp` 命令。以 Claude Desktop 风格的配置为例：

```json
{
  "mcpServers": {
    "hyper-extract": {
      "command": "he-mcp"
    }
  }
}
```

---

## 工具

| 工具 | 说明 | 需要索引 | 需要 LLM |
|------|-------------|:-----------:|:---------:|
| `list_templates` | 列出可用的提取模板 | — | — |
| `info` | KA 统计（模板、数量、chunks、时间戳；`include_sources` 可返回来源账本） | — | — |
| `search` | KA 语义检索 | ✓ | 嵌入器 |
| `ask` | KA 上的 RAG 问答 | ✓ | ✓ |
| `export_obsidian` | 将 KA 导出为 Obsidian 知识库 | — | 嵌入器 |

所有工具都接受一个 `ka_path`（由 `he parse` 创建的目录）。`search`/`ask` 需要索引——用 [`he build-index`](cli/commands/build-index.md) 构建。

> `export_obsidian` 依赖 Obsidian 导出功能（见 [`he export obsidian`](cli/commands/export.md)）。若不可用，该工具会返回说明信息而不会报错。

---

## 示例会话

```text
list_templates()                        → [{name: "general/biography_graph", ...}, ...]
info(ka_path="./tesla_kb")              → {nodes: 48, edges: 70, index_built: true, ...}
search(ka_path="./tesla_kb",
       query="War of Currents")          → {nodes: [...], edges: [...]}
ask(ka_path="./tesla_kb",
    question="Who were Tesla's rivals?")  → "Thomas Edison ..."
export_obsidian(ka_path="./tesla_kb",
                output="./vault")          → "Exported 49 notes to ./vault"
```
