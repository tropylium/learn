import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";

// Commands the user has logged in the current project — powers `learn here`
// and the contextual shell-hook reminder ("3 slurm commands you logged").
export async function GET(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  const { searchParams } = new URL(req.url);
  const project = searchParams.get("project");

  const db = supabaseAdmin();
  let query = db
    .from("commands")
    .select("command, intent, skills, complexity")
    .eq("user_id", user_id)
    .order("created_at", { ascending: false })
    .limit(20);
  if (project) query = query.eq("project", project);

  const { data, error } = await query;
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  return NextResponse.json({ results: data ?? [] });
}
