# Backend — Enterprise Tax Co-Pilot & Intelligence Platform

## Quick Start

```bash
# 1. สร้าง virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. ตั้งค่า environment
cp .env.example .env
# USE_MOCK_LLM=true ไว้ก่อน (dev loop เร็ว ไม่ต้องรอ Ollama จริง — ดู docs/ ส่วนที่ 14.4)

# 4. รันเซิร์ฟเวอร์
uvicorn app.main:app --reload

# 5. ทดสอบ
curl http://localhost:8000/health
# เปิด http://localhost:8000/docs ดู Swagger UI ของทุก endpoint
```

## เมื่อพร้อมใช้ LLM จริง (Phase 5 เป็นต้นไป)

```bash
# ติดตั้ง Ollama แล้ว pull โมเดล
ollama pull qwen2.5:3b-instruct-q4_K_M

# แก้ .env
USE_MOCK_LLM=false
```

## โครงสร้างโค้ด

- `app/agents/` — Agent 1-8 (ดู docstring แต่ละไฟล์, อ้างอิง `docs/VAT_CoPilot_IS_Full_Handoff.md` ส่วนที่ 4)
- `app/graph/pipeline_graph.py` — orchestration เชื่อม Agent 1-6 (ยังเป็น in-memory, TODO ต่อ DB persistence)
- `app/models/models.py` — SQLAlchemy ORM ตรงกับ `docs/schema.sql`
- `app/api/` — REST endpoints (ดู `docs/VAT_CoPilot_IS_Full_Handoff.md` ส่วนที่ 5)
- `scripts/ingest_kb_documents.py` — สำหรับ Phase 1 (ยังไม่ implement)

## สถานะปัจจุบัน

โครงนี้คือ **skeleton พร้อมรัน** (import ได้, health check ผ่าน, mock pipeline ทำงานจบ end-to-end)
แต่ยังไม่ต่อ DB persistence จริงใน pipeline, ยังไม่มี real Ollama/ChromaDB integration,
และยังไม่มี authentication จริง — เป็นจุดเริ่ม Phase 0-1 ตาม Roadmap ใน
`docs/VAT_CoPilot_IS_Full_Handoff.md` ส่วนที่ 11
