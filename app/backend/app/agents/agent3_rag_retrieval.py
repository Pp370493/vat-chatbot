"""
Agent 3: RAG Retrieval Agent (+ Coreference Resolution สำหรับ multi-turn)
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 4, 14.8

INPUT:  {"raw_text": str, "history": list[{"resolved_query": str, "answer_summary": str}]}
OUTPUT: {"resolved_query": str, "chunks": list[dict], "relevance_scores": list[float]}

Final Scope (A5): ค้นหาเฉพาะ kb_articles ที่ status='approved' เท่านั้น
และใช้ Hybrid Search (Semantic Cosine Similarity + Keyword Matching Boost)
"""
import re
import json
from pathlib import Path
import numpy as np
from app.core.ollama_client import generate
from app.core.config import settings
from app.core.embeddings import get_embedding
from app.db.session import SessionLocal
from app.models.models import KbArticle

# แคช metadata และ active law chunks จาก Graph RAG
_ARTICLES_META = {}
_ACTIVE_LAW_CHUNKS = set()


def reload_articles_meta():
    global _ARTICLES_META, _ACTIVE_LAW_CHUNKS
    _ARTICLES_META.clear()
    _ACTIVE_LAW_CHUNKS.clear()
    data_file = Path(__file__).resolve().parent.parent.parent / "data" / "official_vat_articles.json"
    if data_file.exists():
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                items = json.load(f)
                for item in items:
                    _ARTICLES_META[item["id"]] = item.get("metadata", {})
        except Exception as e:
            print("[WARN] Error loading _ARTICLES_META:", e)

    graph_file = Path(__file__).resolve().parent.parent.parent / "data" / "graph_rag_vat_registration.json"
    if graph_file.exists():
        try:
            with open(graph_file, "r", encoding="utf-8") as f:
                gdata = json.load(f)
                lineages = gdata.get("edges", {}).get("legal_evolution_lineage", [])
                for lin in lineages:
                    for cid in lin.get("active_law_chunks", []):
                        _ACTIVE_LAW_CHUNKS.add(cid)
        except Exception as e:
            print("[WARN] Error loading _ACTIVE_LAW_CHUNKS:", e)


reload_articles_meta()


