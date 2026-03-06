"""
Graph-RAG: Graph-based Retrieval-Augmented Generation
Extracts and manages entity-relationship knowledge graphs with standard binary edges.
"""

import json
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any, Set
import networkx as nx
import numpy as np
from pydantic import BaseModel, Field
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from hyperextract.graphs.base import AutoGraph, NodeListSchema, EdgeListSchema
from ontomem.merger import CustomRuleMerger

try:
    from graspologic.partition import hierarchical_leiden
    HAS_GRASPOLOGIC = True
except ImportError:
    HAS_GRASPOLOGIC = False

# ============================================================================
# Node Schema
# ============================================================================


class NodeSchema(BaseModel):
    """Represents an entity extracted from the source text."""

    name: str = Field(description="Name of the entity")
    type: str = Field(
        description="Entity type (person, organization, geo, event, role, concept, etc.)",
    )
    description: str = Field(
        description="Comprehensive description of the entity's attributes and activities",
    )


# ============================================================================
# Edge Schema
# ============================================================================


class EdgeSchema(BaseModel):
    """Represents a directed relationship between two entities."""

    source: str = Field(description="Name of the source entity")
    target: str = Field(description="Name of the target entity")
    description: str = Field(
        description="Detailed explanation of the relationship or event connection"
    )
    keywords: str = Field(
        description="Keywords summarizing the relationship (e.g., 'conflict, trade')",
    )
    strength: int = Field(
        ge=1,
        le=10,
        description="Numerical score indicating relationship strength (1-10)",
    )


# ============================================================================
# Community Report Schema
# ============================================================================

class CommunityFinding(BaseModel):
    summary: str = Field(description="Summary of the insight")
    explanation: str = Field(description="Detailed explanation of the insight")

class CommunityReport(BaseModel):
    """Represents a summary of a graph community."""
    
    title: str = Field(description="Short title for the community")
    summary: str = Field(description="Detailed executive summary of the community's structure and key entities")
    rating: float = Field(description="Impact severity rating (0-10)")
    findings: List[CommunityFinding] = Field(description="List of key findings")
    # Optional fields (filled programmatically)
    id: Optional[str] = Field(default=None, description="Community ID")
    key_entities: Optional[List[str]] = Field(default_factory=list, description="List of key entities in this community")


# ============================================================================
# Extraction Prompts
# ============================================================================

Graph_RAG_NODE_EXTRACTION_PROMPT = """
-Goal-
Identify relevant entities from the text.
Entities will serve as nodes in the knowledge graph.

### Source Text:
"""

Graph_RAG_EDGE_EXTRACTION_PROMPT = """
-Goal-
You are an expert knowledge graph extraction assistant.
Extract binary "Edges" that represent relationships between exactly TWO entities.

-Definition-
An Edge represents a specific connection (action, relation, ownership, etc.) from a Source entity to a Target entity.

-Constraints-
1. You MUST ONLY use names from the "Allowed Entities" list provided below.
2. Ensure every edge has exactly one Source and one Target.
3. Provide a clear, comprehensive description for each edge.

"""

COMMUNITY_REPORT_PROMPT = """
You are an expert analyst. 
Given the following list of entities and relationships within a specific community, generate a comprehensive report.

### Community Data:
Entities: {entities}
Relationships: {relationships}

### Output Requirements:
1. Title: A short name for the community.
2. Summary: An executive summary of the community's structure and dynamics.
3. Impact Rating: Score 0-10 based on importance/severity.
4. Key Findings: 3-5 main insights. Each finding must include a "summary" and an "explanation".

Output must strictly follow the JSON schema.
"""

GLOBAL_SEARCH_PROMPT = """
You are an intelligent assistant capable of answering questions based *solely* on the provided community summaries.

### Question: 
{query}

### Community Summaries:
{context}

### Instructions:
- Synthesize the information from the community summaries to answer the question.
- Do not use outside knowledge.
- If the answer includes multiple points, structure them clearly.
- If the context is insufficient, state that you cannot answer.

Answer:
"""

# ============================================================================
# Merge Templates for LLM.CUSTOM_RULE Strategy
# ============================================================================

Graph_RAG_NODE_MERGE_RULE = """You are an intelligent data merging assistant.
You will receive a list of objects representing the same Entity.

Your task is to merge them into a SINGLE object exactly matching the schema.

Merge strategy:
1. **name/type**: Keep the most frequent or precise value.
2. **description**: Synthesize a single, comprehensive description containing all unique details from the input descriptions. Write it in the third person. Resolve any contradictions coherently.
"""

