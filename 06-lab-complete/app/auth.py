"""
API Key Authentication — Layer 1 của security.

Public URL = ai cũng gọi được = hết tiền OpenAI.
→ Mọi request tới /ask phải có header X-API-Key hợp lệ.

So sánh key bằng hmac.compare_digest (constant-time) để chống timing attack.
"""

import hmac

from fastapi import Header, HTTPException

from .config import settings


def verify_api_key(x_api_key: str = Header(default="")) -> str:
    """
    FastAPI dependency: kiểm tra header X-API-Key.

    Returns:
        api key (đã verify) — caller có thể dùng làm identity.
    Raises:
        HTTPException 401 nếu thiếu hoặc sai key.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not hmac.compare_digest(x_api_key, settings.AGENT_API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
