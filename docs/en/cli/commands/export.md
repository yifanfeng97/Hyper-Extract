# he export obsidian

Export a knowledge abstract to an [Obsidian](https://obsidian.md) vault — a folder of Markdown notes linked by `[[wikilinks]]`.

`export` is a command group. Formats: `obsidian`, `graphml`, `cypher`, `csv`.

---

## Synopsis

```bash
he export obsidian KA_PATH -o VAULT_PATH [OPTIONS]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `KA_PATH` | Path to the knowledge abstract directory (created by `he parse`) |

## Options

| Option | Alias | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(required)* | Output vault directory |
| `--name` | | output dir name | Vault name used for the index note |
| `--no-index` | | off | Skip writing the index / map-of-content note |
| `--force` | `-f` | off | Write into an existing, non-empty directory |

---

## Description

`he export obsidian` turns an extracted knowledge graph into an Obsidian vault you can open and browse in Obsidian's interactive graph view:

- **Each node → a Markdown note.** The node's fields are stored as YAML front-matter, followed by a `# Title` heading and (when present) a description.
- **Each edge → a `[[wikilink]]`.** Relationships are rendered under the source note's `## Relationships` section, with the relationship label and description.
- **An index note** (named after `--name`) lists every note grouped by type — a map-of-content for the vault.

The exporter is dependency-free and writes plain Markdown, so the result is a normal Obsidian vault: open the folder via **"Open folder as vault"** in Obsidian, or re-ingest it later with [`he parse`](parse.md).

---

## Examples

### Basic Usage

```bash
# Extract, then export
he parse tesla.md -t general/biography_graph -o ./tesla_kb/ -l en
he export obsidian ./tesla_kb/ -o ./tesla_vault/
```

### Custom Vault Name

```bash
he export obsidian ./tesla_kb/ -o ./tesla_vault/ --name "Tesla Knowledge Base"
```

### Overwrite an Existing Directory

```bash
he export obsidian ./tesla_kb/ -o ./tesla_vault/ --force
```

### Without the Index Note

```bash
he export obsidian ./tesla_kb/ -o ./tesla_vault/ --no-index
```

---

## Output Structure

```
tesla_vault/
├── Tesla Knowledge Base.md   # index (grouped by type)
├── Nikola Tesla.md
├── Alternating Current.md
└── ...
```

A note looks like:

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

Notes:

- Filenames are sanitized for Obsidian/the filesystem; the original id/title is preserved as a front-matter `alias`, and wikilinks use a `[[stem|display]]` form so links always resolve.
- Name collisions are de-duplicated (e.g. `Tesla coil (2)`).

---

## Supported Auto-Types

Export works with the graph family:

| Auto-Type | Export |
|-----------|--------|
| `AutoGraph` | ✓ one note per node, edges as wikilinks |
| `AutoHypergraph` | ✓ N-ary edges link all members |
| `AutoTemporalGraph` | ✓ (inherits `AutoGraph`) |
| `AutoSpatialGraph` | ✓ (inherits `AutoGraph`) |
| `AutoSpatioTemporalGraph` | ✓ (inherits `AutoGraph`) |

Non-graph types (`AutoList`, `AutoSet`, `AutoModel`) are not supported; the command reports a clear error.

---

## he export graphml

Export a knowledge graph to [GraphML](http://graphml.graphdrawing.org/) — an XML graph format that Gephi, yEd, and other desktop tools can open.

Binary (2-endpoint) edges are written as ordinary `<edge source="…" target="…">` elements. Edges with **three or more** endpoints are written as GraphML 1.0 `<hyperedge>` elements with `<endpoint node="…"/>` children, in extractor order.

### Synopsis

```bash
he export graphml KA_PATH -o FILE.graphml
```

### Arguments

| Argument | Description |
|----------|-------------|
| `KA_PATH` | Path to the knowledge abstract directory (created by `he parse`) |

### Options

| Option | Alias | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(required)* | Output GraphML file |

### Description

- **Directed pairwise edges.** The document uses `graph edgedefault="directed"`. An edge `B → A` is written as `source="B"` `target="A"`; endpoints are never sorted.
- **N-ary hyperedges.** An edge with 3+ incident nodes becomes `<hyperedge>` plus `<endpoint node="…"/>` in the same order `incident_nodes_extractor` returns. Endpoints are never sorted.
- **Attributes.** Scalar fields from each node's / edge's `model_dump()` (`str` / `int` / `float` / `bool`) become GraphML `<data>` keys. Nested values are stringified. XML special characters (`& < > " '`) are escaped.
- **Dangling edges.** An edge whose source or target node is missing (or a hyperedge with any missing endpoint) is skipped (with a warning), not treated as a crash.

Supported Auto-Types: `AutoGraph`, `AutoHypergraph`, and temporal/spatial subclasses. Non-graph types (`AutoList`, `AutoSet`, `AutoModel`) are not supported.

### Examples

```bash
he parse tesla.md -t general/biography_graph -o ./tesla_kb/ -l en
he export graphml ./tesla_kb/ -o ./tesla.graphml
```

---

## he export cypher

Export a Neo4j / Memgraph-compatible Cypher MERGE script (`cypher-shell < file.cypher`). Binary edges become relationships (`:REL`, or a legal `type`/`label` ident). Edges with three or more endpoints become `(:Hyperedge)` nodes plus `(n)-[:IN]->(h)` in extractor order — never a pairwise clique. 0/1-endpoint or missing-endpoint edges are skipped with a warning.

Existing non-empty output files require `--force` / `-f`.

### Synopsis

```bash
he export cypher KA_PATH -o FILE.cypher [--force]
```

### Examples

```bash
he export cypher ./tesla_kb/ -o ./tesla.cypher
he export cypher ./tesla_kb/ -o ./tesla.cypher --force
```

---

## he export csv

Export nodes and edges as CSV tables for spreadsheets and graph tools that ingest edge lists.

### Synopsis

```bash
he export csv KA_PATH -o OUT_DIR [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `KA_PATH` | Path to the knowledge abstract directory (created by `he parse`) |

### Options

| Option | Alias | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | *(required)* | Output directory |
| `--force` | `-f` | off | Write into an existing, non-empty directory |

### Description

**Pairwise graphs** write:

```
OUT_DIR/
├── nodes.csv     # id + schema scalar fields
└── edges.csv     # source, target + edge scalar fields
```

Endpoint order is preserved (`B → A` stays `B,A`). Fields that contain commas, quotes, or newlines are quoted by the stdlib `csv` module.

**Hypergraphs** write `nodes.csv` plus `hyperedges.csv` instead of `edges.csv`. The `members` column joins participant ids with `|` and **sorts them lexicographically** so the file is deterministic. (Binary `edges.csv` does not sort endpoints.)

A missing endpoint skips that edge (with a warning). Non-empty output directories require `--force`.

### Examples

```bash
he export csv ./tesla_kb/ -o ./tesla_csv/
he export csv ./tesla_kb/ -o ./tesla_csv/ --force
```

---

## Python API

The same capability is available on graph Auto-Types for Obsidian, and as standalone functions for GraphML / CSV (they are not methods on AutoType):

```python
ka.export_obsidian("./tesla_vault/", vault_name="Tesla KB", overwrite=True)

from hyperextract.utils.exporters import export_to_graphml, export_to_csv, export_to_cypher

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

export_to_cypher(
    ka.nodes,
    ka.edges,
    node_id_extractor=ka.node_key_extractor,
    incident_nodes_extractor=ka.nodes_in_edge_extractor,
    file_path="./tesla.cypher",
)
```

---

## See Also

- [`he parse`](parse.md) — Extract knowledge (and ingest an existing vault folder)
- [`he show`](show.md) — Visualize the graph with OntoSight
- [`he info`](info.md) — View knowledge abstract statistics
