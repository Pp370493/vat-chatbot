"""
API 5.3 Admin Dashboard Analytics — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md
คำนวณและสรุปสถิติจริงจากฐานข้อมูล SQLite (queries, escalations, out_of_scope_routes)
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.security import require_roles
from app.db.session import get_db
from app.models.models import Query, Escalation, OutOfScopeRoute, RiskAssessment, StaffUser

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
admin_only = require_roles("admin")
RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "all": None}


def _since(range_: str) -> datetime | None:
    if range_ not in RANGE_DAYS:
        raise HTTPException(status_code=400, detail="range ต้องเป็น 7d, 30d, 90d หรือ all")
    days = RANGE_DAYS[range_]
    return datetime.utcnow() - timedelta(days=days) if days else None


@router.get("/overview")
def overview(range: str = "7d", _: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    """
    ภาพรวมสถิติการใช้งานระบบในช่วงเวลาที่เลือก (7d / 30d / 90d / all)
    """
    since = _since(range)
    queries = db.query(Query)
    if since:
        queries = queries.filter(Query.created_at >= since)
    total = queries.count()
    if total == 0:
        return {
            "range": range,
            "total_queries": 0,
            "in_scope_ratio": 1.0,
            "out_of_scope_breakdown": [],
            "escalation_rate": 0.0,
            "auto_answer_rate": 0.0,
            "top_repeated_questions": [],
        }

    query_ids = queries.with_entities(Query.id).subquery()
    in_scope_count = queries.filter(Query.in_scope == True).count()  # noqa: E712
    escalation_count = db.query(Escalation).filter(Escalation.query_id.in_(query_ids)).count()
    reviewed_count = (db.query(Escalation)
                      .filter(Escalation.query_id.in_(query_ids), Escalation.decision.isnot(None)).count())
    auto_count = max(0, queries.filter(Query.status == "answered").count() - reviewed_count)

    oos_rows = (
        db.query(OutOfScopeRoute.matched_topic, func.count(OutOfScopeRoute.id))
        .filter(OutOfScopeRoute.query_id.in_(query_ids))
        .group_by(OutOfScopeRoute.matched_topic)
        .all()
    )
    top_queries = (
        queries.with_entities(Query.raw_text, func.count(Query.id))
        .group_by(Query.raw_text)
        .order_by(func.count(Query.id).desc())
        .limit(5)
        .all()
    )

    return {
        "range": range,
        "total_queries": total,
        "in_scope_ratio": round(in_scope_count / total, 3),
        "out_of_scope_breakdown": [{"topic": r[0], "count": r[1]} for r in oos_rows],
        "escalation_rate": round(escalation_count / total, 3),
        "auto_answer_rate": round(auto_count / total, 3),
        "top_repeated_questions": [{"text": r[0], "count": r[1]} for r in top_queries],
    }


@router.get("/heatmap")
def heatmap(_: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
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
def get_audit_logs(limit: int = 50, _: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    """
    ดึงบันทึก Audit Logs ที่แก้ไขไม่ได้ (Immutable Log Viewer) สำหรับ Admin ตรวจสอบตาม ISO/IEC 27001
    """
    from app.models.models import AuditLog
    limit = max(1, min(limit, 500))
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
