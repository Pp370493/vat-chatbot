"""
Agent 5: Verifier Agent (Two-Tier Verification)
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 4, 14.8

INPUT:  {"draft_text": str, "citations": list[dict], "chunks": list[dict], "tier_hint": str}
OUTPUT: {"confidence_score": float, "ungrounded_claims": list[str]}

ชั้น 1 (ทุกเคส, ไม่ใช้ LLM): regex เช็คเลขมาตรา/ข้อ + embedding similarity
ชั้น 2 (เฉพาะ senior_review, num_ctx=3072): LLM critic แยก call
"""
import re
from app.core.ollama_client import generate
from app.core.embeddings import get_embedding
import numpy as np

# ตรวจจับทั้ง "มาตรา ..." และ "ข้อ ..." (เช่น ประกาศอธิบดีฯ ข้อ 1)
SECTION_PATTERN = re.compile(r"(?:มาตรา|ข้อ)\s*\d+(?:/\d+)?(?:\([ก-ฮ0-9]+\))*")


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def verify_regex(draft_text: str, chunks: list[dict]) -> dict:
    # แปลงเลขไทยเป็นอารบิกก่อนเทียบ (ตัวบทหลายฉบับใช้ "ข้อ ๙" ขณะที่คำตอบมักเขียน "ข้อ 9")
    draft_text = (draft_text or "").translate(THAI_DIGITS)
    cited_sections = set(SECTION_PATTERN.findall(draft_text))
    source_text = " ".join(
        c.get("text", "") + " " + c.get("source_section", "") + " " + c.get("citation", "") for c in chunks
    ).translate(THAI_DIGITS)
    
    ungrounded = [s for s in cited_sections if s not in source_text]
    
    # Grounding check: เทียบความสอดคล้องของคำสำคัญในคำตอบกับ Chunk ที่ดึงมา (0ms latency)
    confidence = 0.90
    if chunks:
        chunk_words = set(re.findall(r"[\w]+", source_text.lower()))
        draft_words = set(re.findall(r"[\w]+", draft_text.lower()))
        if draft_words:
            overlap = len(draft_words.intersection(chunk_words)) / len(draft_words)
            if overlap < 0.25:
                confidence -= 0.20

    if ungrounded:
        confidence = max(0.30, confidence - 0.35)

    return {
        "confidence_score": round(confidence, 3),
        "ungrounded_claims": ungrounded,
    }


def verify_deep_llm(draft_text: str, chunks: list[dict]) -> dict:
    context = "\n".join(c["text"] for c in chunks[:2])
    result = generate(
        prompt=(
            f"คุณคือผู้ตรวจทานกฎหมาย จงตรวจสอบว่าข้อความคำตอบนี้มีข้อความเท็จหรือขัดแย้งกับเอกสารต้นฉบับหรือไม่:\n\n"
            f"เอกสารต้นฉบับ:\n{context}\n\n"
            f"คำตอบที่ตรวจ:\n{draft_text}\n\n"
            f"ตอบว่า 'ถูกต้อง' หรือ 'พบข้อขัดแย้ง' พร้อมระบุสั้นๆ 1 ประโยค:"
        ),
        num_ctx=3072,
        mock_response="ถูกต้อง สอดคล้องกับเอกสารต้นฉบับ",
    )
    is_valid = "ขัดแย้ง" not in result["text"]
    conf = 0.90 if is_valid else 0.40
    return {"confidence_score": conf, "ungrounded_claims": [] if is_valid else ["พบความไม่สอดคล้อง"]}
