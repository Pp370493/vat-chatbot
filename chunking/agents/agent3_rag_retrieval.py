# -*- coding: utf-8 -*-
"""
Agent 3: RAG Retrieval Agent (Graph-Enhanced Hybrid Search)
หน้าที่: สกัดคำสำคัญ ค้นหากฎหมายจาก 75 Chunks ด้วย Hybrid Search ร่วมกับ Graph RAG Traversal
จุดสำคัญ:
1. แก้ปัญหา Semantic Collision ระหว่าง ข้อ 9 (ผู้มีอำนาจลงนาม/ไม่อยู่) กับ ข้อ 7 (แบบฟอร์ม ภ.พ.20)
2. กรองและเชื่อมโยงช่องทางยื่น (กระดาษ ฉบับ 57 / เน็ต ฉบับ 159 / DBD ฉบับ 234)
3. เดินตามเส้นทาง Graph Lineage เพื่อเลือก Active Law Chunks ฉบับล่าสุดมาตอบ ป้องกันตัวบทเก่า

หลักการ (mode="primary", ค่าเริ่มต้น):
- ประกาศ 57 (ยื่นกระดาษ) และ 159 (ยื่นอินเทอร์เน็ต) เป็นตัวบทหลักฉบับรวมล่าสุด → ค้นเฉพาะ chunk ที่
  metadata.role == "primary" (ตัด is_boilerplate ออก)
- ประกาศ 234 (role "special") ใช้เฉพาะเมื่อคำถามระบุช่องทาง DBD
- ฉบับแก้ไข (role "amendment") ไม่ถูกค้น แต่แนบเป็นที่มาผ่าน metadata.amended_by
  เช่น "ประกาศฯ (ฉบับที่ 57) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดยฉบับที่ 74, 139, 165, 245"
mode="all" = พฤติกรรมเดิม (ค้นทั้ง 75 chunks) เก็บไว้ใช้เปรียบเทียบผล
metadata.role/amended_by มาจาก scripts/annotate_roles.py
ข้อมูลประกอบที่ไม่มีในตัวบท 57/159 (เช่น รายการกิจการตาม ม.81/3 ในแบบคำขอฉบับ 234) แนบท้าย context ผ่าน
REFERENCE_SNIPPETS เมื่อคำถามตรงหัวข้อ โดยไม่เข้าไปแข่งอันดับกับตัวบทหลัก
"""

import os
import re
import json
from typing import List, Dict, Any, Tuple

DBD_TRIGGERS = ["dbd", "กรมพัฒนาธุรกิจ", "จดพร้อมตั้งบริษัท", "พร้อมจัดตั้ง", "จัดตั้งบริษัท",
                "เปิดบริษัทพร้อม", "e-registration", "ฉบับที่ 234", "ฉบับ 234"]
ANNOUNCEMENT_LABEL = {"57": "ยื่นแบบกระดาษ", "159": "ยื่นผ่านอินเทอร์เน็ต", "234": "ยื่นผ่าน DBD"}

# เอกสารอ้างอิงเสริม: ข้อมูลที่ไม่มีในตัวบท 57/159 แต่อยู่ใน chunk อื่น — แนบท้าย context เมื่อคำถามตรงหัวข้อ
# (ไม่แย่งอันดับใน top-k ของตัวบทหลัก)
EXEMPT_TRIGGERS = ["81/3", "กิจการที่ได้รับยกเว้น", "ได้รับยกเว้น vat", "ได้รับยกเว้นแวท", "ยกเว้นภาษีมูลค่าเพิ่ม", "ยกเว้น vat", "ยกเว้นแวท", "กิจการยกเว้น",
                   "สละสิทธิ", "ขอเสีย vat", "ขอเสียแวท", "ขอเสียภาษีมูลค่าเพิ่ม", "ไม่ถึง 1.8", "ไม่ถึงเกณฑ์",
                   "เข้าระบบ vat", "เข้าสู่ระบบ vat", "ภ.พ.01.1"]
