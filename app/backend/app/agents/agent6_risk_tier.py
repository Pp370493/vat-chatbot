"""
Agent 6: Risk & Tier Decision Agent
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 4
และเหตุไม่ออกใบทะเบียนตามประกาศอธิบดีฯ VAT ฉบับที่ 57 ข้อ 6 / ฉบับที่ 159 ข้อ 6 / ฉบับที่ 234 ข้อ 5

สำคัญที่สุด: Rule-based ล้วน — ห้าม LLM ตัดสินคะแนนความเสี่ยงเอง (Final Scope ยืนยันซ้ำ)

INPUT:  {"raw_text": str, "confidence_score": float}
OUTPUT: {"risk_score": float, "risk_factors": list[str], "trust_score": float, "tier": str}

กฎความเสี่ยงเป็นรูปแบบคำ (regex) แยกตามเหตุในข้อ 6 — คำที่กำกวมเมื่ออยู่ลำพัง (เช่น "ลูกจ้าง",
"สำนักงานบัญชี", "ต่างชาติ") นับเป็นความเสี่ยงเฉพาะเมื่อมาพร้อมบริบทที่เป็นพฤติการณ์ตามข้อ 6
เพื่อไม่ให้คำถามปกติ (เช่น "มีลูกจ้าง 2 คน จด VAT ได้ไหม") ถูกส่งต่อเจ้าหน้าที่โดยไม่จำเป็น
ทดสอบ: python -m pytest tests/test_agent6_risk.py
"""
import re

from app.core.config import settings

# (ป้ายเหตุ, รูปแบบคำ, น้ำหนัก) — น้ำหนักรวมสูงสุด 1.0
# trust = confidence × (1 − risk) → ที่ confidence 0.9: risk ≥ 0.34 → officer_review, risk ≥ 0.62 → senior_review
RISK_RULES: list[tuple[str, re.Pattern, float]] = [
    ("ข้อ 6(1) แสดงรายการ/เอกสารเป็นเท็จ", re.compile(
        r"เอกสารเท็จ|ข้อมูลเท็จ|เป็นเท็จ|ไม่ตรงกับความเป็นจริง|แต่ความจริง|ปลอม|ทำหลอก|หลอกๆ|ตกแต่งเอกสาร"
        r"|photoshop|โฟโต้ช็อป|ตัดต่อรูป|เซ็นชื่อแทน(?!.{0,6}มอบอำนาจ)|ปลอมลายเซ็น"), 0.50),
    ("ข้อ 6(2) ตัวแทนเชิด", re.compile(
        r"นอมินี|nominee|ตัวแทนเชิด|หุ่นเชิด|สวมชื่อ"
        r"|เอาชื่อ.{0,25}(ไป|มา)?(เปิด|จด|ยื่น)|ใช้ชื่อ(คนอื่น|ผม|เรา|เขา|ญาติ|เพื่อน).{0,15}(เปิด|จด|ยื่น)"
        r"|(จ้าง|ให้).{0,30}(มา)?(เป็น|เซ็นเป็น)(กรรมการ|เจ้าของ|ผู้ถือหุ้น|หุ้นส่วน)"
        r"|ลูกจ้าง.{0,25}(ถือหุ้น|เป็นกรรมการ|เป็นเจ้าของ|เป็นหุ้นส่วน)|(ถือหุ้น|เป็นกรรมการ).{0,15}แทน"
        r"|(เปิด|จด)(บริษัท|ร้าน)?แทน|แบล็กลิสต์|แบล็คลิสต์|blacklist"), 0.50),
    ("ข้อ 6(3) ไม่มีสถานประกอบการจริง", re.compile(
        r"ไม่มีสถานประกอบการ|ที่ดินเปล่า|ไม่มีสิ่งปลูกสร้าง|ตู้ ?ปณ|ตู้ไปรษณีย์|บ้านร้าง|ไม่มีคนอยู่|ร้านร้าง|ปิดร้าง"
        r"|ไม่ได้เปิด(ประตู|ไฟ)|ติดป้าย.{0,20}(ถ่ายรูป|เฉยๆ)|virtual office|ออฟฟิศเสมือน|รับฝากที่อยู่"
        r"|ไม่มีสินค้า|ไม่มีสต็อก|มีแค่โต๊ะ"), 0.45),
    ("ข้อ 6(4) ใช้สำนักงานกฎหมาย/บัญชีของผู้อื่นเป็นสถานประกอบการ", re.compile(
        r"(สำนักงานบัญชี|สำนักงานกฎหมาย|สำนักงานทนาย|สนง\.? ?บัญชี).{0,40}(ที่ตั้ง|ที่อยู่|สถานประกอบการ)"
        r"|(ที่ตั้ง|ที่อยู่|ใช้ที่อยู่|สถานประกอบการ).{0,30}(สำนักงานบัญชี|สำนักงานกฎหมาย|สำนักงานทนาย|สนง\.? ?บัญชี)"), 0.45),
    ("ข้อ 6(5) มิได้ประกอบกิจการจริง", re.compile(
        r"มิได้ประกอบกิจการ|ไม่ได้ประกอบ(กิจการ|การ)จริง|ไม่มีการประกอบธุรกิจ|ไม่ได้กะจะขาย|ไม่ได้ขาย(ของ|สินค้า)?จริง"
        r"|เปิดบิล(ภาษี)?ให้(คนอื่น|พรรคพวก|เพื่อน)|รับจ้างออกใบกำกับ|ออกใบกำกับภาษีอย่างเดียว|ขายบิล|บิลปลอม|มีแต่ชื่อ"), 0.50),
    ("ข้อ 6(6) เคยถูกเพิกถอนทะเบียน", re.compile(r"เพิกถอน|ถูกถอนทะเบียน"), 0.40),
    ("ข้อ 6(7)/(8) ไม่นำส่ง/ไม่อัปโหลดเอกสารตามที่ร้องขอ", re.compile(
        r"ไม่(ได้)?(ส่ง|นำส่ง|แสดง)เอกสาร|ไม่ยอม(ส่ง|นำไปแสดง|ไปแสดง|ไปพบ)|เพิกเฉย|บ่ายเบี่ยง|ขอเลื่อน.{0,15}(ตรวจ|นัด)"
        r"|ไม่(ได้)?แนบไฟล์|โดยไม่แนบ|ไม่(ได้)?อัปโหลด|อัปโหลด.{0,15}ไม่ครบ|ลืมอัปโหลด|ไม่มีให้ดู|ตามหมายเรียก"), 0.35),
    ("ขอวิธีหลบเลี่ยงการตรวจสอบ", re.compile(
        r"ไม่ให้(เขา|เจ้าหน้าที่)?สงสัย|ผ่านง่าย|จะโดนจับ|จะตรวจเจอ|ตรวจเจอชื่อ|เช็กประวัติ|โทรไปเช็ก"
        r"|ตรวจ(สอบ)?(ย้อนหลัง|ของจริง)|จะว่าไหม|เนียนๆ|ไม่ต้องทำอะไรเลย"), 0.30),
]


