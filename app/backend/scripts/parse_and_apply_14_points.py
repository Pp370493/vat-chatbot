"""
Parse 14 points from user prompt and apply them to:
1. c:\\Users\\Windows\\.gemini\\antigravity\\scratch\\chunking ประกาศ\\*.json
2. backend/data/official_vat_articles.json
"""
import re
import os
import glob
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRATCH_DIR = Path(r"c:\Users\Windows\.gemini\antigravity\scratch\chunking ประกาศ")
ARTICLES_JSON = BASE_DIR / "data" / "official_vat_articles.json"
USER_PROMPT_TXT = BASE_DIR / "scripts" / "user_prompt_14_points.txt"

# Mapping each of the 14 points to specific chunk IDs
CHUNK_MAPPING = {
    1: [
        "VAT57_ART_01",
        "VAT159_ART_02",
        "VAT234_ART_02"
    ],
    2: [
        "VAT159_ART_01",
        "VAT246_ART_01",
        "VAT57_ART_04_1",
        "VAT245_ART_01"
    ],
    3: [
        "VAT57_ART_02",
        "VAT159_ART_03"
    ],
    4: [
        "VAT57_ART_03",
        "VAT159_ART_04",
        "VAT234_ART_03"
    ],
    5: [
        "VAT57_ART_04",
        "VAT74_ART_04",
        "VAT139_ART_01",
        "VAT165_ART_01"
    ],
    6: [
        "VAT57_ART_05_A",
        "VAT74_ART_05_A",
        "VAT165_ART_02_A",
        "VAT215_ART_01",
        "VAT159_ART_05_A",
        "VAT214_ART_01_A",
        "VAT246_ART_02_A"
    ],
    7: [
        "VAT57_ART_05_B",
        "VAT74_ART_05_B",
        "VAT165_ART_02_B",
        "VAT159_ART_05_B",
        "VAT214_ART_01_B",
        "VAT246_ART_02_B"
    ],
    8: [
        "VAT57_ART_05_C",
        "VAT74_ART_05_C",
        "VAT165_ART_02_C",
        "VAT215_ART_02",
        "VAT159_ART_05_C",
        "VAT214_ART_02",
        "VAT246_ART_03"
    ],
    9: [
        "VAT159_ART_05_1",
        "VAT246_ART_04"
    ],
    10: [
        "VAT57_ART_06",
        "VAT74_ART_06",
        "VAT159_ART_06",
        "VAT214_ART_03",
        "VAT246_ART_04_1",
        "VAT234_ART_04"
    ],
    11: [
        "VAT57_ART_07",
        "VAT74_ART_07",
        "VAT159_ART_07",
        "VAT234_ART_01"
    ],
    12: [
        "VAT57_ART_08",
        "VAT74_ART_08",
        "VAT159_ART_08",
        "VAT214_ART_03_1",
        "VAT234_ART_05"
    ],
    13: [
        "VAT57_ART_09",
        "VAT74_ART_09",
        "VAT139_ART_02",
        "VAT165_ART_03",
        "VAT159_ART_09",
        "VAT214_ART_04",
        "VAT245_ART_02",
        "VAT246_ART_05"
    ],
    14: [
        "VAT57_ART_10",
        "VAT74_ART_10",
        "VAT159_ART_10"
    ]
}


def load_parsed_points():
    with open(USER_PROMPT_TXT, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = r"\|\s*\*\*(\d+)\.\s*(.*?)\*\*\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
    matches = re.findall(pattern, text)
    print(f"Loaded {len(matches)} rows from user prompt.")

    parsed_points = []
    for m in matches:
        num = int(m[0])
        rule_title = m[1].strip()
        legal_text = m[2].strip()
        slang_raw = m[3].strip()
        questions_raw = m[4].strip()

        # Parse slang keywords
        kws = [k.strip() for k in slang_raw.split(",") if k.strip()]

        # Parse questions
        raw_qs = questions_raw.split("<br>")
        qs = []
        for q in raw_qs:
            cleaned = re.sub(r"^\d+\.\s*", "", q).strip()
            if cleaned:
                qs.append(cleaned)

        parsed_points.append({
            "point": num,
            "title": rule_title,
            "legal_text": legal_text,
            "keywords": kws,
            "intents": qs,
            "chunks": CHUNK_MAPPING.get(num, [])
        })
    return parsed_points


def update_scratch_json_files(points):
    print("\n=== Updating Scratch Chunk Files ===")
    chunk_to_points = {}
    for p in points:
        for cid in p["chunks"]:
            if cid not in chunk_to_points:
                chunk_to_points[cid] = []
            chunk_to_points[cid].append(p)

    source_files = sorted(glob.glob(str(SCRATCH_DIR / "vat*_chunks_local_llm.json")))
    total_updated = 0

    for fpath in source_files:
        with open(fpath, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not isinstance(chunks, list):
            continue

        file_changed = False
        for chunk in chunks:
            cid = chunk.get("chunk_id")
            if cid in chunk_to_points:
                meta = chunk.setdefault("metadata", {})
                b_kws = meta.setdefault("boost_keywords", [])
                u_int = meta.setdefault("user_intents", [])

                for p in chunk_to_points[cid]:
                    for kw in p["keywords"]:
                        if kw not in b_kws:
                            b_kws.append(kw)
                    for intent in p["intents"]:
                        if intent not in u_int:
                            u_int.append(intent)

                file_changed = True
                total_updated += 1

        if file_changed:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            print(f"  [OK] Updated: {Path(fpath).name}")

    print(f"Total chunk instances updated in scratch: {total_updated}")


def update_official_vat_articles(points):
    print("\n=== Updating backend/data/official_vat_articles.json ===")
    with open(ARTICLES_JSON, "r", encoding="utf-8") as f:
        articles = json.load(f)

    chunk_to_points = {}
    for p in points:
        for cid in p["chunks"]:
            if cid not in chunk_to_points:
                chunk_to_points[cid] = []
            chunk_to_points[cid].append(p)

    updated_count = 0
    for art in articles:
        cid = art["id"]
        if cid in chunk_to_points:
            meta = art.setdefault("metadata", {})
            b_kws = meta.setdefault("boost_keywords", [])
            u_int = meta.setdefault("user_intents", [])

            for p in chunk_to_points[cid]:
                for kw in p["keywords"]:
                    if kw not in b_kws:
                        b_kws.append(kw)
                for intent in p["intents"]:
                    if intent not in u_int:
                        u_int.append(intent)
            updated_count += 1

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Updated metadata for {updated_count} chunks in official_vat_articles.json")


if __name__ == "__main__":
    points = load_parsed_points()
    update_scratch_json_files(points)
    update_official_vat_articles(points)
    print("\n[SUCCESS] Metadata and synonym bank successfully updated across all layers!")
