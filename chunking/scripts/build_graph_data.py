#!/usr/bin/env python3
"""
รวมข้อมูลความสัมพันธ์ทั้งหมดเป็น JSON ไฟล์เดียว สำหรับหน้าแสดง Graph RAG และตรวจความสอดคล้อง

    python chunking/scripts/build_graph_data.py --out graph_data.json --html graph_view.html

แหล่งข้อมูล: chunk 75 ชิ้น (metadata จาก annotate_roles.py), graph_rag_vat_registration.json,
vat_synonym_boost_dictionary.json, synthetic_dataset_vat_intent.csv + ผล eval_retrieval (โหมด primary)
ผลตรวจ (checks) = จุดที่แหล่งข้อมูลขัดกันเอง ให้คนตัดสินว่าแหล่งไหนถูก
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_retrieval as er  # noqa: E402

ROOT = er.ROOT


def art_num(cid: str, md: dict) -> str:
    if md.get("is_boilerplate") and md.get("role") == "amendment":
        return "ท้ายประกาศ"
    if md.get("amends_article"):
        return md["amends_article"].split(":")[1].replace("ข้อ", "").strip()
    m = re.search(r"_ART_(\d+)(?:_(\d))?", cid)
    if not m:
        return "แนบท้าย"
    return f"{int(m.group(1))}/{m.group(2)}" if m.group(2) else str(int(m.group(1)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="ไฟล์ JSON")
    ap.add_argument("--html", help="สร้างหน้าแสดงผล (ฝังข้อมูลใน scripts/graph_view_template.html)")
    args = ap.parse_args()

    chunks = er.load_chunks()
    graph = json.load(open(os.path.join(ROOT, "graph_rag_vat_registration.json"), encoding="utf-8"))
    syn = json.load(open(os.path.join(ROOT, "vat_synonym_boost_dictionary.json"), encoding="utf-8"))

    nodes, edges, checks = [], [], []

    def check(level, title, detail, ids):
        checks.append({"level": level, "title": title, "detail": detail, "ids": sorted(set(ids))})

    for a in graph["nodes"]["announcements"]:
        n = a["id"].split("_")[1]
        nodes.append({"id": a["id"], "kind": "ann", "label": f"ฉบับ {n}", "num": n,
                      "title": a.get("official_title", ""), "role": a.get("role", ""),
                      "channel": a.get("channel", ""), "date": a.get("effective_date", "")})

    for cid, c in chunks.items():
        md = c["metadata"]
        ann = cid.split("_")[0].replace("VAT", "")
        nodes.append({"id": cid, "kind": "chunk", "label": cid.replace("VAT", "").replace("_ART_", " ข้อ "),
                      "ann": ann, "art": art_num(cid, md), "role": md.get("role"),
                      "current": md.get("is_current", True), "boiler": md.get("is_boilerplate", False),
                      "title": c["title"], "ref": c.get("article_ref", ""),
                      "text": c["official_raw_text"][:700], "superseded_by": md.get("superseded_by") or [],
                      "amended_by": md.get("amended_by") or [], "nkw": len(md.get("boost_keywords", []))})
        edges.append({"s": cid, "t": f"ANN_{ann}", "kind": "in"})
        for p in md.get("amends") or []:
            edges.append({"s": cid, "t": p, "kind": "amends", "current": md.get("is_current", True)})

    for t in graph["nodes"]["topics"]:
        nodes.append({"id": t["id"], "kind": "topic", "label": t["label"], "title": t.get("description", ""),
                      "rule": t.get("current_rule", "")})
    for e in graph["edges"]["topic_membership"]:
        edges.append({"s": e["source"], "t": e["target"], "kind": "topic", "channel": e.get("channel", "")})

    for ck, cd in syn["clauses"].items():
        nodes.append({"id": f"SYN_{ck}", "kind": "syn", "label": ck.replace("section_", "§").replace("_", " "),
                      "title": ", ".join(cd.get("keywords", [])[:12]), "weight": cd.get("boost_weight")})
        for t in cd.get("target_chunks", []):
            edges.append({"s": f"SYN_{ck}", "t": t, "kind": "syn"})

    # ชุดทดสอบ: หมวด → chunk เฉลย พร้อม Hit@3 (โหมด primary)
    agent = er.RAGRetrievalAgent(base_dir=ROOT, mode="primary")
    cases = er.build_csv_set(chunks)
    with redirect_stdout(io.StringIO()):
        groups = er.by_group(agent, cases, chunks)
    gold_by_group = defaultdict(set)
    for c in cases:
        gold_by_group[c["group"]] |= set(c["gold"])
    for i, (g, r) in enumerate(sorted(groups.items())):
        gid = f"CAT_{i:02d}"
        fails = [{"q": f["query"], "top3": f["top3"]} for f in r["failures"]]
        nodes.append({"id": gid, "kind": "cat", "label": g, "n": r["n"], "hit3": round(r["hit@3"], 3), "fails": fails})
        for t in sorted(gold_by_group[g]):
            edges.append({"s": gid, "t": t, "kind": "gold"})
        if r["hit@3"] < 0.5:
            check("warn", f"ชุดทดสอบหมวด \"{g}\" ค้นเจอข้อที่ถูกใน 3 อันดับแรกแค่ {r['hit@3']:.0%}",
                  f"{len(fails)} จาก {r['n']} ข้อพลาด — ดูคำถามที่พลาดในแผงรายละเอียดของหมวดนี้",
                  [gid] + sorted(gold_by_group[g]))

    # ---- ตรวจความสอดคล้องระหว่างแหล่งข้อมูล
    for lin in graph["edges"].get("legal_evolution_lineage", []):
        stale = [x for x in lin.get("active_law_chunks", []) if x in chunks and not chunks[x]["metadata"].get("is_current", True)]
        if stale:
            check("error", f"graph ระบุว่ายังมีผล แต่ chunk ถูกฉบับหลังเขียนทับแล้ว: {lin['issue']}",
                  "active_law_chunks ใน graph_rag_vat_registration.json ขัดกับ is_current จาก annotate_roles.py "
                  "(ตรวจจากตัวบทจริง) — " + ", ".join(f"{x} แทนที่โดยฉบับ {', '.join(chunks[x]['metadata'].get('superseded_by') or [])}" for x in stale),
                  stale)
    for e in graph["edges"]["topic_membership"]:
        cid, ch = e["source"], e.get("channel", "")
        if cid not in chunks:
            continue
        cur = chunks[cid]["metadata"].get("is_current", True)
        if "ปัจจุบัน" in ch and not cur:
            check("error", f"graph ติดป้าย \"{ch}\" แต่ {cid} ไม่มีผลแล้ว",
                  f"แทนที่โดยฉบับ {', '.join(chunks[cid]['metadata'].get('superseded_by') or [])}", [cid, e["target"]])
        if "ประวัติเก่า" in ch and cur:
            check("warn", f"graph ติดป้าย \"{ch}\" แต่ {cid} ยังมีผล", "ตรวจว่าป้ายใน graph ล้าสมัยหรือไม่", [cid, e["target"]])
    for ck, cd in syn["clauses"].items():
        old = [t for t in cd.get("target_chunks", []) if t in chunks and not chunks[t]["metadata"].get("is_current", True)]
        if old:
            check("warn", f"คำพ้อง {ck} ชี้ไปที่ chunk ที่ไม่มีผลแล้ว",
                  "ในโหมดค้นตัวบทหลักไม่กระทบ (กรองออก) แต่ถ้าเปิดโหมดค้นทุกฉบับ จะดึงกฎเก่าขึ้นมา", [f"SYN_{ck}"] + old)
    topic_of = defaultdict(set)
    for e in graph["edges"]["topic_membership"]:
        topic_of[e["source"]].add(e["target"])
    syn_of = defaultdict(set)
    for ck, cd in syn["clauses"].items():
        for t in cd.get("target_chunks", []):
            syn_of[t].add(ck)
    for cid, c in chunks.items():
        md = c["metadata"]
        if md.get("role") in ("primary", "special") and not md.get("is_boilerplate"):
            if not syn_of[cid]:
                check("info", f"{cid} เป็นตัวบทที่ใช้ตอบ แต่ไม่มีหมวดคำพ้องชี้มา",
                      "คำถามภาษาชาวบ้านอาจค้นไม่เจอข้อนี้", [cid])
        if md.get("role") == "amendment" and not md.get("amends") and not md.get("is_boilerplate"):
            check("error", f"{cid} เป็นฉบับแก้ไข แต่ไม่รู้ว่าแก้ข้อไหน", "", [cid])
    ann_sections = defaultdict(set)
    for e in graph["edges"]["amendment_chain"]:
        ann_sections[(e["source"], e["target"])] |= {re.sub(r"\(.*", "", s.replace(" ", "")) for s in e.get("sections") or []}
    for cid, c in chunks.items():
        md = c["metadata"]
        if md.get("role") == "amendment" and md.get("amends_article"):
            ann = "ANN_" + cid.split("_")[0].replace("VAT", "")
            tgt = "ANN_" + md["amends_article"].split(":")[0]
            art = md["amends_article"].split(":")[1].replace(" ", "")
            secs = ann_sections.get((ann, tgt))
            if secs is not None and art not in secs and art.split("/")[0] not in secs:
                check("warn", f"{cid} แก้ {md['amends_article']} แต่ amendment_chain ใน graph ไม่ได้ระบุข้อนี้",
                      f"graph บอกว่า {ann} แก้ {tgt} ข้อ: {', '.join(sorted(secs))}", [cid, ann, tgt])

    order = {"error": 0, "warn": 1, "info": 2}
    checks.sort(key=lambda c: (order[c["level"]], c["title"]))
    data = {"nodes": nodes, "edges": edges, "checks": checks,
            "stats": {"chunks": len(chunks), "primary": sum(1 for c in chunks.values() if c["metadata"]["role"] == "primary"),
                      "amendment": sum(1 for c in chunks.values() if c["metadata"]["role"] == "amendment"),
                      "special": sum(1 for c in chunks.values() if c["metadata"]["role"] == "special"),
                      "superseded": sum(1 for c in chunks.values() if not c["metadata"].get("is_current", True))}}
    with redirect_stdout(io.StringIO()):
        data["stats"]["hit3"] = round(er.evaluate(agent, cases, chunks)["hit@3"], 3)
    json.dump(data, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
    if args.html:
        tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph_view_template.html"), encoding="utf-8").read()
        blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        open(args.html, "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/", blob))
        print(f"หน้าแสดงผล: {args.html}")
    lv = defaultdict(int)
    for c in checks:
        lv[c["level"]] += 1
    print(f"{args.out}: nodes {len(nodes)} edges {len(edges)} checks {dict(lv)}")
    for c in checks:
        if c["level"] != "info":
            print(f"  [{c['level']}] {c['title']}")


if __name__ == "__main__":
    main()
