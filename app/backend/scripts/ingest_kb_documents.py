"""
Script: ingest เอกสารทางการ VAT เข้า Vector Store และ SQLite (kb_articles)
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md Phase 1, ส่วนที่ 4 (Agent 3 A5), 14.6, 14.8
"""
import os
import sys
import json
from pathlib import Path
from sqlalchemy import text

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.models import KbArticle, gen_uuid
from app.core.config import settings
from app.core.embeddings import get_embedding


def log_msg(msg: str):
    log_file = BASE_DIR / "ingest.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        f.flush()
    try:
        print(msg)
    except Exception:
        pass


def ingest():
    log_file = BASE_DIR / "ingest.log"
    if log_file.exists():
        log_file.unlink()

    log_msg("Starting ingestion of official VAT documents...")
    json_path = BASE_DIR / "data" / "official_vat_articles.json"
    if not json_path.exists():
        log_msg(f"Error: {json_path} not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    log_msg(f"Found {len(articles)} official VAT articles to ingest.")

    # 1. Connect to SQLite and ensure schema
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Ensure embedding column exists in SQLite
    try:
        db.execute(text("ALTER TABLE kb_articles ADD COLUMN embedding JSON"))
        db.commit()
    except Exception:
        db.rollback()

    vector_store = []
    ingested_count = 0

    for idx, item in enumerate(articles, 1):
        title = item["title"]
        source_section = item["source_section"]
        content = item["content"]

        log_msg(f"[{idx}/{len(articles)}] Processing: [{source_section}] {title}...")

        # Calculate embedding
        emb = get_embedding(content)

        existing = db.query(KbArticle).filter(KbArticle.source_section == source_section).first()
        if existing:
            article_id = existing.id
            existing.title = title
            existing.content = content
            existing.status = "approved"
            existing.source = "official"
            existing.embedding = emb
            existing.chroma_vector_id = article_id
        else:
            article_id = gen_uuid()
            new_article = KbArticle(
                id=article_id,
                title=title,
                content=content,
                source_section=source_section,
                source="official",
                status="approved",
                embedding=emb,
                chroma_vector_id=article_id,
            )
            db.add(new_article)

        vector_store.append({
            "id": article_id,
            "title": title,
            "source_section": source_section,
            "content": content,
            "embedding": emb,
            "status": "approved",
            "source": "official",
        })
        ingested_count += 1
        log_msg(f"  -> Vector computed ({len(emb)} dims) and saved.")

    db.commit()
    db.close()

    # Save vector index to persistence directory
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    vector_file = persist_dir / "vat_kb_collection.json"
    with open(vector_file, "w", encoding="utf-8") as f:
        json.dump(vector_store, f, ensure_ascii=False, indent=2)

    log_msg(f"\nSuccessfully ingested {ingested_count} articles!")
    log_msg(f"SQLite DB: {settings.database_url}")
    log_msg(f"Vector Store Persisted: {vector_file}")


if __name__ == "__main__":
    import traceback
    try:
        ingest()
    except Exception as e:
        log_msg(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        sys.exit(1)
