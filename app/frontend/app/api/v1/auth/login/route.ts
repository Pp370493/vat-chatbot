import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const backendUrl = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
    if (backendUrl) {
      try {
        const res = await fetch(`${backendUrl}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (res.ok) return NextResponse.json(await res.json());
      } catch (e) {
        // fallback
      }
    }

    // Standalone login for officer demo
    return NextResponse.json({
      session_token: "demo-officer-token",
      user_id: "demo-officer-id",
      full_name: "เจ้าหน้าที่สรรพากร (Demo Officer)",
      role: "officer",
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
