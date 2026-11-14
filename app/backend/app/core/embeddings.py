"""
Module สำหรับสร้าง Embedding เวกเตอร์
ใช้ Ollama embedding API โดยเชื่อมกับ EMBEDDING_MODEL ใน config
รองรับ Task prefix (search_document / search_query) สำหรับ Nomic-embed-text
"""
import httpx
from app.core.config import settings


def get_embedding(text: str, is_query: bool = False) -> list[float]:
    """
    สร้าง Embedding vector ขนาดคงที่สำหรับข้อความภาษาไทย/อังกฤษ
    """
    base_url = settings.ollama_base_url_fallback
    model = settings.embedding_model or "nomic-embed-text"
    
    # Nomic-embed-text แนะนำให้ใส่ prefix เพื่อเพิ่มความแม่นยำในการค้นหา
    if "nomic" in model.lower() and not text.startswith("search_query:") and not text.startswith("search_document:"):
        prefix = "search_query: " if is_query else "search_document: "
        prompt = f"{prefix}{text.strip()}"
    else:
        prompt = text.strip()
    
    # รองรับทั้ง Ollama /api/embed (เวอร์ชันใหม่) และ /api/embeddings (เวอร์ชันเดิม)
    try:
        resp = httpx.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": prompt},
            timeout=60.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            embs = data.get("embeddings", [])
            if embs:
                return embs[0]
    except Exception:
        pass

    resp = httpx.post(
        f"{base_url}/api/embeddings",
        json={"model": model, "prompt": prompt},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json().get("embedding", [])
