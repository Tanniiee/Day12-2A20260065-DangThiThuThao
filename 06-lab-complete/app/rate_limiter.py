"""
Rate Limiting — Layer 2 của security (sliding window, Redis).

Algorithm: Sliding Window với Redis Sorted Set.
    - Mỗi request → ZADD timestamp vào key rate:{user_id}
    - ZREMRANGEBYSCORE xóa các entry cũ hơn 60s
    - ZCARD đếm số request trong cửa sổ 60s hiện tại
    - Vượt limit → HTTP 429

Tại sao sliding window thay vì fixed window?
→ Fixed window có "burst" ở ranh giới (20 req trong 2 giây quanh phút mới).
  Sliding window đếm chính xác 60 giây gần nhất.

Lưu trong Redis (không phải memory) → limit đúng kể cả khi chạy 3 instances.
"""

import time
import uuid

from fastapi import HTTPException

from .config import settings
from .redis_client import get_redis

WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> None:
    """
    Raises HTTPException 429 nếu user vượt RATE_LIMIT_PER_MINUTE.
    """
    r = get_redis()
    key = f"rate:{user_id}"
    now = time.time()

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)          # bỏ entry quá 60s
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})       # ghi request hiện tại
    pipe.zcard(key)                                              # đếm trong window
    pipe.expire(key, WINDOW_SECONDS * 2)                         # tự dọn key
    _, _, count, _ = pipe.execute()

    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: {settings.RATE_LIMIT_PER_MINUTE} requests/minute. "
                "Try again later."
            ),
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )
