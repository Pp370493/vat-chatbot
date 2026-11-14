# -*- coding: utf-8 -*-
"""
Agent 5: Verifier Agent (Anti-Hallucination & Legal Citation Auditor)
หน้าที่: ตรวจสอบความถูกต้องทางกฎหมายของคำตอบจาก Agent 4 เทียบกับ Chunks ของ Agent 3
กฎการตรวจ:
1. ตรวจสอบว่าข้อกฎหมายที่อ้างอิง (Citations) มีอยู่จริงใน Chunks ที่ส่งมาจาก Agent 3 หรือไม่
2. ตรวจสอบการ Hallucination เชิงเนื้อหา:
   - กรณีถามเรื่องอำนาจลงนาม ภ.พ.20: ต้องอ้างอิง ข้อ 9 เท่านั้น ห้ามอ้างอิง ข้อ 7 (แบบพิมพ์) หรือ ข้อ 10 (อำนาจวินิจฉัย)
   - ห้ามระบุว่าเจ้าพนักงานสรรพากรทั่วไปเซ็นได้
3. ประเมินความสอดคล้อง (Factual Consistency Score 0.0 - 1.0)
4. ตัดสินสถานะ: PASS / FLAG_HALLUCINATION / REJECT
"""

import re
from typing import Dict, Any, List

class VerifierAgent:
    def __init__(self):
        pass

    def verify(self, user_query: str, agent4_output: Dict[str, Any], retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        ตรวจทานคำตอบของ Agent 4
        """
        answer_text = agent4_output.get("answer", "")
        citations = agent4_output.get("citations", [])
        top_chunks = retrieval_result.get("prompt_top_chunks", [])
        is_authority_intent = retrieval_result.get("is_authority_intent", False)

        audit_logs = []
        hallucination_flags = []
        score = 1.0

        # 1. ตรวจสอบ Citation Consistency
        valid_chunk_ids = {c.get("chunk_id") for c in top_chunks}
        for cit in citations:
            cid = cit.get("chunk_id")
            if cid not in valid_chunk_ids:
                hallucination_flags.append(f"Citation mismatch: Chunk {cid} not found in retrieved context.")
                score -= 0.3

        # 2. ตรวจสอบ Semantic Collision Guardrail สำหรับ ข้อ 9 vs ข้อ 7 vs ข้อ 10
        q = user_query.lower()
        if is_authority_intent or "ใครเซ็น" in q or "ไม่อยู่" in q or "ผู้มีอำนาจลงนาม" in q:
            # ต้องระบุ ข้อ 9
            if "ข้อ 9" not in answer_text:
                hallucination_flags.append("Violation: Query asks for signing authority but response does not cite Section 9.")
                score -= 0.5
            
            # ห้ามอ้างว่า ข้อ 7 หรือ ข้อ 10 ให้อำนาจเซ็น
            if "ข้อ 7" in answer_text and "ผู้มีอำนาจออก" in answer_text:
                hallucination_flags.append("Hallucination: Attributed signing authority to Section 7 (which only defines Form VAT 20).")
                score -= 0.6
                
            if "ข้อ 10" in answer_text and "เซ็นแทน" in answer_text:
                hallucination_flags.append("Hallucination: Attributed signing authority to Section 10 (Director-General interpretation power).")
                score -= 0.6

            # ห้ามระบุว่าเจ้าพนักงานสรรพากรทั่วไปมีอำนาจเซ็นโดยไม่มีคำสั่งมอบหมาย
            if "เจ้าพนักงานสรรพากรทั่วไป" in answer_text and "ไม่มีอำนาจ" not in answer_text and "มิได้รับมอบหมาย" not in answer_text:
                hallucination_flags.append("Legal Error: General revenue officer cannot sign VAT certificate without delegation.")
                score -= 0.7

            # ต้องระบุ สรรพากรพื้นที่ หรือ ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่
            if "สรรพากรพื้นที่" not in answer_text:
                hallucination_flags.append("Incomplete: Missing Revenue Area Officer (สรรพากรพื้นที่).")
                score -= 0.3

            if "ผู้ที่ได้รับมอบหมาย" not in answer_text and "มอบหมาย" not in answer_text:
                hallucination_flags.append("Incomplete: Missing legal delegation rule for absence.")
                score -= 0.2

        # 3. ตรวจสอบว่ามีคำอ้างอิงในคำตอบหรือไม่
        if "[อ้างอิง:" not in answer_text:
            audit_logs.append("Warning: Answer lacks official [อ้างอิง: ...] citation tag.")
            score -= 0.1

        score = max(0.0, min(1.0, score))

        # ประเมินผลลัพธ์
        if score >= 0.85:
            status = "PASS"
            verification_note = "คำตอบสอดคล้องกับข้อความกฎหมายและไม่มีอาการ Hallucination"
        elif score >= 0.60:
            status = "NEEDS_REVISION"
            verification_note = "พบข้อบกพร่องเล็กน้อยในคำอ้างอิงหรือรายละเอียดปลีกย่อย"
        else:
            status = "FLAG_HALLUCINATION"
            verification_note = f"พบความเสี่ยงของการบิดเบือนข้อกฎหมาย: {'; '.join(hallucination_flags)}"

        return {
            "status": status,
            "verification_score": round(score, 2),
            "hallucination_flags": hallucination_flags,
            "audit_logs": audit_logs,
            "verification_note": verification_note,
            "verified_answer": answer_text
        }

if __name__ == "__main__":
    verifier = VerifierAgent()

    # ทดสอบตัวอย่างตอบถูกต้อง (ข้อ 9)
    valid_ans = {
        "answer": "ตามประกาศฯ ฉบับที่ 57 ข้อ 9 ผู้มีอำนาจออก ภ.พ.20 คือ สรรพากรพื้นที่ หรือ ผู้อำนวยการกองบริหารภาษีธุรกิจขนาดใหญ่ กรณีไม่อยู่ ให้ผู้ที่ได้รับมอบหมายเป็นผู้ลงนามแทน [อ้างอิง: ประกาศฉบับที่ 57/245 ข้อ 9]",
        "citations": [{"chunk_id": "VAT245_ART_02"}]
    }
    retrieval = {
        "is_authority_intent": True,
        "prompt_top_chunks": [{"chunk_id": "VAT245_ART_02"}]
    }
    res = verifier.verify("ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20", valid_ans, retrieval)
    print("=== Verification Result (Valid Answer) ===")
    print("Status:", res["status"])
    print("Score:", res["verification_score"])
    print("Note:", res["verification_note"])

    # ทดสอบตัวอย่างตอบผิด Hallucination (อ้างข้อ 7 และบอกเจ้าพนักงานทั่วไปเซ็นได้)
    hallucinated_ans = {
        "answer": "ตามประกาศฉบับที่ 57 ข้อ 7 เจ้าพนักงานสรรพากรทั่วไปสามารถลงนามแทนได้ทันที",
        "citations": [{"chunk_id": "VAT57_ART_07"}]
    }
    res_bad = verifier.verify("ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20", hallucinated_ans, retrieval)
    print("\n=== Verification Result (Hallucinated Answer) ===")
    print("Status:", res_bad["status"])
    print("Score:", res_bad["verification_score"])
    print("Flags:", res_bad["hallucination_flags"])
