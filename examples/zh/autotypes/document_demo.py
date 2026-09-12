"""
AutoDocument 示例 - 苏轼语料分块

加载 Gallery 预设 `general/base_document`，将原文切成可检索块。
AutoDocument 不跑 LLM 抽取；LLM 客户端仅用于可选的分块问答。

使用方法：
    python examples/zh/autotypes/document_demo.py
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from hyperextract.utils.template_engine import Template

project_root = Path(__file__).resolve().parent.parent.parent.parent

load_dotenv()

INPUT_FILE = project_root / "examples" / "zh" / "sushi.md"
QUESTION_FILE = project_root / "examples" / "zh" / "sushi_question.md"


if __name__ == "__main__":
    with open(INPUT_FILE, encoding="utf-8") as f:
        text = f.read()
    with open(QUESTION_FILE, encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    print("\n" + "=" * 60)
    print("  AutoDocument 示例 - 苏轼语料")
    print("=" * 60)
    print("通过 general/base_document 分块（不跑 LLM 抽取）...")

    corpus = Template.create("general/base_document", "zh", llm, embedder)
    corpus.feed_text(text, source_id="sushi")

    print(f"\n已存储 {len(corpus.data.chunks)} 个块")
    for chunk in corpus.data.chunks[:3]:
        preview = chunk.content[:80].replace("\n", " ")
        print(f"  - {preview}...")

    corpus.build_index()

    print("-" * 60)
    print("问答")
    print("-" * 60)
    for q in questions[:2]:
        print(f"\nQ: {q}")
        try:
            result = corpus.chat(q)
            print(f"A: {result.content}")
        except Exception as e:
            print(f"Error: {e}")
