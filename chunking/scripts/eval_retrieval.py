#!/usr/bin/env python3
"""
วัดผล Agent 3 (retrieval) เทียบ 2 โหมด:
  all      — ค้นทั้ง 75 chunks (พฤติกรรมเดิม)
  primary  — หลักการใหม่: ค้นเฉพาะตัวบทหลัก 57/159 (+234 เมื่อระบุ DBD) แล้วแนบฉบับแก้ไขเป็นที่มา

ชุดทดสอบ:
  A) synthetic_dataset_vat_intent.csv — กลุ่ม IN_SCOPE_VAT + HIGH_RISK_SECTION_6 (132 ข้อ)
     เฉลยมาจาก target_clause_or_agency ที่เขียนแยกจาก metadata ของ chunk (ชุดทดสอบหลัก)
  B) metadata.user_intents ของทุก chunk (617 ข้อ) — เขียนคู่กับ boost_keywords
     จึงมีโอกาสได้คะแนนสูงกว่าความจริง (ใช้ดูแนวโน้ม)

นับว่า "ถูก" เมื่อได้ตัวบทหลักของข้อที่เฉลย หรือฉบับแก้ไขของข้อนั้นที่ยังมีผล (is_current)
ตัวชี้วัด: Hit@1, Hit@3 (3 chunk ที่ส่งเข้า prompt), MRR@5 และอัตราความเสี่ยงใน top-3:
  ฉบับที่ถูกเขียนทับแล้ว (กฎเก่า) / chunk ท้ายประกาศ / ฉบับ 234 ทั้งที่คำถามไม่ได้ระบุ DBD

ใช้งาน:
  python chunking/scripts/eval_retrieval.py                  # สรุปผล
  python chunking/scripts/eval_retrieval.py --failures 15    # แสดงข้อที่ตอบผิด
  python chunking/scripts/eval_retrieval.py --markdown reports/retrieval_eval.md
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from collections import defaultdict
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agents"))
from agent3_rag_retrieval import DBD_TRIGGERS, RAGRetrievalAgent  # noqa: E402

# เฉลยใน CSV -> chunk ตัวบทหลัก
CSV_GOLD = [
    ("ข้อ 1 (ฉบับ 57) / ข้อ 2 (ฉบับ 159)", ["VAT57_ART_01", "VAT159_ART_02"]),
    ("ข้อ 1 (ฉบับ 159) / ข้อ 4/1", ["VAT159_ART_01", "VAT57_ART_04_1"]),
    ("ข้อ 2 (ฉบับ 57) / ข้อ 3 (ฉบับ 159)", ["VAT57_ART_02", "VAT159_ART_03"]),
    ("ข้อ 3 (ฉบับ 57) / ข้อ 4 (ฉบับ 159)", ["VAT57_ART_03", "VAT159_ART_04"]),
    ("ข้อ 4 (ฉบับ 57", ["VAT57_ART_04"]),
    ("ข้อ 5/1", ["VAT159_ART_05_1"]),
    ("ข้อ 5 (ฉบับ 57/159", ["VAT57_ART_05_A", "VAT57_ART_05_B", "VAT57_ART_05_C",
                           "VAT159_ART_05_A", "VAT159_ART_05_B", "VAT159_ART_05_C"]),
    ("ข้อ 6(", ["VAT57_ART_06", "VAT159_ART_06"]),
    ("ข้อ 7 (ฉบับ 57/159)", ["VAT57_ART_07", "VAT159_ART_07"]),
    ("ข้อ 8 (ฉบับ 57/159", ["VAT57_ART_08", "VAT159_ART_08"]),
    ("ข้อ 9 (ฉบับ 57/159", ["VAT57_ART_09", "VAT159_ART_09"]),
]


def load_chunks() -> dict:
    with open(os.path.join(ROOT, "all_10_announcements_chunks_official.json"), encoding="utf-8") as f:
        return {c["chunk_id"]: c for c in json.load(f)}


def acceptable(primaries: list[str], chunks: dict) -> set[str]:
    """ตัวบทหลัก + ฉบับแก้ไขของข้อนั้นที่ยังมีผล"""
    ok = set(primaries)
    for p in primaries:
        for a in chunks[p]["metadata"].get("amended_by", []):
            if chunks[a]["metadata"].get("is_current"):
                ok.add(a)
    return ok


def build_csv_set(chunks: dict) -> list[dict]:
    path = os.path.join(ROOT, "synthetic_dataset_vat_intent.csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["group"] in ("IN_SCOPE_VAT", "HIGH_RISK_SECTION_6")]
    out = []
    for r in rows:
        gold = next((g for key, g in CSV_GOLD if key in r["target_clause_or_agency"]), None)
        if gold is None:
            raise SystemExit(f"ไม่มี mapping เฉลยสำหรับ: {r['target_clause_or_agency']}")
        out.append({"id": r["id"], "query": r["query"], "group": r["sub_category"],
                    "gold": gold, "ok": acceptable(gold, chunks)})
    return out


def build_intent_set(chunks: dict) -> tuple[list[dict], int]:
    out, skipped = [], 0
    for cid, c in chunks.items():
        m = c["metadata"]
        if m.get("is_boilerplate"):
            skipped += len(m.get("user_intents", []))
            continue
        if m["role"] == "amendment":
            gold = m.get("amends") or []
        else:
            gold = [cid]
        if not gold:
            skipped += len(m.get("user_intents", []))
            continue
        for q in m.get("user_intents", []):
            out.append({"id": cid, "query": q, "group": m["role"], "gold": gold,
                        "ok": acceptable(gold, chunks) if m["role"] != "special" else {cid}})
    return out, skipped


def evaluate(agent: RAGRetrievalAgent, cases: list[dict], chunks: dict) -> dict:
    n = len(cases)
    hit1 = hit3 = mrr = 0.0
    risk = defaultdict(int)
    failures = []
    for case in cases:
        with redirect_stdout(io.StringIO()):
            res = agent.search(case["query"])
        top5 = [c["chunk_id"] for c in res["audit_log_top_5"]]
        top3 = top5[:3]
        rank = next((i + 1 for i, cid in enumerate(top5) if cid in case["ok"]), None)
        hit1 += rank == 1
        hit3 += rank is not None and rank <= 3
        mrr += 1 / rank if rank else 0
        q = case["query"].lower()
        is_dbd = any(t in q for t in DBD_TRIGGERS)
        metas = [chunks[cid]["metadata"] for cid in top3]
        risk["superseded"] += any(not m.get("is_current", True) for m in metas)
        risk["boilerplate"] += any(m.get("is_boilerplate") for m in metas)
        risk["dbd_leak"] += (not is_dbd) and any(m.get("role") == "special" for m in metas)
        if rank is None or rank > 3:
            failures.append({**case, "top3": top3})
    return {"n": n, "hit@1": hit1 / n, "hit@3": hit3 / n, "mrr@5": mrr / n,
            **{f"risk_{k}": v / n for k, v in risk.items()}, "failures": failures}


def by_group(agent, cases, chunks) -> dict:
    groups = defaultdict(list)
    for c in cases:
        groups[c["group"]].append(c)
    return {g: evaluate(agent, cs, chunks) for g, cs in sorted(groups.items())}


def fmt(r: dict) -> str:
    return (f"Hit@1 {r['hit@1']:.1%} | Hit@3 {r['hit@3']:.1%} | MRR@5 {r['mrr@5']:.3f} | "
            f"กฎเก่าใน top3 {r['risk_superseded']:.1%} | ท้ายประกาศ {r['risk_boilerplate']:.1%} | "
            f"234 ทั้งที่ไม่ถาม DBD {r['risk_dbd_leak']:.1%}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--failures", type=int, default=0, help="แสดงข้อที่ผิดในโหมด primary (จำนวน)")
    ap.add_argument("--markdown", help="บันทึกผลเป็นไฟล์ markdown (path สัมพัทธ์กับโฟลเดอร์ chunking)")
    args = ap.parse_args()

    chunks = load_chunks()
    agents = {m: RAGRetrievalAgent(base_dir=ROOT, mode=m) for m in ("all", "primary")}
    csv_cases = build_csv_set(chunks)
    intent_cases, skipped = build_intent_set(chunks)

    results = {}
    lines = ["# ผลวัด retrieval (Agent 3)", "",
             "เทียบ `all` = ค้นทั้ง 75 chunks (เดิม) กับ `primary` = ค้นเฉพาะตัวบทหลัก 57/159 "
             "(+234 เมื่อระบุ DBD) ตามหลักการ", ""]
    for name, cases in (("A) CSV ชุดทดสอบหลัก", csv_cases), ("B) user_intents", intent_cases)):
        print(f"\n== {name} ({len(cases)} คำถาม)")
        lines += [f"## {name} — {len(cases)} คำถาม", "",
                  "| โหมด | Hit@1 | Hit@3 | MRR@5 | กฎเก่าใน top3 | ท้ายประกาศใน top3 | 234 ทั้งที่ไม่ถาม DBD |",
                  "|---|---|---|---|---|---|---|"]
        for mode, agent in agents.items():
            r = evaluate(agent, cases, chunks)
            results[(name, mode)] = r
            print(f"  {mode:8} {fmt(r)}")
            lines.append(f"| `{mode}` | {r['hit@1']:.1%} | {r['hit@3']:.1%} | {r['mrr@5']:.3f} | "
                         f"{r['risk_superseded']:.1%} | {r['risk_boilerplate']:.1%} | {r['risk_dbd_leak']:.1%} |")
        lines.append("")
        if name.startswith("A"):
            lines += ["### แยกตามหมวด (Hit@3)", "", "| หมวด | n | all | primary |", "|---|---|---|---|"]
            ga, gp = by_group(agents["all"], cases, chunks), by_group(agents["primary"], cases, chunks)
            print("  แยกตามหมวด (Hit@3 all → primary):")
            for g in ga:
                print(f"    {ga[g]['hit@3']:6.0%} → {gp[g]['hit@3']:6.0%}  ({ga[g]['n']:2}) {g}")
                lines.append(f"| {g} | {ga[g]['n']} | {ga[g]['hit@3']:.0%} | {gp[g]['hit@3']:.0%} |")
            lines.append("")
    print(f"\n(ข้าม user_intents ของ chunk ท้ายประกาศ {skipped} คำถาม)")
    lines.append(f"_ข้าม user_intents ของ chunk ท้ายประกาศ {skipped} คำถาม — ไม่อยู่ในขอบเขตการตอบตามหลักการ_")

    fails = results[("A) CSV ชุดทดสอบหลัก", "primary")]["failures"]
    lines += ["", f"## ข้อที่ `primary` ไม่ได้เฉลยใน top-3 (ชุด A) — {len(fails)} ข้อ", "",
              "| id | คำถาม | เฉลย | top-3 ที่ได้ |", "|---|---|---|---|"]
    for f in fails:
        lines.append(f"| {f['id']} | {f['query']} | {', '.join(f['gold'])} | {', '.join(f['top3'])} |")
    if args.failures:
        print(f"\n== ข้อที่ primary ผิด (ชุด A) {len(fails)} ข้อ")
        for f in fails[:args.failures]:
            print(f"  [{f['id']}] {f['query']}\n      เฉลย {f['gold']}\n      ได้   {f['top3']}")
    if args.markdown:
        path = os.path.join(ROOT, args.markdown)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"\nบันทึก: {path}")


if __name__ == "__main__":
    main()
