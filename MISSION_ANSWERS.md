# Day 12 Lab — Mission Answers

> **Student:** Đặng Thị Thu Thảo — 2A20260065
> **Repo:** https://github.com/Tanniiee/Day12-2A20260065-DangThiThuThao
> **Lưu ý:** Part 6 (Final Project) trong `06-lab-complete/` được xây mới hoàn toàn, production-hóa **RAG pipeline của Day 8** (hỏi đáp pháp luật ma túy VN) thay vì dùng code mẫu.

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns tìm được trong `01-localhost-vs-production/develop/app.py`

1. **Hardcode secrets** — `OPENAI_API_KEY = "sk-hardcoded..."` và `DATABASE_URL` chứa password ngay trong code (dòng 17-18). Push lên GitHub là lộ key ngay, và muốn đổi key phải sửa code + deploy lại.
2. **Log ra secret** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` (dòng 34). Secret xuất hiện trong log → ai đọc được log là có key.
3. **Dùng `print()` thay vì structured logging** — không có level, không có timestamp, không parse được bởi log aggregator (Datadog/Loki); không thể filter hay alert.
4. **Không có health check endpoint** — platform không có cách nào biết agent còn sống để restart khi crash.
5. **Port và host cố định** — `host="localhost", port=8000`. `localhost` không nhận kết nối từ ngoài container; Railway/Render inject `PORT` qua env var nên port cứng sẽ fail.
6. **`reload=True` trong production** — debug reload tốn tài nguyên và không ổn định.
7. **`DEBUG = True` hardcode, không có config management** — không tách được config theo môi trường (dev/staging/prod).
8. **Không có graceful shutdown** — SIGTERM đến là chết ngay, request đang xử lý bị đứt.

### Exercise 1.3: Bảng so sánh develop vs production

| Feature | Develop | Production | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| Config | Hardcode trong code | Env vars qua `config.py` (pydantic settings) | Đổi config không cần sửa code; secrets không nằm trong git; mỗi môi trường một bộ config (12-factor Factor III) |
| Health check | ❌ Không có | ✅ `/health` (liveness) + `/ready` (readiness) + `/metrics` | Platform tự phát hiện app chết để restart; LB chỉ route traffic vào instance đã sẵn sàng |
| Logging | `print()`, log cả secret | Structured JSON logging, không log secret | JSON parse được bởi log aggregator; có level/timestamp để filter, alert; không lộ key |
| Shutdown | Đột ngột (không xử lý SIGTERM) | Graceful: lifespan + SIGTERM handler, drain in-flight requests | Khi platform rolling-deploy/scale-down, request đang chạy được hoàn thành thay vì đứt giữa chừng → user không thấy lỗi |
| Host/Port | `localhost:8000` cứng | `0.0.0.0` + `PORT` từ env | Container phải bind 0.0.0.0 mới nhận traffic từ ngoài; cloud platform inject PORT động |
| CORS | Không có | Chỉ cho phép origins được cấu hình | Chặn website lạ gọi API từ trình duyệt |

### Checkpoint 1

- [x] Hardcode secrets nguy hiểm vì: lộ key khi push git, không rotate được, xuất hiện trong log
- [x] Env vars: đọc qua `os.getenv()` / pydantic-settings, template `.env.example`, file `.env` thật nằm trong `.gitignore`
- [x] Health check: tín hiệu cho orchestrator restart container hỏng và cho LB điều phối traffic
- [x] Graceful shutdown: bắt SIGTERM → ngừng nhận request mới → hoàn thành request đang chạy → đóng connections → exit

---

## Part 2: Docker

### Exercise 2.1: Câu hỏi về `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11` — bản full distribution (~1 GB), chứa cả build tools không cần thiết lúc runtime.
2. **Working directory:** `/app` (lệnh `WORKDIR /app`) — mọi lệnh COPY/RUN/CMD sau đó chạy tương đối từ đây.
3. **Tại sao COPY requirements.txt trước khi COPY code?** Vì Docker cache theo từng layer: layer `RUN pip install` chỉ bị build lại khi `requirements.txt` đổi. Code đổi thường xuyên nhưng dependencies thì ít đổi → tách ra giúp các lần build sau bỏ qua bước pip install (nhanh hơn rất nhiều).
4. **CMD vs ENTRYPOINT:**
   - `CMD` = lệnh **mặc định**, bị thay thế hoàn toàn khi chạy `docker run image <lệnh khác>`.
   - `ENTRYPOINT` = lệnh **cố định** luôn chạy; tham số ở `docker run` được nối vào sau thay vì thay thế.
   - Kết hợp: `ENTRYPOINT ["uvicorn"]` + `CMD ["app:app", "--port", "8000"]` → user override được args nhưng không đổi được executable.

### Exercise 2.3: Multi-stage build (`02-docker/production/Dockerfile`)

- **Stage 1 (builder):** từ `python:3.11-slim`, cài `gcc`, `libpq-dev` (build tools) rồi `pip install --user` toàn bộ dependencies vào `/root/.local`.
- **Stage 2 (runtime):** từ `python:3.11-slim` sạch, chỉ `COPY --from=builder /root/.local` (site-packages đã compile) + source code. Tạo non-root user `appuser`, thêm HEALTHCHECK.
- **Tại sao image nhỏ hơn:** stage 2 không mang theo gcc, apt cache, pip cache, intermediate layers của quá trình build — chỉ còn Python runtime + packages + code.

### Exercise 2.2/2.3: So sánh image size

| Image | Size |
|-------|------|
| `my-agent:develop` (python:3.11 full, single-stage) | ~1.0 GB |
| `my-agent:advanced` (python:3.11-slim, multi-stage) | ~200-250 MB |
| **Giảm** | **~75-80%** |

*(Image của Part 6 build trên CI — bước "Check image size" trong GitHub Actions xác nhận < 500 MB.)*

### Exercise 2.4: Docker Compose stack

Services trong `02-docker/production/docker-compose.yml`: **agent** (FastAPI, build từ Dockerfile multi-stage, target runtime), **redis** (cache/session/rate-limit), **qdrant** (vector DB), **nginx** (reverse proxy + load balancer).

Architecture:

```
Client → Nginx (:80) → agent (FastAPI :8000, nhiều replicas)
                          ├→ Redis  (session, rate limit)
                          └→ Qdrant (vector search)
