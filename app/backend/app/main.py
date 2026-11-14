"""
FastAPI entrypoint — อ้างอิง VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 5, 7

รัน: uvicorn app.main:app --reload
เช็ค: http://localhost:8000/health และ http://localhost:8000/docs
"""
from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
from app.models import models  # noqa: F401  (import เพื่อให้ Base รู้จักทุก table)
from app.api import auth, chat, escalations, analytics

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Enterprise Tax Co-Pilot & Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(escalations.router)
app.include_router(analytics.router)


@app.on_event("startup")
def on_startup():
    # Dev convenience: สร้างตารางอัตโนมัติบน SQLite ถ้ายังไม่มี
    # Production (PostgreSQL) ควรใช้ Alembic migration แทน
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
