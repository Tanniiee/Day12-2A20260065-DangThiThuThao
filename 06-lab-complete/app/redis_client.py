"""
Redis client dùng chung — nơi lưu TOÀN BỘ state (stateless design).

Tại sao không lưu state trong memory?
→ Khi scale ra 3 instances, mỗi instance có memory riêng.
  Request 1 vào Agent1 (lưu history), request 2 vào Agent2 (không thấy history).
→ Redis là shared store: instance nào cũng đọc/ghi cùng một chỗ.
"""

import redis

from .config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Singleton Redis connection (lazy init)."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _client


def close_redis() -> None:
    """Đóng connection khi graceful shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