```

Chúng giao tiếp qua **Docker network nội bộ bằng service name** (`redis://redis:6379`, `http://qdrant:6333`) — Docker DNS tự resolve. Agent không expose port ra ngoài, chỉ Nginx có port 80. `depends_on + condition: service_healthy` đảm bảo agent chỉ start sau khi Redis/Qdrant đã healthy.

### Checkpoint 2

- [x] Hiểu cấu trúc Dockerfile (FROM → WORKDIR → COPY deps → RUN install → COPY code → CMD)
- [x] Multi-stage: image nhỏ hơn ~75%, ít attack surface, không chứa build tools
- [x] Compose: orchestration nhiều service, network nội bộ, healthcheck, depends_on
- [x] Debug: `docker logs <id>`, `docker exec -it <id> /bin/sh`, `docker compose logs agent`

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://day12-2a202600685-dangthithuthao-production.up.railway.app
- **UI chat:** mở URL trên trình duyệt (giao diện chat tích hợp tại `/`)
- **Setup:** Deploy from GitHub repo → Root Directory = `06-lab-complete` → Add Redis database → Variables: `REDIS_URL = ${{Redis.REDIS_URL}}` (reference), `AGENT_API_KEY`, `OPENAI_API_KEY` → Generate Domain
- **Screenshot:** xem `screenshots/` trong repo

Test:

```bash
curl https://day12-2a202600685-dangthithuthao-production.up.railway.app/health
# {"status":"ok"}
```

### Exercise 3.2: So sánh `render.yaml` vs `railway.toml`

| | `railway.toml` | `render.yaml` |
|--|----------------|---------------|
| Phạm vi | Config cho **1 service** (build + deploy) | **Blueprint cả infrastructure**: nhiều services, database, env vars liên kết |
| Builder | `builder = "NIXPACKS"` hoặc `dockerfile` | `runtime: python` / `runtime: docker` + `buildCommand` |
| Env vars | Set qua dashboard/CLI, file toml không chứa | Khai báo được trong YAML (`envVars`, `sync: false` cho secrets, `fromService` để reference DB) |
| Region/plan | Quản lý ở dashboard | Khai báo trong YAML (`region: singapore`, `plan: free`) |
| Triết lý | Config tối thiểu, dashboard-first | Infrastructure-as-Code đầy đủ, git-first |

Giống nhau: cả hai đều khai báo health check path, start command, auto-restart, và đều không commit secrets.

### Exercise 3.3 (Optional): Cloud Run

