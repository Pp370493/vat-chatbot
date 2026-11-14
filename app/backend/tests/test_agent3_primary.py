"""ทดสอบ Agent 3 ตามหลักการตัวบทหลัก (ใช้ embedding ปลอมแบบ n-gram เพราะไม่มี Ollama ตอนทดสอบ)"""
import hashlib
import json
import os

import numpy as np
import pytest

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "official_vat_articles.json")
DIM = 512


def fake_embedding(text: str, is_query: bool = False) -> list[float]:
    t = "".join((text or "").split())
    v = np.zeros(DIM)
    for i in range(len(t) - 2):
        v[int(hashlib.md5(t[i:i + 3].encode()).hexdigest(), 16) % DIM] += 1
    return v.tolist()


@pytest.fixture(scope="module")
def a3(monkeypatch_module):
    from app.agents import agent3_rag_retrieval as a3
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    from app.models.models import KbArticle

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(KbArticle).delete()
    for item in json.load(open(DATA, encoding="utf-8")):
        db.add(KbArticle(id=item["id"], title=item["title"], content=item["content"],
                         source_section=item["source_section"], status="approved", source="official",
                         embedding=fake_embedding(item["embedding_input"])))
    db.commit()
    db.close()
    monkeypatch_module.setattr(a3, "get_embedding", fake_embedding)
    return a3


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


QUERIES = [
    "ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20",
    "จด vat ต้องเตรียมเอกสารอะไรไปยื่น",
    "ขายของออนไลน์อยู่คอนโด ต้องยื่นจด VAT ทางไหน",
    "สร้างโรงงานยังไม่เสร็จ ขอจด VAT ล่วงหน้าได้ไหม",
    "ใครเป็นผู้ลงนามในประกาศ",
]


@pytest.mark.parametrize("q", QUERIES)
def test_only_primary_chunks_without_dbd(a3, q):
    res = a3.retrieve(q)
    assert res["chunks"], "ควรได้ผลลัพธ์"
    for c in res["chunks"]:
        assert c["chunk_id"].startswith(("VAT57_", "VAT159_")), c["chunk_id"]
        assert c["role"] == "primary"


def test_dbd_query_can_use_234(a3):
    res = a3.retrieve("จด vat พร้อมจัดตั้งบริษัทที่ DBD ต้องทำอย่างไร")
    assert any(c["chunk_id"].startswith("VAT234_") for c in res["chunks"])
    assert all(not c["chunk_id"].startswith(("VAT74_", "VAT139_", "VAT165_", "VAT214_", "VAT215_",
                                             "VAT245_", "VAT246_")) for c in res["chunks"])


def test_boilerplate_never_returned(a3):
    res = a3.retrieve("ประกาศฉบับนี้ใช้บังคับวันไหน ใครเป็นผู้ลงนาม")
    for c in res["chunks"]:
        assert not a3.is_boilerplate(c["chunk_id"], c["text"])


def test_citation_lists_amending_announcements(a3):
    res = a3.retrieve("ถ้าสรรพากรไม่อยู่ใครเซ็น ภ.พ.20")
    by_id = {c["chunk_id"]: c for c in res["chunks"]}
    assert "VAT57_ART_09" in by_id
    cit = by_id["VAT57_ART_09"]["citation"]
    assert "(ฉบับที่ 57)" in cit and "ซึ่งแก้ไขเพิ่มเติมโดยฉบับที่ 74, 139, 165, 245" in cit and "[ยื่นแบบกระดาษ]" in cit


def test_role_fallback_from_chunk_id(a3):
    assert a3.role_of("VAT57_ART_01") == "primary"
    assert a3.role_of("VAT234_ART_01") == "special"
    assert a3.role_of("VAT245_ART_02") == "amendment"
