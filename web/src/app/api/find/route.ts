import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { embed } from "@/lib/annotate";

export const runtime = "nodejs";
export const maxDuration = 30;

// Semantic recall: embed the natural-language query, find nearest commands in
// the user's own history via the match_commands pgvector RPC. This is the
// reveal moment — "submit a job that requires a GPU" → the sbatch you ran.
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const user_id = searchParams.get("user_id");
  const q = searchParams.get("q");
  const limit = Number(searchParams.get("limit") ?? 5);

  if (!user_id || !q?.trim()) {
    return NextResponse.json({ error: "user_id and q required" }, { status: 400 });
  }

  const queryEmbedding = await embed(q);

  const db = supabaseAdmin();
  const { data, error } = await db.rpc("match_commands", {
    p_user_id: user_id,
    query_embedding: queryEmbedding,
    match_count: limit,
  });
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ results: data ?? [] });
}
