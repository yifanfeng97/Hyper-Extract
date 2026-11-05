<div align="center">

<a href="https://yifanfeng97.github.io/Hyper-Extract/latest/">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo/logo-horizontal-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/logo/logo-horizontal.svg">
  <img alt="Hyper-Extract Logo" src="docs/assets/logo/logo-horizontal.svg" width="600">
</picture>
</a>

<br/>
<br/>

**Smart Knowledge Extraction CLI**

**Transform documents into structured knowledge with one command.**

[📖 English Version](./README.md) · [中文版](./README_ZH.md)

<!-- Status ribbon -->
<p align="center">
  <a href="https://trendshift.io/repositories/25420" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/25420" alt="Trendshift" width="250" height="55">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/hyperextract/">
    <img src="https://img.shields.io/pypi/v/hyperextract?style=for-the-badge&logo=pypi&logoColor=white&labelColor=1a1a2e&color=3776ab" alt="PyPI Version">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e" alt="Python Version">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-06b6d4?style=for-the-badge&labelColor=1a1a2e" alt="License">
  </a>
  <a href="https://yifanfeng97.github.io/Hyper-Extract/latest/">
    <img src="https://img.shields.io/badge/docs-online-3b82f6?style=for-the-badge&logo=readthedocs&logoColor=white&labelColor=1a1a2e" alt="Docs">
  </a>
  <a href="https://github.com/yifanfeng97/hyper-extract/stargazers">
    <img src="https://img.shields.io/github/stars/yifanfeng97/hyper-extract?style=for-the-badge&logo=github&labelColor=1a1a2e&color=facc15" alt="GitHub Stars">
  </a>
</p>

<br/>

> **"Stop reading. Start understanding."**  
> *"告别文档焦虑，让信息一目了然"*

<br/>

<img src="docs/assets/hero.jpg" alt="Hero & Workflow" width="800" style="max-width: 100%;">

<br/>
</div>

## ⚡ 30-Second Quick Start

**1. Install:**

```bash
# Install uv first (if you haven't)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Hyper-Extract CLI
uv tool install hyperextract
# or: pipx install hyperextract
```

**2. Configure your provider** (pick one):

```bash
# OpenAI (LLM + embeddings in one key)
he config init -p openai -k YOUR_OPENAI_API_KEY

# DeepSeek (LLM only — pair with an OpenAI embedder, most cost-effective)
he config llm -p deepseek -k YOUR_DEEPSEEK_API_KEY
he config embedder -p openai -k YOUR_OPENAI_API_KEY

# Local vLLM (free, on-premise)
he config llm -p vllm -u http://localhost:8000/v1 -k dummy -m Qwen/Qwen3.5-9B
he config embedder -p vllm -u http://localhost:8001/v1 -k dummy -m BAAI/bge-m3
```

<details>
<summary><b>More providers</b> — Anthropic (Claude), Google Gemini, Alibaba Bailian, OrcaRouter…</summary>
<br>

```bash
# Anthropic (Claude) — LLM only
he config llm -p anthropic -k YOUR_ANTHROPIC_API_KEY
he config embedder -p openai -k YOUR_OPENAI_API_KEY

# Google Gemini — LLM only (default: gemini-3.8-flash)
he config llm -p google -k YOUR_GOOGLE_API_KEY
he config embedder -p openai -k YOUR_OPENAI_API_KEY

# Alibaba Bailian (Qwen, LLM + embeddings in one key)
he config init -p bailian -k YOUR_BAILIAN_API_KEY
```

> OpenAI and Bailian provide both LLM and embedding models in one API. Anthropic, Google Gemini, and DeepSeek are LLM-only (pair them with an OpenAI-compatible embedder). DeepSeek is the most cost-effective option (~$0.001-0.005/page).

</details>

**3. Extract, query & visualize:**

```bash
# Extract knowledge from a document
he parse examples/en/tesla.md -t general/biography_graph -o ./output/ -l en

# Query it
he search ./output/ "What are Tesla's major achievements?"

# Visualize
he show ./output/

# Export to an Obsidian vault (Markdown notes + [[wikilinks]])
he export obsidian ./output/ -o ./vault/

# Your sources change? Feed updates under the same source — old facts roll back automatically
he feed ./output/ updated-tesla.md --source tesla.md

# Tag and scope your searches
he tag ./output/ --source tesla.md --add biography
he search ./output/ "inventions" --tag biography

# Audit: which documents contributed what?
he info ./output/ --sources
```

