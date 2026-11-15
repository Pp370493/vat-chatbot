import socket

import httpx

from app.core import kb_ingest


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_ollama_down_returns_thai_hint():
    msg = kb_ingest.check_ollama(f"http://127.0.0.1:{_free_port()}", "nomic-embed-text", timeout=1)
    assert msg and "เปิดโปรแกรม Ollama" in msg


def _fake_tags(monkeypatch, names):
    req = httpx.Request("GET", "http://x/api/tags")
    monkeypatch.setattr(kb_ingest.httpx, "get",
                        lambda *a, **k: httpx.Response(200, json={"models": [{"name": n} for n in names]}, request=req))


def test_missing_model(monkeypatch):
    _fake_tags(monkeypatch, ["qwen2.5:3b-instruct"])
    assert "ollama pull nomic-embed-text" in kb_ingest.check_ollama("http://x", "nomic-embed-text")


def test_ready(monkeypatch):
    _fake_tags(monkeypatch, ["qwen2.5:3b-instruct", "nomic-embed-text:latest"])
    assert kb_ingest.check_ollama("http://x", "nomic-embed-text") is None
