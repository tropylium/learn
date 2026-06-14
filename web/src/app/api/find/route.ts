import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { embed } from "@/lib/annotate";
import { getUserId, unauthorized } from "@/lib/auth";
import { SCOPE_BOOST, currentFromParams, scopeOf } from "@/lib/context";

export const runtime = "nodejs";
export const maxDuration = 30;

interface MatchRow {
  id: string;
  command: string;
  intent: string | null;
  explanation: string | null;
  complexity: number | null;
  skills: string[] | null;
  similarity: number;
  cwd: string | null;
  project: string | null;
  hostname: string | null;
}

// Semantic recall: embed the natural-language query, find nearest commands in
// the user's own history via the match_commands pgvector RPC, then re-rank so
// commands local to the user's current context (same dir > project > machine)
// surface first. This is the reveal moment — "submit a job that requires a GPU"
// → the sbatch you ran (here).
export async function GET(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q");
  const limit = Number(searchParams.get("limit") ?? 5);
  const ctx = currentFromParams(searchParams);

  if (!q?.trim()) {
    return NextResponse.json({ error: "q required" }, { status: 400 });
  }

  const queryEmbedding = await embed(q);

  const db = supabaseAdmin();
  // Pull a wider candidate set so the context boost can reorder meaningfully.
  const { data, error } = await db.rpc("match_commands", {
    p_user_id: user_id,
    query_embedding: queryEmbedding,
    match_count: Math.max(limit * 4, 20),
  });
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const ranked = ((data ?? []) as MatchRow[])
    .map((r) => {
      const scope = scopeOf(r, ctx);
      return { ...r, scope, score: r.similarity + SCOPE_BOOST[scope] };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return NextResponse.json({ results: ranked });
}
