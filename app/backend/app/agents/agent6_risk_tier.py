"""
Agent 6: Risk & Tier Decision Agent
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 4
และสอดคล้องกับประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 6 (มาตรการตรวจสอบความเสี่ยง)

สำคัญที่สุด: Rule-based ล้วน — ห้าม LLM ตัดสินคะแนนความเสี่ยงเอง (Final Scope ยืนยันซ้ำ)

INPUT:  {"raw_text": str, "confidence_score": float}
OUTPUT: {"risk_score": float, "risk_factors": list[str], "trust_score": float, "tier": str}
"""
from app.core.config import settings

# เกณฑ์ความเสี่ยง Rule-Based สอดคล้องกับประกาศอธิบดีฯ ฉบับที่ 57 ข้อ 6 และ ฉบับที่ 159 ข้อ 6
RISK_KEYWORDS = {
    # 1. แสดงเอกสารหรือข้อมูลเป็นเท็จ
    "เอกสารเท็จ": 0.50,
    "ข้อมูลเท็จ": 0.50,
    "ไม่ตรงกับความเป็นจริง": 0.45,
    "เป็นเท็จ": 0.45,
    # 2. ตัวแทนเชิด (Nominee)
    "ตัวแทนเชิด": 0.50,
    "นอมินี": 0.50,
    "nominee": 0.50,
    "ลูกจ้าง": 0.40,
    "แบล็กลิสต์": 0.40,
    # 3. ไม่มีสถานประกอบการจริง
    "ไม่มีสถานประกอบการ": 0.45,
    "ไม่มีสถานที่": 0.40,
    "ไม่มีหน้าร้าน": 0.40,
    "ปิดร้าง": 0.45,
    # 4. ใช้สำนักงานบัญชีหรือสำนักงานกฎหมายบังหน้า
    "สำนักงานบัญชี": 0.40,
    "สำนักงานกฎหมาย": 0.40,
    "สำนักงานทนาย": 0.40,
    # 5. มิได้ประกอบกิจการจริง / รับจ้างออกใบกำกับภาษีปลอม
    "มิได้ประกอบกิจการ": 0.50,
    "ไม่ได้ประกอบกิจการ": 0.50,
    "ไม่มีการประกอบธุรกิจ": 0.50,
    "ไม่ได้ขายสินค้าหรือให้บริการจริง": 0.50,
    "รับจ้างออกใบกำกับ": 0.50,
    # 6. เคยถูกเพิกถอนทะเบียน VAT มาก่อน
    "เพิกถอน": 0.50,
    # 7. ไม่แสดงหรือไม่นำส่งเอกสารตามที่ร้องขอ
    "ไม่ยอมนำไปแสดง": 0.40,
    "ไม่แสดงเอกสาร": 0.40,
    "ไม่นำส่งเอกสาร": 0.40,
    # 8. ไม่อัปโหลดเอกสารออนไลน์ หรือไม่ครบถ้วน (ฉบับที่ 159)
    "ไม่อัปโหลด": 0.40,
    "ไม่ได้อัปโหลด": 0.40,
    "อัปโหลดไม่ครบ": 0.40,
    # ปัจจัยเสี่ยงโครงสร้างธุรกิจอื่นๆ
    "เปลี่ยนผู้ถือหุ้น": 0.30,
    "ต่างชาติ": 0.30,
    "ข้ามชาติ": 0.30,
    "ควบรวม": 0.25,
}


def assess_risk(raw_text: str, confidence_score: float) -> dict:
    risk_factors = [kw for kw in RISK_KEYWORDS if kw in raw_text]
    risk_score = min(sum(RISK_KEYWORDS[kw] for kw in risk_factors), 1.0)
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
        "risk_factors": risk_factors,
        "trust_score": trust_score,
        "tier": tier,
    }
