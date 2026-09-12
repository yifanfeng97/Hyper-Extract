# he feed

Add documents to an existing knowledge abstract incrementally.

---

## Synopsis

```bash
he feed KA_PATH INPUT [OPTIONS]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `KA_PATH` | Path to existing knowledge abstract directory |
| `INPUT` | Input file, directory, or `-` for stdin |

Supported suffixes: `.txt`/`.md` always; PDF, Word, PowerPoint, Excel, HTML,
CSV, JSON, XML, EPUB and more via the optional ingest extra —
`pip install "hyperextract[ingest]"` (see [he parse](parse.md#supported-input-formats)
for the full table). Scanned (image-only) PDFs have no text layer — run OCR
first. Stdin (`-`) is not suffix-checked.

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--template` | `-t` | Override template (uses metadata if omitted) |
| `--lang` | `-l` | Override language (uses metadata if omitted) |
| `--source` | — | Source attribution (document id) — enables per-document rollback via `he remove --document` |

---

## Description

The `feed` command adds new documents to an existing knowledge abstract without losing existing data:

1. **Loads existing knowledge** — Reads current knowledge abstract state
2. **Extracts from new document** — Processes the new content
3. **Merges intelligently** — Combines new and existing data, handling duplicates
4. **Updates metadata** — Records the update timestamp

This is ideal for:
- Building knowledge abstracts over time
- Adding updates to existing documents
- Combining information from multiple sources

---

## Examples

### Basic Usage

```bash
# Initial extraction
he parse tesla_bio.md -t general/biography_graph -o ./tesla_kb/ -l en

# Add more content
he feed ./tesla_kb/ tesla_inventions.md
```

### Feed Multiple Documents

```bash
he feed ./ka/ doc1.md
he feed ./ka/ doc2.md
he feed ./ka/ doc3.md
```

Or feed a directory (same as `he parse`): each supported file is ingested, attributed by file stem unless `--source` is set. Unsupported extensions are skipped with a warning; if the directory has no readable files, the command exits non-zero.

```bash
he feed ./ka/ ./updates/
```

Or use a loop:

```bash
for file in updates/*.md; do
    he feed ./ka/ "$file"
done
```

### From Stdin

```bash
cat new_content.md | he feed ./ka/ -
```

---

## Merge Behavior

The merge process handles:

| Scenario | Behavior |
|----------|----------|
| Same entity | Merged, descriptions combined |
| Same relation | Updated with latest information |
| New entities | Added to knowledge abstract |
| New relations | Added connecting existing/new entities |

---

## Source Attribution

Pass `--source` with a document id to attribute the document you are feeding:

```bash
he feed ./ka/ doc1.md --source doc-1
```

Attribution records the document in the KA's **source ledger** together with a content hash of the input, which enables:

- **Change detection** — feeding the same source again with unchanged content prints `unchanged (content hash matches) — nothing to do` and skips entirely: **zero LLM calls**. Use `--refeed` to force re-ingestion:

    ```bash
    he feed ./ka/ doc1.md --source doc-1 --refeed
    ```

- **Per-document rollback** — everything this document contributed can later be rolled back with [`he remove --document doc-1`](remove.md)

Inspect the ledger with [`he info --sources`](info.md#source-ledger) or `ka.sources()` in Python. See the [Source Attribution & Provenance](../../python/guides/provenance.md) guide for the full picture.

---

## Workflow Example

### Building a Research Knowledge Abstract

```bash
# Day 1: Initial paper
he parse paper_v1.md -t general/concept_graph -o ./research_kb/ -l en
he show ./research_kb/

# Day 7: Updated version
he feed ./research_kb/ paper_v2.md
he show ./research_kb/

# Day 14: Related work
he feed ./research_kb/ related_work.md
he build-index ./research_kb/
he talk ./research_kb/ -q "What are the key concepts across all papers?"
```

### Incremental Biography

```bash
# Start with early life
he parse early_life.md -t general/biography_graph -o ./bio_kb/ -l en

# Add career period
he feed ./bio_kb/ career.md

# Add later years
he feed ./bio_kb/ later_years.md

# Final visualization
he show ./bio_kb/
```

---

## Verification

Check that the feed worked:

```bash
he info ./ka/
```

Look for:
- Increased node count
- Increased edge count  
- Updated timestamp

---

## Best Practices

1. **Use same template** — Feeding should use compatible templates
2. **Match language** — Use consistent language for best results
3. **Rebuild index after** — `he build-index ./ka/` for search/chat
4. **Visualize changes** — `he show ./ka/` to see updates

---

## Error Handling

### "Not a valid Knowledge Abstract directory"

The directory doesn't contain a valid knowledge abstract. Check:

```bash
ls ./ka/
# Should contain: data.json, metadata.json
```

### "Template mismatch"

Feeding works best with the same template type. Override if needed:

```bash
he feed ./ka/ doc.md -t general/biography_graph
```

---

## See Also

- [`he parse`](parse.md) — Create new knowledge abstract
- [`he info`](info.md) — View knowledge abstract statistics
- [`he build-index`](build-index.md) — Rebuild search index after feeding

## See Also

- [`he remove --document`](remove.md) — roll back a whole source document
- [`he tag`](tag.md) — tag sources for scoped search
- [Managing Documents Over Time](managing-documents.md) — the complete lifecycle guide