# กฎที่สอง: ถามเรื่อง "ขอเข้า VAT" คู่กับประเภทกิจการที่อยู่ในรายการ ม.81/3
OPT_IN_WORDS = ["เข้าแวท", "เข้า vat", "ขอเข้า", "อยากจด vat", "อยากจดแวท"]
EXEMPT_CATEGORY_WORDS = ["พืชผล", "เกษตร", "สัตว์", "ปุ๋ย", "ปลาป่น", "อาหารสัตว์", "ยาฆ่า", "เคมีภัณฑ์",
                         "หนังสือพิมพ์", "นิตยสาร", "ตำรา", "หนังสือเรียน", "ขนส่ง", "อากาศยาน",
                         "เขตอุตสาหกรรมส่งออก", "น้ำมันเชื้อเพลิงทางท่อ", "กิจการขนาดย่อม"]
REFERENCE_SNIPPETS = {
    # รายการกิจการยกเว้นที่ขอเข้า VAT ตาม ม.81/3 ในแบบคำขอแนบท้ายฉบับ 234 (ข้อ 2.1–2.5)
    "s81_3_exempt_list": {"chunk_id": "VAT234_ART_ATTACHMENT", "triggers": EXEMPT_TRIGGERS,
                          "combo": (OPT_IN_WORDS, EXEMPT_CATEGORY_WORDS),
                          "start": "กรณีเป็นกิจการที่ได้รับยกเว้น", "end": "5. ผู้ยื่นคำขอ",
                          "label": "รายการกิจการที่ได้รับยกเว้นภาษีมูลค่าเพิ่มซึ่งขอเข้าสู่ระบบตามมาตรา 81/3 ได้ "
                                   "(จากแบบคำขอแนบท้ายประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม ฉบับที่ 234)"},
}



def kw_in(kw: str, text: str) -> bool:
    """keyword อยู่ใน text ไหม — keyword ที่ลงท้ายด้วยเลข (เช่น "ข้อ 1") ต้องไม่มีเลขหรือ / ต่อท้าย
    ไม่งั้น "ข้อ 1" จะไปเจอใน "ข้อ 10" และ "ข้อ 5" เจอใน "ข้อ 5/1"
    """
    kw = kw.lower()
    if not kw or not kw[-1].isdigit():
        return kw in text
    return re.search(re.escape(kw) + r"(?![\d/])", text) is not None

