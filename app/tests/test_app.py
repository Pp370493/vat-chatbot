# -*- coding: utf-8 -*-
"""ทดสอบแอป: ใช้เซิร์ฟเวอร์ Ollama จำลอง (ไม่ต้องมีโมเดลจริง)
รัน: python -m unittest app/tests/test_app.py  (จากโฟลเดอร์ราก repo)"""
import os, sys, json, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, APP)

class Fake(BaseHTTPRequestHandler):
    last = None
    def do_GET(self):
        body = json.dumps({'models': []}).encode(); self.send_response(200); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        n = int(self.headers['Content-Length']); Fake.last = json.loads(self.rfile.read(n))
        body = json.dumps({'message': {'role': 'assistant', 'content': 'ทดสอบ: ตอบจากข้อมูลอ้างอิง'}}).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        os.environ['VAT_OLLAMA_HOST'] = f'http://127.0.0.1:{cls.srv.server_port}'
        import server
        cls.server = server
        cls.client = server.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_health(self):
        r = self.client.get('/api/health').get_json()
        self.assertTrue(r['ok']); self.assertTrue(r['ollama'])

    def test_ask_penalty_question(self):
        r = self.client.post('/api/ask', json={'question': 'ไม่จดทะเบียนภาษีมูลค่าเพิ่มมีโทษอย่างไร'}).get_json()
        self.assertTrue(r['llm_ok'])
        self.assertEqual(r['answer'], 'ทดสอบ: ตอบจากข้อมูลอ้างอิง')
        labels = [s['label'] for s in r['sources']]
        self.assertTrue(any('90/2' in l for l in labels), labels)
        self.assertIn('ระวางโทษจำคุกไม่เกินหนึ่งเดือน', r['context'])
        # คำสั่งที่ส่งไปโมเดลต้องมีข้อมูลอ้างอิงและคำถาม
        msgs = Fake.last['messages']
        self.assertEqual(msgs[0]['role'], 'system')
        self.assertIn('ข้อมูลอ้างอิง', msgs[1]['content'])
        self.assertIn('ไม่จดทะเบียน', msgs[1]['content'])

    def test_empty_and_long_question(self):
        self.assertEqual(self.client.post('/api/ask', json={'question': '  '}).status_code, 400)
        self.assertEqual(self.client.post('/api/ask', json={'question': 'ก' * 501}).status_code, 400)

    def test_llm_down_still_returns_sources(self):
        self.server.OLLAMA = 'http://127.0.0.1:9'          # พอร์ตที่ไม่มีบริการ
        try:
            r = self.client.post('/api/ask', json={'question': 'จดทะเบียนภาษีมูลค่าเพิ่มต้องใช้เอกสารอะไร'}).get_json()
            self.assertFalse(r['llm_ok']); self.assertTrue(r['sources'])
        finally:
            self.server.OLLAMA = os.environ['VAT_OLLAMA_HOST']

if __name__ == '__main__':
    unittest.main()
