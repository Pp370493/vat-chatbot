# -*- coding: utf-8 -*-
"""ตัวช่วยร่วมของชุด 09_graphrag: normalize ข้อความ, ตัดคำ, ขยายคำค้นด้วยตารางคำพ้อง, แยกการอ้างอิงตรง (ม./ข้อ/ฉบับ), BM25
ไม่พึ่งอินเทอร์เน็ต (ใช้ numpy + pythainlp + scikit-learn)"""
import re, json, os, math, unicodedata, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))      # รากของ repo vat-chatbot
FIN = REPO
DATA = os.environ.get('VAT_DATA_DIR') or os.path.join(REPO, 'data')
EMB = os.path.join(DATA, 'embeddings')
TD = str.maketrans('๐๑๒๓๔๕๖๗๘๙', '0123456789')
ORD_TH = {'หนึ่ง': 1, 'สอง': 2, 'สาม': 3, 'สี่': 4, 'ห้า': 5, 'หก': 6, 'เจ็ด': 7, 'แปด': 8, 'เก้า': 9, 'สิบ': 10}

def jload(path):
    with open(path, encoding='utf-8') as f: return json.load(f)

# ---------------------------------------------------------------- normalize
def norm_text(s):
    """NFC, ลบอักขระล่องหน, สระอำ, เลขไทย→อารบิก, ตัวพิมพ์เล็ก, เลข/รหัสมาตรฐาน (ภพNN, มาตราN_M, ฉบับN, ข้อN_M), ยุบช่องว่าง"""
    x = unicodedata.normalize('NFC', s or '').translate(TD).lower()
    x = re.sub('[​‌‍﻿]', '', x).replace('ํา', 'ำ')
    # แบบ ภ.พ.NN / PPNN / por por NN → ภพNN
    pp = lambda m: ' ภพ%02d ' % int(m.group(1))
    x = re.sub(r'ภ[\s\.\-]*พ[\s\.\-_:/]*0*(\d{1,2})(?!\d)', pp, x)
    x = re.sub(r'(?<![a-z])p[\s\.\-]*p[\s\.\-_:/]*0*(\d{1,2})(?!\d)', pp, x)
    x = re.sub(r'(?:por|phor)[\s\.\-]*(?:por|phor)[\s\.\-_:/]*0*(\d{1,2})(?!\d)', pp, x)
    # มาตรา / ม. / sec → มาตราN หรือ มาตราN_M
    x = re.sub(r'(?:มาตรา|(?<![ก-๙a-z])(?:ม\.|ม(?=\s*\d)|sec(?:tion)?\.?|s\.|m\.))\s*(\d{1,3})\s*[/／⁄\\_\-]\s*(\d{1,3})(?!\d)', r' มาตรา\1_\2 ', x)
    x = re.sub(r'(?:มาตรา|(?<![ก-๙a-z])(?:ม\.|ม(?=\s*\d)|sec(?:tion)?\.?|s\.|m\.))\s*(\d{1,3})(?![\d_/])', r' มาตรา\1 ', x)
    # ฉบับ
    x = re.sub(r'(?:ฉบับที่|ฉบับ|ฉ\.|notification(?:\s*no\.?)?|no\.?)\s*(\d{1,3})(?!\d)', r' ฉบับ\1 ', x)
    # ข้อ N, ข้อ N/M
    x = re.sub(r'ข้อ\s*(\d{1,2})\s*/\s*(\d{1,2})(?!\d)', r' ข้อ\1_\2 ', x)
    x = re.sub(r'ข้อ\s*(\d{1,2})(?![\d_])', r' ข้อ\1 ', x)
    return re.sub(r'\s+', ' ', x).strip()

_NEWMM = None
def _tok():
    global _NEWMM
    if _NEWMM is None:
        from pythainlp.tokenize import word_tokenize
        _NEWMM = lambda s: word_tokenize(s, engine='newmm', keep_whitespace=False)
    return _NEWMM

_CODE = re.compile(r'((?:มาตรา|ฉบับ|ข้อ|ภพ)\d+(?:_\d+)?)')
def words(s, normed=False):
    """ตัดคำ newmm แต่เก็บรหัสมาตรฐาน (มาตรา81_3 / ฉบับ159 / ข้อ5 / ภพ20) เป็นโทเคนเดียว"""
    x = s if normed else norm_text(s)
    out = []
    for seg in _CODE.split(x):
        if _CODE.fullmatch(seg): out.append(seg); continue
        for t in _tok()(seg):
            t = t.strip()
            if not t or re.fullmatch(r'[\W_]+', t): continue
            out.append(t)
    return out

