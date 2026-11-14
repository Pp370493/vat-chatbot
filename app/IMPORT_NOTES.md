# ที่มาของโฟลเดอร์ `app/`

นำเข้าจากโฟลเดอร์ Google Drive `is chatbot/vat-copilot` (เดิมผูกกับเรโป `Pp370493/vat-copilot`) ทั้งหมด 84 ไฟล์
ขนาดไฟล์ตรงกับต้นฉบับทุกไฟล์

**ไม่ได้นำเข้า** (ไม่ควรอยู่ใน git):
- `backend/.env` — อาจมีค่าลับ ใช้ `backend/.env.example` เป็นแม่แบบ
- `vat_copilot.db`, `*.db.backup_before_clean` — ฐานข้อมูล SQLite (สร้างใหม่ตอนรัน + `scripts/ingest_all_announcements.py`)
- `chroma_data/`, `backend/venv/`, `frontend/node_modules/`, `frontend/.next/`, `__pycache__/`, `.git/`
- `*.log`, `test_*output*.txt`, `frontend/tsconfig.tsbuildinfo` — ผลรัน/ไฟล์ build

**ข้อสังเกตตอนนำเข้า**
- ข้อมูลตัวอย่างสำหรับ login (`officer@rd.go.th`, `demo-officer-token`) อยู่ในโค้ด เป็นค่า demo ไม่ใช่บัญชีจริง
- `backend/data/` และ `frontend/data/` มีสำเนาข้อมูลฝั่ง chunking (เช่น `official_vat_articles.json`) ซึ่งเป็นเวอร์ชันก่อนการแก้ไขใน branch `chunking-import`
- `README.md` ชั้นบนมีข้อความ UTF-16 ต่อท้าย (`# vat-copilot`) ทำให้ git มองเป็นไฟล์ binary
