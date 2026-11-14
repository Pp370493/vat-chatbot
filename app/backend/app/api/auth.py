"""
API 5.0 Authentication & RBAC — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md
รองรับ 3 บทบาท: officer, senior_officer, admin
พร้อมบันทึกลง audit_log (ISO/IEC 27001)
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import StaffUser, AuthSession, AuditLog, gen_uuid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RoleSwitchRequest(BaseModel):
    role: str  # officer | senior_officer | admin


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    ตรวจสอบรหัสผ่านและสร้าง session
    """
    user = db.query(StaffUser).filter(StaffUser.email == req.email.strip()).first()
    if not user:
        # Fallback query by role name if someone typed role as email
        user = db.query(StaffUser).filter(StaffUser.role == req.email.strip()).first()

    if not user or user.password_hash != req.password.strip():
        raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

    session_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=8)

    session = AuthSession(
        id=gen_uuid(),
        staff_user_id=user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    db.add(session)
    user.last_login_at = datetime.utcnow()

    # Immutable Audit Log
    audit = AuditLog(
        id=gen_uuid(),
        event_type="user_login",
        event_data={
            "user_id": user.id,
            "role": user.role,
            "full_name": user.full_name,
            "login_time": datetime.utcnow().isoformat(),
        },
        actor_type="staff",
        actor_id=user.id,
    )
    db.add(audit)
    db.commit()

    return {
        "session_token": session_token,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/quick-switch")
def quick_switch_role(req: RoleSwitchRequest, db: Session = Depends(get_db)):
    """
    Quick Role Switcher สำหรับ Demo IS (สลับ role ระหว่าง officer, senior_officer, admin ทันที)
    """
    role = req.role.strip()
    if role not in ["officer", "senior_officer", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    user = db.query(StaffUser).filter(StaffUser.role == role).first()
    if not user:
        raise HTTPException(status_code=404, detail="User with requested role not found")

    session_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=8)

    session = AuthSession(
        id=gen_uuid(),
        staff_user_id=user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    db.add(session)
    user.last_login_at = datetime.utcnow()

    # Immutable Audit Log
    audit = AuditLog(
        id=gen_uuid(),
        event_type="role_switch_demo",
        event_data={
            "user_id": user.id,
            "switched_role": user.role,
            "full_name": user.full_name,
        },
        actor_type="staff",
        actor_id=user.id,
    )
    db.add(audit)
    db.commit()

    return {
        "session_token": session_token,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "expires_at": expires_at.isoformat(),
    }


@router.get("/users")
def list_available_users(db: Session = Depends(get_db)):
    """
    ดึงรายชื่อผู้ใช้ตัวอย่าง 3 สิทธิ์สำหรับแสดงบนหน้า Quick Role Switcher
    """
    users = db.query(StaffUser).filter(StaffUser.is_active == True).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
        }
        for u in users
    ]
