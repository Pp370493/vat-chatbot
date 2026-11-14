"""
Agent 4: Responder Agent
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 4, 14.8

INPUT:  {"resolved_query": str, "chunks": list[dict]}
OUTPUT: {"draft_text": str, "citations": list[dict], "answer_summary": str}

หลักเกณฑ์สำคัญ:
1. Grounded generation เท่านั้น อ้างอิงเฉพาะข้อมูลในเอกสาร
2. แสดงคำตอบครบถ้วน ไม่ตัดทอนกลางประโยค (num_predict=750, num_ctx=2560)
3. ยึดประกาศ 57 (กระดาษ) และ 159 (อินเทอร์เน็ต) เป็นแม่บทหลักในการอ้างอิงเสมอ
4. หากผู้ใช้ยังไม่ได้ระบุช่องทางยื่น ต้องมีคำถามสอบถามเพิ่มเติมเพื่อจำแนกช่องทาง
"""
import re
from app.core.ollama_client import generate
from app.core.config import settings

def respond(resolved_query: str, chunks: list[dict]) -> dict:
    # เลือก 2-3 chunks ที่มีคะแนนความเกี่ยวข้องสูงสุด โดยไม่กรองตัดทิ้งข้อเดียวกัน
    # เพื่อให้ได้เนื้อหาตัวบทกฎหมายที่อัปเดตและตรงจุดมากที่สุด
    if not chunks:
        return {
            "draft_text": "ไม่พบข้อมูลข้อกฎหมายที่ตรงกับคำถาม กรุณาติดต่อสายด่วน 1161",
            "citations": [],
            "answer_summary": "ไม่พบข้อมูล",
        }

    # คัดเลือก top 2-3 chunks
    selected_chunks = chunks[:3] if len(chunks) >= 3 else chunks

    chunks_in_prompt = selected_chunks
    context_text = "\n\n".join(
        f"[{c.get('citation') or c['source_section']}]\n{c['text'][:1200]}" for c in chunks_in_prompt)

    prompt = (
        f"คุณคือผู้เชี่ยวชาญ AI สำหรับเจ้าหน้าที่กรมสรรพากร ในการตอบข้อหารือเกี่ยวกับการจดทะเบียนภาษีมูลค่าเพิ่ม (VAT)\n\n"
        f"ข้อกำหนดสำคัญในการตอบ:\n"
        f"1. ตอบโดยอ้างอิงเฉพาะข้อมูลใน 'เอกสารอ้างอิงทางการ' ด้านล่างนี้เท่านั้น ห้ามใช้ความรู้ภายนอก\n"
        f"2. สรุปเนื้อหากระชับ ชัดเจน ตรงประเด็น เป็นข้อๆ (Bullet points) 2-4 ข้อ ความยาวพอเหมาะให้อ่านรู้เรื่อง เข้าใจง่าย และต้องตอบให้จบประโยคสมบูรณ์ทุกข้อ ห้ามตัดทอนหรือพิมพ์ค้างกลางคำเด็ดขาด\n"
        f"3. การอ้างอิงกฎหมาย: ต้องยึดเฉพาะ 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57)' (สำหรับการยื่นแบบกระดาษ) และ 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159)' (สำหรับการยื่นทางอินเทอร์เน็ต) เป็นหลักเท่านั้น ห้ามอ้างอิงประกาศฉบับที่ 234 เด็ดขาด ยกเว้นในคำถามมีคำว่า 'DBD' หรือ 'กรมพัฒนาธุรกิจ' โดยตรงเท่านั้น โดยหากเป็นข้อที่ได้รับการแก้ไขเพิ่มเติม ให้ระบุ เช่น 'ตามประกาศอธิบดีฯ VAT (ฉบับที่ 57 หรือ 159) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่...)'\n"
        f"4. หากคำถามเกี่ยวกับเอกสารหรือหลักฐาน ให้สรุปเฉพาะรายการเอกสารที่ปรากฏใน 'เอกสารอ้างอิงทางการ' เท่านั้น ห้ามเพิ่มเอกสารที่ตัวบทไม่ได้กำหนด (ตัวบทฉบับปัจจุบันไม่ได้กำหนดให้ผู้ประกอบการบุคคลธรรมดาสัญชาติไทยแนบสำเนาบัตรประจำตัวประชาชนหรือทะเบียนบ้านของตนเอง) และตอบให้จบประโยคสมบูรณ์\n"
        f"5. เมื่ออ้างข้อกฎหมาย ให้ใช้ข้อความในวงเล็บ [...] ที่หัวเอกสารอ้างอิงแต่ละชิ้น ซึ่งระบุฉบับที่แก้ไขเพิ่มเติมไว้แล้ว\n\n"
        f"--- เอกสารอ้างอิงทางการ ---\n"
        f"{context_text}\n"
        f"----------------------------\n\n"
        f"คำถาม: {resolved_query}\n\n"
        f"คำตอบ:"
    )

    result = generate(
        prompt=prompt,
        temperature=0.2,
        num_ctx=2048,
        num_predict=600,
        mock_response="(mock) สรุปคำตอบอ้างอิง ประกาศอธิบดีฯ VAT (ฉบับที่ 57)",
    )

    draft_text = result["text"].strip()

    # ตรวจสอบและตัดแต่งข้อความกรณี LLM พิมพ์ค้างกลางคำเพื่อให้อ่านรู้เรื่องจบประโยคเสมอ
    if draft_text and "\n" in draft_text:
        lines = [line.rstrip() for line in draft_text.split("\n")]
        last_line = lines[-1].strip()
        dangling_words = ["ขอ", "ที่", "และ", "หรือ", "คือ", "ของ", "ใน", "ตาม", "โดย", "เช่น", "ว่า", "การ", "ผู้", "ฉบับ"]
        if last_line and (any(last_line.endswith(" " + w) or last_line.endswith(w) for w in dangling_words) or len(last_line) < 15):
            lines = lines[:-1]
            draft_text = "\n".join(lines).strip()

    # รวบรวม Citations อ้างอิง
    citations = []
    seen_sections = set()
    for c in chunks_in_prompt:
        sec = c.get("citation") or c.get("source_section", "")
        if sec and sec not in seen_sections:
            seen_sections.add(sec)
            citations.append({
                "text_span": sec,
                "source_section": sec,
            })

    if not citations and chunks_in_prompt:
        citations.append({
            "text_span": draft_text[:40],
            "source_section": chunks_in_prompt[0]["source_section"]
        })

    # สรุป 1 ประโยคสั้นๆ (≤200 ตัวอักษร) สำหรับ context เทิร์นถัดไป
    lines = [line.strip() for line in draft_text.split("\n") if line.strip() and not line.startswith("💡")]
    first_line = lines[0] if lines else draft_text
    answer_summary = first_line[:200]

    return {
        "draft_text": draft_text,
        "citations": citations,
        "answer_summary": answer_summary,
    }
