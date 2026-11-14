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

## หลักการ: ตัวบทหลัก vs ตัวเสริม

- **ประกาศ 57 (ยื่นกระดาษ) และ 159 (ยื่นอินเทอร์เน็ต) คือตัวบทหลัก** เป็นฉบับรวมล่าสุด —
  ฉบับแก้ไขทุกฉบับ (รวมฉบับระหว่างทางที่ไม่อยู่ในชุดข้อมูล เช่น 99, 203, 204) ถูกเขียนทับเข้าไปแล้ว
- ฉบับแก้ไข (74, 139, 165, 214, 215, 245, 246) เป็น **ตัวเสริม** ใช้อ้างที่มา ("แก้ไขเพิ่มเติมโดย...")
- ฉบับ 234 เป็นช่องทางพิเศษ (DBD) ใช้เฉพาะคำถามที่ระบุ DBD

`scripts/annotate_roles.py` ใส่ฟิลด์ต่อไปนี้ใน `metadata` ของทุก chunk:

| ฟิลด์ | ความหมาย |
|---|---|
| `role` | `primary` (57/159) · `amendment` · `special` (234) |
| `is_current` | ข้อความยังมีผลบังคับใช้ (amendment ที่ถูกฉบับหลังเขียนทับ = `false`) |
| `is_boilerplate` | ข้อท้ายประกาศ (วันใช้บังคับ/ผู้ลงนาม) — ไม่ควรอยู่ในดัชนีค้นหา |
| `amends` / `amends_article` | (amendment) chunk/ข้อของตัวบทหลักที่ถูกแก้ |
| `merge_coverage` | (amendment) สัดส่วนข้อความใหม่ที่พบในตัวบทหลัก |
| `superseded_by` | (amendment ที่ไม่ current) ฉบับที่เขียนทับ |
| `amended_by` | (primary) ฉบับแก้ไขทั้งหมดของข้อนี้ เรียงตามลำดับ |

แนวทาง retrieval: ค้นเฉพาะ `role == "primary"` (และ `special` เมื่อคำถามระบุ DBD) โดยกรอง `is_boilerplate`
ออก แล้วใช้ `amended_by` ประกอบการอ้างอิง — ห้ามใช้ chunk ที่ `is_current == false` ตอบคำถาม

```bash
python chunking/scripts/annotate_roles.py           # ดูตารางผล
python chunking/scripts/annotate_roles.py --write   # เขียนลงไฟล์ chunk (รายฉบับ + all_10)
```

## วัดผล retrieval

```bash
python chunking/scripts/eval_retrieval.py                        # เทียบโหมด all vs primary
python chunking/scripts/eval_retrieval.py --failures 20          # ดูข้อที่ยังผิด
python chunking/scripts/eval_retrieval.py --markdown reports/retrieval_eval.md
```

ชุดทดสอบหลักคือคำถามในขอบเขต + เคสเสี่ยง 132 ข้อจาก `synthetic_dataset_vat_intent.csv`
(เฉลยเขียนแยกจาก metadata ของ chunk) ผลล่าสุดอยู่ที่ [`reports/retrieval_eval.md`](reports/retrieval_eval.md)

`agents/agent3_rag_retrieval.py` ใช้หลักการนี้เป็นค่าเริ่มต้น (`mode="primary"`) และแนบ `citation`
เช่น "ประกาศ... (ฉบับที่ 57) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดยฉบับที่ 74, 139, 165, 245 [ยื่นแบบกระดาษ]"
— ใช้ `RAGRetrievalAgent(mode="all")` เพื่อเปรียบเทียบกับพฤติกรรมเดิม

## ตรวจคุณภาพข้อมูล

```bash
python chunking/scripts/validate_chunks.py          # รายงานอ่านง่าย
python chunking/scripts/validate_chunks.py --json   # JSON
```

ตรวจ schema, chunk ID ที่ dictionary/graph/agents อ้างถึง, title ตรงกับตัวบท, เลขไทย/อารบิก,
ประกาศที่ถูกอ้างถึงแต่ไม่มีในชุดข้อมูล, คุณภาพ keyword, chunk ท้ายประกาศ,
role/amends และตรวจว่าฉบับแก้ไขรุ่นล่าสุดถูกรวมเข้าตัวบทหลัก 57/159 แล้ว
(exit code 1 ถ้ามี ERROR) — ผลล่าสุดอยู่ที่ [`reports/validation_report.txt`](reports/validation_report.txt)

## รันต้นแบบ

```bash
cd chunking/agents
python orchestrator_pipeline.py
```

> หมายเหตุ: สคริปต์ `generate_*.py` ยังเขียน path ตายตัวเป็น `C:\Users\Windows\...` ต้องแก้ก่อนรันบนเครื่องอื่น
