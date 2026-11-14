-- ============================================================
-- Enterprise Tax Co-Pilot & Intelligence Platform
-- DB Schema (PostgreSQL)
-- อ้างอิงตาม State Flow: NEW -> SCOPE_CHECKED -> RETRIEVED -> DRAFTED
--                        -> VERIFIED -> TIER_ASSIGNED -> ANSWERED -> LOGGED
-- ============================================================

-- ------------------------------------------------------------
-- ENUM TYPES
-- ------------------------------------------------------------

CREATE TYPE staff_role AS ENUM ('officer', 'senior_officer', 'admin');

CREATE TYPE query_status AS ENUM (
    'new',
    'scope_checked',
    'redirected',          -- out-of-scope, จบ flow
    'retrieved',
    'drafted',
    'verified',
    'tier_assigned',
    'pending_review',      -- รอ officer/senior review
    'answered',            -- จบ flow (ไม่ว่า auto หรือผ่านการ review)
    'logged'
);

CREATE TYPE sub_intent AS ENUM ('qa', 'form_assist', 'edge_case');

CREATE TYPE tier_level AS ENUM ('auto_answer', 'officer_review', 'senior_review');

CREATE TYPE review_decision AS ENUM ('approved', 'edited', 'rejected');

CREATE TYPE kb_article_status AS ENUM ('draft', 'approved', 'archived');

-- Final Scope (A5): แยกชั้นความน่าเชื่อถือของแหล่งความรู้ชัดเจน
-- 'official'      = ประกาศ/ข้อหารือที่มีหลักฐานยืนยัน ใช้ตอบได้ทันทีเมื่อ status='approved'
-- 'experiential'  = ความรู้จากประสบการณ์เจ้าหน้าที่ ต้องผ่าน Admin approve เท่านั้นก่อนถูกใช้อ้างอิง
-- 'auto_generated'= ร่างจาก Agent 8 (Knowledge Growth) รอ Admin approve เช่นกัน
CREATE TYPE kb_article_source AS ENUM ('official', 'experiential', 'auto_generated');

-- Final Scope (A3): สถานะของแต่ละรายการเอกสารใน Checklist ที่เจ้าหน้าที่ทำเครื่องหมายเอง
CREATE TYPE checklist_item_status AS ENUM ('pending', 'received', 'missing', 'not_applicable');

-- ------------------------------------------------------------
-- 1. staff_users
-- เจ้าหน้าที่หน้างาน / เจ้าหน้าที่รุ่นพี่ / admin
-- ------------------------------------------------------------
CREATE TABLE staff_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(200) UNIQUE NOT NULL,
    password_hash   VARCHAR(300) NOT NULL,           -- Final Scope: ต้องยืนยันตัวตนก่อนเข้าระบบเสมอ
    role            staff_role NOT NULL DEFAULT 'officer',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 1b. auth_sessions  (Final Scope — ใหม่)
-- จัดการ session หลัง login สำหรับทั้ง 3 role
-- ------------------------------------------------------------
CREATE TABLE auth_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_user_id   UUID NOT NULL REFERENCES staff_users(id) ON DELETE CASCADE,
    session_token   VARCHAR(500) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_auth_sessions_token ON auth_sessions(session_token);

-- ------------------------------------------------------------
-- 2. departments
-- ปลายทางสำหรับ Out-of-Scope Router (Agent 2)
-- ------------------------------------------------------------
CREATE TABLE departments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,           -- เช่น "กองคืนภาษี"
    topic_keywords  TEXT[] NOT NULL DEFAULT '{}',    -- ใช้ช่วย match หมวดคำถาม
    contact_channel VARCHAR(300),                    -- เบอร์โทร/ลิงก์/ระบบ e-Filing
    description     TEXT
);

