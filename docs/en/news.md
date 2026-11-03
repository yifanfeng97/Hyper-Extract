# News

Release notes and highlights. For a complete changelog, see the [GitHub releases](https://github.com/yifanfeng97/hyper-extract/releases).

---

## v0.11.1 — Provider Presets Shipping (0.11.0 packaging correction)

- **🔌 Provider presets actually ship** — the v0.11.0 tag went out before the preset merges landed, so its release notes were ahead of its contents. v0.11.1 includes them: **API Route**, **Runcrate**, **Atlas Cloud**, **Cheaper Inference**, **Ollama**, **CloudGPU**, **llm.buzz** — plus all fixes below.

---

## v0.11.0 — Preset Regression Fix, New Providers & Diagnostics

- **🛠️ Critical fix for 0.10.5** — the load-time identifiers check validated `time_field`/`location_field` against the wrong output section, breaking `Template.create` for 7 shipped presets (`temporal_graph`, `spatial_graph`, `spatio_temporal_graph`, `biography_graph`, `event_timeline`, `case_fact_timeline`, `hospital_timeline`). Now validated against `relations.fields` per the presets and the validator's HE-T006 rule. *(#184)*
- **🔌 New provider presets** — **API Route** (`API_ROUTE_API_KEY`) and **Runcrate** (open models + embeddings on one key, `RUNCRATE_API_KEY`), both OpenAI-compatible, with EN/ZH docs and tests. *(#190, #192)*
- **🛡️ More load-time validation** — hypergraph `relation_members` in string/list form are now field-checked at `Template.create` (previously crashed at feed time with `AttributeError`). *(#185)*
- **🧭 Better diagnostics** — a graph-family template carrying naive `item_id` identifiers fails with the validator's HE-T003 guidance instead of a bare `AttributeError`. *(#191)*

---

## v0.10.5 — Load-Time Template Validation & Friendly Local-Model Errors

- **🛡️ Load-time identifiers validation** — a template whose `node_id`/`relation_id`/`relation_members` reference fields not declared in `output` now fails at `Template.create` with `relation_id references '{type}' but relations.fields does not declare 'type'`, instead of crashing at first merge with an unrelated `max()` error. *(production feedback; requires ontomem ≥ 0.6.1)*
- **🧠 Friendly local-model errors** — without a config file, `Template.create` no longer silently falls back to OpenAI defaults; the error lists the three ways forward (`he config init`, `-p vllm` local setup, explicit clients).
- **ontomem 0.6.1** — exact-rollback safety: `KeyExtractionError` on 100% key-extraction failure, aggregated `key_extraction_failed` warnings, and `remerge="mechanical"` for deterministic (LLM-free, seconds-fast) rollbacks on large shared keys. *(production feedback)*

---

## v0.10.4 — Visible Chunk Failures & Hypergraph Incremental Feed

- **🐛 Hypergraph incremental feed fixed** — feeding a second document into an existing hypergraph KA crashed with `AttributeError: 'key_extractor'` (`_update_data_state` referenced a nonexistent attribute). Now uses `node_key_extractor`/`edge_key_extractor`.
- **👁️ Chunk extraction failures are visible** — failed chunks were silently skipped with only a log line. Every `feed_text()`/`parse()` run now records them: read `ka.extraction_failures` (chunk index, stage, error). `he feed`/`he parse` print a warning when chunks were dropped.
- **⚙️ `on_error` strategy** — new constructor option: `"skip"` (default, current behavior) or `"raise"` to abort a feed on the first failing chunk. Available on all AutoTypes.

---

## v0.10.3 — Working Cypher Export

- **🐛 Cypher export fixed** — `he export cypher` output could not be imported by Neo4j/Memgraph: statements lacked `;` terminators (cypher-shell read the whole file as one query) and variables were re-declared within a single statement (`Variable 'n' already declared` from the second node on). Each node/edge/hyperedge is now its own `;`-terminated statement, and hyperedge members use positional aliases (`n0`, `n1`, …). *(#174)*
- **🧹 Consistency** — `AutoList`/`AutoModel` raise the standard `ValueError` build-index hint instead of a bare `Exception`. *(#175)*

---

## v0.10.2 — Scoped Chat, Method Guide & Persistence Fixes

- **💬 Scoped chat** — `he talk --source/--tag` (and `ka.chat`) narrow the context to attributed/tagged documents, with capability detection for non-tracked types. *(#161, #160)*
- **📖 Choosing a method** — new "baseline vs structured" guide plus a side-by-side `chunk_rag` vs `graph_rag` example on the same corpus, with cost/latency comparison. *(#162, #163 — first two steps of #117)*
- **🏗️ Internal** — `GraphIndexMixin` extracts the shared merge/index/search surface of graph & hypergraph (−168 lines). *(#145)*
- **🐛 Fixes** — temporal/spatial observation context now survives dump/load (was silently lost); MCP load failures return as tool results instead of crashing the stdio session; `he config init` no longer writes a broken same-provider embedder for LLM-only providers; `Cog_RAG.chat` forwards `source_ids`/`tags`; `he list --lang zh` keeps method templates; document templates get output-shape validation; CLI banner lists jsonld/cypher. *(#167, #169, #165, #171, #159, #173, #155)*
- **📚 Docs** — resolved leftover conflict markers in MCP docs; unsmashed JSON-LD/Cypher sections; type-aware index-layout notes; Gemini provider guide. *(#149, #151, #153, #157)*

---

## v0.10.1 — Pickle-Free Index Storage

- **🔒 Safe index format** — `AutoModel`/`AutoList` indexes are now stored as JSON (`index.json`: vectors + documents) and rebuilt in memory on load — **no pickle, no code execution**. Legacy pickle indexes (<= v0.10.0) still load with a deserialization warning; `he build-index --force` migrates them. *(#116)*

---

## v0.10.0 — More Export Formats, Gemini, and Quality Hardening

- **📤 JSON-LD & Cypher exports** — `he export jsonld` (pairwise edges + GraphML-style hyperedges) and `he export cypher` (Neo4j-compatible MERGE script; N-ary edges become Hyperedge nodes, not lossy cliques). *(#139, #141)*
- **🔌 MCP export parity** — `export_graphml`, `export_csv`, `export_jsonld`, `export_cypher` tools on `he-mcp`; MCP `list_templates` now includes methods and `info` shows chunks/timestamps/sources like the CLI. *(#106, #131, #133, #144)*
- **📄 `he feed` accepts directories** — parity with `he parse`: per-file source attribution, same skip/warning behavior. *(#135)*
- **🧠 Native Gemini support** — the previously unused `[google]` extra is now wired to `create_llm`: `pip install "hyperextract[google]"`. *(#137)*
- **🏗️ Internal** — `GraphIndexMixin` extracts the shared merge/index/search surface of graph & hypergraph (−168 lines); contract tests for every registered method; test matrix now includes Windows. *(#112, #108, #145)*
- **🛡️ Hardening** — chunk options validated at parse time (`chunk_overlap < chunk_size`); `relation_members` requires `source`/`target` roles; Windows `config.toml` ACL restricted to the current user; FAISS deserialization warning. *(#91, #92, #110, #94)*
- **🐛 Fixes** — scoped search forwarded on hypergraph; `he search` prints nodes/edges instead of raw tuples; MCP `search` no longer crashes on 3-tuples; GraphML export respects `--force`. *(#90, #144)*

---

## v0.9.1 — Scoped Search Completeness & Validator Hardening

- **🐛 Fixes** — scoped search forwarded on hypergraph (`AutoHypergraph.search` dropped `source_ids`/`tags`); AutoSet provenance wired end-to-end (recording, tags, rollback, persistence); `Graph_RAG`/`Cog_RAG` scope forwarding; friendly error for scope on non-tracked types.

---

## v0.9.0 — Rich Document Ingestion & chunk_rag Baseline

- **📄 Rich Document Ingestion** — `he parse` / `he feed` now accept PDF, Word, PowerPoint, Excel, HTML, CSV/JSON/XML, EPUB and more via the optional ingest extra (`pip install "hyperextract[ingest]"`, powered by [MarkItDown](https://github.com/microsoft/markitdown)). Non-UTF-8 text (GBK, etc.) is auto-detected; text-less (scanned) PDFs fail with a clear OCR hint instead of silently ingesting garbage.
- **🧱 `chunk_rag` Baseline Method** — a new zero-extraction method: documents are chunked and embedded as-is, and search returns raw text chunks. Zero LLM cost at ingestion, with full provenance (tags, scoped search, per-document rollback). The chunk-retrieval baseline for corpus Q&A and method benchmarking.
- **🐛 Fixes** — `he tag` crashed on every knowledge abstract (`tag_source` was never exposed on any type); `he search`/`he talk`/`he feed`/`he remove --document` crashed on method-built KAs (`method/*` templates were not resolvable from KA metadata).

---

## v0.8.1 / v0.8.2

- **🏷️ Source Tags & Scoped Search** — `he tag ./ka/ --source doc-1 --add legal`, then `he search ./ka/ "query" --tag legal` to retrieve only within tagged documents. Works for graph, hypergraph, and set KAs. *(#89, #84)*
- **🛡️ Input Validation** — `he parse` / `he feed` now reject unsupported file types with a conversion hint instead of silently ingesting garbage. *(#88)*
- **📦 Document Archive Fix** — re-feeding the same source from a differently-named file no longer accumulates stale copies. *(#89)*

---

## v0.8.0

- **🔄 Document Upsert** — re-feed an attributed document and its previous version is rolled back automatically: removed facts disappear, shared keys re-merge from surviving sources. *(#84)*
- **📁 Per-File Source Attribution** — `he parse ./docs/` attributes each file by its name automatically; roll back or audit any single file later. An explicit `--source` still overrides.
- **⏱️ Spatiotemporal Provenance** — temporal/spatial/spatio-temporal graphs fully support source attribution and rollback, with deterministic (MERGE_FIELD) replay tests.

---

## v0.5.0 – v0.7.0

- **🗑️ Two-Tier Knowledge Deletion** — hard-delete by key (`he remove --node/--edge`, orphan edges pruned) or remove a single wrong fact via LLM-assisted editing (`he remove --edit-node --fact`), with dry-run, key-invariance checks, and automatic backups. *(#84)*
- **📜 Source Attribution & Provenance** — `he feed --source` / `he parse --source` record each document's raw contributions; `he remove --document` rolls back exactly what one document contributed; `he info --sources` shows the ledger. *(#84)*
- **📈 Incremental Everything** — feed/parse/removal/edit patch the vector index in place (only affected vectors re-embedded); `he feed` skips documents whose content hash is unchanged (`--refeed` to force). *(#84)*
- **🧪 `he template validate`** — catch semantic template errors before paying for LLM calls: 9 diagnostic rules, `--json` for CI, `--all` for directories. *(#77)*
- **📊 GraphML & CSV Export** — desktop graph tools and spreadsheets; hypergraphs get a hyperedges table. *(#85)*
- **🌐 OrcaRouter Provider** — one key for 150+ models via `create_client("orcarouter")`. *(#71)*
- **🔐 Config File Permissions** — `~/.he/config.toml` saved `0600`. *(#86)*
- **🔗 Obsidian wikilink fix** — aliases no longer break on `[ ] | # ^`. *(#87)*
- **🛡️ Chunk-Level Fault Isolation** — one failed chunk no longer discards the rest of a multi-chunk extraction. *(#78)*
- **⚡ MCP Python SDK 2.x** — `he-mcp` works on mcp 1.x and 2.x. *(#72, #82)*
- **🔀 Directed-Edge Fix** — `(source, target)` order preserved; custom endpoint field names. *(#74)*
- **🔑 DeepSeek API Key Fix** — `DEEPSEEK_API_KEY` honored on the OpenAI-compatible path. *(#76)*
- **🎓 Education Templates** — `course_concept_graph` + `curriculum_structure`. *(#80)*
- **🧭 Smaller Fixes** — Graph_RAG.search 3-tuple; `he talk -i --top-k`; onboarding/docs overhaul. *(#70, #73, #57)*
