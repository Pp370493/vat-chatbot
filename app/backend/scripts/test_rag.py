import sys
from pathlib import Path

# Set utf-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.agents import agent3_rag_retrieval as a3
from app.agents import agent4_responder as a4

def test():
    query = "ถ้ากำลังจะสร้างโรงงาน สามารถยื่นขอจดทะเบียน VAT ล่วงหน้าได้กี่เดือน"
    print(f"คำถามทดสอบ: {query}\n")

    # 1. Retrieval
    ret = a3.retrieve(query, top_k=3)
    print("=== ผลการค้นหาเอกสาร (Agent 3: RAG Retrieval) ===")
    for idx, (chunk, score) in enumerate(zip(ret["chunks"], ret["relevance_scores"]), 1):
        print(f"[{idx}] ความตรงกัน: {score:.2%} | มาตรา: {chunk['source_section']}")
        print(f"    ข้อความ: {chunk['text'][:120]}...\n")

    # 2. Responder
    print("=== คำตอบที่ AI ร่างขึ้น (Agent 4: Responder) ===")
    ans = a4.respond(query, ret["chunks"])
    print(f"คำตอบ: {ans['draft_text']}\n")
    print(f"การอ้างอิง (Citations): {ans['citations']}")

if __name__ == "__main__":
    test()
