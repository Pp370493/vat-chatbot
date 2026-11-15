#!/usr/bin/env python3
"""
ตรวจคุณภาพฐานความรู้ chunking (ประกาศอธิบดีฯ VAT 10 ฉบับ)

ตรวจ:
  1. schema ของ chunk แต่ละรายการ + ความสอดคล้องระหว่างไฟล์รายฉบับกับไฟล์รวม
  2. chunk ID ที่ถูกอ้างถึงจาก dictionary / graph / agents มีอยู่จริง
  3. graph: chunk_ids ของแต่ละประกาศครอบคลุม chunk ทุกตัวพอดี
  4. เลขไทย vs เลขอารบิก (article_ref ต้องหาเจอในตัวบทหลัง normalize)
  5. ประกาศฉบับอื่นที่ตัวบทอ้างถึงแต่ไม่อยู่ในชุดข้อมูล
  6. คุณภาพ keyword: สั้น/กว้างเกินไป, "ข้อ N" ที่ชนกัน, keyword ซ้ำข้ามหลายข้อ
  7. title / article_ref ตรงกับตัวบท (กัน title+keyword เลื่อนข้อ)
  8. chunk ท้ายประกาศ (วันใช้บังคับ/ผู้ลงนาม) ที่ปนอยู่ในดัชนีค้นหา
  9. ข้อความซ้ำซ้อนระหว่าง official_raw_text / embedding_input / llm_context
 10. role / amends / is_current (หลักการ 57+159 เป็นตัวบทหลักฉบับรวม) และฉบับแก้ไขรุ่นล่าสุด
     ถูกรวมเข้าตัวบทหลักแล้ว

ใช้งาน:
  python chunking/scripts/validate_chunks.py            # รายงานแบบอ่านง่าย
  python chunking/scripts/validate_chunks.py --json     # ผลแบบ JSON
exit code: 1 ถ้ามี ERROR, 0 ถ้ามีแค่ WARN/INFO
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORPUS = {"57", "74", "139", "159", "165", "214", "215", "234", "245", "246"}
REQUIRED_FIELDS = ["chunk_id", "article_ref", "title", "official_raw_text",
                   "embedding_input", "llm_context", "metadata", "official_announcement"]
META_LIST_FIELDS = ["boost_keywords", "tfidf_keywords", "user_intents"]

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
CHUNK_ID_RE = re.compile(r"VAT\d+_ART_[A-Z0-9_]+?(?=[^A-Z0-9_]|$)")
ANN_REF_RE = re.compile(r"\(ฉบับที่\s*([0-9]+)\)")
ARTICLE_NUM_RE = re.compile(r"^ข้อ\s*([0-9]+(?:/[0-9]+)?)")
GENERIC_ARTICLE_KW_RE = re.compile(r"^ข้อ\s*[0-9]+(?:/[0-9]+)?$")

SHORT_KW_LEN = 4          # keyword ที่ยาว <= นี้ (ตัวอักษร) ถือว่าสั้นเกิน เสี่ยง substring match
SHARED_KW_TOPICS = 3       # keyword ที่กระจายอยู่ใน >= จำนวน topic (ใน graph) นี้ ถือว่ากว้างเกิน


def norm(text: str) -> str:
    return (text or "").translate(THAI_DIGITS)


class Report:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, level: str, check: str, msg: str, **detail):
        self.items.append({"level": level, "check": check, "message": msg, **detail})

    def count(self, level: str) -> int:
        return sum(1 for i in self.items if i["level"] == level)


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def article_key(chunk: dict) -> str:
    """คีย์ของข้อกฎหมายจริงที่ chunk นี้พูดถึง เช่น '57:9' (ใช้นับว่า keyword กระจายไปกี่ข้อ)"""
    ref = norm(chunk.get("article_ref", ""))
    m = re.search(r"(?:แก้ไข|เพิ่ม)ข้อ\s*([0-9]+(?:/[0-9]+)?)[^ฉ]*ฉบับที่\s*([0-9]+)", ref)
    if m:
        return f"{m.group(2)}:{m.group(1)}"
    ann = chunk["chunk_id"].split("_")[0][3:]
    m = ARTICLE_NUM_RE.match(ref)
    return f"{ann}:{m.group(1) if m else ref}"


# --------------------------------------------------------------------------- checks

def check_schema(chunks_by_file: dict, combined: list, rep: Report) -> dict:
    all_chunks: dict[str, dict] = {}
    for fname, chunks in chunks_by_file.items():
        prefix = "VAT" + re.match(r"vat(\d+)_", fname).group(1) + "_"
        for c in chunks:
            cid = c.get("chunk_id", "<missing>")
            missing = [k for k in REQUIRED_FIELDS if not c.get(k)]
            if missing:
                rep.add("ERROR", "schema", f"{cid}: ขาดฟิลด์หรือค่าว่าง {missing}", file=fname)
            if not cid.startswith(prefix):
                rep.add("ERROR", "schema", f"{cid}: prefix ไม่ตรงกับไฟล์ {fname}")
            if cid in all_chunks:
                rep.add("ERROR", "schema", f"{cid}: chunk_id ซ้ำ")
            meta = c.get("metadata") or {}
            for k in META_LIST_FIELDS:
                if not isinstance(meta.get(k), list) or not meta.get(k):
                    rep.add("WARN", "schema", f"{cid}: metadata.{k} ว่างหรือไม่ใช่ list")
            if not str(c.get("embedding_input", "")).startswith("search_document:"):
                rep.add("WARN", "schema", f"{cid}: embedding_input ไม่ขึ้นต้นด้วย 'search_document:'")
            all_chunks[cid] = c

    combined_by_id = {c.get("chunk_id"): c for c in combined}
    only_files = sorted(set(all_chunks) - set(combined_by_id))
    only_combined = sorted(set(combined_by_id) - set(all_chunks))
    if only_files or only_combined:
        rep.add("ERROR", "combined", "ไฟล์รวมกับไฟล์รายฉบับมี chunk ไม่ตรงกัน",
                only_in_files=only_files, only_in_combined=only_combined)
    diff = [cid for cid in set(all_chunks) & set(combined_by_id) if all_chunks[cid] != combined_by_id[cid]]
    if diff:
        rep.add("WARN", "combined", f"เนื้อหาใน all_10 ต่างจากไฟล์รายฉบับ {len(diff)} chunk "
                f"(แก้ที่หนึ่งแต่ไม่ได้ sync อีกที่)", chunk_ids=sorted(diff))
    else:
        rep.add("INFO", "combined", f"all_10 ตรงกับไฟล์รายฉบับทุกตัวอักษร ({len(all_chunks)} chunks)")
    return all_chunks


def check_references(all_chunks: dict, dictionary: dict, graph: dict, rep: Report):
    known = set(all_chunks)

    def verify(source: str, ids):
        bad = sorted({i for i in ids if i not in known})
        if bad:
            rep.add("ERROR", "references", f"{source}: อ้าง chunk ที่ไม่มีอยู่จริง", chunk_ids=bad)
        return bad

    # dictionary
    for key, clause in dictionary.get("clauses", {}).items():
        verify(f"dictionary.{key}.target_chunks", clause.get("target_chunks", []))
        verify(f"dictionary.{key}.suppress_other_clauses", clause.get("suppress_other_clauses", []))

    # graph
    for ann in graph.get("nodes", {}).get("announcements", []):
        verify(f"graph.announcements[{ann.get('id')}].chunk_ids", ann.get("chunk_ids", []))
    for e in graph.get("edges", {}).get("topic_membership", []):
        for end in (e.get("source"), e.get("target")):
            if isinstance(end, str) and end.startswith("VAT"):
                verify("graph.topic_membership", [end])
    for lin in graph.get("edges", {}).get("legal_evolution_lineage", []):
        verify(f"graph.lineage[{lin.get('issue')}].active_law_chunks", lin.get("active_law_chunks", []))
        for step in lin.get("chronology", []) or []:
            if isinstance(step, dict):
                ids = [v for v in step.values() if isinstance(v, str) and v.startswith("VAT")]
                ids += [x for v in step.values() if isinstance(v, list) for x in v
                        if isinstance(x, str) and x.startswith("VAT")]
                verify(f"graph.lineage[{lin.get('issue')}].chronology", ids)

    # chunk ID ที่ hardcode ไว้ใน agents/*.py
    for path in sorted(glob.glob(os.path.join(ROOT, "agents", "*.py"))):
        with open(path, encoding="utf-8") as f:
            ids = set(CHUNK_ID_RE.findall(f.read()))
        verify(f"agents/{os.path.basename(path)}", ids)


def check_graph_coverage(all_chunks: dict, graph: dict, rep: Report):
    seen = defaultdict(list)
    for ann in graph.get("nodes", {}).get("announcements", []):
        for cid in ann.get("chunk_ids", []):
            seen[cid].append(ann.get("id"))
    missing = sorted(set(all_chunks) - set(seen))
    dupes = {cid: anns for cid, anns in seen.items() if len(anns) > 1}
    if missing:
        rep.add("WARN", "graph", "chunk ที่ไม่ถูกผูกกับประกาศใดใน graph", chunk_ids=missing)
    if dupes:
        rep.add("WARN", "graph", "chunk ที่ถูกผูกกับหลายประกาศใน graph", detail=dupes)
    active = {c for lin in graph.get("edges", {}).get("legal_evolution_lineage", [])
              for c in lin.get("active_law_chunks", [])}
    rep.add("INFO", "graph", f"active_law_chunks ครอบคลุม {len(active)}/{len(all_chunks)} chunks "
            f"ใน {len(graph.get('edges', {}).get('legal_evolution_lineage', []))} สายการแก้ไข")


def check_digits(all_chunks: dict, rep: Report):
    thai_digit_chunks = [cid for cid, c in all_chunks.items()
                         if re.search(r"[๐-๙]", c.get("official_raw_text", ""))]
    rep.add("INFO", "digits", f"chunk ที่ตัวบทใช้เลขไทย: {len(thai_digit_chunks)}/{len(all_chunks)} "
            f"(การ match 'ข้อ 9' แบบตรงตัวจะไม่เจอ 'ข้อ ๙' ถ้าไม่ normalize ก่อน)")
    for cid, c in all_chunks.items():
        ref = norm(c.get("article_ref", ""))
        m = ARTICLE_NUM_RE.match(ref)
        if not m:
            continue
        # ผ่านถ้าพบเลขข้อของฉบับนั้นเอง หรือเลขข้อที่ถูกแก้/เพิ่ม (ฉบับ 74 เก็บเฉพาะข้อความที่เพิ่ม ไม่มีคำนำ "ข้อ 2")
        nums = [m.group(1)] + re.findall(r"(?:แก้ไข|เพิ่ม|ยกเลิก)\s*ข้อ\s*([0-9]+(?:/[0-9]+)?)", ref)
        raw = norm(c.get("official_raw_text", ""))
        if not any(re.search(rf"ข้อ\s*{re.escape(n)}(?![0-9/])", raw) for n in nums):
            rep.add("WARN", "digits", f"{cid}: article_ref '{c.get('article_ref')}' ไม่พบเลขข้อในตัวบท "
                    f"แม้ normalize เลขไทยแล้ว", article_ref=c.get("article_ref"))


AMEND_TARGET_RE = re.compile(r"(?:แก้ไข|เพิ่ม|ยกเลิก)\s*ข้อ\s*([0-9]+(?:/[0-9]+)?)")
RAW_TARGET_RE = re.compile(
    r"(?:ยกเลิกความใน|เพิ่มความต่อไปนี้เป็น).{0,60}?ข้อ\s*([0-9]+(?:/[0-9]+)?)", re.S)
LEAD_ARTICLE_RE = re.compile(r"^\s*ข้อ\s*([0-9]+(?:/[0-9]+)?)")
TITLE_OVERLAP_MIN = 0.40   # สัดส่วน 4-gram ของคำอธิบายใน title ที่ต้องพบในตัวบท
PREAMBLE_RE = re.compile(r"ให้(?:ยกเลิกความ|เพิ่มความ|ยกเลิกข้อ).*?(?:\(ฉบับที่\s*[0-9]+\)|$)")


def _ngrams(text: str, n: int = 4) -> set:
    t = re.sub(r"[\s()\[\]【】:/.,\"“”'-]+", "", text)
    return {t[i:i + n] for i in range(max(len(t) - n + 1, 0))}


def check_alignment(all_chunks: dict, rep: Report):
    """title / article_ref / ตัวบท ต้องพูดถึงข้อเดียวกัน (กัน title+keyword เลื่อนข้อ)"""
    bad, substituted_only = [], []
    for cid, c in all_chunks.items():
        raw = norm(c.get("official_raw_text", ""))
        title = norm(c.get("title", ""))
        ref = norm(c.get("article_ref", ""))
        raw_lead = LEAD_ARTICLE_RE.match(raw)
        title_lead = LEAD_ARTICLE_RE.match(title)
        raw_t = RAW_TARGET_RE.search(raw[:500])
        title_t = AMEND_TARGET_RE.search(title.split(":")[0])
        ref_t = AMEND_TARGET_RE.search(ref)
        problems = []

        if raw_t:   # ตัวบทมีคำนำ "ให้ยกเลิกความในข้อ X" → เทียบข้อที่ถูกแก้
            for name, m in (("title", title_t), ("article_ref", ref_t)):
                if m and m.group(1) != raw_t.group(1):
                    problems.append(f"ตัวบทแก้ 'ข้อ {raw_t.group(1)}' แต่ {name} บอก 'ข้อ {m.group(1)}'")
        elif title_t and not re.search(rf"ข้อ\s*{re.escape(title_t.group(1))}(?![0-9/])", raw):
            problems.append(f"title บอกว่าเกี่ยวกับ 'ข้อ {title_t.group(1)}' แต่ตัวบทไม่มีการอ้างถึงข้อนี้เลย")
        elif raw_lead and title_lead and raw_lead.group(1) != title_lead.group(1):
            if title_t and title_t.group(1) == raw_lead.group(1):
                substituted_only.append(cid)   # เก็บเฉพาะข้อความใหม่ที่ใช้แทน ไม่มีคำนำ
            else:
                problems.append(f"ตัวบทขึ้นต้น 'ข้อ {raw_lead.group(1)}' แต่ title 'ข้อ {title_lead.group(1)}'")

        desc = title.split(":", 1)[1] if ":" in title else ""
        desc = re.sub(r"\(.*?\)", "", PREAMBLE_RE.sub("", desc)).strip()   # ตัดคำนำฉบับแก้ไข + วงเล็บสรุป
        dg = _ngrams(desc)
        overlap = len(dg & _ngrams(raw)) / len(dg) if dg else 1.0

        if problems:
            bad.append(cid)
            rep.add("ERROR", "alignment", f"{cid}: " + "; ".join(problems),
                    title=c.get("title", "")[:120], raw_head=c.get("official_raw_text", "")[:120].replace("\n", " "))
        elif overlap < TITLE_OVERLAP_MIN:
            bad.append(cid)
            rep.add("WARN", "alignment", f"{cid}: คำอธิบายใน title แทบไม่ตรงกับตัวบท "
                    f"(overlap {overlap:.0%}) — title/keyword อาจเป็นของข้ออื่น",
                    title=c.get("title", "")[:120], raw_head=c.get("official_raw_text", "")[:120].replace("\n", " "))
    if substituted_only:
        rep.add("INFO", "alignment", f"{len(substituted_only)} chunk เก็บเฉพาะข้อความใหม่ที่ใช้แทน (ไม่มีคำนำ "
                f"'ให้ยกเลิกความใน...') ต่างจากฉบับแก้ไขอื่น — รูปแบบไม่สม่ำเสมอ", chunk_ids=substituted_only)
    if not bad:
        rep.add("INFO", "alignment", "title / article_ref ตรงกับตัวบททุก chunk")


def check_graph_amendments(all_chunks: dict, graph: dict, rep: Report):
    """ข้อที่ตัวบทของฉบับแก้ไขบอกว่าแก้ ต้องอยู่ใน amendment_chain.sections ของ graph"""
    sections = defaultdict(set)
    for e in graph.get("edges", {}).get("amendment_chain", []):
        if e.get("relation") == "AMENDS":
            ann = str(e.get("source", "")).replace("ANN_", "")
            for sec in e.get("sections") or []:
                m = re.search(r"ข้อ\s*([0-9]+(?:/[0-9]+)?)", norm(sec))
                if m:
                    sections[ann].add(m.group(1))
    for cid, c in all_chunks.items():
        ann = cid.split("_")[0][3:]
        if ann not in sections:
            continue
        m = RAW_TARGET_RE.search(norm(c.get("official_raw_text", ""))[:500])
        if m and m.group(1) not in sections[ann]:
            rep.add("WARN", "graph", f"{cid}: ตัวบทแก้ 'ข้อ {m.group(1)}' แต่ graph ระบุว่าฉบับ {ann} "
                    f"แก้เฉพาะ {sorted(sections[ann])}")


def check_missing_announcements(all_chunks: dict, rep: Report):
    refs = defaultdict(set)
    for cid, c in all_chunks.items():
        for num in ANN_REF_RE.findall(norm(c.get("official_raw_text", ""))):
            if num not in CORPUS:
                refs[num].add(cid)
    for num, cids in sorted(refs.items(), key=lambda x: int(x[0])):
        rep.add("INFO", "corpus", f"ตัวบทอ้างถึงประกาศฉบับที่ {num} ซึ่งไม่มีในชุดข้อมูล — เป็นฉบับแก้ไขระหว่างทาง "
                f"ที่ถูกเขียนทับเข้าไปในฉบับ 57/159 แล้ว ไม่ต้องเพิ่ม", referenced_by=sorted(cids))


def chunk_topics(graph: dict) -> dict[str, set]:
    topics = defaultdict(set)
    for e in graph.get("edges", {}).get("topic_membership", []):
        if str(e.get("source", "")).startswith("VAT"):
            topics[e["source"]].add(e.get("target"))
    return topics


def check_keywords(all_chunks: dict, dictionary: dict, graph: dict, rep: Report):
    topics = chunk_topics(graph)
    no_topic = sorted(set(all_chunks) - set(topics))
    boiler = [c for c in no_topic if all_chunks[c].get("metadata", {}).get("is_boilerplate")]
    no_topic = [c for c in no_topic if c not in boiler]
    if no_topic:
        rep.add("WARN", "graph", "chunk ที่ไม่ได้ผูกกับ topic ใดใน graph", chunk_ids=no_topic)
    if boiler:
        rep.add("INFO", "graph", f"chunk ท้ายประกาศ (is_boilerplate) {len(boiler)} ชิ้นไม่ผูก topic — ไม่อยู่ในดัชนีค้นหาอยู่แล้ว",
                chunk_ids=boiler)

    kw_topics = defaultdict(set)
    kw_chunks = defaultdict(set)
    self_numbered = []   # 'ข้อ N' ที่เป็นเลขข้อของฉบับแก้ไขเอง แต่เนื้อหาเป็นข้ออื่นของฉบับแม่บท
    generic = defaultdict(list)
    short = defaultdict(list)
    for cid, c in all_chunks.items():
        akey = article_key(c)
        own_num = (ARTICLE_NUM_RE.match(norm(c.get("article_ref", ""))) or [None, None])[1]
        for kw in (c.get("metadata") or {}).get("boost_keywords", []):
            k = norm(kw).strip().lower()
            kw_topics[k] |= topics.get(cid) or {"(ไม่มี topic)"}
            kw_chunks[k].add(cid)
            if GENERIC_ARTICLE_KW_RE.match(k):
                generic[k].append(cid)
                if own_num and k.replace(" ", "") == f"ข้อ{own_num}" and akey.split(":")[1] != own_num:
                    self_numbered.append(f"{cid} ('{kw}' แต่เนื้อหาคือข้อ {akey.split(':')[1]} ฉบับ {akey.split(':')[0]})")
            elif len(k) <= SHORT_KW_LEN:
                short[kw].append(cid)

    if self_numbered:
        rep.add("WARN", "keywords",
                f"{len(self_numbered)} chunk ของฉบับแก้ไขใช้เลขข้อของตัวเองเป็น keyword "
                f"→ ผู้ใช้ถาม 'ข้อ N' (หมายถึงฉบับแม่บท) จะดึงผิดข้อ", chunks=self_numbered)
    rep.add("INFO", "keywords",
            f"keyword แบบ 'ข้อ N' มี {len(generic)} แบบ ใน {sum(map(len, generic.values()))} chunks "
            f"(agents/agent3 ใช้ kw_in() ซึ่งไม่ให้ 'ข้อ 1' ไปเจอใน 'ข้อ 10' หรือ 'ข้อ 5' เจอใน 'ข้อ 5/1')",
            detail={k: len(v) for k, v in sorted(generic.items())})
    if short:
        rep.add("WARN", "keywords", f"keyword สั้น (<= {SHORT_KW_LEN} ตัวอักษร) {len(short)} คำ "
                f"→ เสี่ยง substring match", detail={k: len(v) for k, v in sorted(short.items())})

    wide = [(k, t) for k, t in kw_topics.items()
            if len(t) >= SHARED_KW_TOPICS and not GENERIC_ARTICLE_KW_RE.match(k)]
    if wide:
        wide.sort(key=lambda x: (-len(x[1]), x[0]))
        rep.add("WARN", "keywords", f"{len(wide)} keyword กระจายอยู่ >= {SHARED_KW_TOPICS} topics "
                f"→ boost ไม่ช่วยแยกข้อ (บางตัวคือ keyword ที่ติดผิด chunk ดูหมวด alignment)",
                detail={k: f"{len(t)} topics / {len(kw_chunks[k])} chunks" for k, t in wide})

    # dictionary: keyword เดียวกันอยู่ในหลาย clause / keyword สั้น
    clause_of = defaultdict(set)
    for key, clause in dictionary.get("clauses", {}).items():
        for kw in clause.get("keywords", []) + clause.get("intent_triggers", []):
            k = kw.strip().lower()
            clause_of[k].add(key)
            if len(k) <= SHORT_KW_LEN:
                rep.add("WARN", "dictionary", f"{key}: keyword สั้นเกินไป '{kw}'")
    for k, clauses in sorted(clause_of.items()):
        if len(clauses) > 1:
            rep.add("WARN", "dictionary", f"keyword '{k}' อยู่ใน {len(clauses)} clauses "
                    f"→ boost หลายข้อพร้อมกัน", clauses=sorted(clauses))
    for key, clause in dictionary.get("clauses", {}).items():
        if clause.get("negative_boost_if") or clause.get("suppress_other_clauses"):
            rep.add("INFO", "dictionary", f"{key}: มีฟิลด์ negative_boost_if/suppress_other_clauses "
                    f"— ตรวจว่า agent อ่านฟิลด์นี้จริง (ไม่ใช่ hardcode ซ้ำในโค้ด)")


def check_boilerplate(all_chunks: dict, rep: Report):
    marked, unmarked = [], []
    for cid, c in all_chunks.items():
        raw = c.get("official_raw_text", "")
        if re.match(r"^\s*ข้อ\s*[0-9๐-๙]+\s*ประกาศนี้ให้ใช้บังคับ", raw):
            (marked if (c.get("metadata") or {}).get("is_boilerplate") else unmarked).append(cid)
    if unmarked:
        rep.add("WARN", "boilerplate", "chunk ท้ายประกาศ (วันใช้บังคับ/ผู้ลงนาม) ที่ยังไม่ได้ติด is_boilerplate "
                "— จะหลุดเข้าดัชนีค้นหาและชนกับคำถามข้อ 9 'ใครลงนาม'", chunk_ids=unmarked)
    if marked:
        rep.add("INFO", "boilerplate", f"chunk ท้ายประกาศ {len(marked)} ตัวติด is_boilerplate แล้ว "
                "— retrieval ต้องกรองออก", chunk_ids=marked)


def check_roles(all_chunks: dict, rep: Report):
    """หลักการ: 57/159 = ตัวบทหลักฉบับรวมล่าสุด, ฉบับแก้ไข = ตัวเสริม, 234 = ช่องทาง DBD"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from annotate_roles import (AMENDS_TARGET, MERGED_MIN_COVERAGE, PRIMARY, SPECIAL,
                                ann_of, coverage, new_text)

    meta = {cid: c.get("metadata") or {} for cid, c in all_chunks.items()}
    missing = [cid for cid, m in meta.items() if "role" not in m or "is_current" not in m]
    if missing:
        rep.add("ERROR", "roles", f"{len(missing)} chunk ยังไม่มี role/is_current "
                "— รัน scripts/annotate_roles.py --write", chunk_ids=missing)
        return

    for cid, m in meta.items():
        ann = ann_of(cid)
        expected = "primary" if ann in PRIMARY else "special" if ann in SPECIAL else "amendment"
        if m["role"] != expected:
            rep.add("ERROR", "roles", f"{cid}: role '{m['role']}' แต่ควรเป็น '{expected}'")
        if m["role"] == "amendment" and not m.get("is_boilerplate"):
            for p in m.get("amends") or []:
                if p not in all_chunks or meta[p].get("role") != "primary":
                    rep.add("ERROR", "roles", f"{cid}: amends '{p}' ไม่ใช่ chunk ตัวบทหลัก")
                elif ann_of(p) != AMENDS_TARGET.get(ann):
                    rep.add("ERROR", "roles", f"{cid}: amends '{p}' แต่ฉบับ {ann} แก้ฉบับ {AMENDS_TARGET.get(ann)}")
                elif cid not in (meta[p].get("amended_by") or []):
                    rep.add("WARN", "roles", f"{p}: amended_by ไม่มี {cid} (ข้อมูลสองทางไม่ตรงกัน)")
            if not m.get("amends"):
                rep.add("WARN", "roles", f"{cid}: ฉบับแก้ไขที่ไม่ได้ระบุ amends")

    # ฉบับแก้ไขรุ่นล่าสุดของแต่ละข้อ ต้องถูกรวมเข้าตัวบทหลักแล้ว (คำนวณใหม่ ไม่เชื่อค่าที่เก็บไว้)
    not_merged = []
    for p, m in meta.items():
        if m.get("role") != "primary" or not m.get("amended_by"):
            continue
        latest = max(int(ann_of(a)) for a in m["amended_by"])
        siblings = "".join(all_chunks[x]["official_raw_text"] for x in sorted(all_chunks)
                           if x.startswith(p.rsplit("_", 1)[0] if p[-2] == "_" and p[-1].isalpha() else p))
        for a in m["amended_by"]:
            if int(ann_of(a)) != latest:
                continue
            text = new_text(all_chunks[a]["official_raw_text"])
            cov = max(coverage(text, all_chunks[p]["official_raw_text"]), coverage(text, siblings))
            if cov < MERGED_MIN_COVERAGE:
                not_merged.append(f"{a} → {p} ({cov:.0%})")
    if not_merged:
        rep.add("ERROR", "consolidation", "ฉบับแก้ไขรุ่นล่าสุดที่ข้อความยังไม่อยู่ในตัวบทหลัก 57/159 "
                "— ตัวบทหลักอาจยังไม่ได้อัปเดต", detail=not_merged)
    else:
        rep.add("INFO", "consolidation", "ฉบับแก้ไขรุ่นล่าสุดของทุกข้อถูกรวมเข้าตัวบทหลัก 57/159 แล้ว")

    superseded = [f"{cid} (แทนที่โดยฉบับ {', '.join(m.get('superseded_by') or [])})"
                  for cid, m in meta.items() if not m.get("is_current")]
    counts = defaultdict(int)
    for m in meta.values():
        counts[m["role"]] += 1
    rep.add("INFO", "roles", "role: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
            + f" | ดัชนีค้นหาหลัก (primary ไม่รวม boilerplate): "
            f"{sum(1 for m in meta.values() if m['role'] == 'primary' and not m.get('is_boilerplate'))} chunks")
    if superseded:
        rep.add("INFO", "roles", f"ฉบับแก้ไขที่ถูกเขียนทับแล้ว {len(superseded)} chunk (มีกฎที่ยกเลิกแล้ว "
                "— ใช้อ้างประวัติได้ ห้ามใช้ตอบ)", chunks=superseded)


