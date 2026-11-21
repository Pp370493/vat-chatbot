# -*- coding: utf-8 -*-
"""VAT chatbot: หน้าเว็บเล็กๆ ถามตอบเรื่องการจดทะเบียนภาษีมูลค่าเพิ่ม
ขั้นตอน: คำถาม -> ตัวค้นข้อมูล (multilevel Graph RAG, เวกเตอร์ e5) -> ส่งข้อมูลอ้างอิงให้โมเดล Ollama ตอบ
รัน:  python server.py   แล้วเปิด http://127.0.0.1:5000
ตัวแปรสภาพแวดล้อม (ไม่บังคับ):
  VAT_LLM_MODEL     ชื่อโมเดลใน Ollama (ค่าเริ่มต้น qwen2.5:3b)
  VAT_OLLAMA_HOST   ที่อยู่ Ollama (ค่าเริ่มต้น http://127.0.0.1:11434)
  VAT_EMBEDDER      ชื่อชุดเวกเตอร์ (ค่าเริ่มต้น multilingual-e5-small-q8)
  VAT_E5_DIR        โฟลเดอร์โมเดล e5 (ค่าเริ่มต้น ../models/multilingual-e5-small-q8)
  VAT_DATA_DIR      โฟลเดอร์ข้อมูล (ค่าเริ่มต้น ../data)
  PORT              พอร์ต (ค่าเริ่มต้น 5000)"""
import os, sys, json, urllib.request

APP = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(APP)
sys.path.insert(0, os.path.join(APP, 'core'))
os.environ.setdefault('VAT_E5_DIR', os.path.join(REPO, 'models', 'multilingual-e5-small-q8'))

from flask import Flask, request, jsonify, render_template
from retrieve import Retriever

LLM = os.environ.get('VAT_LLM_MODEL', 'qwen2.5:3b')
OLLAMA = os.environ.get('VAT_OLLAMA_HOST', 'http://127.0.0.1:11434').rstrip('/')
EMBEDDER = os.environ.get('VAT_EMBEDDER', 'multilingual-e5-small-q8')
MAX_Q = 500
SYSTEM = open(os.path.join(APP, 'system_prompt.md'), encoding='utf-8').read()

app = Flask(__name__, template_folder=os.path.join(APP, 'templates'))
_R = None

def retriever():
    global _R
    if _R is None:
        _R = Retriever(EMBEDDER)          # โหลดครั้งเดียวตอนเริ่มครั้งแรก
    return _R

def ask_llm(question, context):
    msgs = [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': f'ข้อมูลอ้างอิง:\n{context}\n\nคำถาม: {question}'}]
    body = json.dumps({'model': LLM, 'messages': msgs, 'stream': False,
                       'options': {'temperature': 0.1}}).encode('utf-8')
    req = urllib.request.Request(OLLAMA + '/api/chat', data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode('utf-8'))['message']['content']

def ollama_up():
    try:
        with urllib.request.urlopen(OLLAMA + '/api/tags', timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/health')
def health():
    return jsonify(ok=True, embedder=EMBEDDER, llm_model=LLM, ollama=ollama_up())

@app.post('/api/ask')
def ask():
    q = ((request.get_json(silent=True) or {}).get('question') or '').strip()
    if not q:
        return jsonify(error='กรุณาพิมพ์คำถาม'), 400
    if len(q) > MAX_Q:
        return jsonify(error=f'คำถามยาวเกิน {MAX_Q} ตัวอักษร'), 400
    out = retriever().search(q, k=5)
    sources = [dict(label=s['label'], focus=s['focus'], is_current=s['is_current']) for s in out['sources']]
    try:
        answer, llm_ok, err = ask_llm(q, out['context']), True, None
    except Exception as e:
        answer = ('ยังเชื่อมต่อโมเดลภาษาไม่ได้ จึงแสดงเฉพาะข้อมูลอ้างอิงที่ค้นพบ '
                  f'(ตรวจว่า Ollama เปิดอยู่และมีโมเดล {LLM})')
        llm_ok, err = False, str(e)
    return jsonify(answer=answer, sources=sources, must_cite=out['must_cite'],
                   llm_ok=llm_ok, error=err, context=out['context'])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=False)