Graph_RAG_EDGE_MERGE_RULE = """You are an intelligent data merging assistant.
You will receive a list of objects representing the same Relationship (Edge).

Your task is to merge them into a SINGLE object exactly matching the schema.

Merge strategy:
1. **source/target**: Keep them identical to the inputs.
2. **description**: Synthesize a single, comprehensive description covering the relationship dynamics from all inputs. Write it in the third person.
3. **keywords**: Combine keyword lists from all inputs, removing duplicates.
4. **strength**: Calculate the average of the input strengths (round to nearest integer).
"""

# ============================================================================
# Graph_RAG Class
# ============================================================================


class Graph_RAG(AutoGraph[NodeSchema, EdgeSchema]):
    """
    Graph-RAG: Graph-based Retrieval-Augmented Generation

    Extracts entity-relationships (binary edges) and supports advanced GraphRAG features:
    - Community Detection (Leiden/Modularity)
    - Community Reports (Summarization)
    - Global Search (Map-Reduce over summaries)
    - Local Search (Neighbor-based retrieval with community context)

    Implements the architecture of Microsoft GraphRAG / Nano-GraphRAG.
    """

    def __init__(
        self,
        llm_client: BaseChatModel,
        embedder: Embeddings,
        chunk_size: int = 2048,
        chunk_overlap: int = 256,
        max_workers: int = 10,
        verbose: bool = True,
    ):
        """
        Initialize Graph_RAG engine.

        Args:
            llm_client (BaseChatModel): LLM client for text generation.
            embedder (Embeddings): Embedding model for text embeddings.
            chunk_size (int): Size of text chunks for indexing.
            chunk_overlap (int): Overlap between text chunks for indexing.
            max_workers (int): Maximum number of workers for indexing.
            verbose (bool): Display detailed execution logs and progress information.
        """
        # 1. Define Key Extractors (critical for deduplication)
        # Node key: exact match by name
        node_key_fn = lambda x: x.name

        # Edge key: source + target tuple
        edge_key_fn = lambda x: (x.source, x.target)

        # 2. Edge consistency check: tell AutoGraph which nodes this edge connects
        nodes_in_edge_fn = lambda x: (x.source, x.target)

        # 3. Create custom Mergers with LLM.CUSTOM_RULE strategy
        # Node merger: merges entity descriptions using NODE_MERGE_RULE
        node_merger = CustomRuleMerger(
            key_extractor=node_key_fn,
            llm_client=llm_client,
            item_schema=NodeSchema,
            rule=Graph_RAG_NODE_MERGE_RULE,
        )

        # Edge merger: merges relationship descriptions using EDGE_MERGE_RULE
        edge_merger = CustomRuleMerger(
            key_extractor=edge_key_fn,
            llm_client=llm_client,
            item_schema=EdgeSchema,
            rule=Graph_RAG_EDGE_MERGE_RULE,
        )

        # 4. Call parent class initialization
        super().__init__(
            node_schema=NodeSchema,
            edge_schema=EdgeSchema,
            node_key_extractor=node_key_fn,
            edge_key_extractor=edge_key_fn,
            nodes_in_edge_extractor=nodes_in_edge_fn,
            llm_client=llm_client,
            embedder=embedder,
            # Enforce two-stage extraction (nodes first, then edges)
            extraction_mode="two_stage",
            # Inject customized prompts for extraction
            prompt_for_node_extraction=Graph_RAG_NODE_EXTRACTION_PROMPT,
            prompt_for_edge_extraction=Graph_RAG_EDGE_EXTRACTION_PROMPT,
            # Pass custom merger instances
            node_strategy_or_merger=node_merger,
            edge_strategy_or_merger=edge_merger,
            # Optimize indexing
            node_fields_for_index=["name", "type", "description"],
            edge_fields_for_index=["keywords", "description"],
            # Other parameters
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_workers=max_workers,
            verbose=verbose,
        )

        # Community Management
        self.community_reports: Dict[str, CommunityReport] = {}
        self._community_graph: Optional[nx.Graph] = None
        self._community_hierarchy: Dict[int, Dict[str, List[str]]] = {}  # level -> {community_id: [node_names]}
        self._node_to_community: Dict[str, Dict[str, Any]] = {}  # node_name -> {level: community_id}

    def _extract_nodes_batch(self, chunks: List[str]) -> List[NodeListSchema[NodeSchema]]:
        """Batch extract nodes from multiple text chunks.

        Overrides AutoGraph._extract_nodes_batch to fix LangChain warning.

        Args:
            chunks: List of text chunks.

        Returns:
            List of NodeListSchema objects with extracted nodes.
        """
        prompt_template = ChatPromptTemplate.from_template(
            f"{self.node_prompt}{{chunk_text}}"
        )
        llm_chain = prompt_template | self.llm_client.with_structured_output(
            self.node_list_schema,
            method="function_calling"
        )

        inputs = [{"chunk_text": chunk} for chunk in chunks]
        return llm_chain.batch(inputs, config={"max_concurrency": self.max_workers})

    def _extract_edges_batch(
        self, chunks: List[str], node_lists: List[NodeListSchema[NodeSchema]]
    ) -> List[EdgeListSchema[EdgeSchema]]:
        """Batch extract edges using corresponding node lists as context.

        Overrides AutoGraph._extract_edges_batch to fix LangChain warning.

        Args:
            chunks: List of text chunks.
            node_lists: List of NodeListSchema objects (one per chunk).

        Returns:
            List of EdgeListSchema objects with extracted edges.
        """
        inputs = []
        for chunk, node_list in zip(chunks, node_lists):
            nodes = node_list.items if node_list else []
            if not nodes:
                node_context = "No specific entities identified in this chunk."
            else:
                node_keys = [self.node_key_extractor(n) for n in nodes]
                node_context = "Known entities: " + ", ".join(node_keys)

            inputs.append({"chunk_text": chunk, "node_context": node_context})

        prompt_template = ChatPromptTemplate.from_template(
            f"{self.edge_prompt}{{node_context}}\\n\\n### Source Text:\\n{{chunk_text}}"
        )
        llm_chain = prompt_template | self.llm_client.with_structured_output(
            self.edge_list_schema,
            method="function_calling"
        )

        return llm_chain.batch(inputs, config={"max_concurrency": self.max_workers})

    # ============================================================================
    # Serialization (Save/Load) - LightRAG Style
    # ============================================================================

    def dump(self, folder_path: str | Path) -> None:
        """Saves graph state: internal data, community reports, and GraphML for visualization."""
        root = Path(folder_path)
        
        print("Saving Results...")
        print("=" * 80)
        
        # 1. Save standard graph data (nodes, edges, index)
        super().dump(folder_path)

        # 2. Save Community Data
        community_data = {
            "reports": {k: v.model_dump() for k, v in self.community_reports.items()},
            "hierarchy": {str(k): v for k, v in self._community_hierarchy.items()},
            "node_map": self._node_to_community
        }
        
        comm_path = root / "community_data.json"
        with open(comm_path, "w", encoding="utf-8") as f:
            json.dump(community_data, f, indent=2, ensure_ascii=False)

        # 3. Export GraphML for visualization (e.g., Gephi)
        try:
            graphml_path = root / "graph.graphml"
            G_export = nx.Graph()
            for n in self.nodes:
                G_export.add_node(n.name, label=n.name, type=n.type, description=n.description)
            for e in self.edges:
                G_export.add_edge(e.source, e.target, weight=float(e.strength), description=e.description)
            
            nx.write_graphml(G_export, graphml_path)
        except Exception as e:
            if self.verbose:
                print(f"Warning: Failed to save GraphML: {e}")
        
        print(f"✓ Results saved to {root}/")
        print("")
        print("  Saved files:")
        
        if root.exists():
            # List specific key files first if they exist to match style, then generic scan or just scan
            # A simple scan is fine
            files = [p for p in root.rglob("*") if p.is_file()]
            # Sort to keep index files together
            files.sort()
            for p in files:
                # Use forward slash for consistency in output regardless of OS
                rel_path = p.relative_to(root).as_posix()
                print(f"    - {rel_path}")
        print("")

    def load(self, folder_path: str | Path) -> None:
        """Loads graph state from directory."""
        root = Path(folder_path)
        
        # 1. Load standard graph data
        super().load(folder_path)

        # 2. Rebuild NetworkX graph
        self._community_graph = nx.Graph()
        for n in self.nodes:
            self._community_graph.add_node(n.name, **n.model_dump())
        for e in self.edges:
            self._community_graph.add_edge(e.source, e.target, weight=float(e.strength), **e.model_dump())

        # 3. Load Community Data
        comm_path = root / "community_data.json"
        if comm_path.exists():
            with open(comm_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.community_reports = {
                k: CommunityReport.model_validate(v) for k, v in data.get("reports", {}).items()
            }
            self._community_hierarchy = {
                int(k) if k.isdigit() else k: v for k, v in data.get("hierarchy", {}).items()
            }
            self._node_to_community = data.get("node_map", {})
            
            if self.verbose:
                print(f"Loaded {len(self.community_reports)} community reports.")


    # ============================================================================
    # Community Detection & Summarization
    # ============================================================================

    def build_communities(self, level: int = 0):
        """
        Detects communities in the graph and generates reports for them.
        Uses Leiden algorithm (via graspologic).
        
        Args:
            level: The hierarchical level for Leiden algorithm (default 0).
        """
        if self.empty():
            if self.verbose:
                print("Graph is empty, cannot build communities.")
            return

        if self.verbose:
            print("Building graph topology...")
        
        # Construct NetworkX graph
        G = nx.Graph()
        for node in self.nodes:
            G.add_node(node.name, **node.model_dump())
        
        for edge in self.edges:
            # Use 'weight' if available, mapped from 'strength'
            G.add_edge(edge.source, edge.target, weight=float(edge.strength), **edge.model_dump())
        
        self._community_graph = G

        if not HAS_GRASPOLOGIC:
            if self.verbose:
                print("Error: `graspologic` is not installed. Please install it to use Leiden community detection.")
            return

        # Community Detection Strategy
        communities = []
        community_algo = "Leiden"

        if self.verbose:
            print("Using Hierarchical Leiden algorithm (graspologic)...")
            
        try:
            # Create a subgraph without isolated nodes for Leiden to avoid warnings
            G_leiden = G.copy()
            isolates = list(nx.isolates(G_leiden))
            G_leiden.remove_nodes_from(isolates)
            
            if G_leiden.number_of_nodes() == 0:
                if self.verbose:
                    print("No connected nodes found. Skipping community detection.")
                return

            # Hierarchical Leiden returns a list of CommunityAssignment objects
            # Each assignment has (node, cluster, level)
            hierarchical_clusters = hierarchical_leiden(G_leiden, max_cluster_size=100)
            
            # Transform to our internal structure: level -> community_id -> [nodes]
            self._community_hierarchy = {}
            self._node_to_community = {}
            
            # Group by level first
            clusters_by_level = {}
            for assignment in hierarchical_clusters:
                lvl = assignment.level
                cluster_id = f"LEVEL_{lvl}_CID_{assignment.cluster}"
                node = assignment.node
                
                if lvl not in clusters_by_level:
                    clusters_by_level[lvl] = {}
                if cluster_id not in clusters_by_level[lvl]:
                    clusters_by_level[lvl][cluster_id] = []
                
                clusters_by_level[lvl][cluster_id].append(node)
                
                # Track node mapping
                if node not in self._node_to_community:
                    self._node_to_community[node] = {}
                self._node_to_community[node][f"level_{lvl}"] = cluster_id

            self._community_hierarchy = clusters_by_level
            
            # Select the requested level for reports
            # In graspologic, level 0 is usually the top-most (coarsest)
            if level in self._community_hierarchy:
                communities = list(self._community_hierarchy[level].values())
                community_algo = f"Leiden (Level {level})"
            elif self._community_hierarchy:
                # Fallback to the first available level if requested level doesn't exist
                fallback_lvl = next(iter(self._community_hierarchy))
                communities = list(self._community_hierarchy[fallback_lvl].values())
                community_algo = f"Leiden (Fallback Level {fallback_lvl})"

        except Exception as e:
            if self.verbose:
                print(f"Leiden algorithm failed: {e}.")
            return
        
        if self.verbose:
            print(f"Detected {len(communities)} communities using {community_algo}.")

        # Generate Reports
        if self.verbose:
            print("Generating community reports...")
        self.community_reports = {}
        
        chain = (
            ChatPromptTemplate.from_template(COMMUNITY_REPORT_PROMPT) 
            | self.llm_client.with_structured_output(CommunityReport, method="function_calling")
        )

        for i, community_nodes in enumerate(communities):
            cid = f"COMMUNITY_{i}"
            # Gather context
            subgraph_nodes = [n for n in self.nodes if n.name in community_nodes]
            # Edges where *both* source and target are in the community (strict)
            # Or edges where *at least one* is in the community (relaxed) -> tailored for coverage
            subgraph_edges = [e for e in self.edges if e.source in community_nodes and e.target in community_nodes]
            
            if not subgraph_nodes:
                continue

            # Format minimal context for LLM to save tokens
            entities_txt = "\\n".join([f"- {n.name} ({n.type}): {n.description}" for n in subgraph_nodes])
            relationships_txt = "\\n".join([f"- {e.source}->{e.target}: {e.description}" for e in subgraph_edges])
            
            try:
                report = chain.invoke({
                    "entities": entities_txt, 
                    "relationships": relationships_txt
                })
                # Post-processing
                report.id = cid
                report.key_entities = list(community_nodes)[:10] # Track top entities
                self.community_reports[cid] = report
                
                # Check mapping for manual fallback methods
                for node_name in community_nodes:
                    if node_name not in self._node_to_community:
                        self._node_to_community[node_name] = {}
                    self._node_to_community[node_name]["manual"] = cid

            except Exception as e:
                if self.verbose:
                    print(f"Failed to generate report for community {cid}: {e}")

        if self.verbose:
            print(f"Successfully generated {len(self.community_reports)} community reports.")

    # ============================================================================
    # Global Search
    # ============================================================================

    def global_search(self, query: str) -> str:
        """
        Global Search: Answering questions by synthesizing community summaries.
        Best for: "What are the main themes?", "How does X affect Y generally?".
        """
        if not self.community_reports:
            print("No community reports found. Building communities first...")
            self.build_communities()

        # Gather all community summaries
        # For a production system, you would start with a "Map" phase (rate communities by relevance)
        # Here we do a simple aggregation (suitable for small-medium graphs)
        
        context_parts = []
        for r in self.community_reports.values():
            context_parts.append(f"## Community: {r.title} (Rating: {r.rating})\\nSummary: {r.summary}\\n")
        
        full_context = "\\n".join(context_parts)
        
        prompt = ChatPromptTemplate.from_template(GLOBAL_SEARCH_PROMPT)
        chain = prompt | self.llm_client | StrOutputParser()
        
        if self.verbose:
            print("Executing Global Search...")
        
        response = chain.invoke({"query": query, "context": full_context})
        return response

    # ============================================================================
    # Local Search
    # ============================================================================

    def local_search(self, query: str, hops: int = 1) -> str:
        """
        Local Search: Focuses on specific entities mentioned in the query.
        Best for: "What did X do?", "Who is related to Y?".
        
        Using: Entity Vector Search -> Graph Traversal (BFS) -> Context window ingestion including Community Summaries.
        """
        # 1. Identify entities in query (Using Vector Search on Nodes)
        self.build_index() # Ensure index exists
        relevant_nodes = self.search_nodes(query, top_k=5)
        
        if not relevant_nodes:
            return "No relevant entities found in the graph for this query."
        
        start_node_names = {n.name for n in relevant_nodes}
        visited_nodes = set()
        
        # 2. Traverse Graph (Manual BFS for 'hops')
        if not self._community_graph:
            G = nx.Graph()
            for node in self.nodes:
                G.add_node(node.name)
            for edge in self.edges:
                G.add_edge(edge.source, edge.target)
            self._community_graph = G
        else:
            G = self._community_graph
            
        current_layer = start_node_names
        
        for _ in range(hops):
            next_layer = set()
            for node_name in current_layer:
                if node_name in G:
                    neighbors = list(G.neighbors(node_name))
                    next_layer.update(neighbors)
            
            visited_nodes.update(current_layer)
            current_layer = next_layer

        # 3. Retrieve detailed context for visited nodes and their edges
        final_context_edges = [
            e for e in self.edges 
            if e.source in visited_nodes or e.target in visited_nodes
        ]
        
        # Limit to reasonable context size
        final_context_edges = final_context_edges[:50] 
        edges_txt = "\\n".join([f"- {e.source}->{e.target}: {e.description}" for e in final_context_edges])

        # 4. (Enhanced) Retrieve Community Context for key nodes
        community_context = []
        seen_community_ids: Set[str] = set()

        # Try to find which communities the start_node_names belong to
        if self.community_reports:
            # Method A: Use exact node-to-community mapping if available from build_communities
            for node_name in start_node_names:
                if node_name in self._node_to_community:
                    mapping = self._node_to_community[node_name]
                    # We might have multiple levels, pick any or all
                    for cid in mapping.values():
                        if cid in self.community_reports and cid not in seen_community_ids:
                            report = self.community_reports[cid]
                            community_context.append(f"Community: {report.title}\\nSummary: {report.summary}")
                            seen_community_ids.add(cid)
            
            # Method B: Fallback if mapping missed (or inconsistent), check key_entities presence
            for report in self.community_reports.values():
                if report.id not in seen_community_ids and report.key_entities:
                    if set(report.key_entities) & start_node_names:
                        community_context.append(f"Community: {report.title}\\nSummary: {report.summary}")
                        seen_community_ids.add(report.id)

        community_txt = "\\n\\n".join(community_context) if community_context else "No specific community context available."

        # Generate Answer
        prompt_content = f"""
        Answer the query based on the local graph context provided.
        Query: {query}
        
        ### Community Context (High-level themes):
        {community_txt}

        ### Direct Relationships (Fact-based details):
        {edges_txt}
        
        Answer:
        """
        
        return self.llm_client.invoke(prompt_content).content
