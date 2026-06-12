#  Delivery Checklist — Day 12 Lab Submission

> **Student Name:** Đặng Thị Thu Thảo
> **Student ID:** 2A202600685
> **Date:** 12/06/2026

---

##  Submission Requirements

Submit a **GitHub repository** containing:

### 1. Mission Answers (40 points)

> ✅ **Đã hoàn thành** — xem [MISSION_ANSWERS.md](MISSION_ANSWERS.md): đủ Part 1-5 (8 anti-patterns, bảng so sánh dev/prod, Dockerfile + multi-stage, Railway/Render, kết quả test 401/200/429, cost guard, health checks, graceful shutdown, stateless, load balancing).

Template gốc của đề (để đối chiếu):

```markdown
# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. [Your answer]
2. [Your answer]
...

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config  | ...     | ...        | ...            |
...

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: [Your answer]
2. Working directory: [Your answer]
...

### Exercise 2.3: Image size comparison
- Develop: [X] MB
- Production: [Y] MB
- Difference: [Z]%

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://your-app.railway.app
- Screenshot: [Link to screenshot in repo]

## Part 4: API Security

### Exercise 4.1-4.3: Test results
[Paste your test outputs]

### Exercise 4.4: Cost guard implementation
[Explain your approach]

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
[Your explanations and test results]
```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

> ✅ **Đã hoàn thành** — toàn bộ source trong [`06-lab-complete/`](06-lab-complete/): production-hóa **Day 8 RAG agent** (hỏi đáp pháp luật ma túy VN, BM25 retrieval + generation có citation). Cấu trúc khớp yêu cầu, bổ sung thêm `app/history.py`, `app/logging_config.py`, `app/rag/`, `app/static/` (chat UI), `tests/`, `nginx/`, `conftest.py`.

Your final production-ready agent with all files:

```
your-repo/
├── app/
│   ├── main.py              # Main application
│   ├── config.py            # Configuration
│   ├── auth.py              # Authentication
│   ├── rate_limiter.py      # Rate limiting
│   └── cost_guard.py        # Cost protection
├── utils/
│   └── mock_llm.py          # Mock LLM (provided)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── .dockerignore            # Docker ignore
├── railway.toml             # Railway config (or render.yaml)
└── README.md                # Setup instructions
```

**Requirements:**

- [x] All code runs without errors (10/10 unit tests pass, CI xanh)
- [x] Multi-stage Dockerfile (image < 500 MB — CI tự verify mỗi lần build)
- [x] API key authentication (`app/auth.py`, 401, constant-time compare)
- [x] Rate limiting 10 req/min (`app/rate_limiter.py`, sliding window Redis, 429)
- [x] Cost guard $10/month (`app/cost_guard.py`, key theo tháng trong Redis, 402)
- [x] Health + readiness checks (`/health`, `/ready` có ping Redis)
- [x] Graceful shutdown (lifespan + uvicorn SIGTERM, drain in-flight requests)
- [x] Stateless design (history/rate/budget 100% trong Redis)
- [x] No hardcoded secrets (pydantic-settings + env vars, `.env` gitignored)

---

### 3. Service Domain Link

> ✅ **Đã hoàn thành** — xem [DEPLOYMENT.md](DEPLOYMENT.md).
> **Public URL:** https://day12-2a202600685-dangthithuthao-production.up.railway.app (Railway + Redis, chat UI tại `/`)
> **Docker image:** `ghcr.io/tanniiee/day12-2a20260065-dangthithuthao:latest` (CI/CD tự push)

Template gốc của đề (để đối chiếu):

```markdown
# Deployment Information

## Public URL
https://your-agent.railway.app

## Platform
Railway / Render / Cloud Run

## Test Commands

### Health Check
```bash
curl https://your-agent.railway.app/health
# Expected: {"status": "ok"}
```

### API Test (with authentication)
```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables Set
- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
```

##  Pre-Submission Checklist

- [x] Repository is public (or instructor has access)
- [x] `MISSION_ANSWERS.md` completed with all exercises (Part 1-5 + ghi chú Part 6)
- [x] `DEPLOYMENT.md` has working public URL — https://day12-2a202600685-dangthithuthao-production.up.railway.app
- [x] All source code in `06-lab-complete/app/` directory (Final Project = production-hóa Day 8 RAG agent)
- [x] `README.md` has clear setup instructions (`06-lab-complete/README.md`)
- [x] No `.env` file committed (only `.env.example`; `.env` trong `.gitignore`)
- [x] No hardcoded secrets in code (config qua pydantic-settings + env vars)
- [x] Public URL is accessible and working (chat UI tại `/`, API `/ask`, probes `/health` `/ready`)
- [x] Screenshots included in `screenshots/` folder
- [x] Repository has clear commit history

**Bonus ngoài yêu cầu đề:**

- [x] CI/CD: GitHub Actions tự test → build → push image lên GHCR (`.github/workflows/docker-publish.yml`) + verify image < 500 MB
- [x] Chat UI tích hợp tại `/` (tương tác trực tiếp trên trình duyệt)
- [x] 10 unit tests (`06-lab-complete/tests/`) — auth 401, rate limit 429, cost guard 402, stateless, UI
- [x] Script self-test public URL: `selftest.sh`

---

##  Self-Test

> ✅ **Đã chạy** bằng script [`selftest.sh`](selftest.sh) trên public URL — kết quả: `/health` 200, `/ready` 200, không key → 401, có key → 200 (answer + citation), 15 calls liên tục → 200 rồi 429. Bằng chứng: `screenshots/test-results.png`.

```bash
URL=https://day12-2a202600685-dangthithuthao-production.up.railway.app

# 1. Health check
curl $URL/health
# {"status":"ok"}

# 2. Authentication required
curl -X POST $URL/ask -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# → 401

# 3. With API key works
curl -X POST $URL/ask -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# → 200

# 4. Rate limiting
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST $URL/ask \
    -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
    -d '{"user_id":"test","question":"test"}'
done
# → 200 x10 rồi 429

# Hoặc chạy tất cả một lần:  bash selftest.sh <AGENT_API_KEY>
```

---

##  Submission

**Submit your GitHub repository URL:**

```
https://github.com/Tanniiee/Day12-2A202600685-DangThiThuThao
```

**Deadline:** 17/4/2026

---

##  Quick Tips

1.  Test your public URL from a different device
2.  Make sure repository is public or instructor has access
3.  Include screenshots of working deployment
4.  Write clear commit messages
5.  Test all commands in DEPLOYMENT.md work
6.  No secrets in code or commit history

---

##  Need Help?

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review [CODE_LAB.md](CODE_LAB.md)
- Ask in office hours
- Post in discussion forum

---

**Good luck! **
