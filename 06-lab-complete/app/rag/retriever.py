"""
BM25 Retriever — kế thừa Task 6 (lexical search) của Day 8.

BM25 hoạt động thế nào:
    - TF: từ xuất hiện nhiều trong chunk → điểm cao
    - IDF: từ hiếm trong corpus → quan trọng hơn từ phổ biến
    - Length normalization: chunk dài không được ưu tiên quá mức

Index build 1 lần lúc startup (lifespan), sau đó chỉ đọc → thread-safe,
không có state per-user nào ở đây (corpus là static data, không phải session state).
"""

import logging
import re

from rank_bm25 import BM25Okapi

from .loader import chunk_documents, load_documents

logger = logging.getLogger("agent.retriever")

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokenizer đơn giản, unicode-aware (giữ được tiếng Việt có dấu)."""
    return _WORD_RE.findall(text.lower())


class BM25Retriever:
    def __init__(self, data_dir: str):
        docs = load_documents(data_dir)
        self.chunks = chunk_documents(docs)
        if not self.chunks:
            raise RuntimeError(f"No documents found in {data_dir}")
        self._bm25 = BM25Okapi([tokenize(c["content"]) for c in self.chunks])
        logger.info(
            "BM25 index built: %d documents, %d chunks", len(docs), len(self.chunks)
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Returns top_k chunks: [{"chunk_id", "source", "category", "content", "score"}]
        """
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results = []
        for i in ranked[:top_k]:
            if scores[i] <= 0:
                continue
            results.append({**self.chunks[i], "score": round(float(scores[i]), 4)})
        return results
