"""
OrcaRouter Provider Demo

Extract entities and relationships via the OrcaRouter OpenAI-compatible
gateway (150+ upstream models behind one key). No real key is required
to read this file; set ORCAROUTER_API_KEY before running.

Usage:
    ORCAROUTER_API_KEY=or-xxx python examples/providers/orcarouter_demo.py
"""

from hyperextract import create_client, AutoGraph

# Default model is orcarouter/auto. Override with a namespaced id such as
# llm="orcarouter:openai/gpt-4o-mini" when you want a specific upstream.
llm, emb = create_client("orcarouter")

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
