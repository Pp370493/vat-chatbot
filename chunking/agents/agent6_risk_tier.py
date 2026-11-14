# -*- coding: utf-8 -*-
"""
Agent 6: Risk & Tier Decision Agent (Rule-Based Compliance & Fraud Detection)
หน้าที่: ประเมินความเสี่ยงของคำขอจดทะเบียน VAT ตามหลักเกณฑ์ ข้อ 6 แห่งประกาศอธิบดีฯ (ฉบับ 57/159/214/246)
ความเสี่ยง 8 ประการตามตัวบทกฎหมาย:
1. นอมินี / ตัวแทนเชิด / คนต่างด้าวถือหุ้นหรือเป็นกรรมการผิดปกติ
2. ใช้ที่ตั้งสำนักงานบัญชี / สำนักงานกฎหมาย / Virtual Office เป็นสถานประกอบการ
3. ไม่มีสถานประกอบการจริง / ติดต่อไม่ได้ / ร้านร้าง
4. ไม่ส่งมอบเอกสารหลักฐาน หรือเอกสารสัญญาเช่า/ยินยอมเป็นเท็จ
5. เคยมีประวัติออกหรือใช้ใบกำกับภาษีปลอม / บิลขยะ
6. เคยถูกเพิกถอนการจดทะเบียนภาษีมูลค่าเพิ่มมาก่อน
7. ไม่มีทรัพย์สิน เครื่องมือ หรืออุปกรณ์ที่จำเป็นต่อการประกอบธุรกิจ
8. ข้อมูลขัดแย้งกับข้อเท็จจริงหรือฐานข้อมูล DBD

การจัดกลุ่มระดับ Tier:
- GREEN (Risk 0): ความเสี่ยงต่ำ -> AUTO_ANSWER (ตอบคำถามแก่ผู้ใช้ทันที)
- YELLOW (Risk 1-2): ความเสี่ยงปานกลาง -> WARN_AND_GUIDE (แจ้งเตือนจุดที่ต้องตรวจสอบเอกสารเพิ่มเติม)
- RED (Risk >= 3 หรือพบความเสี่ยงข้อ 4, 5, 6): ความเสี่ยงสูง -> ESCALATE_SENIOR (ระงับการออกใบทะเบียนและส่งเรื่องหัวหน้าทีม/ฝ่ายตรวจปฏิบัติการ)
"""

import re
from typing import Dict, Any, List

