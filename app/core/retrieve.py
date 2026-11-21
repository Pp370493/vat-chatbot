# -*- coding: utf-8 -*-
"""ตัวค้น multilevel Graph RAG
ขั้นตอน: normalize+ขยายคำพ้อง -> อ้างอิงตรง (ม./ข้อ/ฉบับ) -> route ระดับบน (L3 ชุมชน, L2 เอกสาร) -> ค้นไฮบริด L0/L1 (เวกเตอร์ + BM25 คำ + BM25 char)
        -> ขยายตามเส้นเชื่อม (≤2 hop, กรองสถานะ/ความสำคัญ) -> ประกอบบริบท parent-child พร้อมอ้างอิง
ใช้เป็นโมดูล: R = Retriever(); R.search('คำถาม', k=8)   หรือ CLI: python3 retrieve.py "คำถาม" --k 5"""
import os, re, sys, json, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from common import (DATA, EMB, norm_text, words, char_grams, BM25, Expander, parse_citations, chunk_key, jload)

def find_data(data, name):
    """หาไฟล์ใน data/ หรือในโฟลเดอร์ย่อย 'ตัวชี้และตาราง' (ตำแหน่งที่ repo เก็บ)"""
    for p in (os.path.join(data, name), os.path.join(data, 'ตัวชี้และตาราง', name)):
        if os.path.exists(p): return p
    return os.path.join(data, name)
from embedders import load_embedder

HISTORY = ('ประวัติ', 'ก่อนแก้ไข', 'แก้ไขโดย', 'ฉบับแก้ไข', 'ยกเลิกความ', 'แก้ไขอะไร', 'ถูกแก้', 'ฉบับเดิม', 'ข้อความเดิม', 'amend', 'history')
DOC_INTENT = ('เอกสาร', 'แนบ', 'หลักฐาน', 'ใช้อะไรบ้าง', 'ต้องมีอะไร', 'document')
APPLICANT = {   # คำที่บ่งชนิดผู้ยื่น -> คอลัมน์ในตารางเอกสารแนบกรมสรรพากร (data/doc_requirements.json)
    'individual': ('บุคคลธรรมดา', 'ฟรีแลนซ์', 'คนไทย', 'ร้านค้า', 'แม่ค้า'),
    'unincorporated': ('คณะบุคคล', 'ห้างหุ้นส่วนสามัญ', 'หุ้นส่วนสามัญ', 'คู่สมรส', 'สามีภรรยา', 'สามีภริยา', 'ผัวเมีย', 'กองทุน', 'มูลนิธิ'),
    'company': ('บริษัท', 'ห้างหุ้นส่วนจำกัด', 'หจก', 'นิติบุคคล', 'กิจการร่วมค้า', 'เจวี'),
    'gov_coop': ('สหกรณ์', 'องค์การของรัฐบาล', 'รัฐวิสาหกิจ'),
    'foreign_agent': ('นอกราชอาณาจักร', 'ต่างประเทศ', 'ตัวแทน', 'บริษัทต่างชาติ')}
KIND_W = {'legal_basis': .6, 'refers_to': .9, 'implements': .8, 'amends': .5, 'supersedes': .4, 'see_also': .3, 'refers_to_announcement': .5}
CONF_W = {'สูง': 1.0, 'กลาง': .8, 'ต่ำ': .5, '': .8}

class Cfg:
    """สวิตช์/น้ำหนัก (ใช้ทำ ablation)"""
    def __init__(self, **kw):
        self.dense = True; self.bm25 = True; self.route = True; self.l0 = True; self.graph = True; self.anchors = True
        self.keywords = True; self.synonyms = True; self.status = True; self.focus = True
        self.concept_chunks = False   # ใช้รายการ chunk ที่ผู้จัดทำผูกกับคำพ้อง (เขียนมือ) จึงปิดไว้เป็นค่าตั้งต้น
        self.w_l0 = .5; self.w_comm = .25; self.w_doc = .15; self.w_kw = .15; self.w_anchor = 1.0; self.w_concept = .15
        self.w_dense = None   # None = ใช้ค่าแนะนำใน manifest ของเวกเตอร์ (LSA 0.5, โมเดลประสาท 1.0)
        self.k_comm = 3; self.k_doc = 5; self.n_seed = 5; self.hops = 2; self.decay = .5; self.rrf_k = 20
        for k, v in kw.items():
            assert hasattr(self, k), k; setattr(self, k, v)

