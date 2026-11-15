#!/usr/bin/env python3
"""
รวมข้อมูลความสัมพันธ์เป็น Graph RAG หลายชั้น (สรุปเป็นข้อความ) สำหรับคนอ่านและตรวจ

    python chunking/scripts/build_graph_data.py --out graph_data.json --html chunking/reports/graph_view.html

ชั้นที่ 1  ภาพรวม: ช่องทางยื่น (กระดาษ 57 · อินเทอร์เน็ต 159 · DBD 234) → หัวข้อ (จาก graph_rag_vat_registration.json)
ชั้นที่ 2  หัวข้อ: ข้อของตัวบทหลักในแต่ละช่องทาง พร้อมสรุปสั้น และสายการแก้ไขเรียงตามปี
ชั้นที่ 3  ข้อ: ข้อความตัวบท ฉบับที่แก้ (ยังมีผล/ถูกแทนที่) คำพ้องที่ชี้มา และผลคำถามทดสอบ
"ประเด็นที่ต้องตรวจ" = จุดที่แหล่งข้อมูลขัดกันเอง เขียนเป็นประโยค ให้คนตัดสินว่าแหล่งไหนถูก

สรุปสั้นของตัวบทหลัก (SUMMARY) เขียนจากข้อความตัวบท ส่วนฉบับแก้ไขใช้คำอธิบายในวงเล็บท้ายชื่อ chunk
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
THAI = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
CHANNEL = {"57": "กระดาษ", "159": "อินเทอร์เน็ต", "234": "DBD"}

SUMMARY = {
    "VAT57_ART_01": "จดล่วงหน้าก่อนเริ่มกิจการได้ ถ้ามีแผนงานและต้องซื้อของเพื่อเตรียมกิจการ (เช่น สร้างโรงงาน ติดตั้งเครื่องจักร) ภายใน 6 เดือนก่อนเริ่มกิจการ",
    "VAT57_ART_02": "ถ้าไม่เข้าเงื่อนไขจดล่วงหน้า ให้ยื่นเมื่อเริ่มประกอบกิจการ",
    "VAT57_ART_03": "กิจการที่ได้รับยกเว้นตาม ม.81/3 ที่แจ้งขอเสีย VAT ต้องยื่นจดภายใน 30 วันนับแต่วันที่แจ้ง",
    "VAT57_ART_04": "สถานที่ยื่น: กทม. ที่สรรพากรพื้นที่หรือพื้นที่สาขา · ต่างจังหวัดที่สรรพากรพื้นที่สาขา · ธุรกิจขนาดใหญ่ที่หน่วยงานบริหารภาษีธุรกิจขนาดใหญ่",
    "VAT57_ART_04_1": "คนไทยขายออนไลน์ที่ใช้ห้องชุดเป็นที่ตั้งแห่งเดียว ต้องยื่นจดผ่านอินเทอร์เน็ตตามฉบับ 159",
    "VAT57_ART_05_A": "เอกสารประกอบคำขอ: บุคคลธรรมดา คณะบุคคล และกรณีมอบอำนาจ",
    "VAT57_ART_05_B": "เอกสารประกอบคำขอ: นิติบุคคล องค์การของรัฐ กิจการร่วมค้า นิติบุคคลต่างประเทศ",
    "VAT57_ART_05_C": "เอกสารเกี่ยวกับสถานประกอบการ: ป้ายชื่อ สัญญาเช่าหรือหนังสือยินยอม แผนที่ และกรณีห้องชุด",
    "VAT57_ART_06": "การตรวจคำขอ และ 6 เหตุที่ไม่ออกใบทะเบียน เช่น เอกสารเท็จ ตัวแทนเชิด ไม่มีสถานประกอบการจริง",
    "VAT57_ART_07": "ใบทะเบียนใช้แบบ ภ.พ.20 และ ภ.พ.21",
    "VAT57_ART_08": "เป็นผู้ประกอบการจดทะเบียนตั้งแต่วันที่สรรพากรรับคำขอ เว้นแต่ไม่ได้ใบทะเบียนเพราะเข้าเหตุตามข้อ 6",
    "VAT57_ART_09": "ผู้มีอำนาจออกใบทะเบียน: สรรพากรพื้นที่ หรือ ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่",
    "VAT57_ART_10": "มีปัญหาในการปฏิบัติ ให้อธิบดีวินิจฉัย",
    "VAT159_ART_01": "ยื่นคำขอ ภ.พ.01 ทาง www.rd.go.th ได้อีกวิธีหนึ่ง (คนไทยขายออนไลน์ใช้ห้องชุดต้องใช้วิธีนี้เท่านั้น)",
    "VAT159_ART_02": "จดล่วงหน้าก่อนเริ่มกิจการ เงื่อนไขเดียวกับฉบับ 57 ข้อ 1",
    "VAT159_ART_03": "ไม่เข้าเงื่อนไขจดล่วงหน้า ให้ยื่นเมื่อเริ่มประกอบกิจการ",
    "VAT159_ART_04": "กิจการยกเว้นตาม ม.81/3 ที่แจ้งขอเสีย VAT ต้องยื่นจดภายใน 30 วัน",
    "VAT159_ART_05_A": "เอกสารที่อัปโหลด: บุคคลธรรมดา คนต่างด้าว คณะบุคคล",
    "VAT159_ART_05_B": "เอกสารที่อัปโหลด: นิติบุคคล กิจการร่วมค้า นิติบุคคลต่างประเทศ",
    "VAT159_ART_05_C": "เอกสารสถานประกอบการ และการยกเว้นหนังสือนิติบุคคลอาคารชุดสำหรับคนไทยขายออนไลน์",
    "VAT159_ART_05_1": "คนไทยขายออนไลน์ใช้ห้องชุด ต้องยินยอมให้แพลตฟอร์มส่งข้อมูลการขายให้กรมสรรพากร",
    "VAT159_ART_06": "การตรวจคำขอ และ 8 เหตุที่ไม่ออกใบทะเบียน (6 เหตุเดียวกับฉบับ 57 และเพิ่มอีก 2 เหตุสำหรับการยื่นออนไลน์)",
    "VAT159_ART_07": "ออกใบทะเบียน ภ.พ.20 เป็นรายสถานประกอบการ",
    "VAT159_ART_08": "เป็นผู้ประกอบการจดทะเบียนนับแต่วันยื่นคำขอ และใช้ ภ.พ.01 แทนใบทะเบียนชั่วคราว",
    "VAT159_ART_09": "ผู้มีอำนาจออกใบทะเบียน: สรรพากรพื้นที่ หรือ ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่",
    "VAT159_ART_10": "มีปัญหาในการปฏิบัติ ให้อธิบดีวินิจฉัย และวันใช้บังคับของประกาศ",
    "VAT234_ART_01": "นิติบุคคลที่จดจัดตั้งผ่านกรมพัฒนาธุรกิจการค้า (DBD) ยื่นคำขอจด VAT พร้อมกันได้",
    "VAT234_ART_02": "จดล่วงหน้าผ่าน DBD ได้ เงื่อนไขเดียวกับการจดล่วงหน้าปกติ",
    "VAT234_ART_03": "กิจการยกเว้นตาม ม.81/3 แจ้งขอเสีย VAT ในแบบคำขอที่ยื่นผ่าน DBD",
    "VAT234_ART_04": "ยื่นผ่าน DBD ตามแบบแนบท้าย และเตรียมเอกสารตัวจริงไว้แสดงต่อเจ้าพนักงาน",
    "VAT234_ART_05": "การตรวจคำขอที่ยื่นผ่าน DBD และ 6 เหตุที่ไม่ออกใบทะเบียน",
    "VAT234_ART_06": "ออกใบทะเบียน ภ.พ.20 เป็นรายสถานประกอบการ",
    "VAT234_ART_07": "เป็นผู้ประกอบการจดทะเบียนนับแต่วันยื่นผ่าน DBD และใช้คำขอที่พิมพ์ออกมาแทนใบทะเบียนชั่วคราว",
    "VAT234_ART_08": "ผู้มีอำนาจออกใบทะเบียน: สรรพากรพื้นที่ หรือ ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่",
    "VAT234_ART_09": "วันใช้บังคับและผู้ลงนาม",
    "VAT234_ART_ATTACHMENT": "แบบคำขอแนบท้าย: รายการกิจการยกเว้นที่ขอเข้า VAT ได้ ข้อรับรอง 5 ข้อ สิทธิและหน้าที่",
    "VAT214_ART_01_C": "เอกสารสถานประกอบการสำหรับการยื่นออนไลน์",
}


def thai_year(text: str) -> str:
    m = re.search(r"(25\d\d)", (text or "").translate(THAI))
    return m.group(1) if m else ""


def article_of(cid: str, md: dict) -> str:
    """ข้อของตัวบทหลักที่ chunk นี้อยู่ (ฉบับแก้ไข = ข้อที่ไปแก้)"""
    if md.get("is_boilerplate") and md.get("role") == "amendment":
        return "ท้ายประกาศ"
    if md.get("amends_article"):
        return md["amends_article"].split(":")[1].replace("ข้อ", "").strip()
    m = re.search(r"_ART_(\d+)(?:_(\d))?", cid)
    if not m:
        return "แนบท้าย"
    return f"{int(m.group(1))}/{m.group(2)}" if m.group(2) else str(int(m.group(1)))


def summarize(cid: str, c: dict) -> tuple[str, str]:
    """(สรุปเนื้อหา, สิ่งที่ฉบับนี้ทำ เช่น 'แก้ไขข้อ 9') — ตัวบทหลักใช้ SUMMARY"""
    md, title = c["metadata"], c["title"]
    head, _, tail = title.partition(":")
    change = ""
    m = re.search(r"\(((?:แก้ไข|เพิ่ม).*?) ฉบับที่ \d+\)", head)
    if m:
        change = m.group(1)
    if cid in SUMMARY:
        return SUMMARY[cid], change
    if md.get("is_boilerplate"):
        return "วันใช้บังคับและผู้ลงนาม", change
    par = re.findall(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", tail)
    return (par[0] if par else tail).strip(), change


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="ไฟล์ JSON")
    ap.add_argument("--html", help="สร้างหน้าแสดงผล (ฝังข้อมูลใน scripts/graph_view_template.html)")
    args = ap.parse_args()

    chunks = er.load_chunks()
    graph = json.load(open(os.path.join(ROOT, "graph_rag_vat_registration.json"), encoding="utf-8"))
    syn = json.load(open(os.path.join(ROOT, "vat_synonym_boost_dictionary.json"), encoding="utf-8"))

    # ---- ข้อมูลรายชิ้น
    arts = {}
    for cid, c in chunks.items():
        md = c["metadata"]
        ann = cid.split("_")[0].replace("VAT", "")
        oa = c.get("official_announcement") or {}
        summary, change = summarize(cid, c)
        arts[cid] = {
            "id": cid, "ann": ann, "art": article_of(cid, md), "role": md.get("role"),
            "current": md.get("is_current", True), "boiler": md.get("is_boilerplate", False),
            "year": thai_year(oa.get("effective_date") or oa.get("announcement_date")),
            "summary": summary, "change": change, "ref": c.get("article_ref", ""),
            "text": " ".join(c["official_raw_text"].split())[:900],
            "amends": md.get("amends") or [], "superseded_by": md.get("superseded_by") or [],
            "topics": [], "syn": [], "tests": [],
        }
    for cid, a in arts.items():
        a["chain"] = sorted([x for x, b in arts.items() if cid in b["amends"]],
                            key=lambda x: (arts[x]["year"] or "9999", int(arts[x]["ann"])))

    topics = []
    tmem = defaultdict(list)
    for e in graph["edges"]["topic_membership"]:
        if e["source"] in arts:
            tmem[e["target"]].append(e)
            arts[e["source"]]["topics"].append(e["target"])
    for ck, cd in syn["clauses"].items():
        for t in cd.get("target_chunks", []):
            if t in arts:
                arts[t]["syn"].append(", ".join(cd.get("keywords", [])[:6]))

    # ---- ผลคำถามทดสอบ (โหมดตัวบทหลัก) ผูกกับข้อเฉลย
    agent = er.RAGRetrievalAgent(base_dir=ROOT, mode="primary")
    cases = er.build_csv_set(chunks)
    with redirect_stdout(io.StringIO()):
        groups = er.by_group(agent, cases, chunks)
        overall = er.evaluate(agent, cases, chunks)["hit@3"]
    gold_of = defaultdict(set)
    for c in cases:
        gold_of[c["group"]] |= set(c["gold"])
    tests = []
    for g, r in sorted(groups.items()):
        fails = [{"q": f["query"], "got": [arts[x]["summary"] for x in f["top3"][:2] if x in arts]} for f in r["failures"]]
        t = {"name": g, "n": r["n"], "ok": r["n"] - len(fails), "fails": fails, "gold": sorted(gold_of[g])}
        tests.append(t)
        for x in t["gold"]:
            if x in arts:
                arts[x]["tests"].append(len(tests) - 1)

    for t in graph["nodes"]["topics"]:
        members = tmem.get(t["id"], [])
        prim = [e["source"] for e in members if arts[e["source"]]["role"] in ("primary", "special")]
        # ฉบับแก้ไขใน topic ที่ตัวบทหลักของมันยังไม่อยู่ใน topic → เพิ่มตัวบทหลักนั้น
        for e in members:
            for p in arts[e["source"]]["amends"]:
                if p not in prim:
                    prim.append(p)
        lanes = {}
        for ch_ann in ("57", "159", "234"):
            ids = sorted([p for p in prim if arts[p]["ann"] == ch_ann])
            if ids:
                lanes[ch_ann] = ids
        t_tests = sorted({i for p in prim for i in arts[p]["tests"]})
        topics.append({"id": t["id"], "label": t["label"], "desc": t.get("description", ""),
                       "lanes": lanes, "tests": t_tests})

    # ---- ประเด็นที่ต้องตรวจ (ประโยคภาษาคน)
    def name(cid):
        a = arts[cid]
        return f"ฉบับ {a['ann']}{' (' + a['year'] + ')' if a['year'] else ''} เรื่อง \"{a['summary']}\""

    def topics_of(ids):
        return sorted({t for i in ids if i in arts for t in arts[i]["topics"]})

    checks = []
    for lin in graph["edges"].get("legal_evolution_lineage", []):
        for x in [x for x in lin.get("active_law_chunks", []) if x in arts and not arts[x]["current"]]:
            checks.append({"level": "error", "topics": topics_of([x]), "ids": [x],
                "title": f"ไฟล์ graph บอกว่า{name(x)} ยังใช้อยู่ แต่ถูกฉบับ {', '.join(arts[x]['superseded_by'])} แทนที่แล้ว",
                "detail": f"เรื่อง \"{lin['issue']}\" — ผลเทียบตัวบทจริงบอกว่าข้อความนี้ไม่มีผลแล้ว ถ้าถูกต้อง ต้องเอาออกจากรายการกฎที่ยังใช้ในไฟล์ graph"})
    for e in graph["edges"]["topic_membership"]:
        x, ch = e["source"], e.get("channel", "")
        if x not in arts:
            continue
        if "ปัจจุบัน" in ch and not arts[x]["current"]:
            checks.append({"level": "error", "topics": [e["target"]], "ids": [x],
                "title": f"ไฟล์ graph ติดป้ายว่าใช้อยู่ แต่{name(x)} ถูกแทนที่แล้ว", "detail": f"ป้ายใน graph: {ch}"})
        if "ประวัติเก่า" in ch and arts[x]["current"]:
            later = [y for y, b in arts.items() if b["role"] == "amendment" and set(b["amends"]) & set(arts[x]["amends"])
                     and int(b["year"] or 0) > int(arts[x]["year"] or 0) and b["current"]]
            checks.append({"level": "warn", "topics": [e["target"]], "ids": [x] + later,
                "title": f"ไฟล์ graph ติดป้ายว่าเป็นประวัติเก่า แต่ผลเทียบตัวบทบอกว่า{name(x)} ยังมีผล",
                "detail": ("ฉบับที่ออกทีหลังและแก้ข้อเดียวกัน: " + "; ".join(name(y) for y in later)
                           + " — ควรเปิดต้นฉบับดูว่าฉบับหลังแทนที่ทั้งข้อหรือแค่บางอนุ")
                          if later else "ควรเปิดต้นฉบับดูว่าป้ายใน graph ล้าสมัยหรือไม่"})
    for ck, cd in syn["clauses"].items():
        old = [t for t in cd.get("target_chunks", []) if t in arts and not arts[t]["current"]]
        if old:
            checks.append({"level": "warn", "topics": topics_of(old), "ids": old,
                "title": f"คำพ้อง ({', '.join(cd.get('keywords', [])[:3])} …) ยังชี้ไปที่กฎที่ถูกแทนที่แล้ว",
                "detail": "กฎเก่า: " + "; ".join(name(x) for x in old)
                          + " — ตอนนี้ไม่กระทบเพราะค้นเฉพาะตัวบทหลัก แต่ถ้าเปิดโหมดค้นทุกฉบับจะดึงกฎเก่าขึ้นมา"})
    for i, t in enumerate(tests):
        if t["ok"] / t["n"] < 0.5:
            checks.append({"level": "warn", "topics": topics_of(t["gold"]), "ids": t["gold"], "test": i,
                "title": f"คำถามทดสอบเรื่อง \"{t['name']}\" ระบบค้นเจอข้อที่ถูกแค่ {t['ok']} จาก {t['n']} ข้อ",
                "detail": "ข้อที่ควรค้นเจอ: " + "; ".join(name(x) for x in t["gold"] if x in arts)})
    checks.sort(key=lambda c: {"error": 0, "warn": 1}[c["level"]])

    data = {"arts": arts, "topics": topics, "tests": tests, "checks": checks, "overall": round(overall, 3),
            "anns": {a["id"].split("_")[1]: {"title": a.get("official_title", ""), "role": a.get("role", "")}
                     for a in graph["nodes"]["announcements"]}}
    json.dump(data, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
    if args.html:
        tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph_view_template.html"), encoding="utf-8").read()
        blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        open(args.html, "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/", blob))
        print(f"หน้าแสดงผล: {args.html}")
    print(f"{args.out}: หัวข้อ {len(topics)} ตัวบท {len(arts)} ประเด็นที่ต้องตรวจ {len(checks)}")
    for c in checks:
        print(f"  [{c['level']}] {c['title']}")


if __name__ == "__main__":
    main()
