# Frontend — Enterprise Tax Co-Pilot & Intelligence Platform

ยังไม่ได้ scaffold โค้ดจริง (เริ่มที่ Phase 5 ตาม Roadmap) นี่คือคำสั่งเริ่มต้นและ
โครงหน้าที่ต้องสร้างตาม `docs/VAT_CoPilot_IS_Full_Handoff.md`

## เริ่ม scaffold

```bash
npx create-next-app@latest . --typescript --tailwind --app
```

## หน้าที่ต้องสร้าง (ตาม Final Scope)

```
app/
├── login/                  # Authentication (RBAC: officer/senior_officer/admin)
├── chat/
│   └── page.tsx            # 3 คอลัมน์: ประวัติคำถาม | ถาม-ตอบ | ต้นฉบับกฎหมาย+highlight
├── review/
│   └── page.tsx            # Supervisor Approval View (escalations queue)
└── dashboard/               # Admin only
    ├── page.tsx             # overview: stats, heatmap
    ├── weekly-report/       # C2
    └── knowledge-manual/    # C3 (approve FAQ/คู่มือ)
```

เชื่อมกับ Backend ผ่าน REST API ตาม `docs/VAT_CoPilot_IS_Full_Handoff.md` ส่วนที่ 5
