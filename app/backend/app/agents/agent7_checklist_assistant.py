"""
Agent 7: Document Checklist Assistant Agent (Based on Section 5 of VAT Announcements 57 & 159)
วิเคราะห์คุณลักษณะของผู้ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่ม แล้วสร้าง Document Checklist เฉพาะกรณี
พร้อมระบบประเมินความครบถ้วนของเอกสาร (Human-Controlled Verification)
"""
from typing import List, Dict, Any
from app.core.ollama_client import generate


TAX_PAYER_TYPES = {
    "individual_thai": "บุคคลธรรมดาสัญชาติไทย",
    "individual_foreigner": "บุคคลธรรมดาต่างด้าว (ชาวต่างชาติ)",
    "joint_non_juristic": "สามีภริยา / ห้างหุ้นส่วนสามัญ หรือคณะบุคคลที่มิใช่นิติบุคคล",
    "juristic_thai": "นิติบุคคลไทย (บริษัทจำกัด / ห้างหุ้นส่วนจำกัด)",
    "joint_venture": "กิจการร่วมค้า (Joint Venture)",
    "foreign_entity": "นิติบุคคลต่างประเทศที่ประกอบกิจการชั่วคราว (ตั้งตัวแทนในไทย)",
}

LOCATION_TYPES = {
    "owned": "กรรมสิทธิ์ของตนเอง (บ้านตนเอง/อาคารตนเอง)",
    "rented": "เช่าอาคาร / เช่าสถานที่",
    "consent_free": "ขอใช้สถานที่ของผู้อื่นโดยไม่มีค่าเช่า (ขอใช้ฟรี)",
    "condo_online": "ห้องชุด/คอนโดมิเนียม (ขายสินค้าออนไลน์ มีทะเบียนพาณิชย์)",
    "condo_general": "ห้องชุด/คอนโดมิเนียม (ธุรกิจทั่วไป)",
}

SUBMISSION_CHANNELS = {
    "paper": "ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ (ประกาศฯ ฉบับที่ 57)",
    "internet": "ยื่นผ่านระบบอินเทอร์เน็ต rd.go.th (ประกาศฯ ฉบับที่ 159)",
}


