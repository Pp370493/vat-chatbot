"""
Config กลางของระบบ โหลดจาก .env
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 3 (Environment Variables)
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # LLM / Ollama
    ollama_base_url_primary: str = ""
    ollama_base_url_fallback: str = "http://localhost:11434"
    ollama_healthcheck_timeout_ms: int = 2000
    ollama_model_default: str = "qwen2.5:3b-instruct"
    embedding_model: str = "nomic-embed-text"
    # จำนวนเธรดที่ส่งให้ Ollama — 0 = ให้ Ollama เลือกเอง (เท่าจำนวนคอร์จริง)
    # ห้ามตั้งเกินจำนวนคอร์ของเครื่อง: บน 4 คอร์ที่ไม่มี SMT การตั้ง 6 ทำให้ช้าลงราว 40 เท่า
    ollama_num_thread: int = 0

    # Database
    database_url: str = f"sqlite:///{_BACKEND_DIR / 'vat_copilot.db'}"

    # Auth
    auth_session_expiry_hours: int = 8

    # Risk thresholds (Agent 6)
    risk_threshold_officer: float = 0.6
    risk_threshold_senior: float = 0.35

    # Multi-turn (Agent 3)
    conversation_max_turns: int = 5
    retrieval_top_k: int = 5
    retrieval_top_k_in_prompt: int = 3
    chunk_max_tokens: int = 350
    # ค้นเฉพาะตัวบทหลัก 57/159 (+234 เมื่อระบุ DBD) — ฉบับแก้ไขใช้เป็นที่มาในข้อความอ้างอิง
    retrieval_primary_only: bool = True

    # Dev workflow
    use_mock_llm: bool = False
    chroma_persist_dir: str = str(_BACKEND_DIR / "chroma_data")

    class Config:
        env_file = str(_BACKEND_DIR / ".env")
        extra = "ignore"  # OLLAMA_NUM_PARALLEL ฯลฯ เป็น env ของ Ollama server เอง ไม่ใช่ของแอปนี้


settings = Settings()
