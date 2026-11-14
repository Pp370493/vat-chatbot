# chunking — ประกาศอธิบดีกรมสรรพากร เกี่ยวกับ VAT (การจดทะเบียน)

ฐานความรู้สำหรับ VAT Co-Pilot: ประกาศ 10 ฉบับ แบ่งเป็น chunk ตามข้อกฎหมาย (รวม 75 chunks)
ดูบริบทโดเมนและสถาปัตยกรรมใน [`context.md`](context.md)

## ไฟล์

| ไฟล์ | เนื้อหา |
|---|---|
| `vat{57,74,139,159,165,214,215,234,245,246}_chunks_local_llm.json` | chunk รายฉบับ (`chunk_id`, `article_ref`, `official_raw_text`, `embedding_input`, `llm_context`, `metadata`) |
| `all_10_announcements_chunks_official.json` | รวม chunk ทั้ง 75 รายการ |
| `graph_rag_vat_registration.json` | Graph RAG: ความสัมพันธ์การแก้ไขระหว่างประกาศ + active law chunks |
| `graph_rag_live_viewer.html` | ตัวดูกราฟในเบราว์เซอร์ |
| `vat_synonym_boost_dictionary.json` | พจนานุกรมคำพ้อง/สแลง → target chunks + น้ำหนัก boost |
| `synthetic_dataset_vat_intent.csv` | ชุดข้อมูลจำลองสำหรับ intent classification |
| `generate_synthetic_dataset.py`, `generate_updated_synthetic_dataset.py` | สคริปต์สร้างชุดข้อมูลจำลอง |
| `batch_qa_audit_log.jsonl` | log ผลรัน batch Q&A |
| `agents/` | ต้นแบบ 8 agents + `orchestrator_pipeline.py` (lexical search, ไม่ใช้ LLM) |

## ตรวจคุณภาพข้อมูล

```bash
python chunking/scripts/validate_chunks.py          # รายงานอ่านง่าย
python chunking/scripts/validate_chunks.py --json   # JSON
```

ตรวจ schema, chunk ID ที่ dictionary/graph/agents อ้างถึง, title ตรงกับตัวบท, เลขไทย/อารบิก,
ประกาศที่ถูกอ้างถึงแต่ไม่มีในชุดข้อมูล, คุณภาพ keyword และ chunk ท้ายประกาศ
(exit code 1 ถ้ามี ERROR) — ผลล่าสุดอยู่ที่ [`reports/validation_report.txt`](reports/validation_report.txt)

## รันต้นแบบ

```bash
cd chunking/agents
python orchestrator_pipeline.py
```

> หมายเหตุ: สคริปต์ `generate_*.py` ยังเขียน path ตายตัวเป็น `C:\Users\Windows\...` ต้องแก้ก่อนรันบนเครื่องอื่น
