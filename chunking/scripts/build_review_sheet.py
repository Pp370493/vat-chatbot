#!/usr/bin/env python3
"""
สร้างไฟล์ Excel ให้คนตรวจรับรองตัวบทใน chunk เทียบกับต้นฉบับ (แบบข้างกัน)

    python chunking/scripts/build_review_sheet.py [--out chunking/reports/ตรวจตัวบท_เทียบต้นฉบับ.xlsx]

- แท็บ "สรุปรายฉบับ": % ต้นฉบับที่มี chunk ครอบคลุม, % ต่ำสุดของ chunk, สถานะจาก sources/README.md
- แท็บ "ตรวจรายชิ้น": 1 แถวต่อ chunk — ข้อความใน chunk (ส่วนที่ไม่พบในต้นฉบับเป็นตัวแดง) คู่กับ
  ข้อความช่วงเดียวกันที่ดึงจากไฟล์ต้นฉบับ พร้อมช่อง ✓/✗ ให้ผู้ตรวจ
- แท็บ "ต้นฉบับที่ไม่อยู่ใน chunk": ข้อความในต้นฉบับ (หลังบทอาศัยอำนาจ) ที่ไม่มี chunk ไหนครอบคลุม
ใช้วิธีเทียบเดียวกับ compare_sources.py (โครงข้อความ: ตัดวรรณยุกต์ วรรคตอน ช่องว่าง)
ต้องติดตั้ง openpyxl
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_sources as cs  # noqa: E402

from openpyxl import Workbook  # noqa: E402
from openpyxl.cell.rich_text import CellRichText, TextBlock  # noqa: E402
from openpyxl.cell.text import InlineFont  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402

ROOT = cs.ROOT
# อักขระ Private Use ที่ฟอนต์ไทยใน PDF ใช้แทนวรรณยุกต์/สระ (ตำแหน่งเลื่อน) → อักขระมาตรฐาน
PUA = {0xF700: "ฐ", 0xF70F: "ญ", 0xF710: "ั", 0xF711: "ํ", 0xF712: "็", 0xF718: "ุ", 0xF719: "ู", 0xF71A: "ฺ"}
for base, marks in ((0xF701, "่้๊๋"), (0xF705, "่้๊๋์"), (0xF70A, "่้๊๋์"), (0xF713, "่้๊๋์")):
    for i, m in enumerate(marks):
        PUA.setdefault(base + i, m)


def clean_pua(t: str) -> str:
    return (t or "").translate(PUA)


def skeleton_map(text: str) -> tuple[str, list[int]]:
    """โครงข้อความแบบเดียวกับ cs.skeleton พร้อมตำแหน่งในข้อความเดิมของแต่ละอักขระ"""
    out, idx = [], []
    for i, ch in enumerate(text or ""):
        ch = unicodedata.normalize("NFC", ch).translate(cs.THAI_DIGITS).replace("ำ", "า")
        for c in ch:
            if cs.MARKS.fullmatch(c) or cs.PUNCT.fullmatch(c):
                continue
            out.append(c)
            idx.append(i)
    sk = "".join(out)
    keep = [True] * len(sk)
    for m in cs.GAZETTE_NOISE.finditer(sk):
        keep[m.start():m.end()] = [False] * (m.end() - m.start())
    return "".join(c for c, k in zip(sk, keep) if k), [p for p, k in zip(idx, keep) if k]


def match_blocks(a: str, b: str) -> list:
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [blk for blk in sm.get_matching_blocks() if blk.size >= cs.MIN_BLOCK]


def raw_spans(covered: list[bool], idx: list[int], raw: str) -> list[tuple[int, int, bool]]:
    """แปลงสถานะพบ/ไม่พบรายอักขระของโครง เป็นช่วงในข้อความเดิม [(start, end, found)]"""
    if not raw:
        return []
    found_raw = [True] * len(raw)
    for k, ok in enumerate(covered):
        if not ok:
            lo = idx[k]
            hi = idx[k + 1] if k + 1 < len(idx) else lo + 1
            for j in range(lo, min(hi, len(raw))):
                found_raw[j] = False
    spans, start = [], 0
    for j in range(1, len(raw) + 1):
        if j == len(raw) or found_raw[j] != found_raw[start]:
            spans.append((start, j, found_raw[start]))
            start = j
    return spans


def gap_mask(covered: list[bool]) -> list[bool]:
    """ช่วงไม่พบที่สั้นกว่า MIN_GAP ถือว่าพบ (สอดคล้องกับ compare_sources --detail)"""
    out, start = list(covered), None
    for i, ok in enumerate(covered + [True]):
        if not ok and start is None:
            start = i
        elif ok and start is not None:
            if i - start < cs.MIN_GAP:
                out[start:i] = [True] * (i - start)
            start = None
    return out


def readme_status() -> dict[str, str]:
    path = os.path.join(cs.SRC, "README.md")
    status = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            status[m.group(1)] = (m.group(2), m.group(3))
    return status


HEAD = PatternFill("solid", fgColor="1F4E78")
FILL = PatternFill("solid", fgColor="FFF2CC")
WARN = PatternFill("solid", fgColor="FBE4D5")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
RED = InlineFont(color="C00000", b=True)


def header(ws, cols):
    ws.append([c for c, _ in cols])
    for i, (_, w) in enumerate(cols, 1):
        c = ws.cell(row=1, column=i)
        c.fill, c.font, c.alignment, c.border = HEAD, Font(bold=True, color="FFFFFF"), WRAP, BOX
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "reports", "ตรวจตัวบท_เทียบต้นฉบับ.xlsx"))
    args = ap.parse_args()

    status = readme_status()
    by_ann: dict[str, list[dict]] = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "vat*_chunks_local_llm.json"))):
        n = re.search(r"vat(\d+)_", os.path.basename(path)).group(1)
        by_ann[n] = json.load(open(path, encoding="utf-8"))

    wb = Workbook()
    ws_sum = wb.active
    ws_sum.title = "สรุปรายฉบับ"
    header(ws_sum, [("ฉบับ", 8), ("ไฟล์ต้นฉบับ", 16), ("จำนวน chunk", 10), ("ต้นฉบับที่มี chunk ครอบคลุม", 14),
                    ("chunk ที่ตรงน้อยสุด", 22), ("สถานะการตรวจ (sources/README.md)", 80), ("ผู้ตรวจรับรอง", 14),
                    ("วันที่", 12)])
    ws = wb.create_sheet("ตรวจรายชิ้น")
    header(ws, [("chunk id", 18), ("ฉบับ", 7), ("ข้อ", 26), ("ไฟล์ต้นฉบับ", 15), ("ตรงกับต้นฉบับ", 10),
                ("ข้อความใน chunk (ตัวแดง = ไม่พบในต้นฉบับ)", 70), ("ข้อความช่วงเดียวกันจากต้นฉบับ", 70),
                ("ถูกต้องไหม (✓/✗)", 10), ("ถ้าผิด: ควรแก้เป็น", 40), ("หมายเหตุ", 25)])
    ws_gap = wb.create_sheet("ต้นฉบับที่ไม่อยู่ใน chunk")
    header(ws_gap, [("ฉบับ", 8), ("ข้อความในต้นฉบับที่ไม่มี chunk ครอบคลุม", 110), ("ควรเพิ่มเข้า chunk ไหม (✓/✗)", 14),
                    ("หมายเหตุ", 30)])

    for n in sorted(by_ann, key=int):
        chunks = by_ann[n]
        fname, note = status.get(n, ("", ""))
        src = cs.source_text(n)
        scanned = src == ""
        src_clean = clean_pua(src or "")
        s_sk, s_idx = skeleton_map(src_clean)
        cut = s_sk.find(cs.PREAMBLE_END)
        body_from = cut + len(cs.PREAMBLE_END) if cut >= 0 else 0

        covered_src = [False] * len(s_sk)
        worst = (2.0, "")
        for c in chunks:
            raw = c["official_raw_text"]
            c_sk, c_idx = skeleton_map(raw)
            if scanned or not s_sk:
                cov, rich, excerpt = None, raw, f"(ต้นฉบับเป็นภาพสแกน — เปิด sources/{fname or f'dgvat{n}.pdf'} เทียบด้วยตา)"
            else:
                blocks = match_blocks(c_sk, s_sk)
                cov_c = [False] * len(c_sk)
                for b in blocks:
                    cov_c[b.a:b.a + b.size] = [True] * b.size
                    covered_src[b.b:b.b + b.size] = [True] * b.size
                cov = sum(cov_c) / len(c_sk) if c_sk else 1.0
                spans = raw_spans(gap_mask(cov_c), c_idx, raw)
                if all(f for _, _, f in spans):
                    rich = raw
                else:
                    rich = CellRichText([TextBlock(RED, raw[a:b]) if not f else raw[a:b] for a, b, f in spans])
                if blocks:
                    lo = s_idx[blocks[0].b]
                    last = blocks[-1]
                    hi = s_idx[min(last.b + last.size, len(s_idx) - 1)]
                    excerpt = " ".join(src_clean[lo:hi + 1].split())
                else:
                    excerpt = "(ไม่พบช่วงที่ตรงในต้นฉบับ)"
                worst = min(worst, (cov, c["chunk_id"]))
            ws.append([c["chunk_id"], n, c.get("article_ref", ""), fname, cov, None, excerpt, "", "", ""])
            r = ws.max_row
            ws.cell(row=r, column=6).value = rich
            ws.cell(row=r, column=5).number_format = "0.0%"
            for col in range(1, 11):
                cell = ws.cell(row=r, column=col)
                cell.alignment, cell.border = WRAP, BOX
                if col >= 8:
                    cell.fill = FILL
            if cov is not None and cov < 0.98:
                ws.cell(row=r, column=5).fill = WARN
            ws.row_dimensions[r].height = 160

        if scanned or not s_sk:
            back_txt, worst_txt = "ภาพสแกน", "ตรวจด้วยตา"
        else:
            body_cov = covered_src[body_from:]
            back = sum(body_cov) / len(body_cov) if body_cov else 1.0
            back_txt = f"{back:.1%}"
            worst_txt = f"{worst[1]} ({worst[0]:.1%})"
            mask = gap_mask(covered_src)
            for a, b, f in raw_spans(mask[body_from:], s_idx[body_from:], src_clean):
                text = " ".join(src_clean[a:b].split())
                if not f and len(text) >= 15:
                    ws_gap.append([n, text, "", ""])
                    for col in range(1, 5):
                        cell = ws_gap.cell(row=ws_gap.max_row, column=col)
                        cell.alignment, cell.border = WRAP, BOX
                        if col >= 3:
                            cell.fill = FILL
        ws_sum.append([n, fname, len(chunks), back_txt, worst_txt, note, "", ""])
        for col in range(1, 9):
            cell = ws_sum.cell(row=ws_sum.max_row, column=col)
            cell.alignment, cell.border = WRAP, BOX
            if col >= 7:
                cell.fill = FILL

    dv = DataValidation(type="list", formula1='"✓,✗"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H2:H{ws.max_row}")
    ws.auto_filter.ref = f"A1:J{ws.max_row}"
    ws_sum.append([])
    ws_sum.append(["หมายเหตุ: ข้อความจากต้นฉบับ PDF ดึงอัตโนมัติ วรรณยุกต์บางตัวอาจเพี้ยน ให้ยึดไฟล์ PDF เป็นหลัก "
                   "ตัวแดงในแท็บ 'ตรวจรายชิ้น' คือข้อความใน chunk ที่ไม่พบในต้นฉบับ (เช่น คำนำ 'ข้อ 2 “ข้อ 5' ที่ chunker เติม)"])
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    wb.save(args.out)
    print(f"{args.out}  ({ws.max_row - 1} chunks, ต้นฉบับที่ไม่อยู่ใน chunk {ws_gap.max_row - 1} ช่วง)")


if __name__ == "__main__":
    main()
