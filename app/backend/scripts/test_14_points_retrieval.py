"""
Test retrieval accuracy across all 14 legal points after tuning.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.agent3_rag_retrieval import retrieve

TEST_CASES = [
    {
        "point": 1,
        "query": "กำลังสร้างโรงงานยังไม่เสร็จ ขอจด VAT ล่วงหน้าได้กี่เดือน?",
        "expected_top": ["VAT57_ART_01", "VAT159_ART_02"]
    },
    {
        "point": 2,
        "query": "ขายของออนไลน์อยู่คอนโด ไปยื่นจด VAT ที่สำนักงานสรรพากรพื้นที่ได้ไหม หรือต้องยื่นเน็ตอย่างเดียว?",
        "expected_top": ["VAT159_ART_01", "VAT246_ART_01", "VAT57_ART_04_1", "VAT245_ART_01"]
    },
    {
        "point": 3,
        "query": "เปิดร้านขายของวันแรกไม่ได้จด VAT ล่วงหน้า กฎหมายให้เวลาไปยื่นจดภายในกี่วัน?",
        "expected_top": ["VAT57_ART_02", "VAT159_ART_03"]
    },
    {
        "point": 4,
        "query": "ธุรกิจที่ได้รับยกเว้นภาษีตามมาตรา 81/3 แต่อยากจด VAT เคลมภาษีซื้อ ต้องยื่นภายในกี่วัน?",
        "expected_top": ["VAT57_ART_03", "VAT159_ART_04"]
    },
    {
        "point": 5,
        "query": "ร้านค้าอยู่เขตจตุจักร และมีหลายสาขา ต้องไปยื่นจด VAT ที่สำนักงานสรรพากรพื้นที่ไหน?",
        "expected_top": ["VAT57_ART_04", "VAT74_ART_04", "VAT139_ART_01", "VAT165_ART_01"]
    },
    {
        "point": 6,
        "query": "บุคคลธรรมดาไปจด VAT ถ้าให้คนอื่นไปแทนต้องใช้ใบมอบอำนาจและเอกสารอะไรบ้าง?",
        "expected_top": ["VAT57_ART_05_A", "VAT165_ART_02_A", "VAT215_ART_01", "VAT159_ART_05_A", "VAT214_ART_01_A", "VAT246_ART_02_A"]
    },
    {
        "point": 7,
        "query": "เปิดบริษัทใหม่จด VAT นิติบุคคล ต้องใช้หนังสือรับรอง บอจ.5 และบริคณห์สนธิอะไรบ้าง?",
        "expected_top": ["VAT57_ART_05_B", "VAT165_ART_02_B", "VAT159_ART_05_B", "VAT214_ART_01_B", "VAT246_ART_02_B"]
    },
    {
        "point": 8,
        "query": "ขายของออนไลน์อยู่คอนโด ทำไมไม่ต้องขอหนังสือรับรองจากนิติคอนโด?",
        "expected_top": ["VAT159_ART_05_C", "VAT246_ART_03", "VAT214_ART_02", "VAT57_ART_05_C"]
    },
    {
        "point": 9,
        "query": "ยื่นจด VAT ผ่านเน็ต ทำไมระบบมีช่องให้กดยินยอมให้ Shopee หรือ TikTok ส่งข้อมูลยอดขายให้สรรพากร?",
        "expected_top": ["VAT159_ART_05_1", "VAT246_ART_04"]
    },
    {
        "point": 10,
        "query": "สรรพากรไม่ออกใบ ภ.พ.20 ให้ กรณีใช้สำนักงานบัญชีเป็นที่ตั้ง หรือมีพฤติการณ์ตัวแทนเชิดนอมินี?",
        "expected_top": ["VAT57_ART_06", "VAT74_ART_06", "VAT159_ART_06", "VAT214_ART_03", "VAT246_ART_04_1"]
    },
    {
        "point": 11,
        "query": "ใบทะเบียนภาษีมูลค่าเพิ่มสำหรับสำนักงานใหญ่กับสาขา ใช้แบบฟอร์มเบอร์อะไร แบบ ภ.พ.20 หรือ ภ.พ.21?",
        "expected_top": ["VAT57_ART_07", "VAT74_ART_07", "VAT159_ART_07"]
    },
    {
        "point": 12,
        "query": "ยื่นจด VAT แล้วมีผลตั้งแต่วันไหน เอา ภ.พ.01 ที่มีเลขที่อ้างอิงมาใช้แทนชั่วคราวได้ไหม?",
        "expected_top": ["VAT57_ART_08", "VAT74_ART_08", "VAT159_ART_08", "VAT214_ART_03_1"]
    },
    {
        "point": 13,
        "query": "ถ้าสรรพากรพื้นที่ไม่อยู่หรือไปราชการ ใครเป็นคนมีอำนาจลงนามเซ็นใบ ภ.พ.20 แทน?",
        "expected_top": ["VAT57_ART_09", "VAT74_ART_09", "VAT165_ART_03", "VAT159_ART_09", "VAT214_ART_04", "VAT245_ART_02", "VAT246_ART_05"]
    },
    {
        "point": 14,
        "query": "ถ้ามีปัญหาข้อพิพาทในการปฏิบัติหรือตีความระเบียบการจดทะเบียน VAT ใครเป็นผู้มีอำนาจวินิจฉัยชี้ขาด?",
        "expected_top": ["VAT57_ART_10", "VAT74_ART_10", "VAT159_ART_10"]
    },
    {
        "point": "Special DBD",
        "query": "จด VAT พร้อมตั้งบริษัทที่กรมพัฒนาธุรกิจการค้า (DBD) ต้องทำอย่างไร?",
        "expected_top": ["VAT234_ATTACH", "VAT234_ART_01", "VAT234_ART_02", "VAT234_ART_04"]
    }
]

print("=== Running 15 RAG Retrieval Benchmark Queries ===\n")
passed = 0
for tc in TEST_CASES:
    res = retrieve(tc["query"], top_k=3)
    top_chunks = [c["chunk_id"] for c in res["chunks"]]
    scores = res["relevance_scores"]
    hit = any(cid in tc["expected_top"] for cid in top_chunks)
    if hit:
        passed += 1
        status = "[PASS]"
    else:
        status = "[FAIL]"

    print(f"{status} Point {tc['point']}: {tc['query']}")
    print(f"       Top Chunks: {top_chunks} (Scores: {scores})")
    print(f"       Expected any of: {tc['expected_top']}\n")

print(f"Total Passed: {passed}/{len(TEST_CASES)} ({passed/len(TEST_CASES)*100:.1f}%)")
