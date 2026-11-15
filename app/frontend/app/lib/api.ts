import { API_BASE_URL } from "../config";

export const SESSION_KEY = "tax_copilot_user";

function sessionToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const saved = localStorage.getItem(SESSION_KEY);
    return saved ? JSON.parse(saved).session_token || null : null;
  } catch {
    return null;
  }
}

/**
 * fetch ไป API พร้อมแนบ session token (Authorization: Bearer)
 * - 401 = session หมดอายุ/ไม่ได้ login → ล้าง session แล้วไปหน้า login
 * - คืน Response ตามเดิม ให้ผู้เรียกตรวจ res.ok เอง
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token = sessionToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/v1/auth/login")) {
    localStorage.removeItem(SESSION_KEY);
    if (window.location.pathname !== "/login") window.location.href = "/login";
  }
  return res;
}
