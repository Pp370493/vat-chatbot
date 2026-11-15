import { NextRequest, NextResponse } from "next/server";
import { DEMO_MODE, backendUnavailable, demoJson, forward } from "../../../../_lib/backend";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const bodyText = await req.text();
    const fwd = await forward(req, "/api/v1/chat/form-session/generate-checklist", bodyText);
    if (fwd) return fwd;
    if (!DEMO_MODE) return backendUnavailable();
    const body = JSON.parse(bodyText || "{}");

    // Standalone Agent 7 Section 5 items generator for Vercel demo
    const { taxpayer_type, location_type, is_power_of_attorney, channel } = body;
    const items: any[] = [];

    // Base identity items
    if (taxpayer_type === "individual_thai") {
      items.push({
        id: "item_thai_id",
        category: "identity",
        title: "บัตรประจำตัวประชาชนผู้ประกอบการ (แสดงตัวจริง)",
        details: "บัตรประจำตัวประชาชนที่ยังไม่หมดอายุ พร้อมสำเนาลงนามรับรอง",
        legal_ref: "ข้อ 5 (1) ประกาศอธิบดีฯ VAT (ฉบับที่ 57/159)",
        is_mandatory: true,
      });
      items.push({
        id: "item_thai_house_reg",
        category: "identity",
        title: "สำเนาทะเบียนบ้านของผู้ประกอบการ",
        details: "ทะเบียนบ้านที่ระบุชื่อผู้ขอจดทะเบียน",
        legal_ref: "ข้อ 5 (1) ประกาศอธิบดีฯ VAT (ฉบับที่ 57/159)",
        is_mandatory: true,
      });
    } else if (taxpayer_type === "corporate_thai") {
      items.push({
        id: "item_corp_cert",
        category: "identity",
        title: "หนังสือรับรองการจดทะเบียนนิติบุคคล (DBD)",
        details: "อายุไม่เกิน 6 เดือน พร้อมวัตถุประสงค์และบัญชีรายชื่อผู้ถือหุ้น (บอจ.5)",
        legal_ref: "ข้อ 5 (3) ประกาศอธิบดีฯ VAT (ฉบับที่ 57/159)",
        is_mandatory: true,
      });
      items.push({
        id: "item_corp_director_id",
        category: "identity",
        title: "บัตรประชาชน/พาสปอร์ต ของกรรมการผู้มีอำนาจลงนาม",
        details: "แสดงบัตรตัวจริงพร้อมสำเนา",
        legal_ref: "ข้อ 5 (3) ประกาศอธิบดีฯ VAT (ฉบับที่ 57/159)",
        is_mandatory: true,
      });
    } else if (taxpayer_type === "individual_foreigner") {
      items.push({
        id: "item_foreign_passport",
        category: "identity",
        title: "หนังสือเดินทาง (Passport) หรือใบสำคัญประจำตัวคนต่างด้าว",
        details: "พร้อมใบอนุญาตประกอบธุรกิจหรือหลักฐานการเข้าเมืองที่ถูกต้อง",
        legal_ref: "ข้อ 5 (1) (ข) ประกาศอธิบดีฯ VAT (ฉบับที่ 57/159)",
        is_mandatory: true,
      });
    }

    // Location items
    if (location_type === "rented") {
      items.push({
        id: "item_lease_agree",
        category: "location",
        title: "สัญญาเช่าอาคาร/สถานที่ประกอบการ",
        details: "ระบุชื่อผู้เช่าตรงกับผู้ประกอบการ และวัตถุประสงค์การใช้พื้นที่",
        legal_ref: "ข้อ 5 (5) (ฉบับ 57) / ข้อ 5 (4) (ฉบับ 159)",
        is_mandatory: true,
      });
      items.push({
        id: "item_lessor_consent",
        category: "location",
        title: "หนังสือยินยอมให้ใช้สถานที่และหลักฐานกรรมสิทธิ์ของผู้ให้เช่า",
        details: "สำเนาบัตร ปชช. และทะเบียนบ้านของผู้ให้เช่า/เจ้าของกรรมสิทธิ์",
        legal_ref: "ข้อ 5 (5) (ฉบับ 57) / ข้อ 5 (4) (ฉบับ 159)",
        is_mandatory: true,
      });
    } else if (location_type === "condo_online") {
      items.push({
        id: "item_condo_ownership",
        category: "location",
        title: "เอกสารแสดงกรรมสิทธิ์ห้องชุด หรือสัญญาเช่าห้องชุด",
        details: "กรรมสิทธิ์ห้องชุดเพื่อการอยู่อาศัยที่ใช้เป็นสถานประกอบการออนไลน์",
        legal_ref: "ข้อ 4/1 (ฉบับ 245) / ข้อ 1 (ฉบับ 246)",
        is_mandatory: true,
      });
      items.push({
        id: "item_ecom_reg",
        category: "location",
        title: "ใบทะเบียนพาณิชย์อิเล็กทรอนิกส์ (DBD Registered)",
        details: "หลักฐานการจดทะเบียนพาณิชย์อิเล็กทรอนิกส์สำหรับขายออนไลน์",
        legal_ref: "ข้อ 4/1 (ฉบับ 57 แก้ไขโดย 245)",
        is_mandatory: true,
      });
    }

    // Signboard and Map
    items.push({
      id: "item_signboard_photo",
      category: "location",
      title: "ภาพถ่ายป้ายชื่อผู้ประกอบการ และสถานประกอบการ",
      details: "ป้ายชื่อติดในที่เปิดเผยเห็นได้ง่าย พร้อมภาพถ่ายหน้าร้านและแผนที่สังเขป",
      legal_ref: "ข้อ 5 (5) (ฉบับ 57) / ข้อ 5 (4) (ฉบับ 159)",
      is_mandatory: true,
    });

    // Power of attorney
    if (is_power_of_attorney) {
      items.push({
        id: "item_poa_doc",
        category: "authorization",
        title: "หนังสือมอบอำนาจ ปิดอากรแสตมป์ถูกต้องตามกฎหมาย",
        details: "ระบุอำนาจในการยื่นคำขอจดทะเบียน VAT ชัดเจน พร้อมบัตรประชาชนตัวจริงของผู้รับมอบอำนาจ",
        legal_ref: "ข้อ 5 (4) (ฉบับ 57) / ข้อ 5 (3) (ฉบับ 159)",
        is_mandatory: true,
      });
    }

    return demoJson({
      session_id: `fsess-${Date.now()}`,
      profile: body,
      checklist_items: items,
      total_items: items.length,
      mandatory_count: items.filter((x) => x.is_mandatory).length,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
