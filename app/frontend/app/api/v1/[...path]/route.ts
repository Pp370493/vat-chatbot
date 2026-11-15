import { NextRequest } from "next/server";
import { backendUnavailable, forward } from "../../_lib/backend";

// ส่งต่อทุก endpoint ที่ไม่มี route เฉพาะ (escalations, analytics, สถานะเคส, logout, me ฯลฯ) ไป backend
export const dynamic = "force-dynamic";

async function handle(req: NextRequest, { params }: { params: { path: string[] } }) {
  const res = await forward(req, `/api/v1/${params.path.map(encodeURIComponent).join("/")}`);
  return res ?? backendUnavailable();
}

export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE };
