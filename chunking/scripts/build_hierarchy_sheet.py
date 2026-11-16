#!/usr/bin/env python3
"""
สร้างไฟล์ Excel ให้คนตรวจลำดับชั้นตัวบท จาก hierarchy/vat_hierarchy.json (สร้างโดย build_hierarchy.py)

    python chunking/scripts/build_hierarchy_sheet.py   # -> reports/ตรวจลำดับชั้นตัวบท.xlsx

ต้องติดตั้ง openpyxl
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "hierarchy", "vat_hierarchy.json")
OUT = os.path.join(ROOT, "reports", "ตรวจลำดับชั้นตัวบท.xlsx")

LEVEL_TH = {"announcement": "ประกาศ", "article": "ข้อ", "paragraph": "วรรค", "clause": "อนุ (1)", "item": "ย่อย (ก)",
            "content": "ข้อความใหม่ (ฉบับแก้ไข)", "note": "หมายเหตุการแก้ไข", "group": "กลุ่ม (แนบท้าย)", "external": "กฎหมายอื่น"}
ANN_FILL = {"57": "DCE6F2", "159": "DDEFE9", "234": "FCEBD3"}
AMEND_FILL = "F2F2F2"
HEAD = PatternFill("solid", fgColor="1F4E78")
FILL_IN = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")


def sheet(wb, title, cols, first=False):
    ws = wb.active if first else wb.create_sheet(title)
    ws.title = title
    ws.append([c for c, _ in cols])
    for i, (_, w) in enumerate(cols, 1):
        c = ws.cell(row=1, column=i)
        c.fill, c.font, c.alignment, c.border = HEAD, Font(bold=True, color="FFFFFF"), WRAP, BOX
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"
    return ws


def style_row(ws, fill_hex=None, input_cols=()):
    r = ws.max_row
    for c in ws[r]:
        c.alignment, c.border = WRAP, BOX
        if c.column in input_cols:
            c.fill = FILL_IN
        elif fill_hex:
            c.fill = PatternFill("solid", fgColor=fill_hex)


def check_dv(ws, col, n):
    dv = DataValidation(type="list", formula1='"✓,✗"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col}2:{col}{n + 1}")


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    nodes = data["nodes"]
    N = {n["id"]: n for n in nodes}
    depth = {}
    for n in nodes:
        d, p = 0, n.get("parent")
        while p:
            d += 1
            p = N.get(p, {}).get("parent")
        depth[n["id"]] = d
    out_ref, in_ref, amends, amended = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    refs, ams = [], []
    for e in data["edges"]:
        if e["kind"] == "refers_to":
            out_ref[e["s"]].append(f"“{e['phrase']}” → {N[e['t']]['label']}")
            in_ref[e["t"]].append(N[e["s"]]["label"])
            refs.append(e)
        elif e["kind"] == "amends":
            amends[e["s"]].append(N.get(e["t"], {"label": e["t"]})["label"])
            amended[e["t"]].append(N[e["s"]]["label"])
            ams.append(e)

    def fill_of(n):
        if n["level"] == "external":
            return None
        return ANN_FILL.get(n.get("ann", ""), AMEND_FILL)

    wb = Workbook()
    ws = sheet(wb, "วิธีอ่าน", [("", 130)], first=True)
    ws.delete_rows(1)
    for t, b in [
        ("ไฟล์ตรวจลำดับชั้นตัวบท (chunking ใหม่)", True),
        ("แตกตัวบททุกประกาศทุกข้อเป็น ข้อ → วรรค → อนุ (1) → ย่อย (ก) และเชื่อมจุดที่อ้างถึงกัน · ข้อความมาจาก chunk เดิมที่ตรวจเทียบต้นฉบับแล้ว (ไม่ได้แก้ข้อความ)", False),
        ("", False),
        ("รหัส node", True),
        ("VAT57/5 = ฉบับ 57 ข้อ 5 · VAT57/5/p2 = ข้อ 5 วรรคสอง · VAT57/5/3 = ข้อ 5 (3) · VAT57/5/3/ก = ข้อ 5 (3) (ก) · VAT57/4_1 = ข้อ 4/1", False),
        ("ฉบับแก้ไข: VAT215/2 = ฉบับ 215 ข้อ 2 (ข้อความคือคำสั่งแก้ไข) · VAT215/2/ใหม่ = ข้อความใหม่ที่ฉบับนั้นใส่แทน แตกชั้นต่อเหมือนตัวบทหลัก", False),
        ("EXT/ประมวลรัษฎากร/ม.81/3 = กฎหมายอื่นที่ตัวบทอ้างถึง", False),
        ("", False),
        ("สีพื้นแถว: ฟ้า = ฉบับ 57 (ยื่นกระดาษ) · เขียว = ฉบับ 159 (ยื่นอินเทอร์เน็ต) · ส้ม = ฉบับ 234 (DBD) · เทา = ฉบับแก้ไข · ช่องสีเหลือง = ช่องให้กรอก", False),
        ("", False),
        ("สิ่งที่ขอให้ตรวจ", True),
        ("1. แท็บ ลำดับชั้น — วรรค/อนุ/ย่อย อยู่ใต้ข้อที่ถูกต้องไหม (ดูคอลัมน์ 'อยู่ใต้' และการย่อหน้าของชื่อ) ข้อความถูกแบ่งตรงจุดไหม", False),
        ("2. แท็บ การอ้างอิง — วลีในตัวบทชี้ไปที่ข้อ/อนุ/วรรคที่ถูกต้องไหม เช่น 'ตาม (1) ถึง (3)' ใน 159 ข้อ 5 (4)", False),
        ("3. แท็บ การแก้ไข — ฉบับแก้ไขแต่ละข้อแก้ที่ระดับที่ถูกต้องไหม เช่น ฉบับ 215 ข้อ 2 แก้ 57 ข้อ 5 (5) (ก)", False),
        ("ใส่ ✓ หรือ ✗ ในช่องสีเหลือง ถ้าผิดเขียนสิ่งที่ถูกในช่องถัดไป ไม่ต้องตรวจครบทุกแถว — เริ่มจากฉบับ 57 และ 159 ก่อนได้", False),
    ]:
        ws.append([t])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=b, size=14 if ws.max_row == 1 else 11)
        ws.cell(row=ws.max_row, column=1).alignment = Alignment(wrap_text=True)

    # ---- ลำดับชั้น
    cols = [("ฉบับ", 7), ("รหัส", 22), ("ระดับ", 14), ("ชื่อเต็ม (ย่อหน้าตามระดับ)", 42), ("อยู่ใต้", 30),
            ("ข้อความ", 70), ("อ้างถึง", 40), ("ถูกอ้างโดย", 32), ("แก้ที่ / แก้โดย", 32), ("ยังมีผล", 8),
            ("chunk เดิม", 18), ("ถูกต้องไหม (✓/✗)", 10), ("ถ้าผิด ควรเป็นอย่างไร", 36)]
    ws = sheet(wb, "ลำดับชั้น", cols)
    count = 0
    for n in nodes:
        if n["level"] == "external":
            continue
        am = ([f"แก้ที่: {x}" for x in amends[n["id"]]] + [f"แก้โดย: {x}" for x in amended[n["id"]]])
        ws.append([n.get("ann", ""), n["id"], LEVEL_TH.get(n["level"], n["level"]),
                   "    " * max(depth[n["id"]] - 1, 0) + n["label"], N.get(n.get("parent") or "", {}).get("label", ""),
                   n.get("own_text", ""), "\n".join(out_ref[n["id"]]), "\n".join(dict.fromkeys(in_ref[n["id"]])),
                   "\n".join(am), "ใช่" if n.get("current", True) else "ไม่ (ถูกแทนที่)",
                   ", ".join(n.get("chunk_ids") or []), "", ""])
        style_row(ws, fill_of(n), input_cols=(12, 13))
        if n["level"] in ("announcement", "article"):
            for c in ws[ws.max_row][:4]:
                c.font = Font(bold=True)
        count += 1
    check_dv(ws, "L", count)
    ws.auto_filter.ref = f"A1:M{count + 1}"

    # ---- การอ้างอิง
    ws = sheet(wb, "การอ้างอิง", [("จาก", 36), ("วลีในตัวบท", 26), ("ไปที่", 36), ("ข้อความต้นของปลายทาง", 60),
                                  ("ถูกต้องไหม (✓/✗)", 10), ("ถ้าผิด ควรชี้ไปที่", 30)])
    for e in refs:
        s, t = N[e["s"]], N[e["t"]]
        ws.append([s["label"], e["phrase"], t["label"], (t.get("own_text") or "")[:220], "", ""])
        style_row(ws, fill_of(s), input_cols=(5, 6))
    check_dv(ws, "E", len(refs))
    ws.auto_filter.ref = f"A1:F{len(refs) + 1}"

    # ---- การแก้ไข
    ws = sheet(wb, "การแก้ไข", [("ฉบับแก้ไข", 36), ("คำสั่งแก้ไข (ข้อความในตัวบท)", 70), ("แก้ที่", 36),
                                ("ถูกต้องไหม (✓/✗)", 10), ("ถ้าผิด ควรเป็น", 30)])
    for e in ams:
        s = N[e["s"]]
        art = N.get(s.get("parent") or "", s)
        instr = art.get("own_text") or e.get("phrase", "")
        ws.append([s["label"], instr, N.get(e["t"], {"label": e["t"]})["label"], "", ""])
        style_row(ws, None, input_cols=(4, 5))
    check_dv(ws, "D", len(ams))

    # ---- สรุปรายฉบับ
    ws = sheet(wb, "สรุปรายฉบับ", [("ฉบับ", 8), ("ข้อ", 8), ("วรรค", 8), ("อนุ", 8), ("ย่อย", 8), ("ข้อความใหม่", 12),
                                  ("อ้างถึงที่อื่น", 12), ("ถูกแก้ (ระดับย่อย)", 14)])
    per = defaultdict(lambda: defaultdict(int))
    for n in nodes:
        if n["level"] != "external":
            per[n.get("ann", "")][n["level"]] += 1
    for e in refs:
        per[N[e["s"]].get("ann", "")]["refs"] += 1
    for e in ams:
        per[N.get(e["t"], {}).get("ann", "")]["amended"] += 1
    for ann in sorted((a for a in per if a), key=int):
        d = per[ann]
        ws.append([ann, d["article"], d["paragraph"], d["clause"], d["item"], d["content"], d["refs"], d["amended"]])
        style_row(ws, ANN_FILL.get(ann, AMEND_FILL))
    cov = data.get("coverage", [])
    ok = sum(1 for r in cov if r["coverage"] >= 0.995)
    ws.append([])
    ws.append([f"ตรวจความครบ: ข้อความของ chunk เดิม {ok} จาก {len(cov)} ชิ้นอยู่ครบใน node · การอ้างอิงที่หาเป้าหมายไม่เจอ {len(data.get('unresolved', []))} จุด"])

    wb.save(OUT)
    print(f"{OUT}: node {count} แถว · อ้างอิง {len(refs)} · แก้ไข {len(ams)}")


if __name__ == "__main__":
    main()
