# Enterprise Tax Co-Pilot & Intelligence Platform
## Full Project Handoff Document (สำหรับพัฒนาต่อด้วย Local LLM และทำงานร่วมกับทีม)

**โครงการ**: Independent Study (IS) — NIDA, MADT Program
**โดเมน**: VAT Registration — กรมสรรพากร (Thai Revenue Department)
**สถานะเอกสาร**: พร้อมใช้เริ่ม implement จริง (engineering-ready) — Sync กับ Final Scope ล่าสุดแล้ว (Auth/RBAC, หน้าจอ 2 ส่วน, Agent 2/7/8 ปรับปรุง, A5 Deterministic Grounding)

---

# สารบัญ
1. Background & Problem Statement
2. Solution Overview
3. Tech Stack & Local LLM Setup
4. Multi-Agent Pipeline (รายละเอียดครบ 8 Agent)
5. API Design (REST Endpoints)
6. Database Schema
7. Recommended Project Folder Structure
8. Feature List & User Benefits (3 กลุ่มผู้ใช้)
9. State Flow (Business Logic State Machine)
10. Out-of-Scope Taxonomy (ฉบับร่าง)
11. Development Roadmap
12. Evaluation Metrics สำหรับ IS
13. Open Items ที่ต้องยืนยันกับอาจารย์/รุ่นพี่
14. Hardware Optimization Guide (สำหรับเครื่อง RAM 8GB ไม่มี GPU)

---

# 1. Background & Problem Statement

โปรเจคเดิมถูกประเมินว่าเป็นเพียง "General Chatbot" ระดับ First Level — ถามมา-ตอบไปจาก PDF เท่านั้น
อาจารย์ที่ปรึกษาให้ยกระดับ Workflow โดยเน้น 4 ประเด็น:

1. **Known vs Unknown Issues & Escalation** — เคสยาก/ซับซ้อนต้องมี Approval Loop ให้หัวหน้างานตรวจ ไม่ใช่ AI ตอบเองจบ 100%
2. **Form Assistance & Document Checking** — ช่วยแนะนำเอกสาร/กรอกฟอร์ม รวมถึงเคสแปลก เช่น เปลี่ยนผู้ถือหุ้นระหว่างจด VAT
3. **Out-of-Scope Handling** — ต้องบอกเหตุผลว่าทำไมไม่ตรงสโคป และแนะแนวทางไปหน่วยงานที่ถูกต้อง
4. **Admin Dashboard with Insights** — สถิติเชิงลึก (คำถามซ้ำ, ถูกเรื่อง/ผิดเรื่อง) ส่ง Insight พัฒนาคลังความรู้กลาง

---

# 2. Solution Overview

เปลี่ยนจาก "RAG Chatbot ธรรมดา" → **Multi-Agent Case Management System** ที่มี:
- Human-in-the-loop สำหรับเคสเสี่ยง/ไม่แน่ใจ
- Risk-based tiered escalation (auto_answer / officer_review / senior_review)
- Verifier Agent ป้องกัน hallucination (grounding check ทุกประโยค)
- Continuous Knowledge Growth Loop (คลังความรู้เติบโตจากงานจริงแบบมี human approval)
- Audit Trail ครบทุก decision สำหรับ compliance และการประเมินผลเชิงวิชาการ

**หลักการออกแบบสำคัญ**: ทุกคำตอบต้องผ่าน "Trust Score" (`confidence × (1 − risk_score)`) ก่อนตัดสินว่าจะตอบผู้ใช้ทันทีหรือต้องรอคนตรวจ

**ผู้ใช้งาน**: เจ้าหน้าที่กรมสรรพากร 3 ระดับสิทธิ์ (Officer / Senior Officer / Admin) — ต้องยืนยันตัวตนก่อนเข้าระบบเสมอ (ดูส่วนที่ 5 API Design)

**โครงสร้างหน้าจอ**:
1. **Chatbot Interface** (ทุก role) — 3 คอลัมน์: ซ้าย=ประวัติคำถาม, กลาง=ถาม-ตอบ, ขวา=ต้นฉบับกฎหมายพร้อม highlight
2. **Admin Dashboard** (Admin/Senior) — สถิติการใช้งาน, log, heatmap, รายงานคำถามยอดนิยม

---

# 3. Tech Stack & Local LLM Setup

| ส่วน | เทคโนโลยี |
|---|---|
| LLM Inference | Qwen2.5:3B-instruct (q4_K_M) ผ่าน Ollama — fallback: Gemma 2B / Qwen2.5:1.5B ถ้า RAM ไม่พอ |
| Embedding | bge-m3 (multilingual, lazy-load/unload เพื่อประหยัด RAM) — fallback: multilingual-e5-base |
| Orchestration | LangChain (LangGraph แนะนำสำหรับ multi-agent state machine) |
| Vector DB | ChromaDB (persist local) |
| Backend API | FastAPI (Python 3.11+) |
| Frontend | Next.js 14+ (App Router) + TypeScript + Tailwind CSS |
| Database | SQLite (dev) → PostgreSQL (production), `uuid.uuid4()` app-layer |
| Authentication | Session-based RBAC (Officer/Senior/Admin) — ดูตาราง `auth_sessions` ใน schema.sql |
| Protocol | REST (HTTP POST, JSON) |

## ขั้นตอนติดตั้ง Local LLM (Ollama + Gemma)

```bash
# 1. ติดตั้ง Ollama (Linux/Mac)
curl -fsSL https://ollama.com/install.sh | sh

# 2. ดึงโมเดล
ollama pull qwen2.5:3b-instruct-q4_K_M   # LLM หลัก
ollama pull bge-m3                        # Embedding (ถ้ามีใน Ollama registry) หรือใช้ผ่าน sentence-transformers

# 3. ทดสอบว่าใช้งานได้
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:3b-instruct-q4_K_M",
  "prompt": "สรุปมาตรา 85/1 ของประมวลรัษฎากรสั้นๆ"
}'
```

