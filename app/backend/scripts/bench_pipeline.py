"""
วัดเวลาและความถูกต้องของ run_pipeline กับโมเดลจริงบน Ollama (ใช้ได้ทั้งเครื่องทดสอบและโน้ตบุ๊กจริง)

    python scripts/bench_pipeline.py --db bench.db --ingest --per-group 12,6,6 --out bench.csv

- --ingest: ทำ embedding ของ chunk ทั้ง 75 ชิ้นใน data/official_vat_articles.json ด้วย EMBEDDING_MODEL ลง DB ที่ระบุ
- เลือกคำถามจาก data/synthetic_dataset_vat_intent.csv แบบแบ่งกลุ่ม (ปกติ, เสี่ยง ข้อ 6, นอกสโคป) สุ่มด้วย seed คงที่
- ถ้าระบบถามช่องทางยื่นก่อน (clarification) จะตอบ "ยื่นแบบกระดาษที่สำนักงานสรรพากรพื้นที่" ในบทสนทนาเดียวกันแล้ววัดต่อ
- บันทึกต่อข้อ: เวลารวม, เวลาที่ใช้ใน LLM แยกตาม agent, จำนวนครั้งที่เรียก embedding, ประเภทผลลัพธ์เทียบกับที่ควรเป็น
ต้องตั้ง DATABASE_URL ก่อน import app.* — สคริปต์จึงอ่าน --db แล้วตั้ง env เองก่อน import
"""
import argparse
import csv
import inspect
import json
import os
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXPECTED = {"IN_SCOPE_VAT": "answer", "HIGH_RISK_SECTION_6": "pending_review", "OUT_OF_SCOPE": "redirect"}
GROUP_ORDER = ["IN_SCOPE_VAT", "HIGH_RISK_SECTION_6", "OUT_OF_SCOPE"]
CHANNEL_REPLY = "ยื่นแบบกระดาษที่สำนักงานสรรพากรพื้นที่"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(BASE_DIR / "bench.db"))
    p.add_argument("--ingest", action="store_true")
    p.add_argument("--per-group", default="12,6,6", help="จำนวนคำถาม ปกติ,เสี่ยง,นอกสโคป")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default=str(BASE_DIR / "bench_pipeline.csv"))
    return p.parse_args()


args = parse_args()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(args.db).resolve()}"
os.environ.setdefault("USE_MOCK_LLM", "false")
sys.path.insert(0, str(BASE_DIR))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.core import embeddings, ollama_client  # noqa: E402
from app.core.config import settings  # noqa: E402

# ---- ตัวจับเวลา: ห่อ generate / get_embedding ในทุกโมดูลที่ import ไปใช้
STATS = defaultdict(float)


def _caller():
    for fr in inspect.stack()[2:]:
        mod = fr.frame.f_globals.get("__name__", "")
        if mod.startswith("app.agents.") or mod.startswith("app.graph."):
            return mod.rsplit(".", 1)[-1].split("_")[0]
    return "other"


_orig_generate, _orig_embed = ollama_client.generate, embeddings.get_embedding


def timed_generate(*a, **kw):
    who, t = _caller(), time.perf_counter()
    try:
        return _orig_generate(*a, **kw)
    finally:
        STATS[f"llm_{who}_s"] += time.perf_counter() - t
        STATS[f"llm_{who}_n"] += 1


def timed_embed(*a, **kw):
    t = time.perf_counter()
    try:
        return _orig_embed(*a, **kw)
    finally:
        STATS["embed_s"] += time.perf_counter() - t
        STATS["embed_n"] += 1


import app.agents as _agents_pkg  # noqa: E402,F401
from app.graph import pipeline_graph  # noqa: E402

for name, mod in list(sys.modules.items()):
    if name.startswith(("app.agents.", "app.graph.")):
        if getattr(mod, "generate", None) is _orig_generate:
            mod.generate = timed_generate
        if getattr(mod, "get_embedding", None) is _orig_embed:
            mod.get_embedding = timed_embed


def ingest():
    from app.core.kb_ingest import ingest_articles
    print(f"embedding model: {settings.embedding_model}", flush=True)
    ingest_articles(embed=_orig_embed)


def pick_questions():
    rows = list(csv.DictReader(open(BASE_DIR / "data" / "synthetic_dataset_vat_intent.csv", encoding="utf-8-sig")))
    rnd = random.Random(args.seed)
    picked = []
    for group, n in zip(GROUP_ORDER, map(int, args.per_group.split(","))):
        pool = [r for r in rows if r["group"] == group]
        picked += rnd.sample(pool, min(n, len(pool)))
    return picked


