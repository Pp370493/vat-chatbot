"""
Agent 8: Knowledge & Reporting Batch Agent (รันกลางคืน, แยกจาก flow หลัก)
อ้างอิง: VAT_CoPilot_IS_Full_Handoff.md ส่วนที่ 4

รัน 3 งานจาก embedding clustering ชุดเดียวกัน:
1. KB Growth -> kb_growth_clusters (รอ Admin approve -> kb_articles)
2. C2: รายงานคำถามยอดนิยมรายสัปดาห์ -> weekly_question_reports
3. C3: FAQ/คู่มือความรู้ -> knowledge_manual_entries (รอ Admin approve)

num_ctx=4096 (ดู 14.8 — ไม่แข่ง RAM กับ real-time traffic)
TODO: เรียกจาก cron/scheduler (เช่น APScheduler) วันละ 1 ครั้งตอนกลางคืน
"""
from app.core.ollama_client import generate


def run_nightly_batch(escalated_queries: list[dict]) -> dict:
    # TODO: ทำ embedding clustering จริงบน escalated_queries
    # threshold ความถี่ >=5 ครั้ง ถึงจะเสนอ KB article ใหม่

    return {
        "kb_clusters": [],
        "weekly_report": {"week_start_date": None, "top_questions": []},
        "manual_entries": [],
    }
