import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { getUserId, unauthorized } from "@/lib/auth";
import { SCOPE_TIER, currentFromParams, scopeOf } from "@/lib/context";

export const runtime = "nodejs";

// Fast literal search — substring match on the command text. Powers the
// instant, per-keystroke phase of the interactive `learn find`. Results are
// ordered by context locality first (same dir > project > machine > global),
// then prefix match, then length.
export async function GET(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q")?.trim();
  const limit = Number(searchParams.get("limit") ?? 8);
  const ctx = currentFromParams(searchParams);
  if (!q) {
    return NextResponse.json({ results: [] });
  }

  // Escape ILIKE wildcards in user input.
  const safe = q.replace(/[\\%_]/g, (c) => `\\${c}`);

  const db = supabaseAdmin();
  const { data, error } = await db
    .from("commands")
    .select("id, command, intent, skills, cwd, project, hostname")
    .eq("user_id", user_id)
    .ilike("command", `%${safe}%`)
    .limit(Math.max(limit * 4, 20));
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const lower = q.toLowerCase();
  const results = (data ?? [])
    .map((r) => ({ ...r, scope: scopeOf(r, ctx) }))
    .sort((a, b) => {
      const t = SCOPE_TIER[a.scope] - SCOPE_TIER[b.scope];
      if (t) return t;
      const ap = a.command.toLowerCase().startsWith(lower) ? 0 : 1;
      const bp = b.command.toLowerCase().startsWith(lower) ? 0 : 1;
      return ap - bp || a.command.length - b.command.length;
    })
    .slice(0, limit);

  return NextResponse.json({ results });
}
