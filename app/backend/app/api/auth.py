"""
API 5.0 Authentication & RBAC — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md
รองรับ 3 บทบาท: officer, senior_officer, admin พร้อมบันทึกลง audit_log (ISO/IEC 27001)
รหัสผ่านเก็บเป็น PBKDF2 hash และทุก endpoint อื่นตรวจ session token (app/core/security.py)
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    get_current_session, get_current_user, new_session_token, require_roles, verify_password,
)
from app.db.session import get_db
from app.models.models import AuditLog, AuthSession, StaffUser, gen_uuid

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RoleSwitchRequest(BaseModel):
    role: str  # officer | senior_officer | admin


def _profile(user: StaffUser, sess: AuthSession) -> dict:
    return {
        "session_token": sess.session_token,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "expires_at": sess.expires_at.isoformat(),
    }


def _open_session(db: Session, user: StaffUser, event_type: str, event_data: dict) -> AuthSession:
    sess = AuthSession(
        id=gen_uuid(),
        staff_user_id=user.id,
        session_token=new_session_token(),
        expires_at=datetime.utcnow() + timedelta(hours=settings.auth_session_expiry_hours),
    )
    db.add(sess)
    user.last_login_at = datetime.utcnow()
    db.add(AuditLog(id=gen_uuid(), event_type=event_type, event_data=event_data, actor_type="staff", actor_id=user.id))
    db.commit()
    return sess


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """ตรวจอีเมลและรหัสผ่าน แล้วสร้าง session"""
    user = db.query(StaffUser).filter(StaffUser.email == req.email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    sess = _open_session(db, user, "user_login", {
        "user_id": user.id, "role": user.role, "full_name": user.full_name,
        "login_time": datetime.utcnow().isoformat(),
    })
    return _profile(user, sess)


@router.post("/logout")
def logout(sess: AuthSession = Depends(get_current_session), db: Session = Depends(get_db)):
    db.add(AuditLog(id=gen_uuid(), event_type="user_logout", event_data={"user_id": sess.staff_user_id},
                    actor_type="staff", actor_id=sess.staff_user_id))
    db.delete(sess)
    db.commit()
    return {"status": "logged_out"}


@router.get("/me")
def me(user: StaffUser = Depends(get_current_user)):
    return {"user_id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role}


@router.post("/quick-switch")
def quick_switch_role(
    req: RoleSwitchRequest,
    current: StaffUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    สลับบทบาทสำหรับการสาธิตเท่านั้น — เปิดได้ด้วย ENABLE_DEMO_ROLE_SWITCH=true และต้องเข้าสู่ระบบอยู่แล้ว
    """
    if not settings.enable_demo_role_switch:
        raise HTTPException(status_code=404, detail="Not Found")
    role = req.role.strip()
    if role not in ["officer", "senior_officer", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")
    user = db.query(StaffUser).filter(StaffUser.role == role, StaffUser.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=404, detail="User with requested role not found")
    sess = _open_session(db, user, "role_switch_demo", {
        "user_id": user.id, "switched_role": user.role, "switched_by": current.id,
    })
    return _profile(user, sess)


@router.get("/users")
def list_available_users(_: StaffUser = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    """รายชื่อผู้ใช้ (เฉพาะผู้ดูแลระบบ)"""
    users = db.query(StaffUser).filter(StaffUser.is_active == True).all()  # noqa: E712
    return [{"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role} for u in users]