def resolve_query(raw_text: str, history: list[dict] | None = None) -> str:
    history = history or []
    if not history:
        return raw_text

    # หากคำถามปัจจุบันเป็นประโยคที่สมบูรณ์ชัดเจนในตัวเองอยู่แล้ว ไม่ต้องเรียก LLM ซ้ำ เพื่อลดเวลาประมวลผลบน CPU
    if len(raw_text) > 30 or any(k in raw_text for k in ["ตามประกาศ", "ฉบับที่", "ณ สำนักงานสรรพากร", "www.rd.go.th", "dbd"]):
        return raw_text

    context = "\n".join(
        f"- {h['resolved_query']} -> {h['answer_summary']}" for h in history[-3:]
    )
    result = generate(
        prompt=f"บริบทก่อนหน้า:\n{context}\n\nคำถามปัจจุบัน: {raw_text}\nเขียนคำถามปัจจุบันให้เป็นประโยคที่สมบูรณ์และชัดเจนในตัวเองโดยอิงบริบท:",
        temperature=0.0,
        num_ctx=1024,
        num_predict=60,
        mock_response=raw_text,
    )
    return result["text"].strip() if result["served_by"] != "mock" else raw_text


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _keyword_boost(query: str, text: str, chunk_id: str | None = None) -> float:
    boost = 0.0
    q_lower = query.lower()

    # 1. คำสำคัญเฉพาะโดเมนจดทะเบียน VAT
    domain_terms = [
        "ก่อสร้าง", "โรงงาน", "ล่วงหน้า", "หกเดือน", "6 เดือน",
        "คอนโด", "ห้องชุด", "ออนไลน์", "อินเทอร์เน็ต",
        "ตัวแทนเชิด", "นอมินี", "สำนักงานบัญชี", "ไม่ออกใบทะเบียน",
        "มอบอำนาจ", "สำนักงานใหญ่", "สัญญาเช่า", "หนังสือยินยอม",
        "เอกสาร", "หลักฐาน", "ภ.พ.01", "ภ.พ.20", "แพลตฟอร์ม"
    ]
    for term in domain_terms:
        if term in q_lower and term in text.lower():
            boost += 0.06

    # 2. Priority ช่องทาง: ยึดประกาศ 57 (กระดาษ) และ 159 (อินเทอร์เน็ต) เป็นหลักเท่านั้น
    # ประกาศฉบับที่ 234 จะนำมาใช้เฉพาะกรณีมีคำว่า "DBD" หรือ "กรมพัฒนาธุรกิจ" ในคำถามเท่านั้น
    is_paper_query = any(k in q_lower for k in ["กระดาษ", "ยื่นด้วยตนเอง", "เดินไปยื่น", "สรรพากรพื้นที่", "สำนักงานสรรพากร", "ฉบับที่ 57", "ฉบับ 57"])
    is_internet_query = any(k in q_lower for k in ["อินเทอร์เน็ต", "อินเตอร์เน็ต", "เน็ต", "ออนไลน์", "online", "rd.go.th", "ฉบับที่ 159", "ฉบับ 159", "คอนโด", "อาคารชุด", "แพลตฟอร์ม", "shopee", "lazada", "tiktok", "e-commerce"])
    is_dbd_query = any(k in q_lower for k in ["dbd", "กรมพัฒนาธุรกิจ", "กรมพัฒนาธุรกิจการค้า", "จดพร้อมตั้งบริษัท", "ฉบับที่ 234", "ฉบับ 234"])

    if chunk_id:
        # หากไม่มีคำว่า DBD ในคำถาม ให้ตัดฉบับ 234 ออกจากผลลัพธ์ทันที
        if not is_dbd_query and chunk_id.startswith("VAT234_"):
            return -999.0

        if is_dbd_query:
            if chunk_id.startswith("VAT234_"):
                boost += 0.35
            else:
                boost -= 0.30
        elif is_paper_query:
            if chunk_id.startswith(("VAT57_", "VAT74_", "VAT139_", "VAT165_", "VAT215_", "VAT245_")):
                boost += 0.25
            else:
                boost -= 0.30
        elif is_internet_query:
            if chunk_id.startswith(("VAT159_", "VAT214_", "VAT246_")):
                boost += 0.25
            else:
                boost -= 0.30
        else:
            # หากยังไม่ระบุช่องทาง ยึด 57 และ 159 เป็นหลัก
            if chunk_id.startswith(("VAT57_", "VAT74_", "VAT139_", "VAT165_", "VAT215_", "VAT245_", "VAT159_", "VAT214_", "VAT246_")):
                boost += 0.15

        # กฎข้อแนะนำเทคนิค 1: ป้องกัน Semantic Collision ระหว่าง ข้อ 9 (ใครเซ็น) และ ข้อ 7 (แบบฟอร์ม ภ.พ.20)
        is_signer_query = any(w in q_lower for w in ["ใครเซ็น", "ไม่อยู่", "เซ็นแทน", "ลงนาม", "อำนาจลงนาม", "ผู้มีอำนาจลงนาม", "ใครมีอำนาจ", "ใครอนุมัติ", "ใครเป็นผู้ออก", "ใครเป็นผู้ลงนาม", "ผู้มีอำนาจออก", "ปฏิบัติราชการแทน", "รักษาการ", "เซ็น"])
        if is_signer_query:
            # ชิ้นส่วนข้อ 7 (แบบฟอร์มใบทะเบียน ภ.พ.20/ภ.พ.21) -> Negative Boost -0.60
            if any(k in chunk_id for k in ["ART_07", "VAT57_ART_07", "VAT74_ART_07", "VAT159_ART_07", "VAT234_ART_01"]):
                boost -= 0.60
            # ชิ้นส่วนข้อ 9 (ผู้มีอำนาจออกใบทะเบียน/ลงนาม/ไม่อยู่) -> Positive Boost +0.45
            if any(k in chunk_id for k in ["ART_09", "245_ART_02", "246_ART_05", "165_ART_03", "139_ART_02", "214_ART_04"]):
                boost += 0.45

        # กฎข้อแนะนำเทคนิค 2: การตรวจจับช่องทาง (Channel Routing) สำหรับ คอนโด / ขายของออนไลน์
        is_condo_online = any(k in q_lower for k in ["คอนโด", "ห้องชุด", "ขายของออนไลน์", "shopee", "tiktok", "e-commerce", "แม่ค้าออนไลน์"])
        if is_condo_online:
            # บังคับดึง ข้อ 4/1 (ฉบับ 245) และ ข้อ 1 (ฉบับ 159/246)
            if any(k in chunk_id for k in ["ART_04_1", "245_ART_01", "159_ART_01", "246_ART_01"]):
                boost += 0.35
            # และดึง ข้อ 5(4) วรรคท้าย (ฉบับ 246 - สิทธิยกเว้นหนังสือนิติคอนโด)
            if any(k in chunk_id for k in ["159_ART_05_C", "246_ART_03", "214_ART_02"]):
                boost += 0.30

        # กรณีคำถามเกี่ยวกับเอกสารหลักฐาน (ข้อ 5 ของประกาศ 57 หรือ 159)
        if any(w in q_lower for w in ["เอกสาร", "หลักฐาน", "ต้องใช้อะไร", "ใช้อะไรบ้าง", "เตรียมอะไร"]):
            if any(k in chunk_id for k in ["05", "ART_05", "165_ART_02", "215_ART_01", "215_ART_02", "214_ART_01", "246_ART_02"]):
                boost += 0.15

    # 3. Boost เพิ่มเติมจาก Metadata (boost_keywords & tfidf_keywords & user_intents)
    if chunk_id and chunk_id in _ARTICLES_META:
        meta = _ARTICLES_META[chunk_id]
        for kw in meta.get("boost_keywords", []):
            if kw.lower() in q_lower:
                boost += 0.10
        for tk in meta.get("tfidf_keywords", []):
            if tk.lower() in q_lower:
                boost += 0.06
        for ui in meta.get("user_intents", []):
            if any(w in q_lower for w in ui.lower().split() if len(w) > 3):
                boost += 0.05

    # 4. Graph RAG Active Law Lineage Boost (+0.06 สำหรับกฎหมายปัจจุบันที่ยังมีผลบังคับใช้)
    if chunk_id and chunk_id in _ACTIVE_LAW_CHUNKS:
        boost += 0.06

    return max(-1.0, min(boost, 0.90))


