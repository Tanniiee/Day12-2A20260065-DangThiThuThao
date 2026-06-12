"""
Document loader + chunker — kế thừa Task 3/4 của Day 8.

Load các file markdown đã chuẩn hóa trong data/standardized/
(văn bản pháp luật về ma túy + bài báo nghệ sĩ liên quan ma túy),
chunk theo đoạn văn với max size + overlap.

Khác Day 8: bỏ embedding/ChromaDB (nặng ~2GB image) — production version
dùng BM25 thuần (xem retriever.py) để giữ Docker image < 500MB.
"""

import re
from pathlib import Path

CHUNK_SIZE = 800      # ký tự
CHUNK_OVERLAP = 100   # ký tự


def load_documents(data_dir: str) -> list[dict]:
    """
    Load tất cả file .md trong data_dir (đệ quy).

    Returns:
        List of {"source": str, "category": str, "content": str}
    """
    root = Path(data_dir)
    docs = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        docs.append({
            "source": path.name,
            "category": path.parent.name,  # "legal" | "news"
            "content": text,
        })
    return docs


def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Chunk theo đoạn văn (paragraph-aware) với overlap.

    Returns:
        List of {"chunk_id": str, "source": str, "category": str, "content": str}
    """
    chunks = []
    for doc in docs:
        paragraphs = re.split(r"\n\s*\n", doc["content"])
        current = ""
        idx = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) + 2 > CHUNK_SIZE and current:
                chunks.append(_make_chunk(doc, idx, current))
                idx += 1
                current = current[-CHUNK_OVERLAP:] + "\n\n" + para  # giữ overlap
            else:
                current = (current + "\n\n" + para).strip()
        if current.strip():
            chunks.append(_make_chunk(doc, idx, current))
    return chunks


def _make_chunk(doc: dict, idx: int, content: str) -> dict:
    return {
        "chunk_id": f"{doc['source']}#{idx}",
        "source": doc["source"],
        "category": doc["category"],
        "content": content.strip(),
    }
