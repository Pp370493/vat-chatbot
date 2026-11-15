#!/usr/bin/env python3
"""
แก้ keyword ใน metadata ที่ทำให้ค้นผิดข้อ (ไม่แตะข้อความตัวบท official_raw_text)

    python chunking/scripts/fix_keywords.py           # แสดงสิ่งที่จะเปลี่ยน
    python chunking/scripts/fix_keywords.py --write   # เขียนลงไฟล์ chunk (รายฉบับ + all_10)

กฎ (ตามคำเตือนหมวด keywords ใน validate_chunks.py):
1. chunk ฉบับแก้ไข (role=amendment): keyword "ข้อ N" ที่เป็นเลขข้อของฉบับแก้ไขเอง (ไม่ใช่ข้อของตัวบทหลักที่ถูกแก้)
   → เปลี่ยนเป็นข้อของตัวบทหลักพร้อมฉบับ เช่น VAT139_ART_02 "ข้อ 2" → "ข้อ 9 ฉบับที่ 57"
   ผู้ใช้ที่ถาม "ข้อ 2" หมายถึงข้อ 2 ของตัวบทหลัก จึงไม่ควรดึงฉบับแก้ไขที่บังเอิญเป็นข้อ 2
keyword สั้นที่ validate_chunks เตือน (เซ็น, LTO, DBD, JV, หจก, 81/3, ภพ20 ...) คงไว้: ทดลองตัด "เซ็น" แล้ว
หมวดผู้มีอำนาจลงนาม (ข้อ 9) ค้นถูกลดจาก 100% เหลือ 90% — ทุก chunk ที่มี "เซ็น" อยู่ในสายข้อ 9 จริง
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBINED = "all_10_announcements_chunks_official.json"
ARTICLE_KW = re.compile(r"^ข้อ\s*(\d+(?:/\d+)?)$")
OWN_ARTICLE = re.compile(r"_ART_(\d+)")
KW_FIELDS = ("boost_keywords", "tfidf_keywords")


def fix_chunk(c: dict) -> list[str]:
    md, changes = c["metadata"], []
    m_own = OWN_ARTICLE.search(c["chunk_id"])
    own = m_own.group(1).lstrip("0") if m_own else None
    target = None
    if md.get("role") == "amendment" and md.get("amends_article"):
        ann, art = md["amends_article"].split(":")
        target = (ann, art.replace("ข้อ", "").strip())
    for field in KW_FIELDS:
        new, seen = [], set()
        for kw in md.get(field, []):
            m = ARTICLE_KW.match(kw.strip())
            if target and m and m.group(1) == own and own != target[1]:
                repl = f"ข้อ {target[1]} ฉบับที่ {target[0]}"
                changes.append(f"{field}: '{kw}' → '{repl}'")
                kw = repl
            if kw not in seen:
                seen.add(kw)
                new.append(kw)
        md[field] = new
    return changes


def dump(path: str, data) -> None:
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, "vat*_chunks_local_llm.json"))) + [os.path.join(ROOT, COMBINED)]
    total = 0
    for i, path in enumerate(files):
        data = json.load(open(path, encoding="utf-8"))
        for c in data:
            ch = fix_chunk(c)
            if ch and not path.endswith(COMBINED):
                total += 1
                print(c["chunk_id"])
                for x in ch:
                    print("   ", x)
        if args.write:
            dump(path, data)
    print(f"\nchunk ที่เปลี่ยน: {total}" + ("  (เขียนแล้ว)" if args.write else "  (ยังไม่เขียน — ใส่ --write)"))


if __name__ == "__main__":
    main()
