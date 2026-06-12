"""
Smoke tests — verify toàn bộ production requirements không cần Docker/Redis thật.

Chạy:  pip install pytest fakeredis httpx && pytest tests/ -v
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import redis_client
from app.config import settings
from app.main import app

API_KEY = settings.AGENT_API_KEY
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Thay Redis thật bằng fakeredis cho test."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_client, "_client", fake)
    yield fake


@pytest.fixture
def client():
    with TestClient(app) as c:  # with → chạy lifespan (build BM25 index)
        yield c


# --------------------------------------------------------------------------
# Probes
# --------------------------------------------------------------------------

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ready(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready"}


# --------------------------------------------------------------------------
# Security layer 1: Authentication
# --------------------------------------------------------------------------

def test_ask_without_key_returns_401(client):
    res = client.post("/ask", json={"user_id": "u1", "question": "Hello"})
    assert res.status_code == 401


def test_ask_with_wrong_key_returns_401(client):
    res = client.post(
        "/ask",
        headers={"X-API-Key": "wrong-key"},
        json={"user_id": "u1", "question": "Hello"},
    )
    assert res.status_code == 401


# --------------------------------------------------------------------------
# Functional: RAG answer + citation + history
# --------------------------------------------------------------------------

def test_ask_returns_answer_with_sources(client):
    res = client.post(
        "/ask",
        headers=HEADERS,
        json={"user_id": "u1", "question": "Tội tàng trữ trái phép chất ma túy bị phạt thế nào?"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["answer"]
    assert len(body["sources"]) > 0
    assert body["request_cost_usd"] > 0
    assert "source" in body["sources"][0]


def test_conversation_history_persists_in_redis(client, fake_redis):
    client.post("/ask", headers=HEADERS, json={"user_id": "u2", "question": "Luật phòng chống ma túy"})
    res = client.post("/ask", headers=HEADERS, json={"user_id": "u2", "question": "Nghị định 105"})
    assert res.json()["history_turns"] == 2
    assert fake_redis.llen("history:u2") == 4  # 2 turns x (user + assistant)


# --------------------------------------------------------------------------
# Security layer 2: Rate limiting (429)
# --------------------------------------------------------------------------

def test_rate_limit_returns_429(client):
    limit = settings.RATE_LIMIT_PER_MINUTE
    statuses = []
    for i in range(limit + 3):
        res = client.post(
            "/ask", headers=HEADERS,
            json={"user_id": "rate-user", "question": f"q{i}"},
        )
        statuses.append(res.status_code)
    assert statuses.count(200) == limit
    assert 429 in statuses


# --------------------------------------------------------------------------
# Security layer 3: Cost guard (402)
# --------------------------------------------------------------------------

def test_cost_guard_returns_402(client, fake_redis):
    from app.cost_guard import _month_key

    # Giả lập user đã tiêu hết budget tháng này
    fake_redis.set(_month_key("rich-user"), settings.MONTHLY_BUDGET_USD + 1)
    res = client.post(
        "/ask", headers=HEADERS,
        json={"user_id": "rich-user", "question": "Hello"},
    )
    assert res.status_code == 402


# --------------------------------------------------------------------------
# Stateless design
# --------------------------------------------------------------------------

def test_no_inmemory_conversation_state():
    """State phải nằm trong Redis — không có dict conversation nào trong module."""
    import app.main as main_module

    for name in dir(main_module):
        obj = getattr(main_module, name)
        assert not (isinstance(obj, dict) and "history" in name.lower()), \
            f"In-memory state detected: {name}"
