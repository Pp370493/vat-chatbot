"""
Wrapper เรียก Ollama พร้อม automatic failover (primary -> fallback)
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 14.9 (Compute Fallback Plan)

USE_MOCK_LLM=true จะคืนค่า canned response ทันที ไม่เรียก Ollama จริง
(สำหรับ dev loop เร็วตาม 14.4)
"""
import httpx
from app.core.config import settings


def _build_options(temperature: float, num_ctx: int, num_predict: int) -> dict:
    options = {"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict}
    # ส่ง num_thread เฉพาะเมื่อตั้งค่าไว้ (OLLAMA_NUM_THREAD) — ไม่งั้นให้ Ollama เลือกตามจำนวนคอร์เอง
    if settings.ollama_num_thread > 0:
        options["num_thread"] = settings.ollama_num_thread
    return options


def _call_ollama(
    base_url: str,
    prompt: str,
    model: str,
    temperature: float,
    num_ctx: int,
    num_predict: int = 400,
) -> str:
    resp = httpx.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": _build_options(temperature, num_ctx, num_predict),
        },
        timeout=300.0,  # ขยาย timeout เป็น 300 วินาที ป้องกัน ReadTimeout บน CPU
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def generate(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.7,
    num_ctx: int = 1536,
    num_predict: int = 400,
    mock_response: str = '{"mock": true}',
) -> dict:
    """
    เรียก LLM พร้อม failover. คืน {"text": str, "served_by": "primary"|"fallback"|"mock"}
    - served_by ใช้บันทึกลง audit_log.event_data ตามที่ตกลงไว้ (14.9)
    """
    model = model or settings.ollama_model_default

    if settings.use_mock_llm:
        return {"text": mock_response, "served_by": "mock"}

    if settings.ollama_base_url_primary:
        try:
            text = _call_ollama(
                settings.ollama_base_url_primary,
                prompt,
                model,
                temperature,
                num_ctx,
                num_predict,
            )
            return {"text": text, "served_by": "primary"}
        except Exception:
            pass  # ตกไป fallback ตาม 14.9

    text = _call_ollama(
        settings.ollama_base_url_fallback,
        prompt,
        model,
        temperature,
        num_ctx,
        num_predict,
    )
    return {"text": text, "served_by": "fallback"}
