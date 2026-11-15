"""
การยืนยันตัวตนและสิทธิ์ (ISO/IEC 27001 A.9)
- รหัสผ่าน: PBKDF2-SHA256 + salt สุ่ม (stdlib ไม่ต้องติดตั้งเพิ่ม)
- session: token สุ่มใน auth_sessions พร้อมวันหมดอายุ ส่งมาทาง header `Authorization: Bearer <token>`
- สิทธิ์: require_roles("senior_officer", "admin") ฯลฯ — ผู้ใช้และบทบาทมาจาก token เสมอ ไม่เชื่อค่าที่ client ส่งมา
"""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import AuthSession, StaffUser

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000
UNUSABLE_PASSWORD = "!"  # บัญชีระบบ: ไม่มีรหัสใดตรวจผ่าน


def hash_password(password: str, iterations: int = _ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_ALGO}${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = (stored or "").split("$")
        if algo != _ALGO:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False  # รูปแบบไม่ถูกต้อง (รวมรหัสแบบ plaintext เดิม) = ไม่ผ่าน


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def get_current_session(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthSession:
    token = _bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    sess = db.query(AuthSession).filter(AuthSession.session_token == token).first()
    if not sess or sess.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="session หมดอายุ กรุณาเข้าสู่ระบบใหม่")
    return sess


def get_current_user(
    sess: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> StaffUser:
    user = db.query(StaffUser).filter(StaffUser.id == sess.staff_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="บัญชีนี้ถูกระงับ")
    return user


def require_roles(*roles: str):
    def checker(user: StaffUser = Depends(get_current_user)) -> StaffUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์เข้าถึง")
        return user
    return checker
