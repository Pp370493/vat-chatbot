import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const role = body.role || "officer";

    const backendUrl = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
    if (backendUrl) {
      try {
        const res = await fetch(`${backendUrl}/api/v1/auth/quick-switch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (res.ok) return NextResponse.json(await res.json());
      } catch (e) {
        // fallback
      }
    }

    const nameMap: Record<string, string> = {
      officer: "นายสมชาย หน้างาน (Officer)",
      senior_officer: "นางสาวสมศรี ชำนาญการ (Senior Officer)",
      admin: "ผู้ดูแลระบบ (Admin)",
    };

    return NextResponse.json({
      user_id: `user-${role}`,
      full_name: nameMap[role] || "เจ้าหน้าที่สรรพากร",
      email: `${role}@rd.go.th`,
      role: role,
      session_token: `token-${role}-${Date.now()}`,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
