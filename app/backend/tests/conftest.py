import os
import sys
import tempfile

# ต้องตั้งก่อน import app.* — ใช้ฐานข้อมูลชั่วคราว และไม่เรียก LLM จริง
_DB = os.path.join(tempfile.mkdtemp(prefix="vatcopilot-test-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["USE_MOCK_LLM"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