def run_one(row, idx):
    STATS.clear()
    t0 = time.perf_counter()
    res = pipeline_graph.run_pipeline(row["query"], session_id=f"bench-{idx}")
    first_type = res["type"]
    clar = res.get("payload", {}).get("clarification_type", "") if first_type == "clarification" else ""
    if first_type == "clarification" and clar != "purpose":
        res = pipeline_graph.run_pipeline(CHANNEL_REPLY, session_id=f"bench-{idx}", conversation_id=res["conversation_id"])
    total = time.perf_counter() - t0
    payload = res.get("payload", {})
    rec = {
        "id": row["id"], "group": row["group"], "query": row["query"],
        "expected": EXPECTED[row["group"]], "first_type": first_type, "final_type": res["type"],
        "clarification": clar or ("channel" if first_type == "clarification" else ""),
        "correct": res["type"] == EXPECTED[row["group"]],
        "tier": payload.get("tier", ""), "trust": payload.get("trust_score", ""),
        "total_s": round(total, 2),
        "answer": (payload.get("draft_text") or payload.get("redirect_message") or "")[:800],
        "risk_factors": "; ".join(payload.get("risk_factors", []) or []),
    }
    rec.update({k: round(v, 2) if k.endswith("_s") else int(v) for k, v in STATS.items()})
    return rec


# RAM: อ่าน rss ของ cgroup จำลอง (ไม่นับ page cache ซึ่งระบบคืนได้) ทุก 0.5 วินาที — บนเครื่องอื่นจะเป็น n/a
_CG = Path("/sys/fs/cgroup/memory/laptop8g")
_RSS_PEAK = [0]


def _sample_rss():
    while True:
        for line in (_CG / "memory.stat").read_text().splitlines():
            if line.startswith("total_rss "):
                _RSS_PEAK[0] = max(_RSS_PEAK[0], int(line.split()[1]))
        time.sleep(0.5)


def mem_peak():
    if not _CG.exists():
        return "n/a"
    return (f"rss {_RSS_PEAK[0] / 2**30:.2f} GB, รวม page cache "
            f"{int((_CG / 'memory.max_usage_in_bytes').read_text()) / 2**30:.2f} GB (เพดาน "
            f"{int((_CG / 'memory.limit_in_bytes').read_text()) / 2**30:.2f} GB)")


def main():
    print(f"model={settings.ollama_model_default} embed={settings.embedding_model} num_thread={settings.ollama_num_thread or 'auto'}")
    if _CG.exists():
        import threading
        threading.Thread(target=_sample_rss, daemon=True).start()
    if args.ingest:
        ingest()
    qs = pick_questions()
    recs = []
    for i, row in enumerate(qs, 1):
        try:
            rec = run_one(row, i)
        except Exception as e:  # บันทึกความล้มเหลว (เช่น timeout) แล้วไปข้อต่อไป
            rec = {"id": row["id"], "group": row["group"], "query": row["query"], "expected": EXPECTED[row["group"]],
                   "final_type": f"ERROR {type(e).__name__}: {e}"[:200], "correct": False}
        recs.append(rec)
        print(f"[{i}/{len(qs)}] {rec['id']} {rec.get('final_type')} ({'✓' if rec['correct'] else '✗'}) "
              f"{rec.get('total_s', '-')}s  {row['query'][:50]}", flush=True)

    keys = sorted({k for r in recs for k in r}, key=lambda k: (k not in recs[0], k))
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(recs)

    print("\n=== สรุป ===")
    for g in GROUP_ORDER:
        rs = [r for r in recs if r["group"] == g]
        ts = sorted(r["total_s"] for r in rs if "total_s" in r)
        if not rs:
            continue
        p90 = ts[min(len(ts) - 1, int(round(0.9 * (len(ts) - 1))))] if ts else 0
        print(f"{g}: ถูก {sum(r['correct'] for r in rs)}/{len(rs)}  เวลา median {statistics.median(ts) if ts else 0:.1f}s "
              f"p90 {p90:.1f}s  max {max(ts) if ts else 0:.1f}s")
    print(f"RAM สูงสุด (cgroup): {mem_peak()}   ผลละเอียด: {args.out}")


if __name__ == "__main__":
    main()
