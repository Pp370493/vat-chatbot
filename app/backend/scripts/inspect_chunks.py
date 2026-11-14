import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
data_path = BASE / "data" / "official_vat_articles.json"
with open(data_path, "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total: {len(items)}")
for it in items:
    cid = it["id"]
    sec = it.get("source_section", "")
    aref = it.get("metadata", {}).get("article_ref", "")
    title = it.get("title", "")
    print(f"{cid} | {sec} | {aref} | {title[:35]}")
