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
