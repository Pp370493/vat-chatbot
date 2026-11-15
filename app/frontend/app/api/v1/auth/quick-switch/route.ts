import { NextRequest } from "next/server";
import { backendUnavailable, forward } from "../../../_lib/backend";

export const dynamic = "force-dynamic";

// สลับบทบาทได้เฉพาะเมื่อ backend เปิด ENABLE_DEMO_ROLE_SWITCH — ไม่มีคำตอบสำรองฝั่งเว็บอีกต่อไป
export async function POST(req: NextRequest) {
  return (await forward(req, "/api/v1/auth/quick-switch")) ?? backendUnavailable();
}