Đã đọc `cloudbuild.yaml`/`service.yaml`: CI/CD pipeline = push code → Cloud Build build image → đẩy lên Artifact Registry → deploy revision mới lên Cloud Run (serverless, scale-to-zero, trả tiền theo request). Trong bài này em làm CI/CD tương đương bằng **GitHub Actions → GHCR** (`.github/workflows/docker-publish.yml`): test → build multi-stage → push `ghcr.io/tanniiee/day12-2a20260065-dangthithuthao` → verify size < 500 MB.

### Checkpoint 3

- [x] Deploy thành công lên Railway (kèm Redis)
- [x] Public URL hoạt động (UI + API)
- [x] Env vars set trên cloud dashboard, dùng variable reference cho REDIS_URL
- [x] Xem logs: Railway → service → Deployments → View Logs (JSON logs của app hiện ở đây)

---

## Part 4: API Security

### Exercise 4.1: API Key authentication (`04-api-gateway/develop/app.py`)

- **Key được check ở đâu?** Dependency `verify_api_key()` dùng `APIKeyHeader(name="X-API-Key")`, inject vào endpoint qua `Depends(verify_api_key)`. FastAPI chạy dependency trước handler.
- **Điều gì xảy ra nếu sai key?** Thiếu key → `401 Unauthorized`; sai key → `403 Forbidden` (bản develop). Trong bản production Part 6 em trả về 401 cho cả hai và so sánh bằng `hmac.compare_digest` để chống timing attack.
- **Làm sao rotate key?** Key đọc từ env var `AGENT_API_KEY` → đổi giá trị trên dashboard (Railway Variables) → restart service. Không cần sửa code. Nâng cao hơn: hỗ trợ đồng thời 2 key (old + new) trong thời gian chuyển tiếp.

### Exercise 4.1-4.3: Kết quả test (trên service đã deploy)

```bash
# ❌ Không có key → 401
$ curl -X POST .../ask -H "Content-Type: application/json" -d '{"user_id":"u1","question":"Hello"}'
{"detail":"Missing X-API-Key header"}            # HTTP 401

# ✅ Có key → 200, có câu trả lời + citation + chi phí
$ curl -X POST .../ask -H "X-API-Key: ***" -H "Content-Type: application/json" \
       -d '{"user_id":"u1","question":"Tội tàng trữ trái phép chất ma túy bị phạt thế nào?"}'
{"answer":"...","sources":[{"chunk_id":"cac-toi-pham-ve-ma-tuy-chuong-xx.md#...","source":"cac-toi-pham-ve-ma-tuy-chuong-xx.md","category":"legal","score":...}],
 "monthly_spending_usd":0.00026,"request_cost_usd":0.00026}   # HTTP 200

# ❌ Gọi 15 lần liên tục → 10 lần đầu 200, từ lần 11 trả 429
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
{"detail":"Rate limit exceeded: 10 requests/minute. Try again later."}   # + header Retry-After
```

**Rate limiter dùng algorithm nào?** Sliding Window. Bản develop (`rate_limiter.py`): in-memory `deque` timestamps per user — pop các timestamp cũ hơn 60s, đếm phần còn lại, vượt limit → 429 kèm headers `X-RateLimit-*` và `Retry-After`. **Limit: 10 req/phút.** Nhược điểm in-memory: scale nhiều instance là sai số (mỗi instance đếm riêng) → bản production Part 6 em chuyển sang **Redis Sorted Set** (ZADD timestamp, ZREMRANGEBYSCORE, ZCARD) để mọi instance dùng chung một counter. **Bypass cho admin:** whitelist user_id/API key riêng không qua check, hoặc cấu hình limit cao hơn theo tier.

### Exercise 4.4: Cost guard — cách tiếp cận

```python
def check_budget(user_id):                      # TRƯỚC khi gọi LLM
    key = f"budget:{user_id}:{datetime.now():%Y-%m}"   # key chứa tháng
    if float(redis.get(key) or 0) >= MONTHLY_BUDGET:   # $10/tháng
        raise HTTPException(402)

def record_cost(user_id, cost):                 # SAU khi gọi LLM
    redis.incrbyfloat(key, cost)
    redis.expire(key, 32 * 24 * 3600)           # key tự hết hạn sau 32 ngày
```

Điểm chính: (1) key chứa `YYYY-MM` nên **tự reset đầu tháng** — qua tháng là key mới từ 0; (2) `expire 32 ngày` để Redis tự dọn key cũ; (3) flow 2 bước — check trước khi gọi LLM (chặn sớm, không tốn tiền), ghi nhận chi phí thật sau khi gọi; (4) chi phí ước tính từ token (~4 ký tự/token × giá gpt-4o-mini); (5) trả về **HTTP 402 Payment Required** đúng ngữ nghĩa. Test thực tế: set spending > $10 trong Redis → request tiếp theo nhận 402.

