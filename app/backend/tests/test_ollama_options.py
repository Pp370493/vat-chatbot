from app.core import ollama_client
from app.core.config import settings


def test_num_thread_omitted_by_default(monkeypatch):
    monkeypatch.setattr(settings, "ollama_num_thread", 0)
    opts = ollama_client._build_options(0.2, 2048, 400)
    assert "num_thread" not in opts
    assert opts == {"temperature": 0.2, "num_ctx": 2048, "num_predict": 400}


def test_num_thread_passed_when_set(monkeypatch):
    monkeypatch.setattr(settings, "ollama_num_thread", 4)
    assert ollama_client._build_options(0.2, 2048, 400)["num_thread"] == 4


def test_call_ollama_sends_options(monkeypatch):
    monkeypatch.setattr(settings, "ollama_num_thread", 0)
    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "ok"}

    def fake_post(url, json, timeout):
        sent.update(json)
        return Resp()

    monkeypatch.setattr(ollama_client.httpx, "post", fake_post)
    assert ollama_client._call_ollama("http://x", "p", "m", 0.1, 1024, 50) == "ok"
    assert "num_thread" not in sent["options"]
