# -*- coding: utf-8 -*-
"""
Agent 8: Knowledge & Reporting Batch Agent (Continuous Learning & Quality Auditing)
หน้าที่: ทำงานแบบ Batch ในการรวบรวม Log การถาม-ตอบ
1. วิเคราะห์และจัดกลุ่มคำถามซ้ำ (Clustering & Frequency Analysis)
2. เมื่อหัวข้อหรือคำถามใดมีความถี่ >= 5 ครั้ง จะร่างบทความฐานความรู้ (Draft KB Article / FAQ) ให้ผู้ดูแลระบบตรวจสอบ
3. สร้างรายงานสรุปคุณภาพรอบสัปดาห์ (Weekly Chatbot Audit & Quality Report):
   - จำนวนคำถามทั้งหมด
   - สัดส่วน In-Scope vs Out-of-Scope
   - ช่องทางยอดนิยม (Walk-in / Online / DBD)
   - อัตราการสกัดกั้น Hallucination (เช่น การป้องกัน Semantic Collision ข้อ 9 กับ ข้อ 7)
   - สถิติความเสี่ยงและการส่งต่อ (Risk Tiers & Escalation Rate)
"""

import os
import json
import datetime
from collections import Counter
from typing import Dict, Any, List

class KnowledgeBatchAgent:
    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = log_dir
        self.audit_log_file = os.path.join(self.log_dir, "batch_qa_audit_log.jsonl")
        self.kb_drafts_file = os.path.join(self.log_dir, "draft_kb_articles.json")

    def record_interaction(self, record: Dict[str, Any]):
        """บันทึกการทำงานแต่ละรอบลงในไฟล์ Audit Log (JSONL)"""
        record["timestamp"] = datetime.datetime.now().isoformat()
        with open(self.audit_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def run_batch_audit(self) -> Dict[str, Any]:
        """ประมวลผลสรุปภาพรวมจาก Logs ทั้งหมด"""
        if not os.path.exists(self.audit_log_file):
            return {"status": "NO_DATA", "message": "ยังไม่มีประวัติการบันทึกคำถามในระบบ"}

        total_queries = 0
        in_scope_count = 0
        out_of_scope_count = 0
        checklist_count = 0
        channel_counts = Counter()
        risk_tier_counts = Counter()
        collision_interceptions = 0
        verified_pass_count = 0
        
        question_topics = Counter()
        raw_queries = []

        with open(self.audit_log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    total_queries += 1
                    raw_queries.append(entry.get("user_query", ""))

                    # การจัดกลุ่มประเภทคำถาม
                    intent = entry.get("classification", "")
                    if intent == "IN_SCOPE_VAT":
                        in_scope_count += 1
                    elif intent == "OUT_OF_SCOPE":
                        out_of_scope_count += 1
                    elif intent == "CHECKLIST_ASSIST":
                        checklist_count += 1

                    # ช่องทาง
                    ch = entry.get("channel", "WALK_IN")
                    channel_counts[ch] += 1

                    # ตรวจสอบการป้องกัน Semantic Collision
                    if entry.get("is_authority_intent", False):
                        collision_interceptions += 1

                    # ผล Verifier
                    v_res = entry.get("verifier_status", "")
                    if v_res == "PASS":
                        verified_pass_count += 1

                    # ระดับความเสี่ยง
                    tier = entry.get("risk_tier", "GREEN")
                    risk_tier_counts[tier] += 1

                    # คลัสเตอร์หัวข้อ
                    topic = entry.get("primary_topic", "ทั่วไป")
                    question_topics[topic] += 1

                except Exception:
                    continue

        # สร้างข้อเสนอแนะร่างบทความฐานความรู้ (Draft KB) สำหรับหัวข้อที่ถามบ่อย (>= 5)
        draft_kb_articles = []
        for topic, count in question_topics.items():
            if count >= 5:
                draft_kb_articles.append({
                    "topic": topic,
                    "frequency": count,
                    "status": "PROPOSED_FOR_OFFICIAL_FAQ",
                    "proposed_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "action_required": "ส่งเจ้าหน้าที่นิติกรตรวจทานและเผยแพร่เป็น FAQ ประจำระบบ"
                })

        # บันทึก Draft KB
        if draft_kb_articles:
            with open(self.kb_drafts_file, "w", encoding="utf-8") as f:
                json.dump(draft_kb_articles, f, ensure_ascii=False, indent=2)

        report = {
            "report_generated_at": datetime.datetime.now().isoformat(),
            "total_queries_processed": total_queries,
            "intent_breakdown": {
                "in_scope_vat": in_scope_count,
                "out_of_scope": out_of_scope_count,
                "checklist_assistant": checklist_count
            },
            "channel_distribution": dict(channel_counts),
            "risk_tier_distribution": dict(risk_tier_counts),
            "hallucination_prevention_stats": {
                "collision_interceptions_section_9_vs_7": collision_interceptions,
                "verified_pass_rate": round((verified_pass_count / total_queries * 100), 2) if total_queries > 0 else 0.0
            },
            "popular_topics": dict(question_topics.most_common(5)),
            "new_kb_proposals_count": len(draft_kb_articles)
        }

        return report

if __name__ == "__main__":
    batch_agent = KnowledgeBatchAgent()

    # ทดลองจำลองบันทึกข้อมูล 6 รายการเพื่อทดสอบระบบรวบรวม
    sample_interactions = [
        {"user_query": "ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20", "classification": "IN_SCOPE_VAT", "channel": "WALK_IN", "is_authority_intent": True, "verifier_status": "PASS", "risk_tier": "GREEN", "primary_topic": "ผู้มีอำนาจลงนาม ข้อ 9"},
        {"user_query": "ใครเซ็น ภ.พ.20 แทนสรรพากรพื้นที่", "classification": "IN_SCOPE_VAT", "channel": "WALK_IN", "is_authority_intent": True, "verifier_status": "PASS", "risk_tier": "GREEN", "primary_topic": "ผู้มีอำนาจลงนาม ข้อ 9"},
        {"user_query": "จด vat ต้องเตรียมเอกสารอะไรไปยื่น", "classification": "IN_SCOPE_VAT", "channel": "WALK_IN", "is_authority_intent": False, "verifier_status": "PASS", "risk_tier": "GREEN", "primary_topic": "เอกสารจดทะเบียน ข้อ 5"},
        {"user_query": "ใช้เอกสารไรบ้าง จด vat บุคคลธรรมดา", "classification": "IN_SCOPE_VAT", "channel": "WALK_IN", "is_authority_intent": False, "verifier_status": "PASS", "risk_tier": "GREEN", "primary_topic": "เอกสารจดทะเบียน ข้อ 5"},
        {"user_query": "ช่วยทำเช็คลิสต์ตรวจเอกสารคอนโด", "classification": "CHECKLIST_ASSIST", "channel": "ONLINE", "is_authority_intent": False, "verifier_status": "PASS", "risk_tier": "GREEN", "primary_topic": "Checklist คอนโด"},
        {"user_query": "อยากลดหย่อนภาษีเงินได้ ภ.ง.ด.90", "classification": "OUT_OF_SCOPE", "channel": "WALK_IN", "is_authority_intent": False, "verifier_status": "N/A", "risk_tier": "GREEN", "primary_topic": "ภาษีเงินได้"}
    ]

    for item in sample_interactions:
        batch_agent.record_interaction(item)

    summary = batch_agent.run_batch_audit()
    print("=== Agent 8 Batch Audit Report ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
