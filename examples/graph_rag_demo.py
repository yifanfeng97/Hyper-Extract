"""
Graph-RAG Demo: Entity-Relationship Extraction with Standard Binary Graphs

This demo demonstrates:
1. Extracting entities and binary relationships from a complex sci-fi story.
2. Analysis of standard graph relationships (Source -> Target).
3. Semantic Search over the constructed Knowledge Graph (Q&A).
"""

import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from hyperextract.graphs.graph_rag import Graph_RAG

# ============================================================================
# Sample Story for Extraction (Shared with AutoHypergraph Demo)
# ============================================================================

STORY = """
【银河纪元 3042年 - 赤红星云事件报告】

危机在这一周达到了顶峰。整个银河系似乎都陷入了暗流涌动的政治漩涡。

【第一阶段：秘密接触】
臭名昭著的星际海盗黑蛇驾驶着他的旗舰复仇号，在泰坦空间站秘密会见了银河联邦的背叛者议员 Valerius。
目击者称，两人在午夜时分登上了空间站的顶层禁区。据情报部门推测，这是一次肮脏的交易——
双方达成了针对皇室的同盟关系。参与此会议的还有 Valerius 手下的特务头目 Shadow，
他负责处理所有不可告人的细节。这个同盟的形成标志着大麻烦即将到来。

【第二阶段：叛变与夺权】
在这次会议的两天后，事态急剧恶化。黑蛇这种疯狂的家伙竟然在极光星区伏击了皇家护卫队。
这场突然的冲突中，皇家护卫队的队长 Leona 与副队长 Marcus 奋力抵抗，
但他们陷入了黑蛇手下的精锐战士的包围。这场激战导致队长 Leona 身受重伤。
而黑蛇的目标不是为了杀戮，而是为了夺取一件神圣的物品——传说中的虚空水晶。
这枚水晶散发着幽蓝的光芒，据说能够打开先祖之门的第一道密封。
黑蛇在战斗中成功夺取了水晶，但 Leona 在临终前用最后的力量将其重新夺回。

【第三阶段：流亡与隐藏】
Leona 被迫带着虚空水晶，从极光星区逃往荒凉的废土行星 Z-9。
在这个被遗忘的角落，她向仅有的几个信任者求救：还有副队长 Marcus 以及隐秘组织"地下抵抗军"的领导人 Cipher。
同时，议员 Valerius 非法持有了开启先祖之门的钥匙——这把钥匙本应被安全保管在皇家金库中。
他现在藏匿在浮空都市中，与黑蛇遥相呼应，计划着下一步的政变。

【第四阶段：势力重组】
银河联邦的最高委员会得知了这一系列事件，决定采取行动。
高级顾问 Artemis 被任命为特使，她与 Leona 在废土行星 Z-9 进行了秘密会晤，
讨论如何制止这场即将到来的危机。同时，地下抵抗军的 Cipher 也加入了这次会议，
三人共同制定了一个大胆的计划。

【第五阶段：最后的筹码】
虽然黑蛇未能获得虚空水晶，但他已经从 Valerius 那里获得了先祖之门钥匙的复制品。
根据情报，这个复制品目前被秘密运往到黑蛇的秘密基地——位于辐射荒漠中的要塞。
参与此次运送的还有 Shadow 和黑蛇手下的精锐战士群体。
与此同时，Leona 和 Marcus 正在准备一场反击，他们计划在虚空水晶的力量下重新夺回局势的控制权。

目前局势：
- 黑蛇：手持复制品钥匙，掌控旗舰复仇号，计划进行最终的攻击
- 议员 Valerius：躲在浮空都市中，与黑蛇保持联系
- Leona：守护虚空水晶，在废土行星 Z-9 养伤，准备反击
- 银河联邦：通过特使 Artemis 支持 Leona，正在调集力量
- 地下抵抗军：Cipher 领导，与 Leona 和 Marcus 联手，准备对抗黑蛇和 Valerius 的同盟

这场战争的走向仍不确定。虚空水晶、先祖之门、以及隐藏在这一切背后的秘密，
都将在接下来的日子里浮出水面。银河的命运，可能就在这些关键人物和物品的碰撞中决定。
"""