def generate_checklist(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    สร้าง Checklist เอกสารตามหลักเกณฑ์ข้อ 5 ของประกาศอธิบดีฯ ฉบับที่ 57 และ 159
    โดยเทียบกับคุณลักษณะของผู้ยื่นขอจดทะเบียน (Taxpayer Profile)
    """
    channel = profile.get("channel", "paper")  # paper | internet
    taxpayer_type = profile.get("taxpayer_type", "individual_thai")
    location_type = profile.get("location_type", "rented")
    is_power_of_attorney = profile.get("is_power_of_attorney", False)

    items = []

    # 1. แบบคำขอ ภ.พ.01 (แบบพิมพ์หลัก)
    if channel == "paper":
        items.append({
            "id": "doc_pp01",
            "category": "แบบคำขอหลัก",
            "title": "คำขอจดทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.01)",
            "details": "จำนวน 3 ฉบับ (ฉบับจริง 1 ฉบับ และคู่ฉบับ 2 ฉบับ) พร้อมลงลายมือชื่อผู้มีอำนาจ",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4 และข้อ 5",
            "is_mandatory": True,
        })
    else:
        items.append({
            "id": "doc_pp01",
            "category": "แบบคำขอหลัก",
            "title": "การกรอกข้อมูลคำขอแบบ ภ.พ.01 ในระบบอินเทอร์เน็ต",
            "details": "กรอกข้อมูลและยืนยันส่งคำขอผ่านระบบเครือข่ายอินเทอร์เน็ตทางเว็บไซต์ www.rd.go.th",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 1 และข้อ 5",
            "is_mandatory": True,
        })

    # 2. เอกสารแสดงตัวตนตามประเภทผู้ประกอบการ (ข้อ 5(1), 5(2), 5(3))
    if taxpayer_type == "individual_thai":
        items.append({
            "id": "doc_id_thai",
            "category": "เอกสารประจำตัวผู้ประกอบการ",
            "title": "ภาพถ่ายบัตรประจำตัวประชาชนของผู้ประกอบการ",
            "details": "บัตรยังไม่หมดอายุ พร้อมลงลายมือชื่อรับรองสำเนาถูกต้อง",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(1) / (ฉบับที่ 159) ข้อ 5(1)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_house_thai",
            "category": "เอกสารประจำตัวผู้ประกอบการ",
            "title": "ภาพถ่ายสำเนาทะเบียนบ้านของผู้ประกอบการ",
            "details": "หน้าที่มีรายการชื่อของผู้ประกอบการ พร้อมรับรองสำเนาถูกต้อง",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(1) / (ฉบับที่ 159) ข้อ 5(1)",
            "is_mandatory": True,
        })

    elif taxpayer_type == "individual_foreigner":
        items.append({
            "id": "doc_passport_foreigner",
            "category": "เอกสารประจำตัวผู้ประกอบการ",
            "title": "ภาพถ่ายหนังสือเดินทาง (Passport) หรือใบสำคัญประจำตัวคนต่างด้าว",
            "details": "หน้าที่มีรูปถ่ายและวีซ่าที่ยังไม่หมดอายุ พร้อมใบอนุญาตทำงาน (Work Permit) ถ้ามี",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(1) แก้ไขโดย (ฉบับที่ 165) / (ฉบับที่ 159) ข้อ 5(1)",
            "is_mandatory": True,
        })

    elif taxpayer_type == "joint_non_juristic":
        items.append({
            "id": "doc_marriage_or_agreement",
            "category": "เอกสารการรวมกลุ่ม / ห้างหุ้นส่วนสามัญ",
            "title": "ภาพถ่ายทะเบียนสมรส หรือสัญญาจัดตั้งห้างหุ้นส่วนสามัญ/คณะบุคคล",
            "details": "กรณีสามีภริยาแนบทด.22 หรือสัญญา/ข้อตกลงจัดตั้งที่ระบุสัดส่วนการลงทุนและผู้มีอำนาจจัดการ",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(2) / (ฉบับที่ 159) ข้อ 5(2)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_id_partners",
            "category": "เอกสารการรวมกลุ่ม / ห้างหุ้นส่วนสามัญ",
            "title": "ภาพถ่ายบัตรประชาชนและทะเบียนบ้านของผู้เป็นหุ้นส่วนหรือบุคคลทุกคน",
            "details": "สำเนาบัตรและทะเบียนบ้านของผู้ร่วมหุ้น/ทุกคนในคณะบุคคล พร้อมลงลายมือชื่อทุกคน",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(2) / (ฉบับที่ 159) ข้อ 5(2)",
            "is_mandatory": True,
        })

    elif taxpayer_type == "juristic_thai":
        items.append({
            "id": "doc_juristic_cert",
            "category": "เอกสารจัดตั้งนิติบุคคล",
            "title": "ภาพถ่ายหนังสือรับรองของนายทะเบียนหุ้นส่วนบริษัท (อายุไม่เกิน 6 เดือน)",
            "details": "รับรองวัตถุประสงค์ กรรมการผู้มีอำนาจลงนาม และทุนจดทะเบียน",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_moa_shareholder",
            "category": "เอกสารจัดตั้งนิติบุคคล",
            "title": "หนังสือบริคณห์สนธิ ข้อบังคับ และบัญชีรายชื่อผู้ถือหุ้น (บอจ.5)",
            "details": "เอกสารคัดรับรองจากกรมพัฒนาธุรกิจการค้า กระทรวงพาณิชย์",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_director_id",
            "category": "เอกสารจัดตั้งนิติบุคคล",
            "title": "ภาพถ่ายบัตรประชาชนและทะเบียนบ้านของกรรมการผู้มีอำนาจลงนาม",
            "details": "สำเนาบัตรและทะเบียนบ้านของกรรมการผู้จัดการหรือหุ้นส่วนผู้จัดการผู้มีอำนาจผูกพันนิติบุคคล",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })

    elif taxpayer_type == "joint_venture":
        items.append({
            "id": "doc_jv_contract",
            "category": "เอกสารกิจการร่วมค้า (Joint Venture)",
            "title": "ภาพถ่ายสัญญาหรือเอกสารการดำเนินกิจการร่วมค้า",
            "details": "สัญญาความร่วมมือ ข้อตกลงสิทธิหน้าที่ และการแบ่งผลกำไรขาดทุน",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_jv_participants",
            "category": "เอกสารกิจการร่วมค้า (Joint Venture)",
            "title": "เอกสารแสดงตัวตนหรือหนังสือรับรองนิติบุคคลของผู้เข้าร่วมค้าทุกฝ่าย",
            "details": "สำเนาบัตรประชาชน หรือหนังสือรับรองนิติบุคคลของผู้ร่วมค้าทุกนิติบุคคล/บุคคล",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })

    elif taxpayer_type == "foreign_entity":
        items.append({
            "id": "doc_embassy_poa",
            "category": "เอกสารนิติบุคคลต่างประเทศ",
            "title": "หนังสือแต่งตั้งตัวแทนเป็นลายลักษณ์อักษรที่ได้รับการรับรองจากสถานทูต/กงสุล",
            "details": "หนังสือตั้งตัวแทนซึ่งได้รับการรับรองโดยสถานทูต สถานกงสุลไทย หรือ Notary Public",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_rep_id",
            "category": "เอกสารนิติบุคคลต่างประเทศ",
            "title": "ภาพถ่ายบัตรประจำตัวประชาชนหรือหนังสือเดินทางของตัวแทนในประเทศไทย",
            "details": "พร้อมสำเนาทะเบียนบ้านของตัวแทนในประเทศไทย",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_project_contract",
            "category": "เอกสารนิติบุคคลต่างประเทศ",
            "title": "ภาพถ่ายสัญญาโครงการก่อสร้างหรือสัญญาให้บริการในประเทศไทย",
            "details": "หลักฐานการรับงานหรือโครงการที่ต้องเข้ามาดำเนินการชั่วคราวในราชอาณาจักร",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(3) / (ฉบับที่ 159) ข้อ 5(3)",
            "is_mandatory": True,
        })

    # 3. เอกสารสถานที่ตั้งสถานประกอบการ (ข้อ 5(5) ฉบับ 57 / ข้อ 5(4) ฉบับ 159)
    items.append({
        "id": "doc_establishment_house_reg",
        "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
        "title": "ภาพถ่ายสำเนาทะเบียนบ้านที่ตั้งสถานประกอบการ",
        "details": "หน้าแรกที่ระบุบ้านเลขที่ตั้งสถานประกอบการ",
        "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
        "is_mandatory": True,
    })

    if location_type == "owned":
        items.append({
            "id": "doc_ownership_proof",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "หลักฐานแสดงการเป็นเจ้าของกรรมสิทธิ์ในสถานที่",
            "details": "ภาพถ่ายโฉนดที่ดิน สัญญาซื้อขาย (ทด.13) หรือหนังสือแสดงกรรมสิทธิ์ของผู้ประกอบการ",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
            "is_mandatory": True,
        })

    elif location_type == "rented":
        items.append({
            "id": "doc_lease_agreement",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "ภาพถ่ายสัญญาเช่าสถานประกอบการ",
            "details": "สัญญาเช่าที่ระบุชื่อผู้ให้เช่า ผู้เช่า ที่ตั้ง และระยะเวลาเช่าชัดเจน",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_landlord_id_house",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "ภาพถ่ายบัตรประชาชนและทะเบียนบ้านของผู้ให้เช่า",
            "details": "พร้อมเอกสารแสดงกรรมสิทธิ์ของผู้ให้เช่า เช่น โฉนดที่ดิน หรือสัญญาเช่าช่วงที่ได้รับความยินยอม",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
            "is_mandatory": True,
        })

    elif location_type == "consent_free":
        items.append({
            "id": "doc_consent_letter",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "หนังสือยินยอมให้ใช้สถานที่ตั้งสถานประกอบการ (โดยไม่มีค่าเช่า)",
            "details": "หนังสือยินยอมที่ระบุความสัมพันธ์และอนุญาตให้ใช้เป็นสถานประกอบการจด VAT",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_owner_id_proof",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "ภาพถ่ายบัตรประชาชน ทะเบียนบ้าน และโฉนดที่ดินของเจ้าของสถานที่ผู้ยินยอม",
            "details": "เอกสารยืนยันว่าเจ้าของเป็นผู้มีอำนาจให้ความยินยอมจริง",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
            "is_mandatory": True,
        })

    elif location_type == "condo_online":
        items.append({
            "id": "doc_online_commercial_reg",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "ใบทะเบียนพาณิชย์อิเล็กทรอนิกส์ (พาณิชยกิจซื้อขายผ่านอินเทอร์เน็ต)",
            "details": "จดทะเบียนพาณิชย์ e-Commerce ระบุชื่อเว็บไซต์/แพลตฟอร์มชัดเจน (ได้รับยกเว้นไม่ต้องมีหนังสือยินยอมนิติคอนโด)",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4/1 และ ข้อ 5(5)(ก) แก้ไขโดย (ฉบับที่ 215)",
            "is_mandatory": True,
        })

    elif location_type == "condo_general":
        items.append({
            "id": "doc_condo_juristic_cert",
            "category": "เอกสารสถานที่ตั้งสถานประกอบการ",
            "title": "หนังสือรับรองจากผู้จัดการนิติบุคคลอาคารชุด",
            "details": "หนังสือยินยอมให้นำห้องชุดไปใช้ประกอบกิจการค้าตามกฎหมายว่าด้วยอาคารชุด",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ก) / (ฉบับที่ 159) ข้อ 5(4)(ก)",
            "is_mandatory": True,
        })

    # 4. ป้ายชื่อและแผนที่ตั้ง (ข้อ 5(5)(ข))
    items.append({
        "id": "doc_map",
        "category": "สถานที่และป้ายชื่อ",
        "title": "แผนที่แสดงที่ตั้งของสถานประกอบการโดยสังเขป",
        "details": "ระบุจุดสังเกตสำคัญ ถนน และบริเวณใกล้เคียง",
        "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ข) / (ฉบับที่ 159) ข้อ 5(4)(ข)",
        "is_mandatory": True,
    })
    items.append({
        "id": "doc_signboard_photo",
        "category": "สถานที่และป้ายชื่อ",
        "title": "ภาพถ่ายแสดงป้ายชื่อสถานประกอบการ",
        "details": "ภาพถ่ายที่แสดงป้ายชื่อผู้ประกอบการหรือชื่อทางการค้าติดตั้ง ณ สถานประกอบการอย่างเปิดเผยชัดเจน",
        "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5(5)(ข) / (ฉบับที่ 159) ข้อ 5(4)(ข)",
        "is_mandatory": True,
    })

    # 5. การมอบอำนาจ (ถ้ามี)
    if is_power_of_attorney:
        items.append({
            "id": "doc_power_of_attorney",
            "category": "การมอบอำนาจ",
            "title": "หนังสือมอบอำนาจ ปิดอากรแสตมป์ถูกต้องตามกฎหมาย",
            "details": "ปิดอากรแสตมป์ 10 บาท (มอบครั้งเดียว) หรือ 30 บาท (มอบทำกิจการมากกว่าหนึ่งครั้ง) พร้อมลายมือชื่อครบถ้วน",
            "legal_ref": "ประมวลรัษฎากร ข้อกำหนดการมอบอำนาจตามประกาศอธิบดีฯ ข้อ 5",
            "is_mandatory": True,
        })
        items.append({
            "id": "doc_poa_parties_id",
            "category": "การมอบอำนาจ",
            "title": "ภาพถ่ายบัตรประจำตัวประชาชนของผู้มอบอำนาจและผู้รับมอบอำนาจ",
            "details": "บัตรยังไม่หมดอายุ และลงลายมือชื่อรับรองสำเนาถูกต้อง",
            "legal_ref": "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5 / (ฉบับที่ 159) ข้อ 5",
            "is_mandatory": True,
        })

    return {
        "profile": profile,
        "taxpayer_label": TAX_PAYER_TYPES.get(taxpayer_type, taxpayer_type),
        "location_label": LOCATION_TYPES.get(location_type, location_type),
        "channel_label": SUBMISSION_CHANNELS.get(channel, channel),
        "total_documents": len(items),
        "items": items,
    }


def evaluate_checklist(items_status: List[Dict[str, Any]], profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    ประเมินผลการตรวจรับเอกสารของเจ้าหน้าที่ (Human-Controlled Verification)
    items_status: list of {id, title, status: "received"|"missing"|"not_applicable", is_mandatory}
    """
    total = len(items_status)
    received = [item for item in items_status if item.get("status") == "received"]
    missing = [item for item in items_status if item.get("status") in ["missing", "pending"] and item.get("is_mandatory", True)]
    not_applicable = [item for item in items_status if item.get("status") == "not_applicable"]

    is_complete = len(missing) == 0

    if is_complete:
        verdict_status = "complete"
        verdict_title = "เอกสารครบถ้วนสมบูรณ์ตามหลักเกณฑ์ข้อ 5"
        verdict_message = (
            "ผู้ประกอบการได้ยื่นเอกสารหลักฐานครบถ้วนตามประกาศอธิบดีกรมสรรพากร (ฉบับที่ 57 หรือ 159) ข้อ 5 แล้ว "
            "เจ้าหน้าที่สามารถออกใบรับคำขอ และดำเนินการตรวจสอบสภาพสถานประกอบการตามข้อ 6 "
            "เพื่อเตรียมออกใบทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.20) ตามข้อ 7 ต่อไปได้ค่ะ"
        )
    else:
        verdict_status = "incomplete"
        verdict_title = f"เอกสารยังไม่ครบถ้วน (ขาดอีก {len(missing)} รายการ)"
        missing_titles = "\n".join([f"• {item.get('title')} ({item.get('legal_ref', '')})" for item in missing])
        verdict_message = (
            f"จากการตรวจสอบเอกสารตามประกาศอธิบดีกรมสรรพากร ข้อ 5 พบว่ายังขาดเอกสารสำคัญ {len(missing)} รายการ ดังนี้:\n\n"
            f"{missing_titles}\n\n"
            f"⚠️ **ข้อพึงระวังตามข้อ 6 ของประกาศฯ**:\n"
            f"หากผู้ประกอบการไม่นำส่งหรือไม่อัปโหลดเอกสารหลักฐานดังกล่าวให้ครบถ้วนภายในระยะเวลาที่เจ้าหน้าที่กำหนด "
            f"เจ้าพนักงานสรรพากรมีอำนาจไม่ออกใบทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.20) ให้แก่ผู้ประกอบการได้ตามข้อ 6 ค่ะ"
        )

    return {
        "is_complete": is_complete,
        "verdict_status": verdict_status,
        "verdict_title": verdict_title,
        "verdict_message": verdict_message,
        "total_count": total,
        "received_count": len(received),
        "missing_count": len(missing),
        "missing_items": missing,
        "received_items": received,
        "not_applicable_count": len(not_applicable),
    }
