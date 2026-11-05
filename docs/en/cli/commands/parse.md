# he parse

Extract knowledge from documents and save to a knowledge abstract.

---

## Synopsis

```bash
he parse INPUT [OPTIONS]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `INPUT` | Input file, directory, or `-` for stdin |

### Supported Input Formats

Plain text is always supported; document formats require the optional
ingest backend (powered by [MarkItDown](https://github.com/microsoft/markitdown)):

```bash
pip install "hyperextract[ingest]"
```

| Format | Suffixes | Requirement |
|--------|----------|-------------|
| Plain text / Markdown | `.txt` `.md` | Always |
| PDF (text layer) | `.pdf` | ingest extra |
| Word | `.docx` | ingest extra |
| PowerPoint | `.pptx` | ingest extra |
| Excel | `.xlsx` | ingest extra |
| HTML | `.html` `.htm` | ingest extra |
| CSV / JSON / XML | `.csv` `.json` `.xml` | ingest extra |
| EPUB / ZIP | `.epub` `.zip` | ingest extra |
| Email | `.eml` `.msg` | ingest extra |

Suffix matching is case-insensitive. Scanned (image-only) PDFs have no text
layer — run OCR first. Directory mode walks nested subdirectories
recursively and reads every supported file found; other regular files are
skipped with a warning. Use `--flat` to scan the top level only. Stdin
(`-`) is not suffix-checked.

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output directory (required) |
| `--template` | `-t` | Template to use (omit for interactive selection) |
| `--method` | `-m` | Method template (e.g., `light_rag`, `graph_rag`) |
| `--lang` | `-l` | Language: `zh` or `en` (required for knowledge templates) |
| `--source` | — | Source attribution (document id) — enables per-document rollback via `he remove --document` |
| `--force` | `-f` | Force overwrite existing output |
| `--no-index` | — | Skip building search index |

---

## Examples

### Basic Usage

Extract from a single file:

```bash
he parse document.md -t general/biography_graph -o ./output/ -l en
```

Adding `--source` records the document's source attribution, which enables per-document rollback later via [`he remove --document`](remove.md).

### Interactive Template Selection

Omit `-t` to select from available templates:

```bash
he parse document.md -o ./output/ -l en

# You'll see:
# Select a template:
#   [1] general/biography_graph
#   [2] general/graph
#   [3] finance/earnings_summary
#   ...
# Enter number or search keyword: 
```

### Process a Directory

Directory mode walks nested subdirectories recursively and reads supported files in the tree (`.txt`/`.md` always; PDF/DOCX/… when `hyperextract[ingest]` is installed); other regular files are skipped with a warning. Use `--flat` for the legacy top-level-only scan.

```bash
he parse ./documents/ -t general/concept_graph -o ./output/ -l en
```

Files are combined in alphabetical order before extraction.

### Using Methods Instead of Templates

Use underlying extraction methods:

```bash
he parse document.md -m light_rag -o ./output/
```

Methods always use English prompts.

### Zero-Extraction Baseline with chunk_rag

Skip knowledge structuring entirely — chunks are embedded as-is and search
returns raw text (zero LLM extraction cost):

```bash
he parse ./documents/ -m chunk_rag -o ./corpus_kb/
he search ./corpus_kb/ "what is this corpus about?"
```

### Force Overwrite

Overwrite existing output directory:

```bash
he parse document.md -t general/biography_graph -o ./output/ -l en -f
```

### Skip Index Building

Speed up extraction if you don't need search/chat:

```bash
he parse document.md -t general/biography_graph -o ./output/ -l en --no-index
```

Build index later with `he build-index`.

### Read from Stdin

```bash
cat document.md | he parse - -t general/biography_graph -o ./output/ -l en
```

---

## Output Structure

```
./output/
├── data.json           # Extracted knowledge (entities, relations, etc.)
├── metadata.json       # Extraction metadata
│   ├── template        # Template used
│   ├── lang           # Language
│   ├── created_at     # Creation timestamp
│   └── updated_at     # Last update timestamp
└── index/             # Vector search index (if built)
```

Index files depend on the Auto-Type:

**AutoModel / AutoList** (pickle-free JSON since v0.10.1): `index/index.json`.

**Graph family / AutoSet / AutoDocument** (still OMem): `index/index.faiss` + `index/docstore.json`.

---

## Language Support

Templates support multiple languages:

```bash
# English
he parse doc.md -t general/biography_graph -l en -o ./output/

# Chinese
he parse doc.md -t general/biography_graph -l zh -o ./output/
```

Choose the language that matches your document for best results.

---

## Common Use Cases

### Research Paper

```bash
he parse paper.md -t general/concept_graph -o ./paper_kb/ -l en
```

### Biography

```bash
he parse biography.md -t general/biography_graph -o ./bio_kb/ -l en
```

### Legal Contract

```bash
he parse contract.md -t legal/contract_obligation -o ./contract_kb/ -l en
```

### Financial Report

```bash
he parse earnings.md -t finance/earnings_summary -o ./finance_kb/ -l en
```

---

## Error Handling

### "Output directory already exists"

The output directory exists and is not empty. Solutions:

1. Use `-f` to force overwrite
2. Choose a different output path
3. Remove the existing directory first

### "Template not found"

The specified template doesn't exist. Solutions:

1. List available templates: `he list template`
2. Use interactive selection (omit `-t`)
3. Check template path spelling

### "Language is required"

Knowledge templates require a language flag. Methods don't:

```bash
# Template - requires -l
he parse doc.md -t general/biography_graph -o ./out/ -l en

# Method - no -l needed
he parse doc.md -m light_rag -o ./out/
```

---

## Best Practices

1. **Choose the right template** — Match your document type
2. **Use correct language** — Improves extraction quality
3. **Organize outputs** — Use descriptive directory names
4. **Skip index during batch** — Use `--no-index`, build once at the end

---

## See Also

- [`he feed`](feed.md) — Add documents incrementally
- [`he build-index`](build-index.md) — Build search index
- [`he list`](list.md) — List available templates
- [Template Library](../../templates/index.md)
