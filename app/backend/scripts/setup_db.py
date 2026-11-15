"""
เตรียมฐานข้อมูลสำหรับใช้งาน/ทดสอบ (ทำซ้ำได้ ไม่สร้างข้อมูลซ้ำ)

    python scripts/setup_db.py --ingest
    python scripts/setup_db.py --password-officer XXX --password-senior YYY --password-admin ZZZ

1. สร้างตารางทั้งหมด
2. --ingest: นำตัวบท 75 chunks เข้า พร้อม embedding (ต้องเปิด Ollama)
3. สร้าง/อัปเดตผู้ใช้ 3 บทบาท — ไม่ระบุรหัส = สุ่มให้และพิมพ์ออกจอครั้งเดียว (ผู้ใช้ที่มีอยู่แล้วไม่ถูกเปลี่ยนรหัส
   เว้นแต่ระบุรหัสใหม่หรือ --reset-passwords)
4. สร้างตาราง departments จากหัวข้อนอกสโคปของ Agent 2 (ให้ผู้ดูแลแก้ช่องทางติดต่อได้ภายหลัง)
ใช้ DATABASE_URL จาก .env หรือ --db เพื่อระบุไฟล์ SQLite
"""
import argparse
import os
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

p = argparse.ArgumentParser()
p.add_argument("--db", help="ไฟล์ SQLite (แทน DATABASE_URL)")
p.add_argument("--ingest", action="store_true", help="นำตัวบทเข้าพร้อม embedding")
p.add_argument("--password-officer")
p.add_argument("--password-senior")
p.add_argument("--password-admin")
p.add_argument("--reset-passwords", action="store_true", help="สุ่มรหัสใหม่ให้ผู้ใช้ที่มีอยู่แล้วด้วย")
args = p.parse_args()
if args.db:
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(args.db).resolve()}"
sys.path.insert(0, str(BASE_DIR))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.agent2_out_of_scope_router import BUILTIN_OUT_OF_SCOPE_TOPICS  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import models  # noqa: E402,F401
from app.models.models import Department, StaffUser, gen_uuid  # noqa: E402

USERS = [
    ("officer", "officer@rd.go.th", "นายสมชาย หน้างาน (Officer)", args.password_officer),
    ("senior_officer", "supervisor@rd.go.th", "นางสาวสมศรี หัวหน้างาน (Supervisor)", args.password_senior),
    ("admin", "admin@rd.go.th", "ผู้ดูแลระบบ (Admin)", args.password_admin),
]


def main():
    print(f"database: {settings.database_url}")
    Base.metadata.create_all(bind=engine)
    if args.ingest:
        from app.core.kb_ingest import check_ollama, ingest_articles
        problem = check_ollama(settings.ollama_base_url_fallback, settings.embedding_model or "nomic-embed-text")
        if problem:
            print(problem)
            sys.exit(1)
        ingest_articles()

    db = SessionLocal()
    try:
        printed = []
        for role, email, name, password in USERS:
            user = db.query(StaffUser).filter(StaffUser.email == email).first()
            if user and not password and not args.reset_passwords:
                print(f"user {email}: มีอยู่แล้ว (ไม่เปลี่ยนรหัส)")
                continue
            pw = password or secrets.token_urlsafe(9)
            if not user:
                user = StaffUser(id=gen_uuid(), email=email, full_name=name, role=role)
                db.add(user)
            user.password_hash = hash_password(pw)
            user.role, user.is_active = role, True
            if not password:
                printed.append((email, role, pw))
            print(f"user {email}: ตั้งรหัสแล้ว")

        added = 0
        for topic in BUILTIN_OUT_OF_SCOPE_TOPICS:
            if not db.query(Department).filter(Department.name == topic["name"]).first():
                db.add(Department(id=gen_uuid(), name=topic["name"], topic_keywords=topic["keywords"],
                                  contact_channel=topic["contact"]))
                added += 1
        db.commit()
        print(f"departments: เพิ่ม {added} (ทั้งหมด {db.query(Department).count()})")

        if printed:
            print("\nรหัสผ่านที่สุ่มให้ (แสดงครั้งเดียว — เก็บไว้ให้ดี):")
            for email, role, pw in printed:
                print(f"  {role:15} {email:22} {pw}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