def retrieve(resolved_query: str, top_k: int = 5) -> dict:
    top_k = settings.retrieval_top_k or top_k
    db = SessionLocal()
    try:
        # A5: ดึงเฉพาะบทความที่ approved เท่านั้น
        articles = db.query(KbArticle).filter(KbArticle.status == "approved").all()
        if not articles:
            return {
                "resolved_query": resolved_query,
                "chunks": [],
                "relevance_scores": [],
            }

        # ยึดประกาศ 57 และ 159 เป็นหลัก: หากไม่มีคำว่า "dbd", "กรมพัฒนาธุรกิจ", หรือ "จดพร้อมตั้งบริษัท" ให้กรองฉบับ 234 ออกทั้งหมด
        is_dbd_query = any(k in resolved_query.lower() for k in ["dbd", "กรมพัฒนาธุรกิจ", "กรมพัฒนาธุรกิจการค้า", "จดพร้อมตั้งบริษัท", "ฉบับที่ 234", "ฉบับ 234"])
        if not is_dbd_query:
            articles = [a for a in articles if not a.id.startswith("VAT234_")]

        # คำนวณ Query Embedding โดยระบุ is_query=True
        q_vec = np.array(get_embedding(resolved_query, is_query=True), dtype=float)
        scored = []
        for art in articles:
            if not art.embedding:
                continue
            art_vec = np.array(art.embedding, dtype=float)
            base_score = cosine_sim(q_vec, art_vec)
            boost = _keyword_boost(resolved_query, art.content + " " + (art.title or ""), chunk_id=art.id)
            total_score = base_score + boost
            scored.append((total_score, art))

        # เรียงลำดับคะแนนจากมากไปน้อย
        scored.sort(key=lambda x: x[0], reverse=True)
        top_articles = scored[:top_k]

        chunks = []
        relevance_scores = []
        for score, art in top_articles:
            chunks.append({
                "chunk_id": art.id,
                "text": art.content,
                "source_section": art.source_section or "ประกาศอธิบดีฯ VAT",
            })
            relevance_scores.append(round(score, 4))

        return {
            "resolved_query": resolved_query,
            "chunks": chunks,
            "relevance_scores": relevance_scores,
        }
    finally:
        db.close()
