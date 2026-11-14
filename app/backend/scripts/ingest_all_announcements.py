import os
import sys
import json
import glob
from pathlib import Path
from sqlalchemy import text

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
    log_file = BASE_DIR / "ingest_75_chunks.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        f.flush()
    try:
        print(msg)
    except Exception:
        pass


def compile_and_ingest():
    log_file = BASE_DIR / "ingest_75_chunks.log"
    if log_file.exists():
        log_file.unlink()

    scratch_dir = Path(r"c:\Users\Windows\.gemini\antigravity\scratch\chunking ประกาศ")
    graph_file = scratch_dir / "graph_rag_vat_registration.json"

    log_msg("=== 1. Loading Knowledge Graph Metadata ===")
    ann_map = {}
    if graph_file.exists():
        with open(graph_file, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        for a in graph_data.get("nodes", {}).get("announcements", []):
            ann_map[a["id"]] = a
        # Also copy graph to backend/data for Agent 3 / Graph RAG routing
        backend_graph_file = BASE_DIR / "data" / "graph_rag_vat_registration.json"
        backend_graph_file.parent.mkdir(parents=True, exist_ok=True)
        with open(backend_graph_file, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        log_msg(f"Saved graph metadata to {backend_graph_file}")

    ann_file_prefix_map = {
        "vat57": "ANN_57",
        "vat74": "ANN_74",
        "vat139": "ANN_139",
        "vat159": "ANN_159",
        "vat165": "ANN_165",
        "vat214": "ANN_214",
        "vat215": "ANN_215",
        "vat234": "ANN_234",
        "vat245": "ANN_245",
        "vat246": "ANN_246",
    }

    log_msg("=== 2. Compiling 75 Chunks across 10 Announcements ===")
    files = sorted(glob.glob(str(scratch_dir / "vat*.json")))
    all_compiled = []

    for fpath in files:
        fname = os.path.basename(fpath)
        prefix = fname.split("_")[0].lower()
        ann_info = ann_map.get(ann_file_prefix_map.get(prefix, ""), {})
        ann_label = ann_info.get("label", f"ประกาศ VAT ({prefix.upper()})")
        ann_official = ann_info.get("official_title", ann_label)
        ann_status = ann_info.get("status", "มีผลบังคับใช้")

        with open(fpath, "r", encoding="utf-8") as fp:
            items = json.load(fp)

        for item in items:
            cid = item.get("chunk_id")
            aref = item.get("article_ref", "")
            title = item.get("title", "")
            content = item.get("llm_context", item.get("official_raw_text", ""))
            raw_text = item.get("official_raw_text", "")
            emb_input = item.get("embedding_input", f"search_document: {title}\n{raw_text}")
            meta = item.get("metadata", {})
            meta["announcement_label"] = ann_label
            meta["announcement_official_title"] = ann_official
            meta["announcement_status"] = ann_status
            meta["article_ref"] = aref
            meta["source_file"] = fname

            source_section = f"{ann_label} {aref}".strip()

            compiled_item = {
                "id": cid,
                "title": title,
                "source_section": source_section,
                "content": content,
                "embedding_input": emb_input,
                "raw_text": raw_text,
                "metadata": meta,
            }
            all_compiled.append(compiled_item)

    log_msg(f"Total compiled articles: {len(all_compiled)}")

    # Save to backend/data/official_vat_articles.json
    articles_json_path = BASE_DIR / "data" / "official_vat_articles.json"
    with open(articles_json_path, "w", encoding="utf-8") as fp:
        json.dump(all_compiled, fp, ensure_ascii=False, indent=2)
    log_msg(f"Saved compiled official VAT articles to {articles_json_path}")

    log_msg("=== 3. Embedding and Ingestion into SQLite & Vector Store ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Ensure embedding column exists
    try:
        db.execute(text("ALTER TABLE kb_articles ADD COLUMN embedding JSON"))
        db.commit()
    except Exception:
        db.rollback()

    vector_store = []
    ingested_count = 0

    for idx, item in enumerate(all_compiled, 1):
        cid = item["id"]
        title = item["title"]
        source_section = item["source_section"]
        content = item["content"]
        emb_input = item["embedding_input"]

        log_msg(f"[{idx}/{len(all_compiled)}] Processing {cid} - {source_section}...")

        # Compute embedding using emb_input
        emb = get_embedding(emb_input, is_query=False)

        existing = db.query(KbArticle).filter(KbArticle.id == cid).first()
        if not existing:
            # Check by source_section
            existing = db.query(KbArticle).filter(KbArticle.source_section == source_section).first()

        if existing:
            existing.title = title
            existing.content = content
            existing.source_section = source_section
            existing.status = "approved"
            existing.source = "official"
            existing.embedding = emb
            existing.chroma_vector_id = cid
            article_id = existing.id
        else:
            article_id = cid
            new_art = KbArticle(
                id=article_id,
                title=title,
                content=content,
                source_section=source_section,
                source="official",
                status="approved",
                embedding=emb,
                chroma_vector_id=cid,
            )
            db.add(new_art)

        vector_store.append({
            "id": article_id,
            "title": title,
            "source_section": source_section,
            "content": content,
            "embedding": emb,
            "status": "approved",
            "source": "official",
            "metadata": item["metadata"],
        })
        ingested_count += 1

    db.commit()
    db.close()

    # Persist vector store
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    vector_file = persist_dir / "vat_kb_collection.json"
    with open(vector_file, "w", encoding="utf-8") as f:
        json.dump(vector_store, f, ensure_ascii=False, indent=2)

    log_msg(f"\nSuccessfully ingested all {ingested_count} chunks into SQLite & Chroma Vector Store!")
    log_msg(f"Persisted to: {vector_file}")


if __name__ == "__main__":
    compile_and_ingest()
