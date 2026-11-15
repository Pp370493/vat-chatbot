import { NextRequest } from "next/server";
import { DEMO_MODE, backendUnavailable, demoJson, forward } from "../../../../_lib/backend";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const fwd = await forward(req, "/api/v1/chat/inquiries/recent");
  if (fwd) return fwd;
  if (!DEMO_MODE) return backendUnavailable();

  // Standalone mock recent inquiries
  return demoJson([
    {
      query_id: "demo-inq-1",
      conversation_id: "demo-conv-1",
      raw_text: "กำลังสร้างโรงงานเพื่อเตรียมเปิดกิจการผลิตสินค้า ยื่นขอจดทะเบียน VAT ล่วงหน้าได้กี่เดือน",
      answer: "ยื่นคำขอจดทะเบียนล่วงหน้าได้ไม่เกิน 6 เดือนก่อนวันเริ่มประกอบกิจการ ตามประกาศฉบับที่ 57 ข้อ 1",
      status: "answered",
      created_at: new Date().toISOString(),
    },
    {
      query_id: "demo-inq-2",
      conversation_id: "demo-conv-2",
      raw_text: "ขายของออนไลน์อยู่คอนโด ต้องยื่นจด VAT ผ่านเน็ตอย่างเดียวใช่ไหม",
      answer: "ใช่ค่ะ บุคคลธรรมดาขายของออนไลน์ในห้องชุดคอนโด ให้ยื่นผ่านระบบอินเทอร์เน็ต www.rd.go.th ได้เพียงวิธีเดียว",
      status: "answered",
      created_at: new Date().toISOString(),
    },
  ]);
}
