# he list

List available templates and methods.

---

## Synopsis

```bash
he list [COMMAND]
```

## Commands

| Command | Description |
|---------|-------------|
| `template` | List knowledge templates |
| `method` | List extraction methods |

---

## he list template

Display all available knowledge templates.

```bash
he list template
```

**Output:**
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

### Filter by Type

Templates are organized by output type:

| Type | Templates |
|------|-----------|
| `document` | Chunked raw text without LLM extraction |
| `model` | Structured data extraction |
| `list` | Ordered collections |
| `set` | Deduplicated collections |
| `graph` | Entity-relationship networks |
| `hypergraph` | Multi-entity relationships |
| `temporal_graph` | Time-based relationships |
| `spatial_graph` | Location-based relationships |
| `spatio_temporal_graph` | Combined time + space |

---

## he list method

Display all available extraction methods.

```bash
he list method
```

**Output:**
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

### Method Categories

| Category | Methods | Best For |
|----------|---------|----------|
| **RAG-based** | `graph_rag`, `light_rag`, `hyper_rag` | Large documents, retrieval-enhanced |
| **Typical** | `itext2kg`, `kg_gen`, `atom` | Direct extraction, specific features |

---

## Use Cases

### Find a Template

```bash
# See all options
he list template

# Then use one
he parse doc.md -t general/biography_graph -o ./out/ -l en
```

### Choose a Method

```bash
# See available methods
he list method

# Use one instead of template
he parse doc.md -m light_rag -o ./out/
```

### Scripting

```bash
# Count available templates
he list template | wc -l

# Find templates by domain
he list template | grep finance

# Check if specific method exists
he list method | grep -q light_rag && echo "Available"
```

---

## Template vs Method

| Feature | Templates | Methods |
|---------|-----------|---------|
| **Purpose** | Domain-specific extraction | General algorithms |
| **Configuration** | Pre-configured prompts | Algorithm parameters |
| **Language** | Multi-language support | English only |
| **Use case** | Quick start, domain tasks | Research, customization |
| **Example** | `finance/earnings_summary` | `light_rag` |

---

## See Also

- [`he parse`](parse.md) — Use templates/methods
- [`he template validate`](template.md) — Check a template YAML file
- [Template Library](../../templates/index.md) — Detailed template documentation
- [Choosing Methods](../../concepts/methods.md) — Method selection guide