class RAGRetrievalAgent:
    def __init__(self, base_dir: str = None, mode: str = "primary"):
        if mode not in ("primary", "all"):
            raise ValueError("mode ต้องเป็น 'primary' หรือ 'all'")
        self.mode = mode
        if base_dir is None:
            # ใช้พาธของโฟลเดอร์ chunking ประกาศ
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir

        self.chunks_db: Dict[str, Dict[str, Any]] = {}
        self.graph_data: Dict[str, Any] = {}
        self.synonym_dict: Dict[str, Any] = {}

        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """โหลดไฟล์ Chunks ทั้ง 10 ประกาศ, Graph RAG และ Synonym Dictionary"""
        # 1. โหลด Graph RAG
        graph_path = os.path.join(self.base_dir, "graph_rag_vat_registration.json")
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                self.graph_data = json.load(f)

        # 2. โหลด Synonym Boost Dictionary
        synonym_path = os.path.join(self.base_dir, "vat_synonym_boost_dictionary.json")
        if os.path.exists(synonym_path):
            with open(synonym_path, "r", encoding="utf-8") as f:
                self.synonym_dict = json.load(f)

        # 3. โหลดไฟล์ Chunks ทั้ง 10 ไฟล์
        chunk_files = [
            "vat57_chunks_local_llm.json",
            "vat74_chunks_local_llm.json",
            "vat139_chunks_local_llm.json",
            "vat159_chunks_local_llm.json",
            "vat165_chunks_local_llm.json",
            "vat214_chunks_local_llm.json",
            "vat215_chunks_local_llm.json",
            "vat234_chunks_local_llm.json",
            "vat245_chunks_local_llm.json",
            "vat246_chunks_local_llm.json"
        ]

        total_loaded = 0
        for cf in chunk_files:
            file_path = os.path.join(self.base_dir, cf)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                    for c in chunks:
                        cid = c.get("chunk_id")
                        if cid:
                            c["source_file"] = cf
                            self.chunks_db[cid] = c
                            total_loaded += 1
        # print(f"[Agent 3] Loaded {total_loaded} chunks from 10 announcement files.")

    def search(self, user_query: str, detected_channel: str = "WALK_IN", top_k_search: int = 5, top_k_prompt: int = 3) -> Dict[str, Any]:
        """
        ทำการค้นหาแบบ Hybrid Search:
        1. Base Lexical Match (คำค้นใน text, title, tfidf_keywords)
        2. Intent & Synonym Boost (จาก vat_synonym_boost_dictionary.json)
        3. Collision Suppression (กดคะแนน ข้อ 7 หากถามเรื่องอำนาจลงนาม ข้อ 9)
        4. Graph RAG Lineage Active Law Priority Boost
        """
        query = user_query.strip().lower()
        scored_chunks: List[Tuple[str, float, Dict[str, Any]]] = []

        # วิเคราะห์ Intent และดึง Boost Rules จาก Synonym Dictionary
        clause_boosts = self._evaluate_synonym_boosts(query)

        # เช็กเฉพาะ Collision Rule ระหว่าง ข้อ 9 และ ข้อ 7
        is_authority_intent = False
        authority_triggers = ["ใครเซ็น", "ไม่อยู่", "เซ็นแทน", "ลงนาม", "ผู้มีอำนาจ", "อำนาจลงนาม", "ใครอนุมัติ", "ใครเป็นคนออก", "เซ็นอนุมัติ"]
        for trig in authority_triggers:
            if trig in query:
                is_authority_intent = True
                break

        # เลือกชุด chunk ที่จะค้นตามหลักการ
        is_dbd = detected_channel == "DBD" or any(t in query for t in DBD_TRIGGERS)
        candidates = {cid: c for cid, c in self.chunks_db.items() if self._is_candidate(c, is_dbd)}

        # คำนวณคะแนนสำหรับทุก Chunk ในชุดที่เลือก
        for cid, chunk in candidates.items():
            base_score = self._compute_lexical_similarity(query, chunk)
            boost_score = 0.0
            reasons = []

            # เพิ่มคะแนนจาก Synonym Boost
            for clause_key, boost_val in clause_boosts.items():
                target_chunks = self.synonym_dict.get("clauses", {}).get(clause_key, {}).get("target_chunks", [])
                if cid in target_chunks:
                    boost_score += boost_val
                    reasons.append(f"Synonym Boost ({clause_key}): +{boost_val:.2f}")

            # แก้ไข Semantic Collision: กดคะแนนข้อ 7 ถ้าระบบตรวจพบ Intent ผู้มีอำนาจลงนาม (ข้อ 9)
            if is_authority_intent:
                if cid in ["VAT57_ART_07", "VAT159_ART_07", "VAT74_ART_07", "VAT234_ART_06"]:
                    boost_score -= 0.60
                    reasons.append("Collision Penalty (Section 7 Form suppressed by Section 9 Signing Authority intent): -0.60")
                elif cid in ["VAT57_ART_09", "VAT159_ART_09", "VAT245_ART_02", "VAT246_ART_05", "VAT234_ART_08"]:
                    boost_score += 0.45
                    reasons.append("Ground Truth Boost (Section 9 Signing Authority active): +0.45")

            # Graph RAG Lineage Boost: กฎหมายฉบับล่าสุด (Active Law) จะได้คะแนนพิเศษ
            # ในโหมด primary ทุก chunk เป็นตัวบทฉบับปัจจุบันอยู่แล้ว lineage boost จึงไม่ช่วยแยก
            # (และจะดัน chunk กลุ่มเดิมขึ้นมาทุกคำถาม) — ใช้เฉพาะโหมด all ที่มีฉบับเก่าปนอยู่
            active_law_bonus = 0.0 if self.mode == "primary" else self._check_graph_lineage_active(cid, detected_channel)
            if active_law_bonus > 0:
                boost_score += active_law_bonus
                reasons.append(f"Graph RAG Lineage Active Law Boost: +{active_law_bonus:.2f}")

            total_score = base_score + boost_score
            scored_chunks.append((cid, total_score, {"base": base_score, "boost": boost_score, "reasons": reasons, "chunk": chunk}))

        # จัดอันดับตามคะแนนรวมจากมากไปน้อย
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Audit Log Top-5 และ Prompt Context Top-3
        search_top_5 = scored_chunks[:top_k_search]
        prompt_top_3 = scored_chunks[:top_k_prompt]

        # รวมข้อความ Context สำหรับส่งให้ Agent 4 (LLM Prompt)
        # แนบข้อความอ้างอิง (รวมฉบับที่แก้ไขเพิ่มเติม) ไว้หัว chunk ให้ LLM อ้างได้ถูก
        assembled_context = "\n\n".join(
            [f"[อ้างอิง: {self.legal_citation(item[0])}]\n{item[2]['chunk']['llm_context']}" for item in prompt_top_3])
        references = self.reference_snippets(query) if self.mode == "primary" else []
        for ref in references:
            assembled_context += f"\n\n[ข้อมูลประกอบ: {ref['label']}]\n{ref['text']}"

        return {
            "query": user_query,
            "mode": self.mode,
            "searched_chunks": len(candidates),
            "detected_channel": detected_channel,
            "is_authority_intent": is_authority_intent,
            "prompt_top_chunks": [
                {
                    "chunk_id": item[0],
                    "score": round(item[1], 4),
                    "article_ref": item[2]["chunk"].get("article_ref"),
                    "title": item[2]["chunk"].get("title"),
                    "source_file": item[2]["chunk"].get("source_file"),
                    "reasons": item[2]["reasons"],
                    "llm_context": item[2]["chunk"].get("llm_context"),
                    "role": item[2]["chunk"].get("metadata", {}).get("role"),
                    "citation": self.legal_citation(item[0]),
                }
                for item in prompt_top_3
            ],
            "audit_log_top_5": [
                {
                    "rank": idx + 1,
                    "chunk_id": item[0],
                    "score": round(item[1], 4),
                    "article_ref": item[2]["chunk"].get("article_ref"),
                    "title": item[2]["chunk"].get("title"),
                    "source_file": item[2]["chunk"].get("source_file")
                }
                for idx, item in enumerate(search_top_5)
            ],
            "reference_snippets": references,
            "assembled_llm_context": assembled_context
        }

    def reference_snippets(self, query: str) -> List[Dict[str, Any]]:
        """ตัดเฉพาะส่วนที่เกี่ยวข้องจาก chunk อ้างอิงเสริม เมื่อคำถามตรงหัวข้อ"""
        out = []
        for key, spec in REFERENCE_SNIPPETS.items():
            combo = spec.get("combo")
            matched = any(t in query for t in spec["triggers"]) or (
                combo is not None and any(w in query for w in combo[0]) and any(w in query for w in combo[1]))
            if not matched:
                continue
            raw = self.chunks_db.get(spec["chunk_id"], {}).get("official_raw_text", "")
            start, end = raw.find(spec["start"]), raw.find(spec["end"])
            if start < 0 or end <= start:
                continue
            out.append({"key": key, "chunk_id": spec["chunk_id"], "label": spec["label"],
                        "text": raw[start:end].strip()})
        return out

    def _is_candidate(self, chunk: Dict[str, Any], is_dbd: bool) -> bool:
        if self.mode == "all":
            return True
        meta = chunk.get("metadata", {})
        if "role" not in meta:
            raise RuntimeError("chunk ยังไม่มี metadata.role — รัน scripts/annotate_roles.py --write ก่อน")
        if meta.get("is_boilerplate"):
            return False
        return meta["role"] == "primary" or (is_dbd and meta["role"] == "special")

    def legal_citation(self, chunk_id: str) -> str:
        """ข้อความอ้างอิงตัวบท เช่น 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดยฉบับที่ 74, 139, 165, 245'"""
        chunk = self.chunks_db.get(chunk_id, {})
        meta = chunk.get("metadata", {})
        ann = chunk_id.split("_")[0][3:]
        article = chunk.get("article_ref", "")
        if meta.get("role") == "amendment" and meta.get("amends"):
            primary = meta["amends"][0]
            return (f"{self.legal_citation(primary)} (ข้อความตามประกาศฉบับที่ {ann}"
                    + ("" if meta.get("is_current", True) else " ซึ่งถูกแก้ไขอีกภายหลัง — ไม่มีผลบังคับแล้ว") + ")")
        text = f"ประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม (ฉบับที่ {ann}) {article}".strip()
        amenders = sorted({a.split("_")[0][3:] for a in meta.get("amended_by", [])}, key=int)
        if amenders:
            text += " ซึ่งแก้ไขเพิ่มเติมโดยฉบับที่ " + ", ".join(amenders)
        if ann in ANNOUNCEMENT_LABEL:
            text += f" [{ANNOUNCEMENT_LABEL[ann]}]"
        return text

    def _compute_lexical_similarity(self, query: str, chunk: Dict[str, Any]) -> float:
        """คำนวณคะแนนความคล้ายคลึงของคำ (Keyword Overlap / TF-IDF Proxy)"""
        score = 0.0
        content = (chunk.get("title", "") + " " + chunk.get("llm_context", "")).lower()

        # ตรวจสอบคำใน Query แบบ N-gram ย่อย
        query_words = re.findall(r"[\w\.\/]+", query)
        for w in query_words:
            if len(w) >= 2 and w in content:
                score += 0.08

        # ตรวจสอบ Boost Keywords ใน Metadata ของ Chunk
        metadata = chunk.get("metadata", {})
        for kw in metadata.get("boost_keywords", []):
            if kw_in(kw, query):
                score += 0.15

        for tf_kw in metadata.get("tfidf_keywords", []):
            if kw_in(tf_kw, query):
                score += 0.10

        return min(score, 1.0)

    def _evaluate_synonym_boosts(self, query: str) -> Dict[str, float]:
        """จับคู่คำใน Query กับ Synonym Boost Dictionary"""
        boosts = {}
        clauses = self.synonym_dict.get("clauses", {})
        for ckey, cdata in clauses.items():
            kws = cdata.get("keywords", [])
            triggers = cdata.get("intent_triggers", [])
            weight = cdata.get("boost_weight", 0.30)

            match = False
            for kw in kws:
                if kw_in(kw, query):
                    match = True
                    break
            if not match:
                for trig in triggers:
                    if kw_in(trig, query):
                        match = True
                        break

            if match:
                boosts[ckey] = weight
        return boosts

    def _check_graph_lineage_active(self, chunk_id: str, channel: str) -> float:
        """ตรวจสอบว่า Chunk นี้เป็น Active Law ใน Graph Lineage หรือไม่"""
        lineages = self.graph_data.get("edges", {}).get("legal_evolution_lineage", [])
        for lin in lineages:
            active_chunks = lin.get("active_law_chunks", [])
            if chunk_id in active_chunks:
                return 0.25
        return 0.0

if __name__ == "__main__":
    agent = RAGRetrievalAgent()
    
    # ทดสอบเคสสำคัญ: ปัญหา Semantic Collision
    test_q = "กรณีผู้มีอำนาจออก ภ.พ.20 ไม่อยู่ ใครจะเป็นผู้มีอำนาจลงนาม"
    res = agent.search(test_q)
    print(f"=== ผลการค้นหาสำหรับ: '{test_q}' ===")
    print("Top-3 Chunks ที่ส่งให้ LLM:")
    for c in res["prompt_top_chunks"]:
        print(f"[{c['chunk_id']}] Score: {c['score']} | {c['title']} | File: {c['source_file']}")
        print(f"   เหตุผล: {c['reasons']}")
