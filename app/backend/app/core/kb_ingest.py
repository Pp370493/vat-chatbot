"""
นำตัวบท (chunks) เข้าฐานข้อมูลพร้อม embedding — ใช้โดย scripts/setup_db.py และ scripts/bench_pipeline.py
ต้องเปิด Ollama และมีโมเดล EMBEDDING_MODEL (ค่าเริ่ม nomic-embed-text)
"""
import json
import time
from pathlib import Path

from app.core.embeddings import get_embedding
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.models import KbArticle

DEFAULT_ARTICLES = Path(__file__).resolve().parent.parent.parent / "data" / "official_vat_articles.json"


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
