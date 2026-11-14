"""
DB session — ใช้ SQLite ตอน dev ตาม DATABASE_URL ใน .env
(ย้ายขึ้น PostgreSQL ตอน production แค่เปลี่ยน DATABASE_URL เพราะ schema ใช้
 uuid.uuid4() app-layer ไว้แล้ว ตาม Hardware Optimization Guide 14.3)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
