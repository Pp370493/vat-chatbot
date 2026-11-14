import json
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_anchored_section(item_id, current_section, title):
    # ฉบับ 57
    if item_id.startswith('VAT57_'):
        m = re.search(r'ข้อ\s*[\d\/\(\),\s]+', current_section)
        sec_num = m.group(0).strip() if m else 'ข้อทั่วไป'
        return f'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) {sec_num}'
    
    # ฉบับ 74 (แก้ไข 57)
    if item_id.startswith('VAT74_'):
        m = re.search(r'ข้อ\s*[\d\/\(\),\s]+', current_section)
        sec_num = m.group(0).strip() if m else ''
        return f'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) {sec_num} ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 74)'
        
    # ฉบับ 139 (แก้ไข 57)
    if item_id.startswith('VAT139_'):
        if 'ข้อ 1' in current_section or 'ข้อ 4' in current_section:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4 วรรคหนึ่ง ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 139)'
        elif 'ข้อ 2' in current_section or 'ข้อ 9' in current_section:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 139)'
        else:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อบังคับใช้ ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 139)'
            
    # ฉบับ 165 (แก้ไข 57)
    if item_id.startswith('VAT165_'):
        if '01' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4(3) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 165)'
        elif '02_A' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(1), (2), (4) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 165)'
        elif '02_B' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 165)'
        elif '02_C' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 165)'
        elif '03' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 165)'
        else:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อบังคับใช้ ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 165)'

    # ฉบับ 215 (แก้ไข 57)
    if item_id.startswith('VAT215_'):
        if '01' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(2) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 215)'
        elif '02' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 215)'
        else:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อบังคับใช้ ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 215)'

    # ฉบับ 245 (แก้ไข 57)
    if item_id.startswith('VAT245_'):
        if '01' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4/1 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 245)'
        elif '02' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 245)'
        else:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อบังคับใช้ ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 245)'

    # ฉบับ 159
    if item_id.startswith('VAT159_'):
        m = re.search(r'ข้อ\s*[\d\/\(\),\s]+', current_section)
        sec_num = m.group(0).strip() if m else 'ข้อทั่วไป'
        return f'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) {sec_num}'

    # ฉบับ 214 (แก้ไข 159)
    if item_id.startswith('VAT214_'):
        if '01_A' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5(1), (2) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'
        elif '01_B' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5(3) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'
        elif '01_C' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5(4) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'
        elif '02' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 6(7) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'
        elif '03' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 8 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'
        elif '04' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'
        else:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อบังคับใช้ ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 214)'

    # ฉบับ 246 (แก้ไข 159)
    if item_id.startswith('VAT246_'):
        if '01' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 1 วรรคสอง ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        elif '02_A' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5(1), (2) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        elif '02_B' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5(3) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        elif '02_C' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5(4), วรรคท้าย ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        elif '03' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5/1 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        elif '04' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 6(8) ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        elif '05' in item_id:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 9 ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'
        else:
            return 'ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อบังคับใช้ ซึ่งแก้ไขเพิ่มเติมโดย (ฉบับที่ 246)'

    # ฉบับ 234 (DBD)
    if item_id.startswith('VAT234_'):
        m = re.search(r'ข้อ\s*[\d\/\(\),\s]+|เอกสารแนบท้ายประกาศ', current_section)
        sec_num = m.group(0).strip() if m else ''
        return f'ประกาศอธิบดีฯ VAT (ฉบับที่ 234) {sec_num} (การจดทะเบียน VAT พร้อมจัดตั้งนิติบุคคลต่อ DBD)'

    return current_section

def update_all():
    json_path = Path("backend/data/official_vat_articles.json")
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    # Dictionary lookup for quick update
    updated_map = {}
    for item in articles:
        new_sec = get_anchored_section(item["id"], item.get("source_section", ""), item.get("title", ""))
        item["source_section"] = new_sec
        # กำหนด content ให้เป็น official_raw_text แท้ๆ ตามที่ผู้ใช้ต้องการ
        raw = item.get("raw_text") or item.get("official_raw_text") or item.get("content")
        item["content"] = raw
        item["raw_text"] = raw
        updated_map[item["id"]] = item

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"Updated {len(articles)} items in {json_path}")

    # อัปเดตลง SQLite ทั้ง 2 ตำแหน่ง
    db_paths = [Path("backend/vat_copilot.db"), Path("vat_copilot.db")]
    for db_path in db_paths:
        if not db_path.exists():
            continue
        engine = create_engine(f"sqlite:///{db_path.as_posix()}", echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            from backend.app.models.models import KbArticle
        except ImportError:
            import sys
            sys.path.insert(0, "backend")
            from app.models.models import KbArticle

        updated_count = 0
        for art in session.query(KbArticle).all():
            if art.id in updated_map:
                u = updated_map[art.id]
                art.source_section = u["source_section"]
                art.content = u["content"]
                updated_count += 1
        session.commit()
        session.close()
        print(f"Updated {updated_count} KbArticles in {db_path}")

if __name__ == "__main__":
    update_all()
