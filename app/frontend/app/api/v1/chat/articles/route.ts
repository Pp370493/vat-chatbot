import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  try {
    // If external backend is configured and reachable
    const backendUrl = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
    if (backendUrl) {
      try {
        const res = await fetch(`${backendUrl}/api/v1/chat/articles`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          return NextResponse.json(data);
        }
      } catch (e) {
        console.warn("Backend proxy failed, falling back to local articles JSON:", e);
      }
    }

    // Fallback: Read local bundled official articles JSON
    const jsonPath = path.join(process.cwd(), "data", "official_vat_articles.json");
    if (fs.existsSync(jsonPath)) {
      const raw = fs.readFileSync(jsonPath, "utf-8");
      const articles = JSON.parse(raw);
      return NextResponse.json(articles);
    }

    return NextResponse.json([]);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