def find_risk_factors(raw_text: str) -> list[tuple[str, float]]:
    text = (raw_text or "").lower()
    return [(label, weight) for label, pattern, weight in RISK_RULES if pattern.search(text)]


def assess_risk(raw_text: str, confidence_score: float) -> dict:
    hits = find_risk_factors(raw_text)
    risk_score = min(sum(w for _, w in hits), 1.0)
    trust_score = round(confidence_score * (1.0 - risk_score), 4)

    # คำนวณ Tier ตาม Threshold ใน .env
    # trust_score >= 0.6 -> auto_answer
    # 0.35 <= trust_score < 0.6 -> officer_review
    # trust_score < 0.35 -> senior_review
    if trust_score >= settings.risk_threshold_officer:
        tier = "auto_answer"
    elif trust_score >= settings.risk_threshold_senior:
        tier = "officer_review"
    else:
        tier = "senior_review"

    return {
        "risk_score": round(risk_score, 4),
        "risk_factors": [label for label, _ in hits],
        "trust_score": trust_score,
        "tier": tier,
    }


# ---- สรุปเคสสำหรับหัวหน้างาน (ไม่ใช้ LLM) — ใช้เมื่อรู้ตั้งแต่ก่อนร่างคำตอบว่าต้องส่งตรวจ
_CLAUSE_NUM_RE = re.compile(r"\((\d)\)")


