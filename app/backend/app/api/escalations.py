"""
API 5.2 Supervisor Dashboard — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md
ระบบจัดการคิว Escalation สำหรับเจ้าหน้าที่รุ่นพี่ (Senior Officer / Supervisor)
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import require_roles
from app.db.session import get_db
from app.models.models import (
    Escalation, Query, DraftAnswer, RiskAssessment, VerificationScore, AuditLog, StaffUser, gen_uuid,
)

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])
reviewer = require_roles("senior_officer", "admin")


@router.get("")
def list_escalations(
    tier: str | None = None,
    status: str = "pending",
    _: StaffUser = Depends(reviewer),
    db: Session = Depends(get_db)
):
    """
    ดึงรายการเคสที่ต้องให้หัวหน้างาน/เจ้าหน้าที่รุ่นพี่ตรวจสอบ
    status: 'pending' (ยังไม่ได้ตัดสินใจ) หรือ 'all'
    tier: 'officer_review' หรือ 'senior_review'
    """
    q = db.query(Escalation)
    if tier:
        q = q.filter(Escalation.tier == tier)
    if status == "pending":
        q = q.filter(Escalation.decision.is_(None))
    elif status == "reviewed":
        q = q.filter(Escalation.decision.isnot(None))

    escalations = q.order_by(Escalation.created_at.desc()).all()
    result = []
    for esc in escalations:
        query_rec = db.query(Query).filter(Query.id == esc.query_id).first()
        draft_rec = db.query(DraftAnswer).filter(DraftAnswer.query_id == esc.query_id).first()
        risk_rec = db.query(RiskAssessment).filter(RiskAssessment.query_id == esc.query_id).first()
        ver_rec = None
        if draft_rec:
            ver_rec = db.query(VerificationScore).filter(VerificationScore.draft_answer_id == draft_rec.id).first()

        result.append({
            "escalation_id": esc.id,
            "query_id": esc.query_id,
            "tier": esc.tier,
            "decision": esc.decision,
            "final_answer": esc.final_answer,
            "raw_text": query_rec.raw_text if query_rec else "",
            "resolved_query": query_rec.resolved_query if query_rec else "",
            "draft_text": draft_rec.draft_text if draft_rec else "",
            "citations": draft_rec.citations if draft_rec else [],
            "confidence_score": float(ver_rec.confidence_score) if ver_rec else 0.0,
            "risk_factors": risk_rec.risk_factors if risk_rec else [],
            "trust_score": float(risk_rec.trust_score) if risk_rec else 0.0,
            "created_at": esc.created_at.isoformat() if esc.created_at else None,
        })
    return result


class DecisionRequest(BaseModel):
    decision: str  # approved | edited | rejected
    final_answer: str


@router.post("/{escalation_id}/decision")
def submit_decision(
    escalation_id: str,
    req: DecisionRequest,
    user: StaffUser = Depends(reviewer),
    db: Session = Depends(get_db)
):
    """
    หัวหน้างานอนุมัติ/แก้ไข/ปฏิเสธคำตอบในคิว Escalation
    """
    esc = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if req.decision not in ("approved", "edited", "rejected"):
        raise HTTPException(status_code=400, detail="decision ต้องเป็น approved, edited หรือ rejected")

    esc.decision = req.decision
    esc.final_answer = req.final_answer
    esc.reviewed_by = user.id
    esc.reviewed_at = datetime.utcnow()

    # อัปเดตสถานะ Query ให้เป็น answered
    query_rec = db.query(Query).filter(Query.id == esc.query_id).first()
    if query_rec:
        query_rec.status = "answered"

    # บันทึก Audit Log
    audit = AuditLog(
        id=gen_uuid(),
        query_id=esc.query_id,
        event_type="escalation_reviewed",
        event_data={
            "escalation_id": escalation_id,
            "decision": req.decision,
            "final_answer": req.final_answer,
            "reviewed_by": user.id,
        },
        actor_type="staff",
        actor_id=user.id,
    )
    db.add(audit)
    db.commit()

    return {
        "status": "answered",
        "escalation_id": escalation_id,
        "decision": req.decision,
        "message": f"เคสนี้ได้รับการบันทึกผลการตรวจสอบ ({req.decision}) เรียบร้อยแล้ว"
    }
