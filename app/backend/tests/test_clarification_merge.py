from app.agents import agent6_risk_tier as a6
from app.graph.pipeline_graph import detect_channel, merge_clarification_reply

CH = [{"resolved_query": "จด vat ต้องใช้เอกสารอะไร",
       "answer_summary": "สอบถามช่องทางการยื่นจดทะเบียน VAT (กระดาษ ฉบับ 57 / อินเทอร์เน็ต ฉบับ 159 / DBD ฉบับ 234)"}]
PU = [{"resolved_query": "ยื่นแบบกระดาษต้องใช้อะไร",
       "answer_summary": "สอบถามยืนยันประเภทการยื่นแบบ (ภ.พ.01 / ภ.พ.09 / ภ.พ.30 / ภ.ง.ด.)"}]


def test_detect_channel():
    assert detect_channel("ยื่นแบบกระดาษ") == "paper"
    assert detect_channel("ยื่นผ่านเน็ต") == "internet"
    assert detect_channel("จดพร้อม DBD") == "dbd"
    assert detect_channel("ต้องใช้เอกสารอะไร") is None


def test_merge_channel_reply():
    assert merge_clarification_reply("กระดาษค่ะ", CH) == \
        "จด vat ต้องใช้เอกสารอะไร (ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ ตามประกาศฉบับที่ 57)"
    assert "ฉบับที่ 159" in merge_clarification_reply("ออนไลน์", CH)
    assert merge_clarification_reply("ไม่แน่ใจ", CH) is None
    assert merge_clarification_reply("กระดาษ", []) is None
    assert merge_clarification_reply("กระดาษ", [{"resolved_query": "x", "answer_summary": "คำตอบปกติ"}]) is None


def test_merge_purpose_reply():
    assert merge_clarification_reply("ภ.พ.01", PU).startswith("ยื่นแบบกระดาษต้องใช้อะไร (ยื่นคำขอจดทะเบียน")
    assert merge_clarification_reply("ต้องการยื่นแบบ ภ.พ.30", PU) is None


ART6 = ("ข้อ 6 ...ไม่ให้เจ้าพนักงานสรรพากรออกใบทะเบียน\n(1) แสดงเอกสารเป็นเท็จ\n"
        "(2) เป็นตัวแทนเชิดของเจ้าของกิจการที่แท้จริง\n(6) เคยถูกเพิกถอน โดยมูลเหตุจากกรณีตาม (1) ถึง (5)")


def test_clause_text():
    assert a6.clause_text(ART6, "2") == "เป็นตัวแทนเชิดของเจ้าของกิจการที่แท้จริง"
    assert a6.clause_text(ART6, "6").endswith("(1) ถึง (5)")
    assert a6.clause_text(ART6, "8") == ""


def test_build_review_brief():
    risk = a6.assess_risk("จ้างคนมาเป็นกรรมการแทน จะโดนจับไหม", 1.0)
    art6 = [{"chunk_id": "VAT57_ART_06", "text": ART6, "citation": "ประกาศ (ฉบับที่ 57) ข้อ 6"}]
    chunks = [{"chunk_id": "VAT57_ART_05_B", "citation": "ประกาศ (ฉบับที่ 57) ข้อ 5", "text": "เอกสาร..."}]
    out = a6.build_review_brief("คำถามทดสอบ", chunks, risk, art6)
    t = out["draft_text"]
    assert "คำถามทดสอบ" in t and "ประกาศ (ฉบับที่ 57) ข้อ 6(2): เป็นตัวแทนเชิด" in t
    assert "ร่างคำตอบเบื้องต้น" in t and "ข้อ 5" in t
    assert {c["source_section"] for c in out["citations"]} >= {"ประกาศ (ฉบับที่ 57) ข้อ 6", "ประกาศ (ฉบับที่ 57) ข้อ 5"}
    assert out["answer_summary"].startswith("ส่งหัวหน้างานตรวจ")


def test_build_review_brief_without_clause():
    risk = {"risk_factors": [], "tier": "senior_review", "risk_score": 0, "trust_score": 0.2}
    out = a6.build_review_brief("q", [], risk, [])
    assert "ไม่พบเหตุตามข้อ 6" in out["draft_text"]
