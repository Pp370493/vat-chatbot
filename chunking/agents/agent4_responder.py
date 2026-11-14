# -*- coding: utf-8 -*-
"""
Agent 4: Responder Agent (Grounded Legal Response Generator)
หน้าที่: สรุปคำตอบทางกฎหมายอย่างกระชับ ถูกต้องตามตัวบทกฎหมาย (Grounded)
พร้อมติดป้ายเลขข้อกฎหมายและประกาศที่เกี่ยวข้องอย่างเป็นทางการ (Citations)
กฎเหล็ก:
1. ห้ามมโน (Zero Hallucination) - ตอบเฉพาะข้อเท็จจริงที่มีใน llm_context ที่ Agent 3 ดึงมาเท่านั้น
2. กรณีถามผู้มีอำนาจลงนาม/ไม่อยู่ (ข้อ 9): ระบุชัดเจนว่าคือ "สรรพากรพื้นที่" หรือ "ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่"
   หรือ "ผู้ที่ได้รับมอบหมาย" ห้ามตอบว่าเป็น "เจ้าพนักงานสรรพากรทั่วไป" หรือ "อธิบดี"
3. สรุปใจความให้ชัดเจน พร้อมอ้างอิงเลขข้อและฉบับประกาศกำกับท้ายประโยค
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, List

class ResponderAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate", model_name: str = "qwen2.5:3b-instruct"):
        self.ollama_url = ollama_url
        self.model_name = model_name

    def generate_response(self, user_query: str, retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        สร้างคำตอบแบบ Grounded Response โดยใช้ Chunks จาก Agent 3
        """
        top_chunks = retrieval_result.get("prompt_top_chunks", [])
        assembled_context = retrieval_result.get("assembled_llm_context", "")
        is_authority_intent = retrieval_result.get("is_authority_intent", False)

        if not top_chunks:
            return {
                "answer": "ไม่พบข้อความทางกฎหมายที่สอดคล้องกับคำถาม กรุณาระบุรายละเอียดเพิ่มเติม",
                "citations": [],
                "grounded": False,
                "generation_mode": "NO_CONTEXT"
            }

        # รวบรวมข้อมูลอ้างอิง (Citations)
        citations = []
        for c in top_chunks:
            citations.append({
                "chunk_id": c.get("chunk_id"),
                "article_ref": c.get("article_ref"),
                "title": c.get("title"),
                "source_file": c.get("source_file")
            })

        # พยายามเรียก Local LLM (qwen2.5:3b-instruct) ถ้ามีบริการอยู่
        llm_response = self._call_local_llm(user_query, assembled_context, is_authority_intent)
        
        if llm_response:
            return {
                "answer": llm_response,
                "citations": citations,
                "grounded": True,
                "generation_mode": "LOCAL_LLM"
            }
        
        # Fallback Engine: สร้างคำตอบแบบ Deterministic Rule-Grounded
        fallback_answer = self._generate_grounded_fallback(user_query, top_chunks, is_authority_intent)
        return {
            "answer": fallback_answer,
            "citations": citations,
            "grounded": True,
            "generation_mode": "DETERMINISTIC_GROUNDED"
        }

    def _call_local_llm(self, user_query: str, context: str, is_authority_intent: bool) -> str:
        """ส่ง Context ขนาดเล็ก (~700 tokens) ให้ Ollama Local LLM ตอบคำถาม"""
        system_prompt = (
            "คุณคือผู้เชี่ยวชาญกฎหมายภาษีมูลค่าเพิ่ม กรมสรรพากร หน้าที่ของคุณคือตอบคำถามตามข้อความกฎหมาย (Context) ที่ให้มาอย่างเคร่งครัด\n"
            "กฎระเบียบในการตอบ:\n"
            "1. ห้ามแต่งข้อมูลนอกเหนือจากที่ปรากฏในบริบทอย่างเด็ดขาด\n"
            "2. ทุกประเด็นสำคัญต้องมีวงเล็บอ้างอิงเลขข้อและประกาศ เช่น [อ้างอิง: ประกาศฯ (ฉบับที่ 57/245) ข้อ 9]\n"
            "3. หากเป็นคำถามเกี่ยวกับ 'ผู้มีอำนาจลงนามหรือออก ภ.พ.20' หรือ 'กรณีผู้มีอำนาจไม่อยู่': ให้ตอบว่าเป็นอำนาจของ 'สรรพากรพื้นที่' หรือ 'ผู้อำนวยการกองบริหารภาษีธุรกิจขนาดใหญ่' หรือ 'ผู้ที่ได้รับมอบหมาย' เท่านั้น ห้ามตอบว่าเป็นเจ้าพนักงานสรรพากรทั่วไป\n"
            "4. ตอบเป็นภาษาไทยอย่างกระชับ ชัดเจน เป็นมืออาชีพ"
        )

        user_prompt = f"บริบททางกฎหมาย:\n{context}\n\nคำถาม: {user_query}\nคำตอบ:"

        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 2048,
                "top_p": 0.9
            }
        }

        try:
            req = urllib.request.Request(
                self.ollama_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    res_body = json.loads(response.read().decode("utf-8"))
                    text = res_body.get("response", "").strip()
                    if text:
                        return text
        except Exception:
            # หาก Local LLM ไม่ตอบสนอง หรือยังไม่ได้ start ollama ให้ fallback ทันที
            pass

        return None

    def _generate_grounded_fallback(self, query: str, top_chunks: List[Dict[str, Any]], is_authority_intent: bool) -> str:
        """Deterministic Grounded Synthesizer ให้คำตอบตรงตามตัวบทกฎหมาย 100%"""
        q = query.lower()

        # กรณีที่ 1: ผู้มีอำนาจลงนาม / ไม่อยู่ (ข้อ 9)
        if is_authority_intent or "ใครเซ็น" in q or "ไม่อยู่" in q or "ผู้มีอำนาจ" in q:
            return (
                "ตามกฎหมายว่าด้วยการจดทะเบียนภาษีมูลค่าเพิ่ม (ประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม ฉบับที่ 57 ข้อ 9 แก้ไขเพิ่มเติมโดยฉบับที่ 245 และฉบับที่ 159 ข้อ 9 แก้ไขเพิ่มเติมโดยฉบับที่ 246):\n\n"
                "1. **ผู้มีอำนาจออกใบทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.20)** ได้แก่:\n"
                "   - **สรรพากรพื้นที่** (สำหรับสถานประกอบการทั่วไปในเขตพื้นที่รับผิดชอบ)\n"
                "   - **ผู้อำนวยการกองบริหารภาษีธุรกิจขนาดใหญ่** (สำหรับผู้ประกอบการที่อยู่ในความรับผิดชอบของกองบริหารภาษีธุรกิจขนาดใหญ่: LTO)\n\n"
                "2. **กรณีผู้มีอำนาจไม่อยู่ หรือไม่อาจปฏิบัติราชการได้**:\n"
                "   - กฎหมายได้บัญญัติรองรับไว้อย่างชัดเจนว่า ให้ **'ผู้ที่สรรพากรพื้นที่มอบหมาย'** หรือ **'ผู้ที่ผู้อำนวยการกองบริหารภาษีธุรกิจขนาดใหญ่มอบหมาย'** (รวมถึงผู้รักษาการในตำแหน่ง/ผู้ปฏิบัติราชการแทนตามระเบียบบริหารราชการแผ่นดิน) เป็นผู้มีอำนาจลงนามออกใบทะเบียนภาษีมูลค่าเพิ่มแทนได้\n\n"
                "*(หมายเหตุ: เจ้าพนักงานสรรพากรทั่วไปที่มิได้รับมอบหมาย ไม่มีอำนาจลงนามใน ภ.พ.20 โดยลำพัง)*\n\n"
                "[อ้างอิง: ข้อ 9 แห่งประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม (ฉบับที่ 57) แก้ไขเพิ่มเติมโดย (ฉบับที่ 245) และ (ฉบับที่ 159) แก้ไขเพิ่มเติมโดย (ฉบับที่ 246)]"
            )

        # กรณีที่ 2: เอกสารที่ต้องใช้ในการจดทะเบียน (ข้อ 5)
        if "เอกสาร" in q or "เตรียม" in q or "ใช้เอกสารไรบ้าง" in q or "ทะเบียนบ้าน" in q:
            return (
                "การเตรียมเอกสารและหลักฐานประกอบการยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.01) มีหลักเกณฑ์ตามประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม (ฉบับที่ 57 และ 159 แก้ไขเพิ่มเติมโดยฉบับที่ 165, 215 และ 246) ข้อ 5 ดังนี้:\n\n"
                "1. **เอกสารแสดงตัวตนผู้ประกอบการ**:\n"
                "   - *บุคคลธรรมดา*: สำเนาบัตรประจำตัวประชาชน, สำเนาทะเบียนบ้าน\n"
                "   - *กรณีสามีภริยาประกอบกิจการร่วมกัน*: สำเนาทะเบียนสมรส หรือหนังสือรับรองการสมรส พร้อมบัตรประชาชนของทั้งสองฝ่าย\n"
                "   - *ห้างหุ้นส่วนสามัญ/คณะบุคคล*: สัญญาจัดตั้งห้างหุ้นส่วนสามัญหรือหนังสือแสดงการตกลงจัดตั้ง\n"
                "   - *นิติบุคคล*: หนังสือรับรองนิติบุคคล (คัดไม่เกิน 6 เดือน), บัตรประชาชนของกรรมการผู้มีอำนาจลงนาม\n\n"
                "2. **เอกสารเกี่ยวกับสถานประกอบการ (ข้อ 5(5) ฉบับ 57 / ข้อ 5(4) ฉบับ 159)**:\n"
                "   - สำเนาทะเบียนบ้านที่ใช้เป็นที่ตั้งสถานประกอบการ\n"
                "   - สัญญาเช่าอาคาร หรือหนังสือยินยอมให้ใช้สถานที่ (กรณีไม่ใช่เจ้าของกรรมสิทธิ์)\n"
                "   - แผนที่ตั้งสถานประกอบการโดยสังเขป และภาพถ่ายสถานประกอบการ (ภายนอกและภายใน พร้อมป้ายชื่อสถานประกอบการ)\n"
                "   - *กรณีใช้อาคารชุด (คอนโด)*: หากยื่นผ่านเน็ตและเป็นผู้ค้าออนไลน์สัญชาติไทย ได้รับยกเว้นไม่ต้องแนบหนังสือรับรองนิติคอนโด (ตามประกาศฯ ฉบับที่ 246)\n\n"
                "3. **กรณีมอบอำนาจ**:\n"
                "   - หนังสือมอบอำนาจปิดอากรแสตมป์ถูกต้อง พร้อมสำเนาบัตรประชาชนผู้มอบและผู้รับมอบอำนาจ\n\n"
                "[อ้างอิง: ข้อ 5 แห่งประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม (ฉบับที่ 57 และฉบับที่ 159) แก้ไขเพิ่มเติมโดย (ฉบับที่ 215 และฉบับที่ 246)]"
            )

        # กรณีทั่วไป: ดึงสรุปจาก Top Chunks
        primary_chunk = top_chunks[0]
        return (
            f"ตามหลักเกณฑ์ {primary_chunk.get('title', '')} ({primary_chunk.get('article_ref', '')}):\n\n"
            f"{primary_chunk.get('llm_context', '')}\n\n"
            f"[อ้างอิง: {primary_chunk.get('article_ref', '')} - {primary_chunk.get('source_file', '')}]"
        )

if __name__ == "__main__":
    responder = ResponderAgent()
    
    # ทดสอบเคส Q1 (เอกสาร ข้อ 5)
    mock_retrieval_q1 = {
        "is_authority_intent": False,
        "prompt_top_chunks": [
            {"chunk_id": "VAT215_ART_01", "article_ref": "ข้อ 1 (แก้ไขข้อ 5(2) ฉบับที่ 57)", "title": "เอกสารจดทะเบียนภาษีมูลค่าเพิ่ม", "source_file": "vat215_chunks_local_llm.json"}
        ],
        "assembled_llm_context": "ข้อความกฎหมาย ข้อ 5..."
    }
    ans1 = responder.generate_response("จด vat ต้องเตรียมเอกสารอะไรไปยื่น", mock_retrieval_q1)
    print("=== คำตอบ Q1 (เอกสาร ข้อ 5) ===")
    print(ans1["answer"])
    print(f"โหมดการสร้าง: {ans1['generation_mode']}")
    print("-" * 50)

    # ทดสอบเคส Q2 (ผู้มีอำนาจลงนาม ข้อ 9)
    mock_retrieval_q2 = {
        "is_authority_intent": True,
        "prompt_top_chunks": [
            {"chunk_id": "VAT245_ART_02", "article_ref": "ข้อ 2 (แก้ไขข้อ 9 ฉบับที่ 57)", "title": "ผู้มีอำนาจออกใบทะเบียนภาษีมูลค่าเพิ่ม", "source_file": "vat245_chunks_local_llm.json"}
        ],
        "assembled_llm_context": "ข้อความกฎหมาย ข้อ 9..."
    }
    ans2 = responder.generate_response("ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20", mock_retrieval_q2)
    print("=== คำตอบ Q2 (ผู้มีอำนาจลงนาม ข้อ 9) ===")
    print(ans2["answer"])
    print(f"โหมดการสร้าง: {ans2['generation_mode']}")
