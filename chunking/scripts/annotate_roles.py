#!/usr/bin/env python3
"""
ใส่ metadata บทบาทของ chunk ตามหลักการของระบบ:

  ประกาศ 57 (ยื่นกระดาษ) และ 159 (ยื่นอินเทอร์เน็ต) = ตัวบทหลัก เป็นฉบับรวมล่าสุด
  (ฉบับแก้ไขถูกเขียนทับเข้าไปแล้ว) ส่วนฉบับอื่นเป็นตัวเสริม

ฟิลด์ที่เพิ่มใน metadata ของทุก chunk:
  role             "primary" (57/159) | "amendment" (ฉบับแก้ไข 57/159) | "special" (234 ช่องทาง DBD)
  is_boilerplate   true ถ้าเป็นข้อท้ายประกาศ (วันใช้บังคับ/ผู้ลงนาม) ไม่ควรอยู่ในดัชนีค้นหา
  is_current       ข้อความนี้ยังมีผลบังคับใช้หรือไม่
                   - primary: true เสมอ
                   - amendment: true ถ้าเป็นฉบับแก้ไขรุ่นล่าสุดของข้อนั้น หรือข้อความยังปรากฏ
                     ในตัวบทหลักแทบครบ (>= CURRENT_MIN_COVERAGE)
  amends           (amendment) chunk_id ของตัวบทหลักที่ถูกแก้ เช่น ["VAT57_ART_09"]
  amends_article   (amendment) ข้อที่ถูกแก้ เช่น "57:ข้อ 9"
  merge_coverage   (amendment) สัดส่วนข้อความใหม่ที่พบในตัวบทหลัก (0-1)
  superseded_by    (amendment ที่ไม่ current) ฉบับแก้ไขรุ่นหลังที่แก้ข้อเดียวกัน
  amended_by       (primary) chunk_id ของฉบับแก้ไขทั้งหมดที่แก้ข้อนี้ เรียงตามลำดับฉบับ

ใช้งาน:
  python chunking/scripts/annotate_roles.py           # แสดงตารางผล ไม่เขียนไฟล์
  python chunking/scripts/annotate_roles.py --write   # เขียนลงไฟล์ chunk ทุกไฟล์ (รายฉบับ + all_10)
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBINED = "all_10_announcements_chunks_official.json"

PRIMARY = {"57", "159"}
SPECIAL = {"234"}
# ฉบับแก้ไข -> ตัวบทหลักที่ถูกแก้ (จาก graph.amendment_chain)
AMENDS_TARGET = {"74": "57", "139": "57", "165": "57", "215": "57", "245": "57",
                 "214": "159", "246": "159"}
CURRENT_MIN_COVERAGE = 0.98   # ฉบับแก้ไขรุ่นเก่า: ต้องพบข้อความแทบครบในตัวบทหลักจึงถือว่ายังมีผล
MERGED_MIN_COVERAGE = 0.90    # ฉบับแก้ไขรุ่นล่าสุด: ต่ำกว่านี้ = อาจยังไม่ได้รวมเข้าตัวบทหลัก

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
QUOTED_RE = re.compile(r"“(.*)”", re.S)
RAW_TARGET_RE = re.compile(
    r"(?:ยกเลิกความใน|เพิ่มความต่อไปนี้เป็น).{0,60}?ข้อ\s*([0-9]+(?:/[0-9]+)?)", re.S)
LEAD_RE = re.compile(r"^\s*(?:ข้อ\s*[0-9]+\s*)?ข้อ\s*([0-9]+(?:/[0-9]+)?)")


def norm(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").translate(THAI_DIGITS)).replace("“", "").replace("”", "")


def ann_of(cid: str) -> str:
    return cid.split("_")[0][3:]


def new_text(raw: str) -> str:
    """ข้อความที่ฉบับแก้ไขกำหนดให้ใช้แทน (ในเครื่องหมาย “…”) หรือทั้ง chunk ถ้าไม่มี"""
    m = QUOTED_RE.search(raw)
    text = m.group(1) if m else raw
    return re.split(r"\s*ประกาศนี้ให้ใช้บังคับ", text)[0]   # ตัดวันใช้บังคับ/ผู้ลงนามที่ต่อท้ายออก


def coverage(part: str, whole: str) -> float:
    """สัดส่วนของ part ที่พบใน whole (ทนต่อการแก้ไขบางส่วนและช่องว่าง)"""
    a, b = norm(part), norm(whole)
    if not a:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(blk.size for blk in sm.get_matching_blocks() if blk.size >= 8) / len(a)


BOILERPLATE_RE = re.compile(r"^\s*ข้อ\s*[0-9๐-๙]+\s*ประกาศนี้ให้ใช้บังคับ")


def is_boilerplate(raw: str) -> bool:
    """ข้อที่เนื้อหาทั้งข้อเป็นแค่วันใช้บังคับ + ผู้ลงนาม (ไม่ใช่ข้อที่มีเนื้อหาจริงแล้วต่อท้ายด้วยวันใช้บังคับ)"""
    return bool(BOILERPLATE_RE.match(raw))


def target_article(raw: str) -> str | None:
    r = raw.translate(THAI_DIGITS)
    m = RAW_TARGET_RE.search(r[:500])
    if m:
        return m.group(1)
    m = LEAD_RE.match(new_text(r).lstrip("“"))
    return m.group(1) if m else None


def primary_article(cid: str) -> str:
    """VAT57_ART_04_1 -> '4/1', VAT57_ART_05_A -> '5', VAT159_ART_05_1 -> '5/1'"""
    parts = cid.split("_")[2:]
    num = str(int(parts[0]))
    if len(parts) > 1 and parts[1].isdigit():
        num += "/" + parts[1]
    return num


def annotate(chunks: dict[str, dict]) -> dict[str, dict]:
    primaries = {cid: c for cid, c in chunks.items() if ann_of(cid) in PRIMARY}
    out: dict[str, dict] = {}

    for cid, c in chunks.items():
        ann = ann_of(cid)
        raw = c.get("official_raw_text", "")
        meta = {"is_boilerplate": is_boilerplate(raw)}
        if ann in PRIMARY:
            meta.update(role="primary", is_current=True, amended_by=[])
        elif ann in SPECIAL:
            meta.update(role="special", is_current=True)
        else:
            meta["role"] = "amendment"
            target_ann = AMENDS_TARGET[ann]
            if meta["is_boilerplate"]:
                meta.update(is_current=True, amends=[], amends_article=None, merge_coverage=None)
            else:
                art = target_article(raw)
                cands = {p: pc for p, pc in primaries.items()
                         if ann_of(p) == target_ann and (art is None or primary_article(p) == art)}
                if not cands:   # หาไม่เจอจากเลขข้อ → เทียบข้อความกับตัวบทหลักทั้งฉบับ
                    cands = {p: pc for p, pc in primaries.items() if ann_of(p) == target_ann}
                text = new_text(raw)
                scored = sorted(((coverage(text, pc["official_raw_text"]), p) for p, pc in cands.items()),
                                reverse=True)
                best = scored[0][1]
                union = "".join(pc["official_raw_text"] for _, pc in sorted(cands.items()))
                cov = max(scored[0][0], coverage(text, union))
                meta.update(amends=[best], amends_article=f"{target_ann}:ข้อ {art or primary_article(best)}",
                            merge_coverage=round(cov, 3))
        out[cid] = meta

    # amended_by (primary) + superseded_by (amendment ที่ไม่ current)
    by_target = defaultdict(list)
    for cid, m in out.items():
        for p in m.get("amends") or []:
            by_target[p].append(cid)
    for p, amendments in by_target.items():
        amendments.sort(key=lambda x: (int(ann_of(x)), x))
        out[p]["amended_by"] = amendments
        latest = max(int(ann_of(a)) for a in amendments)
        for a in amendments:
            m = out[a]
            m["is_current"] = int(ann_of(a)) == latest or m["merge_coverage"] >= CURRENT_MIN_COVERAGE
            if not m["is_current"]:
                m["superseded_by"] = sorted({ann_of(x) for x in amendments
                                             if int(ann_of(x)) > int(ann_of(a))}, key=int)
    return out


FIELD_ORDER = ["role", "is_current", "is_boilerplate", "amends", "amends_article",
               "merge_coverage", "superseded_by", "amended_by"]


def apply(chunk: dict, meta: dict) -> dict:
    md = {k: v for k, v in chunk["metadata"].items() if k not in FIELD_ORDER}
    for k in FIELD_ORDER:
        if k in meta:
            md[k] = meta[k]
    chunk["metadata"] = md
    return chunk


def dump(path: str, data) -> None:
    # รักษารูปแบบไฟล์เดิม: indent 2, UTF-8, CRLF, ไม่มีบรรทัดว่างท้ายไฟล์
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="เขียนผลลงไฟล์ chunk")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(ROOT, "vat*_chunks_local_llm.json")))
    per_file = {p: json.load(open(p, encoding="utf-8")) for p in files}
    chunks = {c["chunk_id"]: c for data in per_file.values() for c in data}
    result = annotate(chunks)

    print(f"{'chunk':18} {'role':10} {'cur':4} {'boiler':6} {'amends':16} {'article':10} {'cov':5} superseded_by / amended_by")
    for cid in sorted(result, key=lambda x: (int(ann_of(x)), x)):
        m = result[cid]
        extra = m.get("superseded_by") or m.get("amended_by") or ""
        print(f"{cid:18} {m['role']:10} {str(m['is_current'])[0]:4} {str(m['is_boilerplate'])[0]:6} "
              f"{','.join(m.get('amends') or []) or '-':16} {m.get('amends_article') or '-':10} "
              f"{'' if m.get('merge_coverage') is None else m['merge_coverage']:<5} {extra}")

    if args.write:
        for path, data in per_file.items():
            dump(path, [apply(c, result[c["chunk_id"]]) for c in data])
        combined_path = os.path.join(ROOT, COMBINED)
        combined = json.load(open(combined_path, encoding="utf-8"))
        dump(combined_path, [apply(c, result[c["chunk_id"]]) for c in combined])
        print(f"\nเขียนแล้ว: {len(files)} ไฟล์รายฉบับ + {COMBINED}")


if __name__ == "__main__":
    main()
