"""
ฟอร์มถามกลับแบบ checkbox — ใช้เมื่อคำตอบขึ้นกับข้อมูลที่ผู้ใช้ยังไม่ได้บอก (ต้องรู้ก่อนว่าตอบข้อไหน)

backend ส่งตัวเลือกใน payload["form"] หน้าเว็บวาดเป็น checkbox แล้วส่งคำตอบกลับเป็นข้อความเดียว:
    - ฟอร์มกลุ่มเดียว: ส่ง label ของตัวเลือกที่เลือก (เหมือนกดปุ่มเดิม)
    - ฟอร์มหลายกลุ่ม: "ช่องทาง: … · ผู้ยื่น: … · สถานประกอบการ: …, …"
merge_form_reply() แปลงคำตอบนั้นเป็นวงเล็บต่อท้ายคำถามเดิม ให้ขั้นค้นตัวบทและร่างคำตอบเห็นข้อมูลครบ

กลุ่มข้อมูลผู้ยื่นถามเฉพาะคำถามเรื่องเอกสาร เพราะเอกสารตามข้อ 5 แยกอนุตามประเภทผู้ยื่นและสถานประกอบการ
"""
from __future__ import annotations

import re

FORM_CLARIFICATION_SUMMARY = "สอบถามข้อมูลก่อนตอบ"
GROUP_SEP = " · "

CHANNEL_GROUP = {
    "key": "channel", "label": "ช่องทางที่จะยื่นคำขอ", "short": "ช่องทาง", "multi": False, "required": True,
    "options": [
        {"value": "paper", "label": "ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ (ฉบับที่ 57)",
         "hint": "ใช้คำขอ ภ.พ.01 จำนวน 3 ฉบับ พร้อมแสดงเอกสารตัวจริง"},
        {"value": "internet", "label": "ยื่นผ่านอินเทอร์เน็ต www.rd.go.th (ฉบับที่ 159)",
         "hint": "กรอกคำขอและอัปโหลดเอกสารทางเว็บไซต์"},
        {"value": "dbd", "label": "ยื่นพร้อมจดทะเบียนจัดตั้งนิติบุคคลผ่าน DBD (ฉบับที่ 234)",
         "hint": "เฉพาะนิติบุคคลที่จดจัดตั้งกับกรมพัฒนาธุรกิจการค้า"},
    ],
}
APPLICANT_GROUP = {
    "key": "applicant", "label": "ผู้ยื่นคำขอเป็น", "short": "ผู้ยื่น", "multi": False, "required": True,
    "options": [
        {"value": "thai", "label": "บุคคลธรรมดาสัญชาติไทย"},
        {"value": "alien", "label": "บุคคลธรรมดาต่างด้าว"},
        {"value": "group", "label": "คณะบุคคล / ห้างหุ้นส่วนสามัญ"},
        {"value": "juristic", "label": "นิติบุคคล (บริษัท / ห้างหุ้นส่วนนิติบุคคล)"},
        {"value": "foreign", "label": "นิติบุคคลต่างประเทศ / กิจการร่วมค้า"},
        {"value": "unsure", "label": "ไม่ระบุ (ขอดูทุกประเภท)"},
    ],
}
PREMISES_GROUP = {
    "key": "premises", "label": "สถานประกอบการ (เลือกได้มากกว่า 1 ข้อ)", "short": "สถานประกอบการ",
    "multi": True, "required": False,
    "options": [
        {"value": "own", "label": "เป็นเจ้าของสถานที่"},
        {"value": "rent", "label": "เช่าสถานที่"},
        {"value": "free", "label": "ใช้สถานที่ของผู้อื่นโดยไม่เสียค่าเช่า"},
        {"value": "condo", "label": "ห้องชุด / คอนโด"},
        {"value": "poa", "label": "มอบอำนาจให้ผู้อื่นยื่นแทน"},
    ],
}
PURPOSE_GROUP = {
    "key": "purpose", "label": "ประเภทแบบหรือคำขอที่จะยื่น", "short": "วัตถุประสงค์", "multi": False, "required": True,
    "options": [
        {"value": "pp01", "label": "ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มใหม่ (แบบ ภ.พ.01)",
         "hint": "ขอเข้าสู่ระบบ VAT ครั้งแรก"},
        {"value": "pp09", "label": "ต้องการแจ้งเปลี่ยนแปลงข้อมูลทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.09)",
         "hint": "ย้ายร้าน เปลี่ยนชื่อ เพิ่มหรือปิดสาขา"},
        {"value": "pp30", "label": "ต้องการยื่นแบบแสดงรายการและชำระภาษีมูลค่าเพิ่ม (แบบ ภ.พ.30)",
         "hint": "ยื่นแบบและเสียภาษีรายเดือน"},
        {"value": "pnd", "label": "ต้องการยื่นแบบแสดงรายการภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91)",
         "hint": "ภาษีเงินได้ประจำปี"},
    ],
}

