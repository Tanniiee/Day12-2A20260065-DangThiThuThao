"""
Generation có citation — kế thừa Task 10 của Day 8.

- Có OPENAI_API_KEY  → gọi OpenAI (gpt-4o-mini mặc định).
- Không có key       → Mock LLM: trả lời extractive từ context
  (đúng tinh thần lab: chạy được offline, không cần credit card).

Đồng thời ƯỚC TÍNH chi phí mỗi call để cost_guard cộng dồn.
"""

import logging

from ..config import settings

logger = logging.getLogger("agent.generator")

SYSTEM_PROMPT = (
    "Bạn là trợ lý pháp luật chuyên về pháp luật Việt Nam liên quan đến ma túy "
    "và các chất cấm. Chỉ trả lời dựa trên CONTEXT được cung cấp. "
    "Luôn trích dẫn nguồn theo dạng [source: tên_file]. "
    "Nếu context không đủ thông tin, hãy nói rõ là không tìm thấy."
)

# Giá gpt-4o-mini (USD / 1M tokens)
PRICE_INPUT_PER_1M = 0.15
PRICE_OUTPUT_PER_1M = 0.60


def _estimate_tokens(text: str) -> int:
    """Ước lượng thô: ~4 ký tự / token."""
    return max(1, len(text) // 4)


def _build_prompt(question: str, contexts: list[dict], history: list[dict]) -> list[dict]:
    context_block = "\n\n---\n\n".join(
        f"[source: {c['source']}]\n{c['content']}" for c in contexts
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context_block}\n\nCÂU HỎI: {question}",
    })
    return messages


def generate(question: str, contexts: list[dict], history: list[dict]) -> tuple[str, float]:
    """
    Returns:
        (answer, estimated_cost_usd)
    """
    messages = _build_prompt(question, contexts, history)
    input_tokens = sum(_estimate_tokens(m["content"]) for m in messages)

    if settings.OPENAI_API_KEY:
        answer = _generate_openai(messages)
    else:
        answer = _generate_mock(question, contexts)

    output_tokens = _estimate_tokens(answer)
    cost = (
        input_tokens * PRICE_INPUT_PER_1M + output_tokens * PRICE_OUTPUT_PER_1M
    ) / 1_000_000
    return answer, round(cost, 6)


def _generate_openai(messages: list[dict]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=800,
    )
    return response.choices[0].message.content or ""


def _generate_mock(question: str, contexts: list[dict]) -> str:
    """Mock LLM: extractive answer từ top chunks, kèm citation."""
    if not contexts:
        return (
            "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu pháp luật/báo chí. "
            "(mock LLM — set OPENAI_API_KEY để dùng LLM thật)"
        )
    top = contexts[0]
    snippet = top["content"][:400]
    sources = ", ".join(c["source"] for c in contexts[:3])
    return (
        f"(mock LLM) Dựa trên tài liệu tìm được, đoạn liên quan nhất tới câu hỏi "
        f"\"{question}\" là:\n\n{snippet}...\n\n[source: {sources}]"
    )
