"""
Orchestrator เชื่อม Agent 1-6 ตาม State Flow พร้อม Full DB Persistence
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 6 (Schema) & ส่วนที่ 9 (State Flow)

State Flow:
NEW -> SCOPE_CHECKED -> [out_of_scope] REDIRECTED (จบ)
                     -> [form_assist] FORM_ASSIST (จบ)
                     -> [qa] RETRIEVED -> DRAFTED -> VERIFIED -> TIER_ASSIGNED
                        -> [auto_answer] ANSWERED (จบ)
                        -> [officer_review / senior_review] PENDING_REVIEW (รอ Supervisor)
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
import re
from app.models.models import (
    Query, Conversation, OutOfScopeRoute, RetrievalLog, DraftAnswer,
    VerificationScore, RiskAssessment, Escalation, AuditLog, Department,
    StaffUser, KbArticle, gen_uuid
)
from app.graph import clarify as cl
from app.agents import (
    agent1_intent_classifier as a1,
    agent2_out_of_scope_router as a2,
    agent3_rag_retrieval as a3,
    agent4_responder as a4,
    agent5_verifier as a5,
    agent6_risk_tier as a6,
    agent7_checklist_assistant as a7,
)


def sanitize_pii(text: str) -> str:
    """
    ตัดข้อมูลส่วนบุคคล (PII Stripping) ตามมาตรฐาน ISO/IEC 27001
    - เลขประจำตัวประชาชน 13 หลัก
    - เบอร์โทรศัพท์ 9-10 หลัก
    """
    if not text:
        return ""
    # เลข ปชช. 13 หลัก (มีหรือไม่มีขีด)
    text = re.sub(r"\b\d{1}-?\d{4}-?\d{5}-?\d{2}-?\d{1}\b", "[REDACTED_ID_CARD]", text)
    text = re.sub(r"\b\d{13}\b", "[REDACTED_ID_CARD]", text)
    # เบอร์โทรศัพท์ไทย
    text = re.sub(r"\b0\d{1,2}-?\d{3,4}-?\d{4}\b", "[REDACTED_PHONE]", text)
    return text


def _get_default_staff_id(db: Session) -> str:
    """
    บัญชีระบบสำหรับสคริปต์/การทดสอบที่เรียก run_pipeline โดยไม่มีผู้ใช้ (API ส่งผู้ใช้จาก token เสมอ)
    is_active=False และรหัสผ่านใช้ไม่ได้ จึงเข้าสู่ระบบด้วยบัญชีนี้ไม่ได้
    """
    from app.core.security import UNUSABLE_PASSWORD
    staff = db.query(StaffUser).filter(StaffUser.email == SYSTEM_USER_EMAIL).first()
    if staff:
        return staff.id
    staff = StaffUser(
        id=gen_uuid(),
        full_name="System (scripts)",
        email=SYSTEM_USER_EMAIL,
        password_hash=UNUSABLE_PASSWORD,
        role="officer",
        is_active=False,
    )
    db.add(staff)
    db.commit()
    return staff.id


SYSTEM_USER_EMAIL = "system@local"

PAPER_WORDS = [
    "กระดาษ", "ยื่นด้วยตนเอง", "เดินไปยื่น", "สรรพากรพื้นที่", "สำนักงานสรรพากร",
    "ฉบับที่ 57", "ฉบับ 57", "ภ.พ.01 3 ฉบับ", "ภพ01 กระดาษ",
]
INTERNET_WORDS = [
    "อินเทอร์เน็ต", "อินเตอร์เน็ต", "เน็ต", "ออนไลน์", "online",
    "rd.go.th", "ฉบับที่ 159", "ฉบับ 159", "คอนโด", "อาคารชุด", "แพลตฟอร์ม", "shopee", "lazada", "tiktok",
]
DBD_WORDS = ["dbd", "กรมพัฒนาธุรกิจ", "จัดตั้งบริษัท", "ฉบับที่ 234", "ฉบับ 234", "พร้อมจัดตั้ง"]

CHANNEL_PHRASE = {
    "paper": "ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ ตามประกาศฉบับที่ 57",
    "internet": "ยื่นผ่านระบบอินเทอร์เน็ต www.rd.go.th ตามประกาศฉบับที่ 159",
    "dbd": "ยื่นพร้อมการจดทะเบียนจัดตั้งนิติบุคคลต่อกรมพัฒนาธุรกิจการค้า (DBD) ตามประกาศฉบับที่ 234",
}
# answer_summary ที่ branch clarification บันทึกไว้ — ใช้รู้ว่าเทิร์นก่อนหน้าเป็นคำถามซักถามแบบใด
CHANNEL_CLARIFICATION_SUMMARY = "สอบถามช่องทางการยื่นจดทะเบียน VAT"
PURPOSE_CLARIFICATION_SUMMARY = "สอบถามยืนยันประเภทการยื่นแบบ"
PP01_CHOICE_RE = re.compile(r"ภ\.?พ\.?\s*01|จดทะเบียนภาษีมูลค่าเพิ่มใหม่|ขอจดทะเบียน")


def detect_channel(text: str) -> str | None:
    """ช่องทางที่ข้อความระบุ: paper (ฉบับ 57) / internet (ฉบับ 159) / dbd (ฉบับ 234) หรือ None"""
    t = (text or "").lower()
    if any(k in t for k in PAPER_WORDS):
        return "paper"
    if any(k in t for k in INTERNET_WORDS):
        return "internet"
    if any(k in t for k in DBD_WORDS):
        return "dbd"
    return None


def merge_clarification_reply(text: str, history: list[dict]) -> str | None:
    """
    ถ้าเทิร์นก่อนหน้าระบบถามช่องทาง/วัตถุประสงค์ และข้อความนี้คือคำตอบของผู้ใช้
    คืนคำถามเดิมที่เติมคำตอบนั้นแล้ว เพื่อให้ขั้นถัดไปค้นและตอบตามคำถามเดิม (ไม่ใช่ตามข้อความเลือกช่องทาง)
    """
    if not history:
        return None
    last = history[-1]
    summary = last.get("answer_summary") or ""
    original = (last.get("resolved_query") or "").strip()
    if not original:
        return None
    if summary.startswith(cl.FORM_CLARIFICATION_SUMMARY):
        return cl.merge_form_reply(text, original, CHANNEL_PHRASE, detect_channel)
    if summary.startswith(CHANNEL_CLARIFICATION_SUMMARY):
        channel = detect_channel(text)
        if channel:
            return f"{original} ({CHANNEL_PHRASE[channel]})"
    elif summary.startswith(PURPOSE_CLARIFICATION_SUMMARY):
        if PP01_CHOICE_RE.search(text or ""):
            return f"{original} (ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่ม แบบ ภ.พ.01)"
    return None


def check_channel_ambiguity(raw_text: str, history: list[dict]) -> tuple[bool, str | None]:
    """
    ตรวจสอบว่าคำถามเป็นเรื่องการจดทะเบียน VAT ที่ยังไม่ระบุช่องทางหรือไม่
    (ยื่นแบบกระดาษ ประกาศ 57 vs ยื่นผ่านอินเทอร์เน็ต ประกาศ 159 vs DBD ประกาศ 234)
    กฎ: ถ้าเป็นการจด VAT แล้วบริบทไม่ครบว่าเป็นการจดด้วยกระดาษ หรือ ผ่านอินเทอร์เน็ต
    ให้ระบบถามก่อนแล้วค่อยตอบ (Clarification)
    ยกเว้น: กรณีที่เป็นประเด็นเฉพาะที่กฎหมายกำหนดไว้เหมือนกันหรือเป็นเอกเทศ
    เช่น การจดล่วงหน้า 6 เดือน (ก่อสร้าง/เครื่องจักร), ข้อ 6 เหตุไม่ออกใบทะเบียน/นอมินี,
    ผู้มีอำนาจลงนาม (ข้อ 9), หรือการสละสิทธิยกเว้นภาษี (81/3)
    """
    # ดูช่องทางจากคำถามของผู้ใช้ในเทิร์นก่อนๆ เท่านั้น ไม่ดูคำตอบของระบบ — คำตอบมักมีคำว่า "สำนักงานสรรพากร"
    # ทำให้คำถามถัดไปในบทสนทนาถูกเดาว่าเป็นการยื่นแบบกระดาษทั้งที่ผู้ใช้ไม่ได้บอก
    hist_text = " ".join(h.get("resolved_query", "") for h in history).lower()
    q_lower = raw_text.lower()
    channel = detect_channel(f"{hist_text} {q_lower}")

    # คำถามที่มีพฤติการณ์ตามข้อ 6 (เหตุไม่ออกใบทะเบียน ซึ่งเหมือนกันทั้ง 57/159) ไม่ต้องถามช่องทาง
    # ให้ไปถึง Agent 6 เพื่อส่งต่อเจ้าหน้าที่
    if a6.find_risk_factors(raw_text):
        return False, None

    if channel:
        return False, channel

    # ประเด็นเฉพาะที่กฎหมายเหมือนกันทั้ง 57 และ 159 หรือเป็นเอกเทศ ไม่ต้องถามช่องทาง
    self_contained_keywords = [
        "ก่อสร้างโรงงาน", "สร้างโรงงาน", "ก่อสร้างอาคาร", "สร้างอาคาร", "ติดตั้งเครื่องจักร", "สั่งซื้อเครื่องจักร", "ซื้อเครื่องจักร",
        "6 เดือน", "หกเดือน", "ล่วงหน้า", "ล่วงหน้ากี่เดือน", "จดล่วงหน้า", "ขอแวทล่วงหน้า", "ขอ vat ล่วงหน้า", "ล่วงหน้าได้กี่เดือน", "จดทะเบียนล่วงหน้า",
        "นอมินี", "ตัวแทนเชิด", "แบล็กลิสต์", "สวมชื่อ", "สำนักงานบัญชีบังหน้า", "สำนักงานทนายความ",
        "ใครเซ็น", "เซ็นแทน", "ใครมีอำนาจ", "ผู้มีอำนาจลงนาม", "สรรพากรพื้นที่ลงนาม",
        "มาตรา 81/3", "81/3", "สละสิทธิ"
    ]
    if any(sk in q_lower for sk in self_contained_keywords):
        return False, None

    # คำถามหัวข้อเกี่ยวกับการจดทะเบียน VAT ทั่วไปทั้งหมด (เอกสาร, สถานที่, ขั้นตอน, ยื่นอย่างไร, ขอจดทะเบียน)
    vat_reg_general_patterns = [
        "จด vat", "จดแวท", "จดทะเบียน", "ยื่นคำขอ", "ขอจด", "เข้า vat", "เข้าแวท",
        "ภ.พ.01", "ภพ01", "ภ.พ.20", "ภพ20", "เอกสาร", "หลักฐาน", "ใช้อะไร", "เตรียมอะไร",
        "ที่ไหน", "สถานที่", "ช่องทาง", "ขั้นตอน", "วิธีการ", "จดยังไง", "ยื่นยังไง",
        "ต้องทำอย่างไร", "ทำอย่างไร", "ทำยังไง"
    ]
    if any(vp in q_lower for vp in vat_reg_general_patterns):
        return True, None

    return False, None


def run_pipeline(
    raw_text: str,
    session_id: str,
    conversation_id: str | None = None,
    staff_user_id: str | None = None,
    db: Session | None = None,
) -> dict:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        user_id = staff_user_id or _get_default_staff_id(db)

        # 1. จัดการ Conversation (Multi-turn Tracking)
        conv = None
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()

        if not conv:
            conv = Conversation(
                id=conversation_id or gen_uuid(),
                staff_user_id=user_id,
                started_at=datetime.utcnow(),
                last_message_at=datetime.utcnow(),
            )
            db.add(conv)
            db.commit()
        else:
            conv.last_message_at = datetime.utcnow()
            db.commit()

        # ดึงประวัติไม่เกิน 5 เทิร์นล่าสุดของ Conversation เดียวกัน (Sliding Window)
        prev_queries = (
            db.query(Query)
            .filter(Query.conversation_id == conv.id, Query.resolved_query.isnot(None))
            .order_by(Query.turn_number.asc())
            .all()
        )
        turn_number = len(prev_queries) + 1
        history = [
            {"resolved_query": q.resolved_query, "answer_summary": q.answer_summary or ""}
            for q in prev_queries[-5:]
        ]

        # 2. บันทึก Query (สถานะ: new) พร้อมตัดข้อมูล PII ตาม ISO/IEC 27001
        sanitized_text = sanitize_pii(raw_text)
        query = Query(
            id=gen_uuid(),
            session_id=session_id,
            conversation_id=conv.id,
            turn_number=turn_number,
            raw_text=sanitized_text,
            status="new",
        )
        db.add(query)
        db.commit()

        # 2.1 ถ้าเทิร์นก่อนหน้าระบบถามช่องทาง/วัตถุประสงค์ ให้รวมคำตอบเข้ากับคำถามเดิม
        # (เดิมระบบค้นตัวบทจากข้อความเลือกช่องทางอย่างเดียว คำถามเดิมจึงหาย)
        effective_text = merge_clarification_reply(sanitized_text, history) or sanitized_text

        # 3. Agent 1: Intent & Scope Classification
        intent = a1.classify(effective_text, history)
        query.in_scope = intent["in_scope"]
        query.sub_intent = intent["sub_intent"]
        query.scope_confidence = intent["confidence"]
        query.status = "scope_checked"
        db.commit()

        # กรณี Out-of-Scope -> Agent 2
        if not intent["in_scope"]:
            import json
            depts = []
            for d in db.query(Department).all():
                kws = d.topic_keywords
                if isinstance(kws, str):
                    try:
                        kws = json.loads(kws)
                    except Exception:
                        kws = []
                depts.append({
                    "id": d.id,
                    "name": d.name,
                    "topic_keywords": kws or [],
                    "contact_channel": d.contact_channel,
                })
            route = a2.route(effective_text, depts)

            oos = OutOfScopeRoute(
                id=gen_uuid(),
                query_id=query.id,
                matched_topic=route["matched_topic"],
                matched_via=route["matched_via"],
                department_id=route.get("department_id"),
                redirect_message=route["redirect_message"],
            )
            db.add(oos)
            query.status = "redirected"

            audit = AuditLog(
                id=gen_uuid(),
                query_id=query.id,
                event_type="out_of_scope_redirect",
                event_data=route,
                actor_type="staff",
                actor_id=user_id,
            )
            db.add(audit)
            db.commit()

            return {
                "query_id": query.id,
                "conversation_id": conv.id,
                "turn_number": turn_number,
                "type": "redirect",
                "payload": route,
            }

        # กรณี Form Assistance -> ส่งต่อ Agent 7 (Document Checklist Assistant)
        if intent["sub_intent"] == "form_assist":
            query.status = "form_assist"
            initial_profile = {
                "channel": "paper",
                "taxpayer_type": "individual_thai",
                "location_type": "rented",
                "is_power_of_attorney": False,
            }
            checklist_data = a7.generate_checklist(initial_profile)
            msg = (
                "📋 **ระบบตัวช่วยตรวจสอบ Checklist เอกสารการยื่นคำขอจดทะเบียน VAT (Agent 7)**\n\n"
                "ระบบเปิดเครื่องมือช่วยตรวจสอบรายการเอกสารตามหลักเกณฑ์ **ข้อ 5 ของประกาศอธิบดีกรมสรรพากร**\n\n"
                "เจ้าหน้าที่สามารถเลือกคุณลักษณะของผู้ยื่นคำขอด้านล่าง เพื่อให้ระบบสร้าง Checklist และทำเครื่องหมาย [✓] "
                "เพื่อประเมินความครบถ้วนของเอกสารได้ทันทีค่ะ"
            )
            query.answer_summary = "เปิดระบบ Checklist Assistant (Agent 7) ตรวจเอกสารข้อ 5"
            db.commit()
            return {
                "query_id": query.id,
                "conversation_id": conv.id,
                "turn_number": turn_number,
                "type": "form_assist",
                "payload": {
                    "message": msg,
                    "draft_text": msg,
                    "checklist_data": checklist_data,
                    "offer_checklist": True,
                    "tier": "auto_answer",
                    "trust_score": 1.0,
                },
            }

        # 3.2 กรณีต้องยืนยันวัตถุประสงค์ (ถามเรื่องยื่นแบบ/ยื่นแบบกระดาษ แต่ไม่ได้ระบุว่าคือ ภ.พ.01 หรือแบบอื่นๆ)
        if intent["sub_intent"] == "confirm_purpose":
            purpose_text = (
                "การยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ มีหลายประเภทแบบแสดงรายการและคำขอ ซึ่งมีหลักเกณฑ์และเอกสารหลักฐานที่แตกต่างกันอย่างสิ้นเชิงค่ะ\n\n"
                "เนื่องจากระบบนี้เป็น **ระบบสนับสนุนงานจดทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.01)** โดยเฉพาะ เพื่อให้คำแนะนำและรายการเอกสารได้อย่างถูกต้องตรงประเด็น ขอสอบถามว่าท่านประสงค์จะยื่นแบบกระดาษในเรื่องใดคะ?\n\n"
                "1. 📄 **การยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มใหม่ (แบบ ภ.พ.01)** *(ตามประกาศอธิบดีฯ ฉบับที่ 57)*\n"
                "2. 📝 **การแจ้งเปลี่ยนแปลงข้อมูลทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.09)** เช่น ย้ายที่ตั้ง, เปลี่ยนชื่อ, เพิ่มสาขา\n"
                "3. 📊 **การยื่นแบบแสดงรายการและชำระภาษีมูลค่าเพิ่มประจำเดือน (แบบ ภ.พ.30)**\n"
                "4. 💼 **การยื่นแบบแสดงรายการภาษีเงินได้บุคคลธรรมดา หรือ นิติบุคคล (ภ.ง.ด.)**"
            )
            citations = []
            relevant_articles = []
            draft_ans = DraftAnswer(
                id=gen_uuid(),
                query_id=query.id,
                draft_text=purpose_text,
                citations=citations,
            )
            db.add(draft_ans)
            query.resolved_query = effective_text
            query.answer_summary = "สอบถามยืนยันประเภทการยื่นแบบ (ภ.พ.01 / ภ.พ.09 / ภ.พ.30 / ภ.ง.ด.)"
            query.status = "answered"
            db.commit()

            return {
                "query_id": query.id,
                "conversation_id": conv.id,
                "turn_number": turn_number,
                "resolved_query": effective_text,
                "type": "clarification",
                "payload": {
                    "draft_text": purpose_text,
                    "citations": citations,
                    "relevant_articles": relevant_articles,
                    "is_clarification": True,
                    "clarification_type": "purpose",
                    "form": cl.build_form([cl.PURPOSE_GROUP]),
                    "tier": "auto_answer",
                    "trust_score": 1.0,
                },
            }

        # 3.5 ถามข้อมูลที่ยังขาดก่อนตอบ (ฟอร์ม checkbox): ช่องทางยื่น และ (คำถามเรื่องเอกสาร) ประเภทผู้ยื่น/สถานประกอบการ
        #     ถ้าเทิร์นก่อนหน้าเพิ่งถามไป ไม่ถามซ้ำ — ตอบตามข้อมูลที่ได้
        is_ambiguous, detected_channel = check_channel_ambiguity(effective_text, history)
        last_summary = (history[-1].get("answer_summary") or "") if history else ""
        just_asked = last_summary.startswith((cl.FORM_CLARIFICATION_SUMMARY, CHANNEL_CLARIFICATION_SUMMARY))
        hist_text = " ".join(h.get("resolved_query", "") for h in history)
        need_applicant = (
            not just_asked
            and cl.is_document_question(effective_text)
            and not cl.has_applicant_info(f"{hist_text} {effective_text}")
            and detected_channel != "dbd"
            and not a6.find_risk_factors(effective_text)
        )
        groups = ([cl.CHANNEL_GROUP] if is_ambiguous and not just_asked else []) + \
                 ([cl.APPLICANT_GROUP, cl.PREMISES_GROUP] if need_applicant else [])
        if groups:
            parts = []
            if is_ambiguous and not just_asked:
                parts.append("ข้อกำหนด ขั้นตอน และเอกสารของการจดทะเบียน VAT แตกต่างกันตามช่องทางที่ยื่นคำขอ")
            if need_applicant:
                parts.append("เอกสารประกอบคำขอตามข้อ 5 แยกตามประเภทผู้ยื่นและสถานประกอบการ")
            clarification_text = (
                " และ".join(parts) + "\n\n"
                "เพื่อให้สรุปข้อมูลได้ตรงกับกรณีของท่าน กรุณาเลือกข้อมูลด้านล่างแล้วกด \"ยืนยัน\" ค่ะ"
            )
            form = cl.build_form(groups)
            draft_ans = DraftAnswer(
                id=gen_uuid(),
                query_id=query.id,
                draft_text=clarification_text,
                citations=[],
            )
            db.add(draft_ans)
            query.resolved_query = effective_text
            query.answer_summary = f"{cl.FORM_CLARIFICATION_SUMMARY} ({', '.join(g['short'] for g in groups)})"
            query.status = "answered"
            db.commit()

            return {
                "query_id": query.id,
                "conversation_id": conv.id,
                "turn_number": turn_number,
                "resolved_query": effective_text,
                "type": "clarification",
                "payload": {
                    "draft_text": clarification_text,
                    "citations": [],
                    "relevant_articles": [],
                    "is_clarification": True,
                    "clarification_type": "form",
                    "form": form,
                    "tier": "auto_answer",
                    "trust_score": 1.0,
                },
            }

        # 4. Agent 3: Query Resolution & RAG Retrieval
        resolved_query = a3.resolve_query(effective_text, history)
        query.resolved_query = resolved_query

        retrieval = a3.retrieve(resolved_query)
        chunks = retrieval["chunks"]

        # ดึงเนื้อหาตัวบทจริง (official_raw_text) เฉพาะ Chunks ที่เกี่ยวข้องกับการตอบ (ไม่เกิน 3-4 chunks)
        top_chunk_ids = [c["chunk_id"] for c in chunks[:3] if "chunk_id" in c]
        rel_db_articles = {a.id: a for a in db.query(KbArticle).filter(KbArticle.id.in_(top_chunk_ids)).all()}
        relevant_articles = []
        for c in chunks[:3]:
            cid = c.get("chunk_id", "")
            if cid in rel_db_articles:
                art = rel_db_articles[cid]
                relevant_articles.append({
                    "id": art.id,
                    "section": art.source_section,
                    "title": art.title,
                    "content": art.content,
                })
            else:
                relevant_articles.append({
                    "id": cid,
                    "section": c.get("source_section", ""),
                    "title": c.get("title", c.get("source_section", "")),
                    "content": c.get("text", ""),
                })

        ret_log = RetrievalLog(
            id=gen_uuid(),
            query_id=query.id,
            rewritten_query=resolved_query,
            rewrite_temperature=0.00,
            retrieved_chunks=chunks,
            relevance_scores=retrieval["relevance_scores"],
        )
        db.add(ret_log)
        query.status = "retrieved"
        db.commit()

        # 5. ประเมินความเสี่ยงล่วงหน้า (rule-based): Agent 5 ให้คะแนนได้ไม่เกิน a5.MAX_CONFIDENCE
        # ถ้าที่คะแนนสูงสุดนั้นยังไม่ใช่ auto_answer เคสนี้ต้องส่งเจ้าหน้าที่แน่นอน — ไม่ต้องรอ LLM ร่างคำตอบ
        # (บน CPU ใช้ราว 2 นาที) ผู้ถามได้ผลทันที และหัวหน้างานได้สรุปเคสพร้อมตัวบทและร่างคร่าวๆ แทน
        pre_risk = a6.assess_risk(effective_text, a5.MAX_CONFIDENCE)
        if pre_risk["tier"] != "auto_answer":
            channel = detect_channel(effective_text)
            art6_ids = {"paper": ["VAT57_ART_06"], "internet": ["VAT159_ART_06"]}.get(
                channel, ["VAT57_ART_06", "VAT159_ART_06"])
            art6 = [{"chunk_id": a.id, "text": a.content, "citation": a3.legal_citation(a.id, a.source_section)}
                    for a in db.query(KbArticle).filter(KbArticle.id.in_(art6_ids)).order_by(KbArticle.id.desc()).all()]
            draft = a6.build_review_brief(resolved_query, chunks, pre_risk, art6)
            verification = {"confidence_score": a5.MAX_CONFIDENCE, "ungrounded_claims": []}
            risk = pre_risk
        else:
            # 5.1 Agent 4: Responder
            try:
                draft = a4.respond(resolved_query, chunks)
            except Exception:
                # Fallback สรุปจากตัวบทกฎหมายโดยตรงกรณี Ollama บน Local CPU ประมวลผลล่าช้า
                summary_from_chunks, fb_citations = a4.summarize_chunks(chunks, n=2)
                draft = {
                    "draft_text": f"สรุปสาระสำคัญและหลักเกณฑ์การยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มตามตัวบทกฎหมาย:\n\n{summary_from_chunks}\n\n• **การดำเนินการ:** ให้ผู้ประกอบการจัดเตรียมคำขอและเอกสารหลักฐานให้ถูกต้องครบถ้วนตามหลักเกณฑ์ที่ระบุข้างต้น",
                    "citations": fb_citations,
                    "answer_summary": "สรุปสาระสำคัญจากตัวบทกฎหมายที่เกี่ยวข้อง",
                }

            # 6. Agent 5: Verifier (Regex + Grounding check)
            verification = a5.verify_regex(draft["draft_text"], chunks)

            # 7. Agent 6: Risk & Tier Decision (Rule-based)
            risk = a6.assess_risk(effective_text, verification["confidence_score"])

            # ถ้าเข้าข่าย senior_review และยังไม่มี risk_factors เชิงโครงสร้างจาก rule-based ให้เรียก Deep LLM Verification เพิ่มเติม
            if risk["tier"] == "senior_review" and not risk.get("risk_factors"):
                try:
                    deep = a5.verify_deep_llm(draft["draft_text"], chunks)
                    verification["confidence_score"] = min(verification["confidence_score"], deep["confidence_score"])
                    risk = a6.assess_risk(effective_text, verification["confidence_score"])
                except Exception:
                    pass

        draft_ans = DraftAnswer(
            id=gen_uuid(),
            query_id=query.id,
            draft_text=draft["draft_text"],
            citations=draft["citations"],
        )
        db.add(draft_ans)
        query.answer_summary = draft["answer_summary"]
        query.status = "drafted"
        db.commit()

        ver_score = VerificationScore(
            id=gen_uuid(),
            draft_answer_id=draft_ans.id,
            confidence_score=verification["confidence_score"],
            ungrounded_claims=verification["ungrounded_claims"],
        )
        db.add(ver_score)

        risk_rec = RiskAssessment(
            id=gen_uuid(),
            query_id=query.id,
            risk_score=risk["risk_score"],
            risk_factors=risk["risk_factors"],
            trust_score=risk["trust_score"],
            tier=risk["tier"],
        )
        db.add(risk_rec)
        query.status = "tier_assigned"
        db.commit()

        # 8. Decision Branching: Auto Answer vs Supervisor Review
        if risk["tier"] == "auto_answer":
            query.status = "answered"
            audit = AuditLog(
                id=gen_uuid(),
                query_id=query.id,
                event_type="auto_answered",
                event_data={
                    "trust_score": risk["trust_score"],
                    "confidence_score": verification["confidence_score"],
                },
                actor_type="staff",
                actor_id=user_id,
            )
            db.add(audit)
            db.commit()

            return {
                "query_id": query.id,
                "conversation_id": conv.id,
                "turn_number": turn_number,
                "resolved_query": resolved_query,
                "type": "answer",
                "payload": {
                    "draft_text": draft["draft_text"],
                    "citations": draft["citations"],
                    "relevant_articles": relevant_articles,
                    "confidence_score": verification["confidence_score"],
                    "trust_score": risk["trust_score"],
                    "tier": "auto_answer",
                    "resolved_query": resolved_query,
                    "answer_summary": draft["answer_summary"],
                    "offer_checklist": cl.is_document_question(effective_text),
                },
            }

        else:
            # เข้าสู่ Escalation Queue สำหรับ Officer / Senior Officer
            query.status = "pending_review"
            esc = Escalation(
                id=gen_uuid(),
                query_id=query.id,
                tier=risk["tier"],
                decision=None,
            )
            db.add(esc)

            audit = AuditLog(
                id=gen_uuid(),
                query_id=query.id,
                event_type="escalated_for_review",
                event_data={
                    "escalation_id": esc.id,
                    "tier": risk["tier"],
                    "risk_factors": risk["risk_factors"],
                    "trust_score": risk["trust_score"],
                },
                actor_type="staff",
                actor_id=user_id,
            )
            db.add(audit)
            db.commit()

            # ข้อกำหนดสำคัญ: กรณีที่เป็นเคสเสี่ยง ให้แจ้งแค่ว่าเป็นเคสเสี่ยง (ส่งเข้าคิวหัวหน้างานแล้ว)
            # แต่ไม่ต้องแสดงข้อความคำตอบ (draft_text) และไม่ต้องแสดงข้อกฎหมายด้านขวา (relevant_articles)
            return {
                "query_id": query.id,
                "conversation_id": conv.id,
                "turn_number": turn_number,
                "resolved_query": resolved_query,
                "type": "pending_review",
                "payload": {
                    "escalation_id": esc.id,
                    "tier": risk["tier"],
                    "draft_text": "",  # ไม่แสดงข้อความคำตอบร่างสำหรับเคสเสี่ยง
                    "citations": [],   # ไม่แสดงตัวบทอ้างอิง
                    "relevant_articles": [],  # ไม่แสดงข้อกฎหมายด้านขวา
                    "risk_factors": risk["risk_factors"],
                    "trust_score": risk["trust_score"],
                    "estimated_wait_message": (
                        f"คำถามนี้มีความเสี่ยงหรือประเด็นที่ต้องตรวจสอบ ({', '.join(risk['risk_factors'])}) "
                        f"ระบบได้ส่งเข้าคิวตรวจสอบของหัวหน้างาน ({risk['tier']}) กรุณารอการอนุมัติ"
                    ),
                },
            }

    finally:
        if close_db:
            db.close()
