"""
Conversation history — lưu trong Redis (stateless design).

Anti-pattern (bản develop):       conversation_history = {}  # memory!
Correct (bản production này):     Redis list per user.

→ Kill bất kỳ instance nào, conversation vẫn còn (test_stateless).
"""

import json

from .config import settings
from .redis_client import get_redis

HISTORY_TTL_SECONDS = 24 * 3600  # history sống 24h


def _key(user_id: str) -> str:
    return f"history:{user_id}"


def get_history(user_id: str) -> list[dict]:
    """Returns [{"role": "user"|"assistant", "content": str}, ...] (cũ → mới)."""
    r = get_redis()
    raw = r.lrange(_key(user_id), 0, -1)
    return [json.loads(item) for item in raw]


def append_history(user_id: str, question: str, answer: str) -> None:
    r = get_redis()
    key = _key(user_id)
    pipe = r.pipeline()
    pipe.rpush(key, json.dumps({"role": "user", "content": question}, ensure_ascii=False))
    pipe.rpush(key, json.dumps({"role": "assistant", "content": answer}, ensure_ascii=False))
    # Giữ tối đa N turns (2 messages / turn)
    pipe.ltrim(key, -settings.HISTORY_MAX_TURNS * 2, -1)
    pipe.expire(key, HISTORY_TTL_SECONDS)
    pipe.execute()
