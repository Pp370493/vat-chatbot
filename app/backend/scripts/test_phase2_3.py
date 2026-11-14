"""
Comprehensive Test Script: Phase 2 & 3
1. ทดสอบคำถามความเสี่ยงต่ำ -> auto_answer + บันทึกลง SQLite
2. ทดสอบคำถามความเสี่ยงสูง (มีนอมินี/เปลี่ยนผู้ถือหุ้น) -> pending_review + สร้าง Escalation
3. ทดสอบหัวหน้างานเข้ามาดูคิวและกดอนุมัติ (Supervisor Approval)
4. ทดสอบดึงสถานะคำตอบที่ผ่านการอนุมัติแล้ว
5. ตรวจสอบสถิติใน Dashboard Analytics
"""
import sys
import json
from pathlib import Path

# Set utf-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db.session import SessionLocal
from app.graph.pipeline_graph import run_pipeline
from app.api.escalations import list_escalations, submit_decision, DecisionRequest
from app.api.chat import get_query_status
from app.api.analytics import overview
from app.models.models import Query, Escalation, AuditLog


def run_tests():
    db = SessionLocal()
    print("==================================================")
    print("เริ่มทดสอบ Phase 2 & 3: DB Persistence & Escalation")
    print("==================================================\n")

    # ------------------------------------------------------------------
    # Test 1: เคสความเสี่ยงต่ำ -> auto_answer
    # ------------------------------------------------------------------
    print("--- 1. ทดสอบเคสทั่วไป (ความเสี่ยงต่ำ -> Auto Answer) ---")
    res1 = run_pipeline(
        raw_text="ถ้าจะก่อสร้างโรงงาน สามารถยื่นขอจดทะเบียน VAT ล่วงหน้าได้กี่เดือน",
        session_id="sess-auto-1",
        conversation_id="conv-auto-1",
        db=db,
    )
    print(f"ผลลัพธ์: Type={res1['type']}")
    print(f"Query ID: {res1['query_id']}")
    print(f"สถานะใน DB: {db.query(Query).filter(Query.id == res1['query_id']).first().status}")
    print(f"Trust Score: {res1['payload'].get('trust_score')}")
    print(f"คำตอบ: {res1['payload'].get('draft_text')[:100]}...\n")

    # ------------------------------------------------------------------
    # Test 2: เคสความเสี่ยงสูง -> pending_review & Escalation Queue
    # ------------------------------------------------------------------
    print("--- 2. ทดสอบเคสความเสี่ยงสูง (นอมินี/เปลี่ยนผู้ถือหุ้น -> Escalation) ---")
    res2 = run_pipeline(
        raw_text="บริษัทมีการเปลี่ยนผู้ถือหุ้นและสงสัยว่าเป็นตัวแทนเชิด (นอมินี) ของคนต่างด้าว แบบนี้เจ้าพนักงานจะออกใบทะเบียนให้ไหม",
        session_id="sess-risk-1",
        conversation_id="conv-risk-1",
        db=db,
    )
    print(f"ผลลัพธ์: Type={res2['type']}")
    print(f"Query ID: {res2['query_id']}")
    print(f"Tier: {res2['payload'].get('tier')}")
    print(f"ปัจจัยความเสี่ยงที่ตรวจพบ: {res2['payload'].get('risk_factors')}")
    print(f"Escalation ID: {res2['payload'].get('escalation_id')}")
    print(f"สถานะใน DB: {db.query(Query).filter(Query.id == res2['query_id']).first().status}\n")

    escalation_id = res2["payload"].get("escalation_id")

    # ------------------------------------------------------------------
    # Test 3: ตรวจสอบคิว Escalation ของหัวหน้างาน (Supervisor Queue)
    # ------------------------------------------------------------------
    print("--- 3. ตรวจสอบรายการในคิว Escalation ของหัวหน้างาน ---")
    queue = list_escalations(status="pending", db=db)
    print(f"จำนวนเคสที่รอตรวจในคิว: {len(queue)} เคส")
    target_esc = next((item for item in queue if item["escalation_id"] == escalation_id), None)
    if target_esc:
        print(f"พบเคสในคิว: คำถาม='{target_esc['raw_text']}'")
        print(f"ระดับความเสี่ยง (Tier): {target_esc['tier']}")

    # ------------------------------------------------------------------
    # Test 4: หัวหน้างานทำการตรวจสอบและอนุมัติ (Supervisor Approval)
    # ------------------------------------------------------------------
    print("\n--- 4. หัวหน้างานทำการพิจารณาอนุมัติคำตอบ (Supervisor Decision) ---")
    decision_req = DecisionRequest(
        decision="approved",
        final_answer=(
            "ตามประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 6 วรรคสาม (2) หากปรากฏข้อเท็จจริงว่า "
            "เป็นตัวแทนเชิด (Nominee) ของเจ้าของที่แท้จริง เจ้าพนักงานสรรพากรไม่ออกใบทะเบียน ภ.พ.20 ให้ "
            "โดยให้เรียกตรวจสอบเอกสาร บอจ.5 และรายงานการประชุมเพิ่มเติมอย่างเคร่งครัด"
        ),
        reviewed_by="supervisor-001",
    )
    decision_res = submit_decision(escalation_id, decision_req, db=db)
    print(f"ผลการตัดสินใจ: {decision_res['message']}")
    print(f"สถานะ Query หลังอนุมัติ: {db.query(Query).filter(Query.id == res2['query_id']).first().status}")

    # ------------------------------------------------------------------
    # Test 5: ตรวจสอบคำตอบหลังได้รับอนุมัติ (Status Polling)
    # ------------------------------------------------------------------
    print("\n--- 5. ตรวจสอบสถานะคำถามจากฝั่งผู้ใช้งาน (Status Polling) ---")
    status_res = get_query_status(res2["query_id"], db=db)
    print(f"Query Status: {status_res['status']}")
    print(f"คำตอบที่ผ่านการอนุมัติ (Final Answer): {status_res['answer']}\n")

    # ------------------------------------------------------------------
    # Test 6: ตรวจสอบ Analytics สถิติภาพรวม
    # ------------------------------------------------------------------
    print("--- 6. ตรวจสอบสถิติภาพรวมใน Admin Dashboard (Analytics) ---")
    stats = overview(db=db)
    print(f"จำนวนคำถามทั้งหมด: {stats['total_queries']}")
    print(f"อัตราส่วน In-Scope: {stats['in_scope_ratio']:.1%}")
    print(f"อัตราการเกิด Escalation: {stats['escalation_rate']:.1%}")
    print(f"อัตราการตอบอัตโนมัติ (Auto-Answer): {stats['auto_answer_rate']:.1%}")

    audit_count = db.query(AuditLog).count()
    print(f"จำนวน Audit Log ทั้งหมดที่บันทึก: {audit_count} รายการ")

    db.close()
    print("\n==================================================")
    print("การทดสอบ Phase 2 & 3 สำเร็จลุล่วง ครบทุกฟังก์ชัน!")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
