import urllib.request
import json
import sys

def test(text):
    data = json.dumps({"session_id": "test", "text": text}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8000/api/v1/chat/query", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            resp = json.loads(res.read().decode("utf-8"))
            print("TYPE:", resp.get("type"))
            payload = resp.get("payload", {})
            print("IS_CLARIFICATION:", payload.get("is_clarification"))
            print("DRAFT_TEXT:\n", payload.get("draft_text", "")[:300])
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "ถ้าจะยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่ม"
    test(q)
