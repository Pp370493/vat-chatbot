"""
Sync Metadata & Synonyms from Scratch Chunking Files to backend/data/official_vat_articles.json
ใช้สำหรับอัปเดตคำค้นทางเลือก (Synonyms / Boost Keywords) เข้าสู่ระบบ RAG ได้ทันทีใน 1 วินาที โดยไม่ต้อง Re-embed ใหม่
"""
import os
import glob
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRATCH_DIR = Path(r"c:\Users\Windows\.gemini\antigravity\scratch\chunking ประกาศ")
ARTICLES_JSON = BASE_DIR / "data" / "official_vat_articles.json"


def sync_metadata():
    if not ARTICLES_JSON.exists():
        print(f"[ERROR] Target file not found: {ARTICLES_JSON}")
        return

    with open(ARTICLES_JSON, "r", encoding="utf-8") as f:
        articles = json.load(f)

    art_dict = {a["id"]: a for a in articles}

    source_files = sorted(glob.glob(str(SCRATCH_DIR / "vat*.json")))
    updated_count = 0

    for fpath in source_files:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        for chunk in chunks:
            cid = chunk.get("chunk_id")
            if cid in art_dict:
                src_meta = chunk.get("metadata", {})
                target_meta = art_dict[cid].get("metadata", {})

                # Sync boost_keywords, tfidf_keywords, user_intents
                target_meta["boost_keywords"] = src_meta.get("boost_keywords", [])
                target_meta["tfidf_keywords"] = src_meta.get("tfidf_keywords", [])
                target_meta["user_intents"] = src_meta.get("user_intents", [])
                art_dict[cid]["metadata"] = target_meta
                updated_count += 1

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] Synced metadata for {updated_count} chunks from {len(source_files)} files into {ARTICLES_JSON.name}")


if __name__ == "__main__":
    sync_metadata()
