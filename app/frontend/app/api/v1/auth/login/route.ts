import { NextRequest } from "next/server";
import { DEMO_MODE, backendUnavailable, demoJson, forward } from "../../../_lib/backend";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const res = await forward(req, "/api/v1/auth/login");
  if (res) return res;
  if (!DEMO_MODE) return backendUnavailable();
  // โหมดเดโม (ไม่มี backend): ผู้ใช้สมมติบทบาทเจ้าหน้าที่
  return demoJson({
    session_token: "demo-officer-token",
    user_id: "demo-officer-id",
    full_name: "เจ้าหน้าที่สรรพากร (Demo)",
    email: "demo@example.local",
    role: "officer",
  });
}
