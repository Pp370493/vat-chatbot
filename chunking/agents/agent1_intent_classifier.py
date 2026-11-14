# -*- coding: utf-8 -*-
"""
Agent 1: Intent & Scope Classifier
หน้าที่: เป็นด่านหน้าตรวจจับ "เจตนาและขอบเขต" ของคำถาม
- ถ้าไม่เกี่ยวกับงานจดทะเบียน VAT -> ส่งต่อ Agent 2 (Out-of-Scope Router)
- ถ้าต้องการตรวจรับเอกสาร / Checklist -> ส่งต่อ Agent 7 (Checklist Assistant)
- ถ้าเป็นข้อหารือการจด VAT (In-Scope) -> ส่งต่อ Agent 3 (RAG Retrieval Agent)
"""

import re
from typing import Dict, Any

class IntentScopeClassifier:
    def __init__(self):
        # คำบ่งชี้ Out-of-Scope (ภาษีอื่น / หน่วยงานอื่น)
        self.out_of_scope_patterns = {
            "CIT_PIT": [
                r"ภ\.ง\.ด\.\s*9[014]", r"ภ\.ง\.ด\.\s*5[01]", r"ภาษีเงินได้บุคคลธรรมดา",
                r"ภาษีเงินได้นิติบุคคล", r"ลดหย่อนภาษี", r"หัก ณ ที่จ่าย", r"ภ\.ง\.ด\.\s*3", r"ภ\.ง\.ด\.\s*53"
            ],
            "LAND_SIGN": [
                r"ภาษีที่ดิน", r"ภาษีโรงเรือน", r"ภาษีป้าย", r"ฝ่ายรายได้สำนักงานเขต", r"เทศบาล", r"อบต\."
            ],
            "EXCISE": [
                r"สรรพสามิต", r"สุรา", r"ยาสูบ", r"ภาษีน้ำหวาน", r"รถยนต์ภาษีสรรพสามิต"
            ],
            "CUSTOMS": [
                r"ศุลกากร", r"ภาษีนำเข้า", r"พิกัดอัตราศุลกากร", r"ใบขนสินค้าขาเข้า"
            ]
        }

        # คำบ่งชี้ว่าต้องการตรวจเอกสาร / Checklist (Agent 7)
        self.checklist_triggers = [
            r"ตรวจรับเอกสาร", r"เช็คลิสต์", r"checklist", r"ตรวจเอกสาร",
            r"ช่วยตรวจเอกสาร", r"ตรวจแบบฟอร์ม", r"แบบตรวจรับ"
        ]

        # คำบ่งชี้ช่องทาง (Channel)
        self.online_triggers = [r"ออนไลน์", r"อินเทอร์เน็ต", r"rd\.go\.th", r"ขายของออนไลน์", r"คอนโด", r"ห้องชุด", r"e-commerce"]
        self.dbd_triggers = [r"dbd", r"กรมพัฒนาธุรกิจ", r"จดพร้อมตั้งบริษัท", r"จัดตั้งนิติบุคคล", r"single window"]

    def classify(self, user_query: str) -> Dict[str, Any]:
        query = user_query.strip()
        
        # 1. ตรวจ Checklist Request (Agent 7)
        for pattern in self.checklist_triggers:
            if re.search(pattern, query, re.IGNORECASE):
                return {
                    "classification": "CHECKLIST_ASSIST",
                    "routing_target": "Agent_7_Checklist_Assistant",
                    "reason": "ผู้ใช้ต้องการตัวช่วยตรวจสอบรายการเอกสาร/เช็คลิสต์",
                    "confidence": 0.98,
                    "channel": self._detect_channel(query)
                }

        # 2. ตรวจ Out-of-Scope (Agent 2)
        for scope_type, patterns in self.out_of_scope_patterns.items():
            for p in patterns:
                if re.search(p, query, re.IGNORECASE):
                    # ข้อยกเว้น: หากถามเรื่องสัญญาเช่าและมี ภ.ง.ด. ประกอบการจด VAT ให้ยังคงเป็น VAT
                    if ("จด vat" in query.lower() or "จดทะเบียนภาษีมูลค่าเพิ่ม" in query) and "ภ.ง.ด." in query:
                        continue
                    return {
                        "classification": "OUT_OF_SCOPE",
                        "routing_target": "Agent_2_Out_of_Scope_Router",
                        "scope_type": scope_type,
                        "reason": f"คำถามเกี่ยวกับประเด็นนอกขอบเขตการจดทะเบียน VAT ({scope_type})",
                        "confidence": 0.95
                    }

        # 3. จัดเป็น In-Scope VAT Q&A (Agent 3)
        detected_channel = self._detect_channel(query)
        return {
            "classification": "IN_SCOPE_VAT",
            "routing_target": "Agent_3_RAG_Retrieval",
            "channel": detected_channel,
            "reason": "คำถามอยู่ในขอบเขตหลักเกณฑ์ วิธีการ และเงื่อนไขการจดทะเบียนภาษีมูลค่าเพิ่ม",
            "confidence": 0.99
        }

    def _detect_channel(self, query: str) -> str:
        q = query.lower()
        for trig in self.dbd_triggers:
            if re.search(trig, q):
                return "DBD"
        for trig in self.online_triggers:
            if re.search(trig, q):
                return "ONLINE"
        return "WALK_IN"

if __name__ == "__main__":
    clf = IntentScopeClassifier()
    tests = [
        "กรณีผู้มีอำนาจออก ภ.พ.20 ไม่อยู่ ใครจะเป็นผู้มีอำนาจลงนาม",
        "อยากคำนวณภาษีเงินได้บุคคลธรรมดา ภ.ง.ด.90 ต้องหักค่าลดหย่อนยังไง",
        "ช่วยทำเช็คลิสต์ตรวจเอกสารจด VAT คอนโดให้หน่อย",
        "ขายของออนไลน์อยู่คอนโด ยื่นจด VAT ผ่านเน็ตต้องใช้อะไรบ้าง"
    ]
    for t in tests:
        print(f"คำถาม: {t}\nผล: {clf.classify(t)}\n{'-'*50}")
