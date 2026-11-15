"""ทดสอบทั้งเส้นทาง run_pipeline ด้วย mock LLM (USE_MOCK_LLM=true) และ embedding ปลอม"""
import pytest

from tests.test_agent3_primary import a3, fake_embedding, monkeypatch_module  # noqa: F401  (fixtures)


@pytest.fixture(scope="module")
def pipeline(a3, monkeypatch_module):  # noqa: F811
    from app.agents import agent5_verifier
    from app.graph import pipeline_graph
    monkeypatch_module.setattr(agent5_verifier, "get_embedding", fake_embedding)
    return pipeline_graph


def test_authority_question_answered_with_amendment_citation(pipeline):
    res = pipeline.run_pipeline("ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20", session_id="t1")
    assert res["type"] == "answer"
    cites = " ".join(c["source_section"] for c in res["payload"]["citations"])
    assert "ซึ่งแก้ไขเพิ่มเติมโดยฉบับที่" in cites
    assert all(a["id"].startswith(("VAT57_", "VAT159_")) for a in res["payload"]["relevant_articles"])


def test_channel_is_asked_when_unclear(pipeline):
    res = pipeline.run_pipeline("จด vat ต้องเตรียมเอกสารอะไรไปยื่น", session_id="t2")
    assert res["type"] == "clarification"


def test_nominee_case_goes_to_review_with_clause_label(pipeline):
    res = pipeline.run_pipeline("จ้างคนขับรถมาเป็นกรรมการแทนเพื่อจด vat ให้ ภ.พ.20 ออกได้ไหม", session_id="t3")
    assert res["type"] == "pending_review"
    assert any("ข้อ 6(2)" in f for f in res["payload"]["risk_factors"])


def test_out_of_scope_is_redirected(pipeline):
    res = pipeline.run_pipeline("ยื่นแบบ ภ.พ.30 ทุกวันที่เท่าไหร่ของเดือน", session_id="t4")
    assert res["type"] == "redirect"


def _query_rec(query_id):
    from app.db.session import SessionLocal
    from app.models.models import DraftAnswer, Query
    db = SessionLocal()
    try:
        return db.query(Query).get(query_id), db.query(DraftAnswer).filter(DraftAnswer.query_id == query_id).first()
    finally:
        db.close()


def test_channel_reply_is_merged_with_original_question(pipeline):
    first = pipeline.run_pipeline("จด vat ต้องเตรียมเอกสารอะไรไปยื่น", session_id="t5")
    assert first["type"] == "clarification"
    res = pipeline.run_pipeline("ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ (ฉบับที่ 57)", session_id="t5",
                                conversation_id=first["conversation_id"])
    assert res["type"] == "answer"
    assert "เตรียมเอกสาร" in res["resolved_query"] and "ฉบับที่ 57" in res["resolved_query"]
    ids = [a["id"] for a in res["payload"]["relevant_articles"]]
    assert ids and ids[0] != "VAT57_ART_09", ids
    q, _ = _query_rec(res["query_id"])
    assert q.raw_text.startswith("ยื่นแบบกระดาษ")  # เก็บข้อความที่ผู้ใช้พิมพ์จริง


def test_internet_reply_is_merged(pipeline):
    first = pipeline.run_pipeline("จด vat ต้องเตรียมเอกสารอะไรไปยื่น", session_id="t6")
    res = pipeline.run_pipeline("ยื่นผ่านอินเทอร์เน็ต www.rd.go.th (ฉบับที่ 159)", session_id="t6",
                                conversation_id=first["conversation_id"])
    assert res["type"] == "answer"
    assert "ฉบับที่ 159" in res["resolved_query"]


def test_purpose_reply_pp01_is_merged(pipeline):
    first = pipeline.run_pipeline("ยื่นแบบกระดาษต้องใช้เอกสารอะไร", session_id="t7")
    assert first["payload"].get("clarification_type") == "purpose"
    res = pipeline.run_pipeline("ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มใหม่ (แบบ ภ.พ.01)", session_id="t7",
                                conversation_id=first["conversation_id"])
    assert res["type"] == "answer"
    assert "ใช้เอกสารอะไร" in res["resolved_query"]


def test_advance_registration_skips_channel_question(pipeline):
    res = pipeline.run_pipeline("จะเปิดร้านอาหารอีก 4 เดือนข้างหน้า ขอจด ภ.พ.01 ล่วงหน้าได้ไหม", session_id="t8")
    assert res["type"] == "answer"


def test_escalation_skips_llm_and_builds_brief(pipeline, monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("ไม่ควรเรียก LLM สำหรับเคสที่ต้องส่งตรวจแน่นอน")
    monkeypatch.setattr(pipeline.a4, "respond", boom)
    res = pipeline.run_pipeline("จ้างคนขับรถมาเป็นกรรมการแทนเพื่อจด vat ยื่นที่สรรพากรพื้นที่", session_id="t9")
    assert res["type"] == "pending_review"
    assert res["payload"]["draft_text"] == ""  # ผู้ถามไม่เห็นร่าง
    _, draft = _query_rec(res["query_id"])
    assert "ข้อ 6(2)" in draft.draft_text
    assert "ตัวแทนเชิด" in draft.draft_text and "(ฉบับที่ 57)" in draft.draft_text
    assert "ร่างคำตอบเบื้องต้น" in draft.draft_text
    assert any("ฉบับที่ 57" in c["source_section"] for c in draft.citations)
