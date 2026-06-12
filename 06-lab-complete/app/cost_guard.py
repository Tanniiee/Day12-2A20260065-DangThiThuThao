"""
Cost Guard — Layer 3 của security: chống cháy ví OpenAI.

Logic:
    - Mỗi user có budget MONTHLY_BUDGET_USD ($10/tháng mặc định)
    - Spending track trong Redis key: budget:{user_id}:{YYYY-MM}
    - Key tự reset đầu tháng (vì key chứa tháng) + expire 32 ngày
    - Vượt budget → HTTP 402 Payment Required

Flow 2 bước:
    1. check_budget(user_id)  — TRƯỚC khi gọi LLM: đã vượt thì chặn luôn
    2. record_cost(user_id, cost) — SAU khi gọi LLM: cộng dồn chi phí thật
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import get_redis

KEY_TTL_SECONDS = 32 * 24 * 3600  # 32 ngày — qua tháng là key cũ tự biến mất


def _month_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def get_spending(user_id: str) -> float:
    """Chi phí user đã dùng trong tháng hiện tại (USD)."""
    r = get_redis()
    return float(r.get(_month_key(user_id)) or 0.0)


def check_budget(user_id: str) -> None:
    """Raises HTTPException 402 nếu user đã vượt budget tháng này."""
    spending = get_spending(user_id)
    if spending >= settings.MONTHLY_BUDGET_USD:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Monthly budget exceeded: ${spending:.4f} / "
                f"${settings.MONTHLY_BUDGET_USD:.2f}. Resets next month."
            ),
        )


def record_cost(user_id: str, cost_usd: float) -> float:
    """Cộng chi phí vào spending tháng này. Returns tổng mới."""
    r = get_redis()
    key = _month_key(user_id)
    new_total = r.incrbyfloat(key, cost_usd)
    r.expire(key, KEY_TTL_SECONDS)
    return float(new_total)