class RiskTierDecisionAgent:
    def __init__(self):
        # คำบ่งชี้ปัจจัยเสี่ยง 8 มิติ
        self.risk_patterns = {
            "NOMINEE": [
                r"นอมินี", r"nominee", r"ตัวแทนเชิด", r"สวมชื่อ", r"ลูกจ้างเป็นกรรมการ",
                r"จ้างคนอื่นมาเปิด", r"คนต่างด้าวถือหุ้นแทน", r"กรรมการหุ่นเชิด"
            ],
            "ACCOUNTING_OFFICE_ADDRESS": [
                r"สำนักงานบัญชี", r"สนง\.บัญชี", r"สำนักงานกฎหมาย", r"สนง\.กฎหมาย",
                r"virtual office", r"ออฟฟิศเสมือน", r"ตู้ ปณ\.", r"จดที่อยู่เดียวกับผู้สอบบัญชี"
            ],
            "NO_REAL_PREMISES": [
                r"ไม่มีร้านจริง", r"ร้านร้าง", r"ที่ดินรกร้าง", r"หาไม่เจอ", r"ติดต่อไม่ได้",
                r"ไม่มีป้ายชื่อ", r"บ้านร้าง", r"ไม่พบสถานประกอบการ"
            ],
            "FAKE_OR_MISSING_DOCS": [
                r"เอกสารปลอม", r"สัญญาเช่าปลอม", r"ลายเซ็นปลอม", r"เอกสารเท็จ",
                r"ไม่ยอมส่งเอกสาร", r"ไม่ส่งหลักฐาน", r"ปลอมบัตร"
            ],
            "TAX_FRAUD_HISTORY": [
                r"ใบกำกับภาษีปลอม", r"บิลปลอม", r"โกง vat", r"ประวัติออกใบกำกับ",
                r"ขายใบกำกับภาษี", r"บิลแวทปลอม"
            ],
            "PREVIOUSLY_REVOKED": [
                r"เคยโดนเพิกถอน", r"ถูกเพิกถอน", r"โดนปิดบริษัท", r"ถูกสั่งยกเลิก vat"
            ],
            "NO_BUSINESS_ASSETS": [
                r"ไม่มีเครื่องจักร", r"ไม่มีสินค้า", r"ไม่มีสต็อก", r"ไม่มีอุปกรณ์", r"ไม่มีการดำเนินงานจริง"
            ],
            "INCONSISTENT_DBD": [
                r"ข้อมูลไม่ตรง dbd", r"ทุนจดทะเบียนไม่ตรง", r"กรรมการไม่ตรง"
            ]
        }

    def evaluate_risk(self, user_query: str, application_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        ประเมินความเสี่ยงจากคำถาม หรือจากข้อมูลคำขอที่ส่งเข้ามา
        """
        text_to_eval = user_query.lower()
        if application_data:
            text_to_eval += " " + json.dumps(application_data, ensure_ascii=False).lower()

        detected_risks: List[str] = []
        risk_descriptions: List[str] = []
        is_critical_flag = False

        for risk_key, patterns in self.risk_patterns.items():
            for p in patterns:
                if re.search(p, text_to_eval):
                    if risk_key not in detected_risks:
                        detected_risks.append(risk_key)
                        risk_descriptions.append(self._get_risk_desc(risk_key))
                        if risk_key in ["FAKE_OR_MISSING_DOCS", "TAX_FRAUD_HISTORY", "PREVIOUSLY_REVOKED"]:
                            is_critical_flag = True
                    break

        risk_count = len(detected_risks)

        # ตัดสินระดับความเสี่ยง (Tier Decision)
        if risk_count == 0:
            tier = "GREEN"
            action = "AUTO_ANSWER"
            instruction = "อนุมัติให้ระบบตอบคำถามหรือให้คำแนะนำตามปกติ เนื่องจากไม่พบสัญญาณความเสี่ยงตามข้อ 6"
        elif risk_count <= 2 and not is_critical_flag:
            tier = "YELLOW"
            action = "WARN_AND_GUIDE"
            instruction = "แจ้งเตือนเจ้าหน้าที่ให้ตรวจสอบเอกสารหรือลงพื้นที่ตรวจสถานที่ก่อนออกใบทะเบียนตามข้อ 6"
        else:
            tier = "RED"
            action = "ESCALATE_SENIOR"
            instruction = "ความเสี่ยงสูงมาก! สั่งระงับการออกใบทะเบียน ภ.พ.20 และส่งเรื่องต่อไปยังหัวหน้าทีม/เจ้าหน้าที่อาวุโสเพื่อตรวจสอบเชิงลึก"

        return {
            "tier": tier,
            "action": action,
            "risk_score": risk_count,
            "detected_risks": detected_risks,
            "risk_descriptions": risk_descriptions,
            "instruction": instruction,
            "legal_grounding": "ข้อ 6 แห่งประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม (ฉบับที่ 57 และฉบับที่ 159 แก้ไขเพิ่มเติมโดยฉบับที่ 214 และฉบับที่ 246)"
        }

    def _get_risk_desc(self, key: str) -> str:
        mapping = {
            "NOMINEE": "ข้อสงสัยเรื่องนอมินีหรือตัวแทนเชิด (Nominee / Puppet Director)",
            "ACCOUNTING_OFFICE_ADDRESS": "ใช้ที่ตั้งสำนักงานบัญชีหรือสำนักงานกฎหมายเป็นสถานประกอบการ",
            "NO_REAL_PREMISES": "ไม่ปรากฏสถานประกอบการจริง หรือไม่สามารถติดต่อได้",
            "FAKE_OR_MISSING_DOCS": "เอกสารหลักฐานหรือสัญญาเช่าต้องสงสัยว่าเป็นเท็จ หรือปฏิเสธไม่ส่งมอบเอกสาร",
            "TAX_FRAUD_HISTORY": "มีประวัติหรือพฤติการณ์เกี่ยวข้องกับการออกใบกำกับภาษีโดยมิชอบ (บิลปลอม)",
            "PREVIOUSLY_REVOKED": "เคยมีประวัติถูกเพิกถอนการจดทะเบียนภาษีมูลค่าเพิ่ม",
            "NO_BUSINESS_ASSETS": "ไม่มีทรัพย์สิน เครื่องมือ หรือสิ่งจำเป็นในการประกอบกิจการจริง",
            "INCONSISTENT_DBD": "ข้อมูลขัดแย้งกับข้อเท็จจริงในทะเบียนนิติบุคคล"
        }
        return mapping.get(key, key)

if __name__ == "__main__":
    risk_agent = RiskTierDecisionAgent()

    # ทดสอบคำถามปกติ
    res1 = risk_agent.evaluate_risk("ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20")
    print("=== Case 1: Normal Query ===")
    print("Tier:", res1["tier"], "| Action:", res1["action"])

    # ทดสอบคำถามที่มีข้อสงสัยเรื่องนอมินีและสำนักงานบัญชี
    res2 = risk_agent.evaluate_risk("บริษัทขอใช้ที่อยู่สำนักงานบัญชีเป็นที่ตั้ง และมีกรรมการเป็นชาวต่างชาติแต่ใช้ชื่อลูกจ้างไทยเซ็นแทน")
    print("\n=== Case 2: Suspicious Application ===")
    print("Tier:", res2["tier"], "| Action:", res2["action"])
    print("Risks detected:", res2["risk_descriptions"])
    print("Instruction:", res2["instruction"])
