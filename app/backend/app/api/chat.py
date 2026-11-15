"""
API 5.1 Chat Flow — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md
เชื่อมต่อ Database Persistence จริงตาม State Flow
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.session import get_db
from app.graph.pipeline_graph import run_pipeline
from app.models.models import (
    Query, DraftAnswer, Escalation, DocumentChecklistItem, FormAssistanceSession,
    KbArticle, Conversation, StaffUser, gen_uuid
)
from app.agents import agent7_checklist_assistant as a7

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    session_id: str
    conversation_id: str | None = None
    text: str


def _owns_query(db: Session, user: StaffUser, query_rec: Query) -> bool:
    """เจ้าหน้าที่เห็นเฉพาะคำถามของตนเอง หัวหน้างานและผู้ดูแลระบบเห็นทั้งหมด"""
    if user.role in ("senior_officer", "admin"):
        return True
    conv = db.query(Conversation).filter(Conversation.id == query_rec.conversation_id).first()
    return bool(conv and conv.staff_user_id == user.id)


@router.post("/query")
def chat_query(req: QueryRequest, user: StaffUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    รับคำถามและส่งต่อเข้าสู่ Multi-Agent Pipeline
    บันทึกทุกขั้นตอนลง SQLite ครบถ้วน
    """
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if conv and conv.staff_user_id != user.id:
            raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ในบทสนทนานี้")
    result = run_pipeline(
        raw_text=req.text,
        session_id=req.session_id,
        conversation_id=req.conversation_id,
        staff_user_id=user.id,
        db=db,
    )
    return result


