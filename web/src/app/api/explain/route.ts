import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { explainTokens } from "@/lib/annotate";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";
export const maxDuration = 30;

// Per-token breakdown for `learn practice`. The CLI sends the command + its own
// tokenization (so alignment is exact). We return one explanation per token,
// plus the command's intent. Cached on the command row (breakdown jsonb) so each
// command is explained by the LLM only once.
export async function POST(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  let command: string | undefined;
  let tokens: string[] | undefined;
  try {
    ({ command, tokens } = await req.json());
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (!command?.trim() || !Array.isArray(tokens) || tokens.length === 0) {
    return NextResponse.json({ error: "command and tokens required" }, { status: 400 });
  }

  const db = supabaseAdmin();

  // Look up the user's row for this command (for cache + intent).
  const { data: row } = await db
    .from("commands")
    .select("id, intent, breakdown")
    .eq("user_id", user_id)
    .eq("command", command)
    .maybeSingle();

  // Cache hit: stored breakdown whose tokens match this request.
  const cached = row?.breakdown as { tokens?: string[]; parts?: string[] } | null;
  if (cached?.parts && JSON.stringify(cached.tokens) === JSON.stringify(tokens)) {
    return NextResponse.json({ parts: cached.parts, intent: row?.intent ?? "" });
  }

  const parts = await explainTokens(command, tokens);

  // Cache on the row if it exists (no row → arbitrary command not in history;
  // still works, just not cached).
  if (row?.id) {
    await db.from("commands").update({ breakdown: { tokens, parts } }).eq("id", row.id);
  }

  return NextResponse.json({ parts, intent: row?.intent ?? "" });
}
