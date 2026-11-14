"""ทดสอบ Agent 6: เคสตามข้อ 6 ต้องถูกส่งต่อ และคำถามปกติที่เอ่ยคำกำกวมต้องไม่ถูกส่งต่อ"""
import csv
import os

import pytest

from app.agents.agent6_risk_tier import assess_risk

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_dataset_vat_intent.csv")
CONF = 0.9


def _rows(group):
    with open(DATA, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r["group"] == group]


@pytest.mark.parametrize("row", _rows("HIGH_RISK_SECTION_6"), ids=lambda r: r["id"])
def test_section6_cases_are_escalated(row):
    assert assess_risk(row["query"], CONF)["tier"] != "auto_answer"


@pytest.mark.parametrize("row", _rows("IN_SCOPE_VAT"), ids=lambda r: r["id"])
def test_normal_questions_are_auto_answered(row):
    res = assess_risk(row["query"], CONF)
    assert res["tier"] == "auto_answer", res["risk_factors"]


BENIGN = [
    "มีลูกจ้าง 2 คน จด VAT ได้ไหม",
    "คนต่างชาติถือพาสปอร์ตมาเปิดร้านในไทย ต้องใช้เอกสารอะไร",
    "จ้างสำนักงานบัญชีทำบัญชีให้ ต้องจด vat เมื่อไหร่",
    "ขายของออนไลน์ไม่มีหน้าร้าน จด vat ได้ไหม",
    "เจ้าของร้านไม่ว่างไปเอง จะมอบอำนาจให้พนักงานไปยื่นแทน ต้องใช้เอกสารอะไร",
    "บริษัทต่างชาติมีตัวแทนในไทย จด vat ยังไง",
    "สรรพากรจะมาตรวจสถานที่ก่อนออก ภ.พ.20 ไหม",
    "ลูกจ้างของบริษัทไปยื่น ภ.พ.01 แทนได้ไหม ต้องมีหนังสือมอบอำนาจไหม",
    "บริษัทอยู่ตึกเดียวกับสำนักงานบัญชี แต่คนละชั้น เช่าพื้นที่เองมีสัญญาเช่า จดได้ไหม",
    "ยังไม่ได้เปิดร้าน ขอจด vat ล่วงหน้าได้ไหม",
]


@pytest.mark.parametrize("query", BENIGN)
def test_benign_mentions_are_not_escalated(query):
    res = assess_risk(query, CONF)
    assert res["tier"] == "auto_answer", res["risk_factors"]


def test_risk_factors_name_the_clause():
    res = assess_risk("ใช้ที่อยู่สำนักงานบัญชีจด VAT ได้ไหม", CONF)
    assert res["risk_factors"] == ["ข้อ 6(4) ใช้สำนักงานกฎหมาย/บัญชีของผู้อื่นเป็นสถานประกอบการ"]
