"""Types - Core data structures for automatic knowledge extraction.

This module exports the fundamental "AutoType" primitives of the Hyper-Extract framework.
Each AutoType is designed to extract a specific structure of knowledge from unstructured text,
handling the complexities of LLM interaction, text chunking, and result merging automatically.

# 🚀 AutoType Selection Guide (知识类型选择指南)

| Class | Structure | Core Use Case | Key Feature |
| :--- | :--- | :--- | :--- |
| **`AutoDocument`** | Text Chunks | Raw corpus retrieval | No LLM extraction; stores and searches chunks |
| **`AutoModel`** | Single Object | Document Summaries, Metadata | Merges all chunks into ONE consistent object |
| **`AutoList`** | List[Item] | Event Logs, Todo Lists | Appends items from all chunks commonly |
| **`AutoSet`** | Set[Item] | Entity Registries, Glossaries | Deduplicates items by key & merges details |
| **`AutoGraph`** | Nodes + Edges | Social Networks, Concept Maps | Enforces structural consistency (Node-Edge) |
| **`AutoHypergraph`** | Nodes + Hyperedges | Complex Events, Narratives | Edges connect 2+ nodes (N-ary relations) |
| **`AutoTemporalGraph`** | Graph + Time | Timelines, History, News | Resolves relative time ("yesterday") |
| **`AutoSpatialGraph`** | Graph + Space | Physical Spaces, 3D Mapping | Resolves relative location ("nearby") |
| **`AutoSpatioTemporalGraph`** | Graph + Time + Space | Event Networks, Travel | Resolves both time & location context |

# 📚 Detailed Scope Description

## 1. Scalar & Document Types (标量与文档型)
*   **`AutoDocument`**: Designed for **"One Document -> Retrievable Chunks"**.
    *   *Scope*: Keep the source text as chunks when you do not want LLM extraction (baseline retrieval, or a fallback when extraction quality/cost is a concern).
    *   *Logic*: `feed_text` splits text, stores chunks, and `search` returns the raw chunks. YAML `type: document`.
*   **`AutoModel`**: Designed for **"One Document -> One Object"**.
    *   *Scope*: When you need to summarize a whole file into a single structure (e.g., "Research Report" with fields for summary, author, conclusion).
    *   *Logic*: It treats every text chunk as a partial view of the *same* object and uses LLM to merge them.

## 2. Collection Types (集合型)
*   **`AutoList`**: Designed for **"Many Independent Items"**.
    *   *Scope*: Extracting simple lists where duplicates might be acceptable or order matters (e.g., extraction of all "Key Quotes" in a text).
*   **`AutoSet`**: Designed for **"Unique Entity Collection"**.
    *   *Scope*: When you need a deduplicated registry (e.g., "RPG Monster Manual").
    *   *Logic*: You define a unique key (e.g., monster name). If the same monster appears in chunk 1 and chunk 10, `AutoSet` intelligently merges their attributes.

## 3. Graph Types (图谱型)
*   **`AutoGraph`**: Standard pairwise knowledge graph.
    *   *Scope*: Modeling relationships between two entities (Source -> Target). Great for standard Knowledge Graphs.
*   **`AutoHypergraph`**: For higher-order relationships.
    *   *Scope*: When a "relationship" involves a group (e.g., "Meeting" involves A, B, and C).

## 4. Context-Aware Graphs (时空感知型)
These types inject "Observation Context" (Current Time/Location) into the LLM prompt.
*   **`AutoTemporalGraph`**: For time-sensitive extraction.
    *   *Scope*: Analyzing news or logs where "current time" matters for resolving relative dates.
*   **`AutoSpatialGraph`**: For location-sensitive extraction.
    *   *Scope*: Analyzing descriptions of physical environments relative to an observer.
*   **`AutoSpatioTemporalGraph`**: The combination of both above.
"""

import os

# Suppress Transformers warnings
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

from .base import BaseAutoType
from .document import AutoDocument, DocumentData, TextChunk
from .graph import AutoGraph
from .hypergraph import AutoHypergraph
from .list import AutoList
from .model import AutoModel
from .set import AutoSet
from .spatial_graph import AutoSpatialGraph
from .spatio_temporal_graph import AutoSpatioTemporalGraph
from .temporal_graph import AutoTemporalGraph

__all__ = [
    # Corpus type
    "AutoDocument",
    # Graph types
    "AutoGraph",
    # Hypergraph type
    "AutoHypergraph",
    # Collection types
    "AutoList",
    # Scalar types
    "AutoModel",
    "AutoSet",
    "AutoSpatialGraph",
    "AutoSpatioTemporalGraph",
    "AutoTemporalGraph",
    # Base class
    "BaseAutoType",
    # Corpus schemas
    "DocumentData",
    "TextChunk",
]
