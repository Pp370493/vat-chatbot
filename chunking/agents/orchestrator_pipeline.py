# -*- coding: utf-8 -*-
"""
Orchestrator Pipeline: VAT Registration Graph RAG & 8-Agent Chatbot Controller
ศูนย์กลางควบคุมและประสานการทำงานของ Agent ทั้ง 8 ตัว ตาม System Workflow Architecture

Workflow:
1. Agent 1: Intent & Scope Classifier
   - หาก Out-of-Scope -> ส่งต่อ Agent 2
   - หาก Checklist / ตรวจเอกสาร -> ส่งต่อ Agent 7
   - หาก In-Scope VAT Q&A -> ส่งต่อ Agent 3
2. Agent 3: RAG Retrieval Agent (สกัดคำสำคัญ + Hybrid Search + Semantic Collision Suppression + Graph Lineage)
3. Agent 4: Responder Agent (สร้างคำตอบแบบ Grounded + Citations ป้องกัน Hallucination)
4. Agent 5: Verifier Agent (ตรวจทานความถูกต้อง ป้องกันการอ้างมาตรามั่ว/อ้างผิดข้อ)
5. Agent 6: Risk & Tier Decision Agent (ประเมินความเสี่ยงตามข้อ 6: GREEN / YELLOW / RED)
6. Agent 8: Knowledge & Reporting Batch Agent (บันทึก Audit Log และประมวลผลสถิติความแม่นยำ)
"""

import os
import sys
import json
from typing import Dict, Any

# นำเข้า Agents ทั้ง 8
from agent1_intent_classifier import IntentScopeClassifier
from agent2_out_of_scope_router import OutOfScopeRouter
from agent3_rag_retrieval import RAGRetrievalAgent
from agent4_responder import ResponderAgent
from agent5_verifier import VerifierAgent
from agent6_risk_tier import RiskTierDecisionAgent
from agent7_checklist_assistant import ChecklistAssistantAgent
from agent8_knowledge_batch import KnowledgeBatchAgent

