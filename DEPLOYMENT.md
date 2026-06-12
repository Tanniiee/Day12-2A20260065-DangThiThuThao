# Deployment Information

> **Student:** Đặng Thị Thu Thảo — 2A202600685

## Public URL

**https://day12-2a202600685-dangthithuthao-production.up.railway.app**

- Mở trên trình duyệt → **chat UI** tích hợp (nhập API key + đặt câu hỏi trực tiếp)
- API docs tự sinh: `/docs` (Swagger UI)

## Platform

**Railway** — service agent (Docker, root directory `06-lab-complete`) + **Redis** database, cùng một project, kết nối qua private network với variable reference.

## Docker Image (CI/CD)

Image build & push tự động bằng GitHub Actions mỗi lần push lên `main`:

```
ghcr.io/tanniiee/day12-2a20260065-dangthithuthao:latest
```

Pipeline (`.github/workflows/docker-publish.yml`): pytest → build multi-stage (Buildx + layer cache) → push GHCR → verify image < 500 MB.

## Test Commands

### Health Check (liveness)

```bash
curl https://day12-2a202600685-dangthithuthao-production.up.railway.app/health
# Expected: {"status":"ok"}
```

### Readiness Check (có kiểm tra kết nối Redis)

```bash
curl https://day12-2a202600685-dangthithuthao-production.up.railway.app/ready
# Expected: {"status":"ready"}
```

### Authentication required — không có key phải bị chặn

```bash
curl -X POST https://day12-2a202600685-dangthithuthao-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: HTTP 401 {"detail":"Missing X-API-Key header"}
```

### API Test (với authentication)

```bash
curl -X POST https://day12-2a202600685-dangthithuthao-production.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Tội tàng trữ trái phép chất ma túy bị phạt thế nào?"}'
# Expected: HTTP 200 — answer + sources (citation từ corpus pháp luật) + chi phí request
```

### Rate Limiting (10 req/phút → 429)

```bash
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " \
    -X POST https://day12-2a202600685-dangthithuthao-production.up.railway.app/ask \
    -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
    -d '{"user_id":"test","question":"test"}'
done
# Expected: 200 x10 rồi 429 x5
```

### Cost Guard

Mỗi user có budget $10/tháng (track trong Redis theo key `budget:{user}:{YYYY-MM}`). Vượt budget → HTTP 402 Payment Required. Mỗi response đều trả về `monthly_spending_usd` để theo dõi.

## Environment Variables Set (trên Railway)

| Biến | Ghi chú |
|------|---------|
| `REDIS_URL` | Reference `${{Redis.REDIS_URL}}` tới Redis service cùng project |
| `AGENT_API_KEY` | Key xác thực API (secret, không commit) |
| `OPENAI_API_KEY` | Key OpenAI cho generation (secret; bỏ trống → mock LLM) |
| `PORT` | Railway inject tự động |

Các biến khác (`RATE_LIMIT_PER_MINUTE=10`, `MONTHLY_BUDGET_USD=10.0`, `LOG_LEVEL=INFO`...) dùng default trong `app/config.py`, override được qua env.

## Screenshots

- [Railway dashboard — agent + Redis online](screenshots/railway-dashboard.png)
- [Chat UI đang trả lời câu hỏi kèm citation](screenshots/ui-chat.png)
- [GitHub Actions CI/CD xanh](screenshots/ci-green.png)
- [GHCR package](screenshots/ghcr-package.png)
- [Test 401/429 bằng curl](screenshots/test-results.png)

## Architecture

```
                  Railway project
   ┌────────────────────────────────────────┐
   │  ┌──────────────┐      ┌────────────┐  │
   │  │ Agent (Docker)│◄────►│   Redis    │  │
   │  │ FastAPI + UI  │ priv │ (state:    │  │
   │  │ BM25 + LLM    │ net  │ history,   │  │
   │  └──────▲───────┘      │ rate, cost)│  │
   │         │ HTTPS         └────────────┘  │
   └─────────┼────────────────────────────--─┘
             │
        Client (browser UI / curl)

   GitHub push → Actions CI → GHCR image (latest, sha-*)
              └→ Railway auto-redeploy
```

Local full stack (Nginx LB + 3 replicas + Redis): `cd 06-lab-complete && docker compose up --build --scale agent=3` — xem `06-lab-complete/README.md`.
