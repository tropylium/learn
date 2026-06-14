import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";

// How many commands you've logged, per skill + total — powers `learn score`.
// Simple count-based model: one point per use, no weighting.
export async function GET(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  const db = supabaseAdmin();
  const { data, error } = await db.rpc("skill_counts", { p_user_id: user_id });
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const skills = (data ?? []).map((r: { skill: string; uses: number }) => ({
    skill: r.skill,
    uses: Number(r.uses),
  }));

  const { count: totalUses } = await db
    .from("command_uses")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user_id);

  return NextResponse.json({ total_uses: totalUses ?? 0, skills });
}