class Retriever:
    def __init__(self, embedder='tfidf-lsa-v1', data=DATA, emb_dir=EMB):
        self.U = {}; self.by_level = collections.defaultdict(list)
        for l in open(os.path.join(data, 'units.jsonl'), encoding='utf-8'):
            u = json.loads(l); self.U[u['id']] = u; self.by_level[u['level']].append(u['id'])
        lv = jload(os.path.join(data, 'levels.json'))
        self.embedder, self.manifest = load_embedder(embedder); self.embedder_name = embedder
        self.E = {}; self.ids = {}
        d = os.path.join(emb_dir, embedder)
        for L in ('L0', 'L1', 'L2', 'L3'):
            self.E[L] = np.load(os.path.join(d, f'{L}.npy')); self.ids[L] = json.load(open(os.path.join(d, f'ids_{L}.json'), encoding='utf-8'))
            assert self.ids[L] == self.by_level[L], f'embeddings ไม่ตรงกับ units ที่ระดับ {L} — รัน embed ใหม่'
        # ดัชนีคำ/ตัวอักษร (ข้อความค้นของ L1 เติมคีย์เวิร์ดเมทาดาทา)
        self.bm = {}
        for L in ('L0', 'L1', 'L2', 'L3'):
            texts = [self._bm_text(self.U[i]) for i in self.ids[L]]
            self.bm[L] = (BM25([words(t) for t in texts]), BM25([char_grams(t, 3) for t in texts]))
        self.exp = Expander()
        # กราฟ L1 (สองทิศทาง)
        self.adj = collections.defaultdict(list)
        for e in lv['edges_semantic']:
            self.adj[e['s']].append((e['t'], e['kind'], e.get('conf', ''), e['focus'], e['n'], 'fwd'))
            self.adj[e['t']].append((e['s'], e['kind'], e.get('conf', ''), e['focus'], e['n'], 'rev'))
        self.children = collections.defaultdict(list)
        for i in self.by_level['L0']: self.children[self.U[i]['parent']].append(i)
        self.chunks_of = collections.defaultdict(list)     # (ann|RC, art/sec) -> chunk ids
        for i in self.by_level['L1']:
            k = chunk_key(i); self.chunks_of[(k[0], k[1])].append(i)
        self.l1_index = {i: n for n, i in enumerate(self.ids['L1'])}
        dp = find_data(data, 'doc_requirements.json')
        self.doc_req = jload(dp) if os.path.exists(dp) else None
        rp = find_data(data, 'reference_pointers.json')
        self.ptr = jload(rp) if os.path.exists(rp) else None

    def must_cite(self, query):
        """ตัวชี้การอ้างอิงเรื่องโทษ/ความผิด/ไม่จดทะเบียน: มาตราที่ต้องอ้าง แยก 'มี chunk ตัวบท' กับ 'ยังไม่มีตัวบท' (คำนวณจากฐานข้อมูลปัจจุบัน)"""
        if not self.ptr: return None
        q = (query or '').lower(); out = []
        for p in self.ptr['pointers']:
            if not any(w in q for w in p['trigger_words']): continue
            cites = []
            for c in p['cite']:
                ch = self.chunks_of.get(('RC', c['section']), [])
                cites.append(dict(section=c['section'], role=c['role'], primary=bool(c.get('primary')), has_text=bool(ch), chunks=ch, evidence_faq_docs=[e['doc'] for e in c['evidence_faq']],
                                  status='มี chunk ตัวบทในฐานข้อมูล' if ch else 'ยังไม่มีตัวบท — ห้ามสรุปเนื้อหาเอง'))
            out.append(dict(id=p['id'], topic=p['topic'], cite=cites, missing=[c['section'] for c in cites if not c['has_text']], caution=p['caution']))
        return out or None

    def required_documents(self, query):
        """รายการเอกสารจากตารางเอกสารแนบกรมสรรพากร (ผู้ใช้ยืนยัน ชั่วคราว) ตามชนิดผู้ยื่นที่พบในคำถาม; ไม่พบชนิด = คืนทุกแถวพร้อมคอลัมน์"""
        if not self.doc_req: return None
        q = (query or '').lower(); keys = [k for k, ws in APPLICANT.items() if any(w in q for w in ws)]
        rows = [r for r in self.doc_req['rows'] if (not keys) or any(r['applies'][k] for k in keys)]
        return dict(applicants=keys, applicant_names={k: self.doc_req['applicant_keys'][k] for k in (keys or self.doc_req['applicant_keys'])},
                    rows=[dict(id=r['id'], doc=r['doc'], applies=r['applies'] if not keys else {k: r['applies'][k] for k in keys}, differs_from_statute_text=r['differs_from_statute_text'], status=r['status']) for r in rows],
                    footnote=self.doc_req['footnote'], decision=self.doc_req['decision']['text'])

    def _bm_text(self, u):
        t = u['text']
        if u['level'] == 'L1': t += ' ' + ' '.join(u.get('keywords') or []) + ' ' + (u.get('topic_summary') or '')
        if u['level'] == 'L3': t += ' ' + ' '.join(u.get('keywords') or [])
        return t

    # ---------------------------------------------------------------- คะแนนไฮบริดต่อระดับ (0..1)
    def hybrid(self, L, qvec, qw, qc, cfg):
        n = len(self.ids[L]); lists = []; wts = []
        if cfg.dense and qvec is not None: lists.append(list(np.argsort(-(self.E[L] @ qvec))[:n])); wts.append(cfg.w_dense if cfg.w_dense is not None else self.manifest.get('recommended_dense_weight', 1.0))
        if cfg.bm25:
            s = self.bm[L][0].scores(qw);  lists.append([i for i in np.argsort(-s) if s[i] > 0]); wts.append(1.0)
            s2 = self.bm[L][1].scores(qc); lists.append([i for i in np.argsort(-s2) if s2[i] > 0]); wts.append(.5)
        sc = np.zeros(n)
        for lst, w in zip(lists, wts):
            for r, i in enumerate(lst): sc[i] += w / (cfg.rrf_k + r + 1)
        mx = sum(w / (cfg.rrf_k + 1) for w in wts) or 1
        return sc / mx

    def search(self, query, k=8, cfg=None, budget=7000):
        cfg = cfg or Cfg(); tr = {'query': query}
        ex = self.exp.expand(query) if cfg.synonyms else {'norm': norm_text(query), 'text': norm_text(query), 'added': [], 'concepts': [], 'fixes': []}
        tr['expansion'] = {k_: ex[k_] for k_ in ('norm', 'added', 'concepts', 'fixes')}
        qtext = ex['text']; qw = words(qtext, normed=True); qc = char_grams(qtext, 3, normed=True)
        qvec = self.embedder.encode(qtext, kind='query')[0] if cfg.dense else None
        cite = parse_citations(query) if cfg.anchors else {'sections': [], 'anns': [], 'articles': []}
        tr['citations'] = cite
        history = any(h in query.lower() for h in HISTORY)
        tr['intent'] = {'history': history}
        # ---- route ระดับบน
        s3 = self.hybrid('L3', qvec, qw, qc, cfg); s2 = self.hybrid('L2', qvec, qw, qc, cfg)
        comm_top = [(self.ids['L3'][i], float(s3[i])) for i in np.argsort(-s3)[:cfg.k_comm]]
        doc_top = [(self.ids['L2'][i], float(s2[i])) for i in np.argsort(-s2)[:cfg.k_doc]]
        comm_sc = dict(comm_top) if cfg.route else {}; doc_sc = dict(doc_top) if cfg.route else {}
        tr['route'] = {'communities': comm_top, 'documents': doc_top}
        # ---- ระดับล่าง
        s1 = self.hybrid('L1', qvec, qw, qc, cfg); s0 = self.hybrid('L0', qvec, qw, qc, cfg) if cfg.l0 else None
        l0_best = collections.defaultdict(float); l0_arg = {}
        if cfg.l0:
            for j in np.argsort(-s0)[:80]:
                u = self.U[self.ids['L0'][j]]
                for p in [u['parent']]:
                    if s0[j] > l0_best[p]: l0_best[p] = float(s0[j]); l0_arg[p] = u['id']
        if cfg.l0:                                           # chunk ที่ไม่มีข้อย่อย (เช่น มาตราที่มีวรรคเดียว) ใช้คะแนนระดับ chunk เป็นหลักฐานระดับล่าง ไม่ให้เสียเปรียบ
            for j, cid in enumerate(self.ids['L1']):
                if not self.children.get(cid): l0_best[cid] = float(s1[j])
        anchor = collections.defaultdict(float)
        if cfg.anchors:
            for sec, para in cite['sections']:
                cs = self.chunks_of.get(('RC', sec), [])
                if para:                                           # วรรคที่ระบุ -> chunk ที่มี node วรรคนั้น
                    nid = f"RC/{sec.replace('/', '_')}/p{para}"; hit = [c for c in cs if nid in (self.U.get(nid, {}).get('chunks') or [])]
                    cs = hit or cs
                for c in cs: anchor[c] = max(anchor[c], 1.0)
            for art, ann in cite['articles']:
                if ann:
                    for c in self.chunks_of.get((ann, art), []): anchor[c] = max(anchor[c], 1.0)
                else:
                    for a in ('57', '159', '234'):
                        for c in self.chunks_of.get((a, art), []): anchor[c] = max(anchor[c], .5)
            for ann in cite['anns']:
                for c in self.U.get(f'VAT{ann}', {}).get('children', []): anchor[c] = max(anchor[c], .3)
        concept_chunks = set()
        if cfg.concept_chunks:
            for cid in ex['concepts']: concept_chunks.update(self.exp.concepts[cid].get('chunks', []))
        qn = ex['norm']; cand = {}
        for j, cid in enumerate(self.ids['L1']):
            u = self.U[cid]
            kwn = sum(1 for w in (u.get('keywords') or []) if len(w) >= 3 and norm_text(w) in qn) if cfg.keywords else 0
            comp = dict(base=float(s1[j]), l0=l0_best.get(cid, 0.), comm=max([comm_sc.get(g, 0.) for g in u['communities']] or [0.]),
                        doc=doc_sc.get(u['doc'], 0.), kw=min(kwn, 3) / 3, anchor=anchor.get(cid, 0.), concept=1.0 if cid in concept_chunks else 0.)
            tot = comp['base'] + cfg.w_l0 * comp['l0'] + cfg.w_comm * comp['comm'] + cfg.w_doc * comp['doc'] + cfg.w_kw * comp['kw'] + cfg.w_anchor * comp['anchor'] + cfg.w_concept * comp['concept']
            mult = 1.0
            if cfg.status and not u['is_current'] and not history: mult *= .5
            if cfg.focus and u['focus'] != 'หลัก' and not history and not anchor.get(cid, 0) and not cite['anns']: mult *= .85
            cand[cid] = dict(id=cid, score=tot * mult, comp=comp, mult=mult, via='direct', l0=l0_arg.get(cid))
        # ---- ขยายตามกราฟ
        if cfg.graph:
            seeds = sorted(cand.values(), key=lambda x: -x['score'])[:cfg.n_seed]; top = seeds[0]['score'] if seeds else 1
            frontier = [(s['id'], s['score'] / top, [s['id']]) for s in seeds]; seen_hop = {s['id'] for s in seeds}
            for hop in range(1, cfg.hops + 1):
                nxt = []
                for cid, sc, path in frontier:
                    for nb, kind, conf, foc, n, dr in self.adj.get(cid, []):
                        if nb not in cand: continue
                        if kind in ('amends', 'supersedes') and not history and hop > 1: continue
                        w = KIND_W.get(kind, .3) * CONF_W.get(conf, .8) * (1.0 if dr == 'fwd' else .7) * (1.0 if foc == 'หลัก' else .6)
                        g = sc * w * (cfg.decay ** (hop - 1)) * .25
                        c = cand[nb]
                        if g > c.get('graph', 0):
                            c['score'] += (g - c.get('graph', 0)) * c['mult']; c['graph'] = g
                            if nb not in seen_hop: c['via'] = f"graph:{cid}-{kind}->{nb}";
                        if nb not in seen_hop: nxt.append((nb, g / .25, path + [nb])); seen_hop.add(nb)
                frontier = nxt
        ranked = sorted(cand.values(), key=lambda x: -x['score'])[:max(k, 10)]
        tr['l1'] = [dict(id=r['id'], score=round(r['score'], 4), via=r['via'], comp={a: round(b, 3) for a, b in r['comp'].items()}, graph=round(r.get('graph', 0), 4), mult=r['mult'], l0=r['l0']) for r in ranked]
        hits = ranked[:k]
        mc = self.must_cite(query); extra = []
        if mc:   # ถามเรื่องโทษ/ไม่จดทะเบียน: แนบตัวบทมาตราหลักที่มี chunk (ตามตัวชี้) ถ้ายังไม่อยู่ใน top-k — เพิ่มงบอักขระเท่าที่แนบ (ไม่เกิน 7000)
            have = {h['id'] for h in hits}
            for p_ in mc:
                for c_ in p_['cite']:
                    for cid_ in (c_['chunks'] if c_['primary'] else []):
                        if cid_ not in have: have.add(cid_); extra.append(dict(id=cid_, score=0.0, via='must_cite', l0=None))
        extra_len = min(7000, sum(len(self.U[e['id']]['raw']) + 80 for e in extra))
        ctx, srcs = self.assemble(hits + extra, comm_top, budget + extra_len)
        tr['must_cite_attached'] = [e['id'] for e in extra]
        doc_table = self.required_documents(query) if any(w in query.lower() for w in DOC_INTENT) else None
        return dict(query=query, hits=[dict(id=h['id'], score=h['score'], label=self.U[h['id']]['label'], via=h['via']) for h in hits], context=ctx, sources=srcs, doc_table=doc_table, must_cite=mc, trace=tr)

    # ---------------------------------------------------------------- ประกอบบริบท parent-child
    def assemble(self, hits, comm_top, budget):
        parts, srcs, used = [], [], 0
        if comm_top and comm_top[0][1] > 0:
            g = self.U[comm_top[0][0]]; s = f"[เรื่อง {g['id']}: {g['title']}] {g['summary']}"; parts.append(s); used += len(s)
        for h in hits:
            u = self.U[h['id']]; status = '' if u['is_current'] else ' (ข้อความนี้ถูกแทนที่/แก้ไขแล้ว)'
            marks = ''
            if h.get('l0') and h['l0'] in self.U and self.U[h['l0']]['text'] not in u['raw']: marks = f" | ข้อย่อยที่ตรง: {self.U[h['l0']]['label']}"
            body = u['raw']; room = budget - used
            must = h.get('via') == 'must_cite'      # ตัวบทที่ตัวชี้บังคับแนบ: ไม่ตัด ไม่ข้ามเพราะงบหมด (งบรวมคุมที่ extra_len ใน search)
            if room < 400 and not must: break
            if len(body) > room and not must: body = body[:room] + '…'
            s = f"[{u['label']}{status}{marks}]\n{body}"; parts.append(s); used += len(s)
            srcs.append(dict(id=u['id'], label=u['label'], focus=u['focus'], is_current=u['is_current'], via=h['via']))
        return '\n\n'.join(parts), srcs

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('query'); ap.add_argument('--k', type=int, default=5); ap.add_argument('--embedder', default='tfidf-lsa-v1')
    ap.add_argument('--json', action='store_true'); ap.add_argument('--context', action='store_true'); a = ap.parse_args()
    R = Retriever(a.embedder); out = R.search(a.query, k=a.k)
    if a.json: print(json.dumps(out, ensure_ascii=False, indent=1, default=float)); sys.exit()
    t = out['trace']
    print('คำถาม:', a.query); print('ขยายคำ:', t['expansion']['added'], '| อ้างตรง:', {k: v for k, v in t['citations'].items() if v})
    print('ชุมชน:', [(g, round(s, 3)) for g, s in t['route']['communities']]); print('เอกสาร:', [(d, round(s, 3)) for d, s in t['route']['documents']])
    for h, r in zip(out['hits'], t['l1']): print(f"  {h['score']:.3f}  {h['id']:<18} {h['label']:<38} via={h['via']}  comp={r['comp']}")
    if a.context: print('\n' + out['context'])
