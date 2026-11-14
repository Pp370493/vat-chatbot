"""
API 5.3 Admin Dashboard Analytics — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md
คำนวณและสรุปสถิติจริงจากฐานข้อมูล SQLite (queries, escalations, out_of_scope_routes)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.models import Query, Escalation, OutOfScopeRoute, RiskAssessment

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview")
def overview(range: str = "7d", db: Session = Depends(get_db)):
    """
    ภาพรวมสถิติการใช้งานระบบ
    """
    total = db.query(Query).count()
    if total == 0:
        return {
            "total_queries": 0,
            "in_scope_ratio": 1.0,
            "out_of_scope_breakdown": [],
            "escalation_rate": 0.0,
            "auto_answer_rate": 0.0,
            "top_repeated_questions": [],
        }

    in_scope_count = db.query(Query).filter(Query.in_scope == True).count()
    escalation_count = db.query(Escalation).count()
    auto_count = db.query(Query).filter(Query.status == "answered").count() - db.query(Escalation).filter(Escalation.decision.isnot(None)).count()
    auto_count = max(0, auto_count)

    # Out of scope breakdown
    oos_rows = (
        db.query(OutOfScopeRoute.matched_topic, func.count(OutOfScopeRoute.id))
        .group_by(OutOfScopeRoute.matched_topic)
        .all()
    )
    oos_breakdown = [{"topic": r[0], "count": r[1]} for r in oos_rows]

    # Top repeated questions
    top_queries = (
        db.query(Query.raw_text, func.count(Query.id))
        .group_by(Query.raw_text)
        .order_by(func.count(Query.id).desc())
        .limit(5)
        .all()
    )
    top_repeated = [{"text": r[0], "count": r[1]} for r in top_queries]

    return {
        "total_queries": total,
        "in_scope_ratio": round(in_scope_count / total, 3),
        "out_of_scope_breakdown": oos_breakdown,
        "escalation_rate": round(escalation_count / total, 3),
        "auto_answer_rate": round(auto_count / total, 3),
        "top_repeated_questions": top_repeated,
    }


@router.get("/heatmap")
def heatmap(db: Session = Depends(get_db)):
    """
    หัวข้อที่ถูกส่งเข้าคิว Escalation บ่อยที่สุด
    """
    rows = (
        db.query(RiskAssessment.tier, func.count(RiskAssessment.id))
        .group_by(RiskAssessment.tier)
        .all()
    )
    return [{"topic": r[0], "escalation_count": r[1]} for r in rows]


@router.get("/audit-logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    ดึงบันทึก Audit Logs ที่แก้ไขไม่ได้ (Immutable Log Viewer) สำหรับ Admin ตรวจสอบตาม ISO/IEC 27001
    """
    from app.models.models import AuditLog, StaffUser
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    results = []
    for log in logs:
        staff = db.query(StaffUser).filter(StaffUser.id == log.actor_id).first() if log.actor_id else None
        results.append({
            "id": log.id,
            "query_id": log.query_id,
            "event_type": log.event_type,
            "event_data": log.event_data,
            "actor_type": log.actor_type,
            "actor_id": log.actor_id,
            "actor_name": staff.full_name if staff else "System",
            "actor_role": staff.role if staff else "system",
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return results
