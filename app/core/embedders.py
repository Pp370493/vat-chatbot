# -*- coding: utf-8 -*-
"""ตัวทำ embedding สองแบบ ใช้ไฟล์ผลลัพธ์โครงสร้างเดียวกัน  embeddings/<ชื่อโมเดล>/{manifest.json, L0..L3.npy, ids_L0..L3.json}
  LocalLSA        TF-IDF (คำ newmm + char 3-4 gram) -> LSA (SVD)  ทำงานออฟไลน์ ไม่ต้องดาวน์โหลดโมเดล
  OllamaEmbedder  เรียก Ollama /api/embed (หรือ /api/embeddings)  ใช้บนเครื่องที่มี Ollama (เช่น nomic-embed-text, bge-m3)"""
import os, re, json, pickle, hashlib, time, urllib.request, urllib.error
import numpy as np
from common import norm_text, words, EMB

def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]
def l2(m):
    m = np.asarray(m, dtype=np.float32); n = np.linalg.norm(m, axis=-1, keepdims=True); n[n == 0] = 1
    return m / n

# ฟังก์ชันระดับโมดูล (pickle ได้)
def _words_an(s): return words(s)
def _char_pre(s): return re.sub(r'[\s\W_]+', '', norm_text(s))

class LocalLSA:
    kind = 'local'
    def __init__(self, dim=128, w_word=.7, w_char=.3):
        self.dim, self.w_word, self.w_char = dim, w_word, w_char
        self.name = 'tfidf-lsa-v1'
    def fit(self, texts):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from scipy.sparse import hstack
        self.wv = TfidfVectorizer(analyzer=_words_an, sublinear_tf=True, min_df=1)
        self.cv = TfidfVectorizer(analyzer='char', ngram_range=(3, 4), sublinear_tf=True, min_df=2, preprocessor=_char_pre)
        X = hstack([self.wv.fit_transform(texts) * self.w_word, self.cv.fit_transform(texts) * self.w_char]).tocsr()
        k = min(self.dim, X.shape[0] - 1, X.shape[1] - 1)
        self.svd = TruncatedSVD(k, algorithm='randomized', n_iter=10, random_state=0)
        self.svd.fit(X); self.dim = k
        self.wv.stop_words_ = None; self.cv.stop_words_ = None      # เก็บคำที่ถูกตัดทิ้งไว้ใหญ่มากและไม่ใช้ตอนเข้ารหัส
        self.explained = float(self.svd.explained_variance_ratio_.sum())
        return self
    def encode(self, texts, kind='doc'):
        from scipy.sparse import hstack
        if isinstance(texts, str): texts = [texts]
        X = hstack([self.wv.transform(texts) * self.w_word, self.cv.transform(texts) * self.w_char]).tocsr()
        return l2(self.svd.transform(X))
    def info(self): return dict(model=self.name, type='local-tfidf-lsa', dim=self.dim, explained_variance=round(getattr(self, 'explained', 0), 4), w_word=self.w_word, w_char=self.w_char)
    def save(self, d):
        with open(os.path.join(d, 'model.pkl'), 'wb') as f: pickle.dump(self, f)
    @staticmethod
    def load(d):
        with open(os.path.join(d, 'model.pkl'), 'rb') as f: return pickle.load(f)

