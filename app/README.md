# VAT Copilot — ระบบผู้ช่วยตอบข้อหารือการจดทะเบียนภาษีมูลค่าเพิ่ม

Independent Study, NIDA MADT

```
app/
├── backend/    # FastAPI + SQLite + Agent 1–8 + Ollama (ดู backend/README.md)
├── frontend/   # Next.js (ดู frontend/README.md)
└── docs/       # เอกสารออกแบบเดิม
```

**ทดสอบบนโน้ตบุ๊ก:** ดูขั้นตอนติดตั้งและสถานการณ์ทดสอบใน [TESTING_TH.md](TESTING_TH.md)

ลำดับการเปิดระบบ: Ollama → backend (`uvicorn`, พอร์ต 8000) → frontend (`npm start`, พอร์ต 3000)

`START_VAT_COPILOT.bat` เปิดทั้ง 3 ส่วนบน Windows (ต้องเตรียมฐานข้อมูลด้วย `backend/scripts/setup_db.py` ก่อนครั้งแรก)
