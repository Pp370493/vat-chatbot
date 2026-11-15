import { NextRequest, NextResponse } from "next/server";
import { DEMO_MODE, backendUnavailable, demoJson, forward } from "../../../_lib/backend";

export const dynamic = "force-dynamic";
import fs from "fs";
import path from "path";

export async function GET(req: NextRequest) {
  try {
    const fwd = await forward(req, "/api/v1/chat/articles");
    if (fwd) return fwd;
    if (!DEMO_MODE) return backendUnavailable();

    // Fallback: Read local bundled official articles JSON
    const jsonPath = path.join(process.cwd(), "data", "official_vat_articles.json");
    if (fs.existsSync(jsonPath)) {
      const raw = fs.readFileSync(jsonPath, "utf-8");
      const articles = JSON.parse(raw);
      return demoJson(articles);
    }

    return demoJson([]);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
