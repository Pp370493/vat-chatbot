import { NextRequest, NextResponse } from "next/server";

/**
 * ตัวกลางส่งคำขอจากหน้าเว็บไป FastAPI backend
 * - ส่งต่อ method, query string, body และ header Authorization (session token) ตามจริง
 * - สถานะจาก backend (401/403/404/422 ฯลฯ) ส่งกลับตามจริง เพื่อให้หน้าเว็บรู้ว่าต้อง login ใหม่หรือไม่มีสิทธิ์
 * - เชื่อมต่อ backend ไม่ได้ → คืน null แล้วแต่ละ route ตัดสินใจ: DEMO_MODE=true ใช้คำตอบเดโม, ไม่เช่นนั้นตอบ 502
 */
export const BACKEND_URL = (
  process.env.BACKEND_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

// โหมดเดโมใช้เฉพาะงานสาธิตที่ไม่มี backend (เช่น Vercel) — ห้ามเปิดบนเครื่องใช้งานจริง
export const DEMO_MODE = process.env.DEMO_MODE === "true";

// บน CPU คำตอบจริงใช้ราว 1.5–2 นาที จึงรอได้ถึง 300 วินาที (เท่ากับที่ backend รอ Ollama)
const TIMEOUT_MS = 300_000;

export async function forward(req: NextRequest, path: string, bodyText?: string): Promise<NextResponse | null> {
  const url = `${BACKEND_URL}${path}${req.nextUrl.search}`;
  const headers: Record<string, string> = {};
  const auth = req.headers.get("authorization");
  if (auth) headers["Authorization"] = auth;
  const method = req.method.toUpperCase();
  let body: string | undefined;
  if (method !== "GET" && method !== "HEAD") {
    body = bodyText ?? (await req.text());
    headers["Content-Type"] = req.headers.get("content-type") || "application/json";
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { method, headers, body, signal: controller.signal, cache: "no-store" });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
    });
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export function backendUnavailable(): NextResponse {
  return NextResponse.json(
    { detail: "เชื่อมต่อระบบหลัก (backend) ไม่ได้ กรุณาตรวจว่าเปิด backend และ Ollama อยู่" },
    { status: 502 },
  );
}

/** คำตอบโหมดเดโม — ติดธง demo: true ให้หน้าเว็บแสดงป้ายเตือน */
export function demoJson(data: any, init?: ResponseInit): NextResponse {
  const payload = Array.isArray(data) ? data : { ...data, demo: true };
  return NextResponse.json(payload, { ...init, headers: { ...(init?.headers || {}), "x-demo-mode": "1" } });
}