-- ------------------------------------------------------------
-- 3. case_templates
-- Case library สำหรับ Checklist Assistant Agent (Agent 7, Final Scope)
-- ------------------------------------------------------------
CREATE TABLE case_templates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(200) NOT NULL,       -- เช่น "เปลี่ยนผู้ถือหุ้นเกิน 50%"
    description         TEXT,
    decision_tree       JSONB NOT NULL DEFAULT '{}', -- เงื่อนไขคำถาม-คำตอบแบบ interview
    required_documents  JSONB NOT NULL DEFAULT '[]', -- checklist เอกสารของเคสนี้
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 3b. conversations  (Multi-turn Scope — ใหม่)
-- ติดตาม session การสนทนาต่อเนื่อง — Sliding Window ไม่เกิน 5 เทิร์นล่าสุด
-- ------------------------------------------------------------
CREATE TABLE conversations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_user_id       UUID NOT NULL REFERENCES staff_users(id),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_message_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 4. kb_articles
-- คลังความรู้ที่ใช้ index เข้า ChromaDB จริง
-- Final Scope (A5): Agent 3 (RAG Retrieval) ค้นหาเฉพาะ status='approved' เท่านั้น
-- และ source='experiential' ต้องผ่าน Admin approve ก่อนถึงจะถูกดึงมาใช้อ้างอิงได้
-- ความคงที่ของคำตอบ (เดียวกันถาม = เดียวกันตอบ) อาศัยการที่ Agent 3 ดึงจาก
-- approved content set เดียวกันเสมอ ไม่ปล่อยให้ LLM เติมความรู้นอกเอกสาร
-- ------------------------------------------------------------
CREATE TABLE kb_articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(300) NOT NULL,
    content         TEXT NOT NULL,
    source_section  VARCHAR(200),                    -- เช่น "มาตรา 85/1"
    source          kb_article_source NOT NULL DEFAULT 'official',
    status          kb_article_status NOT NULL DEFAULT 'draft',
    chroma_vector_id VARCHAR(200),                    -- reference ไปยัง ChromaDB embedding
    created_by      UUID REFERENCES staff_users(id),
    approved_by     UUID REFERENCES staff_users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at     TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- 5. queries
-- ตารางหลัก: 1 แถว = 1 คำถามจากผู้ใช้ (ตัว state ไล่ตาม query_status)
-- Multi-turn Scope: conversation_id/turn_number ผูกกับ conversations (sliding window ≤5 เทิร์น)
-- resolved_query = คำถามหลัง coreference resolution (ใช้เป็นหน่วย consistency guarantee ของ A5
--   แทน raw_text ดิบ — ดูหมายเหตุใน Agent 3)
-- answer_summary = คำตอบสรุป 1 ประโยคต่อเทิร์น (Summary-Truncate แบบเข้ม) ใช้เป็น context
--   ให้เทิร์นถัดไปแทนการเก็บ draft_answer เต็ม — ประหยัด token และลดความเสี่ยง
--   "AI สรุปคำตอบของ AI เอง" ซ้อนชั้น
-- ------------------------------------------------------------
CREATE TABLE queries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      VARCHAR(200) NOT NULL,           -- ผูกกับ session ฝั่ง frontend
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    turn_number     INTEGER,                         -- ลำดับเทิร์นในบทสนทนา (1-based)
    raw_text        TEXT NOT NULL,
    resolved_query  TEXT,                            -- ผลลัพธ์ coreference resolution จาก Agent 3
    answer_summary  VARCHAR(500),                     -- สรุป 1 ประโยค เก็บไว้เป็น context เทิร์นถัดไปเท่านั้น
    sub_intent      sub_intent,
    in_scope        BOOLEAN,
    scope_confidence NUMERIC(4,3),                   -- ผลจาก Agent 1
    status          query_status NOT NULL DEFAULT 'new',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_queries_conversation ON queries(conversation_id, turn_number);

CREATE INDEX idx_queries_status ON queries(status);
CREATE INDEX idx_queries_session ON queries(session_id);

