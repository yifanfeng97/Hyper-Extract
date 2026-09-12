"""
Anthropic Provider Demo

Extract entities and relationships using the Anthropic Messages API.
Anthropic has no embeddings API, so pair it with an OpenAI-compatible
embedder. No real key is required to read this file.

Usage:
    ANTHROPIC_API_KEY=sk-ant-xxx OPENAI_API_KEY=sk-xxx python examples/providers/anthropic_demo.py
"""

from hyperextract import create_client, AutoGraph

# Anthropic for LLM, OpenAI for embeddings (Anthropic has no embeddings API)
llm, emb = create_client(
    llm="anthropic",  # default: claude-opus-4-8
    embedder="openai:text-embedding-3-small",
)

graph = AutoGraph(
    instruction="Extract people and their relationships",
    llm_client=llm,
    embedder=emb,
    node_key_extractor=lambda n: n.name,
    edge_key_extractor=lambda e: (e.source, e.target, e.type),
    nodes_in_edge_extractor=lambda e: (e.source, e.target),
)

text = "Zhang San founded ByteDance. Li Si serves as CEO."
graph.parse(text)

print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
for n in graph.nodes:
    print(f"  - {n.name} ({n.type})")
