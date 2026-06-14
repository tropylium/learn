import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";

// Fast literal search — substring match on the command text. Powers the
// instant, per-keystroke phase of the interactive `learn find` (the slower
// semantic phase hits /api/find). Prefix matches are ranked first.
export async function GET(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q")?.trim();
  const limit = Number(searchParams.get("limit") ?? 8);
  if (!q) {
    return NextResponse.json({ results: [] });
  }

  // Escape ILIKE wildcards in user input.
  const safe = q.replace(/[\\%_]/g, (c) => `\\${c}`);

  const db = supabaseAdmin();
  const { data, error } = await db
    .from("commands")
    .select("id, command, intent, skills")
    .eq("user_id", user_id)
    .ilike("command", `%${safe}%`)
    .limit(limit);
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Rank prefix matches before mid-string matches.
  const lower = q.toLowerCase();
  const results = (data ?? []).sort((a, b) => {
    const ap = a.command.toLowerCase().startsWith(lower) ? 0 : 1;
    const bp = b.command.toLowerCase().startsWith(lower) ? 0 : 1;
    return ap - bp || a.command.length - b.command.length;
  });

  return NextResponse.json({ results });
}