-- ------------------------------------------------------------
-- 6. out_of_scope_routes
-- ผลลัพธ์ของ Agent 2 เมื่อ queries.in_scope = false
-- ------------------------------------------------------------
CREATE TABLE out_of_scope_routes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    matched_topic   VARCHAR(200) NOT NULL,           -- เช่น "ขอคืนภาษี"
    matched_via     VARCHAR(20) NOT NULL DEFAULT 'both', -- 'keyword' | 'llm' | 'both' (Final Scope: เช็คคู่กันเสมอ)
    department_id   UUID REFERENCES departments(id),
    redirect_message TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 7. retrieval_logs
-- ผลลัพธ์ของ Agent 3 (RAG Retrieval)
-- Multi-turn Scope: rewritten_query = resolved_query (coreference resolution ผ่านบริบท ≤5 เทิร์น)
-- ขั้นตอนนี้ต้องเรียก LLM ด้วย temperature=0 (หรือใกล้ 0 ที่สุด) เท่านั้น เพื่อให้การ resolve
-- คำถามเดียวกันในบริบทเดียวกัน ได้ resolved_query เดียวกันทุกครั้ง (deterministic ที่สุดเท่าที่ทำได้)
-- — เป็นเงื่อนไขจำเป็นก่อนที่ A5 consistency guarantee ระดับ resolved query จะมีความหมาย
-- ------------------------------------------------------------
CREATE TABLE retrieval_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id            UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    rewritten_query     TEXT,
    rewrite_temperature NUMERIC(3,2) DEFAULT 0.00,    -- บันทึกไว้ audit ว่าใช้ temperature เท่าไหร่จริง
    retrieved_chunks    JSONB NOT NULL DEFAULT '[]', -- [{chunk_id, text, source_section}]
    relevance_scores    JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 8. draft_answers
-- ผลลัพธ์ของ Agent 4 (Responder)
-- ------------------------------------------------------------
CREATE TABLE draft_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    draft_text      TEXT NOT NULL,
    citations       JSONB NOT NULL DEFAULT '[]',     -- [{text_span, source_section}]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 9. verification_scores
-- ผลลัพธ์ของ Agent 5 (Verifier / Self-Reflection)
-- ------------------------------------------------------------
CREATE TABLE verification_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_answer_id     UUID NOT NULL REFERENCES draft_answers(id) ON DELETE CASCADE,
    confidence_score    NUMERIC(4,3) NOT NULL,       -- 0.000 - 1.000
    ungrounded_claims   JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 10. risk_assessments
-- ผลลัพธ์ของ Agent 6 (Risk & Tier Decision)
-- ------------------------------------------------------------
CREATE TABLE risk_assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    risk_score      NUMERIC(4,3) NOT NULL,
    risk_factors    JSONB NOT NULL DEFAULT '[]',     -- เช่น ["cross_border","shareholder_change"]
    trust_score     NUMERIC(4,3) NOT NULL,           -- confidence * (1 - risk_score)
    tier            tier_level NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 11. escalations
-- คิวตรวจสอบของ Agent 6 -> Human (officer/senior)
-- ------------------------------------------------------------
CREATE TABLE escalations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    tier            tier_level NOT NULL,
    assigned_to     UUID REFERENCES staff_users(id),
    decision        review_decision,
    final_answer    TEXT,
    reviewed_by     UUID REFERENCES staff_users(id),
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_escalations_pending ON escalations(decision) WHERE decision IS NULL;

-- ------------------------------------------------------------
-- 12. kb_growth_clusters
-- ผลลัพธ์ batch job ของ Agent 8 (Knowledge & Reporting Batch Agent, Final Scope)
-- รันคู่กับ weekly_question_reports (C2) และ knowledge_manual_entries (C3) ในรอบ batch เดียวกัน
-- ------------------------------------------------------------
CREATE TABLE kb_growth_clusters (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_topic       VARCHAR(300) NOT NULL,
    matched_query_ids   UUID[] NOT NULL DEFAULT '{}',
    frequency_count     INTEGER NOT NULL DEFAULT 0,
    proposed_article_id UUID REFERENCES kb_articles(id),
    status              VARCHAR(30) NOT NULL DEFAULT 'pending_review', -- pending_review/approved/dismissed
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 13. audit_log
-- บันทึกทุก event ของทุก agent สำหรับ Feature 7 (Compliance)
-- ------------------------------------------------------------
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        UUID REFERENCES queries(id) ON DELETE SET NULL,
    event_type      VARCHAR(100) NOT NULL,           -- เช่น "scope_checked","tier_assigned","approved"
    event_data      JSONB NOT NULL DEFAULT '{}',
    actor_type      VARCHAR(20) NOT NULL,            -- "system" | "staff"
    actor_id        UUID REFERENCES staff_users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_query ON audit_log(query_id);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);