def char_grams(s, n=3, normed=False):
    x = re.sub(r'[\s\W_]+', '', s if normed else norm_text(s))
    return [x[i:i + n] for i in range(len(x) - n + 1)] if len(x) >= n else ([x] if x else [])

# ---------------------------------------------------------------- BM25
class BM25:
    """Okapi BM25 บนรายการโทเคนที่กำหนดเอง"""
    def __init__(self, docs, k1=1.4, b=0.75):
        self.k1, self.b = k1, b
        self.N = len(docs); self.dl = np.array([len(d) for d in docs], float); self.avg = max(self.dl.mean(), 1e-9)
        self.tf = [collections.Counter(d) for d in docs]
        df = collections.Counter(); [df.update(t.keys()) for t in self.tf]
        self.idf = {t: math.log(1 + (self.N - n + .5) / (n + .5)) for t, n in df.items()}
        self.inv = collections.defaultdict(list)
        for i, t in enumerate(self.tf):
            for w, c in t.items(): self.inv[w].append((i, c))
    def scores(self, q):
        sc = np.zeros(self.N)
        for w in set(q):
            if w not in self.idf: continue
            idf = self.idf[w]
            for i, c in self.inv[w]:
                sc[i] += idf * c * (self.k1 + 1) / (c + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avg))
        return sc

# ---------------------------------------------------------------- ขยายคำค้นด้วยตารางคำพ้อง
class Expander:
    """หาคำพ้อง/ภาษาพูด/อังกฤษ/สะกดผิดในคำถาม แล้วคืน (ข้อความขยาย, concept ที่พบ, คำที่แก้)
    ข้ามรูปที่กำกวม (relation != '') และความมั่นใจต่ำ — ไม่แทนที่ข้อความเดิม เพียง 'เติม' คำมาตรฐาน"""
    SKIP_TYPES = ('ตัวพิมพ์เล็ก/ใหญ่', 'เว้นวรรค/จุด/ขีด')
    SHORT_OK = {'vat', 'แวท', 'แวต', 'tin', 'ทิน', 'lto', 'dbd', 'rd', 'jv', 'poa'}
    GENERIC = {'มาตรา', 'วรรค / อนุ / ย่อย', 'ข้อ', 'ฉบับ', 'ประกาศ', 'นิติบุคคล'}      # คำโครงสร้างทั่วไป ไม่เติมเป็นคำค้น
    def __init__(self, path=None):
        J = jload(path or os.path.join(DATA, 'term_variants.json'))
        self.concepts = {c['id']: c for c in J['concepts']}
        self.map = {}                           # key(norm) -> (canonical_norm, concept_id)
        for v in J['variants']:
            if v['relation'] or v['confidence'] == 'ต่ำ' or any(k in v['type'] for k in self.SKIP_TYPES): continue
            k = norm_text(v['variant']); can = norm_text(v['canonical'])
            if not k or k == can or can in self.GENERIC or (len(k) < 3 and k not in self.SHORT_OK): continue
            if re.fullmatch(r'[\d\s%\.]+', k): continue
            self.map.setdefault(k, (can, v['concept']))
        ex = os.path.join(DATA, 'term_variants_extra.json')          # คำพ้องเสริมกลุ่มขอบเขต/ใบกำกับภาษี (ไม่ทับตารางคำพ้องของผู้ใช้)
        if os.path.exists(ex):
            for c in jload(ex)['concepts']:
                self.concepts[c['id']] = {'id': c['id'], 'canonical': c['canonical'], 'chunks': c.get('chunks', [])}
                for v in c['variants']:
                    k = norm_text(v); can = norm_text(c['canonical'])
                    if k and k != can and (len(k) >= 3 or k in self.SHORT_OK): self.map.setdefault(k, (can, c['id']))
        self.typos = {}
        for t in J['typos']:
            k = norm_text(t['typo']); c = norm_text(t['correct'])
            if k and k != c and len(k) >= 3: self.typos.setdefault(k, c)
        keys = sorted(set(self.map) | set(self.typos), key=len, reverse=True)
        self.rx = re.compile('|'.join(('(?<![a-z0-9])' + re.escape(k) + '(?![a-z0-9])') if re.fullmatch(r'[a-z0-9 \.\-]+', k) else re.escape(k) for k in keys))
    def expand(self, q):
        nq = norm_text(q); add, concepts, fixes = [], [], []
        from pythainlp.tokenize import word_tokenize
        bounds = {0}; pos = 0
        for t in word_tokenize(nq, engine='newmm', keep_whitespace=True): pos += len(t); bounds.add(pos)
        for m in self.rx.finditer(nq):
            k = m.group(0)
            if k in self.typos and not nq.startswith(self.typos[k], m.start()):      # ไม่ใช่ส่วนต้นของคำที่สะกดถูกอยู่แล้ว (เช่น 'มาตร' ใน 'มาตรา')
                fixes.append((k, self.typos[k])); add.append(self.typos[k])
            if k in self.map:
                latin = re.fullmatch(r'[a-z0-9 \.\-]+', k) is not None
                if not latin and not (m.start() in bounds and m.end() in bounds): continue   # กันจับกลางคำ เช่น 'ปิดร้าน' ใน 'เปิดร้าน'
                can, cid = self.map[k]; add.append(can); concepts.append(cid)
        seen = set(); add = [a for a in add if not (a in seen or seen.add(a))]
        return {'norm': nq, 'text': (nq + ' ' + ' '.join(add)).strip(), 'added': add, 'concepts': list(dict.fromkeys(concepts)), 'fixes': fixes}

