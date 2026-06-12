"""
Production-ready RAG Agent — Day 12 Final Project.

Agent gốc: Day 8 RAG pipeline (luật ma túy VN + báo chí) → production-hóa với:
    - Config từ env vars (12-factor)          → config.py
    - API key authentication                  → auth.py
    - Rate limiting 10 req/min (Redis)        → rate_limiter.py
    - Cost guard $10/tháng (Redis)            → cost_guard.py
    - Stateless: history trong Redis          → history.py
    - BM25 retrieval (Day 8 Task 6)           → rag/retriever.py
    - Generation + citation (Day 8 Task 10)   → rag/generator.py
    - Health + readiness probes               → /health, /ready
    - Graceful shutdown (SIGTERM)             → lifespan + uvicorn
    - Structured JSON logging                 → logging_config.py
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, get_spending, record_cost
from .history import append_history, get_history
from .logging_config import setup_logging
from .rag.generator import generate
from .rag.retriever import BM25Retriever
from .rate_limiter import check_rate_limit
from .redis_client import close_redis, get_redis

logger = setup_logging(settings.LOG_LEVEL)


# =============================================================================
# LIFESPAN — startup / graceful shutdown
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup: build BM25 index 1 lần (static data, không phải session state)
    logger.info("Starting up: building BM25 index from %s", settings.DATA_DIR)
    app.state.retriever = BM25Retriever(settings.DATA_DIR)
    app.state.ready = True
    logger.info("Startup complete — ready to serve traffic")

    yield  # ←—— app phục vụ requests ở đây

    # --- Graceful shutdown: uvicorn bắt SIGTERM → ngừng nhận request mới,
    # đợi requests đang chạy xong, rồi mới chạy phần dưới đây.
    app.state.ready = False
    logger.info("SIGTERM received: draining in-flight requests, closing connections")
    close_redis()
    logger.info("Shutdown complete")


app = FastAPI(
    title="DrugLaw RAG Agent",
    description="Production-ready RAG agent về pháp luật ma túy VN (Day 8 → Day 12)",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# MIDDLEWARE — structured request logging
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s", request.method, request.url.path,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


# =============================================================================
# SCHEMAS
# =============================================================================

class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=2000)


class Source(BaseModel):
    chunk_id: str
    source: str
    category: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    user_id: str
    history_turns: int
    monthly_spending_usd: float
    request_cost_usd: float


# =============================================================================
# PROBES
# =============================================================================

@app.get("/health")
def health():
    """Liveness probe — process còn sống không? (orchestrator restart nếu fail)"""
    return {"status": "ok"}


@app.get("/ready")
def ready(request: Request):
    """Readiness probe — sẵn sàng nhận traffic không? (check dependencies)"""
    if not getattr(request.app.state, "ready", False):
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": "starting/stopping"})
    try:
        get_redis().ping()
    except Exception as exc:  # Redis down → đừng nhận traffic
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": f"redis: {exc}"})
    return {"status": "ready"}


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request, _key: str = Depends(verify_api_key)):
    """
    Pipeline: auth → rate limit → budget → history(Redis) → BM25 retrieve
              → generate (citation) → record cost → save history(Redis)
    """
    user_id = body.user_id

    # Security layers 2 & 3 (layer 1 = auth dependency)
    check_rate_limit(user_id)
    check_budget(user_id)

    # 1. Conversation history từ Redis (KHÔNG phải memory — stateless)
    history = get_history(user_id)

    # 2. Retrieve (Day 8: BM25 lexical search)
    retriever: BM25Retriever = request.app.state.retriever
    contexts = retriever.search(body.question, top_k=settings.TOP_K)

    # 3. Generate (Day 8: generation có citation)
    answer, cost = generate(body.question, contexts, history)

    # 4. Ghi cost + history vào Redis
    total_spending = record_cost(user_id, cost)
    append_history(user_id, body.question, answer)

    logger.info(
        "answered question", extra={"user_id": user_id, "cost_usd": cost},
    )

    return AskResponse(
        answer=answer,
        sources=[Source(**{k: c[k] for k in ("chunk_id", "source", "category", "score")}) for c in contexts],
        user_id=user_id,
        history_turns=len(history) // 2 + 1,
        monthly_spending_usd=round(total_spending, 6),
        request_cost_usd=cost,
    )


@app.get("/")
def root():
    return {
        "service": "DrugLaw RAG Agent (Day 8 → Day 12 production)",
        "endpoints": {
            "GET /health": "liveness probe",
            "GET /ready": "readiness probe",
            "POST /ask": "hỏi đáp pháp luật ma túy (cần X-API-Key)",
        },
    }
