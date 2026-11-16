#!/usr/bin/env python3
"""
เทียบการค้นระดับข้อ (chunk เดิม) กับการค้นระดับย่อย (node ลำดับชั้น) ด้วยตัวค้นแบบเดียวกัน

    python chunking/scripts/eval_hierarchy_retrieval.py

ตัวค้น: TF-IDF ของ 3-gram ตัวอักษร + cosine (แทนการค้นด้วยความหมาย ไม่ใช้ keyword/คำพ้องที่ติดไว้ใน chunk
เพื่อให้เทียบเฉพาะผลของขนาดชิ้น) · ชุดทดสอบ: CSV 132 ข้อเดียวกับ eval_retrieval.py · ค้นเฉพาะตัวบทหลัก (+234 เมื่อถาม DBD)
ระดับย่อย: ข้อความของ node + ข้อความต้นของ node แม่ (บริบท) แล้วให้คะแนน chunk = คะแนนสูงสุดของ node ใน chunk นั้น
"""
from __future__ import annotations

import io
import math
import os
import sys
from collections import Counter, defaultdict
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_hierarchy as bh  # noqa: E402
import eval_retrieval as er  # noqa: E402


def grams(text: str) -> Counter:
    t = "".join(bh.norm(text).lower().split())
    return Counter(t[i:i + 3] for i in range(len(t) - 2))


class Index:
    def __init__(self, docs: dict[str, str]):
        self.tf = {k: grams(v) for k, v in docs.items()}
        df = Counter(g for c in self.tf.values() for g in c)
        n = len(self.tf)
        self.idf = {g: math.log((n + 1) / (d + 1)) + 1 for g, d in df.items()}
        self.vec = {k: self._w(c) for k, c in self.tf.items()}

    def _w(self, c: Counter) -> dict:
        v = {g: f * self.idf.get(g, 0.0) for g, f in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {g: x / norm for g, x in v.items()}

    def scores(self, q: str) -> dict[str, float]:
        qv = self._w(grams(q))
        return {k: sum(w * v.get(g, 0.0) for g, w in qv.items()) for k, v in self.vec.items()}


def main() -> None:
    chunks = er.load_chunks()
    allowed = {c for c, x in chunks.items() if x["metadata"]["role"] in ("primary", "special") and not x["metadata"].get("is_boilerplate")}
    cases = er.build_csv_set(chunks)

    # ระดับข้อ
    art_idx = Index({c: chunks[c]["official_raw_text"] for c in allowed})

    # ระดับย่อย: node ของตัวบทหลัก/DBD ผูกกลับ chunk ที่มีข้อความนั้น
    st, _ = bh.build(list(chunks.values()))
    raw_sk = {c: bh.skel(chunks[c]["official_raw_text"]) for c in allowed}
    node_docs, node_chunk = {}, {}
    for nid in st.order:
        n = st.nodes[nid]
        text = (n.get("own_text") or "").strip()
        if not text or n["level"] in ("announcement", "note", "external"):
            continue
        cands = [c for c in (n.get("chunk_ids") or []) if c in allowed]
        if not cands:
            continue
        sk = bh.skel(text)
        owner = next((c for c in cands if sk and sk in raw_sk[c]), cands[0])
        parent = st.nodes.get(n.get("parent") or "", {})
        ctx = (parent.get("own_text") or "")[:200]
        node_docs[nid] = f"{ctx}\n{text}"
        node_chunk[nid] = owner
    node_idx = Index(node_docs)

    def rank_art(q):
        s = art_idx.scores(q)
        return sorted(s, key=s.get, reverse=True)

    def rank_node(q):
        s = node_idx.scores(q)
        best = defaultdict(float)
        for nid, v in s.items():
            c = node_chunk[nid]
            best[c] = max(best[c], v)
        return sorted(best, key=best.get, reverse=True)

    def evaluate(rank):
        hit1 = hit3 = 0
        per = defaultdict(lambda: [0, 0])
        for case in cases:
            q = case["query"].lower()
            dbd = any(t in q for t in er.DBD_TRIGGERS)
            top = [c for c in rank(case["query"]) if dbd or chunks[c]["metadata"]["role"] == "primary"][:3]
            h3 = any(c in case["ok"] for c in top)
            hit1 += bool(top) and top[0] in case["ok"]
            hit3 += h3
            per[case["group"]][0] += h3
            per[case["group"]][1] += 1
        return hit1 / len(cases), hit3 / len(cases), per

    with redirect_stdout(io.StringIO()):
        a1, a3, pa = evaluate(rank_art)
        n1, n3, pn = evaluate(rank_node)
    print(f"ชุดทดสอบ {len(cases)} ข้อ · node ระดับย่อย {len(node_docs)} ชิ้น เทียบ chunk ระดับข้อ {len(allowed)} ชิ้น")
    print(f"ระดับข้อ   Hit@1 {a1:.1%}  Hit@3 {a3:.1%}")
    print(f"ระดับย่อย  Hit@1 {n1:.1%}  Hit@3 {n3:.1%}")
    print("แยกตามหมวด (Hit@3 ระดับข้อ → ระดับย่อย):")
    for g in sorted(pa):
        x, n = pa[g]
        y, _ = pn[g]
        print(f"  {x / n:6.0%} → {y / n:6.0%}  ({n:2}) {g}")


if __name__ == "__main__":
    main()