# ---------------------------------------------------------------- การอ้างอิงตรง
def parse_citations(q):
    """คืน sections [(เลขมาตรา '81/3', วรรค|None)], anns [เลขฉบับ], articles [(เลขข้อ '5' | '4/1', ฉบับ|None)]"""
    x = unicodedata.normalize('NFC', q or '').translate(TD).lower()
    secs = []
    for m in re.finditer(r'(?:มาตรา|(?<![ก-๙a-z])(?:ม\.|ม(?=\s*\d)|sec(?:tion)?\.?|s\.|m\.))\s*(\d{1,3})(?:\s*[/／⁄\\_\-]\s*(\d{1,3}))?(?![\d])(?:\s*วรรค\s*(หนึ่ง|สอง|สาม|สี่|ห้า|หก|เจ็ด|แปด|เก้า|สิบ|\d+))?', x):
        sec = m.group(1) + ('/' + m.group(2) if m.group(2) else ''); p = m.group(3)
        secs.append((sec, ORD_TH.get(p, int(p) if p and p.isdigit() else None)))
    anns = [m.group(1) for m in re.finditer(r'(?:ฉบับที่|ฉบับ|ฉ\.|notification(?:\s*no\.?)?|no\.?)\s*(\d{1,3})(?!\d)', x)]
    arts = []
    for m in re.finditer(r'ข้อ\s*(\d{1,2})(?:\s*/\s*(\d{1,2}))?(?![\d])', x):
        art = m.group(1) + ('/' + m.group(2) if m.group(2) else '')
        tail = x[m.end():m.end() + 25]; ann = re.search(r'ฉบับ(?:ที่)?\s*(\d{1,3})', tail)
        arts.append((art, ann.group(1) if ann else (anns[0] if len(anns) == 1 else None)))
    return {'sections': secs, 'anns': anns, 'articles': arts}

def chunk_key(cid):
    """VAT57_ART_04_1 -> ('57','4/1',''), VAT57_ART_05_A -> ('57','5','A'), RC_S81_3 -> ('RC','81/3','')"""
    m = re.match(r'VAT(\d+)_ART_ATTACHMENT$', cid)
    if m: return (m.group(1), 'ATTACHMENT', '')
    m = re.match(r'VAT(\d+)_ART_(\d+)(?:_(\d+))?(?:_([A-Z]))?$', cid)
    if m: return (m.group(1), str(int(m.group(2))) + ('/' + m.group(3) if m.group(3) else ''), m.group(4) or '')
    m = re.match(r'RC_S(\d+)(?:_(\d+))?(?:_([A-Z]))?$', cid)
    if m: return ('RC', m.group(1) + ('/' + m.group(2) if m.group(2) else ''), m.group(3) or '')
    return (None, None, '')

def rrf(rank_lists, k=60, weights=None):
    """Reciprocal Rank Fusion: rank_lists = [[id,...], ...] -> {id: score}"""
    out = collections.defaultdict(float)
    for j, L in enumerate(rank_lists):
        w = (weights or [1] * len(rank_lists))[j]
        for r, i in enumerate(L): out[i] += w / (k + r + 1)
    return out