if __name__ == "__main__":
    # ============================================================================
    # Initialize the Graph-RAG system with LLM and Embeddings
    # ============================================================================
    print("=" * 80)
    print("Initializing Graph-RAG System...")
    print("=" * 80)

    # Use a capable model for extraction
    llm_client = ChatOpenAI(
        model="gpt-4o-mini",
        extra_body={
            "system": "You are a helpful assistant. Always respond in Chinese."
        },
        temperature=0,
    )
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    rag = Graph_RAG(
        llm_client=llm_client,
        embedder=embedder,
        verbose=True,
        chunk_size=1000,
    )

    # Feed text to the system
    # ============================================================================
    print("\nFeeding story to the system...")
    rag.feed_text(STORY)
    print("✓ Story processed successfully\n")

    # ============================================================================
    # Display Extracted Entities
    # ============================================================================
    print("=" * 80)
    print("EXTRACTED ENTITIES")
    print("=" * 80)

    for node in rag.nodes:
        print(f"\n【{node.name}】(Type: {node.type})")
        print(f"  Description: {node.description}")

    print(f"\n✓ Total entities extracted: {len(rag.nodes)}\n")

    # ============================================================================
    # Display Extracted Edges
    # ============================================================================
    print("=" * 80)
    print("EXTRACTED EDGES (Binary Relationships)")
    print("=" * 80)

    for i, edge in enumerate(rag.edges, 1):
        print(f"\n{i}. {edge.source} -> {edge.target}")
        print(f"   Description: {edge.description}")
        print(f"   Keywords: {edge.keywords}")
        print(f"   Strength: {edge.strength}/10")

    print(f"\n✓ Total edges extracted: {len(rag.edges)}\n")

    # ============================================================================
    # Statistics
    # ============================================================================
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)

    # Entity type distribution
    type_counts = {}
    for node in rag.nodes:
        type_counts[node.type] = type_counts.get(node.type, 0) + 1

    print("\nEntity Type Distribution:")
    for entity_type, count in sorted(type_counts.items()):
        print(f"  {entity_type}: {count}")

    # Average edge strength
    if rag.edges:
        avg_strength = sum(e.strength for e in rag.edges) / len(rag.edges)
        print(f"\nAverage Edge Strength: {avg_strength:.2f}/10")

    # Centrality (Out-degree + In-degree)
    print("\nEntity Centrality (Degree):")
    centrality = {}
    for edge in rag.edges:
        centrality[edge.source] = centrality.get(edge.source, 0) + 1
        centrality[edge.target] = centrality.get(edge.target, 0) + 1

    for entity, count in sorted(centrality.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        print(f"  {entity}: {count}")

    # ============================================================================
    # Build Semantic Index & Communities
    # ============================================================================
    print("\n" + "=" * 80)
    print("Building Semantic Index & Communities...")
    print("=" * 80)

    rag.build_index()
    print("✓ Semantic index built successfully")
    
    rag.build_communities()
    print("✓ Communities built successfully\n")

    # ============================================================================
    # Display Community Reports
    # ============================================================================
    print("=" * 80)
    print("COMMUNITY REPORTS")
    print("=" * 80)

    if not rag.community_reports:
        print("No community reports generated.")
    else:
        for cid, report in rag.community_reports.items():
            print(f"\n【{report.title}】 (ID: {report.id}, Rating: {report.rating}/10)")
            print(f"  Summary: {report.summary}")
            print(f"  Findings:")
            for finding in report.findings:
                print(f"   - {finding.summary}")

    # ============================================================================
    # Q&A: Semantic Search over Graph
    # ============================================================================
    print("=" * 80)
    print("Q&A: COMPARISON (Global vs Local vs Standard)")
    print("=" * 80)

    queries = [
        "虚空水晶现在在哪里?",
        "黑蛇和议员Valerius有什么阴谋?",
        "谁参与了泰坦空间站的秘密会议?",
        "Leona目前的状况如何?",
    ]

    # 1. Global Search Example
    print("\n" + "-" * 60)
    print("[1. Global Search] (Broad Understanding / Map-Reduce)")
    print("-" * 60)
    for q in queries:
        print(f"\nQuery: {q}")
        print("Response:")
        try:
            print(rag.global_search(q))
        except Exception as e:
            print(f"Error: {e}")

    # 2. Local Search Example
    print("\n" + "-" * 60)
    print("[2. Local Search] (Targeted Subgraph + Community Context)")
    print("-" * 60)
    for q in queries:
        print(f"\nQuery: {q}")
        print("Response:")
        try:
            print(rag.local_search(q))
        except Exception as e:
            print(f"Error: {e}")

    # 3. Standard Edge Search
    print("\n" + "-" * 60)
    print("[3. Standard Edge Search] (Vector similarity only)")
    print("-" * 60)
    
    for i, query in enumerate(queries, 1):
        print(f"\nQuery: {query}")
        try:
            results = rag.search_edges(query, top_k=3)

            if results:
                for j, result in enumerate(results, 1):
                    print(f"  [{j}] {result.source} -> {result.target}: {result.description[:100]}...")
            else:
                print("  No relevant edges found.")
        except Exception as e:
            print(f"  Search failed: {e}")

    # ============================================================================
    # Save Results
    # ============================================================================
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    rag.dump("temp/graph_rag_demo")
