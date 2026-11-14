# -*- coding: utf-8 -*-
"""
Agent 7: Checklist Assistant Agent (Dynamic Document Preparation Assistant)
หน้าที่: สร้างรายการเอกสารตรวจสอบ (Checklist) และประเมินความครบถ้วนของเอกสาร
อ้างอิงตาม ข้อ 5 แห่งประกาศอธิบดีกรมสรรพากร เกี่ยวกับภาษีมูลค่าเพิ่ม
(ฉบับที่ 57 และฉบับที่ 159 แก้ไขเพิ่มเติมโดยฉบับที่ 165, 215 และ 246)

รองรับ 4 มิติสำคัญ:
1. ช่องทางการยื่น (Channel): WALK_IN (กระดาษ) / ONLINE (อินเทอร์เน็ต) / DBD (Single Window)
2. ประเภทผู้ขอ (Applicant Type): บุคคลธรรมดา / สามีภริยา / ห้างหุ้นส่วนสามัญ / คณะบุคคล / นิติบุคคลไทย / ต่างด้าว / กิจการร่วมค้า
3. ประเภทสถานที่ตั้ง (Premises Type): เจ้าของเอง / เช่า / ยินยอมให้ใช้ฟรี / คอนโดมิเนียม (อาคารชุด)
4. การมอบอำนาจ (Proxy): ยื่นเอง / มอบอำนาจ
"""

from typing import Dict, Any, List

