"""ทดสอบการยืนยันตัวตนและสิทธิ์ของ API (TestClient + DB ชั่วคราวจาก conftest, mock LLM, embedding ปลอม)"""
import pytest
from fastapi.testclient import TestClient

from tests.test_agent3_primary import a3, fake_embedding, monkeypatch_module  # noqa: F401  (fixtures)

PASSWORDS = {"officer@rd.go.th": "pw-officer-1", "officer2@rd.go.th": "pw-officer-2",
             "supervisor@rd.go.th": "pw-senior", "admin@rd.go.th": "pw-admin"}
ROLES = {"officer@rd.go.th": "officer", "officer2@rd.go.th": "officer",
         "supervisor@rd.go.th": "senior_officer", "admin@rd.go.th": "admin"}


@pytest.fixture(scope="module")
def client(a3, monkeypatch_module):  # noqa: F811
    from app.agents import agent5_verifier
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.main import app
    from app.models.models import StaffUser, gen_uuid
    monkeypatch_module.setattr(agent5_verifier, "get_embedding", fake_embedding)
    db = SessionLocal()
    for email, pw in PASSWORDS.items():
        if not db.query(StaffUser).filter(StaffUser.email == email).first():
            db.add(StaffUser(id=gen_uuid(), email=email, full_name=email, role=ROLES[email],
                             password_hash=hash_password(pw, iterations=1000)))
    db.commit()
    db.close()
    return TestClient(app)


def login(client, email):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORDS[email]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['session_token']}"}


def test_password_is_not_stored_in_plaintext(client):
    from app.db.session import SessionLocal
    from app.models.models import StaffUser
    db = SessionLocal()
    u = db.query(StaffUser).filter(StaffUser.email == "officer@rd.go.th").first()
    db.close()
    assert u.password_hash.startswith("pbkdf2_sha256$") and "pw-officer-1" not in u.password_hash


def test_login_rejects_wrong_password_and_role_name(client):
    assert client.post("/api/v1/auth/login", json={"email": "officer@rd.go.th", "password": "x"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "admin", "password": "pw-admin"}).status_code == 401


@pytest.mark.parametrize("method,path", [
    ("post", "/api/v1/chat/query"), ("get", "/api/v1/chat/inquiries/recent"), ("get", "/api/v1/chat/articles"),
    ("get", "/api/v1/escalations"), ("get", "/api/v1/analytics/overview"), ("get", "/api/v1/analytics/audit-logs"),
    ("get", "/api/v1/auth/users"), ("get", "/api/v1/auth/me"),
])
def test_protected_endpoints_need_a_token(client, method, path):
    r = client.post(path, json={"session_id": "s", "text": "x"}) if method == "post" else client.get(path)
    assert r.status_code == 401


def test_garbage_token_is_rejected(client):
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_officer_cannot_reach_review_or_admin(client):
    h = login(client, "officer@rd.go.th")
    assert client.get("/api/v1/escalations", headers=h).status_code == 403
    assert client.get("/api/v1/analytics/overview", headers=h).status_code == 403
    assert client.get("/api/v1/auth/users", headers=h).status_code == 403


def test_quick_switch_is_disabled_by_default(client):
    h = login(client, "officer@rd.go.th")
    assert client.post("/api/v1/auth/quick-switch", json={"role": "admin"}, headers=h).status_code == 404


def test_logout_invalidates_token(client):
    h = login(client, "officer@rd.go.th")
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 200
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_query_uses_token_user_and_history_is_private(client):
    h1, h2 = login(client, "officer@rd.go.th"), login(client, "officer2@rd.go.th")
    r = client.post("/api/v1/chat/query", headers=h1,
                    json={"session_id": "s1", "text": "ยื่นแบบ ภ.พ.30 ทุกวันที่เท่าไหร่ของเดือน", "staff_user_id": "spoof"})
    assert r.status_code == 200
    qid, conv = r.json()["query_id"], r.json()["conversation_id"]
    assert any(i["query_id"] == qid for i in client.get("/api/v1/chat/inquiries/recent", headers=h1).json())
    assert all(i["query_id"] != qid for i in client.get("/api/v1/chat/inquiries/recent", headers=h2).json())
    assert client.get(f"/api/v1/chat/query/{qid}/status", headers=h2).status_code == 404
    r = client.post("/api/v1/chat/query", headers=h2, json={"session_id": "s2", "conversation_id": conv, "text": "x"})
    assert r.status_code == 403


def test_escalation_decision_records_reviewer_from_token(client):
    officer, senior = login(client, "officer@rd.go.th"), login(client, "supervisor@rd.go.th")
    r = client.post("/api/v1/chat/query", headers=officer,
                    json={"session_id": "s3", "text": "จ้างคนขับรถมาเป็นกรรมการแทนเพื่อจด vat ยื่นที่สรรพากรพื้นที่"})
    assert r.json()["type"] == "pending_review"
    esc_id = r.json()["payload"]["escalation_id"]
    queue = client.get("/api/v1/escalations", headers=senior).json()
    case = next(c for c in queue if c["escalation_id"] == esc_id)
    assert "ข้อ 6(2)" in case["draft_text"]
    r = client.post(f"/api/v1/escalations/{esc_id}/decision", headers=senior,
                    json={"decision": "approved", "final_answer": "ok", "reviewed_by": "spoof"})
    assert r.status_code == 200
    from app.db.session import SessionLocal
    from app.models.models import Escalation, StaffUser
    db = SessionLocal()
    esc = db.query(Escalation).get(esc_id)
    reviewer = db.query(StaffUser).get(esc.reviewed_by)
    db.close()
    assert reviewer.email == "supervisor@rd.go.th"


def test_admin_analytics_range(client):
    h = login(client, "admin@rd.go.th")
    for rng in ("7d", "30d", "all"):
        r = client.get(f"/api/v1/analytics/overview?range={rng}", headers=h)
        assert r.status_code == 200 and r.json()["range"] == rng
    assert client.get("/api/v1/analytics/overview?range=1y", headers=h).status_code == 400


def test_checklist_item_saves(client):
    h = login(client, "officer@rd.go.th")
    client.post("/api/v1/chat/query", headers=h, json={"session_id": "s4", "text": "ยื่นแบบ ภ.พ.30 วันไหน"})
    r = client.post("/api/v1/chat/form-session/evaluate-checklist", headers=h, json={
        "profile": {"channel": "paper", "taxpayer_type": "individual_thai", "location_type": "rented",
                    "is_power_of_attorney": False},
        "items": [], "session_id": "fs-test-1"})
    assert r.status_code == 200
    r = client.post("/api/v1/chat/form-session/fs-test-1/checklist-item", headers=h,
                    json={"document_name": "สัญญาเช่า", "status": "received"})
    assert r.status_code == 200, r.text
    other = login(client, "officer2@rd.go.th")
    r = client.post("/api/v1/chat/form-session/fs-test-1/checklist-item", headers=other,
                    json={"document_name": "x", "status": "received"})
    assert r.status_code == 404
