#!/usr/bin/env python3
"""
เทียบตัวบทใน chunk (official_raw_text) กับไฟล์ต้นฉบับ PDF ของประกาศแต่ละฉบับ

ต้นฉบับอยู่ที่ chunking/sources/dgvat{N}.pdf (ดึงข้อความด้วย `pdftotext` จาก poppler-utils) หรือ .docx
ฉบับที่เป็นภาพสแกน (ไม่มีชั้นข้อความ) ใส่ข้อความที่ถอดเองไว้ที่ chunking/sources/dgvat{N}.txt ได้

การเทียบใช้ "โครงข้อความ": ตัดช่องว่าง เครื่องหมายคำพูด/วรรคตอน วรรณยุกต์/สระบน-ล่าง และอักขระ Private Use
(PDF ราชกิจจาฯ เก็บวรรณยุกต์เป็น PUA และบางจุดวรรณยุกต์หาย) แปลงเลขไทยเป็นอารบิก
→ จับข้อความที่หาย/เกิน/ผิดคำได้ แต่ไม่จับความต่างระดับวรรณยุกต์/สระบนล่าง

รายงาน:
  chunk→ต้นฉบับ  สัดส่วนข้อความของ chunk ที่พบในต้นฉบับ (ต่ำ = chunk มีข้อความที่ไม่อยู่ในต้นฉบับ)
  ต้นฉบับ→chunk  สัดส่วนข้อความต้นฉบับ (หลังบท "อาศัยอำนาจ...ดังต่อไปนี้") ที่มี chunk ครอบคลุม
                 (ต่ำ = chunk ตกหล่น) เทียบทีละ chunk จึงไม่ขึ้นกับลำดับ chunk
  --detail       แสดงช่วงข้อความ (โครง) ที่ไม่ตรง ให้คนตรวจกับ PDF

ใช้งาน: python chunking/scripts/compare_sources.py [--detail]
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import os
import re
import subprocess
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
MARKS = re.compile("[ัิ-ฺ็-๎-]")
PUNCT = re.compile(r"[\s\"“”'‘’()\-–—.,:;_]+")
# หัวหน้าราชกิจจานุเบกษา (ใช้กับโครงข้อความหลังตัดวรรณยุกต์แล้ว)
_MONTHS = "มกราคม|กมภาพนธ|มนาคม|เมษายน|พฤษภาคม|มถนายน|กรกฎาคม|สงหาคม|กนยายน|ตลาคม|พฤศจกายน|ธนวาคม"
GAZETTE_NOISE = re.compile(r"เลม\d+ตอนท\d+ง|หนา\d+|ราชกจจานเบกษา|\d{1,2}(?:" + _MONTHS + r")\d{4}(?=ประกาศอธบด|$)")
PREAMBLE_END = "ดงตอไปน"   # "...ดังต่อไปนี้" ท้ายบทอาศัยอำนาจ — ก่อนหน้านี้คือหัวประกาศ ไม่นับ
MIN_BLOCK = 12
MIN_GAP = 6


def skeleton(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "").translate(THAI_DIGITS)
    t = t.replace("ำ", "า")  # ำ → า (คู่กับการตัด ํ)
    t = MARKS.sub("", t)
    t = PUNCT.sub("", t)
    return GAZETTE_NOISE.sub("", t)


def docx_text(path: str) -> str:
    """ข้อความจาก .docx (อ่าน word/document.xml โดยตรง ไม่ต้องติดตั้งไลบรารีเพิ่ม)"""
    import html
    import zipfile
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    return "\n".join(html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))) for p in paras)


def source_text(n: str) -> str | None:
    txt = os.path.join(SRC, f"dgvat{n}.txt")
    if os.path.exists(txt):
        return open(txt, encoding="utf-8").read()
    docx = os.path.join(SRC, f"dgvat{n}.docx")
    if os.path.exists(docx):
        return docx_text(docx)
    pdf = os.path.join(SRC, f"dgvat{n}.pdf")
    if not os.path.exists(pdf):
        return None
    out = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    return out if skeleton(out) else ""   # "" = PDF สแกน ไม่มีชั้นข้อความ


def _gaps(covered: list[bool], text: str) -> list[str]:
    gaps, start = [], None
    for i, ok in enumerate(covered + [True]):
        if not ok and start is None:
            start = i
        elif ok and start is not None:
            if i - start >= MIN_GAP:
                gaps.append(text[start:i])
            start = None
    return gaps


def coverage(a: str, sources: list[str]) -> tuple[float, list[str]]:
    """สัดส่วนของ a ที่พบใน sources ตัวใดก็ได้ + ช่วงของ a ที่ไม่พบ"""
    if not a:
        return 1.0, []
    covered = [False] * len(a)
    for b in sources:
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for blk in sm.get_matching_blocks():
            if blk.size >= MIN_BLOCK:
                covered[blk.a:blk.a + blk.size] = [True] * blk.size
    return sum(covered) / len(a), _gaps(covered, a)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detail", action="store_true", help="แสดงช่วงข้อความที่ไม่ตรง")
    args = ap.parse_args()

    by_ann: dict[str, list[dict]] = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "vat*_chunks_local_llm.json"))):
        n = re.search(r"vat(\d+)_", os.path.basename(path)).group(1)
        by_ann[n] = json.load(open(path, encoding="utf-8"))

    for n in sorted(by_ann, key=int):
        src = source_text(n)
        if src is None:
            print(f"ฉบับ {n:>3}: ยังไม่มีต้นฉบับใน sources/")
            continue
        if src == "":
            print(f"ฉบับ {n:>3}: PDF เป็นภาพสแกน — ใส่ข้อความถอดเองที่ sources/dgvat{n}.txt เพื่อเทียบ")
            continue
        s = skeleton(src)
        cut = s.find(PREAMBLE_END)
        body = s[cut + len(PREAMBLE_END):] if cut >= 0 else s
        chunks = by_ann[n]
        back, back_gaps = coverage(body, [skeleton(c["official_raw_text"]) for c in chunks])
        print(f"ฉบับ {n:>3}: ต้นฉบับ→chunk {back:6.1%}")
        for c in chunks:
            cov, gaps = coverage(skeleton(c["official_raw_text"]), [s])
            flag = "" if cov >= 0.98 else "  ← ตรวจ"
            print(f"    {c['chunk_id']:22} chunk→ต้นฉบับ {cov:6.1%}{flag}")
            if args.detail:
                for g in gaps:
                    print(f"        ไม่พบในต้นฉบับ: {g[:150]}")
        if args.detail:
            for g in back_gaps:
                print(f"    ต้นฉบับที่ไม่อยู่ใน chunk: {g[:150]}")


if __name__ == "__main__":
    main()