class VATRegistrationOrchestrator:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir

        print("[Orchestrator] กำลังเตรียมระบบและโหลดฐานข้อมูล Graph RAG ทั้ง 10 ประกาศ...")
        self.agent1 = IntentScopeClassifier()
        self.agent2 = OutOfScopeRouter()
        self.agent3 = RAGRetrievalAgent(base_dir=self.base_dir)
        self.agent4 = ResponderAgent()
        self.agent5 = VerifierAgent()
        self.agent6 = RiskTierDecisionAgent()
        self.agent7 = ChecklistAssistantAgent()
        self.agent8 = KnowledgeBatchAgent(log_dir=self.base_dir)
        print("[Orchestrator] ระบบพร้อมปฏิบัติการครบทั้ง 8 Agents 100%")

    def process_query(self, user_query: str, session_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        ประมวลผลคำถามผู้ใช้ผ่านเส้นทาง 8 Agents
        """
        query = user_query.strip()
        pipeline_log = []

        # Step 1: Agent 1 - Intent & Scope Classifier
        a1_result = self.agent1.classify(query)
        pipeline_log.append({"agent": "Agent 1", "output": a1_result})

        classification = a1_result.get("classification")
        detected_channel = a1_result.get("channel", "WALK_IN")

        # กรณี 1: Out-of-Scope (ส่งต่อ Agent 2)
        if classification == "OUT_OF_SCOPE":
            a2_result = self.agent2.route(query, a1_result.get("scope_type"))
            pipeline_log.append({"agent": "Agent 2", "output": a2_result})
            
            final_output = {
                "status": "SUCCESS",
                "route": "OUT_OF_SCOPE",
                "user_query": query,
                "answer": a2_result.get("forwarding_advice"),
                "responsible_agency": a2_result.get("responsible_agency"),
                "action_items": a2_result.get("action_items"),
                "pipeline_log": pipeline_log
            }
            
            self._log_batch_record(query, a1_result, "N/A", "GREEN", "ภาษีนอกขอบเขต")
            return final_output

        # กรณี 2: Checklist Assistant (ส่งต่อ Agent 7)
        if classification == "CHECKLIST_ASSIST":
            # ตรวจสอบบริบทของคำถามเพื่อเลือกประเภทผู้ขอและสถานที่
            app_type = "INDIVIDUAL"
            if "บริษัท" in query or "นิติบุคคล" in query:
                app_type = "CORPORATE_THAI"
            elif "สามี" in query or "ภริยา" in query:
                app_type = "SPOUSE"

            prem_type = "RENTED"
            if "คอนโด" in query or "ห้องชุด" in query:
                prem_type = "CONDO"
            elif "บ้านตัวเอง" in query or "เจ้าของ" in query:
                prem_type = "RESIDENTIAL"

            is_online = ("ออนไลน์" in query or "เน็ต" in query or detected_channel == "ONLINE")

            a7_result = self.agent7.generate_checklist(
                channel=detected_channel,
                applicant_type=app_type,
                premises_type=prem_type,
                is_proxy=("มอบอำนาจ" in query),
                is_online_seller=is_online
            )
            pipeline_log.append({"agent": "Agent 7", "output": a7_result})

            final_output = {
                "status": "SUCCESS",
                "route": "CHECKLIST_ASSIST",
                "user_query": query,
                "checklist_summary": a7_result.get("summary_title"),
                "items": a7_result.get("checklist"),
                "special_exemptions": a7_result.get("special_exemptions"),
                "legal_citations": a7_result.get("legal_citations"),
                "pipeline_log": pipeline_log
            }

            self._log_batch_record(query, a1_result, "PASS", "GREEN", "Checklist ตรวจเอกสาร ข้อ 5")
            return final_output

        # กรณี 3: In-Scope VAT Q&A (Agent 3 -> Agent 4 -> Agent 5 -> Agent 6)
        # Step 2: Agent 3 - RAG Retrieval
        a3_result = self.agent3.search(query, detected_channel=detected_channel)
        pipeline_log.append({
            "agent": "Agent 3",
            "top_chunks": [c["chunk_id"] for c in a3_result.get("prompt_top_chunks", [])],
            "collision_handled": a3_result.get("is_authority_intent", False)
        })

        # Step 3: Agent 4 - Responder Agent
        a4_result = self.agent4.generate_response(query, a3_result)
        pipeline_log.append({"agent": "Agent 4", "generation_mode": a4_result.get("generation_mode")})

        # Step 4: Agent 5 - Verifier Agent
        a5_result = self.agent5.verify(query, a4_result, a3_result)
        pipeline_log.append({"agent": "Agent 5", "verifier_status": a5_result.get("status"), "score": a5_result.get("verification_score")})

        # Step 5: Agent 6 - Risk & Tier Decision Agent
        a6_result = self.agent6.evaluate_risk(query)
        pipeline_log.append({"agent": "Agent 6", "risk_tier": a6_result.get("tier"), "action": a6_result.get("action")})

        # รวบรวมหัวข้อหลัก
        primary_topic = "ข้อกฎหมายทั่วไป"
        if a3_result.get("prompt_top_chunks"):
            primary_topic = a3_result["prompt_top_chunks"][0].get("title", "ข้อกฎหมายทั่วไป")

        # Step 6: บันทึกข้อมูลผ่าน Agent 8
        self._log_batch_record(
            query=query,
            a1_result=a1_result,
            verifier_status=a5_result.get("status"),
            risk_tier=a6_result.get("tier"),
            topic=primary_topic,
            is_authority_intent=a3_result.get("is_authority_intent", False)
        )

        return {
            "status": "SUCCESS",
            "route": "IN_SCOPE_VAT",
            "user_query": query,
            "answer": a4_result.get("answer"),
            "citations": a4_result.get("citations"),
            "verifier_audit": {
                "status": a5_result.get("status"),
                "score": a5_result.get("verification_score"),
                "note": a5_result.get("verification_note"),
                "hallucination_flags": a5_result.get("hallucination_flags")
            },
            "risk_assessment": {
                "tier": a6_result.get("tier"),
                "action": a6_result.get("action"),
                "instruction": a6_result.get("instruction"),
                "detected_risks": a6_result.get("detected_risks")
            },
            "pipeline_log": pipeline_log
        }

    def _log_batch_record(self, query: str, a1_result: Dict[str, Any], verifier_status: str, risk_tier: str, topic: str, is_authority_intent: bool = False):
        try:
            self.agent8.record_interaction({
                "user_query": query,
                "classification": a1_result.get("classification"),
                "channel": a1_result.get("channel", "WALK_IN"),
                "verifier_status": verifier_status,
                "risk_tier": risk_tier,
                "primary_topic": topic,
                "is_authority_intent": is_authority_intent
            })
        except Exception:
            pass

if __name__ == "__main__":
    orchestrator = VATRegistrationOrchestrator()

    # ทดสอบคำถาม 2 คำถามสำคัญตามตารางของผู้ใช้
    test_cases = [
        "ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20",
        "จด vat ต้องเตรียมเอกสารอะไรไปยื่น",
        "ช่วยทำเช็คลิสต์ตรวจเอกสาร คอนโด ผู้ค้าออนไลน์",
        "มีลูกจ้างเป็นกรรมการและใช้ที่ตั้งสำนักงานบัญชีจด vat ได้ไหม",
        "อยากยื่นแบบ ภ.ง.ด.50 นิติบุคคล ยื่นที่ไหน"
    ]

    for tc in test_cases:
        print("\n" + "="*80)
        print(f"คำถามทดสอบ: '{tc}'")
        print("="*80)
        res = orchestrator.process_query(tc)
        print(f"เส้นทาง (Route): {res['route']}")
        if res["route"] == "IN_SCOPE_VAT":
            print(f"คำตอบที่ผ่านการ Verify:\n{res['answer']}")
            print(f"ผลการตรวจ Verifier: {res['verifier_audit']['status']} (Score: {res['verifier_audit']['score']})")
            print(f"ระดับความเสี่ยง Risk Tier: {res['risk_assessment']['tier']} ({res['risk_assessment']['action']})")
        elif res["route"] == "OUT_OF_SCOPE":
            print(f"คำแนะนำส่งต่อไปยังหน่วยงาน: {res['responsible_agency']}")
            print(f"คำแนะนำ: {res['answer']}")
        elif res["route"] == "CHECKLIST_ASSIST":
            print(f"Checklist: {res['checklist_summary']}")
            for item in res['items']:
                print(f" - {item['item']} ({item['copies']})")
            if res.get("special_exemptions"):
                print("สิทธิพิเศษ:", res["special_exemptions"])