class OllamaEmbedder:
    kind = 'ollama'
    def __init__(self, model='nomic-embed-text', host='http://localhost:11434', doc_prefix='search_document: ', query_prefix='search_query: ', batch=16, timeout=120):
        self.model, self.host, self.doc_prefix, self.query_prefix, self.batch, self.timeout = model, host.rstrip('/'), doc_prefix, query_prefix, batch, timeout
        self.name = model.replace(':', '_').replace('/', '_'); self.dim = None
    def _post(self, path, payload):
        req = urllib.request.Request(self.host + path, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=self.timeout) as r: return json.loads(r.read().decode('utf-8'))
    def _embed_batch(self, texts):
        try:
            r = self._post('/api/embed', {'model': self.model, 'input': texts})
            if 'embeddings' in r: return r['embeddings']
        except urllib.error.HTTPError as e:
            if e.code != 404: raise
        return [self._post('/api/embeddings', {'model': self.model, 'prompt': t})['embedding'] for t in texts]   # Ollama รุ่นเก่า
    def encode(self, texts, kind='doc'):
        if isinstance(texts, str): texts = [texts]
        pre = self.doc_prefix if kind == 'doc' else self.query_prefix
        out = []
        for i in range(0, len(texts), self.batch):
            out += self._embed_batch([pre + t for t in texts[i:i + self.batch]])
        m = l2(np.array(out, dtype=np.float32)); self.dim = m.shape[1]; return m
    def info(self): return dict(model=self.model, type='ollama', dim=self.dim, host=self.host, doc_prefix=self.doc_prefix, query_prefix=self.query_prefix)
    def save(self, d): pass
    @staticmethod
    def load(d):
        m = json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8'))
        return OllamaEmbedder(m['model'], m.get('host', 'http://localhost:11434'), m.get('doc_prefix', ''), m.get('query_prefix', ''))

class OnnxE5:
    """multilingual-e5-small (ONNX int8 quantized, 384 มิติ) รันในเครื่อง ไม่ต้องใช้เน็ต/Ollama
    ไฟล์โมเดลอยู่นอกชุดข้อมูล (ใหญ่ ~135MB): ตั้งโฟลเดอร์ด้วย --model-dir หรือ env VAT_E5_DIR (ค่าเริ่มต้น <โฟลเดอร์ชุด>/../โมเดล_e5)"""
    kind = 'onnx-e5'
    def __init__(self, model_dir=None, batch=16, max_tokens=512):
        self.model_dir = model_dir or os.environ.get('VAT_E5_DIR') or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'models', 'multilingual-e5-small-q8')
        self.batch, self.max_tokens = batch, max_tokens; self.name = 'multilingual-e5-small-q8'; self.dim = 384; self._s = None; self.truncated = 0
    def _load(self):
        if self._s is not None: return
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.tok = Tokenizer.from_file(os.path.join(self.model_dir, 'tokenizer.json'))
        self.tok.enable_truncation(self.max_tokens); self.tok.enable_padding(pad_id=1, pad_token='<pad>')
        so = ort.SessionOptions(); so.intra_op_num_threads = os.cpu_count() or 4
        self._s = ort.InferenceSession(os.path.join(self.model_dir, 'model_quantized.onnx'), so, providers=['CPUExecutionProvider'])
        self._in = {i.name for i in self._s.get_inputs()}
    def encode(self, texts, kind='doc'):
        self._load()
        if isinstance(texts, str): texts = [texts]
        pre = 'passage: ' if kind == 'doc' else 'query: '; out = []
        for i in range(0, len(texts), self.batch):
            enc = self.tok.encode_batch([pre + t for t in texts[i:i + self.batch]])
            self.truncated += sum(1 for e in enc if e.overflowing)
            ids = np.array([e.ids for e in enc], dtype=np.int64); am = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {'input_ids': ids, 'attention_mask': am}
            if 'token_type_ids' in self._in: feed['token_type_ids'] = np.zeros_like(ids)
            h = self._s.run(None, feed)[0]; m = am[..., None].astype(np.float32)
            out.append((h * m).sum(1) / m.sum(1))                  # mean pooling ตามคู่มือ e5
        return l2(np.vstack(out))
    def info(self): return dict(model=self.name, type='onnx-e5', dim=self.dim, model_dir_hint=self.model_dir, doc_prefix='passage: ', query_prefix='query: ', max_tokens=self.max_tokens)
    def save(self, d): pass
    @staticmethod
    def load(d):
        m = json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8')); return OnnxE5(None, max_tokens=m.get('max_tokens', 512))

def load_embedder(name):
    d = os.path.join(EMB, name); m = json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8'))
    return (LocalLSA.load(d) if m['type'] == 'local-tfidf-lsa' else OnnxE5.load(d) if m['type'] == 'onnx-e5' else OllamaEmbedder.load(d)), m