## Environment Variables ที่ต้องเตรียม (.env)

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_DEFAULT=qwen2.5:3b-instruct-q4_K_M
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=5m
EMBEDDING_MODEL=bge-m3
CHROMA_PERSIST_DIR=./chroma_data
DATABASE_URL=sqlite:///./vat_copilot.db    # dev; เปลี่ยนเป็น postgresql://... ตอน production
AUTH_SESSION_EXPIRY_HOURS=8
RISK_THRESHOLD_OFFICER=0.6         # trust_score ต่ำกว่านี้ -> officer_review
RISK_THRESHOLD_SENIOR=0.35         # ต่ำกว่านี้ -> senior_review
USE_MOCK_LLM=true                  # true ตอน dev Phase 0-4, false ตอนทดสอบคุณภาพจริง
CONVERSATION_MAX_TURNS=5           # sliding window
RETRIEVAL_TOP_K=5                  # ดึงเก็บ log ครบ แต่ส่งเข้า prompt Agent 4 แค่ top 3
RETRIEVAL_TOP_K_IN_PROMPT=3
CHUNK_MAX_TOKENS=350               # บังคับ chunk ที่เข้า prompt ไม่เกินนี้ (ดู 14.8)
OLLAMA_BASE_URL_PRIMARY=           # ปล่อยว่างถ้ายังไม่ใช้ cloud fallback (ดู 14.9)
OLLAMA_BASE_URL_FALLBACK=http://localhost:11434
OLLAMA_HEALTHCHECK_TIMEOUT_MS=2000
```

**คำแนะนำโมเดล**: ใช้ `qwen2.5:3b-instruct-q4_K_M` เป็นโมเดลเดียวทุก Agent (เบาพอสำหรับ RAM 8GB) ใช้ `bge-m3` แบบ lazy-load/unload สำหรับ Agent 3 (Retrieval) และ Agent 5 (embedding similarity check) — ไม่ต้องโหลดโมเดลหลายตัวพร้อมกัน ดู Hardware Optimization Guide (ส่วนที่ 14) สำหรับรายละเอียดเพิ่มเติม

---

# 4. Multi-Agent Pipeline (รายละเอียดครบ 8 Agent)

## ตารางสรุป

| กลุ่ม | Agent | โมเดลแนะนำ | หน้าที่หลัก |
|---|---|---|---|
| Query Routing | 1. Intent & Scope Classifier | qwen2.5:3b (lightweight prompt) | เช็คสโคป VAT registration |
| | 2. Out-of-Scope Router | keyword + qwen2.5:3b **ควบคู่กันทุกครั้ง** | ตรวจ intent คู่ + บอกเหตุผล + redirect |
| Answer Generation | 3. RAG Retrieval Agent | bge-m3 embedding | ดึงข้อมูลจาก `kb_articles` ที่ `status='approved'` เท่านั้น |
| | 4. Responder Agent | qwen2.5:3b | ร่างคำตอบแบบ grounded (ห้ามใช้ความรู้นอกเอกสาร) |
| | 5. Verifier Agent | regex (ทุกเคส) + qwen2.5:3b (เฉพาะ senior_review) | ตรวจ grounding / anti-hallucination สองชั้น |
| Escalation & Growth | 6. Risk & Tier Decision Agent | **rule-based ล้วน — ห้าม LLM คิดคะแนนเอง** | คำนวณ risk, ตัดสิน tier |
| | 7. Checklist Assistant Agent | qwen2.5:3b + decision tree + slot-filling | เก็บคุณสมบัติ, generate checklist, **เจ้าหน้าที่ทำเครื่องหมายเอง** |
| | 8. Knowledge & Reporting Batch Agent | qwen2.5:3b (batch กลางคืน) | KB growth + รายงานคำถามยอดนิยม (C2) + คู่มือความรู้ (C3) |

## รายละเอียดแต่ละ Agent (I/O Contract)

### Agent 1: Intent & Scope Classifier
```
INPUT:  { "raw_text": string }
OUTPUT: { "in_scope": bool, "sub_intent": "qa"|"form_assist"|"edge_case", "confidence": float }
```
- Prompt strategy: system prompt กำหนด taxonomy ของสโคปชัดเจน + 5-10 few-shot examples (ทั้งเคส in-scope และ out-of-scope)
- Route: `in_scope=false` → Agent 2 | `sub_intent="form_assist"` → Agent 7 | อื่นๆ → Agent 3

### Agent 2: Out-of-Scope Router
```
INPUT:  { "raw_text": string, "query_id": uuid }
OUTPUT: { "matched_topic": string, "matched_via": "keyword"|"llm"|"both", "department_id": uuid, "redirect_message": string }
```
- **Final Scope**: ตรวจสอบ intent ที่แท้จริงด้วย **keyword matching กับตาราง `departments` และ LLM วิเคราะห์เชิงความหมายควบคู่กันทุกครั้ง** (ไม่ใช่ keyword-first/LLM-fallback แบบเดิมอีกต่อไป) เพื่อป้องกันการตีความ intent ผิดพลาด
- ตรวจสอบว่าอยู่ในสโคปหรือไม่จากผลทั้ง 2 วิธีประกอบกัน → ถ้าไม่ตรง generate เหตุผล+redirect เฉพาะเจาะจง
- บันทึกผลลง `out_of_scope_routes` (รวม `matched_via` สำหรับ audit)
- **หมายเหตุ**: เรียก LLM ทุกคำถาม (ไม่ประหยัด compute เท่าที่ออกแบบไว้เดิม) — ปรับ prompt ให้ตอบสั้น/เร็วที่สุดเพื่อลดผลกระทบ latency

### Agent 3: RAG Retrieval Agent
```
INPUT:  { "raw_text": string, "query_id": uuid }
OUTPUT: { "rewritten_query": string, "chunks": [{chunk_id, text, source_section}], "relevance_scores": [float] }
```
- Query Rewriting ก่อน embed (ขยายคำย่อ/เติม legal context)
- top-k = 5 (ปรับได้), บันทึกลง `retrieval_logs`
- **Final Scope (A5)**: ค้นหาเฉพาะ `kb_articles` ที่ `status='approved'` เท่านั้น — เอกสาร `source='official'` ใช้ได้ทันทีเมื่อ approved, `source='experiential'` ต้องผ่าน Admin approve ก่อนเท่านั้นถึงจะถูกดึงมาใช้ได้
- **Multi-turn Scope (ใหม่)**: Query Rewriting ขยายหน้าที่เป็น **Coreference Resolution** — แปลงคำถามที่พึ่งพาบริบท (เช่น "แล้วต้องจดเมื่อไหร่") ให้เป็นคำถามสมบูรณ์ในตัวเอง (`resolved_query`) โดยอ้างอิง **สูงสุด 5 เทิร์นล่าสุด** ของบทสนทนา (Sliding Window) ก่อนนำไปค้นหา
- **สำคัญ**: ขั้นตอน resolve นี้ต้องเรียก LLM ด้วย **`temperature=0`** เท่านั้น (เฉพาะ sub-step นี้ ไม่ใช่ทั้งระบบ) เพื่อให้คำถามเดียวกันในบริบทเดียวกัน resolve ออกมาเหมือนกันทุกครั้ง — เป็นเงื่อนไขจำเป็นที่ทำให้ **Consistency Guarantee ของ A5 นิยามที่ระดับ `resolved_query` แทน `raw_text`** มีความหมายจริง (ถ้า resolve ไม่คงที่ guarantee ทั้งระบบจะพังตั้งแต่ขั้นตอนแรก)
- Context ที่ส่งเข้า Agent 3 ต่อเทิร์น: ใช้ `resolved_query` + `answer_summary` (สรุป 1 ประโยค ไม่ใช่ draft answer เต็ม) ของเทิร์นก่อนหน้าเท่านั้น — ไม่ส่ง raw history ทั้งหมด เพื่อควบคุม token budget ให้อยู่ใน `num_ctx` ที่ตั้งไว้

### Agent 4: Responder Agent
```
INPUT:  { "raw_text": string, "chunks": [...] }
OUTPUT: { "draft_text": string, "citations": [{text_span, source_section}] }
```
- Instruction บังคับให้ทุกประโยคที่อ้างข้อกฎหมายต้องมี citation tag
- บันทึกลง `draft_answers`
- **Multi-turn Scope**: นอกจาก `draft_text` เต็ม ให้ generate **`answer_summary`** (สรุป 1 ประโยค ≤500 ตัวอักษร) เก็บลง `queries.answer_summary` ไว้ใช้เป็น context ให้เทิร์นถัดไปเท่านั้น — ไม่ใช้ draft_text เต็มเป็น context เพื่อประหยัด token และลดความเสี่ยง "AI สรุปคำตอบของ AI เอง" ซ้อนชั้นหลายรอบ

### Agent 5: Verifier Agent (Self-Reflection)
```
INPUT:  { "draft_text": string, "citations": [...], "chunks": [...] }
OUTPUT: { "confidence_score": float, "ungrounded_claims": [string] }
```
- **Two-Tier Verification**: (1) Regex ตรวจเลขมาตรามีจริงไหม + Embedding similarity เทียบ draft กับ source chunk — ทำทุกเคส เร็ว ไม่ใช้ LLM (2) LLM "critic" call แยกจาก Agent 4 แบบเต็มรูปแบบ — เฉพาะเคสที่เข้า tier `senior_review` เท่านั้น
- กติกา: ถ้า `ungrounded_claims` ไม่ว่าง หรือ embedding similarity ต่ำกว่า threshold → บังคับ `confidence_score` ลดลงอย่างน้อย 30% และปรับ tier ขึ้น
- บันทึกลง `verification_scores`

### Agent 6: Risk & Tier Decision Agent
```
INPUT:  { "raw_text": string, "confidence_score": float }
OUTPUT: { "risk_score": float, "risk_factors": [string], "trust_score": float, "tier": "auto_answer"|"officer_review"|"senior_review" }
```
- Risk factors ตรวจจาก keyword/pattern (rule-based): มูลค่าเงินสูง, เปลี่ยนผู้ถือหุ้น, ควบรวมกิจการ, ธุรกรรมข้ามชาติ ฯลฯ
- สูตร: `trust_score = confidence_score * (1 - risk_score)`
- Threshold (ปรับได้ผ่าน .env): `trust_score >= 0.6` → auto_answer, `0.35–0.6` → officer_review, `< 0.35` → senior_review
- บันทึกลง `risk_assessments` และถ้าไม่ใช่ auto_answer → สร้าง record ใน `escalations`

### Agent 7: Checklist Assistant Agent (Final Scope — เดิมชื่อ Form Assistance Agent)
```
INPUT:  { "session_id": uuid, "user_answer": string | null }
OUTPUT: { "matched_case_id": uuid | null, "next_question": string | null, "suggested_documents": [string] | null, "is_complete": bool }
```
- ทำงานแบบ multi-turn ด้วย **External State Management (slot-filling)**: เก็บคุณสมบัติผู้ขอจดทะเบียนเป็น structured state ใน DB แทนการพึ่ง context window ยาว — ความจำไม่จำกัดจำนวนรอบ
- จับคู่กับ `case_templates.decision_tree` เพื่อเสนอ `suggested_documents` เริ่มต้น
- **สำคัญ**: AI แค่เสนอรายการเอกสาร — **เจ้าหน้าที่เป็นผู้ทำเครื่องหมายสถานะเอกสารแต่ละชิ้นเอง** ผ่านตาราง `document_checklist_items` (ไม่ใช่ AI generate checklist แล้วจบเหมือนเดิม) AI มีหน้าที่สรุปว่าเอกสารอะไรยังขาดอยู่จากสถานะที่เจ้าหน้าที่ทำเครื่องหมายเท่านั้น
- บันทึก conversation log ลง `form_assistance_sessions`, สถานะเอกสารลง `document_checklist_items`

### Agent 8: Knowledge & Reporting Batch Agent (Final Scope — ขยายจาก Knowledge Growth Agent เดิม)
```
INPUT:  { "time_window": "7d" }  (รันด้วย cron/scheduler ตอนกลางคืน วันละ 1 ครั้ง)
OUTPUT: {
  "kb_clusters": [{ "cluster_topic": string, "matched_query_ids": [uuid], "proposed_article_draft": string }],
  "weekly_report": { "week_start_date": date, "top_questions": [{question_pattern, count, in_scope}] },
  "manual_entries": [{ "title": string, "content": string, "source_query_ids": [uuid] }]
}
```
รวม 3 งานที่ใช้ embedding clustering ชุดเดียวกันเป็นฐาน:
1. **KB Growth**: threshold ความถี่ (เช่น >= 5 ครั้ง) → summarize คำตอบที่เคย approve → ร่าง KB article (`source='experiential'` หรือ `'auto_generated'`) → บันทึกลง `kb_growth_clusters` → รอ Admin approve ก่อน index เข้า `kb_articles` จริง
2. **C2 — รายงานคำถามยอดนิยมรายสัปดาห์**: บันทึกลง `weekly_question_reports` ให้ Admin เห็นในวันทำการถัดไป (ไม่ real-time)
3. **C3 — FAQ/คู่มือความรู้**: สรุปคำถาม-คำตอบเป็นคู่มือ บันทึกลง `knowledge_manual_entries` รอ Admin approve ก่อน publish ใช้ฝึกอบรมเจ้าหน้าที่

---

# 5. API Design (REST Endpoints)

## 5.0 Authentication (Final Scope — ใหม่)

```
POST /api/v1/auth/login
Request:  { "email": string, "password": string }
Response: { "session_token": string, "role": "officer"|"senior_officer"|"admin", "expires_at": datetime }
```
- ทุก endpoint ด้านล่างต้องแนบ `session_token` (header `Authorization: Bearer <token>`) — middleware ตรวจสิทธิ์ตาม `role` ก่อนเข้าถึง (เช่น `/analytics/*` และ `/escalations/*` เฉพาะ senior_officer/admin)

## 5.1 Chat Flow (ฝั่งผู้ใช้/หน้างาน)

```
POST /api/v1/chat/query
Request:  { "session_id": string, "conversation_id": uuid | null, "text": string }
Response: {
  "query_id": uuid,
  "conversation_id": uuid,          -- สร้างใหม่ถ้าไม่ส่งมา, ใช้ต่อถ้าเป็นเทิร์นถัดไป
  "turn_number": int,
  "resolved_query": string,          -- สำหรับ debug/แสดงผลว่าระบบเข้าใจคำถามว่าอย่างไร
  "type": "answer" | "redirect" | "pending_review" | "form_assist",
  "payload": { ... }   // ขึ้นกับ type
}
```
- Endpoint นี้ orchestrate agent 1→8 ภายใน (เรียกผ่าน LangGraph state machine)
- ถ้า `type = "pending_review"` → payload มี `estimated_wait_message` ให้แสดง user
- **Multi-turn Scope**: ก่อนเรียก Agent 1/3 ระบบดึง `resolved_query` + `answer_summary` ของสูงสุด 5 เทิร์นล่าสุดใน `conversation_id` เดียวกันมาแนบเป็น context (ไม่ใช้ `raw_text`/`draft_text` เต็ม)

```
POST /api/v1/chat/form-session/{session_id}/answer
Request:  { "answer": string }
Response: { "next_question": string|null, "suggested_documents": [...]|null, "is_complete": bool }
```

```
POST /api/v1/chat/form-session/{session_id}/checklist-item
Request:  { "document_name": string, "status": "received"|"missing"|"not_applicable", "marked_by": uuid }
Response: { "checklist_item_id": uuid, "remaining_missing": [string] }
```
- **Final Scope**: endpoint นี้คือจุดที่เจ้าหน้าที่ทำเครื่องหมายเอกสารเอง (ตาราง `document_checklist_items`) — AI ไม่ปิด checklist เอง

```
GET /api/v1/chat/query/{query_id}/status
Response: { "status": query_status, "answer": string|null }
```
- ใช้ polling หรือ WebSocket สำหรับกรณี `pending_review` ที่ต้องรอ supervisor

## 5.2 Supervisor Dashboard (ฝั่งเจ้าหน้าที่รุ่นพี่)

```
GET /api/v1/escalations?tier=officer_review&status=pending
Response: [{ query_id, raw_text, draft_text, confidence_score, risk_factors, created_at }]
```

```
POST /api/v1/escalations/{escalation_id}/decision
Request:  { "decision": "approved"|"edited"|"rejected", "final_answer": string, "reviewed_by": uuid }
Response: { "status": "answered" }
```

```
GET /api/v1/kb/growth-clusters?status=pending_review
Response: [{ cluster_id, cluster_topic, frequency_count, proposed_article_draft }]

POST /api/v1/kb/growth-clusters/{id}/approve
Response: { "kb_article_id": uuid, "status": "approved" }
```

## 5.3 Admin Dashboard Analytics (Feature 5)

```
GET /api/v1/analytics/overview?range=7d
Response: {
  "total_queries": int,
  "in_scope_ratio": float,
  "out_of_scope_breakdown": [{topic, count}],
  "escalation_rate": float,
  "auto_answer_rate": float,
  "top_repeated_questions": [{text, count}]
}
```

```
GET /api/v1/analytics/heatmap
Response: [{ "topic": string, "escalation_count": int }]
```

```
GET /api/v1/analytics/weekly-report?week=latest
Response: { "week_start_date": date, "top_questions": [{question_pattern, count, in_scope}], "in_scope_ratio": float }
```
- ข้อมูลมาจาก batch job ของ Agent 8 (รันกลางคืน) — Admin เห็นผลวันทำการถัดไปเสมอ ไม่ real-time

```
GET /api/v1/knowledge-manual?status=published
POST /api/v1/knowledge-manual/{id}/approve
```
- สำหรับ Admin ตรวจและ publish คู่มือความรู้ที่ Agent 8 ร่างไว้ (C3)

---

# 6. Database Schema

ดูไฟล์แนบ `schema.sql` (PostgreSQL DDL ครบ 17 ตาราง, Sync กับ Final Scope แล้ว) — สรุปตารางหลัก:

| ตาราง | เชื่อมกับ Agent |
|---|---|
| `queries` | ตารางแกนกลาง ทุก Agent อ้างอิง (รวม `conversation_id`, `turn_number`, `resolved_query`, `answer_summary`) |
| `conversations` | Multi-turn Scope — ติดตาม session สนทนา, sliding window ≤5 เทิร์น |
| `out_of_scope_routes` | Agent 2 (รวม `matched_via` สำหรับ audit) |
| `retrieval_logs` | Agent 3 |
| `draft_answers` | Agent 4 |
| `verification_scores` | Agent 5 |
| `risk_assessments` | Agent 6 |
| `escalations` | Agent 6 → Human review |
| `form_assistance_sessions`, `document_checklist_items` | Agent 7 (checklist แบบ human-controlled) |
| `kb_growth_clusters`, `kb_articles`, `weekly_question_reports`, `knowledge_manual_entries` | Agent 8 |
| `audit_log` | ทุก Agent (log ทุก event) |
| `staff_users`, `auth_sessions`, `departments`, `case_templates` | ตาราง reference/master data + authentication |

---

# 7. Recommended Project Folder Structure

```
vat-copilot/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── intent_classifier.py       # Agent 1
│   │   │   ├── scope_router.py            # Agent 2
│   │   │   ├── rag_retrieval.py           # Agent 3
│   │   │   ├── responder.py               # Agent 4
│   │   │   ├── verifier.py                # Agent 5
│   │   │   ├── risk_tier.py               # Agent 6
│   │   │   ├── checklist_assistant.py     # Agent 7
│   │   │   └── knowledge_batch.py         # Agent 8 (batch job: KB growth + weekly report + manual)
│   │   ├── graph/
│   │   │   └── pipeline_graph.py          # LangGraph state machine เชื่อม Agent 1-6
│   │   ├── api/
│   │   │   ├── auth.py                    # login/session (Final Scope)
│   │   │   ├── chat.py
│   │   │   ├── escalations.py
│   │   │   └── analytics.py
│   │   ├── models/                        # SQLAlchemy models ตรงกับ schema.sql
│   │   ├── db/
│   │   │   └── session.py
│   │   ├── core/
│   │   │   ├── config.py                  # โหลด .env
│   │   │   └── ollama_client.py
│   │   └── main.py
│   ├── scripts/
│   │   └── ingest_kb_documents.py         # โหลดข้อมูลกฎหมาย VAT เข้า ChromaDB
│   ├── requirements.txt
│   └── alembic/                           # DB migrations
├── frontend/
│   ├── app/
│   │   ├── chat/                          # Split-screen + Interactive Citation
│   │   ├── dashboard/                     # Admin Dashboard
│   │   └── review/                        # Supervisor Approval View
│   ├── components/
│   └── package.json
└── docs/
    ├── VAT_CoPilot_IS_Full_Handoff.md     # เอกสารนี้
    └── schema.sql
```

---

# 8. Feature List & User Benefits (Final Scope — 10 ฟีเจอร์หลัก)

| Feature | คุณค่าหลัก |
|---|---|
| Split-Screen + Interactive Citation | ตอบพร้อมต้นฉบับกฎหมายไฮไลต์คู่กัน ตรวจสอบย้อนกลับได้ทันที |
| Out-of-Scope Router (Dual-check) | ตรวจ intent ด้วย keyword+LLM ทุกครั้ง ป้องกันตีความผิดพลาด |
| Internal Ruling & Precedent Search | ตอบจากเอกสารทางการที่ยืนยันแล้วเท่านั้น คำถามเดียวกัน=คำตอบเดียวกันเสมอ |
| Risk-Based Escalation & Approval | Rule-based ล้วน เคสเสี่ยงต้องผ่านอนุมัติก่อนตอบจริง |
| Checklist Assistant (Human-controlled) | AI เสนอรายการ เจ้าหน้าที่ทำเครื่องหมายเอง AI สรุปที่ขาด |
| Confidence Badge | แสดงระดับความมั่นใจของคำตอบทันที |
| รายงานคำถามยอดนิยมรายสัปดาห์ | Batch กลางคืน ให้ Admin เห็นแนวโน้มวันทำการถัดไป |
| FAQ/คู่มือความรู้ Generator | สรุปคำถาม-คำตอบเป็นคู่มือฝึกอบรมเจ้าหน้าที่เก่า-ใหม่ |
| Continuous Knowledge Growth Loop | คลังความรู้เติบโตจากเคสจริง ผ่าน Admin อนุมัติเสมอ |
| Audit Trail & Compliance Log | บันทึกทุก decision ตรวจสอบย้อนหลังได้ 100% |

*(รายละเอียด trade-off และตัวอย่างเต็มของแต่ละฟีเจอร์ ดูได้ในเอกสาร `VAT_CoPilot_Complete_Feature_Summary.md`)*

---

# 9. State Flow (Business Logic State Machine)

```
AUTHENTICATED (ทุกคำขอต้องผ่านจุดนี้ก่อนเสมอ)
 → NEW
 → SCOPE_CHECKED (in_scope / out_of_scope — ตรวจด้วย keyword+LLM คู่กันเสมอ)
   → [out_of_scope] REDIRECTED (จบ)
   → [in_scope, form_assist] → Agent 7 loop (slot-filling, ไม่จำกัดรอบ)
     → เจ้าหน้าที่ทำเครื่องหมาย document_checklist_items เอง → ANSWERED (จบ)
   → [in_scope, qa] RETRIEVED (เฉพาะเอกสาร approved) → DRAFTED → VERIFIED (2 ชั้น)
     → TIER_ASSIGNED
       → [auto_answer] ANSWERED (จบ)
       → [officer_review / senior_review] PENDING_REVIEW
         → (APPROVED | EDITED | REJECTED) → ANSWERED (จบ)
 → LOGGED (ทุก path ต้องจบที่นี่)

[แยกออกจาก flow หลัก — รันเป็น batch กลางคืนวันละครั้ง]
Agent 8: escalations สะสม → kb_growth_clusters + weekly_question_reports + knowledge_manual_entries
   → รอ Admin approve → เข้าสู่ kb_articles / published
```

---

# 10. Out-of-Scope Taxonomy (ฉบับร่าง — ต้องยืนยันกับอาจารย์/รุ่นพี่)

| หมวด | ตัวอย่าง keyword | หน่วยงานที่แนะนำ |
|---|---|---|
| ขอคืนภาษี | "คืนภาษี", "ขอคืน", "refund" | กองคืนภาษี |
| ภาษีเงินได้บุคคลธรรมดา | "ภงด.90", "ภงด.91", "ภาษีเงินได้บุคคล" | สำนักงานสรรพากรพื้นที่ |
| ภาษีเงินได้นิติบุคคล | "ภงด.50", "ภาษีนิติบุคคล" | สำนักงานสรรพากรพื้นที่ |
| ใบกำกับภาษี | "ใบกำกับภาษี", "e-Tax invoice" | ฝ่ายใบกำกับภาษีอิเล็กทรอนิกส์ |
| ยกเลิกทะเบียน VAT | "เลิกกิจการ", "ยกเลิก VAT" | ฝ่ายทะเบียนภาษีมูลค่าเพิ่ม (ใกล้เคียงสโคปนี้ — พิจารณาว่าจะรวมสโคปหรือไม่) |
| ภาษีศุลกากร/นำเข้า-ส่งออก | "นำเข้า", "ส่งออก", "ศุลกากร" | กรมศุลกากร (คนละกรม) |

*หมายเหตุ: ตารางนี้เป็นจุดเริ่มต้นเท่านั้น ต้องให้อาจารย์/รุ่นพี่ช่วย confirm รายชื่อหน่วยงานและช่องทางติดต่อจริง*

---

# 11. Development Roadmap (แนะนำ)

| Phase | งาน | Output |
|---|---|---|
| Phase 0 | Setup infra: Ollama, ChromaDB, SQLite, FastAPI skeleton + **Authentication (login/session)** | dev environment พร้อม, login ใช้ได้ |
| Phase 1 | Ingest เอกสารทางการ VAT เข้า ChromaDB (source='official') + สร้าง DB schema จริง | RAG พื้นฐานทำงานได้ |
| Phase 2 | Agent 1, 3, 4 (Classifier + Retrieval + Responder) | ตอบคำถามพื้นฐานได้ (ยังไม่มี escalation) |
| Phase 3 | Agent 5, 6 (Verifier 2-tier + Risk/Tier rule-based) + ตาราง escalations | มี Known/Unknown แยกจริง |
| Phase 4 | Agent 2 (Out-of-Scope Router แบบ dual-check) + ตาราง departments | ตอบ redirect ได้ |
| Phase 5 | Frontend: หน้าจอ 2 ส่วน (Chatbot 3-คอลัมน์ + Admin Dashboard) + Supervisor Review UI | Demo ได้ end-to-end |
| Phase 6 | Agent 7 (Checklist Assistant) + UI ทำเครื่องหมายเอกสาร | รองรับ checklist แบบ human-controlled |
| Phase 7 | Agent 8 (KB Growth + รายงานรายสัปดาห์ + คู่มือความรู้) + Admin Dashboard analytics | ปิด feedback loop |
| Phase 8 | Audit trail + Evaluation metrics (ดูส่วนที่ 12) | พร้อมส่งประเมินผล IS |

---

# 12. Evaluation Metrics สำหรับ IS

- **Scope Classification Accuracy**: Confusion matrix ของ Agent 1 (in-scope/out-of-scope) เทียบกับ labeled test set
- **Grounding Precision**: % ของ claims ในคำตอบที่ Agent 5 ยืนยันว่ามีหลักฐานรองรับจริง
- **Agreement Rate**: % ที่ supervisor กด "approved" โดยไม่แก้ไข เทียบกับที่ต้อง "edited"/"rejected" — วัดความแม่นของ AI draft
- **Escalation Precision/Recall**: เทียบว่าเคสที่ AI ส่ง escalate จริงๆ ควรถูก escalate หรือไม่ (เทียบกับ human judgment ย้อนหลัง)
- **Knowledge Growth Effectiveness**: จำนวน KB article ใหม่ที่เกิดจาก Agent 8 และอัตราการลด escalation ซ้ำในหัวข้อเดียวกันหลังเพิ่ม article
- **Coreference & Rewrite Accuracy** (แกนที่ 6 — Multi-turn Scope): วัดความถูกต้องของ Agent 3 ในการแปลงคำถามที่พึ่งพาบริบท (เช่น "แล้วต้องจดเมื่อไหร่") เป็น `resolved_query` ที่สมบูรณ์ถูกต้อง เทียบกับชุดทดสอบบทสนทนา 5 เทิร์นที่มี ground truth — เป็นแกนเพิ่มเติม **ไม่ใช่การแทนที่แกนใดแกนหนึ่งข้างต้น**

**ชุดข้อมูลทดสอบ**: จัดทำ Synthetic & Real Benchmark Dataset รวม 80-100 เคส ครอบคลุมทั้ง 6 แกนข้างต้น

---

# 13. Open Items ที่ต้องยืนยันกับอาจารย์/รุ่นพี่ก่อนเริ่ม Phase 3 เป็นต้นไป

1. ตาราง Out-of-Scope Taxonomy (ส่วนที่ 10) — รายชื่อหน่วยงาน/ช่องทางที่ถูกต้องจริง
2. Case library เริ่มต้นสำหรับ Form Assistance (Agent 7) — อย่างน้อย 3-5 เคส
3. ตัวเลข Threshold ของ `RISK_THRESHOLD_OFFICER` / `RISK_THRESHOLD_SENIOR` — ต้อง calibrate จากข้อมูลจริงหรือ mock case
4. ไฟล์ข้อมูลกฎหมาย VAT ตั้งต้นสำหรับ ingest เข้า ChromaDB (รอผู้ใช้ส่งมา) — **ต้องมีหลักฐานยืนยันว่าเป็นประกาศ/ข้อหารือทางการ** (Final Scope A5)
5. ขอบเขตของ "ยกเลิกทะเบียน VAT" ว่านับเป็น in-scope หรือ out-of-scope ของระบบนี้
6. **กระบวนการ Admin Approval สำหรับความรู้จากประสบการณ์** (`source='experiential'`) — ใครมีอำนาจอนุมัติ และเกณฑ์การอนุมัติควรเป็นอย่างไร
7. รายชื่อเจ้าหน้าที่เริ่มต้นสำหรับสร้างบัญชี `staff_users` (Officer/Senior/Admin) ตอน Phase 0

---

# 14. Hardware Optimization Guide (สำหรับเครื่อง RAM 8GB ไม่มี GPU)

เอกสารส่วนนี้เขียนสำหรับ dev machine สเปค: Intel Core i5 Gen 8, RAM 8GB, SSD, Windows 10 — ข้อจำกัดหลักคือ RAM ต้องแบ่งให้ OS + IDE + FastAPI + ChromaDB + Ollama พร้อมกัน กลยุทธ์คือ "ลดภาระทุกจุดที่ไม่จำเป็น"

## 14.1 เลือกโมเดลให้เหมาะกับ RAM จริง
- **ใช้ Qwen2.5:3B-instruct (q4_K_M) เป็นหลักตลอดโปรเจค** (กิน RAM ~1.9-2.5GB ขึ้นกับ context) — fallback: `qwen2.5:1.5b` หรือ `phi3:mini` ถ้าทดสอบแล้วเครื่องหน่วง
- `bge-m3` (embedding) ใช้แบบ lazy-load/unload ไม่โหลดค้างตลอดเวลา — ดูรายละเอียด 14.6
- วันเดโม/ต้องการคุณภาพคำตอบสูงขึ้น: เช่า GPU ชั่วคราว (Google Colab / Kaggle free tier) รัน Ollama แล้วสลับ `OLLAMA_BASE_URL` ใน `.env` ชี้ไปที่นั่น (architecture รองรับอยู่แล้ว, ดูแผน fallback เต็มใน 14.9) — ควรคุยกับอาจารย์ก่อนว่านับเป็น "local" ตามสเปคเดิมหรือไม่

## 14.2 ปรับ Ollama ให้ประหยัด RAM
```
OLLAMA_NUM_PARALLEL=1        # ไม่โหลดโมเดลซ้ำหลาย instance พร้อมกัน
OLLAMA_MAX_LOADED_MODELS=1   # โหลดทีละโมเดล
OLLAMA_KEEP_ALIVE=5m         # unload โมเดลออกจาก RAM หลังไม่ใช้ 5 นาที
```
- ตั้ง `num_thread` ให้ตรงจำนวน physical core (i5-8250U: 4 core/8 thread → เริ่มที่ `num_thread=4` แล้วทดสอบปรับ)

## 14.3 Database ตอน dev: ใช้ SQLite แทน PostgreSQL
- PostgreSQL server กิน RAM ค้างอยู่เบื้องหลังตลอดเวลา — ตอน dev/test บนเครื่องนี้ใช้ **SQLite** แทน แล้วค่อยสลับเป็น PostgreSQL ตอน deploy จริง/เดโม
- ต้องแก้ schema: เปลี่ยน `gen_random_uuid()` เป็น generate UUID ที่ application layer (`uuid.uuid4()` ใน Python) เพื่อให้ schema portable ระหว่าง SQLite/PostgreSQL

## 14.4 Dev Workflow ที่ประหยัด RAM
- อย่ารันทุก service พร้อมกันตลอดเวลา — ปิด Next.js dev server ตอนพัฒนา backend, ปิด Ollama ตอนพัฒนา frontend
- **ทำ Mock LLM Mode**: flag `USE_MOCK_LLM=true` ให้ Agent คืน canned response แทนเรียก Ollama จริงตอน debug pipeline/API/DB logic — CPU inference บนเครื่องนี้จะช้า (~5-15 token/วินาที) การ mock ช่วยให้ dev loop เร็วขึ้นมาก
- ปิด extension ที่ไม่จำเป็นใน VS Code, ปิด browser tab เยอะๆ ตอน dev

## 14.5 ปรับ Windows ให้รองรับ workload
- เพิ่ม Virtual Memory / Page File (Settings → System → About → Advanced system settings → Performance → Advanced → Virtual Memory) ตั้ง custom size ~8-12GB กัน process ตายตอน RAM เต็ม
- ปิด background app ที่ไม่จำเป็น (OneDrive sync, Windows Search indexing) ตอนรันงานหนัก

## 14.6 ลดขนาดงานฝั่ง RAG/ChromaDB
- ใช้ embedding model เบา เช่น `all-MiniLM-L6-v2` (sentence-transformers, ~80MB) แทน embedding model ใหญ่ — พอเพียงสำหรับ domain แคบแบบ VAT registration
- จำกัด chunk size เอกสารกฎหมายที่ 300-500 token — ลด memory footprint ตอน retrieve

## 14.7 ปรับลำดับ Roadmap ให้เข้ากับข้อจำกัดเครื่อง
- **Phase 0-4** (agent/pipeline logic, ดูส่วนที่ 11): ใช้ `USE_MOCK_LLM=true` + SQLite ทั้งหมด
- **Phase 5 เป็นต้นไป** (ต้องทดสอบคุณภาพคำตอบจริง): ค่อยสลับมาใช้ Ollama + Qwen2.5:3B จริง
- วันเดโม/ส่งงาน: ใช้แผน Hybrid Compute ตาม 14.9 (Colab GPU + local fallback)

## 14.8 Context Budget ต่อ Agent สำหรับ Multi-turn (5-เทิร์น)

หลักการ: **ไม่ตั้ง `num_ctx` เดียวกันทุก Agent** — ใช้ค่าที่พอดีกับงานแต่ละจุด เพื่อไม่ให้ KV cache กิน RAM เกินจำเป็นในการเรียกที่ถี่ (Agent 1-4) ขณะที่การเรียกที่เกิดน้อยครั้ง (Agent 5 deep-verify, Agent 8 batch) ยอมให้ context ใหญ่กว่าได้

**คำนวณ token budget จริงต่อ Agent** (อิงสมมติฐาน: chunk ≤350 token/ชิ้น หลังปรับจาก 14.6, `answer_summary` ≤500 ตัวอักษร ≈150 token, `resolved_query` ≈50 token):

| Agent | องค์ประกอบ context | รวมโดยประมาณ | `num_ctx` แนะนำ |
|---|---|---|---|
| 1 (Intent Classifier) | system prompt สั้น + คำถามปัจจุบัน | ~350 | **1024** |
| 2 (Out-of-scope dual-check) | system prompt + คำถาม + รายการ keyword/department | ~450 | **1024** |
| 3 (Query Rewriting/Resolve) | system(150) + **ประวัติ 5 เทิร์น** (5×200=1000) + คำถามดิบ(50) + output(100) | ~1,300 | **2048** (เหลือ margin ~750) |
| 4 (Responder) | system(200) + resolved_query(60) + **chunks top_k=3×350=1,050** + output คำตอบ(600) | ~1,910 | **2048** (เหลือ margin ~138 — ตึงที่สุด) |
| 5 (Verifier, senior_review เท่านั้น) | system(200) + resolved_query(60) + chunks(1,050) + draft(500) + critique output(300) | ~2,110 | **3072** (เกิน 2048 แต่เรียกน้อยครั้ง จึงใช้ context ใหญ่กว่าเฉพาะ call นี้) |
| 8 (Batch, กลางคืน) | ไม่แข่ง RAM กับ real-time traffic | ไม่จำกัดเข้มงวด | **4096** |

**การเปลี่ยนแปลงที่ต้องทำจากค่าที่ตั้งไว้เดิม** (top_k=5 → **top_k=3** สำหรับ Agent 4):
- Agent 3 (Retrieval เดิม) เคย retrieve top-k=5 chunks แล้วส่งทั้งหมดให้ Agent 4 — ปรับเป็น **retrieve 5 เพื่อ log ใน `retrieval_logs` ครบ แต่ส่งเข้า prompt ของ Agent 4 แค่ top-3 ที่ relevance_score สูงสุด** (เก็บ 5 ไว้เผื่อ debug/audit แต่ไม่ดันเข้า context)
- บังคับ chunk size ที่ใช้จริงใน prompt ไม่เกิน **350 token/ชิ้น** (เข้มกว่า 300-500 เดิมใน 14.6) เพื่อให้ตัวเลขข้างต้นแม่นยำ

**ข้อควรระวังทางวิศวกรรม**: การสลับ `num_ctx` ไปมาระหว่าง call บนโมเดลเดียวกันใน Ollama อาจทำให้เกิด reload/realloc KV cache แฝง (เพิ่ม latency เล็กน้อยตอนสลับ) — ควรทดสอบจริงก่อน ถ้า overhead สูงเกินไป ให้ fallback เป็นมาตรฐานเดียว `num_ctx=2048` สำหรับ Agent 1-4 ทั้งหมด (ซึ่งทุกตัวพอดีอยู่แล้วตามตาราง) และแยก `num_ctx=3072-4096` เฉพาะ Agent 5 (deep-verify)/Agent 8 (batch) ซึ่งเรียกไม่บ่อยพอที่จะคุ้มกับ reload overhead

## 14.9 แผนรองรับความเสี่ยงวันเดโม (Compute Fallback Plan)

**ความเสี่ยงของแผน Hybrid Compute เดิม** (Colab GPU + Secure Tunnel): Colab ตัดการเชื่อมต่ออัตโนมัติเมื่อ idle ~90 นาทีหรือครบเพดาน runtime ของ free tier, tunnel อาจหลุดระหว่างทาง, Wi-Fi สถานที่เดโมอาจไม่เสถียร — ถ้าไม่มีแผนสำรอง ระบบอาจ "ตอบไม่ได้" กลางงานนำเสนอ

**กลไกป้องกัน 3 ชั้น**:

1. **Automatic Failover ระดับ Backend**: ตั้งค่า `OLLAMA_BASE_URL_PRIMARY` (Colab/cloud) และ `OLLAMA_BASE_URL_FALLBACK` (local Ollama บนเครื่อง dev) พร้อมกัน — backend health-check endpoint หลักด้วย timeout สั้น (~2 วินาที) ก่อนทุกการเรียก LLM จริง ถ้าหลักไม่ตอบสนองภายในเวลา ให้ **สลับไปเรียก local endpoint อัตโนมัติทันที** โดยไม่ต้อง restart ระบบ — เดโมเดินต่อได้แม้ช้าลง (CPU-only) แทนที่จะ error
   ```
   OLLAMA_BASE_URL_PRIMARY=https://<colab-tunnel-url>
   OLLAMA_BASE_URL_FALLBACK=http://localhost:11434
   OLLAMA_HEALTHCHECK_TIMEOUT_MS=2000
   ```
   - บันทึกว่าแต่ละคำตอบตอบจาก endpoint ไหนลงใน `audit_log` (`event_data: {"served_by": "primary"|"fallback"}`) เพื่อตรวจสอบย้อนหลังได้หลังเดโม

2. **Local model ต้อง pre-warm ไว้ล่วงหน้า**: โหลด Qwen2.5:3B บน local Ollama ให้พร้อมอยู่ใน RAM ก่อนเริ่มเดโม (เรียก request เปล่าๆ 1 ครั้งล่วงหน้า) ไม่ให้ fallback ครั้งแรกต้องเสียเวลา cold-start โหลดโมเดลซ้ำ

3. **Operational safeguards**:
   - รัน dry-run เต็มรูปแบบด้วยคำถามชุดเดโมจริงล่วงหน้า 30-60 นาทีก่อนนำเสนอ เพื่อให้ Colab session "อุ่น" และจับปัญหาทัน
   - ใช้ **cloudflared tunnel แทน ngrok free tier** ถ้าเป็นไปได้ (ไม่มี session cap เข้มงวดเท่า ngrok free) หรือเตรียม tunnel URL สำรองไว้ล่วงหน้า
   - เผื่อแผนสุดท้าย (ultimate fallback): บันทึกวิดีโอ/ภาพหน้าจอการสาธิตแบบใช้ cloud model ไว้ล่วงหน้า 1 ชุด เผื่อกรณี Wi-Fi สถานที่เดโมใช้งานไม่ได้เลยทั้งระบบ (primary และ fallback local ก็ยังต้องพึ่งเครื่องทำงานได้ปกติ แต่วิดีโอกันกรณีเครื่อง/ไฟ/เน็ตมีปัญหาจริงๆ)

**สรุป**: ระบบไม่ควรพึ่งพา Secure Tunnel เป็นจุดเดียวที่ทำให้เดโมล่มได้ — การมี local model เป็น Plan B ที่ pre-warm ไว้พร้อมสลับอัตโนมัติ คือเกราะป้องกันหลัก ส่วน dry-run และวิดีโอสำรองคือเกราะชั้นที่ 2-3

---

**สรุปภาพรวมส่วนที่ 14**: เครื่องนี้ทำได้ครบทุก feature ที่ออกแบบไว้ในเอกสารนี้ ไม่กระทบ architecture — ใช้ Qwen2.5:3B เป็นหลัก, SQLite ตอน dev, Mock LLM mode ตอน debug logic, จำกัด top_k และ chunk size ให้พอดีกับ `num_ctx` แบบ tiered ต่อ Agent, และมีแผน automatic failover รองรับวันเดโมไม่ให้พึ่งพา Secure Tunnel เป็นจุดเดียว

---

*เอกสารนี้ใช้คู่กับไฟล์ `schema.sql` (DB Schema แบบเต็ม) — ทั้งสองไฟล์ควรเก็บไว้ที่ `docs/` ของ repo และอัปเดตพร้อมกันทุกครั้งที่มีการเปลี่ยนแปลง architecture*