def check_redundancy(all_chunks: dict, rep: Report):
    total = dup = 0
    for c in all_chunks.values():
        raw = c.get("official_raw_text", "")
        for field in ("embedding_input", "llm_context"):
            val = c.get(field, "")
            total += len(val.encode("utf-8"))
            if raw and raw in val:
                dup += len(raw.encode("utf-8"))
    total += sum(len(c.get("official_raw_text", "").encode("utf-8")) for c in all_chunks.values())
    rep.add("INFO", "redundancy", f"ตัวบทถูกเก็บซ้ำใน embedding_input/llm_context รวม {dup/1024:.0f} KB "
            f"จากข้อความ 3 ฟิลด์ทั้งหมด {total/1024:.0f} KB")


def summarize_intents(all_chunks: dict, rep: Report):
    n = sum(len((c.get("metadata") or {}).get("user_intents", [])) for c in all_chunks.values())
    rep.add("INFO", "eval", f"user_intents รวม {n} คำถาม — ใช้เป็นชุดทดสอบ retrieval ได้ (คำถาม → chunk ที่ควรได้)")


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="แสดงผลเป็น JSON")
    args = ap.parse_args()

    chunks_by_file = {os.path.basename(p): load_json(p)
                      for p in sorted(glob.glob(os.path.join(ROOT, "vat*_chunks_local_llm.json")))}
    combined = load_json(os.path.join(ROOT, "all_10_announcements_chunks_official.json"))
    dictionary = load_json(os.path.join(ROOT, "vat_synonym_boost_dictionary.json"))
    graph = load_json(os.path.join(ROOT, "graph_rag_vat_registration.json"))

    rep = Report()
    all_chunks = check_schema(chunks_by_file, combined, rep)
    check_roles(all_chunks, rep)
    check_references(all_chunks, dictionary, graph, rep)
    check_graph_coverage(all_chunks, graph, rep)
    check_alignment(all_chunks, rep)
    check_graph_amendments(all_chunks, graph, rep)
    check_digits(all_chunks, rep)
    check_missing_announcements(all_chunks, rep)
    check_keywords(all_chunks, dictionary, graph, rep)
    check_boilerplate(all_chunks, rep)
    check_redundancy(all_chunks, rep)
    summarize_intents(all_chunks, rep)

    if args.json:
        json.dump({"summary": {lv: rep.count(lv) for lv in ("ERROR", "WARN", "INFO")},
                   "items": rep.items}, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(f"ตรวจ {len(all_chunks)} chunks จาก {len(chunks_by_file)} ไฟล์\n")
        for check in dict.fromkeys(i["check"] for i in rep.items):
            print(f"== {check}")
            for i in rep.items:
                if i["check"] != check:
                    continue
                extra = {k: v for k, v in i.items() if k not in ("level", "check", "message")}
                print(f"  [{i['level']}] {i['message']}")
                for k, v in extra.items():
                    if v:
                        print(f"           {k}: {v}")
            print()
        print(f"สรุป: ERROR {rep.count('ERROR')} | WARN {rep.count('WARN')} | INFO {rep.count('INFO')}")
    return 1 if rep.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
