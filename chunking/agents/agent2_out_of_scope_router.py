# -*- coding: utf-8 -*-
"""
Agent 2: Out-of-Scope Router
หน้าที่: จัดการคำถามที่อยู่นอกเหนือขอบเขตงานจดทะเบียน VAT เช่น ภาษีเงินได้บุคคล/นิติบุคคล, 
ภาษีที่ดิน, สรรพสามิต, ศุลกากร, หรือจัดตั้งบริษัท DBD
ผลลัพธ์: ชี้แจงสุภาพพร้อมระบุหน่วยงานและช่องทางติดต่อที่ถูกต้อง
"""

from typing import Dict, Any

class OutOfScopeRouter:
    def __init__(self):
        self.directory = {
            "CIT_PIT": {
                "name": "งานภาษีเงินได้บุคคลธรรมดาและภาษีเงินได้นิติบุคคล",
                "department": "กองบริหารภาษีบุคคล / กองบริหารภาษีธุรกิจขนาดกลางและขนาดย่อม กรมสรรพากร",
                "phone": "ศูนย์สารนิเทศสรรพากร (RD Intelligence Center) โทร. 1161",
                "website": "https://www.rd.go.th",
                "advice": "สำหรับเรื่องการยื่นแบบ ภ.ง.ด.90/91/50/51 หรือการหักลดหย่อนภาษีเงินได้ โปรดติดต่อฝ่ายประเมินภาษี ณ สำนักงานสรรพากรพื้นที่สาขา หรือติดต่อ Call Center 1161"
            },
            "LAND_SIGN": {
                "name": "ภาษีที่ดินและสิ่งปลูกสร้าง / ภาษีป้าย",
                "department": "ฝ่ายรายได้ สำนักงานเขต (ใน กทม.) หรือ กองคลัง เทศบาล / องค์การบริหารส่วนตำบล (อบต.) ในท้องถิ่น",
                "phone": "ติดต่อสำนักงานเขต หรือองค์กรปกครองส่วนท้องถิ่นที่อสังหาริมทรัพย์หรือป้ายตั้งอยู่",
                "website": "https://www.bangkok.go.th (กทม.)",
                "advice": "ภาษีที่ดินและสิ่งปลูกสร้าง รวมถึงภาษีป้าย เป็นภาษีท้องถิ่นที่มิได้อยู่ในความรับผิดชอบของกรมสรรพากร กรุณาติดต่อองค์กรปกครองส่วนท้องถิ่นโดยตรง"
            },
            "EXCISE": {
                "name": "ภาษีสรรพสามิต (สุรา ยาสูบ เครื่องดื่ม น้ำมัน)",
                "department": "กรมสรรพสามิต กระทรวงการคลัง",
                "phone": "สายด่วนกรมสรรพสามิต โทร. 1713",
                "website": "https://www.excise.go.th",
                "advice": "หากต้องการขออนุญาตขายสุรา ยาสูบ ไพ่ หรือเสียภาษีสินค้าสรรพสามิต โปรดติดต่อสำนักงานสรรพสามิตพื้นที่ในเขตท้องที่"
            },
            "CUSTOMS": {
                "name": "ภาษีศุลกากรและพิกัดอัตราศุลกากรนำเข้า-ส่งออก",
                "department": "กรมศุลกากร กระทรวงการคลัง",
                "phone": "สายด่วนกรมศุลกากร โทร. 1164",
                "website": "https://www.customs.go.th",
                "advice": "เรื่องการผ่านพิธีการศุลกากร ใบขนสินค้า หรือพิกัดอัตราภาษีนำเข้า โปรดติดต่อกรมศุลกากรโดยตรง"
            }
        }

    def route(self, query: str, scope_type: str = "CIT_PIT") -> Dict[str, Any]:
        """Convenience alias สำหรับเรียกจาก Orchestrator"""
        res = self.generate_redirect_response({"scope_type": scope_type}, query)
        return {
            "forwarding_advice": res["user_response"],
            "responsible_agency": res["redirect_department"],
            "action_items": res["contact_channel"]
        }

    def generate_redirect_response(self, scope_info: Dict[str, Any], query: str) -> Dict[str, Any]:
        scope_type = scope_info.get("scope_type", "CIT_PIT")
        info = self.directory.get(scope_type, self.directory["CIT_PIT"])

        message = (
            f"ขออภัยค่ะ คำถามของท่านเกี่ยวกับ '{info['name']}' ซึ่งอยู่นอกเหนือขอบเขตงานบริการจดทะเบียนภาษีมูลค่าเพิ่ม (VAT Registration)\n\n"
            f"📌 หน่วยงานที่รับผิดชอบ: {info['department']}\n"
            f"📞 ช่องทางติดต่อ: {info['phone']}\n"
            f"🌐 เว็บไซต์: {info['website']}\n\n"
            f"💡 คำแนะนำเพิ่มเติม: {info['advice']}\n\n"
            f"หากท่านมีคำถามเกี่ยวกับหลักเกณฑ์ วิธีการ และเอกสารการยื่นขอจดทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.01/ภ.พ.20) สามารถสอบถามเพิ่มเติมได้ตลอดเวลาค่ะ"
        )

        return {
            "status": "REDIRECTED",
            "redirect_department": info["department"],
            "contact_channel": info["phone"],
            "user_response": message
        }

if __name__ == "__main__":
    router = OutOfScopeRouter()
    res = router.generate_redirect_response({"scope_type": "LAND_SIGN"}, "ภาษีป้ายร้านค้าต้องไปจ่ายที่ไหน")
    print(res["user_response"])