> **Which provider should I use?** OpenAI and Bailian provide both LLM and embedding models in one API; Anthropic and DeepSeek are LLM-only (pair with an OpenAI embedder); local vLLM is free but needs a GPU. Full guide: [Provider System](https://yifanfeng97.github.io/Hyper-Extract/latest/concepts/provider-system/).

<details>
<summary><b>🐍 Python API</b> (click to expand)</summary>
<br>

```bash
uv pip install hyperextract
```

```python
from hyperextract import Template

ka = Template.create("general/biography_graph")

with open("examples/en/tesla.md") as f:
    result = ka.parse(f.read())

result.show()
```

> 🔗 More examples: [examples/en](./examples/en/)

</details>

## ✨ Core Features

| | |
|:---|:---|
| 📄 **Rich Document Ingestion** | Feed PDF, Word, PowerPoint, Excel, HTML, EPUB and more — not just `.txt`/`.md` (`pip install "hyperextract[ingest]"`) |
| 🔷 **9 Knowledge Structures** | From raw chunk corpora and simple Lists to advanced Graphs, Hypergraphs, and Spatio-Temporal Graphs |
| 🧠 **11+ Extraction Engines** | chunk_rag (zero-cost baseline), GraphRAG, LightRAG, Hyper-RAG, KG-Gen, and more — ready to use |
| 📝 **80+ YAML Templates** | Zero-code extraction across Finance, Legal, Medical, TCM, Industry, and General domains |
| 🔄 **Incremental Evolution & Provenance** | Feed new documents anytime — every source is attributed and the index updates incrementally; audit (`he info --sources`), roll back (`he remove --document`), or upsert updated versions as your sources change |
| 📤 **Obsidian Export** | Turn any extracted graph into an Obsidian vault — Markdown notes linked by `[[wikilinks]]` |

## 🎯 What Can You Do With It?

<details>
<summary><b>📄 Researcher — Turn papers into knowledge graphs</b></summary>
<br>

Feed a 20-page academic paper, get an interactive graph of key concepts, authors, and citations.

```bash
he parse paper.pdf -t general/academic_graph -o ./paper_kb/
he show ./paper_kb/
```

</details>

<details>
<summary><b>🏦 Financial Analyst — Extract entities from earnings reports</b></summary>
<br>

Automatically identify companies, executives, financial metrics, and their relationships from unstructured reports.

```bash
he parse earnings.md -t finance/earnings_graph -o ./finance_kb/
he search ./finance_kb/ "What are the key risk factors?"
```

</details>

<details>
<summary><b>🔒 Local Deployment — Keep data on-premise with vLLM</b></summary>
<br>

Run Qwen3.5-9B + bge-m3 locally via vLLM. No data leaves your machine.

```python
from hyperextract import create_client
llm, emb = create_client(
    llm="vllm:Qwen3.5-9B@http://localhost:8000/v1",
    embedder="vllm:bge-m3@http://localhost:8001/v1",
    api_key="dummy",
)
```

</details>

<details>
<summary><b>📜 Knowledge Base Manager — Keep your KB in sync with reality</b></summary>
<br>

Documents change. Hyper-Extract tracks every source so you can update, roll back, or audit without starting over.

```bash
# Ingest with attribution — every fact is traceable to its source
he feed ./ka/ contract-v1.md --source contract-v1
he tag ./ka/ --source contract-v1 --add legal --add acme

# Document updated? Re-feed under the same source — old facts roll back automatically
he feed ./ka/ contract-v2.md --source contract-v1

# Document is obsolete? Roll back everything it contributed
he remove ./ka/ --document contract-v1

# Remove a single wrong fact (LLM-assisted, with dry-run preview)
he remove ./ka/ --edit-node Apple --fact "founded by Steve Jobs" --dry-run

# Search only within legal-tagged documents
he search ./ka/ "termination clause" --tag legal

# Audit: which documents contributed what?
he info ./ka/ --sources
```

</details>

## 🚀 Supported Platforms & Models

Hyper-Extract uses LangChain structured output with **function calling**. The model must support tool/function calling.

| Platform | Verified Models |
|----------|-----------------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-5 |
| **Anthropic** | claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5 |
| **Google Gemini** | gemini-3.8-flash |
| **DeepSeek** | deepseek-v4-flash, deepseek-v4-pro |
| **阿里云百炼** | qwen-plus, qwen-turbo, deepseek-r1 |
| **Local vLLM** | Qwen3.5-9B (GPTQ-Marlin) |

**Embedding models** (semantic search) work with any OpenAI-compatible endpoint: `text-embedding-3-small`, `text-embedding-v4` (Bailian), `bge-m3` (local vLLM).

<details>
<summary><b>Provider notes</b> — DeepSeek, Anthropic & Gemini pairing</summary>
<br>

> **DeepSeek:** V4 models default to "thinking" mode, which Hyper-Extract auto-disables so structured extraction works. Set `DEEPSEEK_API_KEY`. DeepSeek has no embeddings API:
>
> ```python
> from hyperextract import create_client
> llm, emb = create_client(llm="deepseek", embedder="openai:text-embedding-3-small")
> ```

> **Anthropic:** Claude is used for the **LLM** (set `ANTHROPIC_API_KEY`, extra: `pip install 'hyperextract[anthropic]'`). No embeddings API:
>
> ```python
> from hyperextract import create_client
> llm, emb = create_client(llm="anthropic", embedder="openai:text-embedding-3-small")
> ```

> **Google Gemini:** Gemini is used for the **LLM** (set `GOOGLE_API_KEY` or `GEMINI_API_KEY`, extra: `pip install 'hyperextract[google]'`). Default model is `gemini-3.8-flash`. No mature embedder path in this repo:
>
> ```python
> from hyperextract import create_client
> llm, emb = create_client(llm="google", embedder="openai:text-embedding-3-small")
> ```

</details>

> 📖 Full guide: [Provider System & Local Model Support](https://yifanfeng97.github.io/Hyper-Extract/latest/concepts/provider-system/)

## 📈 Why Hyper-Extract?

| Feature | GraphRAG | LightRAG | KG-Gen | ATOM | **Hyper-Extract** |
| :------ | :------: | :------: | :----: | :--: | :---------------: |
| Knowledge Graph | ✅ | ✅ | ✅ | ✅ | ✅ |
| Temporal Graph | ✅ | ❌ | ❌ | ✅ | ✅ |
| Spatial Graph | ❌ | ❌ | ❌ | ❌ | ✅ |
| Hypergraph | ❌ | ❌ | ❌ | ❌ | ✅ |
| Domain Templates | ❌ | ❌ | ❌ | ❌ | ✅ |
| Interactive CLI | ✅ | ❌ | ❌ | ❌ | ✅ |
| Multi-language | ✅ | ❌ | ❌ | ❌ | ✅ |

## 🧩 Supported Knowledge Structures

From simple to complex — pick the right structure for your data:

<img src="docs/assets/autotypes.jpg" alt="Knowledge Structures Matrix" width="750" style="max-width: 100%;">

**Example — AutoGraph visualization:**

<img src="docs/assets/en_show.jpg" alt="AutoGraph Visualization" width="750" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">

<details>
<summary><b>📋 What's under the hood? (Architecture & Templates)</b></summary>
<br>

Hyper-Extract follows a **three-layer architecture**:

- **Auto-Types** — 9 strongly-typed data structures (Model, List, Set, Graph, Hypergraph, Temporal Graph, Spatial Graph, Spatio-Temporal Graph, Document corpus)
- **Methods** — Extraction & retrieval algorithms: Chunk-RAG baseline, KG-Gen, GraphRAG, LightRAG, Hyper-RAG, Cog-RAG, and more
- **Templates** — 80+ presets across 6 domains. Zero-code setup.

<img src="docs/assets/arch.jpg" alt="Architecture" width="750" style="max-width: 100%;">

**Template example (Graph type):**

```yaml
language: en
name: Knowledge Graph
type: graph
tags: [general]
description: 'Extract entities and their relationships.'
output:
  entities:
    fields:
    - name: name
      type: str
    - name: type
      type: str
    - name: description
      type: str
  relations:
    fields:
    - name: source
      type: str
    - name: target
      type: str
    - name: type
      type: str
identifiers:
  entity_id: name
  relation_id: '{source}|{type}|{target}'
```

- [Browse all 80+ templates](./hyperextract/templates/presets/)
- [Create custom templates](./hyperextract/templates/DESIGN_GUIDE.md)

</details>

## 📰 What's New

**v0.12.0** — 📁 Nested directory support: `he parse`/`he feed` walk subdirectories recursively; same-named files stay distinct via relative-path source ids.

📰 **[Full release notes](https://yifanfeng97.github.io/Hyper-Extract/latest/news/)** · [All releases](https://github.com/yifanfeng97/hyper-extract/releases)

## 📚 Documentation & Resources

| Resource | Link |
| :------- | :--- |
| Full Documentation | [yifanfeng97.github.io/Hyper-Extract](https://yifanfeng97.github.io/Hyper-Extract/latest/) |
| CLI Guide | [Command-line interface](https://yifanfeng97.github.io/Hyper-Extract/latest/cli/) |
| Provider System | [Model compatibility & local deployment](https://yifanfeng97.github.io/Hyper-Extract/latest/concepts/provider-system/) |
| News | [Release notes & highlights](https://yifanfeng97.github.io/Hyper-Extract/latest/news/) |
| Template Gallery | [80+ presets](./hyperextract/templates/presets/) |
| Examples | [Working code](./examples/) |

## 🔌 MCP Server

Expose your knowledge abstracts to MCP-capable assistants (Claude Desktop, IDE agents) via the [Model Context Protocol](https://modelcontextprotocol.io) — read + export only.

```bash
pip install 'hyperextract[mcp]'
he-mcp        # stdio MCP server
```

Tools: `list_templates`, `info`, `search`, `ask` (RAG), `export_obsidian`, `export_graphml`, `export_csv`, `export_jsonld`, `export_cypher`. Full guide: [MCP Server docs](https://yifanfeng97.github.io/Hyper-Extract/latest/mcp/).

## 🤝 Contributing & License

Contributions are welcome! Please submit [Issues](https://github.com/yifanfeng97/hyper-extract/issues) and [PRs](https://github.com/yifanfeng97/hyper-extract/pulls).  
Licensed under **Apache-2.0**.

## 🔒 Security

This project has been security assessed by [MseeP.ai](https://mseep.ai/app/yifanfeng97-hyper-extract).

## AtomGit Mirror

AtomGit mirror - a synchronized AtomGit mirror of Agent Reach for easier access and cloning in China. Hosted on AtomGit: https://atomgit.com/yifanfeng97/Hyper-Extract