-- ------------------------------------------------------------
-- 14. form_assistance_sessions
-- session ของ Guided Interview (Agent 7) แยกจาก queries หลัก
-- เพราะเป็นบทสนทนาหลายรอบ ไม่ใช่ query เดียวจบ
-- ------------------------------------------------------------
CREATE TABLE form_assistance_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id            UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    matched_case_id     UUID REFERENCES case_templates(id),
    conversation_log    JSONB NOT NULL DEFAULT '[]', -- [{question, answer}] -- external state (slot-filling)
    is_complete         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 15. document_checklist_items  (Final Scope — ใหม่, แทนที่ final_checklist เดิม)
-- A3: Checklist Assistant แบบ Human-Controlled
-- AI generate รายการเริ่มต้นจาก case_templates.required_documents
-- แต่ "เจ้าหน้าที่" เป็นผู้ทำเครื่องหมายสถานะเองเสมอ ระบบแค่สรุปว่าอะไรยังขาด
-- ------------------------------------------------------------
CREATE TABLE document_checklist_items (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_assistance_session_id UUID NOT NULL REFERENCES form_assistance_sessions(id) ON DELETE CASCADE,
    document_name           VARCHAR(300) NOT NULL,
    status                   checklist_item_status NOT NULL DEFAULT 'pending',
    marked_by                UUID REFERENCES staff_users(id),  -- เจ้าหน้าที่ที่ทำเครื่องหมาย (ต้องเป็นคน ไม่ใช่ AI)
    marked_at                TIMESTAMPTZ,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_checklist_items_session ON document_checklist_items(form_assistance_session_id);

-- ------------------------------------------------------------
-- 16. weekly_question_reports  (Final Scope — ใหม่)
-- C2: รายงานคำถามยอดนิยมรายสัปดาห์ — batch กลางคืนวันละครั้ง
-- Admin เห็นผลในวันทำการถัดไป (ไม่ real-time)
-- ------------------------------------------------------------
CREATE TABLE weekly_question_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start_date     DATE NOT NULL,
    week_end_date       DATE NOT NULL,
    top_questions       JSONB NOT NULL DEFAULT '[]', -- [{question_pattern, count, in_scope}]
    in_scope_ratio      NUMERIC(4,3),
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now()  -- รันตอนกลางคืน
);

CREATE INDEX idx_weekly_reports_week ON weekly_question_reports(week_start_date);

-- ------------------------------------------------------------
-- 17. knowledge_manual_entries  (Final Scope — ใหม่, แทนที่ Reasoning Trace Mode เดิม)
-- C3: FAQ / คู่มือความรู้ Generator — ใช้ฝึกอบรมเจ้าหน้าที่เก่า-ใหม่
-- ใช้ batch job เดียวกับ C2 (Agent 8) ประมวลผลข้อมูลชุดเดียวกัน
-- ------------------------------------------------------------
CREATE TABLE knowledge_manual_entries (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                   VARCHAR(300) NOT NULL,
    content                 TEXT NOT NULL,
    source_query_ids        UUID[] NOT NULL DEFAULT '{}',  -- คำถามต้นทางที่ใช้สรุป
    status                  VARCHAR(30) NOT NULL DEFAULT 'draft', -- draft/published
    approved_by             UUID REFERENCES staff_users(id),
    approved_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
