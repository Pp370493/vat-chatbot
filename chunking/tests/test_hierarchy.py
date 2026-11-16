"""ทดสอบลำดับชั้นตัวบทด้วยตัวอย่างจริง (สร้างใหม่จาก chunk ทุกครั้ง)"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import build_hierarchy as bh  # noqa: E402


@pytest.fixture(scope="module")
def H():
    chunks = json.load(open(bh.COMBINED, encoding="utf-8"))
    st, problems = bh.build(chunks)
    unresolved = bh.resolve_refs(st)
    cov = bh.check_coverage(st, chunks)
    refs = {}
    for e in st.edges:
        if e["kind"] == "refers_to":
            refs.setdefault(e["s"], set()).add(e["t"])
    amends = {(e["s"], e["t"]) for e in st.edges if e["kind"] == "amends"}
    return st, unresolved, cov, refs, amends, problems


def kids(st, nid, level=None):
    return [c for c in st.children(nid) if level is None or st.nodes[c]["level"] == level]


def test_all_text_is_kept(H):
    _, _, cov, _, _, problems = H
    assert not problems
    assert all(r["coverage"] >= 0.995 for r in cov), [r for r in cov if r["coverage"] < 0.995]


def test_no_unresolved_references(H):
    assert H[1] == []


def test_57_article5_clauses_and_items(H):
    st = H[0]
    # ข้อ 5 ประกอบกลับจาก 05_A/B/C: วรรคหนึ่งนำอนุ (1)–(5) และมีวรรคปิดท้ายเพียงวรรคเดียว
    p1 = "VAT57/5/p1"
    assert [st.nodes[c]["key"] for c in kids(st, p1, "clause")] == ["1", "2", "3", "4", "5"]
    assert [st.nodes[c]["key"] for c in kids(st, "VAT57/5/3", "item")] == ["ก", "ข", "ค", "ง"]
    assert len(kids(st, "VAT57/5", "paragraph")) == 2
    assert "แสดงเอกสารตัวจริง" in st.nodes["VAT57/5/p2"]["own_text"]


def test_paragraph_inside_item(H):
    st = H[0]
    assert "อาคารชุด" in st.nodes["VAT57/5/5/ก/p2"]["own_text"]
    assert "อาคารชุด" not in st.nodes["VAT57/5/5/ค"]["own_text"]


def test_list_hangs_under_leading_paragraph(H):
    st = H[0]
    assert st.nodes["VAT57/6/1"]["parent"] == "VAT57/6/p3"     # เหตุ (1)–(6) อยู่ใต้วรรคสามของข้อ 6


def test_159_article5_4_references(H):
    refs = H[3]
    assert {"VAT159/5/1", "VAT159/5/2", "VAT159/5/3"} <= refs["VAT159/5/4"]
    assert "VAT159/5/1/ก" in refs["VAT159/5/4/ค"]
    assert "VAT159/5/4/ก" in refs["VAT159/5/4/ก/p2"]          # 'ตามวรรคหนึ่ง' ในย่อย (ก)
    assert {"VAT159/5/1/ก", "VAT159/5/4"} <= refs["VAT159/5/p3"]


def test_range_reference_is_not_a_clause(H):
    st = H[0]
    assert "ตาม (1) ถึง (3)" in st.nodes["VAT57/5/5"]["own_text"]
    assert "VAT57/5/5/1" not in st.nodes


def test_cross_article_and_external_references(H):
    refs = H[3]
    assert "VAT159/5/1/ก" in refs["VAT159/6/8"]
    assert "VAT57/2" in refs["VAT57/7/2"]
    assert "EXT/ประมวลรัษฎากร/ม.82/16" in refs["VAT57/7/2"]


def test_amendments_point_to_the_changed_level(H):
    amends = H[4]
    assert ("VAT215/2/ใหม่", "VAT57/5/5/ก") in amends
    assert ("VAT215/1/ใหม่", "VAT57/5/2") in amends
    assert ("VAT246/4/ใหม่", "VAT159/6/8") in amends
    assert ("VAT139/1/ใหม่", "VAT57/4/p1") in amends
    assert ("VAT246/1/ใหม่", "VAT159/1/p2") in amends
