# DrugLaw RAG Agent — Day 12 Final Project

> **AICB-P1 · VinUniversity 2026**
> Production-hóa RAG pipeline của **Day 8** (hỏi đáp pháp luật Việt Nam về ma túy + báo chí liên quan) theo toàn bộ yêu cầu **Day 12**.

## Agent làm gì?

Trả lời câu hỏi về pháp luật ma túy VN qua REST API, dựa trên corpus thật của Day 8 (`data/standardized/`): Luật Phòng chống ma túy 2021, Nghị định 105/2021, Chương XX BLHS, và 5 bài báo. Pipeline: **BM25 retrieval → generation có citation** (OpenAI, tự fallback mock LLM khi không có key).

So với Day 8 gốc: bỏ ChromaDB + sentence-transformers (nặng ~2GB) để Docker image < 500MB; giữ lexical search (Task 6), chunking (Task 4), generation + citation (Task 10).

## Production features (rubric Day 12)

| Tiêu chí | Implement |
|----------|-----------|
| Config từ env vars | `app/config.py` (pydantic-settings, không hardcode secrets) |
| API key auth (401) | `app/auth.py` — header `X-API-Key`, constant-time compare |
| Rate limiting 10 req/min (429) | `app/rate_limiter.py` — sliding window, Redis sorted set |
| Cost guard $10/tháng (402) | `app/cost_guard.py` — track spending theo `budget:{user}:{YYYY-MM}` |
| Health + readiness | `GET /health`, `GET /ready` (ping Redis) |
| Graceful shutdown | lifespan + uvicorn SIGTERM handling |
| Stateless | conversation history + rate/budget đều trong Redis |
| JSON logging | `app/logging_config.py` |
| Multi-stage Docker | `Dockerfile` (builder → slim runtime, non-root user) |
| Load balancing | `docker-compose.yml` + Nginx, scale 3 replicas |

## Chạy local (không cần Docker)

```bash
cp .env.example .env
pip install -r requirements.txt
# Cần Redis: docker run -d -p 6379:6379 redis:7-alpine
uvicorn app.main:app --port 8000
```

## Chạy full stack (Nginx LB + 3 agents + Redis)

```bash
docker compose up --build --scale agent=3
```

Test:

```bash
curl http://localhost/health
curl http://localhost/ready

# 401 — thiếu key
curl -X POST http://localhost/ask -H "Content-Type: application/json" \
  -d '{"user_id":"u1","question":"Hello"}'

# 200 — có key
curl -X POST http://localhost/ask \
  -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" \
  -d '{"user_id":"u1","question":"Tội tàng trữ trái phép chất ma túy bị xử lý thế nào?"}'

# 429 — gọi quá 10 lần/phút
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost/ask \
    -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" \
    -d '{"user_id":"u1","question":"test"}'
done
```

## Tests

```bash
pip install pytest fakeredis httpx
pytest tests/ -v
```

## Deploy

**Railway:** `railway init` → add Redis plugin → `railway variables set AGENT_API_KEY=...` → `railway up` (đọc `railway.toml`).

**Render:** push GitHub → New Blueprint → repo này (đọc `render.yaml`, tự tạo Redis kèm theo) → set `AGENT_API_KEY` trong dashboard.

## CI/CD — GHCR (GitHub Container Registry)

Workflow `.github/workflows/docker-publish.yml` tự động khi push lên `main`:

1. Chạy `pytest` (fail → không build)
2. Build multi-stage image (cache layer qua GitHub Actions cache)
3. Push lên `ghcr.io/<owner>/<repo>` với tags: `latest`, `sha-<commit>`, `main`, semver khi tag `v*`
4. Verify image < 500 MB (rubric Day 12) — fail CI nếu vượt

Không cần secret thêm — dùng `GITHUB_TOKEN` có sẵn. Pull image:

```bash
docker pull ghcr.io/<owner>/<repo>:latest
docker run -p 8000:8000 -e REDIS_URL=... -e AGENT_API_KEY=... ghcr.io/<owner>/<repo>:latest
```

Lưu ý: lần đầu push xong, vào GitHub → Packages → package settings → đổi visibility thành **Public** nếu muốn pull không cần login (mặc định là private).

## Cấu trúc

```
06-lab-complete/
├── app/
│   ├── main.py            # FastAPI: /health /ready /ask, lifespan, JSON log middleware
│   ├── config.py          # 12-factor config (env vars)
│   ├── auth.py            # API key authentication
│   ├── rate_limiter.py    # Sliding window (Redis)
│   ├── cost_guard.py      # Budget $10/tháng (Redis)
│   ├── history.py         # Conversation history (Redis — stateless)
│   ├── logging_config.py  # Structured JSON logging
│   ├── redis_client.py    # Shared Redis connection
│   └── rag/
│       ├── loader.py      # Load + chunk markdown (Day 8 Task 3/4)
│       ├── retriever.py   # BM25 (Day 8 Task 6)
│       └── generator.py   # OpenAI + mock fallback, citation (Day 8 Task 10)
├── data/standardized/     # Corpus Day 8 (legal + news)
├── tests/test_app.py      # Smoke tests (auth/429/402/stateless)
├── Dockerfile             # Multi-stage, non-root, healthcheck
├── docker-compose.yml     # agent x N + redis + nginx
├── nginx/nginx.conf       # Load balancer
├── railway.toml / render.yaml
└── .env.example           # Template config (không commit .env)
```
