# Backend — VAT Copilot (FastAPI)

ระบบตอบข้อหารือการจดทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.01) จากประกาศอธิบดีกรมสรรพากร ฉบับที่ 57 / 159 (+234 กรณี DBD)
ทำงานบนเครื่องเดียวกับ Ollama — ไม่ต้องใช้อินเทอร์เน็ตตอนตอบคำถาม

## ติดตั้ง (Windows)

1. ติดตั้ง Ollama แล้วดึงโมเดล (รวมราว 2.2 GB)
   ```
   ollama pull qwen2.5:3b-instruct
   ollama pull nomic-embed-text
   ```
   ตั้งตัวแปรระบบ `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_NUM_PARALLEL=1` แล้วเปิด Ollama ใหม่
2. สร้าง venv และติดตั้งแพ็กเกจ (ในโฟลเดอร์ `app/backend`)
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. `copy .env.example .env` แล้วตรวจค่า — สำคัญ: `USE_MOCK_LLM=false`, `OLLAMA_NUM_THREAD` = จำนวนคอร์จริง
   (i5-8250U ใช้ 4) — **ห้าม commit ไฟล์ `.env`**
4. เตรียมฐานข้อมูล (ต้องเปิด Ollama): สร้างตาราง นำตัวบท 75 chunks เข้าพร้อม embedding
   สร้างผู้ใช้ 3 บทบาท และหน่วยงานสำหรับเคสนอกสโคป
   ```
   python scripts/setup_db.py --ingest
   ```
   ไม่ระบุรหัสผ่าน = สุ่มให้และพิมพ์ออกจอครั้งเดียว (`--password-officer/--password-senior/--password-admin` เพื่อกำหนดเอง,
   `--reset-passwords` เพื่อสุ่มใหม่)
5. เปิดเซิร์ฟเวอร์
   ```
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   ตรวจ: http://127.0.0.1:8000/health ต้องได้ `{"status":"ok"}`

## ความปลอดภัย
- ทุก endpoint ยกเว้น `/health` และ `/api/v1/auth/login` ต้องส่ง `Authorization: Bearer <session_token>`
- รหัสผ่านเก็บเป็น PBKDF2-SHA256 · session หมดอายุตาม `AUTH_SESSION_EXPIRY_HOURS` · มี `/auth/logout`
- สิทธิ์: คิวหัวหน้างาน = senior_officer/admin · analytics และรายชื่อผู้ใช้ = admin · ผู้ใช้มาจาก token เสมอ
- `ENABLE_DEMO_ROLE_SWITCH` (สลับบทบาทโดยไม่ใส่รหัส) ปิดไว้ — ใช้เฉพาะงานสาธิต

## ทดสอบ
```
python -m pytest tests
python scripts/bench_pipeline.py --db bench.db --ingest --per-group 12,6,6   # วัดเวลาและความถูกต้องกับโมเดลจริง
```

## หมายเหตุ
- ตัวบทอยู่ใน `data/official_vat_articles.json` · embedding เก็บในคอลัมน์ `kb_articles.embedding` (ไม่ได้ใช้ Chroma)
- สคริปต์เดิม `scripts/ingest_all_announcements.py`, `parse_and_apply_14_points.py`, `apply_user_tuning_table.py`,
  `sync_metadata.py` อ้าง path บนเครื่องผู้พัฒนาเดิม (Windows) — เลิกใช้ ให้ใช้ `setup_db.py` แทน
- Agent 8 (สรุปคำถามรายสัปดาห์) ยังเป็นโครงเปล่า
