"""สร้างแม่แบบ Excel สำหรับเตรียมข้อมูลปรับจูน (ต้องติดตั้ง openpyxl): python scripts/make_tuning_template.py"""
import csv, json, random, re, sys
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from pathlib import Path
B = str(Path(__file__).resolve().parent.parent) + "/"
sys.path.insert(0, B)
rows = list(csv.DictReader(open(B + "data/synthetic_dataset_vat_intent.csv", encoding="utf-8-sig")))
arts = json.load(open(B + "data/official_vat_articles.json", encoding="utf-8"))
A = {a["id"]: a for a in arts}
from app.agents.agent6_risk_tier import RISK_RULES, clause_text

HEAD = PatternFill("solid", fgColor="1F4E78"); HFONT = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="FFF2CC")   # ช่องที่ต้องกรอก
GREY = PatternFill("solid", fgColor="F2F2F2")
thin = Side(style="thin", color="BFBFBF"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
GROUP_TH = {"IN_SCOPE_VAT": "ปกติ", "HIGH_RISK_SECTION_6": "เสี่ยง", "OUT_OF_SCOPE": "นอกขอบเขต"}

def sheet(ws, headers, widths, fill_cols):
    ws.append(headers)
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        c = ws.cell(row=1, column=i); c.fill = HEAD; c.font = HFONT; c.alignment = WRAP; c.border = BOX
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"; ws.row_dimensions[1].height = 36
    return [headers.index(h) + 1 for h in fill_cols]

def style_rows(ws, fill_idx):
    for r in ws.iter_rows(min_row=2):
        for c in r:
            c.alignment = WRAP; c.border = BOX
            if c.column in fill_idx: c.fill = FILL

def dv(ws, col, options, n):
    d = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    ws.add_data_validation(d); d.add(f"{col}2:{col}{n+1}")

wb = Workbook()

# ---------- วิธีกรอก
ws = wb.active; ws.title = "วิธีกรอก"
lines = [
    ("แม่แบบเตรียมข้อมูลปรับจูน VAT Copilot", True),
    ("ช่องสีเหลือง = ช่องที่ต้องกรอก · ช่องสีขาว = ระบบเติมไว้ให้แล้ว (แก้ได้ถ้าผิด) · คลิกช่องที่มีลูกศรเพื่อเลือกจากรายการ", False),
    ("", False),
    ("ลำดับที่ควรทำ", True),
    ("1. แท็บ 1_ชุดเฉลย — สำคัญที่สุด: เติมคำตอบที่ถูก ข้อที่ต้องอ้าง และสิ่งที่ห้ามมีในคำตอบ (คำถาม 100 ข้อคัดจากชุดเดิมไว้แล้ว ลบหรือเพิ่มข้อได้)", False),
    ("2. แท็บ 2_ตรวจตัวบท — ตัวบท 75 ชิ้นในระบบ ตรวจว่าตรงประกาศฉบับล่าสุด ถ้าผิดเขียนข้อความที่ถูกในช่อง 'แก้ไขเป็น'", False),
    ("3. แท็บ 3_เกณฑ์ข้อ6 — ตัวบทและคำที่ระบบใช้จับเคสเสี่ยงอยู่ตอนนี้ เติมสถานการณ์ ตัวอย่าง และตัวอย่างที่ดูเสี่ยงแต่ไม่เสี่ยง", False),
    ("4. แท็บ 4_เอกสาร — รายการเอกสารแยกตามช่องทาง × ประเภทผู้ยื่น (1 เอกสารต่อ 1 บรรทัด แทรกบรรทัดเพิ่มได้)", False),
    ("เวลาน้อย: ทำแท็บ 1, 3, 4 ก่อน", False),
    ("", False),
    ("หลักการกรอกคำตอบที่ถูก (แท็บ 1)", True),
    ("• สั้น 2–3 บรรทัด ตอบตรงคำถาม เขียนแบบที่อยากให้ระบบตอบผู้เสียภาษีจริง", False),
    ("• ข้อที่ต้องอ้าง เขียนรูปแบบ 'ฉบับ 57 ข้อ 5' หรือ 'ฉบับ 159 ข้อ 5' (คั่นด้วย / ถ้ามีหลายข้อ)", False),
    ("• สิ่งที่ห้ามมีในคำตอบ = ข้อผิดที่พบบ่อย เช่น 'สำเนาบัตรประชาชน', 'ยื่นที่สาขาได้' (คั่นด้วย ;) — ระบบจะใช้ตรวจคำตอบอัตโนมัติ", False),
    ("• ถ้าคำถามไม่ระบุช่องทาง และคำตอบต่างกันตามช่องทาง ให้เลือกช่องทาง 'ไม่ระบุ' และเขียนคำตอบว่าระบบควรถามกลับ", False),
    ("• คำถามที่ไม่ชัดหรือตอบไม่ได้จากประกาศ ให้ใส่ ✗ ในช่อง 'ใช้ข้อนี้ไหม' แทนการลบ", False),
    ("", False),
    ("ส่งกลับ: บันทึกไฟล์นี้ (.xlsx) แล้วแนบในแชท ไม่ต้องกรอกครบในครั้งเดียว ส่งเป็นชุดๆ ได้ (ทำลำดับ 1 ราว 30–50 ข้อก่อนก็เริ่มปรับระบบได้)", True),
]
for t, b in lines:
    ws.append([t]); ws.cell(row=ws.max_row, column=1).font = Font(bold=b, size=14 if ws.max_row == 1 else 11)
ws.column_dimensions["A"].width = 140

# ---------- 1_ชุดเฉลย
rnd = random.Random(11)
by = defaultdict(list)
for r in rows: by[(r["group"], r["sub_category"])].append(r)
quota = {"IN_SCOPE_VAT": 4, "HIGH_RISK_SECTION_6": 4, "OUT_OF_SCOPE": 3}
picked = []
for g in ["IN_SCOPE_VAT", "HIGH_RISK_SECTION_6", "OUT_OF_SCOPE"]:
    for (gg, sub), lst in sorted(by.items()):
        if gg == g: picked += rnd.sample(lst, min(quota[g], len(lst)))
ws = wb.create_sheet("1_ชุดเฉลย")
H = ["id", "กลุ่ม", "หมวดย่อย", "คำถาม", "ข้อที่ระบบคาดว่าเกี่ยวข้อง (จากชุดเดิม)",
     "ใช้ข้อนี้ไหม (✓/✗)", "กลุ่มที่ถูก", "ช่องทาง", "คำตอบที่ถูก (2–3 บรรทัด)", "ข้อที่ต้องอ้าง",
     "สิ่งที่ห้ามมีในคำตอบ (คั่นด้วย ;)", "เคสเสี่ยง: เข้าข้อ 6 อนุไหน", "ผู้ตรวจ", "หมายเหตุ"]
fi = sheet(ws, H, [9, 10, 22, 45, 24, 9, 11, 12, 55, 20, 30, 14, 12, 25],
           H[5:])
for r in picked:
    ws.append([r["id"], GROUP_TH[r["group"]], r["sub_category"], r["query"], r["target_clause_or_agency"],
               "✓", GROUP_TH[r["group"]], "", "", "", "", "", "", ""])
style_rows(ws, fi)
n = len(picked)
dv(ws, "F", ["✓", "✗"], n); dv(ws, "G", ["ปกติ", "เสี่ยง", "นอกขอบเขต"], n)
dv(ws, "H", ["กระดาษ (57)", "อินเทอร์เน็ต (159)", "DBD (234)", "ไม่ระบุ", "ไม่เกี่ยว"], n)
dv(ws, "L", ["(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)", "หลายข้อ", "-"], n)
for i in range(2, n + 2): ws.row_dimensions[i].height = 48
ws.auto_filter.ref = f"A1:{get_column_letter(len(H))}{n+1}"

# ---------- 3_เกณฑ์ข้อ6
ws = wb.create_sheet("3_เกณฑ์ข้อ6")
H = ["อนุข้อ", "ตัวบท (ฉบับ 57 / 159)", "คำที่ระบบใช้จับอยู่ตอนนี้", "ตัวอย่างคำถามจากชุดเดิม",
     "สถานการณ์/คำที่บ่งชี้เพิ่ม", "ตัวอย่างคำถามเสี่ยงเพิ่ม (3–5)", "ตัวอย่างที่ดูเสี่ยงแต่ไม่เสี่ยง",
     "ระบบควรทำอะไร", "หมายเหตุ"]
fi = sheet(ws, H, [8, 60, 40, 50, 35, 45, 45, 18, 25], H[4:])
art57, art159 = A["VAT57_ART_06"]["content"], A["VAT159_ART_06"]["content"]
risk_rows = [r for r in rows if r["group"] == "HIGH_RISK_SECTION_6"]
def readable(pat):
    out = []
    for alt in pat.split("|"):
        alt = re.sub(r"\(\?!.*?\)", "", alt)
        alt = re.sub(r"\.\{\d*,?\d*\}", "…", alt)
        alt = alt.replace("\\.", ".").replace("?", "").replace(" ", " ")
        out.append(alt.strip())
    return ", ".join(a for a in out if a)

def kw(num):
    out = []
    for label, pat, _ in RISK_RULES:
        if f"({num})" in label or (num in "78" and "(7)/(8)" in label):
            out.append(readable(pat.pattern))
    return "\n".join(out)
SUBMAP = {"1": "เอกสารเท็จ", "2": "ตัวแทนเชิด", "3": "ไม่มีสถานประกอบการจริง", "4": "สนง.บัญชี",
          "5": "มิได้ประกอบการจริง", "6": "เพิกถอน", "7": "ไม่นำส่งเอกสาร", "8": "ไม่อัปโหลด"}
for num in "12345678":
    t57, t159 = clause_text(art57, num), clause_text(art159, num)
    text = (f"57: {t57}\n" if t57 else "") + (f"159: {t159}" if t159 and t159 != t57 else ("159: (เหมือน 57)" if t159 else ""))
    ex = [r["query"] for r in risk_rows if SUBMAP[num] in r["sub_category"]][:4]
    ws.append([f"({num})", text.strip() or "(ไม่พบในตัวบทที่ระบบมี — โปรดตรวจ)", kw(num), "\n".join("• " + e for e in ex),
               "", "", "", "", ""])
ws.append(["อื่นๆ", "ขอวิธีหลบเลี่ยงการตรวจสอบ (ไม่ใช่อนุข้อในประกาศ — ระบบเพิ่มเอง)", kw("x") or
           readable([p.pattern for l, p, _ in RISK_RULES if "หลบเลี่ยง" in l][0]), "", "", "", "", "", ""])
style_rows(ws, fi)
dv(ws, "H", ["ส่งหัวหน้างาน", "ถามข้อมูลเพิ่มก่อน", "ตอบได้แต่เตือน"], 9)
for i in range(2, 11): ws.row_dimensions[i].height = 150

# ---------- 4_เอกสาร
ws = wb.create_sheet("4_เอกสาร")
H = ["ช่องทาง", "ประเภทผู้ยื่น", "ตัวบทที่น่าจะเกี่ยวข้อง", "เอกสาร (1 รายการต่อบรรทัด)", "ต้นฉบับ/สำเนา",
     "จำนวน", "ใช้เมื่อ (เงื่อนไข)", "ข้อที่อ้าง", "ไม่ต้องใช้/ห้ามขอ", "หมายเหตุ"]
fi = sheet(ws, H, [16, 34, 26, 45, 13, 8, 30, 18, 28, 25], H[3:])
types = ["บุคคลธรรมดา — เป็นเจ้าของสถานที่", "บุคคลธรรมดา — เช่าสถานที่", "บุคคลธรรมดา — ใช้สถานที่ผู้อื่นโดยไม่มีค่าเช่า",
         "บุคคลธรรมดา — ขายออนไลน์ ใช้ห้องชุด/คอนโด", "คณะบุคคล / ห้างหุ้นส่วนสามัญ", "นิติบุคคล — เป็นเจ้าของสถานที่",
         "นิติบุคคล — เช่าสถานที่", "ผู้ประกอบการต่างด้าว", "กรณีมอบอำนาจให้ผู้อื่นยื่นแทน"]
ch = [("กระดาษ (57)", "VAT57_ART_05_A / B / C"), ("อินเทอร์เน็ต (159)", "VAT159_ART_05_A / B / C, 05_1")]
for c, ref in ch:
    for t in types:
        for k in range(3):
            ws.append([c, t, ref if k == 0 else "", "", "", "", "", "", "", ""])
ws.append(["DBD (234)", "นิติบุคคลจดทะเบียนพร้อมกับ DBD", "VAT234_ART_*", "", "", "", "", "", "", ""])
style_rows(ws, fi)
nrow = ws.max_row - 1
dv(ws, "E", ["ต้นฉบับ", "สำเนา", "ต้นฉบับ+สำเนา", "ไฟล์อัปโหลด"], nrow)
for r in ws.iter_rows(min_row=2, max_col=3):
    for c in r: c.fill = GREY
ws.auto_filter.ref = f"A1:J{nrow+1}"

# ---------- 2_ตรวจตัวบท
ws = wb.create_sheet("2_ตรวจตัวบท")
H = ["chunk id", "หัวข้อ", "ที่มา (ฉบับ/ข้อ)", "ข้อความในระบบ", "ถูกต้องไหม (✓/✗)", "แก้ไขเป็น", "หมายเหตุ"]
fi = sheet(ws, H, [18, 40, 40, 90, 10, 50, 25], H[4:])
def order(a):
    m = re.match(r"VAT(\d+)_ART_(\d+)", a["id"]); return (int(m.group(1)), int(m.group(2)), a["id"]) if m else (999, 0, a["id"])
for a in sorted(arts, key=order):
    ws.append([a["id"], a["title"], a["source_section"], a["content"], "", "", ""])
style_rows(ws, fi)
dv(ws, "E", ["✓", "✗"], len(arts))
for i in range(2, len(arts) + 2): ws.row_dimensions[i].height = 120

wb._sheets = [wb["วิธีกรอก"], wb["1_ชุดเฉลย"], wb["2_ตรวจตัวบท"], wb["3_เกณฑ์ข้อ6"], wb["4_เอกสาร"]]
out = str(Path(B).parent / "data_prep" / "VAT_Copilot_เตรียมข้อมูลปรับจูน.xlsx")
wb.save(out)
print(out, "ชุดเฉลย", n, {g: sum(1 for p in picked if p["group"] == g) for g in quota})
