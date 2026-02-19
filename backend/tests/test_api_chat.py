# backend/tests/test_api_chat.py
"""Tests for chat SSE endpoint — uses TestClient, no real LLM."""
from fastapi.testclient import TestClient


def test_health_endpoint():
    from app import app
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


def test_chat_endpoint_returns_error_without_llm():
    from app import app
    with TestClient(app) as client:
        # Create a session via the agent_manager attached during lifespan
        agent_manager = app.state.agent_manager
        sid = agent_manager.session_manager.create_session()

        resp = client.post("/api/chat", json={
            "message": "hello",
            "session_id": sid,
            "stream": False,
        })
        # LLM is not initialized in test env -> 503
        assert resp.status_code == 503


def test_chat_request_model():
    from api.chat import ChatRequest
    req = ChatRequest(message="hello", session_id="test123")
    assert req.message == "hello"
    assert req.stream is True  # default
