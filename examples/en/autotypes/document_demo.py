"""
AutoDocument Demo - Tesla corpus chunks

Load the Gallery `general/base_document` preset and store raw text chunks.
AutoDocument does not run LLM extraction; the LLM client is only used by
optional chat after chunks are indexed.

Usage:
    python examples/en/autotypes/document_demo.py
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from hyperextract.utils.template_engine import Template

project_root = Path(__file__).resolve().parent.parent.parent.parent

load_dotenv()

INPUT_FILE = project_root / "examples" / "en" / "tesla.md"
QUESTION_FILE = project_root / "examples" / "en" / "tesla_question.md"


if __name__ == "__main__":
    with open(INPUT_FILE, encoding="utf-8") as f:
        text = f.read()
    with open(QUESTION_FILE, encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    print("\n" + "=" * 60)
    print("  AutoDocument Demo - Tesla corpus")
    print("=" * 60)
    print("Chunking text via general/base_document (no LLM extraction)...")

    corpus = Template.create("general/base_document", "en", llm, embedder)
    corpus.feed_text(text, source_id="tesla")

    print(f"\nStored {len(corpus.data.chunks)} chunks")
    for chunk in corpus.data.chunks[:3]:
        preview = chunk.content[:80].replace("\n", " ")
        print(f"  - {preview}...")

    corpus.build_index()

    print("-" * 60)
    print("Q&A")
    print("-" * 60)
    for q in questions[:2]:
        print(f"\nQ: {q}")
        try:
            result = corpus.chat(q)
            print(f"A: {result.content}")
        except Exception as e:
            print(f"Error: {e}")