DOC_WORDS = ["เอกสาร", "หลักฐาน", "แนบ", "อัปโหลด", "อัพโหลด", "upload", "สำเนา", "ใช้อะไรบ้าง",
             "เตรียมอะไร", "ต้องเตรียม", "ใช้อะไร"]
APPLICANT_WORDS = ["บุคคลธรรมดา", "คนไทย", "สัญชาติไทย", "ต่างด้าว", "ต่างชาติ", "ชาวต่างชาติ", "คณะบุคคล",
                   "ห้างหุ้นส่วน", "หจก", "บริษัท", "นิติบุคคล", "กิจการร่วมค้า", "joint venture", " jv", "สหกรณ์",
                   "มูลนิธิ", "สมาคม", "ผู้ยื่น:"]


def is_document_question(text: str) -> bool:
    """คำถามถามถึงเอกสาร/หลักฐานที่ต้องใช้หรือแนบ"""
    t = (text or "").lower()
    return any(w in t for w in DOC_WORDS)


def has_applicant_info(text: str) -> bool:
    t = f" {(text or '').lower()}"
    return any(w in t for w in APPLICANT_WORDS)


def build_form(groups: list[dict]) -> dict:
    return {"groups": [{k: g[k] for k in ("key", "label", "short", "multi", "required", "options")} for g in groups]}


def _label_lookup(groups: list[dict]) -> dict[str, dict]:
    return {g["short"]: g for g in groups}


def parse_form_reply(text: str) -> dict[str, list[str]]:
    """'ช่องทาง: A · ผู้ยื่น: B · สถานประกอบการ: C, D' -> {'ช่องทาง': ['A'], 'ผู้ยื่น': ['B'], ...}"""
    out: dict[str, list[str]] = {}
    for part in (text or "").split(GROUP_SEP):
        key, sep, val = part.partition(":")
        if not sep:
            continue
        vals = [v.strip() for v in re.split(r",\s*", val) if v.strip()]
        if vals:
            out[key.strip()] = vals
    return out


def merge_form_reply(text: str, original: str, channel_phrase: dict[str, str], detect_channel) -> str | None:
    """เติมคำตอบจากฟอร์มต่อท้ายคำถามเดิม — คืน None ถ้าไม่พบข้อมูลที่ใช้ได้"""
    parsed = parse_form_reply(text)
    extras = []
    channel = detect_channel(" ".join(parsed.get("ช่องทาง", [])) or text)
    if channel:
        extras.append(channel_phrase[channel])
    if parsed.get("ผู้ยื่น"):
        extras.append("ผู้ยื่น: " + ", ".join(parsed["ผู้ยื่น"]))
    if parsed.get("สถานประกอบการ"):
        extras.append("สถานประกอบการ: " + ", ".join(parsed["สถานประกอบการ"]))
    if not extras and has_applicant_info(text):
        extras.append("ผู้ยื่น: " + text.strip())
    if not extras:
        return None
    return original + "".join(f" ({e})" for e in extras)
