import { NextRequest, NextResponse } from "next/server";
import { suggestCommands } from "@/lib/annotate";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";
export const maxDuration = 30;

// `learn new`: turn a natural-language goal into several command suggestions the
// user can pick from (and then practice).
export async function POST(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  let motivation: string | undefined;
  try {
    ({ motivation } = await req.json());
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (!motivation?.trim()) {
    return NextResponse.json({ error: "motivation required" }, { status: 400 });
  }

  const suggestions = await suggestCommands(motivation.trim());
  return NextResponse.json({ suggestions });
}