def clause_text(art6_text: str, num: str) -> str:
    """ตัดข้อความอนุข้อ (num) ออกจากตัวบทข้อ 6 — ถึงก่อนอนุข้อถัดไป"""
    m = re.search(rf"\({num}\)\s*(.+?)(?=\n\(\d\)|\Z)", art6_text or "", re.S)
    return " ".join(m.group(1).split()) if m else ""


def _with_clauses(citation: str, nums: list[str]) -> str:
    """'...ข้อ 6 ซึ่งแก้ไข...' -> '...ข้อ 6(7), (8) ซึ่งแก้ไข...'"""
    clauses = ", ".join(f"({n})" for n in dict.fromkeys(nums))
    return citation.replace(" ข้อ 6", f" ข้อ 6{clauses}", 1) if " ข้อ 6" in citation else f"{citation} {clauses}"


def build_review_brief(resolved_query: str, chunks: list[dict], risk: dict, art6: list[dict]) -> dict:
    """
    คืน {draft_text, citations, answer_summary} สำหรับคิวหัวหน้างาน
    art6: ตัวบทข้อ 6 ของช่องทางที่เกี่ยวข้อง [{chunk_id, text, citation}] (57 = กระดาษ, 159 = อินเทอร์เน็ต)
    """
    from app.agents.agent4_responder import summarize_chunks  # import ภายในเพื่อเลี่ยง import วน

    factors = risk.get("risk_factors") or []
    parts = [
        "📋 **สรุปเคสสำหรับหัวหน้างาน** (ระบบสร้างจากกฎ ไม่ได้ใช้ AI ร่าง — กรุณาตรวจและแก้ก่อนตอบ)",
        f"**คำถาม:** {resolved_query}",
        f"**ระดับ:** {risk.get('tier')} · risk {risk.get('risk_score')} · trust {risk.get('trust_score')}",
    ]
    citations: list[dict] = []
    nums_by_art: dict[str, list[str]] = {}

    issue_lines = []
    for label in factors:
        nums = _CLAUSE_NUM_RE.findall(label.split(" ", 2)[1]) if label.startswith("ข้อ 6") else []
        issue_lines.append(f"• **{label}**")
        for num in nums:
            for a in art6:
                txt = clause_text(a["text"], num)
                if txt:
                    ref = _with_clauses(a["citation"], [num])
                    issue_lines.append(f"  - {ref}: {txt}")
                    nums_by_art.setdefault(a["citation"], []).append(num)
                    citations.append({"text_span": ref, "source_section": a["citation"]})
    issue_refs = [_with_clauses(cit, nums) for cit, nums in nums_by_art.items()]
    parts.append("**ประเด็นที่อาจขัดกับตัวบท:**\n" + ("\n".join(issue_lines) if issue_lines else
                                                     "• ไม่พบเหตุตามข้อ 6 โดยตรง — ระดับความเชื่อมั่นต่ำ ต้องพิจารณาข้อเท็จจริงเพิ่มเติม"))

    summary, chunk_citations = summarize_chunks(chunks, n=3)
    if summary:
        parts.append("**ตัวบทที่เกี่ยวข้อง (จากการค้น):**\n" + summary)
    for c in chunk_citations:
        if c not in citations:
            citations.append(c)

    if issue_refs:
        named = ", ".join(label.split(" ", 2)[-1] if label.startswith("ข้อ 6") else label for label in factors)
        draft = (f"กรณีตามข้อเท็จจริงที่แจ้ง อาจเข้าลักษณะ{named} ตาม{' และ'.join(issue_refs)} "
                 "ซึ่งเจ้าพนักงานสรรพากรจะไม่ออกใบทะเบียนภาษีมูลค่าเพิ่มให้ หากตรวจสอบข้อเท็จจริงแล้วปรากฏเช่นนั้น "
                 "ขอให้ผู้ประกอบการยื่นคำขอและเอกสารหลักฐานตามข้อเท็จจริง")
    else:
        draft = "(โปรดพิจารณาข้อเท็จจริงเพิ่มเติมก่อนตอบ — ระบบไม่พบเหตุตามข้อ 6 ที่ชัดเจน)"
    parts.append("**ร่างคำตอบเบื้องต้น:**\n" + draft)

    return {
        "draft_text": "\n\n".join(parts),
        "citations": citations,
        "answer_summary": ("ส่งหัวหน้างานตรวจ: " + "; ".join(factors))[:200] if factors else "ส่งหัวหน้างานตรวจ",
    }