class ChecklistAssistantAgent:
    def __init__(self):
        pass

    def generate_checklist(self, 
                           channel: str = "WALK_IN", 
                           applicant_type: str = "INDIVIDUAL", 
                           premises_type: str = "RENTED", 
                           is_proxy: bool = False,
                           is_online_seller: bool = False) -> Dict[str, Any]:
        """
        สร้างตาราง Checklist อัตโนมัติตามมิติต่างๆ
        """
        channel = channel.upper()
        applicant_type = applicant_type.upper()
        premises_type = premises_type.upper()

        checklist_items = []
        legal_clauses = []
        special_exemptions = []

        # 1. เอกสารแบบฟอร์มคำขอ
        if channel == "WALK_IN":
            checklist_items.append({
                "category": "แบบฟอร์มคำขอ",
                "item": "แบบคำขอจดทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.01)",
                "copies": "3 ฉบับ (ต้นฉบับ 1, สำเนา 2)",
                "note": "กรอกรายละเอียดและลงลายมือชื่อผู้มีอำนาจทุกฉบับ"
            })
            legal_clauses.append("ข้อ 5 วรรคหนึ่ง แห่งประกาศฯ (ฉบับที่ 57)")
        elif channel == "ONLINE":
            checklist_items.append({
                "category": "แบบฟอร์มคำขอ",
                "item": "ยื่นแบบ ภ.พ.01 ผ่านระบบเครือข่ายอินเทอร์เน็ตที่ rd.go.th",
                "copies": "ข้อมูลอิเล็กทรอนิกส์ในระบบ",
                "note": "กรอกข้อมูลและแนบไฟล์สแกนหลักฐาน (PDF/JPG)"
            })
            legal_clauses.append("ข้อ 5 แห่งประกาศฯ (ฉบับที่ 159 แก้ไขเพิ่มเติมโดย 246)")
        elif channel == "DBD":
            checklist_items.append({
                "category": "แบบฟอร์มคำขอ",
                "item": "ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มพร้อมคำขอจดทะเบียนจัดตั้งนิติบุคคล ณ DBD",
                "copies": "Single Window Portal",
                "note": "ต้องลงนามในข้อรับรอง 5 ข้อตามแบบแนบท้ายประกาศฯ (ฉบับที่ 234)"
            })
            legal_clauses.append("ข้อ 1 และข้อ 4 แห่งประกาศฯ (ฉบับที่ 234)")

        # 2. เอกสารแสดงตัวตนตามประเภทผู้ขอ
        if applicant_type == "INDIVIDUAL":
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สำเนาบัตรประจำตัวประชาชนของผู้ประกอบการ",
                "copies": "1 ชุด (รับรองสำเนาถูกต้อง)",
                "note": "ยังไม่หมดอายุ พร้อมแสดงบัตรตัวจริงกรณี Walk-in"
            })
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สำเนาทะเบียนบ้านของผู้ประกอบการ",
                "copies": "1 ชุด (รับรองสำเนาถูกต้อง)",
                "note": "หน้าที่มีชื่อและรายการเกี่ยวกับบ้าน"
            })
            legal_clauses.append("ข้อ 5(1) แห่งประกาศฯ (ฉบับที่ 57 / 159)")

        elif applicant_type == "SPOUSE":
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สำเนาบัตรประจำตัวประชาชนและสำเนาทะเบียนบ้านของสามีและภริยา",
                "copies": "ฝ่ายละ 1 ชุด",
                "note": "ลงนามรับรองสำเนาทั้งสามีและภริยา"
            })
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สำเนาทะเบียนสมรส หรือหนังสือรับรองการสมรส",
                "copies": "1 ชุด",
                "note": "ต้องมีหลักฐานการสมรสตามกฎหมาย"
            })
            legal_clauses.append("ข้อ 5(2) แห่งประกาศฯ (ฉบับที่ 57 แก้ไขโดย 215 / ฉบับ 159)")

        elif applicant_type in ["PARTNERSHIP", "NON_JURISTIC_BODY"]:
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สำเนาบัตรประจำตัวประชาชนและทะเบียนบ้านของผู้เป็นหุ้นส่วนทุกคน/บุคคลทุกคน",
                "copies": "คนละ 1 ชุด",
                "note": "ทุกคนต้องลงนามรับรองสำเนาถูกต้อง"
            })
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สัญญาจัดตั้งห้างหุ้นส่วนสามัญ หรือหนังสือแสดงการตกลงจัดตั้งคณะบุคคล",
                "copies": "1 ชุด",
                "note": "ระบุชื่อผู้จัดการ ผู้มีอำนาจทำการแทน และสัดส่วนการลงทุน"
            })
            legal_clauses.append("ข้อ 5(2) แห่งประกาศฯ (ฉบับที่ 57 แก้ไขโดย 215 / ฉบับ 159)")

        elif applicant_type == "CORPORATE_THAI":
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "หนังสือรับรองการจดทะเบียนนิติบุคคล พร้อมวัตถุประสงค์ (คัดไม่เกิน 6 เดือน)",
                "copies": "1 ชุด",
                "note": "กรรมการผู้มีอำนาจลงลายมือชื่อและประทับตราสำคัญของบริษัท"
            })
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "สำเนาบัตรประชาชนและทะเบียนบ้านของกรรมการผู้มีอำนาจลงนามทุกคน",
                "copies": "คนละ 1 ชุด",
                "note": "ลงลายมือชื่อรับรองสำเนาถูกต้อง"
            })
            legal_clauses.append("ข้อ 5(3) แห่งประกาศฯ (ฉบับที่ 57 แก้ไขโดย 165 / ฉบับ 159 แก้ไขโดย 214)")

        elif applicant_type == "CORPORATE_FOREIGN":
            checklist_items.append({
                "category": "หลักฐานตัวตน",
                "item": "หนังสือแต่งตั้งตัวแทนในประเทศไทย และหนังสือรับรองสถานะนิติบุคคลต่างประเทศ",
                "copies": "1 ชุด",
                "note": "ต้องผ่านการรับรองจากสถานทูตหรือกงสุล หรือ Notary Public (ไม่เกิน 6 เดือน)"
            })
            legal_clauses.append("ข้อ 5(3)(จ) แห่งประกาศฯ (ฉบับที่ 57)")

        # 3. เอกสารเกี่ยวกับสถานประกอบการ (Premises)
        checklist_items.append({
            "category": "สถานประกอบการ",
            "item": "สำเนาทะเบียนบ้านที่ใช้เป็นที่ตั้งสถานประกอบการ",
            "copies": "1 ชุด",
            "note": "ต้องตรงกับที่อยู่ที่ระบุในแบบ ภ.พ.01"
        })
        checklist_items.append({
            "category": "สถานประกอบการ",
            "item": "แผนที่ตั้งสถานประกอบการโดยสังเขป และภาพถ่ายสถานประกอบการ",
            "copies": "1 ชุด (ภาพถ่ายป้ายชื่อ + ภายนอก + ภายใน)",
            "note": "ต้องแสดงป้ายชื่อสถานประกอบการอย่างชัดเจน"
        })

        if premises_type == "RENTED":
            checklist_items.append({
                "category": "สถานประกอบการ",
                "item": "สัญญาเช่าอสังหาริมทรัพย์ / สัญญาเช่าอาคาร",
                "copies": "1 ชุด",
                "note": "ระบุชื่อผู้เช่าตรงกับผู้ขอจด VAT พร้อมปิดอากรแสตมป์ถูกต้อง"
            })
            checklist_items.append({
                "category": "สถานประกอบการ",
                "item": "สำเนาบัตรประชาชนและทะเบียนบ้านของผู้ให้เช่า / เอกสารสิทธิ์ (โฉนดที่ดิน)",
                "copies": "1 ชุด",
                "note": "เพื่อพิสูจน์สิทธิในการให้เช่า"
            })
        elif premises_type == "FREE_USE":
            checklist_items.append({
                "category": "สถานประกอบการ",
                "item": "หนังสือยินยอมให้ใช้สถานที่ตั้งสถานประกอบการ",
                "copies": "1 ชุด",
                "note": "ลงนามโดยเจ้าของกรรมสิทธิ์ในอาคารหรือที่ดิน"
            })
            checklist_items.append({
                "category": "สถานประกอบการ",
                "item": "สำเนาบัตรประชาชนและทะเบียนบ้านของเจ้าของสถานที่ผู้ให้ความยินยอม",
                "copies": "1 ชุด",
                "note": "พร้อมหลักฐานกรรมสิทธิ์ (เช่น สำเนาโฉนดที่ดิน หรือสัญญาซื้อขาย)"
            })
        elif premises_type == "CONDO":
            # กรณีอาคารชุด (คอนโด)
            if (channel == "ONLINE" and is_online_seller) or (is_online_seller and applicant_type == "INDIVIDUAL"):
                special_exemptions.append("★ สิทธิยกเว้นพิเศษตามประกาศฯ ฉบับที่ 246 (ข้อ 5(4)): ผู้ค้าออนไลน์สัญชาติไทยที่ใช้อาคารชุดเป็นที่ตั้งสถานประกอบการ 'ไม่ต้องใช้หนังสือรับรองจากนิติบุคคลอาคารชุด' (เพียงแนบสัญญาเช่าหรือหนังสือยินยอมและทะเบียนห้องชุด)")
            else:
                checklist_items.append({
                    "category": "สถานประกอบการ",
                    "item": "หนังสือรับรองจากนิติบุคคลอาคารชุด อนุญาตให้ใช้อาคารชุดเป็นสถานประกอบการ",
                    "copies": "1 ชุด",
                    "note": "ตาม พ.ร.บ.อาคารชุด เฉพาะห้องชุดที่อยู่ในพื้นที่ที่จัดไว้เพื่อการพาณิชย์ หรือได้รับอนุญาต"
                })
            legal_clauses.append("ข้อ 5(5)(ก) ฉบับ 57 แก้ไขโดย 215 / ข้อ 5(4) ฉบับ 159 แก้ไขโดย 246")

        # 4. กรณีมอบอำนาจ
        if is_proxy:
            checklist_items.append({
                "category": "การมอบอำนาจ",
                "item": "หนังสือมอบอำนาจ",
                "copies": "1 ฉบับ (ปิดอากรแสตมป์ 10 หรือ 30 บาท)",
                "note": "ระบุขอบเขตอำนาจในการยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มและรับเอกสาร"
            })
            checklist_items.append({
                "category": "การมอบอำนาจ",
                "item": "สำเนาบัตรประชาชนของผู้มอบอำนาจและผู้รับมอบอำนาจ",
                "copies": "ฝ่ายละ 1 ชุด",
                "note": "ลงลายมือชื่อรับรองสำเนาถูกต้องทั้งสองฝ่าย"
            })
            legal_clauses.append("ข้อ 5(4) แห่งประกาศฯ (ฉบับที่ 57)")

        return {
            "summary_title": f"รายการเอกสารสำหรับ: {applicant_type} | ช่องทาง: {channel} | สถานที่: {premises_type}",
            "checklist": checklist_items,
            "special_exemptions": special_exemptions,
            "legal_citations": list(set(legal_clauses)),
            "instructions": "โปรดเตรียมเอกสารให้ครบถ้วนและลงลายมือชื่อรับรองสำเนาถูกต้องทุกแผ่น เพื่อความรวดเร็วในการพิจารณาออกใบทะเบียน ภ.พ.20"
        }

if __name__ == "__main__":
    agent7 = ChecklistAssistantAgent()

    # ทดสอบเคสแม่ค้าออนไลน์อยู่คอนโด
    res_condo = agent7.generate_checklist(
        channel="ONLINE",
        applicant_type="INDIVIDUAL",
        premises_type="CONDO",
        is_proxy=False,
        is_online_seller=True
    )
    print("=== Checklist Case: Online Seller in Condo ===")
    print("Title:", res_condo["summary_title"])
    print("Special Exemptions:", res_condo["special_exemptions"])
    print("Total items:", len(res_condo["checklist"]))
    for it in res_condo["checklist"]:
        print(f"[{it['category']}] {it['item']} ({it['copies']}) - {it['note']}")
