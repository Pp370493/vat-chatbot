# Frontend — VAT Copilot (Next.js 14)

หน้าเว็บ: `/login` · `/chat` (ถาม-ตอบ) · `/review` (คิวหัวหน้างาน) · `/dashboard` และ `/test` (ผู้ดูแลระบบ)

## รัน
```
npm ci
npm run build
npm start          # http://localhost:3000   (ตอนพัฒนาใช้ npm run dev)
```
ต้องเปิด backend (http://127.0.0.1:8000) ก่อน

## การเชื่อม backend
- หน้าเว็บเรียก `/api/v1/...` บนพอร์ตเดียวกัน แล้ว Next.js ส่งต่อไป backend (รอได้ 300 วินาที) พร้อม session token
- ตัวแปร (ใส่ใน `.env.local` ถ้าต้องการเปลี่ยน):
  - `BACKEND_API_URL` — ที่อยู่ backend ฝั่งเซิร์ฟเวอร์ (ค่าเริ่ม `http://127.0.0.1:8000`)
  - `NEXT_PUBLIC_API_BASE_URL` — ถ้าตั้ง เบราว์เซอร์จะเรียก backend ตรง (ต้องเพิ่ม origin ใน `CORS_ORIGINS` ของ backend)
  - `DEMO_MODE=true` — **เฉพาะงานสาธิตที่ไม่มี backend** (เช่น Vercel): ตอบด้วยข้อความสำเร็จรูปและแสดงป้าย “โหมดเดโม”
    ไม่ตั้ง = ถ้า backend ล่มจะแจ้งว่าเชื่อมต่อไม่ได้ (ไม่แสดงคำตอบปลอม)
- สิทธิ์ตรวจที่ backend ทุกคำขอ หน้าเว็บแค่พาไปหน้าที่บทบาทนั้นเข้าได้