@router.get("/query/{query_id}/status")
def get_query_status(query_id: str, user: StaffUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    ตรวจสอบสถานะคำถาม (สำหรับเคสที่รอ Supervisor Review)
    """
    query_rec = db.query(Query).filter(Query.id == query_id).first()
    if not query_rec or not _owns_query(db, user, query_rec):
        raise HTTPException(status_code=404, detail="Query not found")

    draft_rec = db.query(DraftAnswer).filter(DraftAnswer.query_id == query_id).first()
    esc_rec = db.query(Escalation).filter(Escalation.query_id == query_id).first()

    final_answer = None
    if esc_rec and esc_rec.final_answer:
        final_answer = esc_rec.final_answer
    elif query_rec.status == "answered" and draft_rec:
        final_answer = draft_rec.draft_text

    return {
        "query_id": query_id,
        "status": query_rec.status,
        "answer": final_answer,
        "draft_text": draft_rec.draft_text if draft_rec else None,
        "citations": draft_rec.citations if draft_rec else [],
        "escalation_decision": esc_rec.decision if esc_rec else None,
    }


@router.get("/inquiries/recent")
def get_recent_inquiries(limit: int = 5, user: StaffUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    ประวัติข้อหารือล่าสุดของผู้ใช้ที่เข้าสู่ระบบอยู่ (แสดงบน Sidebar ด้านซ้าย)
    """
    limit = max(1, min(limit, 50))
    user_conv_ids = [c.id for c in db.query(Conversation).filter(Conversation.staff_user_id == user.id).all()]
    if not user_conv_ids:
        return []
    q_filter = db.query(Query).filter(Query.conversation_id.in_(user_conv_ids))

    recent_queries = (
        q_filter.order_by(Query.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for q in recent_queries:
        draft = db.query(DraftAnswer).filter(DraftAnswer.query_id == q.id).first()
        esc = db.query(Escalation).filter(Escalation.query_id == q.id).first()
        ans = esc.final_answer if (esc and esc.final_answer) else (draft.draft_text if draft else "")
        results.append({
            "query_id": q.id,
            "conversation_id": q.conversation_id,
            "raw_text": q.raw_text,
            "answer": ans or "",
            "status": q.status,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        })
    return results


class GenerateChecklistRequest(BaseModel):
    channel: str = "paper"  # paper | internet
    taxpayer_type: str = "individual_thai"
    location_type: str = "rented"
    is_power_of_attorney: bool = False


@router.post("/form-session/generate-checklist")
def generate_checklist_endpoint(req: GenerateChecklistRequest, _: StaffUser = Depends(get_current_user)):
    """
    สร้าง Checklist รายการเอกสารตามหลักเกณฑ์ข้อ 5 ของประกาศอธิบดีฯ ฉบับที่ 57 หรือ 159
    โดยตรวจสอบคุณลักษณะของผู้ยื่นขอจดทะเบียนก่อน
    """
    profile = {
        "channel": req.channel,
        "taxpayer_type": req.taxpayer_type,
        "location_type": req.location_type,
        "is_power_of_attorney": req.is_power_of_attorney,
    }
    return a7.generate_checklist(profile)


class EvaluateChecklistRequest(BaseModel):
    profile: dict
    items: list[dict]
    session_id: str | None = None
    query_id: str | None = None


@router.post("/form-session/evaluate-checklist")
def evaluate_checklist_endpoint(
    req: EvaluateChecklistRequest, user: StaffUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    ประเมินผลการตรวจรับเอกสารของเจ้าหน้าที่ (Human-Controlled Verification)
    AI สรุปผลว่ายื่นครบถ้วนหรือขาดเอกสารอะไรบ้างตามข้อ 5 และแจ้งเตือนผลตามข้อ 6
    """
    eval_result = a7.evaluate_checklist(req.items, req.profile)

    # บันทึกประวัติการตรวจรับเอกสารลง DB
    try:
        session_id = req.session_id or gen_uuid()
        form_session = db.query(FormAssistanceSession).filter(FormAssistanceSession.id == session_id).first()
        if not form_session:
            # ผูกกับคำถามที่ระบุ (ต้องเป็นของผู้ใช้เอง) หรือคำถามล่าสุดของผู้ใช้คนนี้ — ไม่ผูกกับของคนอื่น
            linked_q = db.query(Query).filter(Query.id == req.query_id).first() if req.query_id else None
            if linked_q and not _owns_query(db, user, linked_q):
                linked_q = None
            if not linked_q:
                conv_ids = [c.id for c in db.query(Conversation).filter(Conversation.staff_user_id == user.id).all()]
                linked_q = (db.query(Query).filter(Query.conversation_id.in_(conv_ids))
                            .order_by(Query.created_at.desc()).first()) if conv_ids else None
            if not linked_q:
                return eval_result  # ยังไม่มีคำถามของผู้ใช้ให้ผูก — คืนผลประเมินโดยไม่บันทึก
            form_session = FormAssistanceSession(
                id=session_id,
                query_id=linked_q.id,
                conversation_log=[{"profile": req.profile, "evaluation": eval_result}],
                is_complete=eval_result["is_complete"],
            )
            db.add(form_session)
        else:
            form_session.is_complete = eval_result["is_complete"]

        for item in req.items:
            doc_item = DocumentChecklistItem(
                id=gen_uuid(),
                form_assistance_session_id=session_id,
                document_name=item.get("title", ""),
                status=item.get("status", "pending"),
                marked_by=user.id,
            )
            db.add(doc_item)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Checklist DB save skipped: %s", e)

    return eval_result


class ChecklistItemRequest(BaseModel):
    document_name: str
    status: str  # received | missing | not_applicable


@router.post("/form-session/{session_id}/checklist-item")
def mark_checklist_item(
    session_id: str, req: ChecklistItemRequest, user: StaffUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    เจ้าหน้าที่ทำเครื่องหมายสถานะเอกสารใน Checklist เอง (Human-controlled)
    """
    form_session = db.query(FormAssistanceSession).filter(FormAssistanceSession.id == session_id).first()
    linked_q = db.query(Query).filter(Query.id == form_session.query_id).first() if form_session else None
    if not linked_q or not _owns_query(db, user, linked_q):
        raise HTTPException(status_code=404, detail="ไม่พบ checklist session")
    if req.status not in ("received", "missing", "not_applicable"):
        raise HTTPException(status_code=400, detail="status ต้องเป็น received, missing หรือ not_applicable")
    item = DocumentChecklistItem(
        id=gen_uuid(),
        form_assistance_session_id=session_id,
        document_name=req.document_name,
        status=req.status,
        marked_by=user.id,
    )
    db.add(item)
    db.commit()
    return {"checklist_item_id": item.id, "status": req.status}


@router.get("/articles")
def list_articles(_: StaffUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    ดึงรายการตัวบทกฎหมายทั้งหมด (75 Chunks / 10 ประกาศอธิบดีฯ) สำหรับแสดงใน Citation Viewer
    """
    articles = db.query(KbArticle).filter(KbArticle.status == "approved").all()
    return [
        {
            "id": a.id,
            "section": a.source_section,
            "title": a.title,
            "content": a.content,
        }
        for a in articles
    ]
