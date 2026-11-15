import { NextRequest, NextResponse } from "next/server";
import { DEMO_MODE, backendUnavailable, demoJson, forward } from "../../../../_lib/backend";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const bodyText = await req.text();
    const fwd = await forward(req, "/api/v1/chat/form-session/evaluate-checklist", bodyText);
    if (fwd) return fwd;
    if (!DEMO_MODE) return backendUnavailable();
    const body = JSON.parse(bodyText || "{}");

    const { items = [] } = body;
    const completed = items.filter((x: any) => x.checked);
    const missing = items.filter((x: any) => !x.checked);
    const isReady = missing.length === 0;

    let summaryText = "";
    if (isReady) {
      summaryText =
        "✅ **ผลการตรวจรับเอกสารคำขอจดทะเบียน VAT (Agent 7)**\n\n" +
        "เอกสารหลักฐานครบถ้วนสมบูรณ์ตามหลักเกณฑ์ **ข้อ 5 ของประกาศอธิบดีกรมสรรพากร**\n" +
        "• เจ้าหน้าที่สามารถรับคำขอและออกใบรับคำขอเพื่อดำเนินการต่อไปได้ทันที";
    } else {
      summaryText =
        "⚠️ **ผลการตรวจรับเอกสารคำขอจดทะเบียน VAT (Agent 7)**\n\n" +
        `เอกสารยังขาดอีก ${missing.length} รายการตามหลักเกณฑ์ข้อ 5:\n` +
        missing.map((m: any, i: number) => `${i + 1}. ${m.title}`).join("\n") +
        "\n\n*หมายเหตุ:* หากเอกสารไม่ครบถ้วน เจ้าพนักงานอาจไม่ออกใบทะเบียนตามเกณฑ์ข้อ 6";
    }

    return demoJson({
      is_ready_to_submit: isReady,
      summary_text: summaryText,
      total_items: items.length,
      completed_count: completed.length,
      missing_count: missing.length,
      missing_items: missing,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