### Checkpoint 4

- [x] API key authentication (X-API-Key, constant-time compare)
- [x] JWT flow: POST /token (username/password) → nhận JWT có expiry → gọi API với `Authorization: Bearer <token>`; server verify chữ ký, không cần lưu session
- [x] Rate limiting sliding window trên Redis
- [x] Cost guard với Redis, key theo tháng

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

```python
@app.get("/health")          # Liveness: process còn sống không?
def health():
    return {"status": "ok"}  # 200 = sống; fail → platform restart container

@app.get("/ready")           # Readiness: nhận traffic được chưa?
def ready():
    try:
        redis.ping()                          # check dependency
        return {"status": "ready"}            # 200 → LB route traffic vào
    except Exception:
        return JSONResponse(503, {"status": "not ready"})  # 503 → LB bỏ qua instance này
```

Khác biệt: **liveness** fail → restart; **readiness** fail → tạm ngừng route traffic (không restart). App đang khởi động hoặc Redis tạm mất kết nối thì not-ready chứ không chết.

### Exercise 5.2: Graceful shutdown

SIGTERM là signal platform gửi khi muốn dừng container (rolling deploy, scale down) — khác SIGKILL (không catch được). Uvicorn tự bắt SIGTERM: ngừng nhận connection mới → đợi request đang chạy xong → gọi lifespan shutdown (đóng Redis connection, log). Test thực tế: gửi request dài → `kill -TERM <pid>` → request vẫn hoàn thành, log in ra "draining in-flight requests... Shutdown complete".

### Exercise 5.3: Stateless design

Anti-pattern: `conversation_history = {}` trong memory. Khi scale 3 instances: request 1 vào Agent1 (lưu history), request 2 vào Agent2 → mất history; instance restart là mất sạch.

Refactor: chuyển toàn bộ state sang Redis — history = `RPUSH/LRANGE history:{user_id}` (TTL 24h), rate limit = sorted set, budget = counter theo tháng. Code instance **không giữ state per-user nào trong memory** (BM25 index là static data, không phải session state). Kết quả: kill instance bất kỳ → conversation vẫn còn; thêm/bớt instance không ảnh hưởng user.

### Exercise 5.4: Load balancing

`docker compose up --scale agent=3` → 3 agent replicas. Nginx (`nginx.conf`) proxy_pass tới service name `agent` — Docker DNS round-robin giữa 3 IP; config thêm `resolver 127.0.0.11 valid=5s` để re-resolve khi scale/instance chết, và `proxy_next_upstream error timeout http_502 http_503` để tự failover sang instance khác. Gọi 10 requests → `docker compose logs agent` cho thấy requests phân tán đều cho cả 3 container.

### Exercise 5.5: Test stateless

Kịch bản `test_stateless.py`: (1) gọi API tạo conversation → (2) kill ngẫu nhiên 1 instance → (3) gọi tiếp với cùng user_id → **conversation vẫn còn** (`history_turns` tăng tiếp) vì history nằm trong Redis, không nằm trong instance vừa chết. Trong repo, test tương đương: `tests/test_app.py::test_conversation_history_persists_in_redis` xác nhận history đọc/ghi hoàn toàn qua Redis.

### Checkpoint 5

- [x] Health + readiness checks (có check dependency Redis)
- [x] Graceful shutdown qua lifespan + uvicorn SIGTERM
- [x] Stateless: 100% session state trong Redis
- [x] Load balancing với Nginx (round-robin + failover)
- [x] Test stateless pass

---

## Part 6: Final Project — xem `06-lab-complete/`

Production-hóa **Day 8 RAG pipeline** (corpus: Luật PCMT 2021, Nghị định 105/2021, Chương XX BLHS + 5 bài báo):

- Pipeline: BM25 retrieval (Day 8 Task 6) → generation có citation (Day 8 Task 10, OpenAI + mock fallback)
- Đủ 12 yêu cầu non-functional của đề (auth/429/402, health/ready, graceful shutdown, stateless Redis, JSON logging, multi-stage Docker < 500 MB, compose + Nginx LB, deploy Railway)
- Trade-off có chủ đích: thay ChromaDB + sentence-transformers (image ~2 GB) bằng BM25 để đạt tiêu chí image < 500 MB
- Bonus: chat UI tại `/`, CI/CD GitHub Actions → GHCR, 10 unit tests
- Chi tiết deploy: xem `DEPLOYMENT.md`
