"""
นำตัวบท (chunks) เข้าฐานข้อมูลพร้อม embedding — ใช้โดย scripts/setup_db.py และ scripts/bench_pipeline.py
ต้องเปิด Ollama และมีโมเดล EMBEDDING_MODEL (ค่าเริ่ม nomic-embed-text)
"""
import json
import time
from pathlib import Path

import httpx

from app.core.embeddings import get_embedding
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.models import KbArticle

DEFAULT_ARTICLES = Path(__file__).resolve().parent.parent.parent / "data" / "official_vat_articles.json"


def check_ollama(base_url: str, model: str, timeout: float = 3.0) -> str | None:
    """ตรวจว่า Ollama เปิดอยู่และมีโมเดล embedding — คืนข้อความแนะนำภาษาไทยถ้าไม่พร้อม, None ถ้าพร้อม"""
    base_url = (base_url or "http://localhost:11434").rstrip("/")
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=timeout)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return (f"เชื่อมต่อ Ollama ที่ {base_url} ไม่ได้ — เปิดโปรแกรม Ollama จากเมนู Start "
                f"(หรือเปิดหน้าต่างใหม่แล้วสั่ง ollama serve ทิ้งไว้) แล้วรันคำสั่งนี้ใหม่")
    base = model.split(":")[0]
    if not any(n == model or n.split(":")[0] == base for n in names):
        return f"Ollama ยังไม่มีโมเดล {model} — สั่ง ollama pull {model} แล้วรันคำสั่งนี้ใหม่"
    return None


def ingest_articles(path: Path = DEFAULT_ARTICLES, embed=get_embedding, log=print) -> int:
    """ล้างตัวบทเดิมแล้วใส่ใหม่ทั้งหมดจากไฟล์ JSON คืนจำนวน chunk ที่นำเข้า"""
    Base.metadata.create_all(bind=engine)
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        t = time.perf_counter()
        rows = []
        for i, it in enumerate(items, 1):
            rows.append(KbArticle(
                id=it["id"], title=it["title"], content=it["content"], source_section=it["source_section"],
                status="approved", source="official", chroma_vector_id=it["id"],
                embedding=embed(it["embedding_input"], is_query=False),
            ))
            if i % 25 == 0:
                log(f"  embedding {i}/{len(items)}")
        db.query(KbArticle).delete()
        db.add_all(rows)
        db.commit()
        log(f"ingest {len(rows)} chunks: {time.perf_counter() - t:.1f}s")
        return len(rows)
    finally:
        db.close()
