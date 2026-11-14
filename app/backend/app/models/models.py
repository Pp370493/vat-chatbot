"""
SQLAlchemy ORM models — ตรงกับ schema.sql (PostgreSQL DDL ฉบับเต็ม)
ไฟล์นี้คือ dev-friendly version สำหรับ SQLite (ใช้ String เป็น UUID/Enum
แทน native PostgreSQL types) ดู schema.sql ใน docs/ สำหรับ production DDL จริง

uuid เป็น String(36) generate จาก uuid.uuid4() ที่ app-layer เสมอ (portable
schema ตาม Hardware Optimization Guide 14.3) ไม่ใช้ gen_random_uuid()
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, DateTime, JSON, ForeignKey
)
from app.db.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------- 1. staff_users
class StaffUser(Base):
    __tablename__ = "staff_users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(300), nullable=False)
    role = Column(String(20), nullable=False, default="officer")  # officer|senior_officer|admin
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------------- 1b. auth_sessions
class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    staff_user_id = Column(String(36), ForeignKey("staff_users.id"), nullable=False)
    session_token = Column(String(500), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


# ---------------------------------------------------------------- 2. departments
class Department(Base):
    __tablename__ = "departments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    topic_keywords = Column(JSON, default=list)   # ["คืนภาษี", "refund", ...]
    contact_channel = Column(String(300))
    description = Column(Text)


# ---------------------------------------------------------------- 3. case_templates
class CaseTemplate(Base):
    __tablename__ = "case_templates"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    decision_tree = Column(JSON, default=dict)
    required_documents = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------------- 3b. conversations
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    staff_user_id = Column(String(36), ForeignKey("staff_users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- 4. kb_articles
class KbArticle(Base):
    __tablename__ = "kb_articles"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    source_section = Column(String(200))
    source = Column(String(20), default="official")  # official|experiential|auto_generated
    status = Column(String(20), default="draft")       # draft|approved|archived
    chroma_vector_id = Column(String(200))
    embedding = Column(JSON, nullable=True)
    created_by = Column(String(36), ForeignKey("staff_users.id"))
    approved_by = Column(String(36), ForeignKey("staff_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)


# ---------------------------------------------------------------- 5. queries
class Query(Base):
    __tablename__ = "queries"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    session_id = Column(String(200), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"))
    turn_number = Column(Integer)
    raw_text = Column(Text, nullable=False)
    resolved_query = Column(Text)
    answer_summary = Column(String(500))
    sub_intent = Column(String(20))       # qa|form_assist|edge_case
    in_scope = Column(Boolean)
    scope_confidence = Column(Numeric(4, 3))
    status = Column(String(30), default="new")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------ 6. out_of_scope_routes
class OutOfScopeRoute(Base):
    __tablename__ = "out_of_scope_routes"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False)
    matched_topic = Column(String(200), nullable=False)
    matched_via = Column(String(20), default="both")  # keyword|llm|both
    department_id = Column(String(36), ForeignKey("departments.id"))
    redirect_message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------------ 7. retrieval_logs
class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False)
    rewritten_query = Column(Text)
    rewrite_temperature = Column(Numeric(3, 2), default=0.00)
    retrieved_chunks = Column(JSON, default=list)
    relevance_scores = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------------- 8. draft_answers
class DraftAnswer(Base):
    __tablename__ = "draft_answers"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False)
    draft_text = Column(Text, nullable=False)
    citations = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


# -------------------------------------------------------- 9. verification_scores
class VerificationScore(Base):
    __tablename__ = "verification_scores"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    draft_answer_id = Column(String(36), ForeignKey("draft_answers.id"), nullable=False)
    confidence_score = Column(Numeric(4, 3), nullable=False)
    ungrounded_claims = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------- 10. risk_assessments
class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False)
    risk_score = Column(Numeric(4, 3), nullable=False)
    risk_factors = Column(JSON, default=list)
    trust_score = Column(Numeric(4, 3), nullable=False)
    tier = Column(String(20), nullable=False)  # auto_answer|officer_review|senior_review
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- 11. escalations
class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False)
    tier = Column(String(20), nullable=False)
    assigned_to = Column(String(36), ForeignKey("staff_users.id"))
    decision = Column(String(20))  # approved|edited|rejected
    final_answer = Column(Text)
    reviewed_by = Column(String(36), ForeignKey("staff_users.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------- 12. kb_growth_clusters
class KbGrowthCluster(Base):
    __tablename__ = "kb_growth_clusters"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    cluster_topic = Column(String(300), nullable=False)
    matched_query_ids = Column(JSON, default=list)
    frequency_count = Column(Integer, default=0)
    proposed_article_id = Column(String(36), ForeignKey("kb_articles.id"))
    status = Column(String(30), default="pending_review")
    created_at = Column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------------------ 13. audit_log
class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"))
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, default=dict)
    actor_type = Column(String(20), nullable=False)  # system|staff
    actor_id = Column(String(36), ForeignKey("staff_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------- 14. form_assistance_sessions
class FormAssistanceSession(Base):
    __tablename__ = "form_assistance_sessions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_id = Column(String(36), ForeignKey("queries.id"), nullable=False)
    matched_case_id = Column(String(36), ForeignKey("case_templates.id"))
    conversation_log = Column(JSON, default=list)  # [{question, answer}]
    is_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ------------------------------------------------- 15. document_checklist_items
class DocumentChecklistItem(Base):
    __tablename__ = "document_checklist_items"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    form_assistance_session_id = Column(
        String(36), ForeignKey("form_assistance_sessions.id"), nullable=False
    )
    document_name = Column(String(300), nullable=False)
    status = Column(String(20), default="pending")  # pending|received|missing|not_applicable
    marked_by = Column(String(36), ForeignKey("staff_users.id"))  # ต้องเป็นคน ไม่ใช่ AI
    marked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------- 16. weekly_question_reports
class WeeklyQuestionReport(Base):
    __tablename__ = "weekly_question_reports"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)
    top_questions = Column(JSON, default=list)  # [{question_pattern, count, in_scope}]
    in_scope_ratio = Column(Numeric(4, 3))
    generated_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------- 17. knowledge_manual_entries
class KnowledgeManualEntry(Base):
    __tablename__ = "knowledge_manual_entries"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    source_query_ids = Column(JSON, default=list)
    status = Column(String(30), default="draft")  # draft|published
    approved_by = Column(String(36), ForeignKey("staff_users.id"))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
