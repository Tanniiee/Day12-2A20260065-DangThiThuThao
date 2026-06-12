# =============================================================================
# Multi-stage build — Day 12 production pattern
#
# Stage 1 (builder): cài dependencies (cần build tools, cache pip...)
# Stage 2 (runtime): chỉ copy kết quả đã cài → image nhỏ, ít attack surface
# =============================================================================

# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# COPY requirements.txt TRƯỚC code → tận dụng Docker layer cache:
# code đổi nhưng deps không đổi → không phải pip install lại
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim

# Chạy bằng non-root user (security best practice)
RUN useradd --create-home --shell /usr/sbin/nologin agent

WORKDIR /app

# Chỉ copy site-packages đã cài từ builder (không mang theo pip cache/build tools)
COPY --from=builder /install /usr/local

# Copy code + data (corpus pháp luật/báo chí của Day 8)
COPY app ./app
COPY data ./data

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

USER agent

EXPOSE 8000

# Docker-level liveness check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",8000)}/health')" || exit 1

# sh -c để đọc được $PORT do platform (Railway/Render) inject
# uvicorn tự xử lý SIGTERM → graceful shutdown (drain in-flight requests)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
