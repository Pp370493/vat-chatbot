#!/usr/bin/env python3
"""
แตกตัวบทเป็นลำดับชั้น ข้อ → วรรค → อนุ (1) → ย่อย (ก) และเชื่อมจุดที่อ้างถึงกัน — ใช้ตรรกะเดียวกันทุกประกาศทุกข้อ

    python chunking/scripts/build_hierarchy.py            # เขียน hierarchy/vat_hierarchy.json + reports/hierarchy_report.md

ที่มา: official_raw_text ของ chunk 75 ชิ้น (ตรวจเทียบต้นฉบับแล้ว) — chunk เดิมไม่ถูกแก้
- ข้อที่ถูกแบ่งเป็นหลาย chunk (05_A/B/C) ประกอบกลับเป็นข้อเดียว ตัดคำที่ chunker เติม ("(วรรคท้าย)", "ข้อ 2 “ข้อ 5(")
  และตัดวรรคปิดท้ายที่ซ้ำกันในแต่ละ chunk
- อนุ/ย่อยที่ขึ้นต้นบรรทัดเป็นตัวแบ่งชั้น · บรรทัดที่ไม่มีเครื่องหมาย = วรรคใหม่
  วรรคที่อยู่กลางรายการ (มีอนุถัดไปตามมา) เป็นวรรคของอนุ/ย่อยนั้น ส่วนวรรคหลังรายการตัวสุดท้ายเป็นวรรคของข้อ
- รายการอนุผูกกับวรรคที่นำมันมา (เช่น ข้อ 6 ของฉบับ 57: เหตุ (1)–(6) อยู่ใต้วรรคสาม)
- ฉบับแก้ไข: ส่วนคำสั่ง ("ให้ยกเลิกความใน … ให้ใช้ความต่อไปนี้แทน") เป็นข้อความของข้อ ส่วนข้อความใหม่ในเครื่องหมายคำพูด
  แตกเป็นลำดับชั้นเหมือนตัวบทหลัก และเชื่อม amends ไปยังระดับที่ถูกแก้จริง เช่น 215 ข้อ 2 → 57 ข้อ 5 (5) (ก)

edges: contains (แม่ → ลูก) · refers_to (จุดที่อ้าง → node ที่ถูกอ้าง พร้อมวลี) · amends (ฉบับแก้ไข → node ที่ถูกแก้)
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_sources as cs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBINED = os.path.join(ROOT, "all_10_announcements_chunks_official.json")
OUT_JSON = os.path.join(ROOT, "hierarchy", "vat_hierarchy.json")
OUT_REPORT = os.path.join(ROOT, "reports", "hierarchy_report.md")

THAI = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
PARA_NUM = {"หนึ่ง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5, "หก": 6}
PARA_NAME = {v: k for k, v in PARA_NUM.items()}
CLAUSE_RE = re.compile(r"^\s*[“\"]?\s*\(([0-9๐-๙]+)\)\s*")
ITEM_RE = re.compile(r"^\s*[“\"]?\s*\(([ก-ฮ])\)\s*")
NOTE_RE = re.compile(r"^\s*\((?:แก้ไข|เพิ่ม)")
CHUNKER_LABEL_RE = re.compile(r"^\s*\(วรรค(?:ท้าย|สอง|สาม)\)\s*")
ART_HEAD_RE = re.compile(r"^\s*[“\"]?\s*ข้อ\s*([0-9๐-๙]+(?:/[0-9๐-๙]+)?)\s*(?=\(|\s|$)")
SPLIT_PREFIX_RE = re.compile(r"^\s*ข้อ\s*[0-9๐-๙]+\s*“\s*ข้อ\s*[0-9๐-๙]+(?=\()")   # 'ข้อ 2 “ข้อ 5(3)' (chunker)
SPLIT_PREFIX2_RE = re.compile(r"^\s*ข้อ\s*[0-9๐-๙]+(?=\([0-9๐-๙]+\))")              # 'ข้อ 5(3)' (chunker)


def norm(s: str) -> str:
    return (s or "").translate(THAI)


def skel(s: str) -> str:
    return cs.skeleton(s)


# ------------------------------------------------------------------ node store
class Store:
    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.order: list[str] = []
        self.edges: list[dict] = []

    def add(self, nid, **kw):
        if nid in self.nodes:
            i = 2
            while f"{nid}~{i}" in self.nodes:
                i += 1
            nid = f"{nid}~{i}"
        kw.setdefault("own_text", "")
        kw["id"] = nid
        self.nodes[nid] = kw
        self.order.append(nid)
        if kw.get("parent"):
            self.edges.append({"s": kw["parent"], "t": nid, "kind": "contains"})
        return nid

    def children(self, nid):
        return [e["t"] for e in self.edges if e["kind"] == "contains" and e["s"] == nid]


# ------------------------------------------------------------------ tokenising an article body
def tokens(lines: list[str]) -> list[tuple[str, str, str]]:
    """แต่ละบรรทัด -> (kind, key, text) kind: clause/item/para/note"""
    out = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        line = CHUNKER_LABEL_RE.sub("", line)
        n = norm(line)
        if m := CLAUSE_RE.match(n):
            out.append(("clause", m.group(1), line))
        elif m := ITEM_RE.match(line):
            out.append(("item", m.group(1), line))
        elif NOTE_RE.match(line):
            out.append(("note", "", line))
        else:
            out.append(("para", "", line))
    return out


def build_body(st: Store, root: str, toks: list[tuple[str, str, str]], label: str, meta: dict):
    """
    สร้างลูกของ root จาก token
    - para ก่อนมีรายการ หรือหลังรายการตัวสุดท้าย → วรรคของ root (รายการอนุผูกกับวรรคล่าสุดของ root)
    - para กลางรายการ: ถ้ามีย่อยตามมา → วรรคของย่อยปัจจุบัน · ถ้ามีอนุตามมา → วรรคของอนุปัจจุบัน
    """
    root_paras = []                    # [{"n", "text", "entries": [...]}]
    extra = defaultdict(list)          # node id -> วรรคที่สองเป็นต้นไป
    cur_clause = cur_item = None

    def next_struct(i):
        for t in toks[i + 1:]:
            if t[0] in ("clause", "item"):
                return t[0]
        return None

    for i, (kind, key, text) in enumerate(toks):
        if kind == "note":
            st.add(f"{root}/note", parent=root, level="note", label="หมายเหตุการแก้ไข", own_text=text, **meta)
            continue
        if kind == "para":
            nxt = next_struct(i)
            if cur_item and nxt == "item":
                extra[cur_item].append(text)
            elif cur_clause and nxt == "clause":
                extra[cur_clause].append(text)
            else:
                cur_clause = cur_item = None
                root_paras.append({"n": len(root_paras) + 1, "text": text, "entries": []})
            continue
        if not root_paras:
            root_paras.append({"n": 1, "text": "", "entries": []})
        if kind == "clause":
            cur_clause, cur_item = f"{root}/{key}", None
            root_paras[-1]["entries"].append(("clause", cur_clause, key, text, None))
        else:
            parent = cur_clause
            cur_item = f"{cur_clause}/{key}" if cur_clause else f"{root}/{key}"
            root_paras[-1]["entries"].append(("item", cur_item, key, text, parent))

    multi = len(root_paras) > 1
    root_own = []
    made = {}
    for p in root_paras:
        if multi:
            pid = st.add(f"{root}/p{p['n']}", parent=root, level="paragraph",
                         label=f"{label} วรรค{PARA_NAME.get(p['n'], p['n'])}", own_text=p["text"], para=p["n"], **meta)
        else:
            pid = root
            root_own.append(p["text"])
        for kind, nid, key, text, parent in p["entries"]:
            par = made.get(parent, pid) if parent else pid
            plabel = st.nodes[par]["label"] if parent else label
            made[nid] = st.add(nid, parent=par, level=kind, label=f"{plabel} ({key})", own_text=text, key=key, **meta)
    if root_own:
        st.nodes[root]["own_text"] = "\n".join(t for t in [st.nodes[root].get("own_text", "")] + root_own if t)
    for nid, texts in extra.items():
        real = made.get(nid, nid)
        if real not in st.nodes:
            continue
        node = st.nodes[real]
        for k, text in enumerate(texts, 2):
            st.add(f"{real}/p{k}", parent=real, level="paragraph",
                   label=f"{node['label']} วรรค{PARA_NAME.get(k, k)}", own_text=text, para=k, **meta)


# ------------------------------------------------------------------ article assembly
def article_key(cid: str) -> str:
    if cid.endswith("ATTACHMENT"):
        return "แนบท้าย"
    m = re.search(r"_ART_(\d+)(?:_(\d))?", cid)
    return f"{int(m.group(1))}/{m.group(2)}" if m.group(2) else str(int(m.group(1)))


def clean_split(text: str) -> str:
    t = SPLIT_PREFIX_RE.sub("", text, count=1)
    if t == text:
        t = SPLIT_PREFIX2_RE.sub("", text, count=1)
    return t


def merge_split(parts: list[tuple[str, str]]) -> str:
    """ประกอบข้อที่ถูกแบ่งหลาย chunk: หัว (ก่อนอนุแรก) จาก chunk แรก + อนุทั้งหมดเรียงตามเลข + วรรคปิดท้ายไม่ซ้ำ"""
    head, blocks, tails, seen_tail = [], {}, [], set()
    for idx, (cid, text) in enumerate(parts):
        lines = [ln for ln in (text if idx == 0 else clean_split(text)).split("\n") if ln.strip()]
        toks = tokens(lines)
        cur = None
        # วรรคหลังรายการตัวสุดท้ายของ chunk = วรรคปิดท้ายของข้อ
        last_struct = max((i for i, t in enumerate(toks) if t[0] in ("clause", "item")), default=-1)
        for i, (kind, key, line) in enumerate(toks):
            if kind == "clause":
                cur = int(key)
                blocks.setdefault(cur, [])
                blocks[cur].append(line) if not blocks[cur] else None
                if blocks[cur] and blocks[cur][0] != line and len(blocks[cur]) and skel(blocks[cur][0]) != skel(line):
                    blocks[cur].append(line)
                continue
            if cur is None:
                if idx == 0:
                    head.append(line)
                continue
            if i > last_struct and kind == "para":
                s = skel(line)
                if s not in seen_tail:
                    seen_tail.add(s)
                    tails.append(line)
                continue
            if skel(line) not in {skel(x) for x in blocks[cur]}:
                blocks[cur].append(line)
    out = head + [ln for k in sorted(blocks) for ln in blocks[k]] + tails
    return "\n".join(out)


INSTR_END_RE = re.compile(r"(และให้ใช้ความต่อไปนี้แทน|ให้ใช้ความต่อไปนี้แทน|ดังต่อไปนี้|ต่อไปนี้)")


def split_amendment(text: str) -> tuple[str, str]:
    """(คำสั่งแก้ไข, ข้อความใหม่) — ข้อความใหม่คือส่วนในเครื่องหมายคำพูด"""
    cands = [k for k in (text.find("“"), text.find('"')) if k >= 0]
    if not cands:
        return "", text
    i = min(cands)
    instr = text[:i].strip()
    body = text[i + 1:]
    j = max(body.rfind("”"), body.rfind('"'))
    if j >= 0:
        body = body[:j]
    return instr, body.strip()


def parse_amend_targets(instr: str, fallback_ann: str, fallback_art: str) -> list[str]:
    n = norm(instr)
    ann = re.search(r"\(ฉบับที่\s*(\d+)\)", n)
    ann = ann.group(1) if ann else fallback_ann
    cut = re.search(r"(ของ|แห่ง)\s*ประกาศ", n)
    head = n[:cut.start()] if cut else n
    art = re.findall(r"ข้อ\s*(\d+(?:/\d+)?)", head)
    if not art:
        return [f"VAT{ann}/{fallback_art.replace('/', '_')}"] if fallback_art else []
    art = art[-1]
    before = head[:head.rfind("ข้อ")]
    clauses = re.findall(r"\((\d+)\)", before)
    item = re.findall(r"\(([ก-ฮ])\)", before)
    para = re.search(r"วรรค(หนึ่ง|สอง|สาม|สี่|ท้าย)", before)
    base = f"VAT{ann}/{art.replace('/', '_')}"
    if item and clauses:
        return [f"{base}/{clauses[0]}/{item[0]}"]
    if clauses:
        return [f"{base}/{c}" for c in clauses]
    if para:
        return [f"{base}/p{PARA_NUM.get(para.group(1), 'last')}"]
    return [base]


def build(chunks: list[dict]) -> tuple[Store, list[dict]]:
    st = Store()
    problems = []
    by_ann = defaultdict(lambda: defaultdict(list))
    for c in chunks:
        ann = c["chunk_id"].split("_")[0].replace("VAT", "")
        by_ann[ann][article_key(c["chunk_id"])].append(c)

    for ann in sorted(by_ann, key=int):
        st.add(f"VAT{ann}", level="announcement", label=f"ฉบับ {ann}", ann=ann)
        for akey in sorted(by_ann[ann], key=lambda k: (k == "แนบท้าย", [int(x) for x in re.findall(r"\d+", k)] or [999])):
            group = sorted(by_ann[ann][akey], key=lambda c: c["chunk_id"])
            md = group[0]["metadata"]
            meta = {"ann": ann, "chunk_ids": [c["chunk_id"] for c in group], "role": md.get("role"),
                    "current": md.get("is_current", True), "boiler": md.get("is_boilerplate", False)}
            texts = [(c["chunk_id"], c["official_raw_text"]) for c in group]
            aid_key = akey.replace("/", "_")
            if akey == "แนบท้าย":
                build_attachment(st, ann, texts[0][1], meta)
                continue
            role = md.get("role")
            if role == "amendment" and ann != "74":
                instr, body = split_amendment(texts[0][1])
                own_no = ART_HEAD_RE.match(norm(instr)).group(1) if ART_HEAD_RE.match(norm(instr)) else akey
                if len(texts) > 1:
                    body = merge_split([(texts[0][0], body)] + [(cid, clean_split(t).lstrip("“")) for cid, t in texts[1:]])
                aid = st.add(f"VAT{ann}/{own_no}", parent=f"VAT{ann}", level="article", label=f"ฉบับ {ann} ข้อ {own_no}",
                             own_text=instr if body else texts[0][1], **meta)
                if not body:
                    build_body(st, aid, tokens(texts[0][1].split("\n")[1:]), st.nodes[aid]["label"], meta)
                    continue
                tgt_ann, tgt_art = (md.get("amends_article") or ":").split(":")
                tgt_art = tgt_art.replace("ข้อ", "").strip()
                content_root(st, aid, body, ann, tgt_ann, tgt_art, meta)
                for t in parse_amend_targets(instr, tgt_ann, tgt_art):
                    st.edges.append({"s": f"{aid}/ใหม่", "t": t, "kind": "amends", "phrase": instr[:160]})
                continue
            if role == "amendment" and ann == "74":
                # ฉบับ 74: ข้อ 1 แทนที่ข้อ 4 ของ 57 (มีคำสั่ง) · ข้อ 2 เพิ่มข้อ 5–10 (chunk เก็บเฉพาะข้อความที่เพิ่ม)
                tgt_ann, tgt_art = (md.get("amends_article") or ":").split(":")
                tgt_art = tgt_art.replace("ข้อ", "").strip()
                if akey == "4":
                    instr, body = split_amendment(texts[0][1])
                    aid = st.add("VAT74/1", parent="VAT74", level="article", label="ฉบับ 74 ข้อ 1", own_text=instr, **meta)
                    content_root(st, aid, body, ann, tgt_ann, tgt_art, meta)
                    for t in parse_amend_targets(instr, tgt_ann, tgt_art):
                        st.edges.append({"s": f"{aid}/ใหม่", "t": t, "kind": "amends", "phrase": instr[:160]})
                else:
                    if "VAT74/2" not in st.nodes:
                        st.add("VAT74/2", parent="VAT74", level="article", label="ฉบับ 74 ข้อ 2",
                               own_text="", note="ข้อ 2 ของฉบับ 74 เพิ่มข้อ 5 ถึงข้อ 10 ในฉบับ 57 (chunk เก็บเฉพาะข้อความที่เพิ่ม)",
                               **{**meta, "chunk_ids": []})
                    st.nodes["VAT74/2"]["chunk_ids"] += meta["chunk_ids"]
                    body = merge_split(texts) if len(texts) > 1 else texts[0][1]
                    rid = st.add(f"VAT74/2/ข้อ{akey}", parent="VAT74/2", level="content",
                                 label=f"ฉบับ 74: ข้อความที่เพิ่มเป็นฉบับ 57 ข้อ {akey}", base_ann=tgt_ann, base_art=tgt_art, **meta)
                    lines = body.split("\n")
                    st.nodes[rid]["own_text"] = ""
                    build_body(st, rid, tokens(lines), st.nodes[rid]["label"], {**meta, "base_ann": tgt_ann, "base_art": tgt_art})
                    st.edges.append({"s": rid, "t": f"VAT{tgt_ann}/{tgt_art.replace('/', '_')}", "kind": "amends",
                                     "phrase": f"เพิ่มข้อ {tgt_art} ในฉบับ {tgt_ann}"})
                continue
            # ---- ตัวบทหลัก / DBD / ข้อท้ายประกาศ
            body = merge_split(texts) if len(texts) > 1 else texts[0][1]
            body = body.replace("“", "").replace("”", "")
            lines = [ln for ln in body.split("\n") if ln.strip()]
            m = re.match(r"^\s*ข้อ\s*\S+?\s*(?=\(|\s|$)", lines[0])
            head_txt = lines[0]
            aid = st.add(f"VAT{ann}/{aid_key}", parent=f"VAT{ann}", level="article", label=f"ฉบับ {ann} ข้อ {akey}",
                         own_text="", base_ann=ann, base_art=akey, **meta)
            build_body(st, aid, tokens([head_txt] + lines[1:]), st.nodes[aid]["label"], {**meta, "base_ann": ann, "base_art": akey})
            if not m:
                problems.append({"id": aid, "problem": "ไม่พบหัว 'ข้อ N' ในบรรทัดแรก"})
    return st, problems


def content_root(st: Store, aid: str, body: str, ann: str, tgt_ann: str, tgt_art: str, meta: dict):
    lines = [ln for ln in body.split("\n") if ln.strip()]
    first = norm(lines[0]) if lines else ""
    label = f"ฉบับ {ann}: ข้อความใหม่ของฉบับ {tgt_ann} ข้อ {tgt_art}"
    m = re.match(r"^\s*[“\"]?\s*ข้อ\s*\S+?\s*(?=\(|\s|$)", lines[0]) if lines else None
    rid = st.add(f"{aid}/ใหม่", parent=aid, level="content", label=label, base_ann=tgt_ann, base_art=tgt_art, **meta)
    build_body(st, rid, tokens(lines), label, {**meta, "base_ann": tgt_ann, "base_art": tgt_art})
    return rid


ATT_SEC_RE = re.compile(r"^\s*(\d+)\.\s")
ATT_SUB_RE = re.compile(r"^\s*(\d+)\.(\d+)\s")


def build_attachment(st: Store, ann: str, text: str, meta: dict):
    root = st.add(f"VAT{ann}/แนบท้าย", parent=f"VAT{ann}", level="article", label=f"ฉบับ {ann} เอกสารแนบท้าย",
                  own_text="", base_ann=ann, base_art="แนบท้าย", **meta)
    group = st.add(f"{root}/g1", parent=root, level="group", label="แบบคำขอจดทะเบียน", own_text="", **meta)
    gi, sec, sub = 1, None, None
    for line in [ln for ln in text.split("\n") if ln.strip()]:
        n = norm(line)
        if m := ATT_SUB_RE.match(n):
            par = sec or group
            sub = st.add(f"{par}/{m.group(2)}", parent=par, level="clause", label=f"{st.nodes[par]['label']}.{m.group(2)}",
                         own_text=line, **meta)
        elif m := ATT_SEC_RE.match(n):
            sec = st.add(f"{group}/{m.group(1)}", parent=group, level="clause", label=f"{m.group(1)}", own_text=line, **meta)
            sub = None
        elif m := CLAUSE_RE.match(n):
            par = sub or sec or group
            st.add(f"{par}/{m.group(1)}", parent=par, level="item", label=f"({m.group(1)})", own_text=line, **meta)
        elif len(line.strip()) < 45 and not line.strip().startswith("**") and sec is not None:
            gi += 1
            group = st.add(f"{root}/g{gi}", parent=root, level="group", label=line.strip(), own_text=line, **meta)
            sec = sub = None
        else:
            target = sub or sec or group
            st.nodes[target]["own_text"] = (st.nodes[target]["own_text"] + "\n" + line).strip()


# ------------------------------------------------------------------ references
REF_RE = re.compile(
    r"(?P<pre>ตาม|ใน|ของ|แห่ง|กับ)?\s*"
    r"(?:"
    r"(?P<mat>มาตรา\s*\d+(?:/\d+)?(?:\s*\(\d+\))?(?:\s*\([ก-ฮ]\))?(?:\s*ถึง\s*\([ก-ฮ]\))?)"
    r"|(?P<art>ข้อ\s*\d+(?:/\d+)?)(?P<artc>(?:\s*\(\d+\))?)(?P<arti>(?:\s*\([ก-ฮ]\))?)(?P<artp>(?:\s*วรรค(?:หนึ่ง|สอง|สาม|สี่|ท้าย))?)"
    r"|(?P<rng>\(\d+\)\s*ถึง\s*\(\d+\))"
    r"|(?P<ci>\(\d+\)\s*\([ก-ฮ]\))"
    r"|(?P<c1>\(\d+\))"
    r"|(?P<para>วรรค(?:หนึ่ง|สอง|สาม|สี่|ท้าย))"
    r")"
)
ANN_AFTER_RE = re.compile(r"^.{0,140}?\(ฉบับที่\s*(\d+)\)")
CODE_AFTER_RE = re.compile(r"^\s*(?:แห่ง)?\s*(ประมวลรัษฎากร|ประมวลกฎหมายอาญา)")


def container_of(st: Store, nid: str) -> str:
    """article/content ที่ node นี้อยู่ (ใช้เป็นฐานของ (1), (1) ถึง (3))"""
    cur = nid
    while cur and st.nodes[cur]["level"] not in ("article", "content"):
        cur = st.nodes[cur].get("parent")
    return cur


def para_target(st: Store, nid: str, k: int | str) -> str | None:
    """'วรรคหนึ่ง' ที่ไม่ระบุข้อ = วรรคของ node ที่ครอบอยู่ (ย่อย/อนุ/ข้อ ที่มีหลายวรรค)"""
    cur = nid
    while cur:
        node = st.nodes[cur]
        par = node.get("parent")
        if node["level"] == "paragraph" and par:
            kids = [c for c in st.children(par) if st.nodes[c]["level"] == "paragraph"]
            if k == "last":
                return kids[-1] if kids else par
            if k == 1 and not any(st.nodes[c].get("para") == 1 for c in kids):
                return par               # วรรคหนึ่งคือข้อความของ node แม่เอง
            hit = [c for c in kids if st.nodes[c].get("para") == k]
            return hit[0] if hit else par
        if node["level"] in ("article", "content"):
            kids = [c for c in st.children(cur) if st.nodes[c]["level"] == "paragraph"]
            hit = [c for c in kids if st.nodes[c].get("para") == k]
            if hit:
                return hit[0]
            if node["level"] == "content" and node.get("base_art"):
                # ข้อความใหม่ที่เพิ่มเป็นวรรคหนึ่งวรรคใดของข้อเดิม: 'วรรคหนึ่ง' หมายถึงวรรคของข้อในตัวบทหลัก
                base = f"VAT{node['base_ann']}/{node['base_art'].replace('/', '_')}"
                bp = f"{base}/p{k}"
                return bp if bp in st.nodes else base
            return cur
        cur = par
    return None


def resolve_refs(st: Store) -> list[dict]:
    unresolved = []
    ext = {}
    for nid in list(st.order):
        node = st.nodes[nid]
        text = node.get("own_text") or ""
        if not text or node["level"] in ("announcement", "note"):
            continue
        if node["level"] == "article" and node.get("role") == "amendment":
            continue                      # คำสั่งแก้ไข → ใช้ amends แทน
        cont = container_of(st, nid)
        base_ann = st.nodes[cont].get("base_ann", node["ann"]) if cont else node["ann"]
        base_art = (st.nodes[cont].get("base_art") if cont else None) or ""
        # article id ของฐาน (ในประกาศที่ข้อความนี้ใช้บังคับ)
        own_art_id = cont
        n = norm(text)
        # ตัดเลขหัวของ node ตัวเองออก (เช่น '(3) ' ต้นอนุ, 'ข้อ 5 ' ต้นข้อ)
        lead = re.match(r"^\s*(?:[“\"]?\s*ข้อ\s*\d+(?:/\d+)?\s*)?(?:\(\d+\)\s*)?(?:\([ก-ฮ]\)\s*)?", n)
        start = lead.end() if lead else 0
        for m in REF_RE.finditer(n, start):
            phrase = m.group(0).strip()
            targets = []
            after = n[m.end():]
            if m.group("mat"):
                code = CODE_AFTER_RE.match(after)
                book = code.group(1) if code else "ประมวลรัษฎากร"
                num = re.search(r"มาตรา\s*(\d+(?:/\d+)?)", m.group("mat")).group(1)
                eid = f"EXT/{book}/ม.{num}"
                if eid not in st.nodes:
                    st.add(eid, level="external", label=f"{book} มาตรา {num}", ann="", own_text="")
                targets = [eid]
            elif m.group("art"):
                if not m.group("pre") and not re.search(r"(ตาม|ใน|ของ|แห่ง|ตามความใน)\s*$", n[:m.start()]):
                    pass
                art = re.search(r"\d+(?:/\d+)?", m.group("art")).group(0)
                a2 = ANN_AFTER_RE.match(after)
                ann = a2.group(1) if a2 else base_ann
                t = f"VAT{ann}/{art.replace('/', '_')}"
                c = re.search(r"\d+", m.group("artc") or "")
                i = re.search(r"[ก-ฮ]", m.group("arti") or "")
                p = re.search(r"วรรค(\S+)", m.group("artp") or "")
                if c:
                    t += f"/{c.group(0)}"
                if i:
                    t += f"/{i.group(0)}"
                if p and not c:
                    k = PARA_NUM.get(p.group(1), "last")
                    t2 = f"{t}/p{k}"
                    t = t2 if t2 in st.nodes else t
                targets = [t]
            elif m.group("rng"):
                a, b = map(int, re.findall(r"\d+", m.group("rng")))
                targets = [f"{own_art_id}/{k}" for k in range(a, b + 1)]
            elif m.group("ci"):
                c, i = re.findall(r"\d+|[ก-ฮ]", m.group("ci"))
                targets = [f"{own_art_id}/{c}/{i}"]
            elif m.group("c1"):
                if not m.group("pre"):
                    continue                  # '(1)' เฉยๆ กลางประโยคมักเป็นหัวข้อย่อยในบรรทัด ไม่ใช่การอ้าง
                targets = [f"{own_art_id}/{re.search(r'[0-9]+', m.group('c1')).group(0)}"]
            elif m.group("para"):
                if re.search(r"(ข้อ|มาตรา)\s*\d+(?:/\d+)?\s*$", n[:m.start()]):
                    continue                  # 'มาตรา 81/3 วรรคหนึ่ง' = วรรคของกฎหมายอื่น / 'ข้อ N วรรค..' จับในกลุ่ม art แล้ว
                k = PARA_NUM.get(m.group("para")[4:], "last")
                t = para_target(st, nid, k)
                targets = [t] if t else []
            for t in targets:
                t = resolve_alias(st, t)
                if t and t in st.nodes and t != nid:
                    st.edges.append({"s": nid, "t": t, "kind": "refers_to", "phrase": phrase})
                else:
                    unresolved.append({"from": nid, "label": node["label"], "phrase": phrase, "target": t})
    return unresolved


def resolve_alias(st: Store, t: str | None) -> str | None:
    """id ที่ชี้ไปยังข้อของตัวบทหลัก: ถ้าไม่มี node ตรงตัว ลองระดับที่สูงกว่า (เช่น 5/1/ก → 5/1)"""
    if not t or t in st.nodes:
        return t
    return t


# ------------------------------------------------------------------ checks
def exact_coverage(text: str, parts: list[str]) -> tuple[float, list[str]]:
    """สัดส่วนของ text ที่มี node ข้อความตรงตัวครอบ (หา node แต่ละตัวเป็น substring) + ช่วงที่ไม่มีใครครอบ"""
    covered = [False] * len(text)
    for p in parts:
        if not p:
            continue
        i = text.find(p)
        while i >= 0:
            covered[i:i + len(p)] = [True] * len(p)
            i = text.find(p, i + 1)
    gaps, start = [], None
    for i, ok in enumerate(covered + [True]):
        if not ok and start is None:
            start = i
        elif ok and start is not None:
            if i - start >= 3:
                gaps.append(text[start:i])
            start = None
    return (sum(covered) / len(text) if text else 1.0), gaps


def check_coverage(st: Store, chunks: list[dict]) -> list[dict]:
    """ข้อความของทุก chunk ต้องอยู่ใน own_text ของ node ที่มาจาก chunk นั้น (ยกเว้นคำที่ chunker เติม)"""
    by_chunk = defaultdict(list)
    for nid in st.order:
        node = st.nodes[nid]
        for cid in node.get("chunk_ids") or []:
            if node.get("own_text"):
                by_chunk[cid].append(skel(node["own_text"]))
    rows = []
    for c in chunks:
        raw = CHUNKER_LABEL_RE.sub("", c["official_raw_text"])
        raw = "\n".join(CHUNKER_LABEL_RE.sub("", ln) for ln in raw.split("\n"))
        raw = clean_split(raw)
        cov, gaps = exact_coverage(skel(raw), by_chunk[c["chunk_id"]])
        rows.append({"chunk": c["chunk_id"], "coverage": round(cov, 4), "gaps": gaps[:3]})
    return rows


def main() -> None:
    chunks = json.load(open(COMBINED, encoding="utf-8"))
    st, problems = build(chunks)
    unresolved = resolve_refs(st)
    for e in [e for e in st.edges if e["kind"] == "amends"]:
        if e["t"] not in st.nodes:
            unresolved.append({"from": e["s"], "label": st.nodes[e["s"]]["label"], "phrase": e["phrase"], "target": e["t"], "kind": "amends"})
    cov = check_coverage(st, chunks)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    nodes = [st.nodes[n] for n in st.order]
    for n in nodes:
        n["own_text"] = (n.get("own_text") or "").strip()
    data = {"nodes": nodes, "edges": st.edges, "unresolved": unresolved, "coverage": cov, "problems": problems}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    write_report(st, data)
    lv = defaultdict(int)
    for n in nodes:
        lv[n["level"]] += 1
    kinds = defaultdict(int)
    for e in st.edges:
        kinds[e["kind"]] += 1
    low = [r for r in cov if r["coverage"] < 0.995]
    print(f"nodes {dict(lv)}")
    print(f"edges {dict(kinds)}")
    print(f"ข้อความครบ: {len(cov) - len(low)}/{len(cov)} chunk  (ต่ำกว่า 99.5%: {[r['chunk'] for r in low]})")
    print(f"การอ้างอิงที่ resolve ไม่ได้: {len(unresolved)}")
    print(f"เขียนแล้ว: {OUT_JSON}, {OUT_REPORT}")


def write_report(st: Store, data: dict):
    lines = ["# ลำดับชั้นตัวบท (ข้อ → วรรค → อนุ → ย่อย) และการอ้างอิง", "",
             "สร้างโดย `scripts/build_hierarchy.py` จาก official_raw_text ของ chunk 75 ชิ้น (ไม่แก้ chunk เดิม)", ""]
    per = defaultdict(lambda: defaultdict(int))
    for n in data["nodes"]:
        if n["level"] not in ("announcement", "external"):
            per[n["ann"]][n["level"]] += 1
    lines += ["## จำนวน node ต่อฉบับ", "", "| ฉบับ | ข้อ | ข้อความใหม่ | วรรค | อนุ | ย่อย | หมายเหตุ/กลุ่ม |", "|---|---|---|---|---|---|---|"]
    for ann in sorted(per, key=lambda x: int(x)):
        d = per[ann]
        lines.append(f"| {ann} | {d['article']} | {d['content']} | {d['paragraph']} | {d['clause']} | {d['item']} | {d['note'] + d['group']} |")
    kinds = defaultdict(int)
    for e in data["edges"]:
        kinds[e["kind"]] += 1
    lines += ["", f"เส้นเชื่อม: contains {kinds['contains']} · refers_to {kinds['refers_to']} · amends {kinds['amends']}", ""]
    low = [r for r in data["coverage"] if r["coverage"] < 0.995]
    lines += ["## ตรวจความครบของข้อความ", "",
              f"{len(data['coverage']) - len(low)} จาก {len(data['coverage'])} chunk ข้อความอยู่ครบใน node (≥ 99.5%)", ""]
    for r in low:
        lines.append(f"- `{r['chunk']}` {r['coverage']:.1%} — ส่วนที่ไม่พบ: {' / '.join(g[:60] for g in r['gaps'])}")
    lines += ["", "## การอ้างอิงที่ resolve ไม่ได้ (ต้องให้คนตรวจ)", ""]
    if not data["unresolved"]:
        lines.append("ไม่มี")
    else:
        lines += ["| จาก | วลี | เป้าหมายที่คาด |", "|---|---|---|"]
        for u in data["unresolved"]:
            lines.append(f"| {u['label']} | {u['phrase']} | `{u['target']}` |")
    lines += ["", "## การแก้ไขระดับอนุ (amends)", "", "| ฉบับแก้ไข | แก้ที่ |", "|---|---|"]
    for e in data["edges"]:
        if e["kind"] == "amends":
            src = st.nodes[e["s"]]
            tgt = st.nodes.get(e["t"], {"label": e["t"]})
            lines.append(f"| {src['label'].replace('ข้อความใหม่ ', '')} ({src['chunk_ids'][0] if src.get('chunk_ids') else ''}) | {tgt['label']} |")
    os.makedirs(os.path.dirname(OUT_REPORT), exist_ok=True)
    open(OUT_REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
